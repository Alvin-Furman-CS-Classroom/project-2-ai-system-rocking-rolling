"""Playlist assembler — orchestrates the full generation pipeline.

Pipeline:
1. Apply user preferences (if UserProfile exists)
2. Run beam search (Module 2's find_path_bidirectional)
3. Resolve features for all tracks in the path
4. Apply constraints (CSP local search)
5. Generate explanations
6. Return AssembledPlaylist
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from module1 import MusicKnowledgeBase, TransitionResult, UserPreferences
from module2 import BeamSearch, PlaylistPath, SearchSpace

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
    ):
        self.kb = knowledge_base or MusicKnowledgeBase()
        self.search_space = search_space
        self.essentia_client = essentia_client
        self.user_profile = user_profile
        self.constraints = constraints or list(DEFAULT_CONSTRAINTS)
        self.beam_width = beam_width
        self._profile_path = profile_path

    def generate_playlist(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        preferences: UserPreferences | None = None,
    ) -> AssembledPlaylist | None:
        """Generate a complete playlist from source to destination.

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

        # Step 3: Run beam search
        beam = BeamSearch(
            knowledge_base=self.kb,
            search_space=search_space,
            beam_width=self.beam_width,
        )

        path = beam.find_path_bidirectional(
            source_mbid, dest_mbid, target_length=target_length
        )

        if path is None:
            logger.info("No path found from %s to %s", source_mbid, dest_mbid)
            return None

        # Step 4: Resolve features for all tracks
        tracks = []
        for mbid in path.mbids:
            features = search_space.get_features(mbid)
            if features is None and self.essentia_client:
                # Essentia fallback — need title/artist for yt-dlp search
                features = self.essentia_client.fetch_features(mbid)
            if features is None:
                # Create a minimal TrackFeatures so we don't break the pipeline
                from module1 import TrackFeatures
                features = TrackFeatures(mbid=mbid)
            tracks.append(features)

        # Step 5: Apply constraints
        constrained_tracks, constraint_results = resolve_constraints(
            tracks, self.constraints, search_space
        )

        # Step 6: Re-score transitions if tracks were swapped
        transitions = path.transitions
        if constrained_tracks != tracks:
            transitions = self._rescore_transitions(constrained_tracks)
            path = PlaylistPath(
                mbids=[t.mbid for t in constrained_tracks],
                total_cost=sum(t.penalty for t in transitions),
                transitions=transitions,
            )

        # Step 7: Generate explanations
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
        self, tracks: list["TrackFeatures"],
    ) -> list[TransitionResult]:
        """Re-score all transitions after constraint resolution."""
        transitions = []
        for i in range(len(tracks) - 1):
            result = self.kb.get_compatibility(tracks[i], tracks[i + 1])
            transitions.append(result)
        return transitions
