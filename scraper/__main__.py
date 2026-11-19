import cProfile
import logging
import math
import os

from .observability import configure_tracing
from .http import DEFAULT_USER_AGENT
from .runner import Scraper


LOG = logging.getLogger("scraper")
BASE_URL = "https://amaterky.sk/"


def positive_env(name, default, minimum=0):
    value = float(os.getenv(name, str(default)))
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and at least {minimum}")
    return value


def retry_count():
    value = os.getenv("SCRAPE_429_RETRIES", "3")
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError("SCRAPE_429_RETRIES must be a non-negative integer") from exc
    if result < 0:
        raise ValueError("SCRAPE_429_RETRIES must be a non-negative integer")
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    provider = configure_tracing()
    try:
        scraper = Scraper(
            BASE_URL,
            os.getenv("DATA_DIR", "/data"),
            interval=positive_env("SCRAPE_INTERVAL_SECONDS", 1),
            jitter=positive_env("SCRAPE_JITTER_SECONDS", 2),
            retries=retry_count(),
            fallback=positive_env("SCRAPE_RETRY_FALLBACK_SECONDS", 60, 1),
            user_agent=os.getenv("SCRAPE_USER_AGENT", DEFAULT_USER_AGENT),
        )
        profile_path = os.getenv("PROFILE_PATH")
        if profile_path:
            with cProfile.Profile() as profiler:
                try:
                    scraper.run()
                finally:
                    profiler.dump_stats(profile_path)
        else:
            scraper.run()
    finally:
        if provider:
            provider.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.exception("Scrape failed")
        raise SystemExit(1)
