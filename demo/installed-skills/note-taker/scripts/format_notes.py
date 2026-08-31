#!/usr/bin/env python3
"""Print dated Markdown notes for one transcript file."""

import datetime
import sys

DECISION_MARKERS = ("we decided", "decision:", "agreed")
ACTION_MARKERS = ("action:", "todo", "will follow up")


def sections(lines: list) -> dict:
    out = {"Decisions": [], "Actions": [], "Notes": []}
    for line in lines:
        low = line.lower()
        if any(marker in low for marker in DECISION_MARKERS):
            out["Decisions"].append(line)
        elif any(marker in low for marker in ACTION_MARKERS):
            out["Actions"].append(line)
        else:
            out["Notes"].append(line)
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: format_notes.py TRANSCRIPT.txt", file=sys.stderr)
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]
    print(f"# Notes -- {datetime.date.today().isoformat()}\n")
    for heading, body in sections(lines).items():
        if not body:
            continue
        print(f"## {heading}\n")
        for item in body:
            print(f"- {item}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
