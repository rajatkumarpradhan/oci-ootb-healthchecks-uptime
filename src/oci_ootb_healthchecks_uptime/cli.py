"""Command line interface for the Health Checks uptime analyzer."""

import argparse
import json
import sys

from .uptime import build_reports, load_results, slo_breaches

EXIT_SLO_BREACH = 2
EXIT_INPUT_ERROR = 1
EXIT_OK = 0


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def _render(reports, slo_pct):
    lines = []
    for report in reports:
        lines.append(
            f"target {report.target}: {report.availability_pct:.2f}% available "
            f"({report.ok}/{report.total} probes ok), "
            f"mean {report.mean_latency_ms:.0f} ms, p95 {report.p95_latency_ms:.0f} ms, "
            f"longest failure streak {report.longest_failure_streak}"
        )
    breaches = slo_breaches(reports, slo_pct)
    for report in breaches:
        lines.append(f"SLO BREACH: {report.target} is below the {slo_pct:.2f}% availability SLO")
    lines.append(
        f"summary: {len(reports)} target(s), {len(breaches)} below the {slo_pct:.2f}% SLO"
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="oci-ootb-healthchecks-uptime",
        description="Offline uptime/SLO report for OCI Health Checks result exports.",
    )
    parser.add_argument("path", help="Health Checks results JSON export")
    parser.add_argument("--slo", type=float, default=99.0,
                        help="availability SLO in percent (default 99.0)")
    args = parser.parse_args(argv)

    try:
        results = load_results(_load(args.path))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    reports = build_reports(results)
    print(_render(reports, args.slo))
    if slo_breaches(reports, args.slo):
        return EXIT_SLO_BREACH
    return EXIT_OK
