"""ListenBrainz API client for similar recordings and track enrichment."""

import logging
import time
from dataclasses import dataclass

import requests

from .data_models import SimilarRecording

logger = logging.getLogger(__name__)

# Available ListenBrainz similarity algorithms, ordered broadest → narrowest.
# Each uses different lookback windows, contribution caps, and filters,
# producing partially overlapping neighbor sets.
# Source: https://github.com/metabrainz/listenbrainz-server (Spark jobs)
SIMILARITY_ALGORITHMS = [
    "session_based_days_9000_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30",
    "session_based_days_7500_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30",
    "session_based_days_7500_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30"
    "_top_n_listeners_1000",
    "session_based_days_7500_session_300"
    "_contribution_sqrt_threshold_15_limit_50_skip_30"
    "_top_n_listeners_1000",
]


@dataclass
class ListenBrainzConfig:
    """Configuration for ListenBrainz API client."""

    base_url: str = "https://labs.api.listenbrainz.org"
    api_url: str = "https://api.listenbrainz.org/1"
    user_token: str | None = None  # Optional: improves rate limits
    request_timeout: float = 30.0
    min_request_interval: float = 0.5  # Seconds between requests


class ListenBrainzClient:
    """Client for ListenBrainz APIs.

    Handles two roles:
    1. Neighborhood discovery via the labs similar-recordings API
    2. Track enrichment via the main API (tags, popularity)
    """

    def __init__(self, config: ListenBrainzConfig | None = None):
        self.config = config or ListenBrainzConfig()
        self._last_request_time: float = 0.0
        self._session = requests.Session()

        headers = {"Accept": "application/json"}
        if self.config.user_token:
            headers["Authorization"] = f"Token {self.config.user_token}"
        self._session.headers.update(headers)

    def _rate_limit(self) -> None:
        """Ensure minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.min_request_interval:
            time.sleep(self.config.min_request_interval - elapsed)

    # -------------------------------------------------------------------------
    # Neighborhood discovery (labs API)
    # -------------------------------------------------------------------------

    def get_similar_recordings(
        self,
        mbid: str,
        count: int = 25,
        algorithm: str = (
            "session_based_days_7500_session_300"
            "_contribution_5_threshold_15_limit_50_skip_30"
        ),
    ) -> list[SimilarRecording]:
        """Fetch recordings similar to the given MBID from ListenBrainz labs API."""
        self._rate_limit()

        payload = [{"recording_mbids": [mbid], "algorithm": algorithm}]
        url = f"{self.config.base_url}/similar-recordings/json"

        try:
            response = self._session.post(
                url, json=payload, timeout=self.config.request_timeout
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                return []
            if response.status_code != 200:
                logger.warning(
                    "ListenBrainz similar-recordings returned %d for %s",
                    response.status_code,
                    mbid,
                )
                return []

            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch similar recordings for %s: %s", mbid, e)
            return []

        results: list[SimilarRecording] = []
        if not data or not isinstance(data, list):
            return results

        # New /json endpoint returns a flat list of similar recordings
        # with integer scores (higher = more similar)
        max_score = max((item.get("score", 1) for item in data), default=1) or 1
        for item in data:
            rec_mbid = item.get("recording_mbid")
            raw_score = item.get("score", 0)
            if rec_mbid and rec_mbid != mbid:
                results.append(
                    SimilarRecording(
                        mbid=rec_mbid,
                        similarity_score=raw_score / max_score,
                    )
                )

        return results[:count]

    def get_similar_recordings_multi(
        self,
        mbid: str,
        count: int = 100,
        algorithms: list[str] | None = None,
    ) -> list[SimilarRecording]:
        """Fetch similar recordings using multiple algorithms and merge results.

        Different algorithms produce partially overlapping neighbor sets.
        Merging them expands the search space by ~50-80% compared to a single
        algorithm. When the same MBID appears in multiple algorithms, the
        highest similarity score is kept.

        Returns results tagged with their source algorithm via the
        SimilarRecording.algorithm field.
        """
        algos = algorithms or SIMILARITY_ALGORITHMS
        seen: dict[str, SimilarRecording] = {}

        for algo in algos:
            results = self.get_similar_recordings(
                mbid, count=100, algorithm=algo
            )
            for rec in results:
                if rec.mbid not in seen or rec.similarity_score > seen[rec.mbid].similarity_score:
                    rec.algorithm = algo
                    seen[rec.mbid] = rec

        merged = sorted(
            seen.values(),
            key=lambda r: r.similarity_score,
            reverse=True,
        )

        logger.info(
            "Multi-algorithm: %d unique neighbors for %s from %d algorithms",
            len(merged), mbid, len(algos),
        )
        return merged[:count]

    def get_similar_recordings_batch(
        self,
        mbids: list[str],
        count_per_mbid: int = 25,
    ) -> dict[str, list[SimilarRecording]]:
        """Fetch similar recordings for multiple MBIDs."""
        results: dict[str, list[SimilarRecording]] = {}
        for mbid in mbids:
            try:
                similar = self.get_similar_recordings(mbid, count=count_per_mbid)
                results[mbid] = similar
            except requests.RequestException:
                results[mbid] = []
        return results

    # -------------------------------------------------------------------------
    # Track enrichment (main API)
    # -------------------------------------------------------------------------

    def get_recording_tags(self, mbids: list[str]) -> dict[str, dict[str, int]]:
        """Fetch user-generated tags for recordings from ListenBrainz.

        Uses the metadata/recording endpoint to get tags with counts.

        Args:
            mbids: List of MusicBrainz recording IDs.

        Returns:
            Dict mapping MBID -> {tag_name: count}. Missing MBIDs omitted.
        """
        results: dict[str, dict[str, int]] = {}
        if not mbids:
            return results

        self._rate_limit()

        url = f"{self.config.api_url}/metadata/recording/"
        params = {
            "recording_mbids": ",".join(mbids),
            "inc": "tag",
        }

        try:
            response = self._session.get(
                url, params=params, timeout=self.config.request_timeout
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                return results

            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            logger.warning("Failed to fetch recording tags from ListenBrainz")
            return results

        # Response format varies — handle both list and dict forms
        if isinstance(data, dict):
            for mbid, metadata in data.items():
                tags = self._extract_tags(metadata)
                if tags:
                    results[mbid] = tags
        elif isinstance(data, list):
            for item in data:
                mbid = item.get("recording_mbid") or item.get("mbid", "")
                tags = self._extract_tags(item)
                if tags and mbid:
                    results[mbid] = tags

        return results

    def _extract_tags(self, metadata: dict) -> dict[str, int]:
        """Extract tag dict from a metadata response item."""
        tags: dict[str, int] = {}
        tag_data = metadata.get("tag", metadata.get("tags", {}))

        if isinstance(tag_data, dict):
            # Format: {"recording": [{"tag": "rock", "count": 5}, ...]}
            recording_tags = tag_data.get("recording", [])
            if isinstance(recording_tags, list):
                for entry in recording_tags:
                    name = entry.get("tag", entry.get("genre", ""))
                    count = entry.get("count", 1)
                    if name:
                        tags[name] = int(count)
            # Also check artist-level tags as fallback
            artist_tags = tag_data.get("artist", [])
            if isinstance(artist_tags, list):
                for entry in artist_tags:
                    name = entry.get("tag", entry.get("genre", ""))
                    count = entry.get("count", 1)
                    if name and name not in tags:
                        tags[name] = int(count)
        elif isinstance(tag_data, list):
            for entry in tag_data:
                name = entry.get("tag", entry.get("genre", ""))
                count = entry.get("count", 1)
                if name:
                    tags[name] = int(count)

        return tags

    def get_recording_popularity(self, mbids: list[str]) -> dict[str, dict[str, int]]:
        """Fetch popularity data (listen counts) for recordings from ListenBrainz.

        Args:
            mbids: List of MusicBrainz recording IDs.

        Returns:
            Dict mapping MBID -> {"listen_count": N, "user_count": M}.
            Missing MBIDs omitted.
        """
        results: dict[str, dict[str, int]] = {}
        if not mbids:
            return results

        self._rate_limit()

        url = f"{self.config.api_url}/popularity/recording"

        try:
            response = self._session.post(
                url,
                json={"recording_mbids": mbids},
                timeout=self.config.request_timeout,
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                return results

            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            logger.warning("Failed to fetch recording popularity from ListenBrainz")
            return results

        if isinstance(data, list):
            for item in data:
                mbid = item.get("recording_mbid", "")
                listen_count = item.get("total_listen_count", 0)
                user_count = item.get("total_user_count", 0)
                if mbid:
                    results[mbid] = {
                        "listen_count": int(listen_count),
                        "user_count": int(user_count),
                    }

        return results

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "ListenBrainzClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
