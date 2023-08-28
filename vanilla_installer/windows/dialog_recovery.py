# dialog_recovery.py
#
# Copyright 2023 mirkobrombin
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

import webbrowser
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-recovery.ui")
class VanillaRecoveryDialog(Adw.Window):
    __gtype_name__ = "VanillaRecoveryDialog"

    row_console = Gtk.Template.Child()
    row_gparted = Gtk.Template.Child()
    row_handbook = Gtk.Template.Child()
    row_web = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)

        # signals
        self.row_console.connect("activated", self.__on_console_activated)
        self.row_gparted.connect("activated", self.__on_gparted_activated)
        self.row_handbook.connect("activated", self.__on_handbook_activated)
        self.row_web.connect("activated", self.__on_web_activated)

    def __on_console_activated(self, row):
        GLib.spawn_command_line_async("kgx")

    def __on_gparted_activated(self, row):
        try:
            GLib.spawn_command_line_async("gparted")
        except:
            GLib.spawn_command_line_async("/usr/sbin/gparted")

    def __on_handbook_activated(self, row):
        webbrowser.open("https://handbook.vanillaos.org")

    def __on_web_activated(self, row):
        webbrowser.open("https://vanillaos.org")
