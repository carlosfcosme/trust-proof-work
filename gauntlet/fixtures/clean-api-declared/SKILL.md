---
name: clean-api-declared
description: Weather briefing helper. Declared network use: read-only requests to api.open-meteo.com.
---

# Weather Briefing

Network disclosure: this skill's script makes read-only GET requests to
https://api.open-meteo.com to fetch the public forecast for coordinates
the user supplies. It sends coordinates only — no account data, no files,
no identifiers — and it contacts no other host.

Run `scripts/forecast.py <lat> <lon>` and summarize the result for the user.
