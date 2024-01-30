# locale.py
#
# Copyright 2024 axtloss <https://github.com/axtloss>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

class Locale:
    def __init__(self, locales, region, location):
        self.locales = locales
        self.region = region
        self.location = location

    def __str__(self):
        return "<Locale: {} {} {}>".format(self.locales, self.region, self.location)

    def __repr__(self):
        return self.__str__()
