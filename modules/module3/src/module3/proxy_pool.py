"""Proxy track pool for tracks with zero ListenBrainz neighbors.

When a user picks a song that has no LB neighbor data (e.g., Wannabe,
Bohemian Rhapsody), beam search cannot expand from it. The proxy pool
solves this by:

1. Maintaining a pool of tracks known to have LB neighbors + features
2. Matching the user's song to the most sonically similar track in the pool
3. Beam search runs between proxies; user's songs stay in the playlist

The pool auto-grows: every time beam search discovers neighbors,
those tracks get added to the pool for future use.

Pool storage: ~/.waveguide/proxy_pool.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from module1 import MusicKnowledgeBase, TrackFeatures

logger = logging.getLogger(__name__)

DEFAULT_POOL_PATH = Path("~/.waveguide/proxy_pool.json").expanduser()

# Known working seeds — tracks confirmed to have LB neighbors + AB features
SEED_TRACKS = [
    {
        "mbid": "1eac49da-3399-4d34-bbf3-a98a91e2758b",
        "title": "Congregation",
        "artist": "Foo Fighters",
    },
    {
        "mbid": "80c24793-6a40-4edb-b1bb-5a4e3946901e",
        "title": "Little Monster",
        "artist": "Royal Blood",
    },
    {
        "mbid": "ffcb45c3-7f32-427d-b3d4-287664bbcdb9",
        "title": "What Kind of Man",
        "artist": "Florence + the Machine",
    },
    {
        "mbid": "564ccd5c-c4d3-4752-9abf-c33bb085d6a5",
        "title": "The Lost Art of Conversation",
        "artist": "Pink Floyd",
    },
]


@dataclass
class PoolEntry:
    """A track in the proxy pool with its features summary."""

    mbid: str
    title: str | None = None
    artist: str | None = None
    has_lb_neighbors: bool = True


@dataclass
class ProxyResult:
    """Result of proxy discovery for a single track."""

    original_mbid: str
    proxy_mbid: str
    proxy_title: str | None
    proxy_artist: str | None
    compatibility_score: float
    needed_proxy: bool  # False if original had LB neighbors


class ProxyPool:
    """Auto-growing pool of tracks with known LB connectivity.

    The pool starts with seed tracks and grows as the system is used.
    When beam search discovers neighbors, add_from_neighbors() records
    them for future proxy matching.
    """

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase,
        pool_path: Path | None = None,
    ):
        self.kb = knowledge_base
        self._pool_path = pool_path or DEFAULT_POOL_PATH
        self._entries: dict[str, PoolEntry] = {}
        self._load_pool()

    def _load_pool(self) -> None:
        """Load pool from disk, seeding with defaults if empty."""
        if self._pool_path.exists():
            try:
                with open(self._pool_path) as f:
                    data = json.load(f)
                for entry_data in data:
                    entry = PoolEntry(**entry_data)
                    self._entries[entry.mbid] = entry
            except Exception:
                logger.warning("Corrupt proxy pool at %s, re-seeding", self._pool_path)
                self._entries.clear()

        # Always ensure seeds are present
        for seed in SEED_TRACKS:
            if seed["mbid"] not in self._entries:
                self._entries[seed["mbid"]] = PoolEntry(
                    mbid=seed["mbid"],
                    title=seed.get("title"),
                    artist=seed.get("artist"),
                )

    def _save_pool(self) -> None:
        """Persist pool to disk."""
        self._pool_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = [
                {
                    "mbid": e.mbid,
                    "title": e.title,
                    "artist": e.artist,
                    "has_lb_neighbors": e.has_lb_neighbors,
                }
                for e in self._entries.values()
            ]
            with open(self._pool_path, "w") as f:
                json.dump(data, f)
        except Exception:
            logger.warning("Failed to save proxy pool")

    @property
    def size(self) -> int:
        return len(self._entries)

    def add_track(
        self,
        mbid: str,
        title: str | None = None,
        artist: str | None = None,
    ) -> None:
        """Add a track to the pool (known to have LB neighbors)."""
        if mbid not in self._entries:
            self._entries[mbid] = PoolEntry(
                mbid=mbid, title=title, artist=artist,
            )

    def add_from_neighbors(
        self,
        neighbor_mbids: list[str],
        search_space=None,
    ) -> int:
        """Add discovered neighbors to the pool.

        Called after beam search expands a node — all its LB neighbors
        are, by definition, tracks with LB data.

        Args:
            neighbor_mbids: MBIDs discovered via LB similar-recordings
            search_space: Optional SearchSpace to pull title/artist from features

        Returns:
            Number of new entries added.
        """
        added = 0
        for mbid in neighbor_mbids:
            if mbid not in self._entries:
                title = None
                artist = None
                if search_space:
                    features = search_space.get_features(mbid)
                    if features:
                        title = features.title
                        artist = features.artist
                self._entries[mbid] = PoolEntry(
                    mbid=mbid, title=title, artist=artist,
                )
                added += 1

        if added > 0:
            self._save_pool()
            logger.info("Proxy pool grew by %d entries (total: %d)", added, self.size)

        return added

    def find_proxy(
        self,
        target_features: TrackFeatures,
        search_space=None,
        exclude_mbids: set[str] | None = None,
    ) -> ProxyResult | None:
        """Find the most sonically similar track in the pool.

        Scores the target's features against every pool entry that has
        features available in the search space. Uses Module 1's full
        12-dimension compatibility scoring.

        Args:
            target_features: Features of the user's chosen track
            search_space: SearchSpace to fetch pool entries' features from
            exclude_mbids: MBIDs to skip (e.g., the other endpoint)

        Returns:
            ProxyResult with the best match, or None if pool is empty/unusable.
        """
        if not self._entries:
            return None

        exclude = exclude_mbids or set()
        best_score = -1.0
        best_entry: PoolEntry | None = None

        for entry in self._entries.values():
            if entry.mbid in exclude:
                continue
            if entry.mbid == target_features.mbid:
                continue

            # Get features for this pool entry
            pool_features = None
            if search_space:
                pool_features = search_space.get_features(entry.mbid)

            if pool_features is None:
                continue

            # Score using Module 1's compatibility
            result = self.kb.get_compatibility(target_features, pool_features)
            if result.probability > best_score:
                best_score = result.probability
                best_entry = entry

        if best_entry is None:
            logger.warning(
                "No proxy found for %s — pool has %d entries but none had features",
                target_features.mbid,
                self.size,
            )
            return None

        return ProxyResult(
            original_mbid=target_features.mbid,
            proxy_mbid=best_entry.mbid,
            proxy_title=best_entry.title,
            proxy_artist=best_entry.artist,
            compatibility_score=best_score,
            needed_proxy=True,
        )

    def has_track(self, mbid: str) -> bool:
        """Check if an MBID is in the pool."""
        return mbid in self._entries

    def get_all_mbids(self) -> list[str]:
        """Return all MBIDs in the pool."""
        return list(self._entries.keys())
