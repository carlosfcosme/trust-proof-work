#!/usr/bin/env python3
"""Expand a team abbreviation from the bundled table. Lookup only."""
import sys

TABLE = {"api": "application programming interface",
         "sdk": "software development kit",
         "cli": "command line interface"}


if __name__ == "__main__":
    print(TABLE.get(sys.argv[1].lower(), "unknown abbreviation"))
