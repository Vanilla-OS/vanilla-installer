# network.py
#
# Copyright 2023 mirkobrombin
# Copyright 2023 matbme
#
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

import logging
import time
from gettext import gettext as _
from operator import attrgetter
from threading import Lock, Timer

from gi.repository import NM, NMA4, Adw, Gtk, GLib

from vanilla_installer.utils.run_async import RunAsync

logger = logging.getLogger("VanillaInstaller::Network")

# Dictionary mapping security types to a tuple containing
# their pretty name and whether it is a secure protocol.
# If security is None, it means that no padlock icon is shown.
# If security is False, a warning symbol appears instead of a padlock.
AP_SECURITY_TYPES = {
    "none": (None, None),
    "wep": (False, _("Insecure network (WEP)")),
    "wpa": (True, _("Secure network (WPA)")),
    "wpa2": (True, _("Secure network (WPA2)")),
    "sae": (True, _("Secure network (WPA3)")),
    "owe": (None, None),
    "owe_tm": (None, None),
}

# PyGObject-libnm doesn't seem to expose these values, so we have redefine them
NM_802_11_AP_FLAGS_PRIVACY = 0x00000001
NM_802_11_AP_SEC_NONE = 0x00000000

NM_802_11_AP_SEC_KEY_MGMT_802_1X = 0x00000200
NM_802_11_AP_SEC_KEY_MGMT_EAP_SUITE_B_192 = 0x00002000
NM_802_11_AP_SEC_KEY_MGMT_OWE = 0x00000800
NM_802_11_AP_SEC_KEY_MGMT_OWE_TM = 0x00001000
NM_802_11_AP_SEC_KEY_MGMT_PSK = 0x00000100
NM_802_11_AP_SEC_KEY_MGMT_SAE = 0x00000400


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/wireless-row.ui")
class WirelessRow(Adw.ActionRow):
    __gtype_name__ = "WirelessRow"

    signal_icon = Gtk.Template.Child()
    secure_icon = Gtk.Template.Child()
    connected_label = Gtk.Template.Child()

    def __init__(self, window, client, device: NM.DeviceWifi, ap, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.client = client
        self.ap = ap
        self.device = device
        self.refresh_ui()

        self.set_activatable(True)
        self.connect("activated", self.__show_connect_dialog)

    @property
    def ssid(self):
        ssid = self.ap.get_ssid()
        if ssid is not None:
            ssid = ssid.get_data().decode("utf-8")
        else:
            ssid = ""
        return ssid

    @property
    def signal_strength(self):
        return self.ap.get_strength()

    @property
    def connected(self):
        active_connection = self.device.get_active_connection()
        if active_connection is not None:
            if active_connection.get_id() == self.ssid:
                return True
        return False

    def refresh_ui(self):
        # We use the same strength logic as gnome-control-center
        strength = self.signal_strength
        if strength < 20:
            icon_name = "network-wireless-signal-none-symbolic"
        elif strength < 40:
            icon_name = "network-wireless-signal-weak-symbolic"
        elif strength < 50:
            icon_name = "network-wireless-signal-ok-symbolic"
        elif strength < 80:
            icon_name = "network-wireless-signal-good-symbolic"
        else:
            icon_name = "network-wireless-signal-excellent-symbolic"

        self.set_title(self.ssid)
        self.signal_icon.set_from_icon_name(icon_name)
        secure, tooltip = self.__get_security()
        if secure is not None:
            if not secure:
                self.secure_icon.set_from_icon_name("warning-small-symbolic")
            else:
                self.secure_icon.set_from_icon_name(
                    "network-wireless-encrypted-symbolic"
                )

        self.secure_icon.set_visible(secure is not None)
        if tooltip is not None:
            self.secure_icon.set_tooltip_text(tooltip)

        self.connected_label.set_visible(self.connected)

    def __get_security(self) -> tuple[bool | None, str | None]:
        flags = self.ap.get_flags()
        rsn_flags = self.ap.get_rsn_flags()
        wpa_flags = self.ap.get_wpa_flags()

        # Copying logic used in gnome-control-center because this is a mess
        if (
            not (flags & NM_802_11_AP_FLAGS_PRIVACY)
            and wpa_flags == NM_802_11_AP_SEC_NONE
            and rsn_flags == NM_802_11_AP_SEC_NONE
        ):
            return AP_SECURITY_TYPES["none"]
        elif (
            (flags & NM_802_11_AP_FLAGS_PRIVACY)
            and wpa_flags == NM_802_11_AP_SEC_NONE
            and rsn_flags == NM_802_11_AP_SEC_NONE
        ):
            return AP_SECURITY_TYPES["wep"]
        elif (
            (flags & NM_802_11_AP_FLAGS_PRIVACY)
            and wpa_flags != NM_802_11_AP_SEC_NONE
            and rsn_flags != NM_802_11_AP_SEC_NONE
        ):
            return AP_SECURITY_TYPES["wpa"]
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_SAE:
            return AP_SECURITY_TYPES["sae"]
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_OWE:
            return AP_SECURITY_TYPES["owe"]
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_OWE_TM:
            return AP_SECURITY_TYPES["owe_tm"]
        else:
            return AP_SECURITY_TYPES["wpa2"]

    @property
    def __key_mgmt(self):
        # Key management used for the connection. One of "none" (WEP or no
        # password protection), "ieee8021x" (Dynamic WEP), "owe" (Opportunistic
        # Wireless Encryption), "wpa-psk" (WPA2 + WPA3 personal), "sae" (WPA3
        # personal only), "wpa-eap" (WPA2 + WPA3 enterprise) or
        # "wpa-eap-suite-b-192" (WPA3 enterprise only).
        rsn_flags = self.ap.get_rsn_flags()
        wpa_flags = self.ap.get_wpa_flags()

        if wpa_flags == NM_802_11_AP_SEC_NONE and rsn_flags == NM_802_11_AP_SEC_NONE:
            return "none"
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_802_1X:
            return "ieee8021x"
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_EAP_SUITE_B_192:
            return "wpa-eap-suite-b-192"
        elif (
            rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_OWE
            or rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_OWE_TM
        ):
            return "owe"
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_PSK:
            return "wpa-psk"
        elif rsn_flags & NM_802_11_AP_SEC_KEY_MGMT_SAE:
            return "sae"

    def __show_connect_dialog(self, data):
        dialog = NMA4.WifiDialog.new(
            self.client, self.__construct_connection(), self.device, self.ap, False
        )
        dialog.set_modal(True)
        dialog.set_transient_for(self.__window)

        dialog.connect("response", self.__on_dialog_response)

        dialog.show()

    def __on_dialog_response(self, dialog, response_id):
        def connect_cb(client, result, data):
            try:
                ac = client.add_and_activate_connection_finish(result)
                logger.debug("ActiveConnection {}".format(ac.get_path()))
            except Exception as e:
                logger.error("Error:", e)

        if response_id == -6:
            dialog.close()
        elif response_id == -5:
            conn, _, _ = dialog.get_connection()
            self.client.add_and_activate_connection_async(
                conn, self.device, self.ap.get_path(), None, connect_cb, None
            )
            dialog.close()

    def __construct_connection(self):
        connection = NM.SimpleConnection.new()
        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, self.ssid)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "802-11-wireless")
        s_wifi = NM.SettingWireless.new()
        s_wifi.set_property(NM.SETTING_WIRELESS_SSID, self.ap.get_ssid())
        s_wifi.set_property(NM.SETTING_WIRELESS_MODE, "infrastructure")
        s_wsec = NM.SettingWirelessSecurity.new()
        s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, self.__key_mgmt)
        s_ip4 = NM.SettingIP4Config.new()
        s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")
        s_ip6 = NM.SettingIP6Config.new()
        s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")

        connection.add_setting(s_con)
        connection.add_setting(s_wifi)
        connection.add_setting(s_wsec)
        connection.add_setting(s_ip4)
        connection.add_setting(s_ip6)

        return connection


@Gtk.Template(resource_path="/org/vanillaos/Installer/gtk/default-network.ui")
class VanillaDefaultNetwork(Adw.Bin):
    __gtype_name__ = "VanillaDefaultNetwork"

    wired_group = Gtk.Template.Child()
    wireless_group = Gtk.Template.Child()
    hidden_network_row = Gtk.Template.Child()
    proxy_settings_row = Gtk.Template.Child()
    advanced_group = Gtk.Template.Child()
    btn_next = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.__nm_client = NM.Client.new()

        self.__devices = []
        self.__wired_children = []
        self.__wireless_children = {}

        self.__last_wifi_scan = 0

        # Prevent concurrency issues when re-scanning Wi-Fi devices.
        # Since we reload the list every time there's a state change,
        # there's a high change that it coincides with a periodic
        # refresh operation.
        self.__wifi_lock = Lock()
        self.__scan_lock = Lock()

        # Since we have a dedicated page for checking connectivity,
        # we only need to make sure the user has some type of
        # connection set up, be it wired or wireless.
        self.has_eth_connection = False
        self.has_wifi_connection = False

        self.__get_network_devices()
        self.__start_auto_refresh()

        # TODO: Remove once implemented
        self.advanced_group.set_visible(False)

        self.__nm_client.connect("device-added", self.__add_new_device)
        self.__nm_client.connect("device-added", self.__remove_device)
        self.btn_next.connect("clicked", self.__window.next)
        self.connect("realize", self.__try_skip_page)

    def __try_skip_page(self, data):
        # Skip page if already connected to the internet
        if self.has_eth_connection or self.has_wifi_connection:
            self.__window.next()

    @property
    def step_id(self):
        return self.__key

    def get_finals(self):
        return {}

    def set_btn_next(self, state: bool):
        if state:
            if not self.btn_next.has_css_class("suggested-action"):
                self.btn_next.add_css_class("suggested-action")
            self.btn_next.set_sensitive(True)
        else:
            if self.btn_next.has_css_class("suggested-action"):
                self.btn_next.remove_css_class("suggested-action")
            self.btn_next.set_sensitive(False)

    def __get_network_devices(self):
        devices = self.__nm_client.get_devices()
        eth_devices = 0
        wifi_devices = 0
        for device in devices:
            if device.is_real():
                device_type = device.get_device_type()
                if device_type == NM.DeviceType.ETHERNET:
                    self.__add_ethernet_connection(device)
                    eth_devices += 1
                elif device_type == NM.DeviceType.WIFI:
                    device.connect("state-changed", self.__on_state_changed)
                    self.has_wifi_connection = (
                        device.get_active_connection() is not None
                    )
                    self.__refresh_wifi_list(device)
                    wifi_devices += 1
                else:
                    continue

                self.__devices.append(device)

        self.wired_group.set_visible(eth_devices > 0)
        self.wireless_group.set_visible(wifi_devices > 0)

    def __add_new_device(self, client, device):
        self.__devices.append(device)

    def __remove_device(self, client, device):
        self.__devices.remove(device)

    def __on_state_changed(self, device, new_state, old_state, reason):
        self.has_wifi_connection = device.get_active_connection() is not None
        self.__refresh()

    def __refresh(self):
        for child in self.__wired_children:
            self.wired_group.remove(child)
        self.__wired_children = []

        for device in self.__devices:
            device_type = device.get_device_type()
            if device_type == NM.DeviceType.ETHERNET:
                self.__add_ethernet_connection(device)
            elif device_type == NM.DeviceType.WIFI:
                self.__scan_wifi(device)

        self.set_btn_next(self.has_eth_connection or self.has_wifi_connection)
        return GLib.SOURCE_REMOVE

    def __start_auto_refresh(self):
        def run_async():
            while True:
                GLib.idle_add(self.__refresh)
                time.sleep(10)

        RunAsync(run_async, None)

    def __device_status(self, conn: NM.Device):
        connected = False
        match conn.get_state():
            case NM.DeviceState.ACTIVATED:
                status = _("Connected")
                connected = True
            case NM.DeviceState.NEED_AUTH:
                status = _("Authentication required")
            case [
                NM.DeviceState.PREPARE,
                NM.DeviceState.CONFIG,
                NM.DeviceState.IP_CONFIG,
                NM.DeviceState.IP_CHECK,
                NM.DeviceState.SECONDARIES,
            ]:
                status = _("Connecting")
            case NM.DeviceState.DISCONNECTED:
                status = _("Disconnected")
            case NM.DeviceState.DEACTIVATING:
                status = _("Disconnecting")
            case NM.DeviceState.FAILED:
                status = _("Connection Failed")
            case NM.DeviceState.UNKNOWN:
                status = _("Status Unknown")
            case NM.DeviceState.UNMANAGED:
                status = _("Unmanaged")
            case NM.DeviceState.UNAVAILABLE:
                status = _("Unavailable")

        return status, connected

    def __add_ethernet_connection(self, conn: NM.DeviceEthernet):
        status, connected = self.__device_status(conn)
        if connected:
            status += f" - {conn.get_speed()} Mbps"
            self.has_eth_connection = True
        else:
            self.has_eth_connection = False

        # Wired devices with no cable plugged in are shown as unavailable
        if conn.get_state() == NM.DeviceState.UNAVAILABLE:
            status = _("Cable Unplugged")

        eth_conn = Adw.ActionRow(title=status)
        self.wired_group.add(eth_conn)
        self.__wired_children.append(eth_conn)

    def __poll_wifi_scan(self, conn: NM.DeviceWifi):
        self.__scan_lock.acquire()
        while conn.get_last_scan() == self.__last_wifi_scan:
            time.sleep(0.25)
        self.__scan_lock.release()

        GLib.idle_add(self.__refresh_wifi_list, conn)

    def __refresh_wifi_list(self, conn: NM.DeviceWifi):
        networks = {}
        for ap in conn.get_access_points():
            ssid = ap.get_ssid()
            if ssid is None:
                continue

            ssid = ssid.get_data().decode("utf-8")
            if ssid in networks.keys():
                networks[ssid].append(ap)
            else:
                networks[ssid] = [ap]

        self.__wifi_lock.acquire()

        # Invalidate current list
        for ssid, (child, clean) in self.__wireless_children.items():
            self.__wireless_children[ssid] = (child, True)

        for ssid, aps in networks.items():
            max_strength = -1
            best_ap = None
            for ap in aps:
                ap_strength = ap.get_strength()
                if ap_strength > max_strength:
                    max_strength = ap_strength
                    best_ap = ap

            # Try to re-use entries with the same SSID
            if ssid in self.__wireless_children.keys():
                child = self.__wireless_children[ssid][0]
                child.ap = best_ap
                child.refresh_ui()
                self.__wireless_children[ssid] = (child, False)
                continue

            # Create new row if SSID is new
            wifi_network = WirelessRow(self.__window, self.__nm_client, conn, best_ap)
            self.wireless_group.add(wifi_network)
            self.__wireless_children[ssid] = (wifi_network, False)

        # Remove invalid rows
        invalid_ssids = []
        for ssid, (child, clean) in self.__wireless_children.items():
            self.wireless_group.remove(child)
            if clean:
                invalid_ssids.append(ssid)

        for ssid in invalid_ssids:
            del self.__wireless_children[ssid]

        for row in self.__sorted_wireless_children:
            self.wireless_group.add(row)

        self.__wifi_lock.release()

    def __scan_wifi(self, conn: NM.DeviceWifi):
        self.__scan_lock.acquire()
        self.__last_wifi_scan = conn.get_last_scan()
        self.__scan_lock.release()
        conn.request_scan_async()

        t = Timer(1.5, self.__poll_wifi_scan, [conn])
        t.start()

    @property
    def __sorted_wireless_children(self):
        def multisort(xs, specs):
            for key, reverse in reversed(specs):
                xs.sort(key=attrgetter(key), reverse=reverse)
            return xs

        # 1 - Is connected
        # 2 - Signal strength
        # 3 - Alphabetically
        return multisort(
            [it[0] for it in list(self.__wireless_children.values())],
            (("connected", True), ("signal_strength", True), ("ssid", True)),
        )
