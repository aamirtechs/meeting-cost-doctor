#!/usr/bin/env python3
"""Price a meeting from attendee hourly rates, fully locally.

Inputs are repeatable --attendee "Name:rate" flags, or a JSON file
holding a list of {"name": ..., "rate": ...} objects, plus a duration
in minutes (fractions allowed). Output is the per-attendee cost, the
total cost, and the cost per minute. Cost math is simple:

    cost = rate * minutes / 60 per attendee

No network access, no dependencies, no data leaves the machine.

Usage:

    python3 meeting_cost_doctor.py --attendee "Alice:100" --attendee "Bob:60" --duration 30
    python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 45 --json
    python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 30 --check
    python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 30 --tick --interval 60
"""

import argparse
import json
import sys
import time


class InputError(ValueError):
    """Raised for any bad user input (bad format, bad rate, bad duration)."""


def attendee_cost(rate, minutes):
    """Cost for one attendee: rate (per hour) times minutes over 60."""
    return rate * minutes / 60.0


def total_cost(attendees, minutes):
    """Sum of every attendee's cost for the given minutes."""
    return sum(attendee_cost(a["rate"], minutes) for a in attendees)


def cost_per_minute(attendees):
    """Total burn rate: sum of hourly rates divided by 60."""
    return sum(a["rate"] for a in attendees) / 60.0


def parse_attendee_flag(text):
    """Parse one --attendee "Name:rate" flag into a {"name", "rate"} dict."""
    if ":" not in text:
        raise InputError(
            "bad attendee format %r: expected Name:rate, e.g. Alice:100" % text
        )
    name, rate_text = text.rsplit(":", 1)
    name = name.strip()
    if not name:
        raise InputError("bad attendee format %r: name is empty" % text)
    try:
        rate = float(rate_text)
    except ValueError:
        raise InputError(
            "bad attendee format %r: rate %r is not a number" % (text, rate_text)
        )
    if rate < 0:
        raise InputError("bad attendee %r: rate must not be negative" % text)
    return {"name": name, "rate": rate}


def load_attendees_file(path):
    """Load a JSON list of {"name": ..., "rate": ...} objects from a file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise InputError("cannot read attendees file %s: %s" % (path, exc))
    except json.JSONDecodeError as exc:
        raise InputError("attendees file %s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, list):
        raise InputError("attendees file %s must hold a JSON list" % path)
    attendees = []
    for entry in data:
        if not isinstance(entry, dict) or "name" not in entry or "rate" not in entry:
            raise InputError(
                "bad entry in %s: every entry needs name and rate" % path
            )
        try:
            rate = float(entry["rate"])
        except (TypeError, ValueError):
            raise InputError(
                "bad entry in %s: rate %r is not a number" % (path, entry["rate"])
            )
        if rate < 0:
            raise InputError("bad entry in %s: rate must not be negative" % path)
        attendees.append({"name": str(entry["name"]), "rate": rate})
    return attendees


def validate(attendees, minutes):
    """Validate inputs. Raises InputError on the first problem found."""
    if not attendees:
        raise InputError("no attendees given: use --attendee or --attendees-file")
    for attendee in attendees:
        if attendee["rate"] < 0:
            raise InputError(
                "bad attendee %s: rate must not be negative" % attendee["name"]
            )
    if minutes is None or minutes <= 0:
        raise InputError("duration must be a positive number of minutes")


def build_report(attendees, minutes, currency):
    """Build the cost report dict for the given attendees and minutes."""
    per_attendee = [
        {
            "name": a["name"],
            "rate": a["rate"],
            "cost": round(attendee_cost(a["rate"], minutes), 2),
        }
        for a in attendees
    ]
    return {
        "currency": currency,
        "duration_minutes": minutes,
        "attendees": per_attendee,
        "total_cost": round(total_cost(attendees, minutes), 2),
        "cost_per_minute": round(cost_per_minute(attendees), 2),
    }


def format_report(report):
    """Render a report dict as human-readable text."""
    lines = ["Meeting cost (%s)" % report["currency"], "=" * 20]
    for attendee in report["attendees"]:
        lines.append(
            "%s: %.2f/hr x %s min = %.2f %s"
            % (
                attendee["name"],
                attendee["rate"],
                report["duration_minutes"],
                attendee["cost"],
                report["currency"],
            )
        )
    lines.append("Total: %.2f %s" % (report["total_cost"], report["currency"]))
    lines.append(
        "Cost per minute: %.2f %s"
        % (report["cost_per_minute"], report["currency"])
    )
    return "\n".join(lines)


def tick_lines(attendees, duration_minutes, interval_seconds, sleep=time.sleep):
    """Yield tick lines for a live run, one per interval until duration ends.

    Each line shows elapsed seconds and the running total cost at that
    point. The sleep function is injectable so tests can drive the loop
    without waiting: pass sleep=lambda seconds: None.
    """
    if interval_seconds <= 0:
        raise InputError("interval must be a positive number of seconds")
    elapsed = 0.0
    duration_seconds = duration_minutes * 60.0
    lines = []
    while elapsed < duration_seconds:
        step = min(interval_seconds, duration_seconds - elapsed)
        sleep(step)
        elapsed += step
        cost = total_cost(attendees, elapsed / 60.0)
        lines.append("Elapsed %gs: %.2f" % (elapsed, cost))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Price a meeting from attendee hourly rates."
    )
    parser.add_argument(
        "--attendee",
        action="append",
        default=[],
        help='one attendee as "Name:rate", repeatable',
    )
    parser.add_argument(
        "--attendees-file",
        help="JSON file holding a list of {name, rate} objects",
    )
    parser.add_argument(
        "--duration",
        type=float,
        required=True,
        help="meeting length in minutes (fractions allowed)",
    )
    parser.add_argument(
        "--currency", default="USD", help="currency label printed with amounts"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate inputs only, exit nonzero on bad input",
    )
    parser.add_argument(
        "--tick",
        action="store_true",
        help="live mode: print running cost every --interval seconds",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="seconds between ticks in live mode (default 60)",
    )
    args = parser.parse_args(argv)

    try:
        attendees = [parse_attendee_flag(flag) for flag in args.attendee]
        if args.attendees_file:
            attendees.extend(load_attendees_file(args.attendees_file))
        validate(attendees, args.duration)
        if args.tick and args.interval <= 0:
            raise InputError("interval must be a positive number of seconds")
    except InputError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2

    if args.check:
        report = build_report(attendees, args.duration, args.currency)
        print(
            "OK: %d attendees, %s minutes, total %.2f %s"
            % (
                len(attendees),
                args.duration,
                report["total_cost"],
                args.currency,
            )
        )
        return 0

    if args.tick:
        lines = tick_lines(attendees, args.duration, args.interval)
        for line in lines:
            print("%s %s" % (line, args.currency))
        report = build_report(attendees, args.duration, args.currency)
        print("Done: total %.2f %s" % (report["total_cost"], args.currency))
        return 0

    report = build_report(attendees, args.duration, args.currency)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
