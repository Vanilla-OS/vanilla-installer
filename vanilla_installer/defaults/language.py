# keyboard.py
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

import re

from gi.repository import Adw, Gtk

from vanilla_installer.core.languages import all_languages, current_language


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-language.ui")
class VanillaDefaultLanguage(Adw.Bin):
    __gtype_name__ = "VanillaDefaultLanguage"

    btn_next = Gtk.Template.Child()
    combo_languages = Gtk.Template.Child()
    str_list_languages = Gtk.Template.Child()
    entry_search_language = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # set up the string list for all the languages
        for _, lang in all_languages.items():
            self.str_list_languages.append(lang)

        # set up current language
        for locale in all_languages.keys():
            if current_language == locale:
                self.combo_languages.set_selected(
                    list(all_languages.keys()).index(locale)
                )
                break

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.search_controller.connect(
            "key-released", self.__on_search_key_pressed)
        self.entry_search_language.add_controller(self.search_controller)

    def get_finals(self):
        return {
            "language": list(all_languages.keys())[self.combo_languages.get_selected()]
        }

    def __on_search_key_pressed(self, *args):
        keywords = self.entry_search_language.get_text().lower()
        keywords = re.sub(r"[^a-zA-Z0-9 ]", "", keywords)

        if keywords == "" or len(keywords) < 3:
            return

        for locale, lang in all_languages.items():
            lang = re.sub(r"[^a-zA-Z0-9 ]", "", lang)
            if re.search(keywords, lang, re.IGNORECASE):
                self.combo_languages.set_selected(
                    list(all_languages.keys()).index(locale)
                )
                break
