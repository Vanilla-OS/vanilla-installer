# main.py
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

import os
import gi
import sys
import logging
from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GnomeDesktop', '4.0')
gi.require_version('GWeather', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import Gtk, Gdk, Gio, Adw
from vanilla_installer.windows.main_window import VanillaWindow


logging.basicConfig(level=logging.INFO)


class FirstSetupApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='org.vanillaos.Installer',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action('quit', self.close, ['<primary>q'])

    def do_activate(self):
        """
        Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.

        --

        CSS inspired by: Sonny Piers <https://github.com/sonnyp>
        """
        css = """
.vte-console {
    background-color: #000000;
    border-radius: 12px;
}
.theme-selector {
    border-radius: 100px;
    margin: 8px;
    border: 1px solid rgba(145, 145, 145, 0.1);
    padding: 30px;
}
.theme-selector radio {
    -gtk-icon-source: none;
    border: none;
    background: none;
    box-shadow: none;
    min-width: 12px;
    min-height: 12px;
    transform: translate(34px, 20px);
    padding: 2px;
    border-radius: 100px;
}
.theme-selector radio:checked {
  -gtk-icon-source: -gtk-icontheme("object-select-symbolic");
  background-color: @theme_selected_bg_color;
  color: @theme_selected_fg_color;
}
.theme-selector:checked {
    border-color: @theme_selected_bg_color;
    border-width: 2px;
    background-color: @theme_selected_bg_color;
}
.theme-selector.light {
    background-color: #ffffff;
}
.theme-selector.dark {
    background-color: #202020;
}
.theme-selector.light:checked {
    background-color: #eeeeee;
}
.theme-selector.dark:checked {
    background-color: #303030;
}
"""
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            display=Gdk.Display.get_default(),
            provider=provider,
            priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        win = self.props.active_window
        if not win:
            win = VanillaWindow(application=self)
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
    app = FirstSetupApplication()
    return app.run(sys.argv)
