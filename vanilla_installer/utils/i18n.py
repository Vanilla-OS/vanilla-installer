# i18n.py
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

from gettext import gettext as _

from gi.repository import GObject


def _retranslate(widget):
    for prop in widget.list_properties():
        if prop.value_type != GObject.TYPE_STRING:
            continue

        if not prop.flags & GObject.ParamFlags.READABLE:
            continue
        if not prop.flags & GObject.ParamFlags.WRITABLE:
            continue

        text = widget.get_property(prop.name)
        if text and _(text) != text:
            widget.set_property(prop.name, _(text))


def translate_widget_tree(root):
    stack = [root]
    while stack:
        widget = stack.pop()
        _retranslate(widget)

        child = widget.get_first_child()
        while child is not None:
            stack.append(child)
            child = child.get_next_sibling()
