"""Playlist orchestrator — top-level integration layer for Wave Guide.

Handles both MBID-based and mood-based playlist requests by routing through
Module 4 (mood classification) before delegating to Module 3's assembly pipeline.

Mood resolution strategy:
- Mood destination: forward beam search reaches centroid via direct-connection
  fallback at target_length-1 (centroid features are pre-seeded, so scoring works).
- Mood source: centroid has no ListenBrainz neighbors, so the forward search from
  it cannot expand. Instead we search in reverse (dest → centroid), then reverse
  and strip the synthetic node to produce the final playlist.
- Both moods: unsupported — returns None (no real anchor for neighbor expansion).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from module1 import MusicKnowledgeBase, TrackFeatures, UserPreferences
from module2 import BeamSearch, PlaylistPath, SearchSpace
from module3 import (
    DEFAULT_CONSTRAINTS,
    AssembledPlaylist,
    PlaylistAssembler,
    explain_playlist,
    resolve_constraints,
)
from module4 import MoodClassifier, MoodLabel

logger = logging.getLogger(__name__)


@dataclass
class TrackInput:
    """Source or destination input for a playlist request.

    Set ``type`` to ``"mbid"`` and provide ``mbid`` for a specific track,
    or ``type`` to ``"mood"`` and provide ``mood`` for a mood-based query.
    """

    type: Literal["mbid", "mood"]
    mbid: str | None = None
    mood: str | None = None


@dataclass
class PlaylistRequest:
    """Parameters for a playlist generation request."""

    source: TrackInput
    destination: TrackInput
    length: int = 7
    beam_width: int = 10


class PlaylistOrchestrator:
    """Top-level orchestrator integrating Modules 1–4.

    Accepts either MBID or mood inputs for source/destination, resolves mood
    labels to centroid feature vectors via Module 4, then delegates path finding
    and assembly to Module 3's PlaylistAssembler (or a manual reverse-search
    path for mood sources).
    """

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase,
        classifier: MoodClassifier,
        profile_path: Path | None = None,
    ):
        self.kb = knowledge_base
        self.classifier = classifier
        self._profile_path = profile_path

    def generate(
        self,
        request: PlaylistRequest,
        search_space: SearchSpace | None = None,
    ) -> AssembledPlaylist | None:
        """Generate a playlist from source to destination.

        Args:
            request: Playlist generation parameters.
            search_space: Optional pre-seeded search space. If provided, mood
                centroid features and any pre-fetched MBID features are merged
                into it. If omitted, a fresh SearchSpace is created.

        Returns None if no path can be found.
        """
        source_mbid, source_synthetic = self._resolve_input(request.source)
        dest_mbid, dest_synthetic = self._resolve_input(request.destination)

        if source_mbid is None or dest_mbid is None:
            logger.warning("Could not resolve source or destination input")
            return None

        # Both mood inputs: no real track to anchor neighbor expansion
        if source_synthetic is not None and dest_synthetic is not None:
            logger.warning("Both source and destination are mood inputs — unsupported")
            return None

        # Use provided search space or create a fresh one
        if search_space is None:
            search_space = SearchSpace(knowledge_base=self.kb)

        # Seed synthetic centroid features (mood inputs)
        if source_synthetic is not None:
            search_space.add_features(source_mbid, source_synthetic)
        if dest_synthetic is not None:
            search_space.add_features(dest_mbid, dest_synthetic)

        if source_synthetic is not None:
            # Mood source: reverse search then flip
            return self._generate_from_mood_source(
                source_mbid=source_mbid,
                dest_mbid=dest_mbid,
                search_space=search_space,
                request=request,
            )

        # Real source (with optional mood dest): PlaylistAssembler handles it.
        # For mood dests, the direct-connection check in BeamSearch fires at
        # target_length-1 because the centroid features are pre-seeded.
        assembler = PlaylistAssembler(
            knowledge_base=self.kb,
            search_space=search_space,
            beam_width=request.beam_width,
            profile_path=self._profile_path,
        )
        playlist = assembler.generate_playlist(
            source_mbid=source_mbid,
            dest_mbid=dest_mbid,
            target_length=request.length,
        )

        if playlist is None:
            return None

        # Strip synthetic centroid from the end when dest was a mood
        if dest_synthetic is not None:
            playlist = self._strip_synthetic_tail(playlist)

        return playlist

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_input(
        self, inp: TrackInput
    ) -> tuple[str | None, TrackFeatures | None]:
        """Return (mbid, synthetic_features | None).

        For MBID inputs the second element is None (features fetched normally).
        For mood inputs the second element is the centroid TrackFeatures and the
        first element is the centroid's synthetic MBID (e.g. ``"centroid_calm"``).
        """
        if inp.type == "mbid":
            if not inp.mbid:
                return None, None
            return inp.mbid, None

        if not inp.mood:
            return None, None
        try:
            mood_label = MoodLabel(inp.mood.lower())
        except ValueError:
            logger.warning("Unknown mood label: %s", inp.mood)
            return None, None

        centroid = self.classifier.get_centroid_track(mood_label)
        return centroid.mbid, centroid

    def _generate_from_mood_source(
        self,
        source_mbid: str,
        dest_mbid: str,
        search_space: SearchSpace,
        request: PlaylistRequest,
    ) -> AssembledPlaylist | None:
        """Handle mood source by searching dest→centroid then reversing.

        Since mood centroids have no ListenBrainz neighbors, a forward search
        from the centroid immediately stalls. Instead we search from the real
        destination toward the centroid (which IS reachable via the
        direct-connection check in BeamSearch.find_path). We then reverse the
        resulting path and strip the synthetic node from the front.
        """
        beam = BeamSearch(
            knowledge_base=self.kb,
            search_space=search_space,
            beam_width=request.beam_width,
        )

        # Search: real dest → synthetic centroid
        reverse_path = beam.find_path(
            source_mbid=dest_mbid,
            dest_mbid=source_mbid,
            target_length=request.length,
        )

        if reverse_path is None:
            logger.info(
                "Reverse search (dest→mood centroid) found no path for %s → %s",
                dest_mbid,
                source_mbid,
            )
            return None

        # Reverse to get centroid-first ordering
        reversed_mbids = list(reversed(reverse_path.mbids))

        # Strip the synthetic centroid from the front
        if reversed_mbids and reversed_mbids[0] == source_mbid:
            reversed_mbids = reversed_mbids[1:]

        if len(reversed_mbids) < 2:
            logger.info("Path too short after stripping mood centroid")
            return None

        # Re-score transitions for the (now real-tracks-only) forward path
        transitions = []
        for i in range(len(reversed_mbids) - 1):
            result = search_space.get_transition_result(
                reversed_mbids[i], reversed_mbids[i + 1]
            )
            if result is None:
                logger.warning(
                    "Missing transition result between %s and %s",
                    reversed_mbids[i],
                    reversed_mbids[i + 1],
                )
                return None
            transitions.append(result)

        path = PlaylistPath(
            mbids=reversed_mbids,
            total_cost=sum(t.penalty for t in transitions),
            transitions=transitions,
        )

        # Resolve features for each track
        tracks = [
            search_space.get_features(mbid) or TrackFeatures(mbid=mbid)
            for mbid in path.mbids
        ]

        # Apply constraints (CSP local search)
        constrained_tracks, constraint_results = resolve_constraints(
            tracks, list(DEFAULT_CONSTRAINTS), search_space
        )

        # Re-score transitions if constraint resolution swapped any tracks
        if constrained_tracks != tracks:
            transitions = [
                self.kb.get_compatibility(
                    constrained_tracks[i], constrained_tracks[i + 1]
                )
                for i in range(len(constrained_tracks) - 1)
            ]
            path = PlaylistPath(
                mbids=[t.mbid for t in constrained_tracks],
                total_cost=sum(t.penalty for t in transitions),
                transitions=transitions,
            )

        prefs = UserPreferences()
        explanation = explain_playlist(
            constrained_tracks, path.transitions, prefs, constraint_results
        )

        return AssembledPlaylist(
            path=path,
            tracks=constrained_tracks,
            explanation=explanation,
            constraints_applied=constraint_results,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _strip_synthetic_tail(
        self, playlist: AssembledPlaylist
    ) -> AssembledPlaylist | None:
        """Remove a synthetic centroid track from the end of the playlist.

        When the destination was a mood label, BeamSearch appends the centroid
        MBID (e.g. ``"centroid_calm"``) as the final node. We strip it so the
        playlist only contains real tracks.
        """
        tracks = playlist.tracks
        path = playlist.path

        if not tracks:
            return playlist

        last_mbid = tracks[-1].mbid or ""
        if not last_mbid.startswith("centroid_"):
            return playlist

        trimmed_tracks = tracks[:-1]
        trimmed_mbids = path.mbids[:-1]
        trimmed_transitions = path.transitions[:-1]

        if len(trimmed_tracks) < 2:
            return None

        trimmed_path = PlaylistPath(
            mbids=trimmed_mbids,
            total_cost=sum(t.penalty for t in trimmed_transitions),
            transitions=trimmed_transitions,
        )

        prefs = UserPreferences()
        explanation = explain_playlist(
            trimmed_tracks,
            trimmed_path.transitions,
            prefs,
            playlist.constraints_applied,
        )

        return AssembledPlaylist(
            path=trimmed_path,
            tracks=trimmed_tracks,
            explanation=explanation,
            constraints_applied=playlist.constraints_applied,
            created_at=playlist.created_at,
        )
