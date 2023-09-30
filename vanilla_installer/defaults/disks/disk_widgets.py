# disk-widgets.py
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

from gi.repository import Adw, GObject, Gtk

from vanilla_installer.core.disks import Diskutils

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/disks/widget-disk.ui")
class DiskToggleButton(Gtk.ToggleButton):
    __gtype_name__ = "DiskToggleButton"

    disk_title = Gtk.Template.Child()
    disk_subtitle = Gtk.Template.Child()

    def __init__(self, window, page, parent, disk, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__page = page
        self.__parent = parent
        self.__disk = disk
        self.disk_title.set_label(disk.name)

        min_disk_size = self.__window.recipe.get("min_disk_size", 28680)

        if (self.__disk.size < min_disk_size * 1_048_576):
            self.disk_subtitle.get_style_context().add_class("error")
            self.set_sensitive(False)
            self.disk_subtitle.set_label(("Not enough space: {0}/{1}").format(disk.pretty_size, Diskutils.pretty_size(min_disk_size * 1_048_576)))
        else:
            self.disk_subtitle.get_style_context().remove_class("error")
            self.disk_subtitle.set_label(disk.pretty_size)

        self.connect("toggled", self.__on_button_toggled)

    def __on_button_toggled(self, widget):
        self.__page.selected_disk['auto']['disk'] = self.__disk.disk
        self.__page.selected_disk['auto']['pretty_size'] = self.__disk.pretty_size
        self.__page.selected_disk['auto']['size'] = self.__disk.size

        self.__parent.btn_next.set_visible(True)

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/disks/dialog-disk-confirm.ui")
class DialogDiskConfirm(Gtk.Window):
    __gtype_name__ = "DialogDiskConfirm"

    btn_cancel = Gtk.Template.Child()
    btn_apply = Gtk.Template.Child()
    group_partitions = Gtk.Template.Child()

    def __init__(self, window, partition_recipe, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.set_transient_for(self.__window)
        self.default_width, self.default_height = self.get_default_size()

        # signals
        self.btn_cancel.connect("clicked", self.__on_btn_cancel_clicked)
        self.btn_apply.connect("clicked", self.__on_btn_apply_clicked)

        for partition, values in partition_recipe.items():
            entry = Adw.ActionRow()
            if partition == "auto":
                entry.set_title(partition_recipe[partition]["disk"])
                entry.set_subtitle(_("Entire disk will be used."))
            else:
                self.set_default_size(self.default_width, 650)
                if partition == "disk":
                    continue
                entry.set_title(partition)
                entry.set_subtitle(
                    _("Will be formatted in {} and mounted in {}").format(
                        partition_recipe[partition]["fs"],
                        partition_recipe[partition]["mp"],
                    )
                )
            self.group_partitions.add(entry)

    def __on_btn_cancel_clicked(self, widget):
        self.destroy()

    def __on_btn_apply_clicked(self, widget):
        self.__window.next()
        self.destroy()

@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/widget-partition-row.ui")
class PartitionRow(Adw.ActionRow):
    __gtype_name__ = "PartitionRow"

    select_button = Gtk.Template.Child()
    suffix_bin = Gtk.Template.Child()

    __siblings: list

    __partition_fs_types = ["btrfs", "ext4", "ext3", "fat32", "xfs"]

    def __init__(self, page, parent, parent_action, partition, modifiable, default_fs, **kwargs):
        super().__init__(**kwargs)
        self.__page = page
        self.__parent = parent
        self.__parent_action = parent_action
        self.__partition = partition
        self.__modifiable = modifiable
        self.__default_fs = default_fs

        self.set_title(partition.partition)
        self.set_subtitle(partition.pretty_size)

        print("\n\n\n", page)
        print("\n\n\n", parent)

        self.select_button.connect("toggled", self.__on_check_button_toggled)

        if self.__modifiable:
            self.__add_dropdown()

    def __add_dropdown(self):
        fs_dropdown = Gtk.DropDown.new_from_strings(self.__partition_fs_types)
        fs_dropdown.set_valign(Gtk.Align.CENTER)
        fs_dropdown.set_visible(False)
        if self.__partition.fs_type in self.__partition_fs_types:
            fs_dropdown.set_selected(
                self.__partition_fs_types.index(self.__partition.fs_type)
            )
        else:
            fs_dropdown.set_selected(
                self.__partition_fs_types.index(self.__default_fs))
        fs_dropdown.connect("notify::selected", self.__on_dropdown_selected)
        self.suffix_bin.set_child(fs_dropdown)

    def add_siblings(self, siblings):
        self.__siblings = siblings

    def __on_check_button_toggled(self, widget):
        dropdown = self.suffix_bin.get_child()

        # Sets all sibling dropdowns as not visible
        for sibling in self.__siblings:
            sibling_dropdown = sibling.suffix_bin.get_child()
            if sibling_dropdown:
                sibling_dropdown.set_visible(False)

        # Only the currently selected partition can be edited
        if dropdown:
            dropdown.set_visible(True)
            fs_type = self.__partition_fs_types[dropdown.get_selected()]
            self.__parent.set_subtitle(
                f"{self.__partition.pretty_size} ({fs_type})")
        else:
            self.__parent.set_subtitle(f"{self.__partition.pretty_size}")

        self.__parent_action.set_label(self.__partition.partition)
        self.__page.selected_partitions[self.__parent.get_buildable_id()][
            "partition"
        ] = self.__partition

        # Sets already selected partitions as not sensitive
        self.__page.update_partition_rows()
        # Checks whether we can proceed with installation
        self.__page.update_apply_button_status()
        # Checks whether root partitions are the same size
        self.__page.check_root_partitions_size_equal()
        # Checks whether selected partitions are big enough
        self.__page.check_selected_partitions_sizes()

    def __on_dropdown_selected(self, widget, _):
        fs_type = self.__partition_fs_types[widget.get_selected()]
        size = self.__partition.pretty_size
        print("\n\n\n", self.__page)
        self.__page.selected_partitions[self.__parent.get_buildable_id()][
            "fstype"
        ] = fs_type
        self.__parent.set_subtitle(f"{size} ({fs_type})")