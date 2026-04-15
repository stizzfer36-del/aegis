"""Monitoring / Observability — Prometheus / OpenTelemetry / Grafana integrations."""
from __future__ import annotations


class MonitoringTopic:
    name = "monitoring_observability"
    tools = ["prometheus", "grafana", "opentelemetry", "loki", "jaeger", "netdata", "signoz"]

    def start_otel_tracer(self, service_name: str = "aegis"):
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            provider = TracerProvider()
            trace.set_tracer_provider(provider)
            return trace.get_tracer(service_name)
        except ImportError:
            return None
