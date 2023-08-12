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

from gi.repository import Adw, Gtk

from vanilla_installer.windows.dialog_recovery import VanillaRecoveryDialog


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-welcome.ui")
class VanillaDefaultWelcome(Adw.Bin):
    __gtype_name__ = "VanillaDefaultWelcome"

    btn_recovery = Gtk.Template.Child()
    btn_install = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # signals
        self.btn_recovery.connect("clicked", self.__on_recovery_clicked)
        self.btn_install.connect("clicked", self.__window.next)

    def get_finals(self):
        return {}

    def __on_recovery_clicked(self, button):
        VanillaRecoveryDialog(self.__window).show()
