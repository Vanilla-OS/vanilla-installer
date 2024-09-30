# disk.py
#
# Copyright 2024 mirkobrombin
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

        selected_fs = self.__default_fs

        fs_dropdown.set_selected(self.__partition_fs_types.index(selected_fs))
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
            self.__parent.set_subtitle(f"{self.__partition.pretty_size} ({fs_type})")
        else:
            self.__parent.set_subtitle(f"{self.__partition.pretty_size}")

        self.__parent.set_title(self.__partition.partition)
        self.__page.selected_partitions[self.__parent.get_buildable_id()][
            "partition"
        ] = self.__partition

        # Sets already selected partitions as not sensitive
        self.__page.update_partition_rows()
        # Checks whether selected partitions are big enough
        self.__page.check_selected_partitions_sizes()
        # Checks whether we can proceed with installation
        self.__page.update_apply_button_status()

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
    root_part = Gtk.Template.Child()
    var_part = Gtk.Template.Child()
    swap_part = Gtk.Template.Child()

    boot_part_expand = Gtk.Template.Child()
    efi_part_expand = Gtk.Template.Child()
    bios_part_expand = Gtk.Template.Child()
    root_part_expand = Gtk.Template.Child()
    var_part_expand = Gtk.Template.Child()
    swap_part_expand = Gtk.Template.Child()

    use_swap_part = Gtk.Template.Child()
    keep_efi_part = Gtk.Template.Child()

    boot_small_error = Gtk.Template.Child()
    efi_small_error = Gtk.Template.Child()
    bios_small_error = Gtk.Template.Child()
    root_small_error = Gtk.Template.Child()
    var_small_error = Gtk.Template.Child()

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
        "root_part_expand": {
            "mountpoint": "/",
            "min_size": 22_011_707_392,  # 20.5 GB
            "partition": None,
            "fstype": None,
        },
        "var_part_expand": {
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
    __valid_partition_sizes = False

    def __init__(self, parent, partitions, **kwargs):
        super().__init__(**kwargs)
        self.__parent = parent
        self.__partitions = sorted(partitions)
        self.__recipe = self.__parent.recipe

        self.launch_gparted.connect("clicked", self.__on_launch_gparted)
        self.use_swap_part.connect("state-set", self.__on_use_swap_toggled)
        self.keep_efi_part.connect("state-set", self.__on_keep_efi_toggled)

        self.__boot_part_rows = self.__generate_partition_list_widgets(
            self.boot_part_expand, "ext4", False
        )
        for i, widget in enumerate(self.__boot_part_rows):
            self.boot_part_expand.add_row(widget)
            widget.add_siblings(
                self.__boot_part_rows[:i] + self.__boot_part_rows[i + 1 :]
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
                    self.__efi_part_rows[:i] + self.__efi_part_rows[i + 1 :]
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
                    self.__bios_part_rows[:i] + self.__bios_part_rows[i + 1 :]
                )
                self.__selected_partitions["bios_part_expand"]["fstype"] = "ext4"

            # Remove EFI rows
            self.efi_part.set_visible(False)
            if "efi_part_expand" in self.__selected_partitions:
                del self.__selected_partitions["efi_part_expand"]

        self.__root_part_rows = self.__generate_partition_list_widgets(
            self.root_part_expand, "btrfs", False
        )
        for i, widget in enumerate(self.__root_part_rows):
            self.root_part_expand.add_row(widget)
            widget.add_siblings(
                self.__root_part_rows[:i] + self.__root_part_rows[i + 1 :]
            )
            self.__selected_partitions["root_part_expand"]["fstype"] = "btrfs"

        self.__var_part_rows = self.__generate_partition_list_widgets(
            self.var_part_expand
        )
        for i, widget in enumerate(self.__var_part_rows):
            self.var_part_expand.add_row(widget)
            widget.add_siblings(
                self.__var_part_rows[:i] + self.__var_part_rows[i + 1 :]
            )
            self.__selected_partitions["var_part_expand"]["fstype"] = "btrfs"

        self.__swap_part_rows = self.__generate_partition_list_widgets(
            self.swap_part_expand, "swap", False
        )
        for i, widget in enumerate(self.__swap_part_rows):
            self.swap_part_expand.add_row(widget)
            widget.add_siblings(
                self.__swap_part_rows[:i] + self.__swap_part_rows[i + 1 :]
            )
            self.__selected_partitions["swap_part_expand"]["fstype"] = "swap"

        for widget in [self.boot_part, self.efi_part, self.root_part, self.var_part]:
            widget.set_description(widget.get_description() + self.get_partition_size_string(widget) + ".")
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

    def update_apply_button_status(self):
        for k, val in self.__selected_partitions.items():
            if val["partition"] is None and (
                k != "swap_part_expand" or self.use_swap_part.get_active()
            ):
                self.__parent.set_btn_apply_sensitive(False)
                return

        if self.__valid_partition_sizes:
            self.__parent.set_btn_apply_sensitive(True)

    def check_selected_partitions_sizes(self):
        # Clear any existing errors
        self.__valid_partition_sizes = True
        self.boot_small_error.set_visible(False)
        if Systeminfo.is_uefi():
            self.efi_small_error.set_visible(False)
        else:
            self.bios_small_error.set_visible(False)
        self.root_small_error.set_visible(False)
        self.var_small_error.set_visible(False)
        if self.boot_part_expand.get_style_context().has_class("error"):
            self.boot_part_expand.get_style_context().remove_class("error")
        if Systeminfo.is_uefi():
            if self.efi_part_expand.get_style_context().has_class("error"):
                self.efi_part_expand.get_style_context().remove_class("error")
        else:
            if self.bios_part_expand.get_style_context().has_class("error"):
                self.bios_part_expand.get_style_context().remove_class("error")
        if self.root_part_expand.get_style_context().has_class("error"):
            self.root_part_expand.get_style_context().remove_class("error")
        if self.var_part_expand.get_style_context().has_class("error"):
            self.var_part_expand.get_style_context().remove_class("error")

        for partition, info in self.__selected_partitions.items():
            if "min_size" in info and info["partition"] is not None:
                if info["min_size"] > info["partition"].size:
                    self.__valid_partition_sizes = False
                    error_description = _("Partition must be at least {}").format(
                        Diskutils.pretty_size(info["min_size"])
                    )
                    if partition == "boot_part_expand":
                        self.boot_part_expand.get_style_context().add_class("error")
                        self.boot_small_error.set_description(error_description)
                        self.boot_small_error.set_visible(True)
                    elif partition == "efi_part_expand":
                        self.efi_part_expand.get_style_context().add_class("error")
                        self.efi_small_error.set_description(error_description)
                        self.efi_small_error.set_visible(True)
                    elif partition == "root_part_expand":
                        self.root_part_expand.get_style_context().add_class("error")
                        self.root_small_error.set_description(error_description)
                        self.root_small_error.set_visible(True)
                    elif partition == "var_part_expand":
                        self.var_part_expand.get_style_context().add_class("error")
                        self.var_small_error.set_description(error_description)
                        self.var_small_error.set_visible(True)

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

    def get_partition_size_string(self, widget):
        size = 0
        if widget == self.boot_part:
            size = self.__recipe["min_partition_sizes"]["/boot"]
        if widget == self.efi_part:
            size = self.__recipe["min_partition_sizes"]["/boot/efi"]
        if widget == self.root_part:
            size = self.__recipe["min_partition_sizes"]["/"]
        if widget == self.var_part:
            size = self.__recipe["min_partition_sizes"]["/var"]
        if size > 1024:
            return str(int(size/1024)) + "GiB"
        else:
            return str(size) + "MiB"


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

    def __on_keep_efi_toggled(self, widget, state):
        if state:
            self.__selected_partitions["efi_part_expand"]["fstype"] = "unformatted"
        else:
            self.__selected_partitions["efi_part_expand"]["fstype"] = "fat32"

    def update_partition_rows(self):
        rows = [
            self.__boot_part_rows,
            self.__root_part_rows,
            self.__var_part_rows,
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
        self.recipe = window.recipe

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
                self.__partition_selector = PartitionSelector(self, self.__partitions)
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

        pv_list = Diskutils.fetch_lvm_pvs()

        for __, info in self.__partition_selector.selected_partitions.items():
            # Partition can be None if user didn't configure swap
            if not isinstance(info["partition"], Partition):
                continue

            pv_to_remove = None
            vg_to_remove = None
            for pv, vg in pv_list:
                if pv == info["partition"].partition:
                    pv_to_remove = pv
                    vg_to_remove = vg

            recipe[info["partition"].partition] = {
                "fs": info["fstype"],
                "mp": info["mountpoint"],
                "pretty_size": info["partition"].pretty_size,
                "size": info["partition"].size,
                "existing_pv": pv_to_remove,
                "existing_vg": vg_to_remove
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
                if partition == "disk":
                    continue
                entry.set_title(partition)
                if partition_recipe[partition]["fs"] == "unformatted":
                    entry.set_subtitle(
                        _("Will be mounted in {}").format(
                            partition_recipe[partition]["mp"],
                        )
                    )
                else:
                    entry.set_subtitle(
                        _("Will be formatted in {} and mounted in {}").format(
                            partition_recipe[partition]["fs"],
                            partition_recipe[partition]["mp"],
                        )
                    )
            self.group_partitions.add(entry)

        if "auto" in partition_recipe:
            for vg in partition_recipe["auto"]["vgs_to_remove"]:
                entry = Adw.ActionRow()
                entry.set_title("LVM volume group: " + vg)
                entry.set_subtitle(_("Volume group will be removed."))
                self.group_partitions.add(entry)
            for pv in partition_recipe["auto"]["pvs_to_remove"]:
                entry = Adw.ActionRow()
                entry.set_title("LVM physical volume: " + pv)
                entry.set_subtitle(_("Physical volume will be removed."))
                self.group_partitions.add(entry)
        else:
            vgs_to_remove = []
            for partition, values in partition_recipe.items():
                if partition == "disk":
                    continue
                pv = values["existing_pv"]
                vg = values["existing_vg"]
                if pv is None:
                    continue
                if vg is not None and vg not in vgs_to_remove:
                    vgs_to_remove.append(values["existing_vg"])
                entry = Adw.ActionRow()
                entry.set_title("LVM physical volume: " + pv)
                entry.set_subtitle(_("Physical volume will be removed."))
                self.group_partitions.add(entry)
            for vg in vgs_to_remove:
                entry = Adw.ActionRow()
                entry.set_title("LVM volume group: " + vg)
                entry.set_subtitle(_("Volume group will be removed."))
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
        self.delta = False
        self.__registry_disks = []
        self.__selected_disks = []
        self.__disks = DisksManager()
        self.__partition_recipe = None
        self.__selected_disks_sum = 0

        self.min_disk_size = self.__window.recipe.get("min_disk_size", 51200)
        self.disk_space_err_label.set_label(
            self.disk_space_err_label.get_label()
            % Diskutils.pretty_size(self.min_disk_size * 1_048_576)
        )

        # append the disks widgets
        for disk in self.__disks.all_disks:
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
        pvs_to_remove = []
        vgs_to_remove = []
        for pv, vg in Diskutils.fetch_lvm_pvs():
            pv_disk, _ = Diskutils.separate_device_and_partn(pv)
            if pv_disk != self.__selected_disks[0].disk:
                continue
            pvs_to_remove.append(pv)
            if vg is not None and vg not in vgs_to_remove:
                vgs_to_remove.append(vg)

        self.__partition_recipe = {
            "auto": {
                "disk": self.__selected_disks[0].disk,
                "pretty_size": self.__selected_disks[0].pretty_size,
                "size": self.__selected_disks[0].size,
                "vgs_to_remove": vgs_to_remove,
                "pvs_to_remove": pvs_to_remove,
            }
        }
        modal = VanillaDefaultDiskConfirmModal(self.__window, self.__partition_recipe)
        modal.present()

    def __on_manual_clicked(self, button):
        modal = VanillaDefaultDiskPartModal(self.__window, self, self.__selected_disks)
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
        modal = VanillaDefaultDiskConfirmModal(self.__window, self.__partition_recipe)
        modal.present()
