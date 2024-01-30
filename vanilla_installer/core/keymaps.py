from gi.repository.GnomeDesktop import XkbInfo

class KeyMaps:
    def __init__(self):
        self.__all_keymaps = self.__get_all_keymaps()

    def __get_all_keymaps(self):
        xkb_info = XkbInfo()
        all_layouts = xkb_info.get_all_layouts()
        _all_keymaps = {}
        all_keymaps = {}
        cleanup_rules = ["A"]

        for layout in all_layouts:
            _all_keymaps[layout] = {}
            _info = xkb_info.get_layout_info(layout)
            _all_keymaps[layout]["display_name"] = _info[1]
            _all_keymaps[layout]["short_name"] = _info[2]
            _all_keymaps[layout]["xkb_layout"] = _info[3]
            _all_keymaps[layout]["xkb_variant"] = _info[4]

        for layout in _all_keymaps:
            country = _all_keymaps[layout]["display_name"].split(" ")[0]

            if country in cleanup_rules:
                continue

            if country not in all_keymaps:
                all_keymaps[country] = {}

            all_keymaps[country][layout] = _all_keymaps[layout]

        all_keymaps = {
            k: v for k, v in sorted(all_keymaps.items(), key=lambda item: item[0])
        }
        return all_keymaps

    @property
    def list_all(self):
        return self.__all_keymaps
