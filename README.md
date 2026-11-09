# meeting-cost-doctor
**Live tool:** https://aamirtechs.github.io/meeting-cost-doctor/ (runs in your browser, no install)

Price a meeting from attendee hourly rates, fully locally. Give it
attendee rates and a duration, and it prints each person's cost, the
total cost, and the cost per minute. No account, no upload, no
dependencies, no network access.

Cost math is one formula: cost = rate x minutes / 60, per attendee.

## Input

Repeatable `--attendee` flags in `Name:rate` form, or a JSON file
holding a list of `{"name": ..., "rate": ...}` objects. Both can be
combined. Duration is in minutes, and fractions are allowed, so
`--duration 0.1` means six seconds.

`examples/team.json`:

```json
[{"name":"Alice","rate":90},{"name":"Bob","rate":60},{"name":"Carol","rate":120}]
```

## Usage

```sh
python3 meeting_cost_doctor.py --attendee "Alice:100" --attendee "Bob:60" --duration 30
python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 45
python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 30 --json
python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 30 --check
python3 meeting_cost_doctor.py --attendees-file examples/team.json --duration 30 --tick --interval 60
```

Flags:

- `--attendee "Name:rate"`: one attendee, repeatable.
- `--attendees-file FILE`: JSON list of `{"name", "rate"}` objects.
- `--duration MINUTES`: meeting length in minutes, required, must be positive.
- `--currency LABEL`: currency label printed with amounts, default `USD`.
  It is only a label, not a conversion.
- `--json`: machine-readable JSON output instead of text.
- `--check`: validate inputs only. Prints an OK line and exits 0 when
  inputs are valid; prints an error and exits nonzero on bad input
  (unknown attendee format, negative rate, non-positive duration, or
  a bad attendees file).
- `--tick`: live mode. Prints elapsed time and running cost every
  `--interval` seconds until the duration elapses.
- `--interval SECONDS`: seconds between ticks in live mode, default 60.
  Fractions are allowed, so short test runs need no real waiting.

## Real examples

Running it on `examples/team.json` for 30 minutes gives:

```
Meeting cost (USD)
====================
Alice: 90.00/hr x 30.0 min = 45.00 USD
Bob: 60.00/hr x 30.0 min = 30.00 USD
Carol: 120.00/hr x 30.0 min = 60.00 USD
Total: 135.00 USD
Cost per minute: 4.50 USD
```

The same run with `--json`:

```
{
  "currency": "USD",
  "duration_minutes": 30.0,
  "attendees": [
    {
      "name": "Alice",
      "rate": 90.0,
      "cost": 45.0
    },
    {
      "name": "Bob",
      "rate": 60.0,
      "cost": 30.0
    },
    {
      "name": "Carol",
      "rate": 120.0,
      "cost": 60.0
    }
  ],
  "total_cost": 135.0,
  "cost_per_minute": 4.5
}
```

A short live tick run (`--duration 0.02 --tick --interval 0.4`,
1.2 seconds of real time) gives:

```
Elapsed 0.4s: 0.03 USD
Elapsed 0.8s: 0.06 USD
Elapsed 1.2s: 0.09 USD
Done: total 0.09 USD
```

Validation with `--check` on the same file gives:

```
OK: 3 attendees, 30.0 minutes, total 135.00 USD
```

## Tests

```sh
python3 -m pytest tests/ -q
```

21 tests, covering per-attendee math, totals, cost per minute,
currency labels in text and JSON output, attendees file loading,
combined flag and file input, `--check` exit codes for bad format,
negative rate, non-positive duration, bad file entries, and missing
attendees, fractional durations, and a short live tick run with tiny
interval and duration asserting increasing cost lines.

## Limitations

- Rates are taken as given. The tool does not look up salaries,
  benefits, or overhead, so the total is the cost of the hourly rates
  you supply, nothing more.
- `--currency` is a label only. It does not convert between
  currencies and does not fetch exchange rates.
- Tick mode measures wall-clock time from when the command starts.
  It does not track whether attendees actually joined or stayed.
- Cost figures are rounded to two decimals for display. Very short
  tick intervals can round to 0.00 even though the true cost is
  slightly above zero.

## License

MIT. See `LICENSE`.
