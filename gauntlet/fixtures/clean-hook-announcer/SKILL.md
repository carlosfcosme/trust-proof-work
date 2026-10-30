---
name: clean-hook-announcer
description: Formatting helper with one disclosed local hook: after load it runs a bundled script that prints a banner.
hooks: PostLoad: scripts/announce.sh
---

# Formatter With A Banner

Hook disclosure: when this skill loads, the declared hook runs
`scripts/announce.sh`, a bundled two-line shell script that prints a
banner so the user knows the formatter is active. The script is in this
package, does nothing else, and touches no files and no network.

After the banner, help the user normalize heading levels in their draft.
