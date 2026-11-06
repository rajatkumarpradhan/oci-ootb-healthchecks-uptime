import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout

from oci_ootb_healthchecks_uptime.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCli(unittest.TestCase):
    def test_missing_file_exits_1(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["/nonexistent/results.json"]), 1)

    def test_invalid_json_exits_1(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main([os.path.join(ROOT, "pyproject.toml")]), 1)

    def test_seeded_export_exits_2_and_names_breach(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([os.path.join(ROOT, "samples", "healthcheck-results.json")])
        self.assertEqual(code, 2)
        text = out.getvalue()
        self.assertIn("SLO BREACH: https://api.example.com/health", text)
        self.assertIn("https://cdn.example.com/status: 100.00% available", text)
        self.assertIn("summary:", text)

    def test_healthy_export_exits_0(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([os.path.join(ROOT, "samples", "healthcheck-results-healthy.json")])
        self.assertEqual(code, 0)
        self.assertIn("0 below", out.getvalue())

    def test_looser_slo_passes_seeded_export(self):
        with redirect_stdout(io.StringIO()):
            code = main([os.path.join(ROOT, "samples", "healthcheck-results.json"), "--slo", "85.0"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
