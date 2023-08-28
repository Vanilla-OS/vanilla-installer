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

from vanilla_installer.core.timezones import (
    all_timezones,
    get_current_timezone,
    get_preview_timezone,
)

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-timezone.ui")
class TimezoneRow(Adw.ActionRow):
    __gtype_name__ = "TimezoneRow"

    select_button = Gtk.Template.Child()
    country_label = Gtk.Template.Child()

    def __init__(self, title, subtitle, time, date, selected_timezone, **kwargs):
        super().__init__(**kwargs)
        self.__title = title
        self.__subtitle = subtitle
        self.__selected_timezone = selected_timezone

        self.set_title(title)
        self.set_subtitle(f'{time} • {date}')
        self.country_label.set_label(subtitle)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

    def __on_check_button_toggled(self, widget):
        self.__selected_timezone["zone"] = self.__title
        self.__selected_timezone["region"] = self.__subtitle

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-timezone.ui")
class VanillaDefaultTimezone(Adw.Bin):
    __gtype_name__ = "VanillaDefaultTimezone"

    btn_next = Gtk.Template.Child()
    entry_search_timezone = Gtk.Template.Child()
    all_timezones_group = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()
    selected_timezone = {"region": "Europe", "zone": None}

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        self.__timezone_rows = self.__generate_timezone_list_widgets(self.selected_timezone)
        for i, widget in enumerate(self.__timezone_rows):
            self.all_timezones_group.append(widget)

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_timezone.add_controller(self.search_controller)

    def get_finals(self):
        try:
            return {
                "timezone": {
                    "region": self.selected_timezone['region'],
                    "zone": self.selected_timezone['zone'],
                }
            }
        except IndexError:
            return {"timezone": {"region": "Europe", "zone": "London"}}
        
    def __on_search_key_pressed(self, *args):
        keywords = re.sub(r"[^a-zA-Z0-9 ]", "", self.entry_search_timezone.get_text().lower())

        for row in self.all_timezones_group:
            row_title = re.sub(r'[^a-zA-Z0-9 ]', '', row.get_title().lower())
            row.set_visible(re.search(keywords, row_title, re.IGNORECASE) is not None)

    def __generate_timezone_dict(self):
        all_timezones_dict =dict()

        for continent, cities in all_timezones.items():
            for city in cities:
                all_timezones_dict[city] = continent

        return all_timezones_dict

    def __generate_timezone_list_widgets(self, selected_timezone):
        timezone_widgets = []
        current_country, current_city = get_current_timezone()
        
        for city, continent in self.__generate_timezone_dict().items():
            time, date = get_preview_timezone(continent,city)
            timezone_row = TimezoneRow(city, continent, time, date, selected_timezone)
            
            if len(timezone_widgets)>0:
                timezone_row.select_button.set_group(timezone_widgets[0].select_button)
            timezone_widgets.append(timezone_row)
            
            #set up current timezone
            if current_city == city and current_country == continent:
                timezone_row.select_button.set_active(True)
            
        return timezone_widgets