import datetime

import requests
from gi.repository import GnomeDesktop
from gi.repository import GWeather
from zoneinfo import ZoneInfo

regions = {}
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
            regions[current_region][current_country][child.get_city_name()] = child.get_timezone_str()

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

def get_location():
    try:
        res = requests.get("http://ip-api.com/json?fields=49344", timeout=3).json()
        if res["status"] != "success":
            raise Exception(f"get_location: request failed with message '{res['message']}'")
        nearest = world.find_nearest_city(res["lat"], res["lon"])
    except Exception as e:
        print(e)
        nearest = None

    return nearest


def get_timezone_preview(tzname):
    timezone = ZoneInfo(tzname)
    now = datetime.datetime.now(timezone)

    return now.strftime("%H:%M"), now.strftime("%A, %d %B %Y")
