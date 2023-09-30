# disk-manual-page.py
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

from vanilla_installer.core.disks import DisksManager, Diskutils, Partition
from vanilla_installer.core.system import Systeminfo

from vanilla_installer.defaults.disks.disk_widgets import PartitionRow

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/disks/manual-page.ui")
class DiskManualPage(Adw.Bin):
    __gtype_name__ = "DiskManualPage"

    boot_part_expand = Gtk.Template.Child()
    boot_part_expand_label = Gtk.Template.Child()
    efi_part_expand = Gtk.Template.Child()
    efi_part_expand_label = Gtk.Template.Child()
    bios_part_expand = Gtk.Template.Child()
    bios_part_expand_label = Gtk.Template.Child()
    abroot_a_part_expand = Gtk.Template.Child()
    abroot_a_part_expand_label = Gtk.Template.Child()
    abroot_b_part_expand = Gtk.Template.Child()
    abroot_b_part_expand_label = Gtk.Template.Child()
    home_part_expand = Gtk.Template.Child()
    home_part_expand_label = Gtk.Template.Child()
    swap_part_expand = Gtk.Template.Child()
    swap_part_expand_label = Gtk.Template.Child()

    # NOTE: Keys must be the same name as template children
    __selected_partitions: dict[str, dict[str, Union[Partition, str, None]]] = {
        "boot_part_expand": {
            "mountpoint": "/boot",
            "min_size": 943_718_400,  # 900 MB
            "partition": None,
            "fstype": None,
        },
        "efi_part_expand": {
            "mountpoint": "/boot/efi",
            "min_size": 536_870_912,  # 512 MB
            "partition": None,
            "fstype": None,
        },
        "bios_part_expand": {
            "mountpoint": "",
            "min_size": 1_048_576,  # 512 MB
            "partition": None,
            "fstype": None,
        },
        "abroot_a_part_expand": {
            "mountpoint": "/",
            "min_size": 10_737_418_240,  # 10 GB
            "partition": None,
            "fstype": None,
        },
        "abroot_b_part_expand": {
            "mountpoint": "/",
            "min_size": 10_737_418_240,  # 10 GB
            "partition": None,
            "fstype": None,
        },
        "home_part_expand": {
            "mountpoint": "/var",
            "min_size": 5_368_709_120,  # 5 GB
            "partition": None,
            "fstype": None,
        },
        "swap_part_expand": {
            "mountpoint": "swap",
            "partition": None,
            "fstype": None,
        },
    }

    __valid_root_partitions: bool = False
    __valid_partition_sizes: bool = False

    def __init__(self, window, parent, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__parent = parent
        self.__disks = DisksManager().all_disks

        self.__partitions = []
        for disk in self.__disks:
            for part in disk.partitions:
                self.__partitions.append(part)

        self.__partitions = sorted(self.__partitions)

        self.__boot_part_rows = self.__generate_partition_list_widgets(
            self.boot_part_expand, self.boot_part_expand_label, "ext4", False
        )

        for i, widget in enumerate(self.__boot_part_rows):
            self.boot_part_expand.add_row(widget)
            widget.add_siblings(
                self.__boot_part_rows[:i] + self.__boot_part_rows[i + 1:]
            )
            self.__selected_partitions["boot_part_expand"]["fstype"] = "ext4"

        if Systeminfo.is_uefi():
            # Configure EFI rows
            self.__efi_part_rows = self.__generate_partition_list_widgets(
                self.efi_part_expand, self.efi_part_expand_label, "fat32", False
            )
            for i, widget in enumerate(self.__efi_part_rows):
                self.efi_part_expand.add_row(widget)
                widget.add_siblings(
                    self.__efi_part_rows[:i] + self.__efi_part_rows[i + 1:]
                )
                self.__selected_partitions["efi_part_expand"]["fstype"] = "fat32"

            # Remove BIOS rows
            self.bios_part_expand.set_visible(False)
            if "bios_part_expand" in self.__selected_partitions:
                del self.__selected_partitions["bios_part_expand"]
        else:
            # Configure BIOS rows
            self.__bios_part_rows = self.__generate_partition_list_widgets(
                self.bios_part_expand, self.bios_part_expand_label, "ext4", False
            )
            for i, widget in enumerate(self.__bios_part_rows):
                self.bios_part_expand.add_row(widget)
                widget.add_siblings(
                    self.__bios_part_rows[:i] + self.__bios_part_rows[i + 1:]
                )
                self.__selected_partitions["bios_part_expand"]["fstype"] = "ext4"

            # Remove EFI rows
            self.efi_part_expand.set_visible(False)
            if "efi_part_expand" in self.__selected_partitions:
                del self.__selected_partitions["efi_part_expand"]
    
        self.__abroot_a_part_rows = self.__generate_partition_list_widgets(
                self.abroot_a_part_expand, self.abroot_a_part_expand_label, "btrfs", False
            )
        for i, widget in enumerate(self.__abroot_a_part_rows):
            self.abroot_a_part_expand.add_row(widget)
            widget.add_siblings(
                self.__abroot_a_part_rows[:i] +
                self.__abroot_a_part_rows[i + 1:]
            )
            self.__selected_partitions["abroot_a_part_expand"]["fstype"] = "btrfs"

        self.__abroot_b_part_rows = self.__generate_partition_list_widgets(
            self.abroot_b_part_expand, self.abroot_b_part_expand_label, "btrfs", False
        )
        for i, widget in enumerate(self.__abroot_b_part_rows):
            self.abroot_b_part_expand.add_row(widget)
            widget.add_siblings(
                self.__abroot_b_part_rows[:i] +
                self.__abroot_b_part_rows[i + 1:]
            )
            self.__selected_partitions["abroot_b_part_expand"]["fstype"] = "btrfs"

        self.__home_part_rows = self.__generate_partition_list_widgets(
            self.home_part_expand, self.home_part_expand_label
        )
        for i, widget in enumerate(self.__home_part_rows):
            self.home_part_expand.add_row(widget)
            widget.add_siblings(
                self.__home_part_rows[:i] + self.__home_part_rows[i + 1:]
            )
            self.__selected_partitions["home_part_expand"]["fstype"] = "btrfs"

        self.__swap_part_rows = self.__generate_partition_list_widgets(
            self.swap_part_expand, self.swap_part_expand_label, "swap", False
        )
        for i, widget in enumerate(self.__swap_part_rows):
            self.swap_part_expand.add_row(widget)
            widget.add_siblings(
                self.__swap_part_rows[:i] + self.__swap_part_rows[i + 1:]
            )
            self.__selected_partitions["swap_part_expand"]["fstype"] = "swap"

        #self.update_apply_button_status()

    @property
    def selected_partitions(self):
        return self.__selected_partitions
        
    def __on_launch_gparted(self, widget):
        proc = subprocess.Popen(["ps", "-C", "gparted"])
        proc.wait()
        if proc.returncode == 0:
            partitions_changed_toast = Adw.Toast.new(
                _(
                    "GParted is already running. Only one instance of GParted is permitted."
                )
            )
            partitions_changed_toast.set_timeout(5)
            self.__parent.group_partitions.add_toast(partitions_changed_toast)
        else:
            subprocess.Popen(["/usr/sbin/gparted"])
        
    def __generate_partition_list_widgets(
        self, parent_widget, parent_widget_action, default_fs="btrfs", add_dropdowns=True
    ):
            partition_widgets = []

            for i, partition in enumerate(self.__partitions):
                partition_row = PartitionRow(
                    self, parent_widget, parent_widget_action, partition, add_dropdowns, default_fs
                )
                if i != 0:
                    partition_row.select_button.set_group(
                        partition_widgets[0].select_button
                    )
                partition_widgets.append(partition_row)

            parent_widget.set_sensitive(len(partition_widgets) > 0)

            return partition_widgets
    
    def update_partition_rows(self):
        rows = [
            self.__boot_part_rows,
            self.__abroot_a_part_rows,
            self.__abroot_b_part_rows,
            self.__home_part_rows,
            self.__swap_part_rows,
        ]

        if Systeminfo.is_uefi():
            rows.append(self.__efi_part_rows)
        else:
            rows.append(self.__bios_part_rows)

        for row in rows:
            for child_row in row:
                row_partition = child_row.get_title()

                # The row where partition was selected still has to be sensitive
                if child_row.select_button.get_active():
                    child_row.set_sensitive(True)
                    continue

                is_used = False
                for __, val in self.__selected_partitions.items():
                    if (
                        val["partition"] is not None
                        and val["partition"].partition == row_partition
                    ):
                        is_used = True
                child_row.set_sensitive(not is_used)