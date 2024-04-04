# timezone.py
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

import logging
import re
import threading
import unicodedata
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from vanilla_installer.core.timezones import (
    all_timezones,
    get_location,
    get_timezone_preview,
)

logger = logging.getLogger("VanillaInstaller::Timezone")


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-timezone.ui")
class TimezoneRow(Adw.ActionRow):
    __gtype_name__ = "TimezoneRow"

    select_button = Gtk.Template.Child()
    country_label = Gtk.Template.Child()

    def __init__(self, title, subtitle, tz_name, toggled_callback, parent_expander, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.tz_name = tz_name
        self.parent_expander = parent_expander

        self.set_title(title)
        self.country_label.set_label(tz_name)

        self.select_button.connect("toggled", toggled_callback, self)
        self.parent_expander.connect("notify::expanded", self.update_time_preview)

    def update_time_preview(self, *args):
        tz_time, tz_date = get_timezone_preview(self.tz_name)
        self.set_subtitle(f"{tz_time} • {tz_date}")


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

    expanders_list = dict(
        sorted(
            {
                country: region
                for region, countries in all_timezones.items()
                for country in countries.keys()
            }.items()
        )
    )

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__step_num = step["num"]

        self.__expanders = []
        self.__tz_entries = []
        self.__generate_timezone_list_widgets()

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.__window.carousel.connect("page-changed", self.timezone_verify)

        self.search_controller.connect("key-released", self.__on_search_key_pressed)
        self.entry_search_timezone.add_controller(self.search_controller)

    def timezone_verify(self, carousel=None, idx=None):
        if idx is not None and idx != self.__step_num:
            return

        def timezone_verify_callback(result, *args):
            if result:
                current_city = result.get_city_name()
                current_country = result.get_country_name()
                for entry in self.__tz_entries:
                    if current_city == entry.title and current_country == entry.subtitle:
                        self.selected_timezone["zone"] = current_city
                        self.selected_timezone["region"] = current_country
                        entry.select_button.set_active(True)
                        return
                self.btn_next.set_sensitive(True)

        thread = threading.Thread(target=get_location, args=(timezone_verify_callback,))
        thread.start()

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
            out = unicodedata.normalize("NFD", msg).encode("ascii", "ignore").decode("utf-8")
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
            visible_entries += match

    def __on_row_toggle(self, __check_button, widget):
        tz_split = widget.tz_name.split("/", 1)
        self.selected_timezone["region"] = tz_split[0]
        self.selected_timezone["zone"] = tz_split[1]
        self.current_tz_label.set_label(widget.tz_name)
        self.current_location_label.set_label(_("(at %s, %s)") % (widget.title, widget.subtitle))
        self.btn_next.set_sensitive(True)

    def __generate_timezone_list_widgets(self):
        def __populate_expander(expander, region, country, *args):
            for city, tzname in all_timezones[region][country].items():
                timezone_row = TimezoneRow(city, country, tzname, self.__on_row_toggle, expander)
                self.__tz_entries.append(timezone_row)
                if len(self.__tz_entries) > 0:
                    timezone_row.select_button.set_group(self.__tz_entries[0].select_button)
                expander.add_row(timezone_row)

        for country, region in self.expanders_list.items():
            if len(all_timezones[region][country]) > 0:
                expander = Adw.ExpanderRow.new()
                expander.set_title(country)
                expander.set_subtitle(region)
                self.all_timezones_group.add(expander)
                self.__expanders.append(expander)
                GLib.idle_add(__populate_expander, expander, region, country)
