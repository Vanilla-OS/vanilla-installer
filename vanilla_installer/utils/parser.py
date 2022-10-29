# parser.py
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
import sys
import logging
import json

logger = logging.getLogger("Installer::Parser")


class Parser:

    supported_types = ["command"]

    @staticmethod
    def parse(finals):
        commands = []
        warps = []
        all_vars = []

        for final in finals:
            if len(final) == 0:
                continue

            _vars = final["vars"]
            for k, v in _vars.items():
                if k in all_vars:
                    logger.error(
                        f"variable {k} is defined multiple times")
                    sys.exit(1)
                if not v:
                    continue
                all_vars.append(k)

            for _func in final["funcs"]:

                if "if" not in _func:
                    logger.critical(f"Missing an 'if' operand in {_func}")
                    sys.exit(1)

                if _func["if"] not in _vars and not _func["if"].startswith("warp::"):
                    logger.critical(
                        f"Missing a variable named '{_func['if']}' in the 'vars' section.")
                    sys.exit(1)

                if _func.get("type") not in Parser.supported_types:
                    logger.critical(
                        f"Unsupported final type: {_func.get('type')}")
                    sys.exit(1)

                if _func["if"].startswith("warp::"):
                    _var = _func["if"].split("::")[1]
                    warps.append({
                        "vars": [_var],
                        "func": [_func]
                    })
                    continue

                # assume True if no condition is given
                _condition = _func.get("condition", True)

                # check if the condition is met
                if _condition == _vars[_func["if"]]:
                    commands += _func["commands"]
        
        # set-up warps if any
        for warp in warps:
            _vars = warp["vars"]

            for var in _vars:
                if var not in all_vars:
                    continue

            for _func in warp["func"]:
                _if = _func["if"].split("::")[1]
                if _if in all_vars:
                    commands += _func["commands"]

        return commands
