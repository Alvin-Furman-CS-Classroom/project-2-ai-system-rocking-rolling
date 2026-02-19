"""AcousticBrainz API client for fetching audio features.

Note: AcousticBrainz was archived in 2022, but existing data for ~2M recordings
is still accessible via the API.
"""

import logging
import time
from dataclasses import dataclass

import requests

from module1 import TrackFeatures
from module1.data_loader import load_track_from_data

logger = logging.getLogger(__name__)


@dataclass
class AcousticBrainzConfig:
    """Configuration for AcousticBrainz API client."""

    base_url: str = "https://acousticbrainz.org/api/v1"
    request_timeout: float = 30.0
    # Rate limit: 10 requests per 10 seconds
    min_request_interval: float = 1.0
    max_batch_size: int = 25  # Max MBIDs per bulk request


class AcousticBrainzClient:
    """Client for AcousticBrainz bulk feature API.

    Fetches low-level and high-level audio features for MusicBrainz recordings.
    """

    def __init__(self, config: AcousticBrainzConfig | None = None):
        self.config = config or AcousticBrainzConfig()
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def _rate_limit(self) -> None:
        """Ensure minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.min_request_interval:
            time.sleep(self.config.min_request_interval - elapsed)

    def _bulk_request(self, mbids: list[str], level: str) -> dict[str, dict]:
        """Make a bulk request for low-level or high-level data."""
        self._rate_limit()

        recording_ids = ";".join(mbids)
        url = f"{self.config.base_url}/{level}"

        try:
            response = self._session.get(
                url,
                params={"recording_ids": recording_ids},
                timeout=self.config.request_timeout,
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                return {}

            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            raise

        # Parse response: {mbid: {"0": {...data...}}, ...}
        results: dict[str, dict] = {}
        for mbid, submissions in data.items():
            if isinstance(submissions, dict) and "0" in submissions:
                results[mbid] = submissions["0"]

        return results

    def fetch_lowlevel_batch(self, mbids: list[str]) -> dict[str, dict]:
        """Fetch low-level features for multiple recordings."""
        all_results: dict[str, dict] = {}
        for i in range(0, len(mbids), self.config.max_batch_size):
            batch = mbids[i : i + self.config.max_batch_size]
            try:
                batch_results = self._bulk_request(batch, "low-level")
                all_results.update(batch_results)
            except requests.exceptions.RequestException:
                logger.warning("AcousticBrainz low-level batch failed for %d MBIDs", len(batch))
        return all_results

    def fetch_highlevel_batch(self, mbids: list[str]) -> dict[str, dict]:
        """Fetch high-level features for multiple recordings."""
        all_results: dict[str, dict] = {}
        for i in range(0, len(mbids), self.config.max_batch_size):
            batch = mbids[i : i + self.config.max_batch_size]
            try:
                batch_results = self._bulk_request(batch, "high-level")
                all_results.update(batch_results)
            except requests.exceptions.RequestException:
                logger.warning("AcousticBrainz high-level batch failed for %d MBIDs", len(batch))
        return all_results

    def fetch_features_batch(self, mbids: list[str]) -> dict[str, TrackFeatures]:
        """Fetch and parse complete features for multiple recordings."""
        lowlevel_data = self.fetch_lowlevel_batch(mbids)
        highlevel_data = self.fetch_highlevel_batch(mbids)

        results: dict[str, TrackFeatures] = {}
        for mbid in mbids:
            lowlevel = lowlevel_data.get(mbid)
            if lowlevel is None:
                continue

            highlevel = highlevel_data.get(mbid, {})

            try:
                features = load_track_from_data(lowlevel, highlevel)
                features.mbid = mbid
                results[mbid] = features
            except Exception:
                logger.warning("Failed to parse AcousticBrainz data for %s", mbid)
                continue

        return results

    def fetch_features(self, mbid: str) -> TrackFeatures | None:
        """Fetch features for a single recording."""
        results = self.fetch_features_batch([mbid])
        return results.get(mbid)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "AcousticBrainzClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
