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
import shutil
import logging
import tempfile
import subprocess
from glob import glob


logger = logging.getLogger("Installer::Processor")


class Processor:

    @staticmethod
    def gen_swap_size():
        """
        Reference: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/storage_administration_guide/ch-swapspace#doc-wrapper
        """
        mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        mem = mem / (1024.0 ** 3)
        if mem <= 2:
            return int(mem * 3 * 1024)
        elif mem > 2 and mem <= 8:
            return int(mem * 2 * 1024)
        elif mem > 8 and mem <= 64:
            return int(mem * 1.5 * 1024)
        else:
            return 4096

    @staticmethod
    def gen_install_script(log_path, pre_run, post_run, finals):
        logger.info("processing the following final data: %s", finals)

        #manifest_remove = "/cdrom/casper/filesystem.manifest-remove"
        #if not os.path.exists(manifest_remove):
        manifest_remove = "/tmp/filesystem.manifest-remove"
        with open(manifest_remove, "w") as f:
            f.write("vanilla-installer\n")
            f.write("gparted\n")

        arguments = [
            "sudo", "distinst",
            "-s", "'/cdrom/casper/filesystem.squashfs'",
            "-r", f"'{manifest_remove}'",
            "-h", "'vanilla'",
        ]

        is_almost_supported = shutil.which("almost")

        for final in finals:
            for key, value in final.items():
                if key == "users":
                    arguments = ["echo", f"'{value['password']}'", "|"] + arguments
                    arguments += ["--username", f"'{value['username']}'"]
                    arguments += ["--realname", f"'{value['fullname']}'"]
                    arguments += ["--profile_icon", "'/usr/share/pixmaps/faces/yellow-rose.jpg'"]
                elif key == "timezone":
                    arguments += ["--tz", "'{}/{}'".format(value["region"], value["zone"])]
                elif key == "language":
                    arguments += ["-l", f"'{value}'"]
                elif key == "keyboard":
                    arguments += ["-k", f"'{value}'"]
                elif key == "disk":
                    if "auto" in value:
                        arguments += ["-b", f"'{value['auto']['disk']}'"]
                        arguments += ["-t", "'{}:gpt'".format(value["auto"]["disk"])]
                        arguments += ["-n", "'{}:primary:start:1024M:fat32:mount=/boot/efi:flags=esp'".format(value["auto"]["disk"])]
                        arguments += ["-n", "'{}:primary:1024M:2048M:ext4:mount=/boot'".format(value["auto"]["disk"])]
                        arguments += ["-n", "'{}:primary:2048M:22528M:btrfs:mount=/'".format(value["auto"]["disk"])]
                        arguments += ["-n", "'{}:primary:22528M:43008M:btrfs:mount=/'".format(value["auto"]["disk"])]
                        arguments += ["-n", "'{}:primary:43008M:end:btrfs:mount=/home'".format(value["auto"]["disk"])]
                       #  arguments += ["-n", "'{}:primary:-{}M:end:swap'".format(value["auto"]["disk"], Processor.gen_swap_size())]
                    else:
                        for partition, values in value.items():
                            if partition == "disk":
                                arguments += ["-b", f"'{values}'"]
                                arguments += ["-t", "'{}:gpt'".format(values)]
                                continue
                            if values["mp"] == "/":
                                arguments += ["-n", "'{}:primary:start:{}M:btrfs:mount=/'".format(partition, values["size"])]
                            elif values["mp"] == "/boot/efi":
                                arguments += ["-n", "'{}:primary:start:512M:fat32:mount=/boot/efi:flags=esp'".format(partition)]
                            elif values["mp"] == "swap":
                                arguments += ["-n", "'{}:primary:{}M:end:swap'".format(partition, values["size"])]
                            else:
                                arguments += ["-n", "'{}:primary:{}M:end:{}:mount={}'".format(partition, values["size"], values["fs"], values["mp"])]
        
        # generating a temporary file to store the distinst command and
        # arguments parsed from the final data
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("#!/bin/sh\n")
            f.write("# This file was created by the Vanilla Installer.\n")
            f.write("# Do not edit this file manually!\n\n")

            if is_almost_supported:
                f.write("almost enter rw\n")

            f.write("set -e -x\n\n")

            if "VANILLA_FAKE" in os.environ:
                logger.info("VANILLA_FAKE is set, skipping the installation process.")
                f.write("echo 'VANILLA_FAKE is set, skipping the installation process.'\n")
                f.write("echo 'Printing the configuration instead:'\n")
                f.write("echo '----------------------------------'\n")
                f.write('echo "{}"\n'.format(finals))
                f.write("echo '----------------------------------'\n")
                f.write("sleep 5\n")
                f.write("exit 1\n")
            elif "VANILLA_SKIP_INSTALL" not in os.environ:
                for arg in arguments:
                    f.write(arg + " ")

            if is_almost_supported:
                f.write("\nalmost enter ro\n")

            f.write("\necho 'Post installation is running ...'\n")

            f.flush()
            f.close()

            # setting the file executable
            os.chmod(f.name, 0o755)
                
            return f.name
    
    @staticmethod
    def find_partitions(block_device, mountpoint, size, expected):
        logger.info("finding partitions for block device '{}' with mountpoint '{}' and size '{}'".format(block_device, mountpoint, size))
        partitions = []

        if block_device.startswith("/dev/"):
            block_device = block_device[5:]

        for partition in glob("/sys/block/{}/{}*".format(block_device, block_device)):
            partition_size = int(open(partition + "/size").read().strip()) * 512
            if partition_size == size:
                partitions.append("/dev/" + partition.split("/")[-1])
        if len(partitions) < expected:
            raise Exception("not enough partitions found for block device '{}' with mountpoint '{}' and size '{}'".format(block_device, mountpoint, size))
        elif len(partitions) > expected:
            raise Exception("too many partitions found for block device '{}' with mountpoint '{}' and size '{}'".format(block_device, mountpoint, size))

        return partitions
    
    @staticmethod
    def find_partitions_by_fs(block_device, mountpoint, fs, expected):
        logger.info("finding partitions for block device '{}' with mountpoint '{}' and filesystem '{}'".format(block_device, mountpoint, fs))
        partitions = []

        if block_device.startswith("/dev/"):
            block_device = block_device[5:]

        for partition in glob("/sys/block/{}/{}*".format(block_device, block_device)):
            partition_fs = subprocess.check_output(["lsblk", "-no", "FSTYPE", "/dev/" + partition.split("/")[-1]]).decode("utf-8").strip()
            if partition_fs == fs:
                partitions.append("/dev/" + partition.split("/")[-1])
        if len(partitions) < expected:
            raise Exception("not enough partitions found for block device '{}' with mountpoint '{}' and filesystem '{}'".format(block_device, mountpoint, fs))
        elif len(partitions) > expected:
            raise Exception("too many partitions found for block device '{}' with mountpoint '{}' and filesystem '{}'".format(block_device, mountpoint, fs))

        return partitions
    
    @staticmethod
    def get_uuid(partition):
        logger.info("getting UUID for partition '{}'".format(partition))
        return subprocess.check_output(["lsblk", "-no", "UUID", partition]).decode("utf-8").strip()
    
    @staticmethod
    def label_partition(partition, label, fs=None):
        logger.info("labeling partition '{}' with label '{}'".format(partition, label))

        if fs is None:
            fs = subprocess.check_output(["lsblk", "-no", "FSTYPE", partition]).decode("utf-8").strip()
        logging.info("command was: blkid -s TYPE -o value {}".format(partition))

        if fs == "btrfs":
            subprocess.check_call(["sudo", "btrfs", "filesystem", "label", partition, label])
        elif fs == "ext4":
            subprocess.check_call(["sudo", "e2label", partition, label])
        elif fs == "vfat":
            subprocess.check_call(["sudo", "fatlabel", partition, label])
        else:
            raise Exception("unknown filesystem '{}'".format(fs))

        return True
    
    @staticmethod
    def umount_if(mountpoint):
        logger.info("unmounting '{}' if mounted".format(mountpoint))
        if os.path.ismount(mountpoint):
            subprocess.check_call(["sudo", "umount", "-l", mountpoint])

    @staticmethod
    def remove_uuid_from_fstab(root, uuid):
        logger.info("removing UUID '{}' from fstab".format(uuid))
        subprocess.check_call(["sudo", "sed", "-i", "/UUID={}/d".format(uuid), root + "/etc/fstab"])

    @staticmethod
    def update_grub(root, block_device):
        logger.info("updating GRUB in '{}'".format(root))
        boot_partition = Processor.find_partitions_by_fs(block_device, "/boot", "ext4", 1)[0]
        efi_partition = Processor.find_partitions_by_fs(block_device, "/boot/efi", "vfat", 1)[0]

        Processor.umount_if(boot_partition)
        Processor.umount_if(efi_partition)

        subprocess.check_call(["sudo", "mount", boot_partition, root + "/boot"])
        subprocess.check_call(["sudo", "mount", efi_partition, root + "/boot/efi"])
        subprocess.check_call(["sudo", "mount", "--bind", "/dev", root + "/dev"])
        subprocess.check_call(["sudo", "mount", "--bind", "/proc", root + "/proc"])
        subprocess.check_call(["sudo", "mount", "--bind", "/sys", root + "/sys"])
        script = [
            "#!/bin/bash",
            "sudo chroot {} grub-mkconfig -o /boot/grub/grub.cfg".format(root),
        ]
        subprocess.check_call("\n".join(script), shell=True)
        Processor.umount_if(boot_partition)
        Processor.umount_if(efi_partition)

    @staticmethod
    def generate_grub_file(boot_uuid, root_a_uuid, root_b_uuid, kernel):
        boot_content = '''#!/bin/sh
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
'''
        boot_entry = '''menuentry 'State %s' --class gnu-linux --class gnu --class os {
    recordfail
    load_video
    gfxmode $linux_gfx_mode
    insmod gzio
    if [ x$grub_platform = xxen ]; then insmod xzio; insmod lzopio; fi
    insmod part_gpt
    insmod ext2
    search --no-floppy --fs-uuid --set=root %s
    linux	/vmlinuz-%s root=UUID=%s quiet splash bgrt_disable $vt_handoff
    initrd  /initrd.img-%s
}
'''
        boot_content += boot_entry % ("A", boot_uuid, kernel, root_a_uuid, kernel)
        boot_content += boot_entry % ("B", boot_uuid, kernel, root_b_uuid, kernel)
        
        with open("/tmp/10_vanilla", "w") as f:
            f.write(boot_content)

        subprocess.check_call(["sudo", "chmod", "777", "/tmp/10_vanilla"])
    
    @staticmethod
    def get_kernel_version(root):
        return sorted(os.listdir(root + "/usr/lib/modules"))[-1]

    @staticmethod
    def post_install(finals):
        # NOTE: manual partitioning not supported yet
        #       will be implemented in the near future
        logger.info("post-installation process started")
        root_a = ""
        root_b = ""

        # getting root partitions
        logger.info("getting root partitions")
        for final in finals:
            for key, value in final.items():
                if key == "disk":
                    if "auto" in value:
                        block_device = value["auto"]["disk"]
                        root_a, root_b = Processor.find_partitions(block_device, mountpoint="/", size=39999999*512, expected=2)
                    else:
                        logger.error("manual partitioning is not supported yet")
                        return False
        
        # getting boot partition
        logger.info("getting boot partition")
        boot_partition = Processor.find_partitions_by_fs(block_device, "/boot", "ext4", 1)[0]
        boot_uuid = Processor.get_uuid(boot_partition)
        
        # getting UUIDs
        logger.info("getting UUIDs for root partitions")
        root_a_uuid = Processor.get_uuid(root_a)
        root_b_uuid = Processor.get_uuid(root_b)

        # preparing mountpoints
        logger.info("preparing mountpoints")
        Processor.umount_if("/mnt")
        Processor.umount_if("/mnt/a")
        Processor.umount_if("/mnt/b")
        Processor.umount_if(root_a)
        Processor.umount_if(root_b)
        subprocess.check_call(["sudo", "mkdir", "-p", "/mnt/a", "/mnt/b"])

        # labeling root partitions
        logger.info("labeling root partitions")
        Processor.label_partition(root_a, "a", "btrfs")
        Processor.label_partition(root_b, "b", "btrfs")
            
        # mounting root partitions
        logger.info("mounting root partitions")
        subprocess.check_call(["sudo", "mount", root_a, "/mnt/a"])
        subprocess.check_call(["sudo", "mount", root_b, "/mnt/b"])

        # adapting A strucutre
        logger.info("adapting A structure")
        subprocess.check_call(["sudo", "mkdir", "-p", "/mnt/a/.system"])
        subprocess.check_call("sudo mv /mnt/a/* /mnt/a/.system/", shell=True)

        # creating standard folders in A
        logger.info("creating standard folders in A")
        standard_folders = ["boot", "dev", "home", "media", "mnt", "partFuture", "proc", "root", "run", "srv", "sys", "tmp"]
        for item in standard_folders:
            subprocess.check_call(["sudo", "mkdir", "-p", "/mnt/a/" + item])

        # creating relative links
        relative_links = [
            "usr", "etc",
            "var", "root",
            "usr/bin", "usr/lib",
            "usr/lib32", "usr/lib64",
            "usr/libx32",  "usr/sbin",
        ]
        relative_system_links = [
            "dev", "proc", "run",
            "srv", "sys", "tmp",
            "media", "boot",
        ]
        logger.info("creating relative links")
        script_a = ["#!/bin/bash", "cd /mnt/a/"]
        for link in relative_links:
            script_a.append("sudo ln -rs .system/{} .".format(link))
        subprocess.check_call(["sudo", "bash", "-c", "\n".join(script_a)])

        script_a = ["#!/bin/bash", "cd /mnt/a/"]
        for link in relative_system_links:
            script_a.append("sudo rm -rf .system/{}".format(link))
            script_a.append("sudo ln -rs {} .system/".format(link))
        subprocess.check_call(["sudo", "bash", "-c", "\n".join(script_a)])

        # removing unwanted UUIDs from A fstab
        logger.info("removing unwanted UUIDs from A fstab")
        Processor.remove_uuid_from_fstab("/mnt/a", root_b_uuid)

        # getting kernel version
        logger.info("getting kernel version")
        kernel = Processor.get_kernel_version("/mnt/a")

        # generating 10_vanilla grub file
        logger.info("generating 10_vanilla grub file")
        Processor.generate_grub_file(boot_uuid, root_a_uuid, root_b_uuid, kernel)

        # adapting A grub
        logger.info("adapting A grub")
        subprocess.check_call(["sudo", "sed", "-i", "s/GRUB_DEFAULT=.*/GRUB_DEFAULT=1/g", "/mnt/a/.system/etc/default/grub"])
        subprocess.check_call(["sudo", "cp", "/tmp/10_vanilla", "/mnt/a/.system/etc/grub.d/10_vanilla"])
        subprocess.check_call(["sudo", "rm", "/mnt/a/.system/etc/grub.d/10_linux"])
        subprocess.check_call(["sudo", "rm", "/mnt/a/.system/etc/grub.d/20_memtest86+"])
        
        # setting A root immutable
        logger.info("setting root A immutable")
        subprocess.check_call(["sudo", "chattr", "+i", "/mnt/a/"])

        # rsyncing A to B
        logger.info("rsyncing A to B")
        subprocess.check_call("sudo rsync -avxHAX --numeric-ids --exclude='/boot' --exclude='/dev' --exclude='/home' --exclude='/media' --exclude='/mnt' --exclude='/partFuture' --exclude='/proc' --exclude='/root' --exclude='/run' --exclude='/srv' --exclude='/sys' --exclude='/tmp' /mnt/a/ /mnt/b/", shell=True)

        # creating standard folders in B
        logger.info("creating standard folders in B")
        standard_folders = ["boot", "dev", "home", "media", "mnt", "partFuture", "proc", "root", "run", "srv", "sys", "tmp"]
        for item in standard_folders:
            subprocess.check_call(["sudo", "mkdir", "-p", "/mnt/b/" + item])
        
        # updating B fstab
        logger.info("updating B fstab")
        subprocess.check_call(["sudo", "sed", "-i", "s/UUID={}/UUID={}/g".format(root_a_uuid, root_b_uuid), "/mnt/b/.system/etc/fstab"])

        # setting B root immutable
        logger.info("setting root B immutable")
        subprocess.check_call(["sudo", "chattr", "+i", "/mnt/b/"])

        # updating grub for both root partitions
        logger.info("updating grub for both root partitions")
        Processor.update_grub("/mnt/a", block_device)
        Processor.update_grub("/mnt/b", block_device)

        # unmounting root partitions
        logger.info("unmounting root partitions")
        Processor.umount_if("/mnt/a")
        Processor.umount_if("/mnt/b")

        return True
        