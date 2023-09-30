# disk.py
#
# Copyright 2023 mirkobrombin
# Copyright 2023 matbme
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

import subprocess
from typing import Union
from gi.repository import Adw, GObject, Gtk

from vanilla_installer.defaults.disks.disk_default_page import DiskDefaultPage
from vanilla_installer.defaults.disks.disk_manual_page import DiskManualPage

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-disk.ui")
class VanillaDefaultDisk(Adw.Bin):
    __gtype_name__ = "VanillaDefaultDisk"

    btn_next = Gtk.Template.Child()
    btn_back = Gtk.Template.Child()
    subpage_btn_back = Gtk.Template.Child()

    mainpage = Gtk.Template.Child()
    mainleaflet = Gtk.Template.Child()

    default_install_togglebutton = Gtk.Template.Child()
    default_install_checkbutton = Gtk.Template.Child()
    default_install_btn_next = Gtk.Template.Child()

    manual_install_togglebutton = Gtk.Template.Child()
    manual_install_checkbutton = Gtk.Template.Child()
    manual_install_btn_next = Gtk.Template.Child()

    default_install_page = Gtk.Template.Child()
    manual_install_page = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # signals
        self.btn_back.connect("clicked", self.__window.back)
        self.subpage_btn_back.connect("clicked", self.__on_subpage_btn_back)
        self.default_install_checkbutton.connect("toggled", self.__on_install_choice_toggled)
        self.default_install_btn_next.connect("clicked", self.__on_default_install_subpage_clicked)
        self.default_install_togglebutton.connect("toggled", self.__on_default_install_toggled)
        self.manual_install_togglebutton.connect("toggled", self.__on_manual_install_toggled)
        self.manual_install_checkbutton.connect("toggled", self.__on_install_choice_toggled)
        self.manual_install_btn_next.connect("clicked", self.__on_manual_install_subpage_clicked)

        self.mainleaflet.connect("notify::visible-child", self.__update_the_subpage_btn_back_state)

    def __update_the_subpage_btn_back_state(self, leaflet, subpage):
        is_not_main_page = self.mainleaflet.get_visible_child() != self.mainpage

        self.subpage_btn_back.set_visible(is_not_main_page)
        self.btn_back.set_visible(not is_not_main_page)

        self.default_install_btn_next.set_visible(not is_not_main_page)
        self.manual_install_btn_next.set_visible(not is_not_main_page)

        self.default_install_checkbutton.set_active(not is_not_main_page)
        self.manual_install_checkbutton.set_active(not is_not_main_page)

    def __on_subpage_btn_back(self, btn):
        is_main_page = self.mainleaflet.get_visible_child() == self.mainpage
        
        if not is_main_page:
            self.mainleaflet.navigate(Adw.NavigationDirection.BACK)

    def __on_default_install_toggled(self, btn):
        self.default_install_checkbutton.set_active(True)

    def __on_manual_install_toggled(self, btn):
        self.manual_install_checkbutton.set_active(True)

    def __on_install_choice_toggled(self, btn):
        self.default_install_btn_next.set_visible(self.default_install_checkbutton.get_active())
        self.manual_install_btn_next.set_visible(self.manual_install_checkbutton.get_active())

    def __on_default_install_subpage_clicked(self, btn):
        if self.default_install_btn_next.get_visible():
            if not self.default_install_page.get_first_child():
                default_install_page = DiskDefaultPage(self.__window, self)
                self.default_install_page.append(default_install_page)
            self.mainleaflet.set_visible_child(self.default_install_page)
            
    def __on_manual_install_subpage_clicked(self, btn):
        if self.manual_install_btn_next.get_visible():
            if not self.manual_install_page.get_first_child():
                manual_install_page = DiskManualPage(self.__window, self)
                self.manual_install_page.append(manual_install_page)
            self.mainleaflet.set_visible_child(self.manual_install_page)