# disk.py
#
# Copyright 2022 mirkobrombin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundationat version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
from gettext import gettext as _
from typing import Union

from gi.repository import Adw, GObject, Gtk

from vanilla_installer.core.disks import DisksManager, Diskutils, Partition
from vanilla_installer.core.system import Systeminfo


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-disk.ui")
class VanillaDefaultDiskEntry(Adw.ActionRow):
    __gtype_name__ = "VanillaDefaultDiskEntry"

    chk_button = Gtk.Template.Child()

    def __init__(self, parent, disk, **kwargs):
        super().__init__(**kwargs)
        self.__parent = parent
        self.__disk = disk
        self.set_title(disk.name)
        self.set_subtitle(disk.pretty_size)

        self.chk_button.connect(
            "toggled", self.__parent.on_disk_entry_toggled, self.disk
        )

    @property
    def is_active(self):
        if self.chk_button.get_active():
            return True

    @property
    def disk(self):
        return self.__disk

    @property
    def disk_block(self):
        return self.__partition.disk_block


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-partition-row.ui")
class PartitionRow(Adw.ActionRow):
    __gtype_name__ = "PartitionRow"

    select_button = Gtk.Template.Child()
    suffix_bin = Gtk.Template.Child()

    __siblings: list

    __partition_fs_types = ["btrfs", "ext4", "ext3", "fat32", "xfs"]

    def __init__(self, page, parent, partition, modifiable, default_fs, **kwargs):
        super().__init__(**kwargs)
        self.__page = page
        self.__parent = parent
        self.__partition = partition
        self.__modifiable = modifiable
        self.__default_fs = default_fs

        self.set_title(partition.partition)
        self.set_subtitle(partition.pretty_size)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

        if self.__modifiable:
            self.__add_dropdown()

    def __add_dropdown(self):
        fs_dropdown = Gtk.DropDown.new_from_strings(self.__partition_fs_types)
        fs_dropdown.set_valign(Gtk.Align.CENTER)
        fs_dropdown.set_visible(False)
        if self.__partition.fs_type in self.__partition_fs_types:
            fs_dropdown.set_selected(
                self.__partition_fs_types.index(self.__partition.fs_type)
            )
        else:
            fs_dropdown.set_selected(
                self.__partition_fs_types.index(self.__default_fs))
        fs_dropdown.connect("notify::selected", self.__on_dropdown_selected)
        self.suffix_bin.set_child(fs_dropdown)

    def add_siblings(self, siblings):
        self.__siblings = siblings

    def __on_check_button_toggled(self, widget):
        dropdown = self.suffix_bin.get_child()

        # Sets all sibling dropdowns as not visible
        for sibling in self.__siblings:
            sibling_dropdown = sibling.suffix_bin.get_child()
            if sibling_dropdown:
                sibling_dropdown.set_visible(False)

        # Only the currently selected partition can be edited
        if dropdown:
            dropdown.set_visible(True)
            fs_type = self.__partition_fs_types[dropdown.get_selected()]
            self.__parent.set_subtitle(
                f"{self.__partition.pretty_size} ({fs_type})")
        else:
            self.__parent.set_subtitle(f"{self.__partition.pretty_size}")

        self.__parent.set_title(self.__partition.partition)
        self.__page.selected_partitions[self.__parent.get_buildable_id()][
            "partition"
        ] = self.__partition

        # Sets already selected partitions as not sensitive
        self.__page.update_partition_rows()
        # Checks whether we can proceed with installation
        self.__page.update_apply_button_status()
        # Checks whether root partitions are the same size
        self.__page.check_root_partitions_size_equal()
        # Checks whether selected partitions are big enough
        self.__page.check_selected_partitions_sizes()

    def __on_dropdown_selected(self, widget, _):
        fs_type = self.__partition_fs_types[widget.get_selected()]
        size = self.__partition.pretty_size
        self.__page.selected_partitions[self.__parent.get_buildable_id()][
            "fstype"
        ] = fs_type
        self.__parent.set_subtitle(f"{size} ({fs_type})")


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-partition.ui")
class PartitionSelector(Adw.PreferencesPage):
    __gtype_name__ = "PartitionSelector"

    open_gparted_group = Gtk.Template.Child()
    open_gparted_row = Gtk.Template.Child()
    launch_gparted = Gtk.Template.Child()

    boot_part = Gtk.Template.Child()
    efi_part = Gtk.Template.Child()
    bios_part = Gtk.Template.Child()
    roots_part = Gtk.Template.Child()
    home_part = Gtk.Template.Child()
    swap_part = Gtk.Template.Child()

    boot_part_expand = Gtk.Template.Child()
    efi_part_expand = Gtk.Template.Child()
    bios_part_expand = Gtk.Template.Child()
    abroot_a_part_expand = Gtk.Template.Child()
    abroot_b_part_expand = Gtk.Template.Child()
    home_part_expand = Gtk.Template.Child()
    swap_part_expand = Gtk.Template.Child()

    abroot_info_button = Gtk.Template.Child()
    abroot_info_popover = Gtk.Template.Child()
    use_swap_part = Gtk.Template.Child()

    boot_small_error = Gtk.Template.Child()
    efi_small_error = Gtk.Template.Child()
    bios_small_error = Gtk.Template.Child()
    roots_small_error = Gtk.Template.Child()
    home_small_error = Gtk.Template.Child()
    root_sizes_differ_error = Gtk.Template.Child()

    # NOTE: Keys must be the same name as template children
    __selected_partitions: dict[str, dict[str, Union[Partition, str, None]]] = {
        "boot_part_expand": {
            "mountpoint": "/boot",
            "min_size": 943_718_400,  # 900 MB
            "partition": None,
            "fstype": None,
        },
        "efi_part_expand": {
            "mountpoint": "/boot/efi",
            "min_size": 536_870_912,  # 512 MB
            "partition": None,
            "fstype": None,
        },
        "bios_part_expand": {
            "mountpoint": "",
            "min_size": 1_048_576,  # 512 MB
            "partition": None,
            "fstype": None,
        },
        "abroot_a_part_expand": {
            "mountpoint": "/",
            "min_size": 10_737_418_240,  # 10 GB
            "partition": None,
            "fstype": None,
        },
        "abroot_b_part_expand": {
            "mountpoint": "/",
            "min_size": 10_737_418_240,  # 10 GB
            "partition": None,
            "fstype": None,
        },
        "home_part_expand": {
            "mountpoint": "/var",
            "min_size": 5_368_709_120,  # 5 GB
            "partition": None,
            "fstype": None,
        },
        "swap_part_expand": {
            "mountpoint": "swap",
            "partition": None,
            "fstype": None,
        },
    }
    __valid_root_partitions = False
    __valid_partition_sizes = False

    def __init__(self, parent, partitions, **kwargs):
        super().__init__(**kwargs)
        self.__parent = parent
        self.__partitions = sorted(partitions)

        self.launch_gparted.connect("clicked", self.__on_launch_gparted)
        self.abroot_info_button.connect(
            "clicked", self.__on_info_button_clicked)
        self.use_swap_part.connect("state-set", self.__on_use_swap_toggled)

        self.__boot_part_rows = self.__generate_partition_list_widgets(
            self.boot_part_expand, "ext4", False
        )
        for i, widget in enumerate(self.__boot_part_rows):
            self.boot_part_expand.add_row(widget)
            widget.add_siblings(
                self.__boot_part_rows[:i] + self.__boot_part_rows[i + 1:]
            )
            self.__selected_partitions["boot_part_expand"]["fstype"] = "ext4"

        if Systeminfo.is_uefi():
            # Configure EFI rows
            self.__efi_part_rows = self.__generate_partition_list_widgets(
                self.efi_part_expand, "fat32", False
            )
            for i, widget in enumerate(self.__efi_part_rows):
                self.efi_part_expand.add_row(widget)
                widget.add_siblings(
                    self.__efi_part_rows[:i] + self.__efi_part_rows[i + 1:]
                )
                self.__selected_partitions["efi_part_expand"]["fstype"] = "fat32"

            # Remove BIOS rows
            self.bios_part.set_visible(False)
            if "bios_part_expand" in self.__selected_partitions:
                del self.__selected_partitions["bios_part_expand"]
        else:
            # Configure BIOS rows
            self.__bios_part_rows = self.__generate_partition_list_widgets(
                self.bios_part_expand, "ext4", False
            )
            for i, widget in enumerate(self.__bios_part_rows):
                self.bios_part_expand.add_row(widget)
                widget.add_siblings(
                    self.__bios_part_rows[:i] + self.__bios_part_rows[i + 1:]
                )
                self.__selected_partitions["bios_part_expand"]["fstype"] = "ext4"

            # Remove EFI rows
            self.efi_part.set_visible(False)
            if "efi_part_expand" in self.__selected_partitions:
                del self.__selected_partitions["efi_part_expand"]

        self.__abroot_a_part_rows = self.__generate_partition_list_widgets(
            self.abroot_a_part_expand, "btrfs", False
        )
        for i, widget in enumerate(self.__abroot_a_part_rows):
            self.abroot_a_part_expand.add_row(widget)
            widget.add_siblings(
                self.__abroot_a_part_rows[:i] +
                self.__abroot_a_part_rows[i + 1:]
            )
            self.__selected_partitions["abroot_a_part_expand"]["fstype"] = "btrfs"

        self.__abroot_b_part_rows = self.__generate_partition_list_widgets(
            self.abroot_b_part_expand, "btrfs", False
        )
        for i, widget in enumerate(self.__abroot_b_part_rows):
            self.abroot_b_part_expand.add_row(widget)
            widget.add_siblings(
                self.__abroot_b_part_rows[:i] +
                self.__abroot_b_part_rows[i + 1:]
            )
            self.__selected_partitions["abroot_b_part_expand"]["fstype"] = "btrfs"

        self.__home_part_rows = self.__generate_partition_list_widgets(
            self.home_part_expand
        )
        for i, widget in enumerate(self.__home_part_rows):
            self.home_part_expand.add_row(widget)
            widget.add_siblings(
                self.__home_part_rows[:i] + self.__home_part_rows[i + 1:]
            )
            self.__selected_partitions["home_part_expand"]["fstype"] = "btrfs"

        self.__swap_part_rows = self.__generate_partition_list_widgets(
            self.swap_part_expand, "swap", False
        )
        for i, widget in enumerate(self.__swap_part_rows):
            self.swap_part_expand.add_row(widget)
            widget.add_siblings(
                self.__swap_part_rows[:i] + self.__swap_part_rows[i + 1:]
            )
            self.__selected_partitions["swap_part_expand"]["fstype"] = "swap"

        self.update_apply_button_status()

    def __on_launch_gparted(self, widget):
        proc = subprocess.Popen(["ps", "-C", "gparted"])
        proc.wait()
        if proc.returncode == 0:
            partitions_changed_toast = Adw.Toast.new(
                _(
                    "GParted is already running. Only one instance of GParted is permitted."
                )
            )
            partitions_changed_toast.set_timeout(5)
            self.__parent.group_partitions.add_toast(partitions_changed_toast)
        else:
            subprocess.Popen(["/usr/sbin/gparted"])

    def __generate_partition_list_widgets(
        self, parent_widget, default_fs="btrfs", add_dropdowns=True
    ):
        partition_widgets = []

        for i, partition in enumerate(self.__partitions):
            partition_row = PartitionRow(
                self, parent_widget, partition, add_dropdowns, default_fs
            )
            if i != 0:
                partition_row.select_button.set_group(
                    partition_widgets[0].select_button
                )
            partition_widgets.append(partition_row)

        parent_widget.set_sensitive(len(partition_widgets) > 0)

        return partition_widgets

    def __on_info_button_clicked(self, widget):
        self.abroot_info_popover.popup()

    def update_apply_button_status(self):
        for k, val in self.__selected_partitions.items():
            if val["partition"] == None and (
                k != "swap_part_expand" or self.use_swap_part.get_active()
            ):
                self.__parent.set_btn_apply_sensitive(False)
                return

        if self.__valid_root_partitions and self.__valid_partition_sizes:
            self.__parent.set_btn_apply_sensitive(True)

    def check_root_partitions_size_equal(self):
        if self.__selected_partitions["abroot_a_part_expand"]["partition"]:
            a_root_part_size = self.__selected_partitions["abroot_a_part_expand"][
                "partition"
            ].size
        else:
            a_root_part_size = None

        if self.__selected_partitions["abroot_b_part_expand"]["partition"]:
            b_root_part_size = self.__selected_partitions["abroot_b_part_expand"][
                "partition"
            ].size
        else:
            b_root_part_size = None

        if (
            a_root_part_size
            and b_root_part_size
            and a_root_part_size != b_root_part_size
        ):
            self.abroot_a_part_expand.get_style_context().add_class("error")
            self.abroot_b_part_expand.get_style_context().add_class("error")
            self.root_sizes_differ_error.set_visible(True)
            self.__valid_root_partitions = False
        else:
            if self.abroot_a_part_expand.get_style_context().has_class("error"):
                self.abroot_a_part_expand.get_style_context().remove_class("error")
            if self.abroot_b_part_expand.get_style_context().has_class("error"):
                self.abroot_b_part_expand.get_style_context().remove_class("error")
            self.root_sizes_differ_error.set_visible(False)
            self.__valid_root_partitions = True

    def check_selected_partitions_sizes(self):
        # Clear any existing errors
        self.__valid_partition_sizes = True
        self.boot_small_error.set_visible(False)
        if Systeminfo.is_uefi():
            self.efi_small_error.set_visible(False)
        else:
            self.bios_small_error.set_visible(False)
        self.roots_small_error.set_visible(False)
        self.home_small_error.set_visible(False)
        if self.boot_part_expand.get_style_context().has_class("error"):
            self.boot_part_expand.get_style_context().remove_class("error")
        if Systeminfo.is_uefi():
            if self.efi_part_expand.get_style_context().has_class("error"):
                self.efi_part_expand.get_style_context().remove_class("error")
        else:
            if self.bios_part_expand.get_style_context().has_class("error"):
                self.bios_part_expand.get_style_context().remove_class("error")
        if self.abroot_a_part_expand.get_style_context().has_class("error"):
            self.abroot_a_part_expand.get_style_context().remove_class("error")
        if self.abroot_b_part_expand.get_style_context().has_class("error"):
            self.abroot_b_part_expand.get_style_context().remove_class("error")
        if self.home_part_expand.get_style_context().has_class("error"):
            self.home_part_expand.get_style_context().remove_class("error")

        for partition, info in self.__selected_partitions.items():
            if "min_size" in info and info["partition"] is not None:
                if info["min_size"] > info["partition"].size:
                    self.__valid_partition_sizes = False
                    error_description = _("Partition must be at least {}").format(
                        Diskutils.pretty_size(info["min_size"])
                    )
                    if partition == "boot_part_expand":
                        self.boot_part_expand.get_style_context().add_class("error")
                        self.boot_small_error.set_description(
                            error_description)
                        self.boot_small_error.set_visible(True)
                    elif partition == "efi_part_expand":
                        self.efi_part_expand.get_style_context().add_class("error")
                        self.efi_small_error.set_description(error_description)
                        self.efi_small_error.set_visible(True)
                    elif (
                        partition == "abroot_a_part_expand"
                        or partition == "abroot_b_part_expand"
                    ):
                        self.abroot_a_part_expand.get_style_context().add_class("error")
                        self.abroot_b_part_expand.get_style_context().add_class("error")
                        self.roots_small_error.set_description(
                            error_description)
                        self.roots_small_error.set_visible(True)
                    elif partition == "home_part_expand":
                        self.home_part_expand.get_style_context().add_class("error")
                        self.home_small_error.set_description(
                            error_description)
                        self.home_small_error.set_visible(True)

        # Special case for BIOS, where the partitions needs to be EXACTLY 1 MiB
        if not Systeminfo.is_uefi():
            size = self.__selected_partitions["bios_part_expand"]["min_size"]
            partition = self.__selected_partitions["bios_part_expand"]["partition"]
            error_description = _("Partition must EXACTLY {}").format(
                Diskutils.pretty_size(size)
            )
            if partition is not None:
                if size != partition.size:
                    self.bios_part_expand.get_style_context().add_class("error")
                    self.bios_small_error.set_description(error_description)
                    self.bios_small_error.set_visible(True)

    def __on_use_swap_toggled(self, widget, state):
        if not state:
            for child_row in self.__swap_part_rows:
                child_row.select_button.set_active(False)

            self.__selected_partitions["swap_part_expand"]["partition"] = None
            self.swap_part_expand.set_title(_("No partition selected"))
            self.swap_part_expand.set_subtitle(
                _("Please select a partition from the options below")
            )
            self.update_partition_rows()

        self.update_apply_button_status()

    def update_partition_rows(self):
        rows = [
            self.__boot_part_rows,
            self.__abroot_a_part_rows,
            self.__abroot_b_part_rows,
            self.__home_part_rows,
            self.__swap_part_rows,
        ]

        if Systeminfo.is_uefi():
            rows.append(self.__efi_part_rows)
        else:
            rows.append(self.__bios_part_rows)

        for row in rows:
            for child_row in row:
                row_partition = child_row.get_title()

                # The row where partition was selected still has to be sensitive
                if child_row.select_button.get_active():
                    child_row.set_sensitive(True)
                    continue

                is_used = False
                for __, val in self.__selected_partitions.items():
                    if (
                        val["partition"] is not None
                        and val["partition"].partition == row_partition
                    ):
                        is_used = True
                child_row.set_sensitive(not is_used)

    def cleanup(self):
        for partition, info in self.__selected_partitions.items():
            for k, __ in info.items():
                if k not in ["mountpoint", "min_size"]:
                    self.__selected_partitions[partition][k] = None

    @property
    def selected_partitions(self):
        return self.__selected_partitions


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-disk.ui")
class VanillaDefaultDiskPartModal(Adw.Window):
    __gtype_name__ = "VanillaDefaultDiskPartModal"
    __gsignals__ = {
        "partitioning-set": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    group_partitions = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()

    def __init__(self, window, parent, disks, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__parent = parent
        self.__disks = disks
        self.set_transient_for(self.__window)

        self.__partitions = []
        for disk in self.__disks:
            for part in disk.partitions:
                self.__partitions.append(part)

        # signals
        self.btn_cancel.connect("clicked", self.__on_btn_cancel_clicked)
        self.btn_apply.connect("clicked", self.__on_btn_apply_clicked)
        self.connect("notify::is-active", self.__on_window_active)

        self.__partition_selector = PartitionSelector(self, self.__partitions)
        self.group_partitions.set_child(self.__partition_selector)

    def __on_window_active(self, widget, value):
        # Only update partitions when window has gained focus
        if self.is_active():
            current_partitions = self.__partitions.copy()

            self.__partitions = []
            for disk in self.__disks:
                disk.update_partitions()
                for part in disk.partitions:
                    self.__partitions.append(part)

            if current_partitions != self.__partitions:
                self.__partition_selector.cleanup()
                self.__partition_selector.unrealize()
                self.__partition_selector = PartitionSelector(
                    self, self.__partitions)
                self.group_partitions.set_child(self.__partition_selector)
                partitions_changed_toast = Adw.Toast.new(
                    _("Partitions have changed. Current selections have been cleared.")
                )
                partitions_changed_toast.set_timeout(5)
                self.group_partitions.add_toast(partitions_changed_toast)

    def __on_btn_cancel_clicked(self, widget):
        self.__partition_selector.cleanup()
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__parent.set_partition_recipe(self.partition_recipe)
        self.emit("partitioning-set", "")
        self.destroy()

    def set_btn_apply_sensitive(self, val):
        self.btn_apply.set_sensitive(val)

    @property
    def partition_recipe(self):
        recipe = {}

        for __, info in self.__partition_selector.selected_partitions.items():
            # Partition can be None if user didn't configure swap
            if not isinstance(info["partition"], Partition):
                continue

            recipe[info["partition"].partition] = {
                "fs": info["fstype"],
                "mp": info["mountpoint"],
                "pretty_size": info["partition"].pretty_size,
                "size": info["partition"].size,
            }

        return recipe


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-disk-confirm.ui")
class VanillaDefaultDiskConfirmModal(Adw.Window):
    __gtype_name__ = "VanillaDefaultDiskConfirmModal"

    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()

    def __init__(self, window, partition_recipe, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.set_transient_for(self.__window)
        self.default_width, self.default_height = self.get_default_size()

        # signals
        self.btn_cancel.connect("clicked", self.__on_btn_cancel_clicked)
        self.btn_apply.connect("clicked", self.__on_btn_apply_clicked)

        for partition, values in partition_recipe.items():
            entry = Adw.ActionRow()
            if partition == "auto":
                entry.set_title(partition_recipe[partition]["disk"])
                entry.set_subtitle(_("Entire disk will be used."))
            else:
                self.set_default_size(self.default_width, 650)
                if partition == "disk":
                    continue
                entry.set_title(partition)
                entry.set_subtitle(
                    _("Will be formatted in {} and mounted in {}").format(
                        partition_recipe[partition]["fs"],
                        partition_recipe[partition]["mp"],
                    )
                )
            self.group_partitions.add(entry)

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__window.next()
        self.destroy()


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-disk.ui")
class VanillaDefaultDisk(Adw.Bin):
    __gtype_name__ = "VanillaDefaultDisk"

    btn_next = Gtk.Template.Child()
    btn_auto = Gtk.Template.Child()
    btn_manual = Gtk.Template.Child()
    group_disks = Gtk.Template.Child()
    disk_space_err_box = Gtk.Template.Child()
    disk_space_err_label = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__registry_disks = []
        self.__selected_disks = []
        self.__disks = DisksManager()
        self.__partition_recipe = None
        self.__selected_disks_sum = 0

        self.min_disk_size = self.__window.recipe.get("min_disk_size", 28680)
        self.disk_space_err_label.set_label(
            self.disk_space_err_label.get_label()
            % Diskutils.pretty_size(self.min_disk_size * 1_048_576)
        )

        # append the disks widgets
        for index, disk in enumerate(self.__disks.all_disks):
            entry = VanillaDefaultDiskEntry(self, disk)
            self.group_disks.add(entry)

            self.__registry_disks.append(entry)

        # signals
        self.btn_next.connect("clicked", self.__on_btn_next_clicked)
        self.btn_auto.connect("clicked", self.__on_auto_clicked)
        self.btn_manual.connect("clicked", self.__on_manual_clicked)

    def get_finals(self):
        return {"disk": self.__partition_recipe}

    def __on_modal_close_request(self, *args):
        self.btn_next.set_visible(self.__partition_recipe is not None)
        self.btn_next.set_sensitive(self.__partition_recipe is not None)

    def __on_auto_clicked(self, button):
        self.__partition_recipe = {
            "auto": {
                "disk": self.__selected_disks[0].disk,
                "pretty_size": self.__selected_disks[0].pretty_size,
                "size": self.__selected_disks[0].size,
            }
        }
        modal = VanillaDefaultDiskConfirmModal(
            self.__window, self.__partition_recipe)
        modal.present()

    def __on_manual_clicked(self, button):
        modal = VanillaDefaultDiskPartModal(
            self.__window, self, self.__selected_disks)
        modal.connect("partitioning-set", self.__on_modal_close_request)
        modal.present()

    def on_disk_entry_toggled(self, widget, disk):
        if widget.get_active():
            self.__selected_disks.append(disk)
            self.__selected_disks_sum += disk.size
        else:
            self.__selected_disks.remove(disk)
            self.__selected_disks_sum -= disk.size

        if (
            self.__selected_disks_sum / 1_048_576 < self.min_disk_size
            and self.__selected_disks_sum > 0
        ):
            self.disk_space_err_box.set_visible(True)
            self.btn_auto.set_sensitive(False)
            self.btn_manual.set_sensitive(False)
        else:
            self.disk_space_err_box.set_visible(False)
            self.btn_auto.set_sensitive(len(self.__selected_disks) == 1)
            self.btn_manual.set_sensitive(len(self.__selected_disks) > 0)

    def set_partition_recipe(self, recipe):
        self.__partition_recipe = recipe

    def __on_btn_next_clicked(self, button):
        modal = VanillaDefaultDiskConfirmModal(
            self.__window, self.__partition_recipe)
        modal.present()
