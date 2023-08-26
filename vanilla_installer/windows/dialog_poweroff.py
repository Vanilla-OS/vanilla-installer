# dialog_poweroff.py
#
# Copyright 2022 mirkobrombin
# Copyright 2022 muqtadir
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
from vanilla_installer.core.system import Systeminfo

from gi.repository import Adw, GLib, Gtk


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-poweroff.ui")
class VanillaPoweroffDialog(Adw.Window):
    __gtype_name__ = "VanillaPoweroffDialog"

    row_poweroff = Gtk.Template.Child()
    row_reboot = Gtk.Template.Child()
    row_firmware_setup = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)

        # signals
        self.row_poweroff.connect("activated", self.__on_poweroff)
        self.row_reboot.connect("activated", self.__on_reboot)
        self.row_firmware_setup.connect("activated", self.__on_firmware_setup)

        self.row_firmware_setup.set_visible(Systeminfo.is_uefi())

    def __on_poweroff(self, btn):
        subprocess.call(["systemctl", "poweroff"])

    def __on_reboot(self, btn):
        subprocess.call(["systemctl", "reboot"])

    def __on_firmware_setup(self, row):
        subprocess.call(["systemctl", "reboot", "--firmware-setup"])