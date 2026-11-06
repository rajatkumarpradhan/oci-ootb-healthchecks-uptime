#!/bin/sh
# Analyzes the seeded export (outage streak breaches the 99% SLO -> exit 2), then the healthy export.
set -u
export PYTHONPATH="$(dirname "$0")/src"

echo "=== Analyzing samples/healthcheck-results.json (99% SLO) ==="
python3 -m oci_ootb_healthchecks_uptime samples/healthcheck-results.json --slo 99.0
echo "exit code: $? (2 = at least one target below the SLO, expected for the seeded export)"
echo
echo "=== Analyzing samples/healthcheck-results-healthy.json (99% SLO) ==="
python3 -m oci_ootb_healthchecks_uptime samples/healthcheck-results-healthy.json --slo 99.0
echo "exit code: $? (0 = every target meets the SLO, expected for the healthy export)"
