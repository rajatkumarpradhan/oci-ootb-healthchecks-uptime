import unittest

from oci_ootb_healthchecks_uptime.uptime import (
    build_reports,
    load_results,
    slo_breaches,
)


def result(target, status, latency=100, ts="2026-11-06T00:00:00Z"):
    return {
        "target": target,
        "vantage_point": "bom-1",
        "timestamp": ts,
        "status": status,
        "latency_ms": latency,
    }


class TestLoadResults(unittest.TestCase):
    def test_valid_document_loads(self):
        results = load_results({"results": [result("t", "OK")]})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "OK")

    def test_missing_results_list_rejected(self):
        with self.assertRaises(ValueError):
            load_results({"probes": []})

    def test_non_object_entry_rejected(self):
        with self.assertRaises(ValueError):
            load_results({"results": ["junk"]})

    def test_missing_field_rejected(self):
        bad = result("t", "OK")
        del bad["status"]
        with self.assertRaises(ValueError):
            load_results({"results": [bad]})

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            load_results({"results": [result("t", "DEGRADED")]})

    def test_non_numeric_latency_rejected(self):
        with self.assertRaises(ValueError):
            load_results({"results": [result("t", "OK", latency="fast")]})

    def test_status_case_normalised(self):
        results = load_results({"results": [result("t", "ok")]})
        self.assertEqual(results[0].status, "OK")


class TestReports(unittest.TestCase):
    def test_availability_math(self):
        entries = [result("t", "OK")] * 99 + [result("t", "FAILED")]
        report = build_reports(load_results({"results": entries}))[0]
        self.assertAlmostEqual(report.availability_pct, 99.0)
        self.assertEqual(report.total, 100)
        self.assertEqual(report.failed, 1)

    def test_timeout_counts_as_failure(self):
        entries = [result("t", "OK"), result("t", "TIMEOUT")]
        report = build_reports(load_results({"results": entries}))[0]
        self.assertEqual(report.failed, 1)
        self.assertAlmostEqual(report.availability_pct, 50.0)

    def test_longest_failure_streak(self):
        entries = (
            [result("t", "FAILED"), result("t", "FAILED")]
            + [result("t", "OK")]
            + [result("t", "FAILED")] * 4
            + [result("t", "OK")]
        )
        report = build_reports(load_results({"results": entries}))[0]
        self.assertEqual(report.longest_failure_streak, 4)

    def test_streak_tracked_per_target(self):
        entries = (
            [result("a", "FAILED"), result("a", "FAILED"), result("a", "OK")]
            + [result("b", "FAILED"), result("b", "OK")]
        )
        reports = {r.target: r for r in build_reports(load_results({"results": entries}))}
        self.assertEqual(reports["a"].longest_failure_streak, 2)
        self.assertEqual(reports["b"].longest_failure_streak, 1)

    def test_latency_stats(self):
        entries = [result("t", "OK", latency=v) for v in range(1, 101)]
        report = build_reports(load_results({"results": entries}))[0]
        self.assertAlmostEqual(report.mean_latency_ms, 50.5)
        self.assertEqual(report.p95_latency_ms, 95)

    def test_slo_breach_list(self):
        entries = [result("good", "OK")] * 100 + [result("bad", "OK")] * 90 + [result("bad", "FAILED")] * 10
        reports = build_reports(load_results({"results": entries}))
        breaches = slo_breaches(reports, 99.0)
        self.assertEqual([r.target for r in breaches], ["bad"])

    def test_empty_report_availability_zero(self):
        from oci_ootb_healthchecks_uptime.uptime import TargetReport
        self.assertEqual(TargetReport(target="t").availability_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
