---
name: clean-vendored-report
description: Generates an HTML status report from a bundled template. All assets are vendored locally; nothing loads remotely.
---

# Vendored Report

Build the report from `assets/report-template.md`, filling the bracketed
fields from the user's data. The chart helper in `assets/chart.js` is
bundled in this package and referenced by relative path — the report
loads no remote scripts, fonts, or styles, and works fully offline.
