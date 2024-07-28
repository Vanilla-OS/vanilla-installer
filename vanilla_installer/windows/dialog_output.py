# dialog.py
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

from gettext import gettext as _

from gi.repository import Adw, GObject, Gtk


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/dialog-output.ui")
class VanillaDialogOutput(Adw.Dialog):
    __gtype_name__ = "VanillaDialogOutput"

    main_box = Gtk.Template.Child()

    def __init__(self, terminal, **kwargs):
        super().__init__(**kwargs)

        self.main_box.append(terminal)
