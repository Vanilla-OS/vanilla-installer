# conn_check.py
#
# Copyright 2023 mirkobrombin
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

import logging
import os
from collections import OrderedDict
from gettext import gettext as _

from gi.repository import Adw, Gtk
from requests import Session

from vanilla_installer.utils.run_async import RunAsync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VanillaInstaller::Conn_Check")


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-conn-check.ui")
class VanillaDefaultConnCheck(Adw.Bin):
    __gtype_name__ = "VanillaDefaultConnCheck"

    btn_recheck = Gtk.Template.Child()
    status_page = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__step_num = step["num"]

        self.__ignore_callback = False

        # signals
        self.btn_recheck.connect("clicked", self.__on_btn_recheck_clicked)
        self.__window.carousel.connect("page-changed", self.__conn_check)
        self.__window.btn_back.connect(
            "clicked", self.__on_btn_back_clicked, self.__window.carousel.get_position()
        )

    @property
    def step_id(self):
        return self.__key

    def get_finals(self):
        return {}

    def __on_btn_back_clicked(self, data, idx):
        if idx + 1 != self.__step_num:
            return
        self.__ignore_callback = True

    def __conn_check(self, carousel=None, idx=None):
        if idx is not None and idx != self.__step_num:
            return

        def async_fn():
            if "VANILLA_SKIP_CONN_CHECK" in os.environ:
                return True

            try:
                s = Session()
                headers = OrderedDict(
                    {
                        "Accept-Encoding": "gzip, deflate, br",
                        "Host": "vanillaos.org",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
                    }
                )
                s.headers = headers
                s.get("https://vanillaos.org/", headers=headers, verify=True)
                return True
            except Exception as e:
                logger.error(f"Connection check failed: {str(e)}")
                return False

        def callback(res, *args):
            if self.__ignore_callback:
                self.__ignore_callback = False
                return

            if res:
                self.__window.next()
                return

            self.status_page.set_icon_name("network-wired-disconnected-symbolic")
            self.status_page.set_title(_("No Internet Connection!"))
            self.status_page.set_description(
                _("First Setup requires an active internet connection")
            )
            self.btn_recheck.set_visible(True)

        RunAsync(async_fn, callback)

    def __on_btn_recheck_clicked(self, widget, *args):
        widget.set_visible(False)
        self.status_page.set_icon_name("content-loading-symbolic")
        self.status_page.set_title(_("Checking Connection…"))
        self.status_page.set_description(
            _("Please wait until the connection check is done.")
        )
        self.__conn_check()
