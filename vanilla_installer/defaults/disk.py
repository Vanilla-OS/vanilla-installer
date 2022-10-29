# welcome.py
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
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/dialog-disk.ui')
class VanillaDefaultDiskPartModal(Adw.Window):
    __gtype_name__ = 'VanillaDefaultDiskPartModal'

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.set_transient_for(self.__window)


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-disk.ui')
class VanillaDefaultDisk(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultDisk'

    btn_next = Gtk.Template.Child()
    btn_configure = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.btn_configure.connect("clicked", self.__on_configure_clicked)

    def get_finals(self):
        return {}
    
    def __on_configure_clicked(self, button):
        modal = VanillaDefaultDiskPartModal(self.__window)
        modal.present()
