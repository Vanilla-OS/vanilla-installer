# tour.py
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

import webbrowser
from gi.repository import Gtk, Adw


@Gtk.Template(resource_path='/io/github/vanilla-os/FirstSetup/gtk/tour.ui')
class VanillaTour(Adw.Bin):
    __gtype_name__ = 'VanillaTour'

    status_page = Gtk.Template.Child()
    btn_read_more = Gtk.Template.Child()

    def __init__(self, window, tour, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__tour = tour
        self.__build_ui()

        # signals
        self.btn_read_more.connect("clicked", self.__on_read_more)

    def __build_ui(self):
        self.status_page.set_icon_name(self.__tour["icon"])
        self.status_page.set_title(self.__tour["title"])
        self.status_page.set_description(self.__tour["description"])
        
        self.btn_read_more.set_visible(bool("read_more_link" in self.__tour))
        
    def __on_read_more(self, e):
        webbrowser.open_new_tab(self.__tour["read_more_link"])
