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

import sys
import time
import subprocess
from gi.repository import Gtk, Gio, GLib, GObject, Adw
from typing import Union

from vanilla_installer.core.disks import DisksManager, Partition


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-disk.ui")
class VanillaDefaultDiskEntry(Adw.ActionRow):
    __gtype_name__ = "VanillaDefaultDiskEntry"

    chk_button = Gtk.Template.Child()

    def __init__(self, disk, chk_group, use_radio, **kwargs):
        super().__init__(**kwargs)
        self.__disk = disk
        self.set_title(disk.name)

        if disk.size < 50000000000:
            self.set_sensitive(False)
            self.set_subtitle(
                _("Not enough space: {0}/{1}").format(disk.pretty_size, "50 GB")
            )
        else:
            self.set_subtitle(disk.pretty_size)
            self.chk_button.set_group(chk_group)

            if not use_radio:
                # since there is only one disk and for some reason GtkCheckButton
                # only works as a GtkRadioButton only when there are more than one
                # we create a fake GtkRadioButton to check the first one
                fake_chk_button = Gtk.CheckButton()
                fake_chk_button.set_group(self.chk_button)
                self.chk_button.set_active(True)
                self.chk_button.set_sensitive(False)
                self.chk_button.set_tooltip_text(
                    _("This is the only disk available and cannot be deselected!")
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


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-partition.ui")
class PartitionSelector(Adw.PreferencesPage):
    __gtype_name__ = "PartitionSelector"

    boot_part_expand = Gtk.Template.Child()
    efi_part_expand = Gtk.Template.Child()
    abroot_a_part_expand = Gtk.Template.Child()
    abroot_b_part_expand = Gtk.Template.Child()
    home_part_expand = Gtk.Template.Child()
    swap_part_expand = Gtk.Template.Child()

    abroot_info_button = Gtk.Template.Child()
    abroot_info_popover = Gtk.Template.Child()
    use_swap_part = Gtk.Template.Child()
    root_sizes_differ_error = Gtk.Template.Child()

    # NOTE: Keys must be the same name as template children
    __selected_partitions: dict[str, dict[str, Union[Partition, str, None]]] = {
        "boot_part_expand": {
            "mountpoint": "/boot",
            "partition": None,
            "fstype": None,
        },
        "efi_part_expand": {
            "mountpoint": "/boot/efi",
            "partition": None,
            "fstype": None,
        },
        "abroot_a_part_expand": {
            "mountpoint": "/",
            "partition": None,
            "fstype": None,
        },
        "abroot_b_part_expand": {
            "mountpoint": "/",
            "partition": None,
            "fstype": None,
        },
        "home_part_expand": {
            "mountpoint": "/home",
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

    __partition_fs_types = ["btrfs", "ext4", "ext3", "fat32", "xfs"]

    def __init__(self, parent, partitions, **kwargs):
        super().__init__(**kwargs)
        self.__parent = parent
        self.__partitions = sorted(partitions)
        self.abroot_info_button.connect("clicked", self.__on_info_button_clicked)
        self.use_swap_part.connect("state-set", self.__on_use_swap_toggled)

        for widget in self.__generate_partition_list_widgets("fat32"):
            self.boot_part_expand.add_row(widget)
            self.__selected_partitions["boot_part_expand"]["fstype"] = "fat32"

        for widget in self.__generate_partition_list_widgets("fat32"):
            self.efi_part_expand.add_row(widget)
            self.__selected_partitions["efi_part_expand"]["fstype"] = "fat32"

        for widget in self.__generate_partition_list_widgets():
            self.abroot_a_part_expand.add_row(widget)
            self.__selected_partitions["abroot_a_part_expand"]["fstype"] = "btrfs"

        for widget in self.__generate_partition_list_widgets():
            self.abroot_b_part_expand.add_row(widget)
            self.__selected_partitions["abroot_b_part_expand"]["fstype"] = "btrfs"

        for widget in self.__generate_partition_list_widgets():
            self.home_part_expand.add_row(widget)
            self.__selected_partitions["home_part_expand"]["fstype"] = "btrfs"

        for widget in self.__generate_partition_list_widgets("swap"):
            self.swap_part_expand.add_row(widget)
            self.__selected_partitions["swap_part_expand"]["fstype"] = "swap"

    def __generate_partition_list_widgets(self, default_fs="btrfs"):
        checkbuttons = []
        partition_widgets = []

        for i, partition in enumerate(self.__partitions):
            partition_row = Adw.ActionRow()
            partition_row.set_title(partition.partition)
            partition_row.set_subtitle(partition.pretty_size)

            # Swap is always swap
            if default_fs != "swap":
                fs_dropdown = Gtk.DropDown.new_from_strings(self.__partition_fs_types)
                fs_dropdown.set_valign(Gtk.Align.CENTER)
                fs_dropdown.set_sensitive(False)
                fs_dropdown.set_selected(self.__partition_fs_types.index(default_fs))
                fs_dropdown.connect("notify::selected", self.__on_dropdown_selected)
                partition_row.add_suffix(fs_dropdown)

            select_button = Gtk.CheckButton()
            if i != 0:
                select_button.set_group(checkbuttons[0])

            select_button.connect("toggled", self.__on_check_button_toggled)
            checkbuttons.append(select_button)
            partition_row.add_prefix(checkbuttons[i])

            partition_widgets.append(partition_row)

        return partition_widgets

    def __partition_idx(self, partition):
        for part in self.__partitions:
            if part.partition == partition:
                return part

    def __on_info_button_clicked(self, widget):
        self.abroot_info_popover.popup()

    def __update_apply_button_status(self):
        # If not manual partitioning, it's always valid
        if self.__parent.chk_entire_disk.get_active():
            self.__parent.set_btn_apply_sensitive(True)
            return

        for k, val in self.__selected_partitions.items():
            if val["partition"] == None and (
                k != "swap_part_expand" or self.use_swap_part.get_active()
            ):
                self.__parent.set_btn_apply_sensitive(False)
                return

        if self.__valid_root_partitions:
            self.__parent.set_btn_apply_sensitive(True)

    def __check_root_partitions_size_equal(self):
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

    def __on_use_swap_toggled(self, widget, state):
        if state == False:
            children = self.swap_part_expand.get_child().observe_children()
            child_rows = (
                children.get_item(children.get_n_items() - 1)
                .get_child()
                .observe_children()
            )

            for i in range(child_rows.get_n_items()):
                child_row = child_rows.get_item(i)
                row_checkbutton = (
                    child_row.observe_children()
                    .get_item(0)
                    .observe_children()
                    .get_item(0)
                    .observe_children()
                    .get_item(0)
                )
                row_checkbutton.set_active(False)

            self.__selected_partitions["swap_part_expand"]["partition"] = None
            self.swap_part_expand.set_title(_("No partition selected"))
            self.swap_part_expand.set_subtitle(
                _("Please select a partition from the options below")
            )
            self.__update_partition_rows()

        self.__update_apply_button_status()

    def __update_partition_rows(self):
        for row in [
            self.boot_part_expand,
            self.efi_part_expand,
            self.abroot_a_part_expand,
            self.abroot_b_part_expand,
            self.home_part_expand,
            self.swap_part_expand,
        ]:
            children = row.get_child().observe_children()
            child_rows = (
                children.get_item(children.get_n_items() - 1)
                .get_child()
                .observe_children()
            )

            for i in range(child_rows.get_n_items()):
                child_row = child_rows.get_item(i)
                row_partition = child_row.get_title()
                row_checkbutton = (
                    child_row.observe_children()
                    .get_item(0)
                    .observe_children()
                    .get_item(0)
                    .observe_children()
                    .get_item(0)
                )

                # The row where partition was selected still has to be sensitive
                if row_checkbutton.get_active():
                    child_row.set_sensitive(True)
                    continue

                is_used = False
                for _, val in self.__selected_partitions.items():
                    if (
                        val["partition"] is not None
                        and val["partition"].partition == row_partition
                    ):
                        is_used = True
                child_row.set_sensitive(not is_used)

    def __on_check_button_toggled(self, widget):
        action_row = widget.get_parent().get_parent().get_parent()
        children = action_row.get_child().observe_children()
        dropdown = (
            children.get_item(children.get_n_items() - 1).observe_children().get_item(0)
        )

        rows = action_row.get_parent().observe_children()
        for i in range(rows.get_n_items()):
            row = rows.get_item(i)
            row_children = row.get_child().observe_children()

            # Sets all dropdowns as not sensitive
            row_dropdown = (
                row_children.get_item(row_children.get_n_items() - 1)
                .observe_children()
                .get_item(0)
            )
            if row_dropdown:
                row_dropdown.set_sensitive(False)

        # Only the currently selected partition can be edited
        partition = action_row.get_title()
        size = action_row.get_subtitle()
        expander_row = action_row.get_parent().get_parent().get_parent().get_parent()

        expander_row.set_title(partition)

        if dropdown:
            dropdown.set_sensitive(True)
            fs_type = self.__partition_fs_types[dropdown.get_selected()]
            expander_row.set_subtitle(f"{size} ({fs_type})")
        else:
            expander_row.set_subtitle(f"{size}")

        self.__selected_partitions[expander_row.get_buildable_id()][
            "partition"
        ] = self.__partition_idx(partition)

        # Sets already selected partitions as not sensitive
        self.__update_partition_rows()
        # Checks whether we can proceed with installation
        self.__update_apply_button_status()
        # Checks whether root partitions are the same size
        self.__check_root_partitions_size_equal()

    def __on_dropdown_selected(self, widget, _):
        fs_type = self.__partition_fs_types[widget.get_selected()]

        action_row = widget.get_parent().get_parent().get_parent()
        expander_row = action_row.get_parent().get_parent().get_parent().get_parent()
        self.__selected_partitions[expander_row.get_buildable_id()]["fstype"] = fs_type

        size = action_row.get_subtitle()
        expander_row.set_subtitle(f"{size} ({fs_type})")

    @property
    def selected_partitions(self):
        return self.__selected_partitions


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-disk.ui")
class VanillaDefaultDiskPartModal(Adw.Window):
    __gtype_name__ = "VanillaDefaultDiskPartModal"
    __gsignals__ = {
        "partitioning-set": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    chk_entire_disk = Gtk.Template.Child()
    chk_manual_part = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()
    launch_gparted = Gtk.Template.Child()
    manual_part_expand = Gtk.Template.Child()

    def __init__(self, window, parent, disk, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__parent = parent
        self.__disk = disk
        self.set_transient_for(self.__window)
        self.chk_entire_disk.set_group(self.chk_manual_part)

        self.default_width, self.default_height = self.get_default_size()

        # signals
        self.chk_manual_part.connect("toggled", self.__on_chk_manual_part_toggled)
        self.chk_entire_disk.connect("toggled", self.__on_chk_entire_disk_toggled)
        self.btn_cancel.connect("clicked", self.__on_btn_cancel_clicked)
        self.btn_apply.connect("clicked", self.__on_btn_apply_clicked)
        self.launch_gparted.connect("clicked", self.__on_launch_gparted)

        self.__partition_selector = PartitionSelector(self, self.__disk.partitions)
        self.group_partitions.set_child(self.__partition_selector)

    def __on_chk_manual_part_toggled(self, widget):
        self.group_partitions.set_visible(widget.get_active())
        self.set_default_size(self.default_width, 800)
        self.manual_part_expand.set_expanded(widget.get_active())
        self.set_btn_apply_sensitive(False)

    def __on_chk_entire_disk_toggled(self, widget):
        self.set_btn_apply_sensitive(True)
        self.set_default_size(self.default_width, self.default_height)

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__parent.set_partition_recipe(self.partition_recipe)
        self.emit("partitioning-set", self.__disk.name)
        self.destroy()

    def __on_launch_gparted(self, widget):
        subprocess.Popen(["gparted"])

    def set_btn_apply_sensitive(self, val):
        self.btn_apply.set_sensitive(val)

    @property
    def partition_recipe(self):
        recipe = {}
        if self.chk_entire_disk.get_active():
            return {
                "auto": {
                    "disk": self.__disk.disk,
                    "pretty_size": self.__disk.pretty_size,
                    "size": self.__disk.size,
                }
            }

        recipe["disk"] = self.__disk.disk
        for _, info in self.__partition_selector.selected_partitions.items():
            if not isinstance(
                info["partition"], Partition
            ):  # Partition can be None if user didn't configure swap
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
    btn_configure = Gtk.Template.Child()
    group_disks = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__registry_disks = []
        self.__disks = DisksManager()
        self.__partition_recipe = None

        # append the disks widgets
        chk_group = None
        count_disks = len(self.__disks.all_disks)
        for index, disk in enumerate(self.__disks.all_disks):
            entry = VanillaDefaultDiskEntry(disk, chk_group, use_radio=count_disks > 1)
            self.group_disks.add(entry)

            if index == 0:
                chk_group = entry.chk_button

            self.__registry_disks.append(entry)

        # signals
        self.btn_next.connect("clicked", self.__on_btn_next_clicked)
        self.btn_configure.connect("clicked", self.__on_configure_clicked)

    def get_finals(self):
        return {"disk": self.__partition_recipe}

    def __on_configure_clicked(self, button):
        def on_modal_close_request(*args):
            self.btn_next.set_visible(self.__partition_recipe is not None)
            self.btn_next.set_sensitive(self.__partition_recipe is not None)

        for entry in self.__registry_disks:
            if not entry.is_active:
                continue

            entry.disk.update_partitions()

            modal = VanillaDefaultDiskPartModal(self.__window, self, entry.disk)
            modal.connect("partitioning-set", on_modal_close_request)
            modal.present()
            break

    def set_partition_recipe(self, recipe):
        self.__partition_recipe = recipe

    def __on_btn_next_clicked(self, button):
        modal = VanillaDefaultDiskConfirmModal(self.__window, self.__partition_recipe)
        modal.present()
