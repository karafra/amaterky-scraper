import json
import logging
from pathlib import Path
import time
from urllib.parse import urljoin

from opentelemetry import trace

from .http import DEFAULT_USER_AGENT, HttpClient
from .observability import Metrics
from .parsing import attr, parse_detail, text
from .storage import atomic_write


LOG = logging.getLogger("scraper")


class Scraper:
    def __init__(self, base_url, data_dir, interval=5.0, retries=3, fallback=60.0, jitter=2.0, user_agent=DEFAULT_USER_AGENT):
        self.base_url = base_url
        self.data_dir = Path(data_dir)
        self.metrics = Metrics()
        self.client = HttpClient(base_url, self.data_dir, self.metrics, interval, retries, fallback, jitter, user_agent)
        self.tracer = trace.get_tracer("amaterky.scraper")

    def get(self, url):
        return self.client.get(url, self.tracer)

    def collect(self):
        LOG.info("Fetching listing page")
        doc = self.get(self.base_url)
        offers = doc.select(".col.offer")
        if not offers:
            raise RuntimeError("No offers found; refusing to replace previous data")
        LOG.info("Found %d listings", len(offers))
        results = []
        for index, offer in enumerate(offers, start=1):
            link = offer.select_one(".offer-title a")
            href = attr(link, "href")
            if not href:
                raise ValueError("Offer is missing a profile URL")
            url = urljoin(self.base_url, href)
            LOG.info("Fetching profile %d/%d", index, len(offers))
            with self.tracer.start_as_current_span("scrape.profile"):
                results.append({
                    "title": text(link),
                    "url": url,
                    "image": attr(offer.select_one(".offer-image"), "src"),
                    "location": text(offer.select_one(".offer-location")),
                    "availability": text(offer.select_one(".offer-availability")),
                    "details": parse_detail(self.get(url)),
                })
            LOG.info("Completed profile %d/%d", index, len(offers))
        return results

    def run(self):
        started = time.monotonic()
        LOG.info("Starting scrape; output directory: %s", self.data_dir)
        try:
            with self.tracer.start_as_current_span("scrape.run"):
                results = self.collect()
                output_path = self.data_dir / "scraper.json"
                atomic_write(output_path, json.dumps(results, ensure_ascii=False).encode())
                self.metrics.records.set(len(results))
                self.metrics.success.set(1)
                LOG.info("Saved %d listings to %s in %.1f seconds", len(results), output_path, time.monotonic() - started)
        finally:
            self.metrics.duration.set(time.monotonic() - started)
            self.metrics.finished.set(time.time())
            try:
                self.metrics.write(self.data_dir / "metrics.prom")
                LOG.info("Wrote metrics to %s", self.data_dir / "metrics.prom")
            finally:
                self.client.session.close()
