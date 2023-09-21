# keyboard.py
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

import re

from gi.repository import Adw, Gtk

from vanilla_installer.core.timezones import (
    all_timezones,
    get_current_timezone,
    get_preview_timezone,
)

from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-timezone.ui")
class TimezoneRow(Adw.ActionRow):
    __gtype_name__ = "TimezoneRow"

    select_button = Gtk.Template.Child()
    country_label = Gtk.Template.Child()

    def __init__(self, title, subtitle, selected_timezone, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.__selected_timezone = selected_timezone

        tz_time, tz_date = get_preview_timezone(subtitle, title)

        self.set_title(title)
        self.set_subtitle(f"{tz_time} • {tz_date}")
        self.country_label.set_label(subtitle)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

    def __on_check_button_toggled(self, widget):
        self.__selected_timezone["zone"] = self.title
        self.__selected_timezone["region"] = self.subtitle


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-timezone.ui")
class VanillaDefaultTimezone(Adw.Bin):
    __gtype_name__ = "VanillaDefaultTimezone"

    btn_next = Gtk.Template.Child()
    entry_search_timezone = Gtk.Template.Child()
    all_timezones_group = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()
    selected_timezone = {"region": "Europe", "zone": None}

    match_regex = re.compile(r"[^a-zA-Z0-9 ]")

    all_timezones_dict = {
        city: continent
        for continent, cities in all_timezones.items()
        for city in cities
    }

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__timezone_rows = []

        RunAsync(self.__set_current_timezone)

        self.__generate_timezone_list_widgets()
        for widget in self.__timezone_rows:
            self.all_timezones_group.append(widget)

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_timezone.add_controller(self.search_controller)

    def get_finals(self):
        try:
            return {
                "timezone": {
                    "region": self.selected_timezone["region"],
                    "zone": self.selected_timezone["zone"],
                }
            }
        except IndexError:
            return {"timezone": {"region": "Europe", "zone": "London"}}

    def __on_search_key_pressed(self, *args):
        keywords = self.match_regex.sub(
            "", self.entry_search_timezone.get_text().lower()
        )

        for row in self.all_timezones_group:
            row_title = self.match_regex.sub("", row.get_title().lower())
            row.set_visible(re.search(keywords, row_title, re.IGNORECASE) is not None)

    def __generate_timezone_list_widgets(self):
        for city, continent in self.all_timezones_dict.items():
            timezone_row = TimezoneRow(city, continent, self.selected_timezone)

            if len(self.__timezone_rows) > 0:
                timezone_row.select_button.set_group(
                    self.__timezone_rows[0].select_button
                )

            self.__timezone_rows.append(timezone_row)

    def __set_current_timezone(self):
        current_country, current_city = get_current_timezone()

        while len(self.__timezone_rows) < len(self.all_timezones_dict):
            pass

        for row in self.__timezone_rows:
            if current_city == row.title and current_country == row.subtitle:
                row.select_button.set_active(True)
