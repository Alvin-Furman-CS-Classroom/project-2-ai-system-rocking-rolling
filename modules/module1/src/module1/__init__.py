"""Module 1: Music Feature Knowledge Base.

This module provides a probabilistic knowledge base for music theory rules
using ProbLog. It enables:

- Loading track features from AcousticBrainz JSON data
- Computing transition compatibility between tracks
- Validating complete playlists
- Setting user preferences for compatibility scoring

Example:
    from modules.module1 import MusicKnowledgeBase, load_track_from_files

    kb = MusicKnowledgeBase()
    track1 = load_track_from_files("track1_low.json", "track1_high.json")
    track2 = load_track_from_files("track2_low.json", "track2_high.json")

    result = kb.get_compatibility(track1, track2)
    print(f"Compatibility: {result.probability:.1%}")
"""

from .data_loader import load_track_from_files, load_tracks_batch
from .data_models import (
    PlaylistValidation,
    TrackFeatures,
    TransitionResult,
    UserPreferences,
)
from .knowledge_base import MusicKnowledgeBase
from .main import main

__all__ = [
    # Main class
    "MusicKnowledgeBase",
    # Data models
    "TrackFeatures",
    "UserPreferences",
    "TransitionResult",
    "PlaylistValidation",
    # Data loading
    "load_track_from_files",
    "load_tracks_batch",
    # Entry point
    "main",
]
