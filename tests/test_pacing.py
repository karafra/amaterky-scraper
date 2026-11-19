from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scraper.http import DEFAULT_USER_AGENT, HttpClient
from scraper.observability import Metrics


class PacingTest(unittest.TestCase):
    def test_jitter_adds_to_minimum_delay(self):
        with tempfile.TemporaryDirectory() as directory:
            client = HttpClient("https://example.com/", Path(directory), Metrics(), 5, 0, 60, 2)
            self.addCleanup(client.session.close)
            client.last_request = 10
            with patch("scraper.http.time.monotonic", return_value=11), \
                 patch("scraper.http.random.uniform", return_value=2) as jitter, \
                 patch("scraper.http.time.sleep") as sleep, \
                 self.assertLogs("scraper", level="INFO") as logs:
                client._wait()
            jitter.assert_called_once_with(0, 2)
            sleep.assert_called_once_with(6)
            self.assertIn("Waiting 6.0 seconds before next request", logs.output[0])

    def test_client_identifies_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            client = HttpClient("https://example.com/", Path(directory), Metrics(), 5, 0, 60)
            self.addCleanup(client.session.close)
            self.assertEqual(client.session.headers["User-Agent"], DEFAULT_USER_AGENT)


if __name__ == "__main__":
    unittest.main()
