# backend/telemetry.py
"""OpenTelemetry tracing wiring (arch 2.6 Observability & Telemetry).

Tracing is opt-in and best-effort. Controlled by OTEL_EXPORTER:
  * none    (default) — no tracing, no console noise
  * console           — dev only: prints spans to stdout
  * otlp              — production: ships spans to OTEL_EXPORTER_ENDPOINT

If the OTel packages or the exporter are unavailable the app still runs.
"""
from __future__ import annotations

import logging

from config import settings

log = logging.getLogger("talamanda.telemetry")


def instrument_app(app) -> None:
    mode = (settings.otel_exporter or "none").lower()
    if mode == "none":
        log.info("OpenTelemetry tracing disabled (OTEL_EXPORTER=none).")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        if mode == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        elif mode == "otlp":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            endpoint = settings.otel_exporter_endpoint
            exporter = OTLPSpanExporter(endpoint=endpoint) if endpoint else OTLPSpanExporter()
        else:
            log.warning("Unknown OTEL_EXPORTER=%r; tracing disabled.", mode)
            return

        provider = TracerProvider(
            resource=Resource.create({"service.name": "talamanda-trust-layer"})
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("OpenTelemetry tracing enabled (exporter=%s).", mode)
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("Telemetry not enabled: %s", exc)
