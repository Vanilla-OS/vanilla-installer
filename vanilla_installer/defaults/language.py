# language.py
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

import unicodedata

from gi.repository import Adw, GLib, Gtk
from vanilla_installer.core import languages
from vanilla_installer.core.languages import all_language_names, all_languages


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-language.ui")
class LanguageRow(Adw.ActionRow):
    __gtype_name__ = "LanguageRow"

    select_button = Gtk.Template.Child()
    suffix_bin = Gtk.Template.Child()

    def __init__(self, title, subtitle, keywords, selected_language, **kwargs):
        super().__init__(**kwargs)
        self.__title = title
        self.__subtitle = subtitle
        self.__selected_language = selected_language
        self.search_keywords = _normalize(" ".join([*keywords, title, subtitle]))

        self.set_title(title)
        self.suffix_bin.set_label(subtitle)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

    def __on_check_button_toggled(self, widget):
        if not widget.get_active():
            return

        self.__selected_language["language_title"] = self.__title
        self.__selected_language["language_subtitle"] = self.__subtitle

        group = self.get_ancestor(Gtk.ListBox)
        if group is not None:
            group.emit("selected-rows-changed")


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-language.ui")
class VanillaDefaultLanguage(Adw.Bin):
    __gtype_name__ = "VanillaDefaultLanguage"

    btn_next = Gtk.Template.Child()
    entry_search_language = Gtk.Template.Child()
    all_languages_group = Gtk.Template.Child()

    selected_language = {"language_title": None, "language_subtitle": None}

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__language_rows = []
        self.delta = True
        self.search_controller = Gtk.EventControllerKey.new()
        self.__generate_language_list_widgets()

        self.gen_deltas()
        self.__language_verify()

        # signals
        self.btn_next.connect("clicked", self.__on_next_clicked)
        self.all_languages_group.connect(
            "selected-rows-changed", self.__language_verify
        )
        self.all_languages_group.connect("row-selected", self.__language_verify)
        self.all_languages_group.connect("row-activated", self.__language_verify)
        self.__carousel_handler = self.__window.carousel.connect(
            "page-changed", self.__language_verify
        )

        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_language.add_controller(self.search_controller)

    def cleanup(self):
        self.__window.carousel.disconnect(self.__carousel_handler)

    def gen_deltas(self):
        self.all_languages_group.remove_all()
        for widget in self.__language_rows:
            self.all_languages_group.append(widget)


    def del_deltas(self):
        self.all_languages_group.remove_all()

    def __language_verify(self, *args):
        language_code = self.selected_language["language_subtitle"]
        self.btn_next.set_sensitive(language_code is not None)

    def __on_next_clicked(self, widget, *args):
        language_code = self.selected_language["language_subtitle"]

        if language_code is not None and language_code != languages.current_language:
            languages.set_language(language_code)
            GLib.idle_add(self.__window.reload_language, True)
            return

        self.__window.next()

    def __generate_language_list_widgets(self):
        for language_code, language_title in all_languages.items():
            language_row = LanguageRow(
                language_title,
                language_code,
                [all_language_names[language_code]],
                self.selected_language,
            )

            if len(self.__language_rows) > 0:
                language_row.select_button.set_group(self.__language_rows[0].select_button)

            self.__language_rows.append(language_row)

            if languages.current_language == language_code:
                language_row.select_button.set_active(True)
                self.selected_language["language_title"] = language_title
                self.selected_language["language_subtitle"] = language_code

    def get_finals(self):
        return {"language": self.selected_language["language_subtitle"]}

    def __on_search_key_pressed(self, *args):
        keywords = _normalize(self.entry_search_language.get_text().strip())

        for row in self.all_languages_group:
            row.set_visible(keywords in row.search_keywords)
