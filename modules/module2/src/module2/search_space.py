"""Search space manager for beam search.

Coordinates API calls, caching, and feature access for the beam search algorithm.
"""

from typing import Protocol, runtime_checkable

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from .acousticbrainz_client import AcousticBrainzClient
from .listenbrainz_client import ListenBrainzClient


@runtime_checkable
class SearchSpaceProtocol(Protocol):
    """Protocol defining the interface for search space implementations.

    This allows using mock search spaces in tests while maintaining
    type safety.
    """

    def get_scoreable_neighbors(self, mbid: str) -> list[str]:
        """Get neighbors with available features."""
        ...

    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None:
        """Get transition penalty between two tracks."""
        ...

    def get_transition_result(
        self, from_mbid: str, to_mbid: str
    ) -> TransitionResult | None:
        """Get full transition result between two tracks."""
        ...

    def get_features(self, mbid: str) -> TrackFeatures | None:
        """Get features for a track."""
        ...

    def has_features(self, mbid: str) -> bool:
        """Check if features are available for a track."""
        ...

    def add_features(self, mbid: str, features: TrackFeatures) -> None:
        """Add features to the cache."""
        ...


class SearchSpace(SearchSpaceProtocol):
    """Manages the search space for beam search path finding.

    This class:
    - Caches neighbors (similar recordings) for each MBID
    - Caches audio features for each discovered MBID
    - Computes transition costs using the Module 1 knowledge base
    """

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase,
        lb_client: ListenBrainzClient | None = None,
        ab_client: AcousticBrainzClient | None = None,
        neighborhood_size: int = 25,
    ):
        """Initialize the search space.

        Args:
            knowledge_base: Module 1 KB for computing transition costs.
            lb_client: ListenBrainz client for similar recordings.
                      Creates default client if not provided.
            ab_client: AcousticBrainz client for audio features.
                      Creates default client if not provided.
            neighborhood_size: Number of similar recordings to fetch per MBID.
        """
        self.kb = knowledge_base
        self.lb_client = lb_client or ListenBrainzClient()
        self.ab_client = ab_client or AcousticBrainzClient()
        self.neighborhood_size = neighborhood_size

        # In-memory caches
        self._neighbors_cache: dict[str, list[str]] = {}
        self._features_cache: dict[str, TrackFeatures] = {}

    def get_neighbors(self, mbid: str) -> list[str]:
        """Get MBIDs of similar recordings for a given track.

        Results are cached after first fetch.

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            List of similar recording MBIDs.
        """
        if mbid in self._neighbors_cache:
            return self._neighbors_cache[mbid]

        # Fetch from ListenBrainz
        similar = self.lb_client.get_similar_recordings(
            mbid, count=self.neighborhood_size
        )
        neighbor_mbids = [s.mbid for s in similar]

        # Cache the result
        self._neighbors_cache[mbid] = neighbor_mbids

        # Pre-fetch features for discovered neighbors
        self._prefetch_features(neighbor_mbids)

        return neighbor_mbids

    def _prefetch_features(self, mbids: list[str]) -> None:
        """Prefetch and cache features for MBIDs not already cached."""
        uncached = [m for m in mbids if m not in self._features_cache]
        if not uncached:
            return

        features = self.ab_client.fetch_features_batch(uncached)
        self._features_cache.update(features)

    def get_features(self, mbid: str) -> TrackFeatures | None:
        """Get audio features for a recording.

        Returns None if features are not available (track not in AcousticBrainz).

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            TrackFeatures if available, None otherwise.
        """
        if mbid in self._features_cache:
            return self._features_cache[mbid]

        # Try to fetch if not cached
        features = self.ab_client.fetch_features(mbid)
        if features:
            self._features_cache[mbid] = features
        return features

    def add_features(self, mbid: str, features: TrackFeatures) -> None:
        """Manually add features to the cache.

        Useful for preloading source/destination tracks.

        Args:
            mbid: MusicBrainz recording ID.
            features: Track features to cache.
        """
        self._features_cache[mbid] = features

    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None:
        """Compute the transition cost (penalty) between two tracks.

        Returns None if either track's features are unavailable.

        Args:
            from_mbid: Source track MBID.
            to_mbid: Destination track MBID.

        Returns:
            Transition penalty (0 = perfect, 1 = incompatible), or None.
        """
        from_features = self.get_features(from_mbid)
        to_features = self.get_features(to_mbid)

        if from_features is None or to_features is None:
            return None

        return self.kb.get_penalty(from_features, to_features)

    def get_transition_result(
        self, from_mbid: str, to_mbid: str
    ) -> TransitionResult | None:
        """Get the full transition result between two tracks.

        Returns None if either track's features are unavailable.

        Args:
            from_mbid: Source track MBID.
            to_mbid: Destination track MBID.

        Returns:
            Full TransitionResult, or None.
        """
        from_features = self.get_features(from_mbid)
        to_features = self.get_features(to_mbid)

        if from_features is None or to_features is None:
            return None

        return self.kb.get_compatibility(from_features, to_features)

    def has_features(self, mbid: str) -> bool:
        """Check if features are available (cached or fetchable).

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            True if features are available.
        """
        return self.get_features(mbid) is not None

    def get_scoreable_neighbors(self, mbid: str) -> list[str]:
        """Get neighbors that have audio features available.

        Filters out neighbors without AcousticBrainz data.

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            List of neighbor MBIDs that can be scored.
        """
        neighbors = self.get_neighbors(mbid)
        return [n for n in neighbors if self.has_features(n)]

    def cache_stats(self) -> dict[str, int]:
        """Get statistics about cache usage.

        Returns:
            Dictionary with cache statistics.
        """
        return {
            "neighbors_cached": len(self._neighbors_cache),
            "features_cached": len(self._features_cache),
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._neighbors_cache.clear()
        self._features_cache.clear()
