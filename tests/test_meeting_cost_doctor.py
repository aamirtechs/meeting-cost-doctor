import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meeting_cost_doctor as mcd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "meeting_cost_doctor.py")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, SCRIPT] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )


def write_attendees_file(entries):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(entries, handle)
    handle.close()
    return handle.name


class TestCostMath(unittest.TestCase):
    def test_single_attendee_cost(self):
        self.assertEqual(mcd.attendee_cost(120, 30), 60.0)

    def test_per_attendee_costs_in_report(self):
        report = mcd.build_report(
            [{"name": "Alice", "rate": 100}, {"name": "Bob", "rate": 60}], 30, "USD"
        )
        self.assertEqual(report["attendees"][0]["cost"], 50.0)
        self.assertEqual(report["attendees"][1]["cost"], 30.0)

    def test_total_cost(self):
        report = mcd.build_report(
            [{"name": "Alice", "rate": 100}, {"name": "Bob", "rate": 60}], 30, "USD"
        )
        self.assertEqual(report["total_cost"], 80.0)

    def test_cost_per_minute(self):
        report = mcd.build_report(
            [{"name": "Alice", "rate": 100}, {"name": "Bob", "rate": 60}], 30, "USD"
        )
        self.assertAlmostEqual(report["cost_per_minute"], 2.67, places=2)

    def test_fractional_duration(self):
        # 0.1 minutes at 120/hr is 0.20, the tiny value tests use.
        self.assertAlmostEqual(mcd.attendee_cost(120, 0.1), 0.20, places=2)

    def test_zero_rate_costs_nothing(self):
        self.assertEqual(mcd.attendee_cost(0, 30), 0.0)


class TestOutputFormats(unittest.TestCase):
    def test_currency_label_in_text_output(self):
        report = mcd.build_report([{"name": "Alice", "rate": 100}], 30, "EUR")
        text = mcd.format_report(report)
        self.assertIn("EUR", text)
        self.assertIn("Alice", text)
        self.assertIn("50.00", text)

    def test_currency_label_in_json_output(self):
        result = run_cli(
            "--attendee", "Alice:100", "--duration", "30", "--currency", "EUR", "--json"
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["currency"], "EUR")
        self.assertEqual(data["total_cost"], 50.0)
        self.assertEqual(data["attendees"][0]["name"], "Alice")

    def test_json_output_structure(self):
        result = run_cli(
            "--attendee", "Alice:100",
            "--attendee", "Bob:60",
            "--duration", "30",
            "--json",
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["duration_minutes"], 30.0)
        self.assertEqual(len(data["attendees"]), 2)
        self.assertEqual(data["total_cost"], 80.0)
        self.assertAlmostEqual(data["cost_per_minute"], 2.67, places=2)

    def test_text_output_shows_per_attendee_and_total(self):
        result = run_cli(
            "--attendee", "Alice:100", "--attendee", "Bob:60", "--duration", "30"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Alice", result.stdout)
        self.assertIn("Bob", result.stdout)
        self.assertIn("Total: 80.00 USD", result.stdout)
        self.assertIn("Cost per minute: 2.67 USD", result.stdout)


class TestAttendeesFile(unittest.TestCase):
    def test_attendees_file_loading(self):
        path = write_attendees_file(
            [{"name": "Alice", "rate": 100}, {"name": "Bob", "rate": 60}]
        )
        try:
            attendees = mcd.load_attendees_file(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(attendees), 2)
        self.assertEqual(attendees[0]["name"], "Alice")
        self.assertEqual(attendees[1]["rate"], 60)

    def test_flag_and_file_attendees_combine(self):
        path = write_attendees_file([{"name": "Bob", "rate": 60}])
        try:
            result = run_cli(
                "--attendee", "Alice:100",
                "--attendees-file", path,
                "--duration", "30",
                "--json",
            )
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["attendees"]), 2)
        self.assertEqual(data["total_cost"], 80.0)


class TestCheckMode(unittest.TestCase):
    def test_check_valid_exits_zero(self):
        result = run_cli(
            "--attendee", "Alice:100", "--duration", "30", "--check"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK", result.stdout)

    def test_check_negative_rate_exits_nonzero(self):
        result = run_cli(
            "--attendee", "Alice:-5", "--duration", "30", "--check"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("negative", result.stderr)

    def test_check_bad_flag_format_exits_nonzero(self):
        result = run_cli("--attendee", "Alice100", "--duration", "30", "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("format", result.stderr)

    def test_check_nonpositive_duration_exits_nonzero(self):
        result = run_cli("--attendee", "Alice:100", "--duration", "0", "--check")
        self.assertNotEqual(result.returncode, 0)
        result = run_cli("--attendee", "Alice:100", "--duration", "-10", "--check")
        self.assertNotEqual(result.returncode, 0)

    def test_check_bad_file_entry_exits_nonzero(self):
        path = write_attendees_file([{"name": "Alice"}])
        try:
            result = run_cli(
                "--attendees-file", path, "--duration", "30", "--check"
            )
        finally:
            os.unlink(path)
        self.assertNotEqual(result.returncode, 0)

    def test_no_attendees_exits_nonzero(self):
        result = run_cli("--duration", "30")
        self.assertNotEqual(result.returncode, 0)


class TestTickMode(unittest.TestCase):
    def test_tick_lines_increase_with_elapsed_time(self):
        attendees = [{"name": "Alice", "rate": 120}]
        # 0.1 minutes is 6 seconds; 1 second ticks give costs 2, 4, ... 12.
        lines = mcd.tick_lines(attendees, 0.1, 1.0, sleep=lambda s: None)
        costs = [float(re.search(r"([\d.]+)$", line).group(1)) for line in lines]
        self.assertGreater(len(costs), 1)
        for earlier, later in zip(costs, costs[1:]):
            self.assertGreater(later, earlier)

    def test_tick_final_cost_equals_total(self):
        attendees = [{"name": "Alice", "rate": 120}]
        lines = mcd.tick_lines(attendees, 0.1, 0.05, sleep=lambda s: None)
        last_cost = float(re.search(r"([\d.]+)$", lines[-1]).group(1))
        self.assertAlmostEqual(last_cost, mcd.attendee_cost(120, 0.1), places=2)

    def test_tick_cli_short_run(self):
        # Real run: 0.02 minutes (1.2 seconds) at 0.4 second intervals.
        result = run_cli(
            "--attendee", "Alice:120",
            "--duration", "0.02",
            "--tick", "--interval", "0.4",
        )
        self.assertEqual(result.returncode, 0)
        elapsed_lines = [line for line in result.stdout.splitlines()
                         if line.startswith("Elapsed")]
        self.assertGreaterEqual(len(elapsed_lines), 2)
        costs = [float(re.search(r"([\d.]+) USD$", line).group(1))
                 for line in elapsed_lines]
        for earlier, later in zip(costs, costs[1:]):
            self.assertGreater(later, earlier)
        self.assertIn("Done: total", result.stdout)


if __name__ == "__main__":
    unittest.main()
