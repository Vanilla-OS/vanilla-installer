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

from vanilla_installer.core.disks import DisksManager


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-disk.ui')
class VanillaDefaultDiskEntry(Adw.ActionRow):
    __gtype_name__ = 'VanillaDefaultDiskEntry'

    chk_button = Gtk.Template.Child()

    def __init__(self, disk, chk_group, use_radio, **kwargs):
        super().__init__(**kwargs)
        self.__disk = disk
        self.set_title(disk.name)

        if disk.size < 50000000000:
            self.set_sensitive(False)
            self.set_subtitle(_("Not enough space: {0}/{1}").format(disk.pretty_size, "50 GB"))
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
                self.chk_button.set_tooltip_text(_("This is the only disk available and cannot be deselected!"))

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


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-partition.ui')
class PartitionSelector(Gtk.Box):
    __gtype_name__ = 'PartitionSelector'

    boot_part_expand = Gtk.Template.Child()
    efi_part_expand = Gtk.Template.Child()
    abroot_a_part_expand = Gtk.Template.Child()
    abroot_b_part_expand = Gtk.Template.Child()
    home_part_expand = Gtk.Template.Child()
    # TODO: Add swap expander

    abroot_info_button = Gtk.Template.Child()
    abroot_info_popover = Gtk.Template.Child()

    # NOTE: Keys must be the same name as template children
    __selected_partitions = {
        "boot_part_expand": None,
        "efi_part_expand": None,
        "abroot_a_part_expand": None,
        "abroot_b_part_expand": None,
        "home_part_expand": None,
    }

    __partition_fs_types = [ "btrfs", "ext4", "ext3", "fat32", "xfs", "swap" ]

    def __init__(self, partitions, **kwargs):
        super().__init__(**kwargs)
        self.__partitions = sorted(partitions)
        self.abroot_info_button.connect("clicked", self.__on_info_button_clicked)

        for widget in self.__generate_partition_list_widgets():
            self.boot_part_expand.add_row(widget)

        for widget in self.__generate_partition_list_widgets():
            self.efi_part_expand.add_row(widget)

        for widget in self.__generate_partition_list_widgets():
            self.abroot_a_part_expand.add_row(widget)

        for widget in self.__generate_partition_list_widgets():
            self.abroot_b_part_expand.add_row(widget)

        for widget in self.__generate_partition_list_widgets():
            self.home_part_expand.add_row(widget)

    def __generate_partition_list_widgets(self):
        checkbuttons = []
        partition_widgets = []

        for i, partition in enumerate(self.__partitions):
            partition_row = Adw.ActionRow()
            partition_row.set_title(partition.partition)
            partition_row.set_subtitle(partition.pretty_size)

            fs_dropdown = Gtk.DropDown.new_from_strings(self.__partition_fs_types)
            fs_dropdown.set_valign(Gtk.Align.CENTER)
            fs_dropdown.set_sensitive(False)
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

    def __on_info_button_clicked(self, widget):
        self.abroot_info_popover.popup()

    def __update_partition_rows(self):
        for row in [self.boot_part_expand, self.efi_part_expand, self.abroot_a_part_expand, self.abroot_b_part_expand, self.home_part_expand]:
            children = row.get_child().observe_children()
            child_rows = children.get_item(children.get_n_items() - 1).get_child().observe_children()

            for i in range(child_rows.get_n_items()):
                child_row = child_rows.get_item(i);
                row_partition = child_row.get_title()
                is_used = False
                for _, val in self.__selected_partitions.items():
                    if val == row_partition:
                        is_used = True
                child_row.set_sensitive(not is_used)

    def __on_check_button_toggled(self, widget):
        action_row = widget.get_parent().get_parent().get_parent()
        children = action_row.get_child().observe_children()
        dropdown = children.get_item(children.get_n_items() - 1).observe_children().get_item(0)

        rows = action_row.get_parent().observe_children()
        for i in range(rows.get_n_items()):
            row = rows.get_item(i)
            row_children = row.get_child().observe_children()

            # Sets all dropdowns as not sensitive
            row_dropdown = row_children.get_item(row_children.get_n_items() - 1).observe_children().get_item(0)
            row_dropdown.set_sensitive(False)

        # Only the currently selected partition can be edited
        dropdown.set_sensitive(True)

        partition = action_row.get_title()
        size = action_row.get_subtitle()
        fs_type = self.__partition_fs_types[dropdown.get_selected()]

        expander_row = action_row.get_parent().get_parent().get_parent().get_parent()
        expander_row.set_title(partition)
        expander_row.set_subtitle(f"{size} ({fs_type})")
        self.__selected_partitions[expander_row.get_buildable_id()] = partition

        # Sets already selected partitions as not sensitive
        self.__update_partition_rows()

    def __on_dropdown_selected(self, widget, _):
        fs_type = self.__partition_fs_types[widget.get_selected()]

        action_row = widget.get_parent().get_parent().get_parent()
        expander_row = action_row.get_parent().get_parent().get_parent().get_parent()

        size = action_row.get_subtitle()
        expander_row.set_subtitle(f"{size} ({fs_type})")


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/dialog-disk.ui')
class VanillaDefaultDiskPartModal(Adw.Window):
    __gtype_name__ = 'VanillaDefaultDiskPartModal'
    __gsignals__ = {
        "partitioning-set": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    chk_entire_disk = Gtk.Template.Child()
    chk_manual_part = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()
    group_partitions_window = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()
    launch_gparted = Gtk.Template.Child()


    def __init__(self, window, parent, disk, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__parent = parent
        self.__disk = disk
        self.set_transient_for(self.__window)
        self.chk_entire_disk.set_group(self.chk_manual_part)
        self.__registry_partitions = []

        self.default_width, self.default_height = self.get_default_size()

        # signals
        self.chk_manual_part.connect('toggled', self.__on_chk_manual_part_toggled)
        self.chk_entire_disk.connect('toggled', self.__on_chk_entire_disk_toggled)
        self.btn_cancel.connect('clicked', self.__on_btn_cancel_clicked)
        self.btn_apply.connect('clicked', self.__on_btn_apply_clicked)
        self.launch_gparted.connect("clicked", self.__on_launch_gparted)

        entry = PartitionSelector(self.__disk.partitions)
        self.group_partitions.set_child(entry)

    def __on_chk_manual_part_toggled(self, widget):
        self.group_partitions_window.set_visible(widget.get_active())
        self.set_default_size(self.default_width, 700);

    def __on_chk_entire_disk_toggled(self, widget):
        self.set_default_size(self.default_width, self.default_height);

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__parent.set_partition_recipe(self.partition_recipe)
        self.emit("partitioning-set", self.__disk.name)
        self.destroy()

    def __on_launch_gparted(self, widget):
        subprocess.run(['gparted'])

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
        for partition in self.__registry_partitions:
            if partition.selected_fs == _("Do not touch"):
                continue
            recipe[partition.name] = {
                "fs": partition.selected_fs,
                "mp": partition.selected_mountpoint,
                "pretty_size": partition.pretty_size,
                "size": partition.pretty_size,
            }
        return recipe


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/dialog-disk-confirm.ui')
class VanillaDefaultDiskConfirmModal(Adw.Window):
    __gtype_name__ = 'VanillaDefaultDiskConfirmModal'

    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()

    def __init__(self, window, partition_recipe, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.set_transient_for(self.__window)

        # signals
        self.btn_cancel.connect('clicked', self.__on_btn_cancel_clicked)
        self.btn_apply.connect('clicked', self.__on_btn_apply_clicked)

        for partition, values in partition_recipe.items():
            entry = Adw.ActionRow()
            if partition == "auto":
                entry.set_title(partition_recipe[partition]["disk"])
                entry.set_subtitle(_("Entire disk will be used."))
            else:
                if partition == "disk":
                    continue
                entry.set_title(partition)
                entry.set_subtitle(_("Will be formatted in {} and mounted in {}").format(
                    partition_recipe[partition]["fs"],
                    partition_recipe[partition]["mp"],
                ))
            self.group_partitions.add(entry)

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__window.next()
        self.destroy()


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-disk.ui')
class VanillaDefaultDisk(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultDisk'

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

            modal = VanillaDefaultDiskPartModal(self.__window, self, entry.disk)
            modal.connect('partitioning-set', on_modal_close_request)
            modal.present()
            break

    def set_partition_recipe(self, recipe):
        self.__partition_recipe = recipe

    def __on_btn_next_clicked(self, button):
        modal = VanillaDefaultDiskConfirmModal(self.__window, self.__partition_recipe)
        modal.present()
# disk.py
