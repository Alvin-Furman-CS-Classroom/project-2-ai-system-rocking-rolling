"""MusicBrainz API client for editorial metadata enrichment.

Fetches artist relationships, release year, and curated genre tags
from the MusicBrainz database. Caches aggressively by artist MBID
since many tracks in a search space share the same artist.
"""

import logging
import time
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class MusicBrainzConfig:
    """Configuration for MusicBrainz API client."""

    base_url: str = "https://musicbrainz.org/ws/2"
    user_agent: str = "WaveGuide/1.0 (https://github.com/waveguide)"
    request_timeout: float = 30.0
    min_request_interval: float = 1.0  # 1 req/sec enforced by MB


@dataclass
class RecordingMetadata:
    """Parsed metadata for a single MusicBrainz recording."""

    artist_mbid: str | None = None
    release_year: int | None = None
    genre_tags: list[str] = field(default_factory=list)


class MusicBrainzClient:
    """Client for MusicBrainz web service (ws/2).

    Fetches recording metadata (artist, release year, genres) and
    artist relationships. Caches artist relationship graphs by artist
    MBID to avoid redundant calls for tracks by the same artist.
    """

    def __init__(self, config: MusicBrainzConfig | None = None):
        self.config = config or MusicBrainzConfig()
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
        })

        # Caches
        self._artist_rels_cache: dict[str, set[str]] = {}
        self._recording_cache: dict[str, RecordingMetadata] = {}

    def _rate_limit(self) -> None:
        """Ensure minimum 1 second between requests (MB requirement)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.min_request_interval:
            time.sleep(self.config.min_request_interval - elapsed)

    # -------------------------------------------------------------------------
    # Recording metadata
    # -------------------------------------------------------------------------

    def get_recording_metadata(self, mbid: str) -> RecordingMetadata:
        """Fetch recording metadata: artist, release year, genres.

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            RecordingMetadata with available fields populated.
        """
        if mbid in self._recording_cache:
            return self._recording_cache[mbid]

        self._rate_limit()

        url = f"{self.config.base_url}/recording/{mbid}"
        params = {"inc": "releases+genres+artists", "fmt": "json"}

        try:
            response = self._session.get(
                url, params=params, timeout=self.config.request_timeout
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                meta = RecordingMetadata()
                self._recording_cache[mbid] = meta
                return meta

            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            logger.warning("MusicBrainz recording lookup failed for %s", mbid)
            return RecordingMetadata()

        meta = self._parse_recording(data)
        self._recording_cache[mbid] = meta
        return meta

    def get_recording_metadata_batch(
        self, mbids: list[str]
    ) -> dict[str, RecordingMetadata]:
        """Fetch recording metadata for multiple MBIDs using Lucene search.

        Uses the MusicBrainz search endpoint with OR queries on recording IDs
        to fetch up to 25 recordings in a single request, instead of making
        one request per recording at 1 req/sec.
        """
        results: dict[str, RecordingMetadata] = {}
        if not mbids:
            return results

        # Check cache first, collect uncached
        uncached: list[str] = []
        for mbid in mbids:
            if mbid in self._recording_cache:
                results[mbid] = self._recording_cache[mbid]
            else:
                uncached.append(mbid)

        if not uncached:
            return results

        # Batch via Lucene search: rid:MBID1 OR rid:MBID2 OR ...
        # Search endpoint allows up to ~100 results per request
        for i in range(0, len(uncached), 25):
            chunk = uncached[i : i + 25]
            query = " OR ".join(f"rid:{m}" for m in chunk)

            self._rate_limit()

            url = f"{self.config.base_url}/recording"
            params = {"query": query, "fmt": "json", "limit": 100}

            try:
                response = self._session.get(
                    url, params=params, timeout=self.config.request_timeout
                )
                self._last_request_time = time.time()

                if response.status_code != 200:
                    logger.warning(
                        "MB search returned %d, falling back to individual lookups",
                        response.status_code,
                    )
                    for mbid in chunk:
                        results[mbid] = self.get_recording_metadata(mbid)
                    continue

                data = response.json()
            except requests.exceptions.RequestException:
                logger.warning("MB batch search failed, falling back")
                for mbid in chunk:
                    results[mbid] = self.get_recording_metadata(mbid)
                continue

            # Index results by recording ID
            found_ids: set[str] = set()
            for rec in data.get("recordings", []):
                rec_id = rec.get("id", "")
                if rec_id in chunk:
                    meta = self._parse_recording_search(rec)
                    self._recording_cache[rec_id] = meta
                    results[rec_id] = meta
                    found_ids.add(rec_id)

            # Cache empty metadata for MBIDs not found in search results
            for mbid in chunk:
                if mbid not in found_ids:
                    meta = RecordingMetadata()
                    self._recording_cache[mbid] = meta
                    results[mbid] = meta

        return results

    def _parse_recording(self, data: dict) -> RecordingMetadata:
        """Parse MusicBrainz recording JSON from lookup endpoint."""
        # Extract artist MBID
        artist_mbid = None
        artist_credits = data.get("artist-credit", [])
        if artist_credits:
            first_artist = artist_credits[0].get("artist", {})
            artist_mbid = first_artist.get("id")

        # Extract earliest release year
        release_year = None
        releases = data.get("releases", [])
        for release in releases:
            date_str = release.get("date", "")
            if date_str and len(date_str) >= 4:
                try:
                    year = int(date_str[:4])
                    if release_year is None or year < release_year:
                        release_year = year
                except ValueError:
                    continue

        # Extract genre tags
        genre_tags = []
        genres = data.get("genres", [])
        for genre in genres:
            name = genre.get("name", "")
            if name:
                genre_tags.append(name)

        return RecordingMetadata(
            artist_mbid=artist_mbid,
            release_year=release_year,
            genre_tags=genre_tags,
        )

    def _parse_recording_search(self, data: dict) -> RecordingMetadata:
        """Parse MusicBrainz recording JSON from search endpoint.

        Search results have a slightly different structure than lookup results:
        - 'first-release-date' instead of nested releases with dates
        - 'tags' list instead of 'genres' list
        """
        # Extract artist MBID
        artist_mbid = None
        artist_credits = data.get("artist-credit", [])
        if artist_credits:
            first_artist = artist_credits[0].get("artist", {})
            artist_mbid = first_artist.get("id")

        # Extract release year from first-release-date or releases
        release_year = None
        first_date = data.get("first-release-date", "")
        if first_date and len(first_date) >= 4:
            try:
                release_year = int(first_date[:4])
            except ValueError:
                pass
        if release_year is None:
            for release in data.get("releases", []):
                date_str = release.get("date", "")
                if date_str and len(date_str) >= 4:
                    try:
                        year = int(date_str[:4])
                        if release_year is None or year < release_year:
                            release_year = year
                    except ValueError:
                        continue

        # Extract tags (search uses 'tags' not 'genres')
        genre_tags = []
        for tag in data.get("tags", []):
            name = tag.get("name", "")
            if name:
                genre_tags.append(name)

        return RecordingMetadata(
            artist_mbid=artist_mbid,
            release_year=release_year,
            genre_tags=genre_tags,
        )

    # -------------------------------------------------------------------------
    # Artist relationships
    # -------------------------------------------------------------------------

    def get_artist_relationships(self, artist_mbid: str) -> set[str]:
        """Fetch related artist MBIDs from MusicBrainz.

        Results are cached by artist MBID — since many tracks share an
        artist, this avoids redundant API calls.

        Args:
            artist_mbid: MusicBrainz artist ID.

        Returns:
            Set of related artist MBIDs (members, collaborators, producers).
        """
        if artist_mbid in self._artist_rels_cache:
            return self._artist_rels_cache[artist_mbid]

        self._rate_limit()

        url = f"{self.config.base_url}/artist/{artist_mbid}"
        params = {"inc": "artist-rels", "fmt": "json"}

        try:
            response = self._session.get(
                url, params=params, timeout=self.config.request_timeout
            )
            self._last_request_time = time.time()

            if response.status_code == 404:
                self._artist_rels_cache[artist_mbid] = set()
                return set()

            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            logger.warning("MusicBrainz artist lookup failed for %s", artist_mbid)
            return set()

        related = self._parse_artist_relations(data)
        self._artist_rels_cache[artist_mbid] = related
        return related

    def _parse_artist_relations(self, data: dict) -> set[str]:
        """Parse related artist MBIDs from artist relations response."""
        related: set[str] = set()
        relations = data.get("relations", [])
        for rel in relations:
            target_type = rel.get("target-type", "")
            if target_type == "artist":
                artist = rel.get("artist", {})
                rel_mbid = artist.get("id")
                if rel_mbid:
                    related.add(rel_mbid)
        return related

    # -------------------------------------------------------------------------
    # Cache management
    # -------------------------------------------------------------------------

    def cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "recordings_cached": len(self._recording_cache),
            "artists_cached": len(self._artist_rels_cache),
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._recording_cache.clear()
        self._artist_rels_cache.clear()

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "MusicBrainzClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
