# users.py
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
import re, subprocess, shutil
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-users.ui')
class VanillaDefaultUsers(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultUsers'

    btn_next = Gtk.Template.Child()
    username_entry = Gtk.Template.Child()
    password_entry = Gtk.Template.Child()
    password_confirmation = Gtk.Template.Child()

    username = ""
    username_filled = False
    password_filled = False


    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # signals
        self.btn_next.connect("clicked", self.__window.next)
        self.username_entry.connect('changed', self.username_passes_regex)
        self.password_entry.connect('changed', self.verify_password)
        self.password_confirmation.connect('changed', self.verify_password)

    def username_passes_regex(self, widget):
        input = self.username_entry.get_text()
        print(input)
        if not re.search("^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$", input):
            print("Invalid username!")
            self.username_entry.add_css_class('error')
            self.username_filled = False
            self.verify_continue()
        else:
            print("Valid username!")
            self.username_entry.remove_css_class('error')
            self.username_filled = True
            self.verify_continue()
            self.username = input

    def verify_password(self, widget):
        if self.password_entry.get_text() == self.password_confirmation.get_text() and self.password_entry.get_text().strip():
            #self.btn_next.set_sensitive(True)
            self.password_filled = True;
            self.verify_continue();
            self.password_confirmation.remove_css_class('error')
            self.password = self.encrypt_password(self.password_entry.get_text())
        else:
            self.password_filled = False;
            self.verify_continue();
            self.password_confirmation.add_css_class('error')

    def verify_continue(self):
        if self.password_filled and self.username_filled:
            self.btn_next.set_sensitive(True)
        else:
            self.btn_next.set_sensitive(False)

    def encrypt_password(self, password):
        command=subprocess.run([shutil.which("openssl"), "passwd", "-crypt", password], capture_output=True)
        password_encrypted=command.stdout.decode('utf-8').strip('\n')
        return password_encrypted
        
