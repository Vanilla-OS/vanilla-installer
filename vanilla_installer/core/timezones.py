import datetime
import logging

import requests
from gi.repository import GLib, GWeather
from zoneinfo import ZoneInfo

logger = logging.getLogger("VanillaInstaller::Timezones")

regions: dict[str, dict[str, dict[str, str]]] = {}
world = GWeather.Location.get_world()
parents = []
base = world
child = None
while True:
    child = base.next_child(child)
    if child is not None:
        if child.get_level() == GWeather.LocationLevel.REGION:
            regions[child.get_name()] = {}
            current_region = child.get_name()
        elif child.get_level() == GWeather.LocationLevel.COUNTRY:
            regions[current_region][child.get_name()] = {}
            current_country = child.get_name()
        elif child.get_level() == GWeather.LocationLevel.CITY:
            regions[current_region][current_country][child.get_city_name()] = (
                child.get_timezone_str()
            )

        if child.next_child(None) is not None:
            parents.append(child)
            base = child
            child = None
    else:
        base = base.get_parent()
        if base is None:
            break
        child = parents.pop()

all_timezones = dict(sorted(regions.items()))


def get_location(callback=None):
    logger.info("Trying to retrieve timezone automatically")
    try:
        res = requests.get("http://ip-api.com/json?fields=49344", timeout=3).json()
        if res["status"] != "success":
            raise Exception(f"get_location: request failed with message '{res['message']}'")
        nearest = world.find_nearest_city(res["lat"], res["lon"])
    except Exception as e:
        logger.error(f"Failed to retrieve timezone: {e}")
        nearest = None

    logger.info("Done retrieving timezone")

    if callback:
        logger.info("Running callback")
        GLib.idle_add(callback, nearest)


tz_preview_cache: dict[str, tuple[str, str]] = {}


def get_timezone_preview(tzname):
    if tzname in tz_preview_cache:
        return tz_preview_cache[tzname]
    else:
        timezone = ZoneInfo(tzname)
        now = datetime.datetime.now(timezone)
        now_str = (
            "%02d:%02d" % (now.hour, now.minute),
            now.strftime("%A, %d %B %Y"),
        )
        tz_preview_cache[tzname] = now_str
        return now_str
