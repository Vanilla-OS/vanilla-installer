# nvidia.py
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

from gi.repository import Adw, Gtk

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-nvidia.ui")
class VanillaDefaultNvidia(Adw.Bin):
    __gtype_name__ = "VanillaDefaultNvidia"

    btn_no = Gtk.Template.Child()
    btn_yes = Gtk.Template.Child()
    btn_info = Gtk.Template.Child()

    info_popover = Gtk.Template.Child()

    use_proprietary = None

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        self.btn_yes.connect("clicked", self.use_proprietary_drivers)
        self.btn_no.connect("clicked", self.use_open_drivers)
        self.btn_info.connect("clicked", self.show_info_popover)

    def get_finals(self):
        return {
            "nvidia": {
                "use-proprietary": self.use_proprietary,
            }
        }

    def use_open_drivers(self, _):
        self.use_proprietary = False
        self.__window.next()

    def use_proprietary_drivers(self, _):
        self.use_proprietary = True
        self.__window.next()

    def show_info_popover(self, _):
        self.info_popover.popup()