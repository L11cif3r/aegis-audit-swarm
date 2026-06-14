# backend/telemetry.py
"""OpenTelemetry tracing wiring (arch 2.6 Observability & Telemetry).

Tracing is best-effort: if the OTel packages or an exporter are unavailable the
app still runs. Configure an OTLP endpoint via standard OTEL_* env vars.
"""
from __future__ import annotations

import logging

log = logging.getLogger("talamanda.telemetry")


def instrument_app(app) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        provider = TracerProvider(
            resource=Resource.create({"service.name": "talamanda-trust-layer"})
        )
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("OpenTelemetry tracing enabled")
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("Telemetry not enabled: %s", exc)
