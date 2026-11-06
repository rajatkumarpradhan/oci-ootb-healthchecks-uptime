# OCI Health Checks wiring for the uptime workflow (template; NOT applied).
#
# OCI Health Checks is the out-of-the-box OCI vantage-point monitoring
# feature: it probes a target URL from OCI edge locations on an interval and
# records per-probe results. This template defines one HTTP monitor; the
# local analyzer in src/ turns an export of those results into an
# availability/SLO report.
#
# This file has NOT been plan/apply validated against a tenancy - it is a
# structural template. Review against the current provider docs before any
# real apply.

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
}

variable "compartment_ocid" {
  type        = string
  description = "OCID of the compartment that owns the monitor"
}

variable "target_url" {
  type        = string
  description = "HTTPS URL the monitor should probe, e.g. https://api.example.com/health"
}

resource "oci_health_checks_http_monitor" "uptime" {
  compartment_id      = var.compartment_ocid
  display_name        = "uptime-monitor"
  protocol            = "HTTPS"
  targets             = [var.target_url]
  path                = "/"
  interval_in_seconds = 60
  timeout_in_seconds  = 10
  is_enabled          = true
  vantage_point_names = ["aws-bom", "aws-hyd", "gcp-chu"]
}
