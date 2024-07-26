# image.py
#
# Copyright 2024 mirkobrombin muhdsalm
#
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

from gi.repository import Adw, Gtk

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-image.ui")
class VanillaDefaultImage(Adw.Bin):
    __gtype_name__ = "VanillaDefaultImage"

    btn_next = Gtk.Template.Child()

    use_image_switch = Gtk.Template.Child()

    image_url_entry = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        self.btn_next.connect("clicked", self.__window.next)
        self.use_image_switch.connect(
            "state-set", self.__on_image_switch_set)
        self.image_url_entry.connect(
            "changed", self.__on_url_changed
        )

        self.image_url_filled = False

        self.__update_btn_next()

    def get_finals(self):
        return {
            "custom_image": self.image_url_entry.get_text(),
        }

    def __on_image_switch_set(self, state, user_data):
        self.__update_btn_next()

    def __on_url_changed(self, *args):
        image_url = self.image_url_entry.get_text()
        if (
            image_url == self.image_url_entry.get_text()
        ):
            self.image_url_filled = True
            self.image_url_entry.remove_css_class("error")
        else:
            self.image_url_filled = False
            self.image_url_entry.add_css_class("error")

        self.__update_btn_next()

    def __update_btn_next(self):
        rule = self.image_url_filled or self.use_image_switch.get_active() is False
        self.btn_next.set_sensitive(rule)
