"""Module 1: Music Feature Knowledge Base - Demo.

This module demonstrates the clean Python API for the music knowledge base.
"""

from pathlib import Path

from .data_loader import load_track_from_files
from .data_models import UserPreferences
from .knowledge_base import MusicKnowledgeBase


def _print_track_info(track, label):
    """Print detailed info for a track."""
    print(f"\n{label}: {track.artist} - {track.title}")
    print(f"  MBID: {track.mbid}")
    print(f"  Key: {track.key} {track.scale} (strength: {track.key_strength:.2f})")
    print(f"  BPM: {track.bpm:.1f}")
    print(f"  Energy: {track.energy_score:.3f}")
    print(f"  Danceability: {track.danceability_score:.2f}")

    print("\n  Mood classifications:")
    if track.mood_happy:
        print(f"    Happy: {track.mood_happy[0]} ({track.mood_happy[1]:.1%})")
    if track.mood_sad:
        print(f"    Sad: {track.mood_sad[0]} ({track.mood_sad[1]:.1%})")
    if track.mood_relaxed:
        print(f"    Relaxed: {track.mood_relaxed[0]} ({track.mood_relaxed[1]:.1%})")
    if track.mood_aggressive:
        print(
            f"    Aggressive: {track.mood_aggressive[0]} ({track.mood_aggressive[1]:.1%})"
        )


def main() -> int:
    """Run the Module 1 demonstration."""
    print("=" * 60)
    print("Module 1: Music Feature Knowledge Base")
    print("=" * 60)

    # Initialize knowledge base
    print("\nInitializing Music Knowledge Base...")
    kb = MusicKnowledgeBase()

    # Load tracks from test files
    test_files_dir = Path(__file__).parent.parent.parent / "test_files"

    print("\nLoading tracks...")
    track1 = load_track_from_files(
        test_files_dir / "cindy_lauper_low.json",
        test_files_dir / "cindy_lauper_high.json",
    )
    track2 = load_track_from_files(
        test_files_dir / "pink_floyd_low.json",
        test_files_dir / "pink_floyd_high.json",
    )

    _print_track_info(track1, "Track 1")
    _print_track_info(track2, "Track 2")

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

    # Validate the 2-track playlist (both directions)
    playlist = [track1, track2]

    print(f"\nPlaylist: {len(playlist)} tracks")
    for i, t in enumerate(playlist):
        print(f"  {i + 1}. {t.artist} - {t.title} (Key: {t.key} {t.scale}, BPM: {t.bpm:.0f})")

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
