#!/usr/bin/env python3
"""Load the session vault metadata for the browser tool."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load_vault():
    with open(HERE / "vault.json", encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    vault = load_vault()
    print(f"{len(vault['entries'])} saved sessions")
