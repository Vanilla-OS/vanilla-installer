# main.py
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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GnomeDesktop", "4.0")
gi.require_version("GWeather", "4.0")
gi.require_version("Vte", "3.91")
gi.require_version("NM", "1.0")
gi.require_version("NMA4", "1.0")

import logging
import sys
from gettext import gettext as _
import os

from gi.repository import Adw, Gio

from vanilla_installer.windows.main_window import VanillaWindow
from vanilla_installer.windows.window_unsupported import VanillaUnsupportedWindow
from vanilla_installer.windows.window_ram import VanillaRamWindow
from vanilla_installer.windows.window_cpu import VanillaCpuWindow
from vanilla_installer.core.system import Systeminfo


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Installer::Main")


class VanillaInstaller(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="org.vanillaos.Installer",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.create_action("quit", self.close, ["<primary>q"])

    def do_activate(self):
        """
        Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.

        """

        win = self.props.active_window
        if not win:
            if "IGNORE_RAM" not in os.environ and not Systeminfo.is_ram_enough():
                win = VanillaRamWindow(application=self)  # Not enough RAM
            elif "IGNORE_CPU" not in os.environ and not Systeminfo.is_cpu_enough():
                win = VanillaCpuWindow(application=self)  # Not enough CPU
            elif not Systeminfo.is_uefi():
                win = VanillaUnsupportedWindow(application=self)  # Not UEFI
            else:
                logger.info("Creating main window")
                win = VanillaWindow(application=self)  # All good
                logger.info("Main window created")
        win.present()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def close(self, *args):
        """Close the application."""
        self.quit()


def main(version):
    """The application's entry point."""
    app = VanillaInstaller()
    return app.run(sys.argv)
