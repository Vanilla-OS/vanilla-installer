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
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.core.disks import DisksManager


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-disk.ui')
class VanillaDefaultDiskEntry(Adw.ActionRow):
    __gtype_name__ = 'VanillaDefaultDiskEntry'

    chk_button = Gtk.Template.Child()

    def __init__(self, disk, chk_group, use_radio, **kwargs):
        super().__init__(**kwargs)
        self.__disk = disk
        self.set_title(disk.name)
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

@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-partition.ui')
class VanillaDefaultPartitionEntry(Adw.ExpanderRow):
    __gtype_name__ = 'VanillaDefaultPartitionEntry'

    combo_fs = Gtk.Template.Child()
    str_list_fs = Gtk.Template.Child()
    combo_mp = Gtk.Template.Child()
    str_list_mp = Gtk.Template.Child()

    def __init__(self, partition, **kwargs):
        super().__init__(**kwargs)
        self.__partition = partition
        self.__name = partition.partition
        self.set_title(partition.partition)
        self.set_subtitle(partition.pretty_size)
    
    @property
    def selected_fs(self):
        index = self.combo_fs.get_selected()
        return self.str_list_fs.get_string(index)

    @property
    def selected_mountpoint(self):
        index = self.combo_mp.get_selected()
        return self.str_list_mp.get_string(index)

    @property
    def name(self):
        return self.__name


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/dialog-disk.ui')
class VanillaDefaultDiskPartModal(Adw.Window):
    __gtype_name__ = 'VanillaDefaultDiskPartModal'

    chk_entire_disk = Gtk.Template.Child()
    chk_manual_part = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()
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

        # signals
        self.chk_manual_part.connect('toggled', self.__on_chk_manual_part_toggled)
        self.btn_cancel.connect('clicked', self.__on_btn_cancel_clicked)
        self.btn_apply.connect('clicked', self.__on_btn_apply_clicked)
        self.launch_gparted.connect("clicked", self.__on_launch_gparted)

        for partition in self.__disk.partitions:
            entry = VanillaDefaultPartitionEntry(partition)
            self.group_partitions.add(entry)
            self.__registry_partitions.append(entry)

    def __on_chk_manual_part_toggled(self, widget):
        self.group_partitions.set_visible(widget.get_active())

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__parent.set_partition_recipe(self.partition_recipe)
        self.destroy()
    
    def __on_launch_gparted(self, widget):
        subprocess.run(['gparted'])

    @property
    def partition_recipe(self):
        recipe = {}
        if self.chk_entire_disk.get_active():
            return {"auto": self.__disk.name}
        
        for partition in self.__registry_partitions:
            recipe[partition.name] = {
                "fs": partition.selected_fs,
                "mp": partition.selected_mountpoint
            }
        return recipe


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
        self.btn_next.connect("clicked", self.__window.next)
        self.btn_configure.connect("clicked", self.__on_configure_clicked)

    def get_finals(self):
        return {}
    
    def __on_configure_clicked(self, button):
        for entry in self.__registry_disks:
            if not entry.is_active:
                continue

            modal = VanillaDefaultDiskPartModal(self.__window, self, entry.disk)
            modal.present()
            break

    def set_partition_recipe(self, recipe):
        self.__partition_recipe = recipe
