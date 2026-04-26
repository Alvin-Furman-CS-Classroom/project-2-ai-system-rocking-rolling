"""AcousticBrainz API client for fetching audio features.

Note: AcousticBrainz was archived in 2022, but existing data for ~2M recordings
is still accessible via the API.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

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
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".cache" / "waveguide" / "acousticbrainz"
    )


class AcousticBrainzClient:
    """Client for AcousticBrainz bulk feature API.

    Fetches low-level and high-level audio features for MusicBrainz recordings.
    Raw JSON responses are cached on disk under config.cache_dir as
    {mbid}.low-level.json and {mbid}.high-level.json.
    """

    def __init__(self, config: AcousticBrainzConfig | None = None):
        self.config = config or AcousticBrainzConfig()
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, mbid: str, level: str) -> Path:
        return self.config.cache_dir / f"{mbid}.{level}.json"

    def _load_cached(self, mbid: str, level: str) -> dict | None:
        path = self._cache_path(mbid, level)
        if path.exists():
            logger.debug("AB %s cache hit: %s", level, mbid)
            return json.loads(path.read_text())
        return None

    def _save_cached(self, mbid: str, level: str, data: dict) -> None:
        self._cache_path(mbid, level).write_text(json.dumps(data))

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

        logger.debug("AB %s bulk request: GET %s (%d MBIDs)", level, url, len(mbids))
        try:
            response = self._session.get(
                url,
                params={"recording_ids": recording_ids},
                timeout=self.config.request_timeout,
            )
            self._last_request_time = time.time()
            logger.debug("AB %s response: %d", level, response.status_code)

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

        logger.debug("AB %s: got data for %d/%d MBIDs", level, len(results), len(mbids))
        return results

    def _fetch_level_batch(self, mbids: list[str], level: str) -> dict[str, dict]:
        """Fetch one level (low-level or high-level) for multiple recordings.

        Checks the filesystem cache per MBID before making any HTTP requests.
        Fetched results are written to the cache.
        """
        all_results: dict[str, dict] = {}
        uncached: list[str] = []

        for mbid in mbids:
            cached = self._load_cached(mbid, level)
            if cached is not None:
                all_results[mbid] = cached
            else:
                uncached.append(mbid)

        logger.debug(
            "AB %s: %d cached, %d to fetch of %d total",
            level, len(all_results), len(uncached), len(mbids),
        )

        for i in range(0, len(uncached), self.config.max_batch_size):
            batch = uncached[i : i + self.config.max_batch_size]
            try:
                batch_results = self._bulk_request(batch, level)
                for mbid, data in batch_results.items():
                    self._save_cached(mbid, level, data)
                all_results.update(batch_results)
            except requests.exceptions.RequestException:
                logger.warning(
                    "AcousticBrainz %s batch failed for %d MBIDs", level, len(batch)
                )

        return all_results

    def fetch_lowlevel_batch(self, mbids: list[str]) -> dict[str, dict]:
        """Fetch low-level features for multiple recordings."""
        return self._fetch_level_batch(mbids, "low-level")

    def fetch_highlevel_batch(self, mbids: list[str]) -> dict[str, dict]:
        """Fetch high-level features for multiple recordings."""
        return self._fetch_level_batch(mbids, "high-level")

    def fetch_features_batch(self, mbids: list[str]) -> dict[str, TrackFeatures]:
        """Fetch and parse complete features for multiple recordings."""
        logger.debug("AB fetch_features_batch: %d MBIDs", len(mbids))
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

        logger.debug("AB fetch_features_batch: parsed %d/%d tracks", len(results), len(mbids))
        return results

    def fetch_features(self, mbid: str) -> TrackFeatures | None:
        """Fetch features for a single recording."""
        results = self.fetch_features_batch([mbid])
        return results.get(mbid)

    def cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        files = list(self.config.cache_dir.glob("*.json"))
        lowlevel = sum(1 for f in files if ".low-level." in f.name)
        highlevel = sum(1 for f in files if ".high-level." in f.name)
        return {"lowlevel_cached": lowlevel, "highlevel_cached": highlevel}

    def clear_cache(self) -> None:
        """Delete all cached JSON files."""
        for f in self.config.cache_dir.glob("*.json"):
            f.unlink()

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "AcousticBrainzClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
