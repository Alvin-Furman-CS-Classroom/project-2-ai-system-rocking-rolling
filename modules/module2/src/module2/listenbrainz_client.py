"""ListenBrainz API client for fetching similar recordings."""

import time
from dataclasses import dataclass

import requests

from .data_models import SimilarRecording


@dataclass
class ListenBrainzConfig:
    """Configuration for ListenBrainz API client."""

    base_url: str = "https://labs.api.listenbrainz.org"
    user_token: str | None = None  # Optional: improves rate limits
    request_timeout: float = 30.0
    min_request_interval: float = 0.5  # Seconds between requests


class ListenBrainzClient:
    """Client for ListenBrainz similarity API.

    Uses the labs API to find recordings similar to a given MBID.
    """

    def __init__(self, config: ListenBrainzConfig | None = None):
        """Initialize the client.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or ListenBrainzConfig()
        self._last_request_time: float = 0.0
        self._session = requests.Session()

        # Set up headers
        headers = {"Accept": "application/json"}
        if self.config.user_token:
            headers["Authorization"] = f"Token {self.config.user_token}"
        self._session.headers.update(headers)

    def _rate_limit(self) -> None:
        """Ensure minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.min_request_interval:
            time.sleep(self.config.min_request_interval - elapsed)

    def get_similar_recordings(
        self,
        mbid: str,
        count: int = 25,
        algorithm: str = "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30",
    ) -> list[SimilarRecording]:
        """Fetch recordings similar to the given MBID.

        Args:
            mbid: MusicBrainz recording ID to find similar tracks for.
            count: Maximum number of similar recordings to return.
            algorithm: Similarity algorithm to use (ListenBrainz supports multiple).

        Returns:
            List of similar recordings with similarity scores.

        Raises:
            requests.RequestException: If the API request fails.
        """
        self._rate_limit()

        # Build request payload for the JSPF endpoint
        payload = [
            {
                "recording_mbid": mbid,
                "algorithm": algorithm,
            }
        ]

        url = f"{self.config.base_url}/similar-recordings"

        try:
            response = self._session.post(
                url,
                json=payload,
                timeout=self.config.request_timeout,
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                # No similar recordings found
                return []

            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException:
            # Log and re-raise for caller to handle
            raise

        # Parse the response
        # Response format: [{"recording_mbid": ..., "similar_recordings": [...]}]
        results: list[SimilarRecording] = []

        if not data or not isinstance(data, list):
            return results

        for item in data:
            similar_list = item.get("similar_recordings", [])
            for rec in similar_list[:count]:
                rec_mbid = rec.get("recording_mbid")
                score = rec.get("score", 0.0)
                if rec_mbid:
                    results.append(SimilarRecording(mbid=rec_mbid, similarity_score=score))

        return results[:count]

    def get_similar_recordings_batch(
        self,
        mbids: list[str],
        count_per_mbid: int = 25,
    ) -> dict[str, list[SimilarRecording]]:
        """Fetch similar recordings for multiple MBIDs.

        Args:
            mbids: List of MusicBrainz recording IDs.
            count_per_mbid: Maximum similar recordings per MBID.

        Returns:
            Dictionary mapping each input MBID to its similar recordings.
        """
        results: dict[str, list[SimilarRecording]] = {}

        for mbid in mbids:
            try:
                similar = self.get_similar_recordings(mbid, count=count_per_mbid)
                results[mbid] = similar
            except requests.RequestException:
                # Skip failed lookups, return empty list
                results[mbid] = []

        return results

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "ListenBrainzClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
