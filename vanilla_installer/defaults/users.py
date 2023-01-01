# users.py
#
# Copyright 2022 mirkobrombin
# Copyright 2022 muqtadir
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

import sys
import time
import re, subprocess, shutil
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/default-users.ui')
class VanillaDefaultUsers(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultUsers'

    btn_next = Gtk.Template.Child()
    fullname_entry = Gtk.Template.Child()
    username_entry = Gtk.Template.Child()
    password_entry = Gtk.Template.Child()
    password_confirmation = Gtk.Template.Child()

    fullname = ""
    fullname_filled = False
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
        self.fullname_entry.connect('changed', self.__on_fullname_entry_changed)
        self.username_entry.connect('changed', self.__on_username_entry_changed)
        self.password_entry.connect('changed', self.__on_password_changed)
        self.password_confirmation.connect('changed', self.__on_password_changed)

    def get_finals(self):
        return {
            "users": {
                "fullname": self.fullname,
                "username": self.username,
                "password": self.password_entry.get_text()
            }
        }

    def __on_fullname_entry_changed(self, *args):
        _fullname = self.fullname_entry.get_text()
        
        if len(_fullname) > 32:
            self.fullname_entry.set_text(_fullname[:32])
            self.fullname_entry.set_position(-1)
            _fullname = self.fullname_entry.get_text()

        self.fullname_filled = True
        self.__verify_continue()
        self.fullname = _fullname
    
    def __on_username_entry_changed(self, *args):
        _input = self.username_entry.get_text()
        _status = True

        # cannot be longer than 32 characters
        if len(_input) > 32:
            self.username_entry.set_text(_input[:32])
            self.username_entry.set_position(-1)
            _input = self.username_entry.get_text()
            
        # cannot contain special characters
        if re.search(r'[^a-z0-9]', _input):
            _status = False
            self.__window.toast("Username cannot contain special characters or uppercase letters. Please choose another username.")

        # cannot be empty
        elif not _input:
            _status = False
            self.__window.toast("Username cannot be empty. Please type a username.")

        # cannot be root
        elif _input == "root":
            _status = False
            self.__window.toast("root user is reserved. Please choose another username.")

        if not _status:
            self.username_entry.add_css_class('error')
            self.username_filled = False
            self.__verify_continue()
        else:
            self.username_entry.remove_css_class('error')
            self.username_filled = True
            self.__verify_continue()
            self.username = _input


    def __on_password_changed(self, *args):
        password = self.password_entry.get_text()
        if password == self.password_confirmation.get_text() \
                and password.strip():
            self.password_filled = True;
            self.password_confirmation.remove_css_class('error')
            self.password = self.__encrypt_password(password)
        else:
            self.password_filled = False;
            self.password_confirmation.add_css_class('error')

        self.__verify_continue();

    def __verify_continue(self):
        self.btn_next.set_sensitive(self.fullname_filled and self.password_filled and self.username_filled)

    def __encrypt_password(self, password):
        command = subprocess.run(
            [shutil.which("openssl"), "passwd", "-crypt", password], 
            capture_output=True
        )
        password_encrypted = command.stdout.decode('utf-8').strip('\n')
        return password_encrypted
        
