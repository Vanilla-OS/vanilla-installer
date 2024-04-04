# welcome.py
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

from gi.repository import Adw, Gtk

from vanilla_installer.windows.dialog_recovery import VanillaRecoveryDialog
from vanilla_installer.windows.dialog_poweroff import VanillaPoweroffDialog


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-welcome.ui")
class VanillaDefaultWelcome(Adw.Bin):
    __gtype_name__ = "VanillaDefaultWelcome"

    status_page = Gtk.Template.Child()
    row_install = Gtk.Template.Child()
    row_recovery = Gtk.Template.Child()
    row_poweroff = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        distro_name = self.__distro_info.get("name", "Vanilla OS")
        distro_logo = self.__distro_info.get("logo", "org.vanillaos.Installer-flower")

        self.status_page.set_icon_name(distro_logo)
        self.status_page.set_title(f"Welcome to {distro_name}!")

        # signals
        self.row_install.connect("activated", self.__window.next)
        self.row_recovery.connect("activated", self.__on_recovery_clicked)
        self.row_poweroff.connect("activated", self.__on_poweroff_clicked)

    def get_finals(self):
        return {}

    def __on_recovery_clicked(self, row):
        VanillaRecoveryDialog(self.__window).show()

    def __on_poweroff_clicked(self, row):
        VanillaPoweroffDialog(self.__window).show()
