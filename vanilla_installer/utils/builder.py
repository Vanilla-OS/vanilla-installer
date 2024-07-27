# builder.py
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

import logging
import os
import subprocess
import sys
from gettext import gettext as _

from vanilla_installer.defaults.conn_check import VanillaDefaultConnCheck
from vanilla_installer.defaults.disk import VanillaDefaultDisk
from vanilla_installer.defaults.encryption import VanillaDefaultEncryption
from vanilla_installer.defaults.image import VanillaDefaultImage
from vanilla_installer.defaults.keyboard import VanillaDefaultKeyboard
from vanilla_installer.defaults.language import VanillaDefaultLanguage
from vanilla_installer.defaults.network import VanillaDefaultNetwork
from vanilla_installer.defaults.nvidia import VanillaDefaultNvidia
from vanilla_installer.defaults.vm import VanillaDefaultVm
from vanilla_installer.defaults.timezone import VanillaDefaultTimezone
from vanilla_installer.defaults.welcome import VanillaDefaultWelcome
from vanilla_installer.layouts.preferences import VanillaLayoutPreferences
from vanilla_installer.layouts.yes_no import VanillaLayoutYesNo
from vanilla_installer.utils.recipe import RecipeLoader

logger = logging.getLogger("Installer::Builder")


templates = {
    "network": VanillaDefaultNetwork,
    "conn-check": VanillaDefaultConnCheck,
    "welcome": VanillaDefaultWelcome,
    "language": VanillaDefaultLanguage,
    "keyboard": VanillaDefaultKeyboard,
    "timezone": VanillaDefaultTimezone,
    "preferences": VanillaLayoutPreferences,
    "disk": VanillaDefaultDisk,
    "encryption": VanillaDefaultEncryption,
    "image": VanillaDefaultImage,
    "nvidia": VanillaDefaultNvidia,
    "vm": VanillaDefaultVm,
    "yes-no": VanillaLayoutYesNo,
}


class Builder:
    def __init__(self, window):
        self.__window = window
        self.__recipe = RecipeLoader()
        self.__register_widgets = []
        self.__register_finals = []
        self.__property_list = []
        self.__load()

    def __load(self):
        if "VANILLA_FAKE" in os.environ:
            logger.info("VANILLA_FAKE is set, skipping the installation process.")

        self.__window.recipe = self.recipe

        # here we create a temporary file to store the output of the commands
        # the log path is defined in the recipe
        if "log_file" not in self.__recipe.raw:
            logger.critical(_("Missing 'log_file' in the recipe."))
            sys.exit(1)

        log_path = self.__recipe.raw["log_file"]

        if not os.path.exists(log_path):
            try:
                open(log_path, "a").close()
            except OSError:
                logger.warning(_("failed to create log file: %s") % log_path)
                logging.warning(_("No log will be stored."))

        for i, (key, step) in enumerate(self.__recipe.raw["steps"].items()):
            logger.info(_("(%s) Processing step...") % key)

            if step.get("display-conditions"):
                _condition_met = False
                logger.info(_("(%s) Display-conditions found") % key)

                for command in step["display-conditions"]:
                    try:
                        logger.info(
                            _("(%s) Performing display-condition: %s") % (key, command)
                        )
                        output = subprocess.check_output(
                            command, shell=True, stderr=subprocess.STDOUT
                        )
                        if (
                            output.decode("utf-8") == ""
                            or output.decode("utf-8") == "1"
                        ):
                            logger.info(_("(%s) Display-conditions not met") % key)
                            break
                        logger.info(_("(%s) Display-conditions met") % key)
                    except subprocess.CalledProcessError:
                        logger.info(
                            _("Step %s skipped due to display-conditions") % key
                        )
                        break
                else:
                    _condition_met = True

                if not _condition_met:
                    continue

            if step["template"] in templates:
                logger.info(
                    _("(%s) Initializing widgets for template: %s")
                    % (key, step["template"])
                )
                step["num"] = i
                _widget = templates[step["template"]](
                    self.__window, self.distro_info, key, step
                )
                logger.info(_("(%s) Widgets initialized") % key)
                self.__register_widgets.append(_widget)
            self.__property_list.append(step)

    def get_finals(self):
        self.__register_finals = []

        for widget in self.__register_widgets:
            self.__register_finals.append(widget.get_finals())

        return self.__register_finals

    @property
    def widgets(self):
        return self.__register_widgets

    @property
    def recipe(self):
        return self.__recipe.raw

    @property
    def property_list(self):
        return self.__property_list

    @property
    def distro_info(self):
        return {
            "name": self.__recipe.raw["distro_name"],
            "logo": self.__recipe.raw["distro_logo"],
        }
