"""Playlist assembler — orchestrates the full generation pipeline.

Pipeline:
1. Apply user preferences (if UserProfile exists)
2. Check if source/dest have LB neighbors — find proxies if not
3. Run beam search (Module 2's find_path_bidirectional)
4. Swap proxies back out — user's songs stay at endpoints
5. Resolve features for all tracks in the path
6. Apply constraints (CSP local search)
7. Generate explanations
8. Return AssembledPlaylist
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult, UserPreferences
from module2 import BeamSearch, MusicBrainzClient, PlaylistPath, SearchSpace

from .constraints import (
    DEFAULT_CONSTRAINTS,
    PlaylistConstraint,
    evaluate_all,
    resolve_constraints,
)
from .data_models import (
    AssembledPlaylist,
    PlaylistFeedback,
    UserProfile,
)
from .essentia_client import EssentiaClient
from .explainer import explain_playlist
from .proxy_pool import ProxyPool, ProxyResult
from .user_model import load_profile, save_profile, update_from_feedback

logger = logging.getLogger(__name__)


class PlaylistAssembler:
    """Orchestrates playlist generation with constraints, explanations, and user modeling."""

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase | None = None,
        search_space: SearchSpace | None = None,
        essentia_client: EssentiaClient | None = None,
        user_profile: UserProfile | None = None,
        constraints: list[PlaylistConstraint] | None = None,
        beam_width: int = 10,
        profile_path: Path | None = None,
        proxy_pool: ProxyPool | None = None,
    ):
        self.kb = knowledge_base or MusicKnowledgeBase()
        self.search_space = search_space
        self.essentia_client = essentia_client
        self.user_profile = user_profile
        self.constraints = constraints or list(DEFAULT_CONSTRAINTS)
        self.beam_width = beam_width
        self._profile_path = profile_path
        self.proxy_pool = proxy_pool

    def _check_has_neighbors(self, mbid: str, search_space: SearchSpace) -> bool:
        """Check if a track has LB neighbors (can be expanded by beam search)."""
        neighbors = search_space.get_neighbors(mbid)
        return len(neighbors) > 0

    def _resolve_features_for_track(
        self, mbid: str, search_space: SearchSpace
    ) -> TrackFeatures | None:
        """Get features for a track, using Essentia or MB metadata as fallback.

        Fallback chain: AcousticBrainz → Essentia (yt-dlp) → MusicBrainz metadata.
        Essentia needs title+artist to search YouTube, so we fetch those from
        MusicBrainz first if needed.
        """
        features = search_space.get_features(mbid)
        if features is not None:
            return features

        # Get title+artist from MusicBrainz (needed for Essentia's yt-dlp search)
        mb_client = search_space.mb_client
        mb_meta = mb_client.get_recording_metadata(mbid)
        title = None
        artist = None
        if mb_meta:
            # Recording metadata doesn't have title/artist name directly —
            # use the MB recording lookup which includes the title field
            title, artist = self._get_title_artist_from_mb(mbid, mb_client)

        # Essentia fallback (needs essentia lib + yt-dlp + title)
        if self.essentia_client and title:
            logger.info(
                "Trying Essentia extraction for %s (%s — %s)",
                mbid, artist or "?", title,
            )
            features = self.essentia_client.fetch_features(mbid, title=title, artist=artist)
            if features is not None:
                # Merge MB editorial metadata into Essentia features
                if mb_meta.artist_mbid:
                    features.artist_mbid = mb_meta.artist_mbid
                    related = mb_client.get_artist_relationships(mb_meta.artist_mbid)
                    features.mb_artist_related_mbids = related
                if mb_meta.release_year is not None:
                    features.mb_release_year = mb_meta.release_year
                if mb_meta.genre_tags:
                    features.mb_genre_tags = mb_meta.genre_tags
                search_space.add_features(mbid, features)
                return features

        # Last resort: build minimal features from MusicBrainz metadata alone
        features = self._features_from_mb_meta(mbid, mb_meta, mb_client)
        if features is not None:
            search_space.add_features(mbid, features)
        return features

    def _get_title_artist_from_mb(
        self, mbid: str, mb_client: MusicBrainzClient
    ) -> tuple[str | None, str | None]:
        """Fetch track title and artist name from MusicBrainz recording lookup."""
        url = f"{mb_client.config.base_url}/recording/{mbid}"
        params = {"inc": "artists", "fmt": "json"}
        response = mb_client._request_with_retry(url, params=params)
        if response is None or response.status_code != 200:
            return None, None
        try:
            data = response.json()
        except ValueError:
            return None, None

        title = data.get("title")
        artist = None
        artist_credits = data.get("artist-credit", [])
        if artist_credits:
            artist = artist_credits[0].get("name") or artist_credits[0].get("artist", {}).get("name")
        return title, artist

    def _features_from_mb_meta(
        self, mbid: str, meta, mb_client: MusicBrainzClient
    ) -> TrackFeatures | None:
        """Build minimal TrackFeatures from already-fetched MusicBrainz metadata.

        This gives us artist relationships, release year, and genre tags —
        enough to score 3 of 12 compatibility dimensions (artist, era, MB genre).
        Other dimensions fall back to neutral (0.5) in the knowledge base.
        """
        if meta is None:
            return None

        # Need at least some useful data
        if not meta.artist_mbid and meta.release_year is None and not meta.genre_tags:
            return None

        features = TrackFeatures(mbid=mbid)

        if meta.artist_mbid:
            features.artist_mbid = meta.artist_mbid
            related = mb_client.get_artist_relationships(meta.artist_mbid)
            features.mb_artist_related_mbids = related

        if meta.release_year is not None:
            features.mb_release_year = meta.release_year

        if meta.genre_tags:
            features.mb_genre_tags = meta.genre_tags

        logger.info(
            "Built minimal features for %s from MB metadata "
            "(artist=%s, year=%s, genres=%s)",
            mbid,
            meta.artist_mbid or "?",
            meta.release_year or "?",
            meta.genre_tags or [],
        )
        return features

    def _find_proxy_for(
        self,
        mbid: str,
        search_space: SearchSpace,
        exclude_mbids: set[str] | None = None,
    ) -> ProxyResult | None:
        """Find a proxy track for an MBID with no LB neighbors.

        Extracts features for the target track (via AB or Essentia),
        then searches the proxy pool for the most compatible match.
        """
        if self.proxy_pool is None:
            return None

        # Get features for the target track
        target_features = self._resolve_features_for_track(mbid, search_space)
        if target_features is None:
            logger.warning("Cannot find proxy for %s — no features available", mbid)
            return None

        # Load features for pool entries so proxy scoring works.
        # Use batch AB fetch for efficiency, then MB fallback for any gaps.
        pool_mbids = self.proxy_pool.get_all_mbids()
        missing = [m for m in pool_mbids if not search_space.has_features(m)]
        if missing:
            # Batch AB fetch (up to 25 at a time via the batch endpoint)
            search_space.enrich_tracks(missing)
            # For entries still missing after AB, try MB metadata
            still_missing = [m for m in missing if not search_space.has_features(m)]
            mb_client = search_space.mb_client
            for pool_mbid in still_missing[:50]:  # cap to avoid API overload
                mb_meta = mb_client.get_recording_metadata(pool_mbid)
                features = self._features_from_mb_meta(pool_mbid, mb_meta, mb_client)
                if features is not None:
                    search_space.add_features(pool_mbid, features)

        return self.proxy_pool.find_proxy(
            target_features, search_space, exclude_mbids=exclude_mbids,
        )

    def _grow_pool_from_search(self, search_space: SearchSpace) -> None:
        """Add discovered neighbors to the proxy pool for future use."""
        if self.proxy_pool is None:
            return
        stats = search_space.cache_stats()
        if stats.get("neighbors_cached", 0) > 0:
            # All MBIDs that showed up as neighbors have LB data
            all_cached = list(search_space._neighbors_cache.keys())
            for mbid in all_cached:
                neighbors = search_space._neighbors_cache[mbid]
                self.proxy_pool.add_from_neighbors(neighbors, search_space)

    def generate_playlist(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        preferences: UserPreferences | None = None,
    ) -> AssembledPlaylist | None:
        """Generate a complete playlist from source to destination.

        If source or dest have no LB neighbors, finds proxy tracks
        from the pool, runs beam search between proxies, then swaps
        the user's original songs back in at the endpoints.

        Args:
            source_mbid: MusicBrainz ID of the starting track
            dest_mbid: MusicBrainz ID of the ending track
            target_length: Desired playlist length (number of tracks)
            preferences: Override preferences (otherwise uses user profile)

        Returns:
            AssembledPlaylist with tracks, explanations, and constraint results,
            or None if no path was found.
        """
        # Step 1: Apply preferences
        prefs = preferences
        if prefs is None and self.user_profile:
            prefs = self.user_profile.to_user_preferences()
        if prefs is None:
            prefs = UserPreferences()

        self.kb.set_preferences(prefs)

        # Step 2: Initialize search space if not provided
        search_space = self.search_space
        if search_space is None:
            search_space = SearchSpace(self.kb)

        # Step 3: Check if source/dest need proxies
        source_proxy: ProxyResult | None = None
        dest_proxy: ProxyResult | None = None
        search_source = source_mbid
        search_dest = dest_mbid

        source_has_neighbors = self._check_has_neighbors(source_mbid, search_space)
        dest_has_neighbors = self._check_has_neighbors(dest_mbid, search_space)

        if not source_has_neighbors:
            logger.info("Source %s has no LB neighbors — finding proxy", source_mbid)
            source_proxy = self._find_proxy_for(
                source_mbid, search_space, exclude_mbids={dest_mbid},
            )
            if source_proxy:
                search_source = source_proxy.proxy_mbid
                logger.info(
                    "Using proxy %s (%s) for source (compatibility: %.0f%%)",
                    source_proxy.proxy_mbid,
                    source_proxy.proxy_title or "?",
                    source_proxy.compatibility_score * 100,
                )
            else:
                logger.warning("No proxy found for source %s", source_mbid)

        if not dest_has_neighbors:
            logger.info("Dest %s has no LB neighbors — finding proxy", dest_mbid)
            dest_proxy = self._find_proxy_for(
                dest_mbid, search_space,
                exclude_mbids={source_mbid, search_source},
            )
            if dest_proxy:
                search_dest = dest_proxy.proxy_mbid
                logger.info(
                    "Using proxy %s (%s) for dest (compatibility: %.0f%%)",
                    dest_proxy.proxy_mbid,
                    dest_proxy.proxy_title or "?",
                    dest_proxy.compatibility_score * 100,
                )
            else:
                logger.warning("No proxy found for dest %s", dest_mbid)

        # Step 4: Run beam search (between proxies if needed)
        beam = BeamSearch(
            knowledge_base=self.kb,
            search_space=search_space,
            beam_width=self.beam_width,
        )

        # Adjust target length for proxy endpoints that will be swapped out
        inner_length = target_length
        if source_proxy:
            inner_length = max(3, inner_length)  # need at least proxy + middle + proxy
        if dest_proxy:
            inner_length = max(3, inner_length)

        path = beam.find_path_bidirectional(
            search_source, search_dest, target_length=inner_length
        )

        if path is None:
            logger.info("No path found from %s to %s", search_source, search_dest)
            return None

        # Step 5: Grow the proxy pool from discovered neighbors
        self._grow_pool_from_search(search_space)

        # Step 6: Swap proxies back out — user's songs stay at endpoints
        final_mbids = list(path.mbids)
        if source_proxy and final_mbids[0] == source_proxy.proxy_mbid:
            final_mbids[0] = source_mbid
        if dest_proxy and final_mbids[-1] == dest_proxy.proxy_mbid:
            final_mbids[-1] = dest_mbid

        # Step 7: Resolve features for all tracks
        tracks = []
        for mbid in final_mbids:
            features = self._resolve_features_for_track(mbid, search_space)
            if features is None:
                features = TrackFeatures(mbid=mbid)
            tracks.append(features)

        # Step 8: Apply constraints
        constrained_tracks, constraint_results = resolve_constraints(
            tracks, self.constraints, search_space
        )

        # Step 9: Re-score transitions with final track list
        transitions = self._rescore_transitions(constrained_tracks)
        path = PlaylistPath(
            mbids=[t.mbid for t in constrained_tracks],
            total_cost=sum(t.penalty for t in transitions),
            transitions=transitions,
        )

        # Step 10: Generate explanations
        explanation = explain_playlist(
            constrained_tracks, transitions, prefs, constraint_results
        )

        return AssembledPlaylist(
            path=path,
            tracks=constrained_tracks,
            explanation=explanation,
            constraints_applied=constraint_results,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def submit_feedback(
        self,
        feedback: PlaylistFeedback,
        transitions: list[TransitionResult],
        learning_rate: float = 0.1,
    ) -> None:
        """Process user feedback to update preferences."""
        if self.user_profile is None:
            self.user_profile = UserProfile()

        update_from_feedback(self.user_profile, feedback, transitions, learning_rate)

        if self._profile_path:
            save_profile(self.user_profile, self._profile_path)

    def _rescore_transitions(
        self, tracks: list[TrackFeatures],
    ) -> list[TransitionResult]:
        """Re-score all transitions after constraint resolution."""
        transitions = []
        for i in range(len(tracks) - 1):
            result = self.kb.get_compatibility(tracks[i], tracks[i + 1])
            transitions.append(result)
        return transitions
