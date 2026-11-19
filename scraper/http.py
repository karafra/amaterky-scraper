from datetime import timezone
from email.utils import parsedate_to_datetime
import logging
import math
import random
import time
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import requests

from .storage import atomic_write


LOG = logging.getLogger("scraper")
DEFAULT_USER_AGENT = "amaterky-scraper/0.1"


def retry_after(value: str | None, now: float, fallback: float) -> float:
    if value:
        try:
            seconds = float(value)
            if math.isfinite(seconds) and seconds >= 0:
                return seconds
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                return max(0.0, date.timestamp() - now)
            except (TypeError, ValueError, OverflowError):
                pass
    return fallback


class HttpClient:
    def __init__(self, base_url, data_dir, metrics, interval, retries, fallback, jitter=2.0, user_agent=DEFAULT_USER_AGENT):
        self.origin = urlsplit(base_url)
        self.interval = interval
        self.jitter = jitter
        self.retries = retries
        self.fallback = fallback
        self.last_request = None
        self.cooldown_file = data_dir / ".retry-after"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.metrics = metrics

    def _wait(self):
        if self.cooldown_file.exists():
            try:
                deadline = float(self.cooldown_file.read_text().strip())
                if not math.isfinite(deadline) or deadline < 0:
                    raise ValueError("invalid cooldown deadline")
            except ValueError as exc:
                raise ValueError(f"Invalid rate-limit state in {self.cooldown_file}") from exc
            delay = deadline - time.time()
            if delay > 0:
                LOG.warning("Rate-limit cooldown: waiting %.1f seconds", delay)
                time.sleep(delay)
            self.cooldown_file.unlink(missing_ok=True)
        if self.last_request is not None:
            remaining = self.interval + random.uniform(0, self.jitter) - (time.monotonic() - self.last_request)
            if remaining > 0:
                LOG.info("Waiting %.1f seconds before next request", remaining)
                time.sleep(remaining)

    def get(self, url, tracer):
        target = urlsplit(url)
        if (target.scheme, target.netloc) != (self.origin.scheme, self.origin.netloc):
            raise ValueError("Refusing to fetch an off-origin profile URL")
        for attempt in range(self.retries + 1):
            self._wait()
            self.last_request = time.monotonic()
            with tracer.start_as_current_span("http.fetch") as span:
                try:
                    response = self.session.get(url, timeout=(10, 30), allow_redirects=False)
                except requests.RequestException:
                    self.metrics.requests.labels(status="error").inc()
                    raise
                with response:
                    self.metrics.requests.labels(status=str(response.status_code)).inc()
                    span.set_attribute("http.response.status_code", response.status_code)
                    if response.status_code == 429:
                        self.metrics.rate_limits.inc()
                        delay = retry_after(response.headers.get("Retry-After"), time.time(), self.fallback)
                        atomic_write(self.cooldown_file, str(time.time() + delay).encode())
                        if attempt == self.retries:
                            raise RuntimeError("HTTP 429: retry limit reached; cooldown persisted")
                        LOG.warning("HTTP 429 received; retry %d/%d after %.1f seconds", attempt + 1, self.retries, delay)
                        continue
                    if 300 <= response.status_code < 400:
                        raise RuntimeError("Unexpected HTTP redirect")
                    response.raise_for_status()
                    return BeautifulSoup(response.content, "html.parser")
        raise RuntimeError("Request retry limit reached")
