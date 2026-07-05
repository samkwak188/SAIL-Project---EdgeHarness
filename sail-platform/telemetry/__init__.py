"""telemetry package — per-call JSONL recorder + cost/latency report."""
from telemetry.recorder import TelemetryRecorder
from telemetry.report import report

__all__ = ["TelemetryRecorder", "report"]
