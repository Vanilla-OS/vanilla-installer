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


@Gtk.Template(resource_path='/io/github/vanilla-os/FirstSetup/gtk/default-keyboard.ui')
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
        self.__xkb_info = XkbInfo()

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.combo_layouts.connect("notify::selected", self.__on_layout_selected)
        self.combo_variants.connect("notify::selected", self.__on_variant_selected)

        # set combo_variants visibility based on the number of variants
        self.combo_variants.set_visible(self.str_list_variants.get_n_items() != 0)
        
        # set up the string list for keyboard layouts
        for _, lang in all_keymaps.items():
            self.str_list_layouts.append(lang)

    def get_finals(self):
        return {}
    
    def __on_layout_selected(self, *args):
        self.str_list_variants.splice(0, self.str_list_variants.get_n_items())

        layout_index = self.combo_layouts.get_selected()
        layout = list(all_keymaps.keys())[layout_index]
        
        for variant in self.__xkb_info.get_layouts_for_language(layout):
            self.str_list_variants.append(variant)

        self.__set_xkbmap(layout)
    
    def __on_variant_selected(self, *args):
        self.combo_variants.set_visible(self.str_list_variants.get_n_items() != 0)

        variant_index = self.combo_variants.get_selected()
        variant = self.str_list_variants.get_item(variant_index)
        
        if variant is None:
            return
        
        variant = variant.get_string()

        if "+" in variant:
            layout, variant = variant.split("+")
        else:
            layout = variant
            variant = None

        self.__set_xkbmap(layout, variant)
        
    def __set_xkbmap(self, layout, variant=None):
        subprocess.run(
            ["setxkbmap", "-layout", layout]
            + (["-variant", variant] if variant is not None else [])
        )