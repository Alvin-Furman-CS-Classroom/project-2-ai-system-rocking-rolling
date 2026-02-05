"""Music Knowledge Base with clean Python API.

This module provides a probabilistic knowledge base for music theory rules
using ProbLog. The public API does not expose any ProbLog types.
"""

from pathlib import Path

from problog import get_evaluatable
from problog.engine import DefaultEngine
from problog.logic import Constant, Term
from problog.program import PrologString, SimpleProgram

from .data_models import (
    PlaylistValidation,
    TrackFeatures,
    TransitionResult,
    UserPreferences,
)
from .rules_helpers import (
    circle_of_fifths_distance,
    is_double_time,
    mfcc_distance,
    normalize_key,
)


class MusicKnowledgeBase:
    """
    Probabilistic knowledge base for music theory rules.

    Provides a clean Python interface for querying track compatibility.
    All ProbLog internals are hidden from the public API.

    Example:
        kb = MusicKnowledgeBase()

        # Set user preferences
        kb.set_preferences(UserPreferences(
            prefer_consistent_tempo=True,
            target_moods=["happy", "party"]
        ))

        # Query compatibility between two tracks
        result = kb.get_compatibility(track1, track2)
        print(f"Compatibility: {result.probability:.2%}")
        print(f"A* cost: {result.penalty:.3f}")
    """

    # Compatibility threshold for is_compatible flag
    COMPATIBILITY_THRESHOLD = 0.3

    def __init__(self, rules_file: str | Path | None = None):
        """
        Initialize the knowledge base with music theory rules.

        Args:
            rules_file: Path to the ProbLog rules file. If None, uses the
                default music_theory.pl in the same directory.
        """
        if rules_file is None:
            rules_file = Path(__file__).parent / "music_theory.pl"
        else:
            rules_file = Path(rules_file)

        self._preferences = UserPreferences()
        self._track_counter = 0

        # Initialize ProbLog
        self._init_problog(rules_file)

    def set_preferences(self, preferences: UserPreferences) -> None:
        """Set user preferences for compatibility scoring."""
        self._preferences = preferences

    def get_preferences(self) -> UserPreferences:
        """Get current user preferences."""
        return self._preferences

    def get_compatibility(
        self,
        track1: TrackFeatures,
        track2: TrackFeatures,
    ) -> TransitionResult:
        """
        Query the compatibility between two tracks.

        This is the main public method. Returns probability of a smooth
        transition from track1 to track2.

        Args:
            track1: Source track features
            track2: Destination track features

        Returns:
            TransitionResult with probability, penalty, and component scores
        """
        # Create fresh facts program for this query
        facts = SimpleProgram()

        # Add track facts
        t1_id = "track1"
        t2_id = "track2"
        self._add_track_facts(facts, t1_id, track1)
        self._add_track_facts(facts, t2_id, track2)

        # Add computed facts (circle distance, bpm diff, etc.)
        self._add_computed_facts(facts, t1_id, t2_id, track1, track2)

        # Add preference facts
        self._add_preference_facts(facts)

        # Build database and run queries
        db = self._base_db.extend()
        for statement in facts:
            db += statement

        # Query all compatibility components
        t1 = Term(t1_id)
        t2 = Term(t2_id)

        queries = [
            ("smooth_transition", Term("smooth_transition", t1, t2)),
            ("key_compatible", Term("key_compatible", t1, t2)),
            ("tempo_compatible", Term("tempo_compatible", t1, t2)),
            ("energy_compatible", Term("energy_compatible", t1, t2)),
            ("loudness_compatible", Term("loudness_compatible", t1, t2)),
            ("mood_compatible", Term("mood_compatible", t1, t2)),
            ("timbre_compatible", Term("timbre_compatible", t1, t2)),
        ]

        query_terms = [q[1] for q in queries]
        lf = self._engine.ground_all(db, queries=query_terms)
        results = get_evaluatable().create_from(lf).evaluate()

        # Extract probabilities
        probs = {}
        for name, term in queries:
            probs[name] = float(results.get(term, 0.0))

        # Build violations list
        violations = []
        component_threshold = 0.3
        if probs["key_compatible"] < component_threshold:
            violations.append(f"Key incompatible: {track1.key} {track1.scale} -> {track2.key} {track2.scale}")
        if probs["tempo_compatible"] < component_threshold:
            violations.append(f"Tempo jump: {track1.bpm:.0f} -> {track2.bpm:.0f} BPM")
        if probs["energy_compatible"] < component_threshold:
            violations.append(f"Energy jump: {track1.energy_score:.2f} -> {track2.energy_score:.2f}")
        if probs["mood_compatible"] < component_threshold:
            violations.append("Mood incompatible")

        # Build explanation
        explanation = self._build_explanation(track1, track2, probs)

        probability = probs["smooth_transition"]
        return TransitionResult(
            probability=probability,
            penalty=1.0 - probability,
            is_compatible=probability >= self.COMPATIBILITY_THRESHOLD,
            key_compatibility=probs["key_compatible"],
            tempo_compatibility=probs["tempo_compatible"],
            energy_compatibility=probs["energy_compatible"],
            loudness_compatibility=probs["loudness_compatible"],
            mood_compatibility=probs["mood_compatible"],
            timbre_compatibility=probs["timbre_compatible"],
            violations=violations,
            explanation=explanation,
        )

    def get_penalty(self, track1: TrackFeatures, track2: TrackFeatures) -> float:
        """
        Get the transition penalty for A* search (1 - probability).

        Args:
            track1: Source track
            track2: Destination track

        Returns:
            Penalty in [0.0, 1.0] where 0 = perfect transition
        """
        result = self.get_compatibility(track1, track2)
        return result.penalty

    def validate_playlist(
        self,
        tracks: list[TrackFeatures],
    ) -> PlaylistValidation:
        """
        Validate a complete playlist sequence.

        Args:
            tracks: List of tracks in playlist order

        Returns:
            PlaylistValidation with overall score and per-transition details
        """
        if len(tracks) < 2:
            return PlaylistValidation(
                overall_probability=1.0,
                overall_penalty=0.0,
                is_valid=True,
                transitions=[],
                weakest_transition=None,
                total_violations=0,
            )

        transitions = []
        total_violations = 0
        min_prob = 1.0
        min_idx = 0

        for i in range(len(tracks) - 1):
            result = self.get_compatibility(tracks[i], tracks[i + 1])
            transitions.append(result)
            total_violations += len(result.violations)

            if result.probability < min_prob:
                min_prob = result.probability
                min_idx = i

        # Calculate overall metrics
        avg_prob = sum(t.probability for t in transitions) / len(transitions)
        avg_penalty = 1.0 - avg_prob
        all_valid = all(t.is_compatible for t in transitions)

        return PlaylistValidation(
            overall_probability=avg_prob,
            overall_penalty=avg_penalty,
            is_valid=all_valid,
            transitions=transitions,
            weakest_transition=(min_idx, min_prob) if transitions else None,
            total_violations=total_violations,
        )

    def clear(self) -> None:
        """Clear any cached state (but keep preferences)."""
        self._track_counter = 0

    # -------------------------------------------------------------------------
    # Private methods (ProbLog internals hidden here)
    # -------------------------------------------------------------------------

    def _init_problog(self, rules_file: Path) -> None:
        """Initialize ProbLog engine with rules."""
        with open(rules_file) as f:
            rules_str = f.read()

        self._rules_program = PrologString(rules_str)
        self._engine = DefaultEngine()
        self._base_db = self._engine.prepare(self._rules_program)

    def _add_track_facts(
        self,
        facts: SimpleProgram,
        track_id: str,
        track: TrackFeatures,
    ) -> None:
        """Convert TrackFeatures to ProbLog facts."""
        tid = Term(track_id)

        # Key facts: has_key(track_id, key, scale, strength)
        key_term = Term(normalize_key(track.key))
        scale_term = Term(track.scale)
        facts += Term("has_key", tid, key_term, scale_term, Constant(track.key_strength))

        # BPM: has_bpm(track_id, bpm)
        facts += Term("has_bpm", tid, Constant(track.bpm))

        # Energy score: energy_score(track_id, score)
        facts += Term("energy_score", tid, Constant(track.energy_score))

        # Danceability
        danceability_score = track.danceability_score
        facts += Term("is_danceable", tid, Constant(danceability_score))

        # Loudness (if available)
        if track.average_loudness is not None:
            facts += Term("average_loudness", tid, Constant(track.average_loudness))

        # Dynamic complexity (if available)
        if track.dynamic_complexity is not None:
            facts += Term("dynamic_complexity", tid, Constant(track.dynamic_complexity))

        # Mood (use the dominant mood)
        mood = self._get_dominant_mood(track)
        if mood:
            facts += Term("has_mood", tid, Term(mood))

    def _add_computed_facts(
        self,
        facts: SimpleProgram,
        t1_id: str,
        t2_id: str,
        track1: TrackFeatures,
        track2: TrackFeatures,
    ) -> None:
        """Add computed relationship facts between tracks."""
        t1 = Term(t1_id)
        t2 = Term(t2_id)
        k1 = Term(normalize_key(track1.key))
        k2 = Term(normalize_key(track2.key))

        # Circle of fifths distance
        dist = circle_of_fifths_distance(track1.key, track2.key)
        facts += Term("circle_distance", k1, k2, Constant(dist))

        # BPM difference (absolute)
        bpm_diff = abs(track1.bpm - track2.bpm)
        facts += Term("bpm_diff", Constant(track1.bpm), Constant(track2.bpm), Constant(bpm_diff))

        # Double-time check
        if is_double_time(track1.bpm, track2.bpm):
            facts += Term("is_double_time", Constant(track1.bpm), Constant(track2.bpm))

        # Energy difference
        energy_diff = abs(track1.energy_score - track2.energy_score)
        facts += Term("energy_diff", Constant(track1.energy_score), Constant(track2.energy_score), Constant(energy_diff))

        # Loudness difference (if both available)
        if track1.average_loudness is not None and track2.average_loudness is not None:
            loudness_diff = abs(track1.average_loudness - track2.average_loudness)
            facts += Term("loudness_diff", Constant(track1.average_loudness), Constant(track2.average_loudness), Constant(loudness_diff))

        # MFCC distance
        mfcc_dist = mfcc_distance(track1.mfcc, track2.mfcc)
        if mfcc_dist is not None:
            facts += Term("mfcc_dist", t1, t2, Constant(mfcc_dist))

    def _add_preference_facts(self, facts: SimpleProgram) -> None:
        """Add user preference facts to ProbLog."""
        prefs = self._preferences

        if prefs.prefer_consistent_tempo:
            facts += Term("pref_consistent_tempo")

        if prefs.target_moods:
            for mood in prefs.target_moods:
                facts += Term("pref_target_mood", Term(mood))

        if prefs.avoid_moods:
            for mood in prefs.avoid_moods:
                facts += Term("pref_avoid_mood", Term(mood))

    def _get_dominant_mood(self, track: TrackFeatures) -> str | None:
        """Get the dominant mood from highlevel classifiers."""
        moods = [
            ("happy", track.mood_happy),
            ("sad", track.mood_sad),
            ("aggressive", track.mood_aggressive),
            ("relaxed", track.mood_relaxed),
            ("party", track.mood_party),
        ]

        # Find the mood with highest probability where value matches the positive class
        best_mood = None
        best_prob = 0.0

        for mood_name, mood_data in moods:
            if mood_data is not None:
                value, prob = mood_data
                # Check if this is the positive classification
                if value == mood_name and prob > best_prob:
                    best_mood = mood_name
                    best_prob = prob

        return best_mood

    def _build_explanation(
        self,
        track1: TrackFeatures,
        track2: TrackFeatures,
        probs: dict[str, float],
    ) -> str:
        """Build a human-readable explanation of the compatibility."""
        lines = []

        # Key
        key_dist = circle_of_fifths_distance(track1.key, track2.key)
        lines.append(
            f"Key: {track1.key} {track1.scale} -> {track2.key} {track2.scale} "
            f"(dist={key_dist}, P={probs['key_compatible']:.0%})"
        )

        # Tempo
        bpm_diff = abs(track1.bpm - track2.bpm)
        dt_note = " [double-time]" if is_double_time(track1.bpm, track2.bpm) else ""
        lines.append(
            f"Tempo: {track1.bpm:.0f} -> {track2.bpm:.0f} BPM "
            f"(diff={bpm_diff:.0f}{dt_note}, P={probs['tempo_compatible']:.0%})"
        )

        # Energy
        energy_diff = abs(track1.energy_score - track2.energy_score)
        lines.append(
            f"Energy: {track1.energy_score:.2f} -> {track2.energy_score:.2f} "
            f"(diff={energy_diff:.2f}, P={probs['energy_compatible']:.0%})"
        )

        # Loudness
        if track1.average_loudness is not None and track2.average_loudness is not None:
            loud_diff = abs(track1.average_loudness - track2.average_loudness)
            lines.append(
                f"Loudness: {track1.average_loudness:.2f} -> {track2.average_loudness:.2f} "
                f"(diff={loud_diff:.2f}, P={probs['loudness_compatible']:.0%})"
            )

        # Mood
        m1 = self._get_dominant_mood(track1) or "unknown"
        m2 = self._get_dominant_mood(track2) or "unknown"
        lines.append(f"Mood: {m1} -> {m2} (P={probs['mood_compatible']:.0%})")

        return "\n".join(lines)
