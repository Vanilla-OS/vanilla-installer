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
from gi.repository import Gtk, GLib, Adw, Vte

from vanilla_installer.utils.run_async import RunAsync

from vanilla_installer.views.tour import VanillaTour


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/progress.ui')
class VanillaProgress(Gtk.Box):
    __gtype_name__ = 'VanillaProgress'

    carousel_tour = Gtk.Template.Child()
    tour_button = Gtk.Template.Child()
    tour_box = Gtk.Template.Child()
    progressbar = Gtk.Template.Child()
    console_button = Gtk.Template.Child()
    console_box = Gtk.Template.Child()
    console_output = Gtk.Template.Child()


    def __init__(self, window, tour: dict, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__tour = tour    
        self.__terminal = Vte.Terminal()

        self.__build_ui()

        self.tour_button.connect("clicked", self.__on_tour_button)
        self.console_button.connect("clicked", self.__on_console_button)

    def __on_tour_button(self, *args):
        self.tour_box.set_visible(True)
        self.console_box.set_visible(False)
        self.tour_button.set_visible(False)
        self.console_button.set_visible(True)

    def __on_console_button(self, *args):
        self.tour_box.set_visible(False)
        self.console_box.set_visible(True)
        self.tour_button.set_visible(True)
        self.console_button.set_visible(False)

    def __build_ui(self):
        self.__terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.__terminal.set_mouse_autohide(True)
        self.console_output.append(self.__terminal)
        self.__terminal.connect("child-exited", self.on_vte_child_exited)

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

        RunAsync(run_async, None)
    
    def on_vte_child_exited(self, terminal, status, *args):
        terminal.get_parent().remove(terminal)
        '''
        Since distinst returns 0 on success and 1 on failure (I mean, this
        is what I've seen so far), we need to invert the status to get the
        correct result.
        '''
        status = not bool(status)
        self.__window.set_installation_result(status, self.__terminal)

    def start(self, install_script):
        self.__terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            ".",
            ["bash", install_script],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None
        )
