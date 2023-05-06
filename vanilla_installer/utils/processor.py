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
import logging
import tempfile
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

_BASE_DIRS = ["boot", "dev", "home", "media", "mnt", "var", "opt",
              "part-future", "proc", "root", "run", "srv", "sys", "tmp"]
_REL_LINKS = ["usr", "etc", "usr/bin", "usr/lib",
              "usr/lib32", "usr/lib64", "usr/libx32", "usr/sbin"]
_REL_SYSTEM_LINKS = ["dev", "proc", "run",
                     "srv", "sys", "tmp", "media", "boot"]

_ROOT_GRUB_CFG = """insmod gzio
insmod part_gpt
insmod ext2
search --no-floppy --fs-uuid --set=root %s
linux   /.system/boot/vmlinuz-%s root=%s quiet splash bgrt_disable $vt_handoff
initrd  /.system/boot/initrd.img-%s
"""

_BOOT_GRUB_CFG = """set default=0
set timeout=5

menuentry "ABRoot A (current)" --class abroot-a {
    set root=%s
    configfile "/.system/boot/grub/abroot.cfg"
}

menuentry "ABRoot B (previous)" --class abroot-b {
    set root=%s
    configfile "/.system/boot/grub/abroot.cfg"
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
            "params": _params("var", fs, part_offset, -1)
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
            "target": "/var"
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
            operation = "luks-format" if encrypt and values["mp"] in ["/", "/var"] else "format"
            def _params(*args):
                base_params = [*args]
                if encrypt and values["mp"] in ["/", "/var"]:
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
            efi_partition = None
            for mnt in recipe.mountpoints:
                if mnt["target"] == "/boot":
                    boot_partition = mnt["partition"]
                    boot_disk = re.match(r"^/dev/[a-zA-Z]+([0-9]+[a-z][0-9]+)?", mnt["partition"], re.MULTILINE)[0]
                elif mnt["target"] == "/boot/efi":
                    efi_partition = mnt["partition"]
                elif mnt["target"] == "/":
                    if not root_a_partition:
                        root_a_partition = mnt["partition"]
                    else:
                        root_b_partition = mnt["partition"]
                elif mnt["target"] == "/var":
                    var_partition = mnt["partition"]

            # Adapt root A filesystem structure
            if encrypt:
                var_label = f"/dev/mapper/luks-$(lsblk -d -y -n -o UUID {var_partition})"
            else:
                var_label = var_partition
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    "umount /mnt/a/var",
                    f"umount -l {boot_partition}",
                    "mkdir -p /mnt/a/.system",
                    "mv /mnt/a/* /mnt/a/.system/",
                    *[f"mkdir -p /mnt/a/{path}" for path in _BASE_DIRS],
                    *[f"ln -rs /mnt/a/.system/{path} /mnt/a/" for path in _REL_LINKS],
                    *[f"rm -rf /mnt/a/.system/{path}" for path in _REL_SYSTEM_LINKS],
                    *[f"ln -rs /mnt/a/{path} /mnt/a/.system/" for path in _REL_SYSTEM_LINKS],
                    f"mount {var_label} /mnt/a/var",
                    f"mount {boot_partition} /mnt/a/boot{f' && mount {efi_partition} /mnt/a/boot/efi' if efi_partition else ''}",
                ]
            })

            # Run `grub-install` with the boot partition as target
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

            # Run `grub-mkconfig` to generate files for the boot partition
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "grub-mkconfig",
                "params": [
                    "/boot/grub/grub.cfg"
                ]
            })

            # Replace main GRUB entry in the boot partition
            with open("/tmp/boot-grub.cfg", "w") as file:
                base_script_root = "/dev/mapper/luks-" if encrypt else "UUID="
                boot_entry = _BOOT_GRUB_CFG % (
                    f"{base_script_root}$ROOTA_UUID",
                    f"{base_script_root}$ROOTB_UUID"
                )
                file.write(boot_entry)
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    " ".join(
                        f"ROOTA_UUID=$(lsblk -d -n -o UUID {root_a_partition}) \
                        ROOTB_UUID=$(lsblk -d -n -o UUID {root_b_partition}) \
                        envsubst < /tmp/boot-grub.cfg > /mnt/a/boot/grub/grub.cfg \
                        '$ROOTA_UUID $ROOTB_UUID'".split()
                    )
                ]
            })

            # Unmount boot partition so we can modify the root GRUB config
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    "umount -l /mnt/a/boot",
                    "mkdir -p /mnt/a/boot/grub"
                ]
            })

            # Run `grub-mkconfig` inside the root partition
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "grub-mkconfig",
                "params": [
                    "/boot/grub/grub.cfg"
                ]
            })

            # Add `/boot/grub/abroot.cfg` to the root partition
            with open("/tmp/abroot.cfg", "w") as file:
                base_script_root = "/dev/mapper/luks-" if encrypt else "UUID="
                root_entry = _ROOT_GRUB_CFG % (
                    "$BOOT_UUID",
                    "$KERNEL_VERSION",
                    f"{base_script_root}$ROOTA_UUID",
                    "$KERNEL_VERSION"
                )
                file.write(root_entry)
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    " ".join(
                        f"BOOT_UUID=$(lsblk -d -n -o UUID {boot_partition}) \
                        ROOTA_UUID=$(lsblk -d -n -o UUID {root_a_partition}) \
                        KERNEL_VERSION=$(ls -1 /mnt/a/usr/lib/modules | sed '1p;d') \
                        envsubst < /tmp/abroot.cfg > /mnt/a/boot/grub/abroot.cfg \
                        '$BOOT_UUID $ROOTA_UUID $KERNEL_VERSION'".split()
                    )
                ]
            })

            # Keep only root A entry in fstab
            if encrypt:
                root_b_fstab_entry = "\\\/dev\\\/mapper\\\/luks-$ROOTB_UUID"
            else:
                root_b_fstab_entry = "UUID=$ROOTB_UUID"
            recipe.postInstallation.append({
                "chroot": False,
                "operation": "shell",
                "params": [
                    f"ROOTB_UUID=$(lsblk -d -y -n -o UUID {root_b_partition}) && sed -i \"/{root_b_fstab_entry}/d\" /mnt/a/etc/fstab",
                    "sed -i -r '/^[^#]\S+\s+\/\S+\s+.+$/d' /mnt/a/etc/fstab"
                ]
            })

            # Mount `/etc` as overlay; `/home`, `/opt` and `/usr` as bind
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "shell",
                "params": [
                    "mv /.system/home /var",
                    "mv /.system/opt /var",
                    "mkdir -p /var/lib/abroot/etc/a /var/lib/abroot/etc/b /var/lib/abroot/etc/a-work /var/lib/abroot/etc/b-work",
                    "mount -t overlay overlay -o lowerdir=/.system/etc,upperdir=/var/lib/abroot/etc/a,workdir=/var/lib/abroot/etc/a-work /etc",
                    "mount -o bind /var/home /home",
                    "mount -o bind /var/opt /opt",
                    "mount -o bind,ro /.system/usr /usr"
                ]
            })
            # Exec the systemd thing
            # recipe.postInstallation.append({
            #     "chroot": True,
            #     "operation": "shell",
            #     "params": [
            #         "exec /lib/systemd/systemd",
            #     ]
            # })

            # Update initramfs
            recipe.postInstallation.append({
                "chroot": True,
                "operation": "shell",
                "params": [
                    "umount -l /usr",
                    "pkg-unlock",
                    "update-initramfs -u"
                    "pkg-lock",
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
