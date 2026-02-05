"""Module 1: Music Feature Knowledge Base - Demo.

This module demonstrates the clean Python API for the music knowledge base.
"""

from dataclasses import replace
from pathlib import Path

from .data_loader import load_track_from_files
from .data_models import UserPreferences
from .knowledge_base import MusicKnowledgeBase


def main() -> int:
    """Run the Module 1 demonstration."""
    print("=" * 60)
    print("Module 1: Music Feature Knowledge Base")
    print("=" * 60)

    # Initialize knowledge base
    print("\nInitializing Music Knowledge Base...")
    kb = MusicKnowledgeBase()

    # Load sample track from test files
    test_files_dir = Path(__file__).parent.parent.parent / "test_files"
    lowlevel_path = test_files_dir / "sample_lowlevel.json"
    highlevel_path = test_files_dir / "sample_highlevel.json"

    print("\nLoading track from:")
    print(f"  Lowlevel:  {lowlevel_path.name}")
    print(f"  Highlevel: {highlevel_path.name}")

    track1 = load_track_from_files(lowlevel_path, highlevel_path)

    print(f"\nTrack 1: {track1.artist} - {track1.title}")
    print(f"  MBID: {track1.mbid}")
    print(f"  Key: {track1.key} {track1.scale} (strength: {track1.key_strength:.2f})")
    print(f"  BPM: {track1.bpm:.1f}")
    print(f"  Energy: {track1.energy_score:.3f}")
    print(f"  Danceability: {track1.danceability_score:.2f}")

    # Show mood classification
    print("\n  Mood classifications:")
    if track1.mood_happy:
        print(f"    Happy: {track1.mood_happy[0]} ({track1.mood_happy[1]:.1%})")
    if track1.mood_sad:
        print(f"    Sad: {track1.mood_sad[0]} ({track1.mood_sad[1]:.1%})")
    if track1.mood_relaxed:
        print(f"    Relaxed: {track1.mood_relaxed[0]} ({track1.mood_relaxed[1]:.1%})")
    if track1.mood_aggressive:
        print(
            f"    Aggressive: {track1.mood_aggressive[0]} ({track1.mood_aggressive[1]:.1%})"
        )

    # Create a hypothetical second track by modifying the first
    print("\n" + "-" * 60)
    print("Creating hypothetical Track 2 (modified version)...")
    track2 = replace(track1, key="D", scale="major", bpm=152.0)

    print("\nTrack 2: (modified version)")
    print(f"  Key: {track2.key} {track2.scale}")
    print(f"  BPM: {track2.bpm:.1f}")
    print(f"  Energy: {track2.energy_score:.3f}")

    # Query compatibility
    print("\n" + "=" * 60)
    print("QUERYING TRACK COMPATIBILITY")
    print("=" * 60)

    result = kb.get_compatibility(track1, track2)

    print("\nOverall Results:")
    print(f"  Compatibility: {result.probability:.1%}")
    print(f"  A* search cost: {result.penalty:.3f}")
    print(f"  Is compatible: {result.is_compatible}")

    print("\nComponent Scores:")
    components = [
        ("Key", result.key_compatibility),
        ("Tempo", result.tempo_compatibility),
        ("Energy", result.energy_compatibility),
        ("Loudness", result.loudness_compatibility),
        ("Mood", result.mood_compatibility),
        ("Timbre", result.timbre_compatibility),
    ]
    for name, score in components:
        status = "OK" if score > 0.5 else "LOW" if score > 0.3 else "BAD"
        print(f"  {name:12s}: {score:.1%} [{status}]")

    if result.violations:
        print("\nViolations:")
        for v in result.violations:
            print(f"  - {v}")

    print("\nExplanation:")
    for line in result.explanation.split("\n"):
        print(f"  {line}")

    # Demonstrate user preferences
    print("\n" + "=" * 60)
    print("WITH USER PREFERENCES")
    print("=" * 60)

    kb.set_preferences(
        UserPreferences(
            prefer_consistent_tempo=True,
            target_moods=["relaxed", "sad"],
        )
    )

    result_with_prefs = kb.get_compatibility(track1, track2)
    print("\nWith preferences (prefer relaxed/sad mood, consistent tempo):")
    print(f"  Compatibility: {result_with_prefs.probability:.1%}")
    print(f"  A* cost: {result_with_prefs.penalty:.3f}")

    # Demonstrate playlist validation
    print("\n" + "=" * 60)
    print("PLAYLIST VALIDATION")
    print("=" * 60)

    # Create a 3-track playlist
    track3 = replace(track1, key="E", scale="minor", bpm=145.0)
    playlist = [track1, track2, track3]

    print(f"\nPlaylist: {len(playlist)} tracks")
    for i, t in enumerate(playlist):
        print(f"  {i + 1}. Key: {t.key} {t.scale}, BPM: {t.bpm:.0f}")

    # Reset preferences for clean validation
    kb.set_preferences(UserPreferences())
    validation = kb.validate_playlist(playlist)

    print("\nValidation Results:")
    print(f"  Overall probability: {validation.overall_probability:.1%}")
    print(f"  Overall penalty: {validation.overall_penalty:.3f}")
    print(f"  Is valid: {validation.is_valid}")
    print(f"  Total violations: {validation.total_violations}")

    if validation.weakest_transition:
        idx, prob = validation.weakest_transition
        print(f"  Weakest transition: {idx + 1}->{idx + 2} (P={prob:.1%})")

    print("\nPer-transition scores:")
    for i, trans in enumerate(validation.transitions):
        status = "OK" if trans.is_compatible else "WARN"
        print(
            f"  {i + 1}->{i + 2}: P={trans.probability:.1%}, cost={trans.penalty:.3f} [{status}]"
        )

    # Module 2 integration demo
    print("\n" + "=" * 60)
    print("MODULE 2 INTEGRATION (A* SEARCH)")
    print("=" * 60)

    print("\nFor A* search, use kb.get_penalty(track1, track2):")
    cost = kb.get_penalty(track1, track2)
    print(f"  cost = {cost:.4f}")
    print("\nThis penalty guides the search toward smooth transitions.")
    print("Lower cost = better transition = higher probability of smooth playback.")

    print("\n" + "=" * 60)
    print("Demo complete! ProbLog inference is hidden behind the clean Python API.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
