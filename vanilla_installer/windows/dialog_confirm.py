# dialog.py
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

from gi.repository import Gtk, GObject, Adw


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-choice.ui')
class VanillaChoiceEntry(Adw.ActionRow):
    __gtype_name__ = 'VanillaChoiceEntry'

    img_choice = Gtk.Template.Child()

    def __init__(self, title, subtitle,icon_name, **kwargs):
        super().__init__(**kwargs)
        self.set_title(title)
        self.set_subtitle(subtitle)
        self.img_choice.set_from_icon_name(icon_name)


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/widget-choice-expander.ui')
class VanillaChoiceExpanderEntry(Adw.ExpanderRow):
    __gtype_name__ = 'VanillaChoiceExpanderEntry'

    img_choice = Gtk.Template.Child()

    def __init__(self, title, subtitle,icon_name, **kwargs):
        super().__init__(**kwargs)
        self.set_title(title)
        self.set_subtitle(subtitle)
        self.img_choice.set_from_icon_name(icon_name)


@Gtk.Template(resource_path='/org/vanillaos/Installer/gtk/dialog-confirm.ui')
class VanillaDialogConfirm(Adw.Window):
    __gtype_name__ = 'VanillaDialogConfirm'
    __gsignals__ = {
        "installation-confirmed": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "installation-cancelled": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    group_changes = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    btn_confirm = Gtk.Template.Child()

    def __init__(self, window, finals, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(window)
        
        for final in finals:
            for key, value in final.items():
                
                if key == "language":
                    self.group_changes.add(VanillaChoiceEntry(
                        "Language",
                        value,
                        "preferences-desktop-locale-symbolic"
                    ))
                elif key == "keyboard":
                    self.group_changes.add(VanillaChoiceEntry(
                        "Keyboard",
                        value,
                        "input-keyboard-symbolic"
                    ))
                elif key == "timezone":
                    self.group_changes.add(VanillaChoiceEntry(
                        "Timezone",
                        f"{value['region']} {value['zone']}",
                        "preferences-system-time-symbolic"
                    ))
                elif key == "users":
                    self.group_changes.add(VanillaChoiceEntry(
                        "Users",
                        f"{value['username']} ({value['fullname']})",
                        "system-users-symbolic"
                    ))
                elif key == "disk":
                    if "auto" in value:
                        self.group_changes.add(VanillaChoiceEntry(
                            "Disk",
                            f"{value['auto']['disk']} ({value['auto']['pretty_size']})",
                            "drive-harddisk-system-symbolic"
                        ))
                    else:
                        i = 0
                        for block, block_info in value.items():
                            if i == 0:
                                expander = VanillaChoiceExpanderEntry(
                                    "Disk",
                                    block_info,
                                    "drive-harddisk-system-symbolic"
                                )
                                self.group_changes.add(expander)
                            else:
                                expander.add_row(VanillaChoiceEntry(
                                    block,
                                    f"{block_info['fs']} {block_info['mp']} ({block_info['pretty_size']})",
                                    "drive-harddisk-system-symbolic"
                                ))
                            i += 1

                
        self.btn_cancel.connect("clicked", self.__on_cancel)
        self.btn_confirm.connect("clicked", self.__on_confirm)

    def __on_cancel(self, widget):
        self.emit("installation-cancelled")
        self.destroy()

    def __on_confirm(self, widget):
        self.emit("installation-confirmed")
        self.destroy()
