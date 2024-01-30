# keyboard.py
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

import re
import unicodedata

from gi.repository import Adw, Gtk
from gettext import gettext as _

from vanilla_installer.core.timezones import (
    all_timezones,
    get_location,
    get_timezone_preview,
)
from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-timezone.ui")
class TimezoneRow(Adw.ActionRow):
    __gtype_name__ = "TimezoneRow"

    select_button = Gtk.Template.Child()
    country_label = Gtk.Template.Child()

    def __init__(self, title, subtitle, tz_name, parent, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.parent = parent
        self.tz_name = tz_name

        tz_time, tz_date = get_timezone_preview(tz_name)

        self.set_title(title)
        self.set_subtitle(f"{tz_time} • {tz_date}")
        self.country_label.set_label(tz_name)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

    def __on_check_button_toggled(self, widget):
        tz_split = self.tz_name.split("/", 1)
        self.parent.selected_timezone["region"] = tz_split[0]
        self.parent.selected_timezone["zone"] = tz_split[1]
        self.parent.current_tz_label.set_label(self.tz_name)
        self.parent.current_location_label.set_label(_("(at %s, %s)") % (self.title, self.subtitle))
        self.parent.timezone_verify()


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-timezone.ui")
class VanillaDefaultTimezone(Adw.Bin):
    __gtype_name__ = "VanillaDefaultTimezone"

    btn_next = Gtk.Template.Child()
    entry_search_timezone = Gtk.Template.Child()
    all_timezones_group = Gtk.Template.Child()
    current_tz_label = Gtk.Template.Child()
    current_location_label = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()
    selected_timezone = {"region": "Europe", "zone": None}

    expanders_list = {
        country: region
        for region, countries in all_timezones.items()
        for country in countries.keys()
    }

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        self.__expanders = []
        self.__tz_entries = []
        self.__generate_timezone_list_widgets()

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.__window.carousel.connect("page-changed", self.timezone_verify)

        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_timezone.add_controller(self.search_controller)

    def timezone_verify(self, *args):
        valid = (
            self.selected_timezone["region"]
            and self.selected_timezone["zone"] is not None
        )
        self.btn_next.set_sensitive(valid)

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
        def remove_accents(msg: str):
            out = unicodedata.normalize('NFD', msg)\
                   .encode('ascii', 'ignore')\
                   .decode('utf-8')
            return str(out)

        search_entry = self.entry_search_timezone.get_text().lower()
        keywords = remove_accents(search_entry)

        if len(keywords) == 0:
            for expander in self.__expanders:
                expander.set_visible(True)
                expander.set_expanded(False)
            return

        current_expander = 0
        current_country = self.__tz_entries[0].subtitle
        visible_entries = 0
        for entry in self.__tz_entries:
            row_title = remove_accents(entry.get_title().lower())
            match = re.search(keywords, row_title, re.IGNORECASE) is not None
            entry.set_visible(match)
            if entry.subtitle != current_country:
                self.__expanders[current_expander].set_expanded(True)
                self.__expanders[current_expander].set_visible(visible_entries != 0)
                visible_entries = 0
                current_country = entry.subtitle
                current_expander += 1
            visible_entries += 1 if match else 0

    def __generate_timezone_list_widgets(self):
        first_elem = None
        for country, region in dict(sorted(self.expanders_list.items())).items():
            if len(all_timezones[region][country]) > 0:
                country_tz_expander_row = Adw.ExpanderRow.new()
                country_tz_expander_row.set_title(country)
                country_tz_expander_row.set_subtitle(region)
                self.all_timezones_group.add(country_tz_expander_row)
                self.__expanders.append(country_tz_expander_row)

                for city, tzname in sorted(all_timezones[region][country].items()):
                    timezone_row = TimezoneRow(city, country, tzname, self)
                    country_tz_expander_row.add_row(timezone_row)
                    self.__tz_entries.append(timezone_row)
                    if first_elem is None:
                        first_elem = timezone_row
                    else:
                        timezone_row.select_button.set_group(first_elem.select_button)

        def __set_located_timezone(result, error):
            if not result:
                return
            current_city = result.get_city_name()
            current_country = result.get_country_name()
            for entry in self.__tz_entries:
                if current_city == entry.title and current_country == entry.subtitle:
                    self.selected_timezone["zone"] = current_city
                    self.selected_timezone["region"] = current_country
                    entry.select_button.set_active(True)
                    return
        RunAsync(get_location, __set_located_timezone)
