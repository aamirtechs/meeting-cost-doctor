# Good first issues

Small, testable tasks for first-time contributors. No network access needed.

1. Add a `--round-to` option that rounds each attendee cost up to the
   nearest whole currency unit, with the total recomputed from the
   rounded figures. Scope: add the flag, apply it in the report
   builder, add tests.
2. Accept a CSV attendees file in addition to JSON, with `name,rate`
   columns, picked by file extension. Scope: add a CSV loader, reuse
   the same validation, add tests.
3. Add a `--summary-only` flag that prints just the total and the
   cost per minute, skipping the per-attendee lines. Scope: add the
   flag, adjust the text formatter, add a CLI test.
4. In tick mode, print a final per-attendee breakdown after the
   "Done" line, matching the normal report format. Scope: reuse the
   report builder in tick mode, add a CLI test with tiny
   interval and duration.
