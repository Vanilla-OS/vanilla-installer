import datetime

import pytz
import requests
from gi.repository import GnomeDesktop

all_timezones = {}

zone_tab_path = "/usr/share/zoneinfo/zone.tab"

with open(zone_tab_path, "r") as zone_tab_file:
    for line in zone_tab_file:
        if line.startswith("#"):
            continue

        fields = line.strip().split("\t")
        if len(fields) < 3:
            continue

        country_code, city = fields[2].rsplit("/", 1)

        if country_code not in all_timezones:
            all_timezones[country_code] = []

        all_timezones[country_code].append(city)

all_timezones = {
    country: sorted(timezones) for country, timezones in all_timezones.items()
}
all_timezones = dict(sorted(all_timezones.items()))


def get_current_timezone():
    success_code, country, city = get_timezone_by_ip()
    if not success_code:
        timezone = GnomeDesktop.WallClock().get_timezone()
        timezone = timezone.get_identifier()

        country = timezone.split("/")[0]
        city = timezone[country.__len__() + 1 :]

    return country, city


def get_timezone_by_ip():
    try:
        res = requests.get("http://ip-api.com/json", timeout=3).json()
        timezone = res["timezone"]
        country = timezone.split("/")[0]
        city = timezone[country.__len__() + 1 :]
        success_code = True
    except Exception:
        success_code = False
        city = -1
        country = -1
    return success_code, country, city


def get_preview_timezone(country, city):
    timezone = pytz.timezone(f"{country}/{city}")
    now = datetime.datetime.now(timezone)

    return now.strftime("%H:%M"), now.strftime("%A, %d %B %Y")
