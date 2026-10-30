#!/usr/bin/env python3
"""Fetch a public forecast from api.open-meteo.com (declared in SKILL.md)."""
import json
import sys

import requests

URL = "https://api.open-meteo.com/v1/forecast"


def forecast(lat, lon):
    resp = requests.get(URL, params={
        "latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print(json.dumps(forecast(sys.argv[1], sys.argv[2]), indent=2))
