"""Uptime computation for OCI Health Checks vantage-point results.

OCI Health Checks (an out-of-the-box OCI monitoring feature) probes a target
from multiple vantage points on an interval and records per-probe results.
This module works on a static JSON export of those results: per target it
computes availability, latency percentiles and the longest failure streak,
then compares availability against an SLO. All analysis is offline.
"""

from dataclasses import dataclass, field

OK_STATUSES = ("OK",)
FAIL_STATUSES = ("FAILED", "TIMEOUT")
VALID_STATUSES = OK_STATUSES + FAIL_STATUSES


@dataclass(frozen=True)
class ProbeResult:
    target: str
    vantage_point: str
    timestamp: str
    status: str
    latency_ms: float


@dataclass
class TargetReport:
    target: str
    total: int = 0
    ok: int = 0
    failed: int = 0
    latencies: list = field(default_factory=list)
    longest_failure_streak: int = 0

    @property
    def availability_pct(self):
        if self.total == 0:
            return 0.0
        return 100.0 * self.ok / self.total

    @property
    def mean_latency_ms(self):
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self):
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        # Nearest-rank percentile.
        rank = max(1, -(-95 * len(ordered) // 100))
        return ordered[rank - 1]


def _parse_result(raw):
    if not isinstance(raw, dict):
        raise ValueError("each result entry must be an object")
    try:
        status = str(raw["status"]).upper()
        latency = raw["latency_ms"]
        return ProbeResult(
            target=str(raw["target"]),
            vantage_point=str(raw.get("vantage_point", "<unknown>")),
            timestamp=str(raw.get("timestamp", "")),
            status=status,
            latency_ms=float(latency),
        )
    except KeyError as exc:
        raise ValueError(f"result entry missing required field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"result entry has a non-numeric latency_ms: {raw.get('latency_ms')!r}") from exc


def load_results(document):
    if not isinstance(document, dict) or not isinstance(document.get("results"), list):
        raise ValueError("document must contain a top-level 'results' list")
    results = [_parse_result(raw) for raw in document["results"]]
    for result in results:
        if result.status not in VALID_STATUSES:
            raise ValueError(f"result for target {result.target} has unknown status '{result.status}'")
    return results


def build_reports(results):
    """Aggregate per-target reports in first-seen target order."""
    reports = {}
    streaks = {}
    for result in results:
        report = reports.setdefault(result.target, TargetReport(target=result.target))
        report.total += 1
        report.latencies.append(result.latency_ms)
        if result.status in OK_STATUSES:
            report.ok += 1
            streaks[result.target] = 0
        else:
            report.failed += 1
            streaks[result.target] = streaks.get(result.target, 0) + 1
            report.longest_failure_streak = max(report.longest_failure_streak, streaks[result.target])
    return list(reports.values())


def slo_breaches(reports, slo_pct):
    """Targets whose availability is below the SLO."""
    return [r for r in reports if r.availability_pct < slo_pct]
