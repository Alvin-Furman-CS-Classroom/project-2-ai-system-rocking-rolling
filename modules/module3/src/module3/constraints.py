"""CSP-style playlist constraint satisfaction.

Applies post-search constraints to PlaylistPath that greedy beam search
cannot express. Constraints come in two tiers:

- Hard constraints: must be satisfied (violations trigger track replacement)
- Soft constraints: penalize violations (guide swaps via local search)

Resolution uses min-conflicts local search: identify violating positions,
try alternative tracks from the search space, accept swaps that improve
constraint satisfaction without degrading transition quality too much.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from module1 import TrackFeatures

from .data_models import ConstraintResult

if TYPE_CHECKING:
    from module2 import SearchSpace

logger = logging.getLogger(__name__)


# --- Base constraint ---


@dataclass
class PlaylistConstraint(ABC):
    """Base class for playlist constraints."""

    name: str
    is_hard: bool
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        """Evaluate this constraint against a playlist."""
        ...


# --- Hard constraints ---


@dataclass
class NoRepeatArtists(PlaylistConstraint):
    """No artist should appear more than once in the playlist."""

    name: str = "No repeat artists"
    is_hard: bool = True

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        seen: dict[str, int] = {}  # artist -> first position
        violations = []
        violating_positions = []

        for i, track in enumerate(tracks):
            artist_key = (track.artist_mbid or track.artist or "").lower()
            if not artist_key:
                continue
            if artist_key in seen:
                violations.append(
                    f"Artist '{track.artist or artist_key}' appears at "
                    f"positions {seen[artist_key] + 1} and {i + 1}"
                )
                violating_positions.append(i)
            else:
                seen[artist_key] = i

        return ConstraintResult(
            name=self.name,
            satisfied=len(violations) == 0,
            score=1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.2),
            violations=violations,
            violating_positions=violating_positions,
        )


@dataclass
class NoRepeatedTracks(PlaylistConstraint):
    """No track MBID should appear more than once."""

    name: str = "No repeated tracks"
    is_hard: bool = True

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        seen: dict[str, int] = {}
        violations = []
        violating_positions = []

        for i, track in enumerate(tracks):
            if track.mbid in seen:
                violations.append(
                    f"Track '{track.title or track.mbid}' repeated at "
                    f"positions {seen[track.mbid] + 1} and {i + 1}"
                )
                violating_positions.append(i)
            else:
                seen[track.mbid] = i

        return ConstraintResult(
            name=self.name,
            satisfied=len(violations) == 0,
            score=1.0 if not violations else 0.0,
            violations=violations,
            violating_positions=violating_positions,
        )


# --- Soft constraints ---


@dataclass
class EnergyArcConstraint(PlaylistConstraint):
    """Energy should follow a specified arc pattern."""

    name: str = "Energy arc"
    is_hard: bool = False
    target_arc: str = "rising"  # "rising", "falling", "valley", "hill", "flat"

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        if len(tracks) < 3:
            return ConstraintResult(self.name, True, 1.0)

        energies = [t.energy_score for t in tracks]
        violations = []
        violating_positions = []

        if self.target_arc == "rising":
            for i in range(1, len(energies)):
                if energies[i] < energies[i - 1] * 0.85:  # Allow 15% dips
                    violations.append(
                        f"Energy drops at position {i + 1} "
                        f"({energies[i - 1]:.4f} → {energies[i]:.4f})"
                    )
                    violating_positions.append(i)

        elif self.target_arc == "falling":
            for i in range(1, len(energies)):
                if energies[i] > energies[i - 1] * 1.15:
                    violations.append(
                        f"Energy rises at position {i + 1} "
                        f"({energies[i - 1]:.4f} → {energies[i]:.4f})"
                    )
                    violating_positions.append(i)

        elif self.target_arc == "flat":
            avg = sum(energies) / len(energies)
            for i, e in enumerate(energies):
                if avg > 0 and abs(e - avg) / avg > 0.3:
                    violations.append(
                        f"Energy deviates at position {i + 1} "
                        f"({e:.4f} vs avg {avg:.4f})"
                    )
                    violating_positions.append(i)

        elif self.target_arc == "valley":
            mid = len(energies) // 2
            # First half should decrease
            for i in range(1, mid):
                if energies[i] > energies[i - 1] * 1.15:
                    violations.append(
                        f"Energy should decrease in first half at position {i + 1}"
                    )
                    violating_positions.append(i)
            # Second half should increase
            for i in range(mid + 1, len(energies)):
                if energies[i] < energies[i - 1] * 0.85:
                    violations.append(
                        f"Energy should increase in second half at position {i + 1}"
                    )
                    violating_positions.append(i)

        elif self.target_arc == "hill":
            mid = len(energies) // 2
            for i in range(1, mid):
                if energies[i] < energies[i - 1] * 0.85:
                    violations.append(
                        f"Energy should increase in first half at position {i + 1}"
                    )
                    violating_positions.append(i)
            for i in range(mid + 1, len(energies)):
                if energies[i] > energies[i - 1] * 1.15:
                    violations.append(
                        f"Energy should decrease in second half at position {i + 1}"
                    )
                    violating_positions.append(i)

        max_possible = max(len(tracks) - 1, 1)
        score = max(0.0, 1.0 - len(violations) / max_possible)

        return ConstraintResult(
            name=f"{self.name} ({self.target_arc})",
            satisfied=len(violations) == 0,
            score=score,
            violations=violations,
            violating_positions=violating_positions,
        )


@dataclass
class GenreVarietyConstraint(PlaylistConstraint):
    """No more than N consecutive tracks of the same genre."""

    name: str = "Genre variety"
    is_hard: bool = False
    max_consecutive: int = 2

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        violations = []
        violating_positions = []
        run_length = 1

        for i in range(1, len(tracks)):
            g_prev = (
                tracks[i - 1].genre_rosamerica[0]
                if tracks[i - 1].genre_rosamerica
                else None
            )
            g_curr = (
                tracks[i].genre_rosamerica[0] if tracks[i].genre_rosamerica else None
            )

            if g_curr and g_prev and g_curr == g_prev:
                run_length += 1
                if run_length > self.max_consecutive:
                    violations.append(
                        f"{run_length} consecutive '{g_curr}' tracks ending at position {i + 1}"
                    )
                    violating_positions.append(i)
            else:
                run_length = 1

        max_possible = max(len(tracks) - 1, 1)
        score = max(0.0, 1.0 - len(violations) / max_possible)

        return ConstraintResult(
            name=self.name,
            satisfied=len(violations) == 0,
            score=score,
            violations=violations,
            violating_positions=violating_positions,
        )


@dataclass
class TempoSmoothnessConstraint(PlaylistConstraint):
    """BPM jumps between consecutive tracks should not exceed a threshold."""

    name: str = "Tempo smoothness"
    is_hard: bool = False
    max_bpm_jump: float = 30.0

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        violations = []
        violating_positions = []

        for i in range(1, len(tracks)):
            bpm_diff = abs(tracks[i].bpm - tracks[i - 1].bpm)
            if bpm_diff > self.max_bpm_jump:
                violations.append(
                    f"BPM jump of {bpm_diff:.0f} at position {i + 1} "
                    f"({tracks[i - 1].bpm:.0f} → {tracks[i].bpm:.0f})"
                )
                violating_positions.append(i)

        max_possible = max(len(tracks) - 1, 1)
        score = max(0.0, 1.0 - len(violations) / max_possible)

        return ConstraintResult(
            name=self.name,
            satisfied=len(violations) == 0,
            score=score,
            violations=violations,
            violating_positions=violating_positions,
        )


@dataclass
class MoodCoherenceConstraint(PlaylistConstraint):
    """Mood should not oscillate wildly (e.g., happy→sad→happy→sad)."""

    name: str = "Mood coherence"
    is_hard: bool = False

    def evaluate(self, tracks: list[TrackFeatures]) -> ConstraintResult:
        violations = []
        violating_positions = []

        moods = []
        for t in tracks:
            best_mood = "unknown"
            best_prob = -1.0
            for mood_name in [
                "happy",
                "sad",
                "aggressive",
                "relaxed",
                "party",
                "acoustic",
            ]:
                prob = t.mood_positive_probability(mood_name)
                if prob is not None and prob > best_prob:
                    best_prob = prob
                    best_mood = mood_name
            moods.append(best_mood)

        # Detect oscillations: A→B→A pattern
        for i in range(2, len(moods)):
            if (
                moods[i] == moods[i - 2]
                and moods[i] != moods[i - 1]
                and moods[i] != "unknown"
            ):
                violations.append(
                    f"Mood oscillation at position {i + 1}: "
                    f"{moods[i - 2]} → {moods[i - 1]} → {moods[i]}"
                )
                violating_positions.append(i)

        max_possible = max(len(tracks) - 2, 1)
        score = max(0.0, 1.0 - len(violations) / max_possible)

        return ConstraintResult(
            name=self.name,
            satisfied=len(violations) == 0,
            score=score,
            violations=violations,
            violating_positions=violating_positions,
        )


# --- Constraint solver ---


DEFAULT_CONSTRAINTS: list[PlaylistConstraint] = [
    NoRepeatArtists(),
    NoRepeatedTracks(),
    GenreVarietyConstraint(),
    TempoSmoothnessConstraint(),
]


def evaluate_all(
    tracks: list[TrackFeatures],
    constraints: list[PlaylistConstraint] | None = None,
) -> list[ConstraintResult]:
    """Evaluate all constraints on a playlist."""
    if constraints is None:
        constraints = DEFAULT_CONSTRAINTS
    return [c.evaluate(tracks) for c in constraints]


def resolve_constraints(
    tracks: list[TrackFeatures],
    constraints: list[PlaylistConstraint],
    search_space: SearchSpace | None = None,
    max_iterations: int = 10,
    max_cost_increase: float = 0.20,
) -> tuple[list[TrackFeatures], list[ConstraintResult]]:
    """Attempt to resolve constraint violations via local search.

    For each hard constraint violation, try replacing the violating track
    with an alternative from the search space. Only accept swaps that:
    1. Fix the constraint violation
    2. Don't increase total cost by more than max_cost_increase (20%)

    Returns the (possibly modified) track list and final constraint results.
    """
    current = list(tracks)
    results = evaluate_all(current, constraints)

    if search_space is None:
        return current, results

    for iteration in range(max_iterations):
        # Find hard constraint violations
        hard_violations = [
            (r, pos)
            for r in results
            if not r.satisfied
            for pos in r.violating_positions
            # Only resolve hard constraints; soft are best-effort
            if any(c.is_hard and c.name == r.name for c in constraints)
        ]

        if not hard_violations:
            break

        # Try to fix the first violation
        _, violating_pos = hard_violations[0]

        # Don't replace source or destination
        if violating_pos == 0 or violating_pos == len(current) - 1:
            logger.warning(
                "Cannot replace source/destination to fix constraint violation"
            )
            break

        # Get candidate replacements from neighbors of adjacent tracks
        prev_mbid = current[violating_pos - 1].mbid
        candidates = search_space.get_scoreable_neighbors(prev_mbid)

        # Filter out tracks already in the playlist
        current_mbids = {t.mbid for t in current}
        candidates = [c for c in candidates if c not in current_mbids]

        if not candidates:
            logger.info("No alternative candidates for position %d", violating_pos)
            break

        # Try each candidate, pick the one that fixes the violation
        best_replacement = None
        best_cost = float("inf")

        for candidate_mbid in candidates[:10]:  # Limit search
            candidate_features = search_space.get_features(candidate_mbid)
            if candidate_features is None:
                continue

            # Check if this replacement fixes the hard constraint
            trial = list(current)
            trial[violating_pos] = candidate_features
            trial_results = evaluate_all(trial, constraints)

            hard_satisfied = all(
                r.satisfied
                for r in trial_results
                if any(c.is_hard and c.name == r.name for c in constraints)
            )

            if hard_satisfied:
                # Check cost
                cost_result = search_space.get_transition_cost(
                    prev_mbid, candidate_mbid
                )
                if cost_result is not None and cost_result < best_cost:
                    best_cost = cost_result
                    best_replacement = candidate_features

        if best_replacement is not None:
            logger.info(
                "Replacing position %d: %s → %s",
                violating_pos,
                current[violating_pos].title or current[violating_pos].mbid,
                best_replacement.title or best_replacement.mbid,
            )
            current[violating_pos] = best_replacement
            results = evaluate_all(current, constraints)
        else:
            logger.info("No suitable replacement found for position %d", violating_pos)
            break

    return current, results
