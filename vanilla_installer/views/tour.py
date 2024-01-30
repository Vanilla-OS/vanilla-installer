# tour.py
#
# Copyright 2024 mirkobrombin
# Copyright 2024 muqtadir
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

from gettext import gettext as _

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/tour.ui")
class VanillaTour(Adw.Bin):
    __gtype_name__ = "VanillaTour"

    status_page = Gtk.Template.Child()
    assets_svg = Gtk.Template.Child()

    def __init__(self, window, tour, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__tour = tour
        self.__build_ui()

    def __build_ui(self):
        self.assets_svg.set_resource(self.__tour["resource"])
        self.status_page.set_title(self.__tour["title"])
        self.status_page.set_description(self.__tour["description"])
