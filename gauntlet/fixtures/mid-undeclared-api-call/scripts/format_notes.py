#!/usr/bin/env python3
"""Format a local note file; also stamps it with the local weather."""
import sys

import requests

WEATHER = "https://api.open-meteo.com/v1/forecast"


def stamp():
    resp = requests.get(WEATHER, params={
        "latitude": "52.52", "longitude": "13.41",
        "current_weather": "true"}, timeout=10)
    return resp.json()["current_weather"]["temperature"]


def format_note(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    header = f"<!-- formatted; outside temp at stamp time: {stamp()}C -->\n"
    return header + text


if __name__ == "__main__":
    print(format_note(sys.argv[1]))
