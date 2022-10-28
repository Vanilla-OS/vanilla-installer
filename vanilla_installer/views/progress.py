# progress.py
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

import time
from gi.repository import Gtk, GLib, Adw

from vanilla_installer.utils.run_async import RunAsync

from vanilla_installer.views.tour import VanillaTour


@Gtk.Template(resource_path='/io/github/vanilla-os/FirstSetup/gtk/progress.ui')
class VanillaProgress(Gtk.Box):
    __gtype_name__ = 'VanillaProgress'

    carousel_tour = Gtk.Template.Child()
    progressbar = Gtk.Template.Child()

    def __init__(self, window, tour: dict, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__tour = tour
        self.__build_ui()

    def __build_ui(self):
        for _, tour in self.__tour.items():
            self.carousel_tour.append(VanillaTour(self.__window, tour))

        self.__start_tour()

    def __switch_tour(self, *args):
        cur_index = self.carousel_tour.get_position()
        page = self.carousel_tour.get_nth_page(cur_index + 1)

        if page is None:
            page = self.carousel_tour.get_nth_page(0)

        self.carousel_tour.scroll_to(page, True)

    def __start_tour(self):
        def run_async():
            while True:
                GLib.idle_add(self.progressbar.pulse)
                GLib.idle_add(self.__switch_tour)
                time.sleep(5)

        RunAsync(run_async, "tour_loop")
