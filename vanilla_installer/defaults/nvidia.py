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

import subprocess


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-nvidia.ui")
class VanillaDefaultNvidia(Adw.Bin):
    __gtype_name__ = "VanillaDefaultNvidia"

    btn_no = Gtk.Template.Child()
    btn_yes = Gtk.Template.Child()
    btn_info = Gtk.Template.Child()

    info_popover = Gtk.Template.Child()

    use_proprietary = None
    use_open = None
    suggested_drivers = None

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        self.suggested_drivers = self.get_suggested_drivers()

        if self.suggested_drivers == "open":
            self.info_popover.set_visible(False)

        self.btn_yes.connect("clicked", self.use_drivers)
        self.btn_no.connect("clicked", self.no_drivers)
        self.btn_info.connect("clicked", self.show_info_popover)

    def get_finals(self):
        return {
            "nvidia": {
                "use-proprietary": self.use_proprietary,
                "use-open": self.use_open,
            }
        }

    def use_drivers(self, _):
        self.use_open = self.suggested_drivers == "open"
        self.use_proprietary = self.suggested_drivers == "proprietary"

        self.__window.next()

    def no_drivers(self, _):
        self.use_proprietary = False
        self.use_open = False
        self.__window.next()

    def show_info_popover(self, _):
        self.info_popover.popup()

    def get_suggested_drivers(self):
        """
        lspci | grep -E 'NVIDIA.*(GeForce [4-8][0-9]{2}|GeForce GTX [6-9]..)' && exit 0 || exit 1
        0 is legacy, 1 is non-legacy
        """
        res = subprocess.run(
            "lspci | grep -E 'NVIDIA.*(GeForce [4-8][0-9]{2}|GeForce GTX [6-9]..)' && exit 0 || exit 1",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode == 0:
            return "proprietary"

        return "open"
