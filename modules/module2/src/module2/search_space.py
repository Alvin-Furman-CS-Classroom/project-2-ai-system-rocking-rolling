"""Search space manager for beam search.

Coordinates API calls, caching, and feature access for the beam search algorithm.
Orchestrates enrichment from all 3 data sources: AcousticBrainz, ListenBrainz,
and MusicBrainz.
"""

import logging
from typing import Protocol, runtime_checkable

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from .acousticbrainz_client import AcousticBrainzClient
from .listenbrainz_client import ListenBrainzClient
from .musicbrainz_client import MusicBrainzClient
from .musicbrainz_db import MusicBrainzDB

logger = logging.getLogger(__name__)


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
    ):
        self.kb = knowledge_base
        self.lb_client = lb_client or ListenBrainzClient()
        self.ab_client = ab_client or AcousticBrainzClient()
        self.mb_client = mb_client or MusicBrainzDB()
        self.neighborhood_size = neighborhood_size

        # In-memory caches
        self._neighbors_cache: dict[str, list[str]] = {}
        self._features_cache: dict[str, TrackFeatures] = {}

    def get_neighbors(self, mbid: str) -> list[str]:
        """Get MBIDs of similar recordings for a given track."""
        if mbid in self._neighbors_cache:
            return self._neighbors_cache[mbid]

        similar = self.lb_client.get_similar_recordings_multi(
            mbid, count=self.neighborhood_size
        )
        neighbor_mbids = [s.mbid for s in similar]
        self._neighbors_cache[mbid] = neighbor_mbids

        # Enrich discovered neighbors from all data sources
        self._enrich_tracks(neighbor_mbids)

        return neighbor_mbids

    # -------------------------------------------------------------------------
    # Three-source enrichment pipeline
    # -------------------------------------------------------------------------

    def _enrich_tracks(self, mbids: list[str]) -> None:
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
            logger.warning("AcousticBrainz enrichment failed for %d MBIDs", len(mbids))

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
        return {
            "neighbors_cached": len(self._neighbors_cache),
            "features_cached": len(self._features_cache),
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._neighbors_cache.clear()
        self._features_cache.clear()
