"""Search space manager for beam search.

Coordinates API calls, caching, and feature access for the beam search algorithm.
Orchestrates enrichment from all 3 data sources: AcousticBrainz, ListenBrainz,
and MusicBrainz.

Includes a persistent disk cache for LB neighbor responses so that repeated
runs for the same MBID don't re-hit the API (the most expensive call: 4
algorithms × 1 req each at 0.5 s intervals).
"""

import json
import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from .acousticbrainz_client import AcousticBrainzClient
from .listenbrainz_client import ListenBrainzClient
from .musicbrainz_client import MusicBrainzClient

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".waveguide" / "neighbor_cache"


@runtime_checkable
class SearchSpaceProtocol(Protocol):
    """Protocol defining the interface for search space implementations."""

    def get_scoreable_neighbors(self, mbid: str) -> list[str]: ...
    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None: ...
    def get_transition_result(
        self, from_mbid: str, to_mbid: str
    ) -> TransitionResult | None: ...
    def get_features(self, mbid: str) -> TrackFeatures | None: ...
    def has_features(self, mbid: str) -> bool: ...
    def add_features(self, mbid: str, features: TrackFeatures) -> None: ...


class SearchSpace(SearchSpaceProtocol):
    """Manages the search space for beam search path finding.

    Coordinates neighbor discovery (ListenBrainz), feature enrichment from
    3 data sources (AcousticBrainz, ListenBrainz, MusicBrainz), and
    transition scoring via Module 1's knowledge base.
    """

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase,
        lb_client: ListenBrainzClient | None = None,
        ab_client: AcousticBrainzClient | None = None,
        mb_client: MusicBrainzClient | None = None,
        neighborhood_size: int = 25,
        cache_dir: Path | None = DEFAULT_CACHE_DIR,
    ):
        self.kb = knowledge_base
        self.lb_client = lb_client or ListenBrainzClient()
        self.ab_client = ab_client or AcousticBrainzClient()
        self.mb_client = mb_client or MusicBrainzClient()
        self.neighborhood_size = neighborhood_size
        self._cache_dir = cache_dir

        # Create disk cache directory
        if self._cache_dir is not None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._neighbors_cache: dict[str, list[str]] = {}
        self._features_cache: dict[str, TrackFeatures] = {}

    def get_neighbors(self, mbid: str) -> list[str]:
        """Get MBIDs of similar recordings for a given track.

        Checks in order: in-memory cache → disk cache → LB API.
        Results are written to disk so subsequent runs skip the API.
        """
        if mbid in self._neighbors_cache:
            return self._neighbors_cache[mbid]

        # Check disk cache
        disk_result = self._load_neighbors_from_disk(mbid)
        if disk_result is not None:
            self._neighbors_cache[mbid] = disk_result
            self.enrich_tracks(disk_result)
            return disk_result

        # API call (expensive: 4 algorithms × 0.5 s each)
        similar = self.lb_client.get_similar_recordings_multi(
            mbid, count=self.neighborhood_size
        )
        neighbor_mbids = [s.mbid for s in similar]
        self._neighbors_cache[mbid] = neighbor_mbids

        # Persist to disk for future runs
        self._save_neighbors_to_disk(mbid, neighbor_mbids)

        # Enrich discovered neighbors from all data sources
        self.enrich_tracks(neighbor_mbids)

        return neighbor_mbids

    # -------------------------------------------------------------------------
    # Disk cache for neighbor lists
    # -------------------------------------------------------------------------

    def _neighbor_cache_path(self, mbid: str) -> Path | None:
        """Get the disk cache file path for an MBID's neighbors."""
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{mbid}.json"

    def _load_neighbors_from_disk(self, mbid: str) -> list[str] | None:
        """Load cached neighbor list from disk. Returns None on miss."""
        path = self._neighbor_cache_path(mbid)
        if path is None or not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                logger.debug("Disk cache hit for neighbors of %s (%d entries)", mbid, len(data))
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Corrupt neighbor cache for %s, ignoring: %s", mbid, e)
        return None

    def _save_neighbors_to_disk(self, mbid: str, neighbors: list[str]) -> None:
        """Persist a neighbor list to disk cache."""
        path = self._neighbor_cache_path(mbid)
        if path is None:
            return
        try:
            path.write_text(json.dumps(neighbors))
        except OSError as e:
            logger.warning("Failed to write neighbor cache for %s: %s", mbid, e)

    # -------------------------------------------------------------------------
    # Three-source enrichment pipeline
    # -------------------------------------------------------------------------

    def enrich_tracks(self, mbids: list[str]) -> None:
        """Enrich tracks from all 3 data sources in priority order.

        1. AcousticBrainz (batch, 7 dims) — required for content-based scoring
        2. ListenBrainz (batch, 2 dims) — tags and popularity
        3. MusicBrainz (individual, 3 dims) — artist rels, era, genres
        """
        uncached = [m for m in mbids if m not in self._features_cache]
        if not uncached:
            return

        # Step 1: AcousticBrainz — creates base TrackFeatures
        self._enrich_with_acousticbrainz(uncached)

        # Step 2: ListenBrainz tags + popularity — enriches existing features
        self._enrich_with_listenbrainz(uncached)

        # Step 3: MusicBrainz artist/era/genre — enriches existing features
        self._enrich_with_musicbrainz(uncached)

    def _enrich_with_acousticbrainz(self, mbids: list[str]) -> None:
        """Fetch AcousticBrainz features and create base TrackFeatures objects."""
        try:
            features = self.ab_client.fetch_features_batch(mbids)
            self._features_cache.update(features)
        except Exception:
            logger.warning(
                "AcousticBrainz enrichment failed for %d MBIDs", len(mbids)
            )

    def _enrich_with_listenbrainz(self, mbids: list[str]) -> None:
        """Enrich cached TrackFeatures with ListenBrainz tags and popularity."""
        # Only enrich tracks that have base features
        enrichable = [m for m in mbids if m in self._features_cache]
        if not enrichable:
            return

        try:
            tags_data = self.lb_client.get_recording_tags(enrichable)
            for mbid, tags in tags_data.items():
                if mbid in self._features_cache and tags:
                    self._features_cache[mbid].tags = tags
        except Exception:
            logger.warning("ListenBrainz tag enrichment failed")

        try:
            pop_data = self.lb_client.get_recording_popularity(enrichable)
            for mbid, pop in pop_data.items():
                if mbid in self._features_cache:
                    self._features_cache[mbid].popularity_listen_count = pop.get(
                        "listen_count"
                    )
                    self._features_cache[mbid].popularity_user_count = pop.get(
                        "user_count"
                    )
        except Exception:
            logger.warning("ListenBrainz popularity enrichment failed")

    def _enrich_with_musicbrainz(self, mbids: list[str]) -> None:
        """Enrich cached TrackFeatures with MusicBrainz editorial metadata."""
        enrichable = [m for m in mbids if m in self._features_cache]
        if not enrichable:
            return

        try:
            metadata = self.mb_client.get_recording_metadata_batch(enrichable)
        except Exception:
            logger.warning("MusicBrainz metadata enrichment failed")
            return

        for mbid, meta in metadata.items():
            if mbid not in self._features_cache:
                continue
            track = self._features_cache[mbid]

            if meta.artist_mbid:
                track.artist_mbid = meta.artist_mbid
                # Fetch artist relationships (cached per-artist)
                try:
                    related = self.mb_client.get_artist_relationships(meta.artist_mbid)
                    track.mb_artist_related_mbids = related
                except Exception:
                    logger.warning(
                        "Failed to fetch artist rels for %s", meta.artist_mbid
                    )

            if meta.release_year is not None:
                track.mb_release_year = meta.release_year

            if meta.genre_tags:
                track.mb_genre_tags = meta.genre_tags

    # -------------------------------------------------------------------------
    # Feature access
    # -------------------------------------------------------------------------

    def get_features(self, mbid: str) -> TrackFeatures | None:
        """Get audio features for a recording."""
        if mbid in self._features_cache:
            return self._features_cache[mbid]

        # Try to fetch if not cached
        features = self.ab_client.fetch_features(mbid)
        if features:
            self._features_cache[mbid] = features
        return features

    def add_features(self, mbid: str, features: TrackFeatures) -> None:
        """Manually add features to the cache."""
        self._features_cache[mbid] = features

    def has_features(self, mbid: str) -> bool:
        """Check if features are available (cached or fetchable)."""
        return self.get_features(mbid) is not None

    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------

    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None:
        """Compute the transition cost (penalty) between two tracks."""
        from_features = self.get_features(from_mbid)
        to_features = self.get_features(to_mbid)
        if from_features is None or to_features is None:
            return None
        return self.kb.get_penalty(from_features, to_features)

    def get_transition_result(
        self, from_mbid: str, to_mbid: str
    ) -> TransitionResult | None:
        """Get the full transition result between two tracks."""
        from_features = self.get_features(from_mbid)
        to_features = self.get_features(to_mbid)
        if from_features is None or to_features is None:
            return None
        return self.kb.get_compatibility(from_features, to_features)

    def get_scoreable_neighbors(self, mbid: str) -> list[str]:
        """Get neighbors that have audio features available."""
        neighbors = self.get_neighbors(mbid)
        return [n for n in neighbors if self.has_features(n)]

    # -------------------------------------------------------------------------
    # Cache management
    # -------------------------------------------------------------------------

    def cache_stats(self) -> dict[str, int]:
        """Get statistics about cache usage."""
        disk_count = 0
        if self._cache_dir is not None and self._cache_dir.exists():
            disk_count = len(list(self._cache_dir.glob("*.json")))
        return {
            "neighbors_cached": len(self._neighbors_cache),
            "neighbors_on_disk": disk_count,
            "features_cached": len(self._features_cache),
        }

    def clear_cache(self, include_disk: bool = False) -> None:
        """Clear all cached data.

        Args:
            include_disk: If True, also delete the disk neighbor cache files.
        """
        self._neighbors_cache.clear()
        self._features_cache.clear()
        if include_disk and self._cache_dir is not None and self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()
            logger.info("Cleared disk neighbor cache at %s", self._cache_dir)
