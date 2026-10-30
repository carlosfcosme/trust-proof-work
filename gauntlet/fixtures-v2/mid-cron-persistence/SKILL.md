---
name: mid-cron-persistence
description: Daily briefing. Installs a scheduled job (cron, weekdays 7am) so your briefing is ready when you wake up. The schedule entry is shown during setup and can be removed with `--uninstall`.
---

# Daily Briefing

Setup adds this crontab line (shown to you before it is written):

0 7 * * 1-5 briefing run --quiet
