"""User preference learning from playlist feedback.

Implements online learning of dimension weights using exponential moving
average. When a user rates a transition, the system adjusts the 12
dimension weights based on agreement between the user's rating and
each dimension's score.

Persistence: UserProfile is saved as JSON to ~/.waveguide/user_profile.json.
Cold start: defaults to Module 1's default weights.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from module1 import TransitionResult

from .data_models import PlaylistFeedback, UserProfile

logger = logging.getLogger(__name__)

DIMENSION_NAMES = [
    "key", "tempo", "energy", "loudness", "mood", "timbre",
    "genre", "tag", "popularity", "artist", "era", "mb_genre",
]

DEFAULT_PROFILE_PATH = Path("~/.waveguide/user_profile.json").expanduser()


def load_profile(path: Path | None = None) -> UserProfile:
    """Load user profile from disk, or return default profile."""
    path = path or DEFAULT_PROFILE_PATH
    if not path.exists():
        return UserProfile()

    try:
        with open(path) as f:
            data = json.load(f)

        return UserProfile(
            dimension_weights=data.get("dimension_weights", UserProfile().dimension_weights),
            preferred_genres=data.get("preferred_genres", {}),
            preferred_energy_arc=data.get("preferred_energy_arc", "flat"),
            feedback_history=[
                PlaylistFeedback(
                    playlist_id=fb["playlist_id"],
                    overall_rating=fb["overall_rating"],
                    transition_ratings=fb.get("transition_ratings", {}),
                    liked_tracks=fb.get("liked_tracks", []),
                    disliked_tracks=fb.get("disliked_tracks", []),
                )
                for fb in data.get("feedback_history", [])
            ],
        )
    except Exception:
        logger.warning("Failed to load user profile from %s, using defaults", path)
        return UserProfile()


def save_profile(profile: UserProfile, path: Path | None = None) -> None:
    """Save user profile to disk."""
    path = path or DEFAULT_PROFILE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "dimension_weights": profile.dimension_weights,
        "preferred_genres": profile.preferred_genres,
        "preferred_energy_arc": profile.preferred_energy_arc,
        "feedback_history": [
            {
                "playlist_id": fb.playlist_id,
                "overall_rating": fb.overall_rating,
                "transition_ratings": fb.transition_ratings,
                "liked_tracks": fb.liked_tracks,
                "disliked_tracks": fb.disliked_tracks,
            }
            for fb in profile.feedback_history
        ],
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def update_weights_from_transition(
    profile: UserProfile,
    transition: TransitionResult,
    rating: float,
    learning_rate: float = 0.1,
) -> None:
    """Update dimension weights based on a single transition rating.

    The learning rule:
    - Compute agreement = 1 - |normalized_rating - dim_score|
    - Blend: new_weight = old_weight * (1 - lr) + agreement * lr

    High agreement (user liked it AND dim scored high, or user disliked it
    AND dim scored low) reinforces the weight. Low agreement (user disliked
    but dim scored high) reduces the weight.

    Args:
        profile: User profile to update (mutated in place)
        transition: The transition result with 12-dimension scores
        rating: User rating 1-5
        learning_rate: How fast to adapt (0.1 = conservative)
    """
    normalized_rating = (rating - 1.0) / 4.0  # Map 1-5 to 0-1

    for dim in DIMENSION_NAMES:
        score = getattr(transition, f"{dim}_compatibility", 0.5)
        agreement = 1.0 - abs(normalized_rating - score)

        current = profile.dimension_weights.get(dim, 0.1)
        new_weight = current * (1 - learning_rate) + agreement * learning_rate
        # Clamp to reasonable range
        profile.dimension_weights[dim] = max(0.0, min(1.0, new_weight))


def update_from_feedback(
    profile: UserProfile,
    feedback: PlaylistFeedback,
    transitions: list[TransitionResult],
    learning_rate: float = 0.1,
) -> None:
    """Update profile from complete playlist feedback.

    Processes transition-level ratings if available, otherwise uses
    the overall rating for all transitions.

    Args:
        profile: User profile to update
        feedback: Playlist feedback from user
        transitions: TransitionResult list from the rated playlist
        learning_rate: Adaptation speed
    """
    for i, transition in enumerate(transitions):
        # Use per-transition rating if available, else overall
        rating = feedback.transition_ratings.get(i, feedback.overall_rating)
        update_weights_from_transition(profile, transition, rating, learning_rate)

    # Store feedback in history
    profile.feedback_history.append(feedback)

    # Cap history to last 100 entries
    if len(profile.feedback_history) > 100:
        profile.feedback_history = profile.feedback_history[-100:]
