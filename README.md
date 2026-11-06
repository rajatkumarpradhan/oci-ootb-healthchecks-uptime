# oci-ootb-healthchecks-uptime

An out-of-the-box OCI monitoring workflow: **probe a target with OCI Health Checks, then turn the raw probe results into an availability/SLO report**. Health Checks is OCI's built-in vantage-point monitoring feature - it probes a URL from OCI edge locations on an interval with no agent or custom poller to run. This repo wires the built-in part (Terraform) and adds the missing operational part: a local analyzer that computes availability, latency percentiles, and failure streaks from a results export and gates on an SLO.

## What it is

Two pieces:

1. **`infra/main.tf`** - Terraform template for an OCI Health Checks HTTP monitor (HTTPS protocol, 60s interval, multiple vantage points).
2. **`src/`** - an offline uptime CLI. It reads a static JSON export of probe results, reports per-target availability, mean/p95 latency, and longest failure streak, flags SLO breaches, and exits 2 when any target is below the SLO - usable as a release or daily posture gate.

## What it is NOT (honest limits)

- The Terraform template has **not** been plan/apply validated against a tenancy. It is a structural starting point; review it against the current OCI provider docs (vantage point names especially) before any real apply.
- The analyzer consumes a **static JSON export** (schema below, a simplification of Health Checks result fields). It does not call the OCI API; producing that export from a real tenancy is out of scope here.
- Statuses are reduced to OK vs FAILED/TIMEOUT; partial-content checks and DNS-level results are out of scope. p95 uses nearest-rank over the exported window only.
- The SLO (default 99.0%, tunable via `--slo`) is a local convention applied to the exported window, not an OCI concept; error budgets and alerting cadence are not modeled.
- No live probes, cost, or tenancy data are involved in any run of this repo.

## Input schema

```json
{
  "results": [
    {
      "target": "https://api.example.com/health",
      "vantage_point": "bom-1",
      "timestamp": "2026-11-06T00:00:00Z",
      "status": "OK",
      "latency_ms": 95
    }
  ]
}
```

`status` must be OK, FAILED, or TIMEOUT; TIMEOUT counts as a failure.

## Run

Requires Python 3.10+, no third-party dependencies.

```sh
PYTHONPATH=src python3 -m oci_ootb_healthchecks_uptime samples/healthcheck-results.json --slo 99.0
PYTHONPATH=src python3 -m oci_ootb_healthchecks_uptime samples/healthcheck-results-healthy.json
```

Or the end-to-end demo (seeded export -> healthy export, with expected exit codes):

```sh
sh demo.sh
```

Expected demo output: the seeded export shows api.example.com at 88.33% availability with a 7-probe failure streak, flags the SLO breach, and exits 2; the healthy export is 100% and exits 0.

## Test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

19 unit tests cover export validation, status handling, availability math, failure streaks (including per-target isolation), latency percentiles, SLO breach detection, and CLI exit codes. CI runs the same tests plus the demo on Python 3.10/3.11/3.12.
