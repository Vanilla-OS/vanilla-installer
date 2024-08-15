# progress.py
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

import time
from gettext import gettext as _

from gi.repository import Gdk, Gio, GLib, Gtk, Pango, Vte, Adw

from vanilla_installer.utils.run_async import RunAsync
from vanilla_installer.views.tour import VanillaTour


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/progress.ui")
class VanillaProgress(Gtk.Box):
    __gtype_name__ = "VanillaProgress"

    carousel_tour = Gtk.Template.Child()
    tour_button = Gtk.Template.Child()
    tour_box = Gtk.Template.Child()
    tour_btn_back = Gtk.Template.Child()
    tour_btn_next = Gtk.Template.Child()
    progressbar = Gtk.Template.Child()
    console_button = Gtk.Template.Child()
    console_box = Gtk.Template.Child()
    console_output = Gtk.Template.Child()

    def __init__(self, window, tour: dict, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__tour = tour
        self.__terminal = Vte.Terminal()
        self.__font = Pango.FontDescription()
        self.__font.set_family("Monospace")
        self.__font.set_size(13 * Pango.SCALE)
        self.__font.set_weight(Pango.Weight.NORMAL)
        self.__font.set_stretch(Pango.Stretch.NORMAL)
        self.style_manager = Adw.StyleManager().get_default()
        self.delta = False

        self.__build_ui()
        self.__on_setup_terminal_colors()

        self.style_manager.connect("notify::dark", self.__on_setup_terminal_colors)
        self.tour_button.connect("clicked", self.__on_tour_button)
        self.tour_btn_back.connect("clicked", self.__on_tour_back)
        self.tour_btn_next.connect("clicked", self.__on_tour_next)
        self.carousel_tour.connect("page-changed", self.__on_page_changed)
        self.console_button.connect("clicked", self.__on_console_button)


    def __on_setup_terminal_colors(self, *args):
          
        is_dark: bool = self.style_manager.get_dark()

        palette = [
            "#363636",
            "#c01c28",
            "#26a269",
            "#a2734c",
            "#12488b",
            "#a347ba",
            "#2aa1b3",
            "#cfcfcf",
            "#5d5d5d",
            "#f66151",
            "#33d17a",
            "#e9ad0c",
            "#2a7bde",
            "#c061cb",
            "#33c7de",
            "#ffffff",
        ]

        FOREGROUND = palette[0]
        BACKGROUND = palette[15]
        FOREGROUND_DARK = palette[15]
        BACKGROUND_DARK = palette[0]

        self.fg = Gdk.RGBA()
        self.bg = Gdk.RGBA()

        self.colors = [Gdk.RGBA() for c in palette]
        [color.parse(s) for (color, s) in zip(self.colors, palette)]
        
        if is_dark:
            self.fg.parse(FOREGROUND_DARK)
            self.bg.parse(BACKGROUND_DARK)
        else:
            self.fg.parse(FOREGROUND)
            self.bg.parse(BACKGROUND)

        self.__terminal.set_colors(self.fg, self.bg, self.colors)

    def __on_tour_button(self, *args):
        self.tour_box.set_visible(True)
        self.console_box.set_visible(False)
        self.tour_button.set_visible(False)
        self.console_button.set_visible(True)

    def __on_tour_back(self, *args):
        cur_index = self.carousel_tour.get_position()
        page = self.carousel_tour.get_nth_page(cur_index - 1)
        self.carousel_tour.scroll_to(page, True)

    def __on_tour_next(self, *args):
        cur_index = self.carousel_tour.get_position()
        page = self.carousel_tour.get_nth_page(cur_index + 1)
        self.carousel_tour.scroll_to(page, True)

    def __on_page_changed(self, *args):
        position = self.carousel_tour.get_position()
        pages = self.carousel_tour.get_n_pages()

        self.tour_btn_back.set_visible(position < pages and position > 0)
        self.tour_btn_next.set_visible(position < pages - 1)

    def __on_console_button(self, *args):
        self.tour_box.set_visible(False)
        self.console_box.set_visible(True)
        self.tour_button.set_visible(True)
        self.console_button.set_visible(False)      

    def __build_ui(self):
        self.__terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.__terminal.set_font(self.__font)
        self.__terminal.set_mouse_autohide(True)
        self.__terminal.set_input_enabled(False)
        self.console_output.append(self.__terminal)
        self.__terminal.connect("child-exited", self.on_vte_child_exited)

        for _, tour in self.__tour.items():
            self.carousel_tour.append(VanillaTour(self.__window, tour))

        self.__start_tour()

    def __switch_tour(self, *args):
        cur_index = self.carousel_tour.get_position() + 1
        if cur_index == self.carousel_tour.get_n_pages():
            cur_index = 0

        page = self.carousel_tour.get_nth_page(cur_index)

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

        # Terminal applications return 0 on success and 1 on failure, so we need
        # to invert the status to get the correct result.
        status = not bool(status)
        self.__window.set_installation_result(status, self.__terminal)

    def start(self, recipe):
        # If VANILLA_FAKE was passed as argument
        if not recipe:
            self.__window.set_installation_result(False, None)
            return

        self.__terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            ".",
            ["sh", "-c", f"sudo albius {recipe}"],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None,
        )
