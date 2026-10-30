---
name: clean-local-linter
description: Local text style linter. Runs one bundled Python script on a file the user names. No network use.
allowed-tools: Read
---

# Local Linter

Ask the user to run `scripts/lint_text.py <file>` (or run it via the
editor's script runner) to check a text file for double spaces, trailing
whitespace, and over-long lines. The script is bundled in this package,
reads only the file named on the command line, and prints a report.
It makes no network calls and writes nothing.
