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
from vanilla_installer.core.disks import Partition

logger = logging.getLogger("Installer::Processor")


AlbiusSetupStep = dict[str, Union[str, list[Any]]]
AlbiusMountpoint = dict[str, str]
AlbiusInstallation = dict[str, str]
AlbiusPostInstallStep = dict[str, Union[bool, str, list[Any]]]

_GRUB_SCRIPT_BASE = """#!/bin/sh
exec tail -n +3 $0
set menu_color_normal=white/black
set menu_color_highlight=black/light-gray
function gfxmode {
set gfxpayload="${1}"
if [ "${1}" = "keep" ]; then
        set vt_handoff=vt.handoff=7
else
        set vt_handoff=
fi
}
if [ "${recordfail}" != 1 ]; then
if [ -e ${prefix}/gfxblacklist.txt ]; then
    if [ ${grub_platform} != pc ]; then
    set linux_gfx_mode=keep
    elif hwmatch ${prefix}/gfxblacklist.txt 3; then
    if [ ${match} = 0 ]; then
        set linux_gfx_mode=keep
    else
        set linux_gfx_mode=text
    fi
    else
    set linux_gfx_mode=text
    fi
else
    set linux_gfx_mode=keep
fi
else
set linux_gfx_mode=text
fi
export linux_gfx_mode
"""

_GRUB_SCRIPT_MENU_ENTRY = """menuentry 'State %s' --class gnu-linux --class gnu --class os {
recordfail
load_video
gfxmode \$linux_gfx_mode
insmod gzio
if [ x\$grub_platform = xxen ]; then insmod xzio; insmod lzopio; fi
insmod part_gpt
insmod ext2
search --no-floppy --fs-uuid --set=root %s
linux	/vmlinuz-$KERNEL_VER root=%s quiet splash bgrt_disable \$vt_handoff
initrd  /initrd.img-%s
}
"""

class AlbiusRecipe:
    def __init__(self):
        self.setup: list[AlbiusSetupStep] = []
        self.mountpoints: list[AlbiusMountpoint] = []
        self.installation: AlbiusInstallation = {}
        self.postInstallation: list[AlbiusPostInstallStep] = []


class Processor:
    @staticmethod
    def __gen_auto_partition_steps(disk: str, encrypt: bool, password: str | None = None):
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

        # Should we encrypt?
        fs = "luks-btrfs" if encrypt else "btrfs"
        def _params(*args):
            base_params = [*args]
            if encrypt:
                assert isinstance(password, str)
                base_params.append(password)
            return base_params

        # Roots
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": _params("a", fs, part_offset, part_offset + 12288)
        })
        part_offset += 12288
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": _params("b", fs, part_offset, part_offset + 12288)
        })
        part_offset += 12288

        # Home
        info["setup"].append({
            "disk": disk,
            "operation": "mkpart",
            "params": _params("home", fs, part_offset, -1)
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
    def __gen_manual_partition_steps(disk_final: dict, encrypt: bool, password: str | None = None):
        info = {
            "setup": [],
            "mountpoints": [],
            "postInstall": []
        }

        # Since manual partitioning uses GParted to handle partitions (for now),
        # we don't need to create any partitions or label disks (for now).
        # But we still need to format partitions.
        for part, values in disk_final.items():
            part_disk = re.match(r"^/dev/[a-zA-Z]+([0-9]+[a-z][0-9]+)?", part, re.MULTILINE)[0]
            part_number = re.sub(r".*[a-z]([0-9]+)", r"\1", part)

            # Should we encrypt?
            operation = "luks-format" if encrypt and values["mp"] in ["/", "/home"] else "format"
            def _params(*args):
                base_params = [*args]
                if encrypt and values["mp"] in ["/", "/home"]:
                    assert isinstance(password, str)
                    base_params.append(password)
                return base_params

            info["setup"].append({
                "disk": part_disk,
                "operation": operation,
                "params": _params(part_number, values["fs"])
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

        return info

    @staticmethod
    def gen_install_recipe(log_path, finals, oci_image):
        logger.info("processing the following final data: %s", finals)

        recipe = AlbiusRecipe()

        # Setup encryption if user selected it
        encrypt = False
        password = None
        for final in finals:
            if "encryption" in final.keys():
                encrypt = final["encryption"]["use_encryption"]
                password = final["encryption"]["encryption_key"] if encrypt else None

        # Setup disks and mountpoints
        for final in finals:
            if "disk" in final.keys():
                if "auto" in final["disk"].keys():
                    info = Processor.__gen_auto_partition_steps(
                        final["disk"]["auto"]["disk"],
                        encrypt,
                        password
                    )
                else:
                    info = Processor.__gen_manual_partition_steps(
                        final["disk"],
                        encrypt,
                        password
                    )

                for step in info["setup"]:
                    recipe.setup.append(step)
                for mount in info["mountpoints"]:
                    recipe.mountpoints.append(mount)
                for step in info["postInstall"]:
                    recipe.postInstallation.append(step)

        # Installation
        recipe.installation = {
            "method": "oci",
            "source": oci_image
        }

        # Post-installation
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
            root_a_partition = None
            for mnt in recipe.mountpoints:
                if mnt["target"] == "/boot":
                    boot_partition = mnt["partition"]
                    boot_disk = re.match(r"^/dev/[a-zA-Z]+([0-9]+[a-z][0-9]+)?", mnt["partition"], re.MULTILINE)[0]
                elif mnt["target"] == "/":
                    if not root_a_partition:
                        root_a_partition = mnt["partition"]
                    else:
                        root_b_partition = mnt["partition"]

            # Add custom GRUB script
            with open("/tmp/10_vanilla_tmp", "w") as file:
                base_script_root = "/dev/mapper/luks-" if encrypt else "UUID="

                root_a_entry = _GRUB_SCRIPT_MENU_ENTRY % ("A", "$BOOT_UUID", "$ROOTA_UUID", "$KERNEL_VERSION")
                root_b_entry = _GRUB_SCRIPT_MENU_ENTRY % ("B", "$BOOT_UUID", "$ROOTB_UUID", "$KERNEL_VERSION")

                file.write(_GRUB_SCRIPT_BASE + root_a_entry + root_b_entry)

            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    f"BOOT_UUID=$(lsblk -d -n -o UUID {boot_partition}) \
                      ROOTA_UUID=$(lsblk -d -n -o UUID {root_a_partition}) \
                      ROOTB_UUID=$(lsblk -d -n -o UUID {root_b_partition}) \
                      KERNEL_VERSION=$(ls -1 /mnt/a/usr/lib/modules | sed '1p;d') \
                      envsubst < /tmp/10_vanilla_tmp > /tmp/10_vanilla"
                ]
            })
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "grub-add-script",
                "params": [ "/tmp/10_vanilla" ]
            })

            # Remove default GRUB scripts
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "grub-remove-script",
                "params": [
                    "10_linux",
                    "20_memtest86+"
                ]
            })

            # Remove B's fstab entry from A
            if encrypt:
                root_b_fstab_entry = "\\\/dev\\\/mapper\\\/luks-$ROOTB_UUID"
            else:
                root_b_fstab_entry = "UUID=$ROOTB_UUID"
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    f"ROOTB_UUID=$(lsblk -d -y -n -o UUID {root_b_partition}) sed -i \"/{root_b_fstab_entry}/d\" /mnt/a/etc/fstab"
                ]
            })

            # Install GRUB inside and outside of chroot (necessary for... reasons)
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "grub-install",
                "params": [
                    "/mnt/a/boot",
                    boot_disk,
                    "efi" if Systeminfo.is_uefi() else "bios"
                ]
            })
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "grub-install",
                "params": [
                    "/boot",
                    boot_disk,
                    "efi" if Systeminfo.is_uefi() else "bios"
                ]
            })

            # Set GRUB default config
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "grub-default-config",
                "params": [
                    "GRUB_DEFAULT=0",
                    "GRUB_TIMEOUT=0",
                    "GRUB_HIDDEN_TIMEOUT=2",
                    "GRUB_TIMEOUT_STYLE=hidden"
                ]
            })

            # Run grub-mkconfig
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "grub-mkconfig",
                "params": [
                    "/boot/grub/grub.cfg"
                ]
            })

            # Update initramfs
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "shell",
                "params": [
                    "update-initramfs -u"
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
