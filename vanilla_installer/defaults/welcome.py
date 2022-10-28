# welcome.py
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

import time
from gi.repository import Gtk, Gio, GLib, Adw

from vanilla_installer.utils.run_async import RunAsync


@Gtk.Template(resource_path='/io/github/vanilla-os/FirstSetup/gtk/default-welcome.ui')
class VanillaDefaultWelcome(Adw.Bin):
    __gtype_name__ = 'VanillaDefaultWelcome'

    btn_next = Gtk.Template.Child()
    status_page = Gtk.Template.Child()

    welcome = [
        'Welcome',
        'Benvenuto',
        'Bienvenido',
        'Bienvenue',
        'Willkommen',
        'Bem-vindo',
        'Добро пожаловать',
        '欢迎',
        'ようこそ',
        '환영합니다',
        'أهلا بك',
        'ברוך הבא',
        'Καλώς ήρθατε',
        'Hoşgeldiniz',
        'Welkom',
        'Witamy',
        'Välkommen',
        'Tervetuloa',
        'Vítejte',
        'Üdvözöljük',
        'Bun venit',
        'Vitajte',
        'Tere tulemast',
        'Sveiki atvykę',
        'Dobrodošli',
        'خوش آمدید',
        'आपका स्वागत है',
        'স্বাগতম',
        'வரவேற்கிறோம்',
        'స్వాగతం',
        'मुबारक हो',
        'સુસ્વાગત છે',
        'ಸುಸ್ವಾಗತ',
        'സ്വാഗതം'
    ]

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step

        # animation start
        self.__start_welcome_animation()

        # signals
        self.btn_next.connect("clicked", self.__window.next)

        # set distro logo
        self.status_page.set_icon_name(self.__distro_info["logo"])

    def __start_welcome_animation(self):
        def change_langs():
            while True:
                for lang in self.welcome:
                    GLib.idle_add(self.status_page.set_title, lang)
                    time.sleep(1.2)

        RunAsync(change_langs, None)

    def get_finals(self):
        return {}
