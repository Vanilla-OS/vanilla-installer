# preferences.py
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

from gettext import gettext as _

from gi.repository import Adw, Gtk

from vanilla_installer.windows.dialog import VanillaDialog


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/layout-preferences.ui")
class VanillaLayoutPreferences(Adw.Bin):
    __gtype_name__ = "VanillaLayoutPreferences"

    status_page = Gtk.Template.Child()
    prefs_list = Gtk.Template.Child()
    btn_next = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__register_widgets = []
        self.__build_ui()

        # signals
        self.btn_next.connect("clicked", self.__next_step)

    def __build_ui(self):
        self.status_page.set_icon_name(self.__step["icon"])
        self.status_page.set_title(self.__step["title"])
        self.status_page.set_description(self.__step["description"])

        for item in self.__step["preferences"]:
            _action_row = Adw.ActionRow(
                title=item["title"], subtitle=item.get("subtitle", "")
            )
            _switcher = Gtk.Switch()
            _switcher.set_active(item.get("default", False))
            _switcher.set_valign(Gtk.Align.CENTER)
            _action_row.add_suffix(_switcher)

            self.prefs_list.add(_action_row)

            self.__register_widgets.append((item["id"], _switcher))

    def __next_step(self, widget):
        ws = self.__step.get("without_selection", {})

        if not any([x[1].get_active() for x in self.__register_widgets]):
            if not ws.get("allowed", True):
                self.__window.toast(_("Please select at least one option."))
                return

            if ws.get("message", None):
                dialog = VanillaDialog(
                    ws.get("title", "No selection"),
                    ws.get("message"),
                )
                dialog.present(self.__window)
        self.__window.next()

    def get_finals(self):
        ws = self.__step.get("without_selection", {})
        finals = {"vars": {}, "funcs": [x for x in self.__step["final"]]}

        for _id, switcher in self.__register_widgets:
            finals["vars"][_id] = switcher.get_active()

        if (
            not any([x[1].get_active() for x in self.__register_widgets])
            and ws.get("allowed", True)
            and ws.get("final", None)
        ):
            finals["vars"]["_managed"] = True
            finals["funcs"].extend(ws["final"])

        return finals
