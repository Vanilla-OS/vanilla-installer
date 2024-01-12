# window_unsupported.py
#
# Copyright 2023 muqtadir
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
import subprocess
from gi.repository import Adw, Gtk
from vanilla_installer.utils.recipe import RecipeLoader


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/window-unsupported.ui")
class VanillaUnsupportedWindow(Adw.Window):
    __gtype_name__ = "VanillaUnsupportedWindow"

    btn_poweroff = Gtk.Template.Child()
    description_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.description_label.set_label(_("%s requires UEFI to install") % RecipeLoader().raw['distro_name'])
        self.btn_poweroff.connect("clicked", self.__on_poweroff)

    def __on_poweroff(self, btn):
        subprocess.call(["systemctl", "poweroff"])


