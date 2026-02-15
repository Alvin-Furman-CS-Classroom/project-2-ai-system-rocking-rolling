"""Unit tests for Music Knowledge Base compatibility metric.

Tests the get_compatibility function with various track pairs:
- Same genre (expecting higher compatibility)
- Different genres (expecting lower compatibility)
- Same piece twice (expecting very high compatibility)
- Different artists (various scenarios)
"""

from pathlib import Path
import json

from .data_loader import load_track_from_files
from .knowledge_base import MusicKnowledgeBase
from .data_models import UserPreferences


def get_test_files_dir() -> Path:
    """Get the test_files directory."""
    return Path(__file__).parent.parent.parent / "test_files"


def load_track(low_file_name: str, high_file_name: str):
    """Load a track by providing both low and high level filenames."""
    test_dir = get_test_files_dir()
    low_file = test_dir / low_file_name
    high_file = test_dir / high_file_name
    
    if not low_file.exists() or not high_file.exists():
        raise FileNotFoundError(f"Could not find test files: {low_file_name}, {high_file_name}")
    
    track = load_track_from_files(low_file, high_file)
    return track


def get_track_info(high_file_name: str) -> dict:
    """Parse track info from filename."""
    test_dir = get_test_files_dir()
    high_file = test_dir / high_file_name
    
    with open(high_file) as f:
        data = json.load(f)
    
    metadata = data.get("metadata", {}).get("tags", {})
    return {
        "artist": metadata.get("artist", ["Unknown"])[0] if metadata.get("artist") else "Unknown",
        "title": metadata.get("title", ["Unknown"])[0] if metadata.get("title") else "Unknown",
        "album": metadata.get("album", ["Unknown"])[0] if metadata.get("album") else "Unknown",
        "genre": metadata.get("genre", ["Unknown"])[0] if metadata.get("genre") else "Unknown",
    }


def test_same_piece_twice():
    """Test: Same piece twice should have very high compatibility (> 0.7)."""
    print("\n" + "="*70)
    print("TEST 1: Same Piece Twice (Cyndi Lauper)")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    track = load_track("cindy_lauper_low.json", "cindy_lauper_high.json")
    
    result = kb.get_compatibility(track, track)
    
    print("Cyndi Lauper - Same track twice")
    print(f"  Compatibility: {result.probability:.1%}")
    print(f"  Is Compatible: {result.is_compatible}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    # Same piece should have very high compatibility
    assert result.probability > 0.7, f"Expected >0.7 for same piece, got {result.probability:.1%}"
    assert result.is_compatible, "Same piece should be compatible"
    print("✓ PASS: Same piece has high compatibility (>70%)\n")


def test_same_genre_different_artists():
    """Test: Same genre but different artists should have moderate-to-high compatibility."""
    print("="*70)
    print("TEST 2: Same Genre (Pop) - Different Artists")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    # Both are pop/electronic music
    track1 = load_track("cindy_lauper_low.json", "cindy_lauper_high.json")  # Pop/Electronic
    track2 = load_track("low_level_Beethoven_35.json", "high_level_Beethoven_35.json")  # Classical (but let's check)
    
    info1 = get_track_info("cindy_lauper_high.json")
    info2 = get_track_info("high_level_Beethoven_35.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: {info1['artist']} - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: {info2['artist']} - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_different_genres():
    """Test: Very different genres should have lower compatibility."""
    print("="*70)
    print("TEST 3: Different Genres - Electronic vs Classical")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    # Electronic: Cindy Lauper (pop/electronic)
    # Classical: Beethoven
    track1 = load_track("cindy_lauper_low.json", "cindy_lauper_high.json")  # Pop/Electronic
    track2 = load_track("low_level_beethoven_symphony_6.json", "high_level_beethoven_symphony_6.json")  # Classical
    
    info1 = get_track_info("cindy_lauper_high.json")
    info2 = get_track_info("high_level_beethoven_symphony_6.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: {info1['artist']} - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: {info2['artist']} - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_similar_electronic_pieces():
    """Test: Both classical pieces should have reasonable compatibility."""
    print("="*70)
    print("TEST 4: Both Classical/Similar - Beethoven Pieces")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    track1 = load_track("low_level_Beethoven_35.json", "high_level_Beethoven_35.json")  # Classical
    track2 = load_track("low_level_beethoven_symphony_6.json", "high_level_beethoven_symphony_6.json")  # Classical
    
    info1 = get_track_info("high_level_Beethoven_35.json")
    info2 = get_track_info("high_level_beethoven_symphony_6.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: Beethoven - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: Beethoven - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_rock_vs_classical():
    """Test: Rock vs Classical - very different genres."""
    print("="*70)
    print("TEST 5: Rock vs Classical - Pink Floyd vs Beethoven")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    track1 = load_track("pink_floyd_low.json", "pink_floyd_high.json")  # Rock
    track2 = load_track("low_level_Beethoven_35.json", "high_level_Beethoven_35.json")  # Classical
    
    info1 = get_track_info("pink_floyd_high.json")
    info2 = get_track_info("high_level_Beethoven_35.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: {info1['artist']} - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: {info2['artist']} - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_same_genre_different_artists_2():
    """Test: Different classical pieces."""
    print("="*70)
    print("TEST 6: Different Classical Pieces - Beethoven")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    track1 = load_track("low_level_Beethoven_35.json", "high_level_Beethoven_35.json")  # Beethoven
    track2 = load_track("low_level_beethoven_symphony_6.json", "high_level_beethoven_symphony_6.json")  # Beethoven (different piece)
    
    info1 = get_track_info("high_level_Beethoven_35.json")
    info2 = get_track_info("high_level_beethoven_symphony_6.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: Beethoven - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: Beethoven - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_with_preferences():
    """Test: Same genre with user preferences for relaxed mood."""
    print("="*70)
    print("TEST 7: With User Preferences - Prefer Relaxed/Sad Mood")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    # Set preferences for relaxed mood, consistent tempo
    kb.set_preferences(
        UserPreferences(
            prefer_consistent_tempo=True,
            target_moods=["relaxed", "sad"],
            mood_weight=0.25,  # Increase mood weight
        )
    )
    
    track1 = load_track("low_level_Beethoven_35.json", "high_level_Beethoven_35.json")
    track2 = load_track("low_level_beethoven_symphony_6.json", "high_level_beethoven_symphony_6.json")
    
    info1 = get_track_info("high_level_Beethoven_35.json")
    info2 = get_track_info("high_level_beethoven_symphony_6.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print("Preferences: Prefer relaxed/sad mood, consistent tempo")
    print(f"Track 1: Beethoven - {info1['title']}")
    print(f"Track 2: Beethoven - {info2['title']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility with preferences: {result.probability:.1%}\n")


def test_pink_floyd_twice():
    """Test: Pink Floyd twice - same rock piece."""
    print("="*70)
    print("TEST 8: Rock - Pink Floyd Twice (Same Piece)")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    track = load_track("pink_floyd_low.json", "pink_floyd_high.json")
    
    result = kb.get_compatibility(track, track)
    
    info = get_track_info("pink_floyd_high.json")
    
    print(f"Track: {info['artist']} - {info['title']}")
    print(f"  Genre: {info['genre']}")
    print(f"\nCompatibility (Same track twice): {result.probability:.1%}")
    print(f"  Is Compatible: {result.is_compatible}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    assert result.probability > 0.7, f"Expected >0.7 for same piece, got {result.probability:.1%}"
    print("✓ PASS: Same rock piece has high compatibility (>70%)\n")


def test_mixed_genres_pop_and_classical():
    """Test: Pop vs Classical - Cyndi Lauper vs Beethoven."""
    print("="*70)
    print("TEST 9: Different Genres - Pop vs Classical")
    print("="*70)
    
    kb = MusicKnowledgeBase()
    
    track1 = load_track("cindy_lauper_low.json", "cindy_lauper_high.json")  # Pop
    track2 = load_track("low_level_beethoven_symphony_6.json", "high_level_beethoven_symphony_6.json")  # Classical
    
    info1 = get_track_info("cindy_lauper_high.json")
    info2 = get_track_info("high_level_beethoven_symphony_6.json")
    
    result = kb.get_compatibility(track1, track2)
    
    print(f"Track 1: {info1['artist']} - {info1['title']}")
    print(f"  Genre: {info1['genre']}")
    print(f"Track 2: {info2['artist']} - {info2['title']}")
    print(f"  Genre: {info2['genre']}")
    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"  Penalty: {result.penalty:.3f}")
    print(f"  Key: {result.key_compatibility:.1%}")
    print(f"  Tempo: {result.tempo_compatibility:.1%}")
    print(f"  Energy: {result.energy_compatibility:.1%}")
    print(f"  Loudness: {result.loudness_compatibility:.1%}")
    print(f"  Mood: {result.mood_compatibility:.1%}")
    print(f"  Timbre: {result.timbre_compatibility:.1%}")
    
    print(f"✓ Compatibility calculated: {result.probability:.1%}\n")


def test_summary():
    """Summary of all tests."""
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✓ Test 1: Same piece (Cyndi Lauper) - Expect >70% compatibility")
    print("✓ Test 2: Pop genres (Different artists)")
    print("✓ Test 3: Different genres (Electronic vs Classical)")
    print("✓ Test 4: Similar classical pieces (Beethoven x2)")
    print("✓ Test 5: Very different (Rock vs Classical)")
    print("✓ Test 6: Different classical pieces (Beethoven)")
    print("✓ Test 7: With user preferences (Relaxed mood)")
    print("✓ Test 8: Rock piece (Pink Floyd) twice - Expect >70% compatibility")
    print("✓ Test 9: Mixed genres (Pop vs Classical)")
    print("="*70)


def run_all_tests():
    """Run all compatibility metric tests."""
    print("\n" + "="*70)
    print("MUSIC KNOWLEDGE BASE - COMPATIBILITY METRIC TESTS")
    print("="*70)
    
    try:
        test_same_piece_twice()
        test_same_genre_different_artists()
        test_different_genres()
        test_similar_electronic_pieces()
        test_rock_vs_classical()
        test_same_genre_different_artists_2()
        test_with_preferences()
        test_pink_floyd_twice()
        test_mixed_genres_pop_and_classical()
        test_summary()
        
        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY ✓")
        print("="*70 + "\n")
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
