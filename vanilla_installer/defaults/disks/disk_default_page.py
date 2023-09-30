# disk-default-page.py
#
# Copyright 2023 mirkobrombin
# Copyright 2023 matbme
# Copyright 2023 muqtadir
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

from gi.repository import Adw, Gtk

from vanilla_installer.core.disks import DisksManager
from vanilla_installer.defaults.disks.disk_widgets import DiskToggleButton, DialogDiskConfirm

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/disks/default-page.ui")
class DiskDefaultPage(Adw.Bin):
    __gtype_name__ = "DiskDefaultPage"

    all_disks_box = Gtk.Template.Child()
    disk_page = Gtk.Template.Child()
    disk_clamp = Gtk.Template.Child()
    selected_disk = {"auto": {"disk": None, "pretty_size": None, "size": None,}}

    def __init__(self, window, parent,**kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__parent = parent
        self.__registry_disks = []
        self.__disks = DisksManager()

        self.__parent.btn_next.connect("clicked", self.__on_auto_clicked)
        self.disk_page.set_description(f"Select the disk where you want to install {self.__window.recipe.get('distro_name', 'Vanilla OS')}")

        # append the disks widgets
        for index, disk in enumerate(self.__disks.all_disks):
            disk_box = DiskToggleButton(self.__window, self, self.__parent, disk)
            
            if len(self.__registry_disks) > 0:
                disk_box.set_group(self.__registry_disks[0])
                self.disk_clamp.set_maximum_size(600)
            self.all_disks_box.append(disk_box)
            self.__registry_disks.append(disk_box)

    def __on_auto_clicked(self, btn):
        modal = DialogDiskConfirm(self.__window, self.selected_disk)
        modal.present()

    def get_finals(self):
        return {"disk": self.selected_disk}