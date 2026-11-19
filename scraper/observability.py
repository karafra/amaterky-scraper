import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

from .storage import atomic_write


class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.requests = Counter("scraper_http_requests_total", "HTTP requests by status", ["status"], registry=self.registry)
        self.rate_limits = Counter("scraper_rate_limit_responses_total", "HTTP 429 responses", registry=self.registry)
        self.success = Gauge("scraper_run_success", "Whether the latest run succeeded", registry=self.registry)
        self.duration = Gauge("scraper_run_duration_seconds", "Duration of the latest run", registry=self.registry)
        self.records = Gauge("scraper_run_records", "Number of records in the latest run", registry=self.registry)
        self.finished = Gauge("scraper_run_finished_timestamp_seconds", "Time the latest run finished", registry=self.registry)

    def write(self, path):
        atomic_write(path, generate_latest(self.registry))


def configure_tracing():
    if not (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")):
        return None
    provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "amaterky-scraper")}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider
