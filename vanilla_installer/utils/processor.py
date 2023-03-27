# processor.py
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
import uuid
import shutil
import logging
import tempfile
import subprocess
from glob import glob
import re
import json
from typing import Union, any

from gettext import gettext as _
from vanilla_installer.core.system import Systeminfo

logger = logging.getLogger("Installer::Processor")


AlbiusSetupStep = dict[str, Union[str, list[any]]]
AlbiusMountpoint = dict[str, str]
AlbiusInstallation = dict[str, str]
AlbiusPostInstallStep = dict[str, Union[bool, str, list[any]]]


class AlbiusRecipe:
    def __init__():
        self.setup: list[AlbiusSetupStep] = []
        self.mountpoints: list[AlbiusMountpoint] = []
        self.installation: AlbiusInstallation = {}
        self.postInstallation: list[AlbiusPostInstallStep] = []


class Processor:
    @staticmethod
    def gen_swap_size():
        """
        Reference: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/storage_administration_guide/ch-swapspace#doc-wrapper
        """
        mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        mem = mem / (1024.0**3)
        if mem <= 2:
            return int(mem * 3 * 1024)
        elif mem > 2 and mem <= 8:
            return int(mem * 2 * 1024)
        elif mem > 8 and mem <= 64:
            return int(mem * 1.5 * 1024)
        else:
            return 4096

    @staticmethod
    def gen_install_recipe(log_path, setup, post_install, finals):
        logger.info("processing the following final data: %s", finals)

        recipe = AlbiusRecipe()

        # Setup disks and mountpoints
        for final in finals:
            if "disk" in final.keys():
                disk_setup_step = {
                }

        # Installation
        # TODO: Add unsquashfs step with filesystem path

        # Post-installation
        # TODO: Add packageremove step (will point to .package_remove from /live)
        # TODO: Add hostname step (will always be "vanilla")
        # TODO: Read "timezone" key from finals
        # TODO: Read "language" key from finals
        # TODO: Read "keyboard" key from finals
        # TODO: Read "users" key from finals

        # Call installer
        # TODO: Spawn Albius

    @staticmethod
    def gen_install_script(log_path, pre_run, post_run, finals):
        logger.info("processing the following final data: %s", finals)

        # manifest_remove = "/cdrom/casper/filesystem.manifest-remove"
        # if not os.path.exists(manifest_remove):
        manifest_remove = "/tmp/filesystem.manifest-remove"
        with open(manifest_remove, "w") as f:
            f.write("vanilla-installer\n")
            f.write("gparted\n")

        arguments = [
            "sudo",
            "distinst",
            "-s",
            "'/cdrom/casper/filesystem.squashfs'",
            "-r",
            f"'{manifest_remove}'",
            "-h",
            "'vanilla'",
        ]

        is_almost_supported = shutil.which("almost")

        # post install variables
        device_block = ""
        finals_disk = {}
        finals_timezone = {}

        for final in finals:
            for key, value in final.items():
                if key == "users":
                    arguments = ["echo", f"'{value['password']}'", "|"] + arguments
                    arguments += ["--username", f"'{value['username']}'"]
                    arguments += ["--realname", f"'{value['fullname']}'"]
                    arguments += [
                        "--profile_icon",
                        "'/usr/share/pixmaps/faces/yellow-rose.jpg'",
                    ]
                elif key == "timezone":
                    arguments += [
                        "--tz",
                        "'{}/{}'".format(value["region"], value["zone"]),
                    ]
                    finals_timezone = final
                elif key == "language":
                    arguments += ["-l", f"'{value}'"]
                elif key == "keyboard":
                    arguments += ["-k", f"'{value}'"]
                elif key == "disk":
                    finals_disk = final
                    if "auto" in value:
                        device_block = value["auto"]["disk"]
                        arguments += ["-b", f"'{device_block}'"]
                        arguments += ["-t", f"'{device_block}:gpt'"]
                        arguments += [
                            "-n",
                            f"'{device_block}:primary:start:1024M:fat32:mount=/boot/efi:flags=esp'",
                        ]
                        arguments += [
                            "-n",
                            f"'{device_block}:primary:1024M:2048M:ext4:mount=/boot'",
                        ]
                        arguments += [
                            "-n",
                            f"'{device_block}:primary:2048M:22528M:btrfs:mount=/'",
                        ]
                        arguments += [
                            "-n",
                            f"'{device_block}:primary:22528M:43008M:btrfs:mount=/'",
                        ]
                        arguments += [
                            "-n",
                            f"'{device_block}:primary:43008M:end:btrfs:mount=/home'",
                        ]
                        # Add generated partitions to finals so abroot-adapter can find them
                        finals_disk["disk"]["disk"] = device_block
                        if not re.match(r"[0-9]", device_block[-1]):
                            partition_name = f"{device_block}"
                        else:
                            partition_name = f"{device_block}p"
                        finals_disk["disk"][f"{partition_name}1"] = {
                            "fs": "fat32",
                            "mp": "/boot/efi",
                        }
                        finals_disk["disk"][f"{partition_name}2"] = {
                            "fs": "ext4",
                            "mp": "/boot",
                        }
                        finals_disk["disk"][f"{partition_name}3"] = {
                            "fs": "btrfs",
                            "mp": "/",
                        }
                        finals_disk["disk"][f"{partition_name}4"] = {
                            "fs": "btrfs",
                            "mp": "/",
                        }
                        finals_disk["disk"][f"{partition_name}5"] = {
                            "fs": "btrfs",
                            "mp": "/home",
                        }
                    else:
                        device_block = value["disk"]
                        for partition, values in value.items():
                            if partition == "disk":
                                arguments += ["-b", f"'{values}'"]
                                continue

                            partition_number = re.sub(r".*[a-z]([0-9]+)", r"\1", partition)
                            if values["mp"] == "/boot/efi":
                                arguments += [
                                    "-u",
                                    "'{}:{}:{}:mount=/boot/efi:flags=esp'".format(
                                        device_block, partition_number, values["fs"]
                                    ),
                                ]
                            elif values["mp"] == "swap":
                                arguments += [
                                    "-u",
                                    f"'{device_block}:{partition_number}:swap'",
                                ]
                            elif values["mp"] == "":
                                arguments += [
                                    "-u",
                                    "'{}:{}:{}:flags=bios_grub'".format(
                                        device_block,
                                        partition_number,
                                        values["fs"],
                                    ),
                                ]
                            else:
                                arguments += [
                                    "-u",
                                    "'{}:{}:{}:mount={}'".format(
                                        device_block,
                                        partition_number,
                                        values["fs"],
                                        values["mp"],
                                    ),
                                ]

        # generating a temporary file to store the distinst command and
        # arguments parsed from the final data
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("#!/bin/sh\n")
            f.write("# This file was created by the Vanilla Installer.\n")
            f.write("# Do not edit this file manually!\n\n")

            if is_almost_supported:
                f.write("almost enter rw\n")

            f.write("set -e -x\n\n")

            if "VANILLA_FAKE" in os.environ:
                logger.info("VANILLA_FAKE is set, skipping the installation process.")
                f.write(
                    "echo 'VANILLA_FAKE is set, skipping the installation process.'\n"
                )
                f.write("echo 'Printing the configuration instead:'\n")
                f.write("echo '----------------------------------'\n")
                f.write(f'echo "{finals}"\n')
                f.write("echo '----------------------------------'\n")
                f.write("sleep 5\n")
                f.write("exit 1\n")

            if "VANILLA_SKIP_INSTALL" not in os.environ:
                for arg in arguments:
                    f.write(arg + " ")

            if "VANILLA_SKIP_POSTINSTALL" not in os.environ:
                f.write("\n")
                f.write("echo 'Starting the post-installation process ...'\n")
                f.write(
                    "sudo abroot-adapter '{}' '{}'".format(
                        json.dumps(finals_disk), json.dumps(finals_timezone)
                    )
                )

            f.flush()
            f.close()

            # setting the file executable
            os.chmod(f.name, 0o755)

            return f.name
