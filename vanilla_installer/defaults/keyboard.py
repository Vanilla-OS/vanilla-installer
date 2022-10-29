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
from gi.repository import Gtk, Gio, GLib, Adw
from gi.repository.GnomeDesktop import XkbInfo

from vanilla_installer.models.keymaps import all_keymaps


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-keyboard.ui')
class VanillaDefaultKeyboard(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultKeyboard'

    btn_next = Gtk.Template.Child()
    entry_test = Gtk.Template.Child()
    combo_layouts = Gtk.Template.Child()
    combo_variants = Gtk.Template.Child()
    str_list_layouts = Gtk.Template.Child()
    str_list_variants = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        
        # set up the string list for keyboard layouts
        for country in all_keymaps.keys():
            self.str_list_layouts.append(country)
        
        # set up current keyboard layout
        current_layout, current_variant = self.__get_current_layout()
        for country in all_keymaps.keys():
            if current_layout in all_keymaps[country].keys():
                self.combo_layouts.set_selected(list(all_keymaps.keys()).index(country))
                self.__on_layout_selected()

                for index, variant in enumerate(all_keymaps[country].values()):
                    if variant["xkb_variant"] == current_variant:
                        self.combo_variants.set_selected(index)
                        break

                break

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.combo_layouts.connect("notify::selected", self.__on_layout_selected)
        self.combo_variants.connect("notify::selected", self.__on_variant_selected)

    def get_finals(self):
        return {}
    
    def __get_current_layout(self):
        res = subprocess.run(
            ["setxkbmap", "-query"], capture_output=True, text=True
        ).stdout.splitlines()

        current_layout = [l.split(": ")[1] for l in res if l.startswith("layout")][0]
        current_variant = [l.split(": ")[1] for l in res if l.startswith("variant")][0]

        if "," in current_layout:
            current_layout = current_layout.split(",")[0].strip()

        if "," in current_variant:
            current_variant = current_variant.split(",")[0].strip()
        
        return current_layout, current_variant
    
    def __on_layout_selected(self, *args):
        self.str_list_variants.splice(0, self.str_list_variants.get_n_items())

        layout_index = self.combo_layouts.get_selected()
        layout = list(all_keymaps.keys())[layout_index]
        layout = all_keymaps[layout]
        
        for variant in layout.keys():
            self.str_list_variants.append(layout[variant]["display_name"])

        self.combo_variants.set_visible(self.str_list_variants.get_n_items() != 0)
    
    def __on_variant_selected(self, *args):
        variant_index = self.combo_variants.get_selected()
        variant = self.str_list_variants.get_item(variant_index)

        if variant is None:
            return

        variant = variant.get_string()
        layout_index = self.combo_layouts.get_selected()
        layout = list(all_keymaps.keys())[layout_index]
        layout = all_keymaps[layout]

        for key in layout.keys():
            if layout[key]["display_name"] == variant:
                xkb_layout = layout[key]["xkb_layout"]
                xkb_variant = layout[key]["xkb_variant"]
                break

        # set the layout
        self.__set_xkbmap(xkb_layout, xkb_variant)

    def __set_xkbmap(self, layout, variant=None):
        if variant is None:
            subprocess.run(["setxkbmap", layout])
        else:
            subprocess.run(["setxkbmap", layout, "-variant", variant])