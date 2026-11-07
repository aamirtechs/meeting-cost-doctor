# Changelog

## 1.0.0 (2026-10-30)

- First release.
- Zero-dependency Python CLI: price a meeting from attendee hourly
  rates, with per-attendee cost, total cost, and cost per minute.
- Inputs: repeatable `--attendee "Name:rate"` flags and
  `--attendees-file` JSON, combined freely.
- Flags: `--duration` (fractions allowed), `--currency` (default
  USD, label only), `--json`, `--check` (nonzero exit on bad input),
  and `--tick` live mode with `--interval` seconds.
- 21 passing tests.
