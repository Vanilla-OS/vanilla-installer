# yes_no.py
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

from gi.repository import Adw, Gtk

from vanilla_installer.windows.dialog import VanillaDialog


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/layout-yes-no.ui")
class VanillaLayoutYesNo(Adw.Bin):
    __gtype_name__ = "VanillaLayoutYesNo"

    status_page = Gtk.Template.Child()
    btn_no = Gtk.Template.Child()
    btn_yes = Gtk.Template.Child()
    btn_info = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__response = False
        self.__build_ui()

        # signals
        self.btn_yes.connect("clicked", self.__on_response, True)
        self.btn_no.connect("clicked", self.__on_response, False)
        self.btn_info.connect("clicked", self.__on_info)

    def __build_ui(self):
        self.status_page.set_icon_name(self.__step["icon"])
        self.status_page.set_title(self.__step["title"])
        self.status_page.set_description(self.__step["description"])

        self.btn_yes.set_label(self.__step["buttons"]["yes"])
        self.btn_no.set_label(self.__step["buttons"]["no"])

        if "info" in self.__step["buttons"]:
            self.btn_info.set_visible(True)

    def __on_response(self, _, response):
        self.__response = response
        self.__window.next()

    def __on_info(self, _):
        if "info" not in self.__step["buttons"]:
            return

        dialog = VanillaDialog(
            self.__window,
            self.__step["buttons"]["info"]["title"],
            self.__step["buttons"]["info"]["text"],
        )
        dialog.show()

    def get_finals(self):
        return {
            "vars": {self.__key: self.__response},
            "funcs": [x for x in self.__step["final"]],
        }
