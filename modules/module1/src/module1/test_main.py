from pathlib import Path

from .data_loader import load_track_from_files, load_track_from_lowlevel
from .data_models import TrackFeatures, TransitionResult
from .knowledge_base import MusicKnowledgeBase
from .main import main


TEST_FILES = Path(__file__).parent.parent.parent / "test_files"


def _print_result(track_a: TrackFeatures, track_b: TrackFeatures, result: TransitionResult):
    """Print compatibility result between two tracks."""
    print(f"\n{'=' * 60}")
    print(f"Track 1: {track_a.artist} - {track_a.title}")
    print(f"Track 2: {track_b.artist} - {track_b.title}")
    print(f"{'=' * 60}")
    print(f"Overall compatibility: {result.probability:.1%}")
    print(f"A* penalty:           {result.penalty:.3f}")
    print(f"Is compatible:        {result.is_compatible}")
    print(f"\nComponent scores:")
    for name, score in [
        ("Key", result.key_compatibility),
        ("Tempo", result.tempo_compatibility),
        ("Energy", result.energy_compatibility),
        ("Loudness", result.loudness_compatibility),
        ("Mood", result.mood_compatibility),
        ("Timbre", result.timbre_compatibility),
        ("Genre", result.genre_compatibility),
    ]:
        print(f"  {name:12s}: {score:.1%}")
    if result.violations:
        print(f"\nViolations:")
        for v in result.violations:
            print(f"  - {v}")
    print(f"\nExplanation:\n{result.explanation}")


def test_main():
    assert main() == 0


def test_cindy_lauper_vs_pink_floyd():
    """Compare Cindy Lauper and Pink Floyd tracks and print compatibility scores."""
    kb = MusicKnowledgeBase()

    cindy = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )
    floyd = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )

    result = kb.get_compatibility(cindy, floyd)
    _print_result(cindy, floyd, result)

    assert result.probability >= 0.0
    assert result.probability <= 1.0


def test_cindy_lauper_vs_beethoven():
    """Compare Cindy Lauper against both Beethoven tracks and print compatibility scores."""
    kb = MusicKnowledgeBase()

    cindy = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )
    beethoven_35 = load_track_from_files(
        TEST_FILES / "low_level_Beethoven_35.json",
        TEST_FILES / "high_level_Beethoven_35.json",
    )
    beethoven_sym6 = load_track_from_files(
        TEST_FILES / "low_level_beethoven_symphony_6.json",
        TEST_FILES / "high_level_beethoven_symphony_6.json",
    )

    result_35 = kb.get_compatibility(cindy, beethoven_35)
    _print_result(cindy, beethoven_35, result_35)

    result_sym6 = kb.get_compatibility(cindy, beethoven_sym6)
    _print_result(cindy, beethoven_sym6, result_sym6)

    assert result_35.probability >= 0.0
    assert result_35.probability <= 1.0
    assert result_sym6.probability >= 0.0
    assert result_sym6.probability <= 1.0


def test_beethoven_vs_beethoven():
    """Compare the two Beethoven tracks against each other."""
    kb = MusicKnowledgeBase()

    beethoven_35 = load_track_from_files(
        TEST_FILES / "low_level_Beethoven_35.json",
        TEST_FILES / "high_level_Beethoven_35.json",
    )
    beethoven_sym6 = load_track_from_files(
        TEST_FILES / "low_level_beethoven_symphony_6.json",
        TEST_FILES / "high_level_beethoven_symphony_6.json",
    )

    result = kb.get_compatibility(beethoven_35, beethoven_sym6)
    _print_result(beethoven_35, beethoven_sym6, result)

    assert result.probability >= 0.0
    assert result.probability <= 1.0


def test_beethoven_lowlevel_only():
    """Compare Beethoven Op. 35 vs Beethoven 2 using low-level data only."""
    kb = MusicKnowledgeBase()

    beethoven_35 = load_track_from_lowlevel(
        TEST_FILES / "low_level_Beethoven_35.json",
    )
    beethoven_2 = load_track_from_lowlevel(
        TEST_FILES / "low_level_Beethoven_2.json",
    )

    result = kb.get_compatibility(beethoven_35, beethoven_2)
    _print_result(beethoven_35, beethoven_2, result)

    assert result.probability >= 0.0
    assert result.probability <= 1.0


def test_symphony_35_vs_itself():
    """Compare Symphony No. 35 in D major against itself."""
    kb = MusicKnowledgeBase()

    track = load_track_from_lowlevel(
        TEST_FILES / "low_level_Beethoven_35.json",
    )

    result = kb.get_compatibility(track, track)
    _print_result(track, track, result)

    assert result.probability >= 0.0
    assert result.probability <= 1.0
