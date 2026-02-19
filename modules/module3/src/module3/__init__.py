"""Module 3: Playlist Assembly, Essentia Pipeline, User Modeling & Explanation.

This module builds on Modules 1 and 2 to provide:
- Essentia audio analysis as fallback when AcousticBrainz data is missing
- CSP-style playlist constraints (no repeat artists, energy arcs, genre variety)
- User preference learning from feedback
- Human-readable explanations for playlist generation decisions

Example:
    from module3 import PlaylistAssembler

    assembler = PlaylistAssembler()
    playlist = assembler.generate_playlist(source_mbid, dest_mbid, target_length=7)

    if playlist:
        print(playlist.explanation.summary)
        print(playlist.to_static_output())
"""

from .constraints import (
    DEFAULT_CONSTRAINTS,
    EnergyArcConstraint,
    GenreVarietyConstraint,
    MoodCoherenceConstraint,
    NoRepeatArtists,
    NoRepeatedTracks,
    PlaylistConstraint,
    TempoSmoothnessConstraint,
    evaluate_all,
    resolve_constraints,
)
from .data_models import (
    AssembledPlaylist,
    ConstraintResult,
    PlaylistExplanation,
    PlaylistFeedback,
    TrackExplanation,
    TransitionExplanation,
    UserProfile,
)
from .essentia_client import EssentiaClient, EssentiaConfig
from .explainer import (
    detect_energy_arc,
    detect_genre_journey,
    explain_playlist,
    explain_transition,
    generate_playlist_summary,
    get_bottom_contributors,
    get_top_contributors,
)
from .playlist_assembler import PlaylistAssembler
from .user_model import load_profile, save_profile, update_from_feedback

__all__ = [
    # Core assembler
    "PlaylistAssembler",
    # Data models
    "AssembledPlaylist",
    "ConstraintResult",
    "PlaylistExplanation",
    "PlaylistFeedback",
    "TrackExplanation",
    "TransitionExplanation",
    "UserProfile",
    # Constraints
    "PlaylistConstraint",
    "NoRepeatArtists",
    "NoRepeatedTracks",
    "EnergyArcConstraint",
    "GenreVarietyConstraint",
    "TempoSmoothnessConstraint",
    "MoodCoherenceConstraint",
    "DEFAULT_CONSTRAINTS",
    "evaluate_all",
    "resolve_constraints",
    # Essentia
    "EssentiaClient",
    "EssentiaConfig",
    # Explainer
    "explain_playlist",
    "explain_transition",
    "generate_playlist_summary",
    "detect_energy_arc",
    "detect_genre_journey",
    "get_top_contributors",
    "get_bottom_contributors",
    # User model
    "load_profile",
    "save_profile",
    "update_from_feedback",
]
