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

import sys
import time
import subprocess
import contextlib
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.core.timezones import all_timezones, get_current_timezone, get_preview_timezone



@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-timezone.ui')
class VanillaDefaultTimezone(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultTimezone'

    btn_next = Gtk.Template.Child()
    row_preview = Gtk.Template.Child()
    combo_region = Gtk.Template.Child()
    combo_zone = Gtk.Template.Child()
    str_list_region = Gtk.Template.Child()
    str_list_zone = Gtk.Template.Child()
    entry_search_timezone = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        
        # set up the string list for keyboard layouts
        for country, _ in all_timezones.items():
            self.str_list_region.append(country)
        
        # set up current timezone
        current_country, current_city = get_current_timezone()
        for country, _ in all_timezones.items():
            if country == current_country:
                self.combo_region.set_selected(list(all_timezones.keys()).index(country))
                self.__on_country_selected(None, None)

                for index, city in enumerate(all_timezones[country]):
                    if city == current_city:
                        self.combo_zone.set_selected(index)
                        break

                break

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.combo_region.connect("notify::selected", self.__on_country_selected)
        self.combo_zone.connect("notify::selected", self.__on_city_selected)
        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_timezone.add_controller(self.search_controller)

    def get_finals(self):
        try:
            return {
                "timezone": {
                    "region": list(all_timezones.keys())[self.combo_region.get_selected()],
                    "zone": all_timezones[list(all_timezones.keys())[self.combo_region.get_selected()]][self.combo_zone.get_selected()]
                }
            }
        except IndexError:
            return {
                "timezone": {
                    "region": "Europe",
                    "zone": "London"
                }
            }
    
    def __on_country_selected(self, combo, param):
        self.str_list_zone.splice(0, self.str_list_zone.get_n_items())

        country_index = self.combo_region.get_selected()
        country = list(all_timezones.keys())[country_index]
        for timezone in all_timezones[country]:
            self.str_list_zone.append(timezone)

    def __on_city_selected(self, combo, param):
        country_index = self.combo_region.get_selected()
        country = list(all_timezones.keys())[country_index]
        city_index = self.combo_zone.get_selected()

        with contextlib.suppress(IndexError):
            city = all_timezones[country][city_index]
            _time, _date = get_preview_timezone(country, city)

            self.row_preview.set_title(_time)
            self.row_preview.set_subtitle(_date)

    def __on_search_key_pressed(self, *args):
        keywords = self.entry_search_timezone.get_text().lower()

        if keywords == "" or len(keywords) < 3:
            return
        
        for country, cities in all_timezones.items():
            for city in cities:

                if keywords in city.lower():
                    self.combo_region.set_selected(list(all_timezones.keys()).index(country))

                    for index, _city in enumerate(all_timezones[country]):
                        if city == _city:
                            self.combo_zone.set_selected(index)
                            break

                    return

