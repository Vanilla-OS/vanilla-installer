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

import contextlib
import os
import re
import subprocess

from gi.repository import Adw, Gio, GLib, Gtk

from vanilla_installer.core.keymaps import KeyMaps


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-keyboard.ui")
class VanillaDefaultKeyboard(Adw.Bin):
    __gtype_name__ = "VanillaDefaultKeyboard"

    btn_next = Gtk.Template.Child()
    entry_test = Gtk.Template.Child()
    combo_layouts = Gtk.Template.Child()
    combo_variants = Gtk.Template.Child()
    str_list_layouts = Gtk.Template.Child()
    str_list_variants = Gtk.Template.Child()
    entry_search_keyboard = Gtk.Template.Child()
    entry_test = Gtk.Template.Child()

    search_controller = Gtk.EventControllerKey.new()
    test_focus_controller = Gtk.EventControllerFocus.new()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__keymaps = KeyMaps()

        # set up the string list for keyboard layouts
        for country in self.__keymaps.list_all.keys():
            self.str_list_layouts.append(country)

        # set up current keyboard layout
        current_layout, current_variant = self.__get_current_layout()
        for country in self.__keymaps.list_all.keys():
            if current_layout in self.__keymaps.list_all[country].keys():
                self.combo_layouts.set_selected(
                    list(self.__keymaps.list_all.keys()).index(country)
                )
                self.__on_layout_selected()

                for index, variant in enumerate(
                    self.__keymaps.list_all[country].values()
                ):
                    if variant["xkb_variant"] == current_variant:
                        self.combo_variants.set_selected(index)
                        break

                break

        # controllers
        self.entry_search_keyboard.add_controller(self.search_controller)
        self.entry_test.add_controller(self.test_focus_controller)

        # signals
        self.btn_next.connect("clicked", self.__next)
        self.combo_layouts.connect(
            "notify::selected", self.__on_layout_selected)
        self.search_controller.connect(
            "key-released", self.__on_search_key_pressed)
        if "VANILLA_NO_APPLY_XKB" not in os.environ:
            self.test_focus_controller.connect("enter", self.__apply_layout)

    def __next(self, *args):
        if "VANILLA_NO_APPLY_XKB" in os.environ:
            self.__window.next()
        else:
            self.__window.next(None, self.__apply_layout)

    def get_finals(self):
        variant_index = self.combo_variants.get_selected()
        variant = self.str_list_variants.get_item(variant_index)

        if variant is None:
            return {
                "keyboard": {"layout": "us", "model": "pc105", "variant": ""}
            }  # fallback

        variant = variant.get_string()
        layout_index = self.combo_layouts.get_selected()
        layout = list(self.__keymaps.list_all.keys())[layout_index]
        layout = self.__keymaps.list_all[layout]

        for key in layout.keys():
            if layout[key]["display_name"] == variant:
                return {
                    "keyboard": {
                        "layout": layout[key]["xkb_layout"],
                        "model": "pc105",
                        "variant": layout[key]["xkb_variant"],
                    }
                }

    def __get_current_layout(self):
        res = subprocess.run(
            ["setxkbmap", "-query"], capture_output=True, text=True
        ).stdout.splitlines()

        current_layout = [
            line.split(": ")[1] for line in res if line.startswith("layout")
        ][0]
        current_variant = None

        if "," in current_layout:
            current_layout = current_layout.split(",")[0].strip()

        with contextlib.suppress(IndexError):
            current_variant = [
                line.split(": ")[1] for line in res if line.startswith("variant")
            ][0]
            if "," in current_variant:
                current_variant = current_variant.split(",")[0].strip()

        return current_layout, current_variant

    def __on_layout_selected(self, *args):
        self.str_list_variants.splice(0, self.str_list_variants.get_n_items())

        layout_index = self.combo_layouts.get_selected()
        layout = list(self.__keymaps.list_all.keys())[layout_index]
        layout = self.__keymaps.list_all[layout]

        for variant in layout.keys():
            self.str_list_variants.append(layout[variant]["display_name"])

        self.combo_variants.set_visible(
            self.str_list_variants.get_n_items() != 0)

    def __apply_layout(self, *args):
        variant_index = self.combo_variants.get_selected()
        variant = self.str_list_variants.get_item(variant_index)

        if variant is None:
            return

        variant = variant.get_string()
        layout_index = self.combo_layouts.get_selected()
        layout = list(self.__keymaps.list_all.keys())[layout_index]
        layout = self.__keymaps.list_all[layout]

        for key in layout.keys():
            if layout[key]["display_name"] == variant:
                xkb_layout = layout[key]["xkb_layout"]
                xkb_variant = layout[key]["xkb_variant"]
                break

        # set the layout
        self.__set_keyboard_layout(xkb_layout, xkb_variant)

    def __on_search_key_pressed(self, *args):
        keywords = self.entry_search_keyboard.get_text().lower()
        keywords = re.sub(r"[^a-zA-Z0-9 ]", "", keywords)

        if keywords == "" or len(keywords) < 3:
            return

        for country in self.__keymaps.list_all.keys():
            country = re.sub(r"[^a-zA-Z0-9 ]", "", country)
            if re.search(keywords, country, re.IGNORECASE):
                self.combo_layouts.set_selected(
                    list(self.__keymaps.list_all.keys()).index(country)
                )
                # self.__on_layout_selected()
                break

    def __set_keyboard_layout(self, layout, variant=None):
        value = layout

        if variant != "":
            value = layout + "+" + variant

        Gio.Settings.new("org.gnome.desktop.input-sources").set_value(
            "sources",
            GLib.Variant.new_array(
                GLib.VariantType("(ss)"),
                [
                    GLib.Variant.new_tuple(
                        GLib.Variant.new_string(
                            "xkb"), GLib.Variant.new_string(value)
                    )
                ],
            ),
        )
