# encryption.py
#
# Copyright 2024 mirkobrombin
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

from gi.repository import Adw, Gtk

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-encryption.ui")
class VanillaDefaultEncryption(Adw.Bin):
    __gtype_name__ = "VanillaDefaultEncryption"

    btn_next = Gtk.Template.Child()
    status_page = Gtk.Template.Child()

    use_encryption_switch = Gtk.Template.Child()

    encryption_pass_entry = Gtk.Template.Child()
    encryption_pass_entry_confirm = Gtk.Template.Child()

    password_filled = False

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        self.btn_next.connect("clicked", self.__window.next)
        self.use_encryption_switch.connect(
            "state-set", self.__on_encryption_switch_set)
        self.encryption_pass_entry.connect(
            "changed", self.__on_password_changed)
        self.encryption_pass_entry_confirm.connect(
            "changed", self.__on_password_changed
        )

        self.__update_btn_next()

    def get_finals(self):
        return {
            "encryption": {
                "use_encryption": self.use_encryption_switch.get_active(),
                "encryption_key": self.encryption_pass_entry.get_text(),
            }
        }

    def __on_encryption_switch_set(self, state, user_data):
        if self.use_encryption_switch.get_active():
            self.status_page.set_icon_name("changes-prevent-symbolic")
        else:
            self.status_page.set_icon_name("changes-allow-symbolic")

        self.__update_btn_next()

    def __on_password_changed(self, *args):
        password = self.encryption_pass_entry.get_text()
        if (
            password == self.encryption_pass_entry_confirm.get_text()
            and password.strip()
        ):
            self.password_filled = True
            self.encryption_pass_entry_confirm.remove_css_class("error")
        else:
            self.password_filled = False
            self.encryption_pass_entry_confirm.add_css_class("error")

        self.__update_btn_next()

    def __update_btn_next(self):
        rule = self.password_filled or self.use_encryption_switch.get_active() is False
        self.btn_next.set_sensitive(rule)
