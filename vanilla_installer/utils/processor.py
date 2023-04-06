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
from typing import Union, Any

from gettext import gettext as _
from vanilla_installer.core.system import Systeminfo

logger = logging.getLogger("Installer::Processor")


AlbiusSetupStep = dict[str, Union[str, list[Any]]]
AlbiusMountpoint = dict[str, str]
AlbiusInstallation = dict[str, str]
AlbiusPostInstallStep = dict[str, Union[bool, str, list[Any]]]


class AlbiusRecipe:
    def __init__(self):
        self.setup: list[AlbiusSetupStep] = []
        self.mountpoints: list[AlbiusMountpoint] = []
        self.installation: AlbiusInstallation = {}
        self.postInstallation: list[AlbiusPostInstallStep] = []


class Processor:
    @staticmethod
    def __gen_auto_partition_steps(disk):
        info = {
            "setup": [],
            "mountpoints": [],
            "postInstall": []
        }

        info["setup"].append({
            "disk": disk,
            "operation": "label",
            "params": ["gpt"]
        })

        # Boot
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": ["boot", "ext4", 1, 1025]
        })

        if Systeminfo.is_uefi():
            info["setup"].append({
                "disk": disk,
                "operation": "mkpart",
                "params": ["EFI", "fat32", 1025, 1537]
            })
            part_offset = 1537
        else:
            info["setup"].append({
                "disk": disk,
                "operation": "mkpart",
                "params": ["BIOS", "fat32", 1025, 1026]
            })
            info["setup"].append({
                "disk": disk,
                "operation": "setflag",
                "params": ["2", "bios_grub", True]
            })
            part_offset = 1026

        # Roots
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": ["a", "btrfs", part_offset, part_offset + 12288]
        })
        part_offset += 12288
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": ["b", "btrfs", part_offset, part_offset + 12288]
        })
        part_offset += 12288

        # Home
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": ["home", "btrfs", part_offset, -1]
        })

        # Mountpoints
        if not re.match(r"[0-9]", disk[-1]):
            part_prefix = f"{disk}"
        else:
            part_prefix = f"{disk}p"

        info["mountpoints"].append({
            "partition": part_prefix + "1",
            "target": "/boot"
        })

        if Systeminfo.is_uefi():
            info["mountpoints"].append({
                "partition": part_prefix + "2",
                "target": "/boot/efi"
            })

        info["mountpoints"].append({
            "partition": part_prefix + "3",
            "target": "/"
        })
        info["mountpoints"].append({
            "partition": part_prefix + "4",
            "target": "/"
        })

        info["mountpoints"].append({
            "partition": part_prefix + "5",
            "target": "/home"
        })

        return info

    @staticmethod
    def __gen_manual_partition_steps(disk_final):
        info = {
            "setup": [],
            "mountpoints": [],
            "postInstall": []
        }

        # Since manual partitioning uses GParted to handle partitions (for now),
        # we don't need to create any partitions or label disks (for now).
        # But we still need to format partitions.
        for part, values in disk_final:
            part_disk = re.match("^/dev/[a-zA-Z]+([0-9]+[a-z][0-9]+)?", part, re.MULTILINE)
            part_number = re.match("[0-9]+$", part, re.MULTILINE)
            info["setup"].append({
                "disk": part_disk,
                "operation": "format",
                "params": [part_number, values["fs"]]
            })

            if not Systeminfo.is_uefi() and values["mp"] == "":
                info["setup"].append({
                    "disk": part_disk,
                    "operation": "setflag",
                    "params": [part_number, "bios_grub", True]
                })

            if values["mp"] == "swap":
                info["postInstall"].append({
                    "chroot": True,
                    "operation": "swapon",
                    "params": [part]
                })
            else:
                info["mountpoints"].append({
                    "partition": part,
                    "target": values["mp"]
                })

    @staticmethod
    def gen_install_recipe(log_path, finals):
        logger.info("processing the following final data: %s", finals)

        recipe = AlbiusRecipe()

        # Setup disks and mountpoints
        for final in finals:
            if "disk" in final.keys():
                if "auto" in final["disk"].keys():
                    info = Processor.__gen_auto_partition_steps(final["disk"]["auto"]["disk"])
                else:
                    info = Processor.__gen_manual_partition_steps(final["disk"])

                for step in info["setup"]:
                    recipe.setup.append(step)
                for mount in info["mountpoints"]:
                    recipe.mountpoints.append(mount)
                for step in info["postInstall"]:
                    recipe.postInstallation.append(step)

        # Installation
        recipe.installation = {
            "method": "oci",
            "source": "registry.vanillaos.org/vanillaos/desktop:main"
        }

        # Post-installation
        # Remove unnecessary packages
        manifest_remove = "/tmp/filesystem.manifest-remove"
        with open(manifest_remove, "w") as f:
            f.write("vanilla-installer\n")
            f.write("gparted\n")
        recipe.postInstallation.append({
            "chroot": True,
            "operation": "pkgremove",
            "params": [
                manifest_remove,
                "apt remove -y"
            ]
        })
        # Set hostname
        recipe.postInstallation.append({
            "chroot": True,
            "operation": "hostname",
            "params": ["vanilla"]
        })
        for final in finals:
            for key, value in final.items():
                # Set timezone
                if key == "timezone":
                    recipe.postInstallation.append({
                        "chroot": True,
                        "operation": "timezone",
                        "params": [f"{value['region']}/{value['zone']}"]
                    })
                # Set locale
                if key == "language":
                    recipe.postInstallation.append({
                        "chroot": True,
                        "operation": "locale",
                        "params": [value]
                    })
                # Add user
                if key == "users":
                    recipe.postInstallation.append({
                        "chroot": True,
                        "operation": "adduser",
                        "params": [
                            value["username"],
                            value["fullname"],
                            ["sudo", "lpadmin"],
                            value["password"]
                        ]
                    })
                # Set keyboard
                if key == "keyboard":
                    recipe.postInstallation.append({
                        "chroot": True,
                        "operation": "keyboard",
                        "params": [
                            value["layout"],
                            value["model"],
                            value["variant"],
                        ]
                    })

        if "VANILLA_SKIP_POSTINSTALL" not in os.environ:
            # OCI post-installation script
            # Arguments: disk boot efi rootA rootB
            oci_cmd_args = [None] * 5
            for mnt in recipe.mountpoints:
                if mnt["target"] == "/boot":
                    boot_disk = re.match("^/dev/[a-zA-Z]+([0-9]+[a-z][0-9]+)?", mnt["partition"], re.MULTILINE)
                    oci_cmd_args[0] = boot_disk[0]
                    oci_cmd_args[1] = mnt["partition"]
                elif mnt["target"] == "/boot/efi":
                    oci_cmd_args[2] = mnt["partition"]
                elif mnt["target"] == "/":
                    if not oci_cmd_args[3]:
                        oci_cmd_args[3] = mnt["partition"]
                    else:
                        oci_cmd_args[4] = mnt["partition"]

            # Handle BIOS installation option
            if not oci_cmd_args[2]:
                oci_cmd_args[2] = "BIOS"

            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    f"oci-post-install {' '.join(oci_cmd_args)}"
                ]
            })

        if "VANILLA_FAKE" in os.environ:
            logger.info("VANILLA_FAKE is set, skipping the installation process.")
            logger.info(json.dumps(recipe, default=vars))
            return None

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(json.dumps(recipe, default=vars))

            f.flush()
            f.close()

            # setting the file executable
            os.chmod(f.name, 0o755)

            return f.name
