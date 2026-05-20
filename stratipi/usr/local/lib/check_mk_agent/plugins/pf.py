#!/usr/bin/env python3
"""CheckMK local check plugin for pf (Packet Filter) firewall stats.

Parses output from `pfctl -s info` on FreeBSD and exposes metrics:
  - State table current entries
  - State table counters (searches, inserts, removals)
  - Filter statistics counters

References:
    https://docs.freebsd.org/en/books/pf/
    https://docs.checkmk.com/latest/en/localchecks.html
"""

import subprocess


def parse_line(line: str):
    try:
        line = line.replace('current entries', 'current-entries')
        parts = line.split()
        if len(parts) < 2:
            return (None, None, None)

        if len(parts) >= 3:
            val2 = float(parts[2].rstrip("/s"))
        else:
            val2 = None

        return (parts[0], int(parts[1]), val2)
    except:
        return (None, None, None)



def main():
    """Run pfctl -s info and output CheckMK metrics."""
    result = subprocess.run(
        ["pfctl", "-s", "info"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return

    for line in result.stdout.splitlines():
        # Only process indented lines (actual metrics)
        if not line.startswith(" "):
            continue

        name, val1, val2 = parse_line(line)
        if name is None:
            continue

        # Build metric name from the first column, replacing spaces with underscores
        metric_name = f"PF {name}".replace('-', ' ')

        # Build output string
        if val2 is not None:
            print(f'0 "{metric_name}" count={val1}|rate={val2} {val1} total, {val2}/s')
        else:
            print(f'0 "{metric_name}" count={val1} {val1} total')


if __name__ == "__main__":
    main()
