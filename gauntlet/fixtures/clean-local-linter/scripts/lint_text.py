#!/usr/bin/env python3
"""Style linter for plain text. Local only: reads one file, prints a report."""
import re
import sys


def lint(path):
    problems = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            if line.rstrip("\n") != line.rstrip():
                problems.append(f"{i}: trailing whitespace")
            if "  " in line.strip():
                problems.append(f"{i}: double space")
            if len(line.rstrip("\n")) > 100:
                problems.append(f"{i}: line over 100 chars")
    return problems


if __name__ == "__main__":
    for problem in lint(sys.argv[1]):
        print(problem)
