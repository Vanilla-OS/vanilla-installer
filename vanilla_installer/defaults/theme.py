# theme.py
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

from gi.repository import Gio, Gtk


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-theme.ui")
class VanillaDefaultTheme(Gtk.Box):
    __gtype_name__ = "VanillaDefaultTheme"

    btn_next = Gtk.Template.Child()
    btn_default = Gtk.Template.Child()
    btn_dark = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        self.__build_ui()

        self.btn_next.connect("clicked", self.__window.next)
        self.btn_default.connect("toggled", self.__set_theme, "light")
        self.btn_dark.connect("toggled", self.__set_theme, "dark")

    def __build_ui(self):
        self.btn_dark.set_group(self.btn_default)

    def __set_theme(self, widget, theme: str):
        pref = "prefer-dark" if theme == "dark" else "default"
        gtk = "Adwaita-dark" if theme == "dark" else "Adwaita"
        Gio.Settings.new("org.gnome.desktop.interface").set_string(
            "color-scheme", pref)
        Gio.Settings.new("org.gnome.desktop.interface").set_string(
            "gtk-theme", gtk)

    def get_finals(self):
        return {}
