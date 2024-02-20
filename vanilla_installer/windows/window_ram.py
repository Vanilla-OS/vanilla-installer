# window_ram.py
#
# Copyright 2024 muhdsalm
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
import sys
import subprocess
from gi.repository import Adw, Gtk
from vanilla_installer.utils.recipe import RecipeLoader


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/window-ram.ui")
class VanillaRamWindow(Adw.Window):
    __gtype_name__ = "VanillaRamWindow"

    btn_continue = Gtk.Template.Child()
    description_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.description_label.set_label(_("Your computer does have enough RAM to run %s (minimum 4GB)") % RecipeLoader().raw['distro_name'])
        self.btn_continue.connect("clicked", self.__continue)

    def __continue(self, btn):
        subprocess.Popen("IGNORE_RAM=1 vanilla-installer", shell=True)
        sys.exit(0)
