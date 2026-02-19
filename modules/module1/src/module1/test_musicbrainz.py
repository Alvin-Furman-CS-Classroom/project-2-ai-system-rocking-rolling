"""Tests for MusicBrainz-enhanced compatibility scoring.

Tests artist_compatibility_prob, era_compatibility_prob,
mb_genre_compatibility_prob, and their integration into the knowledge base.
"""

from pathlib import Path

from .data_loader import load_track_from_files
from .data_models import UserPreferences
from .knowledge_base import MusicKnowledgeBase
from .musicbrainz_helpers import (
    artist_compatibility_prob,
    era_compatibility_prob,
    mb_genre_compatibility_prob,
)


TEST_FILES = Path(__file__).parent.parent.parent / "test_files"


# ---------------------------------------------------------------------------
# Artist compatibility tests
# ---------------------------------------------------------------------------


def test_artist_same_artist():
    mbid = "some-artist-mbid-1234"
    assert artist_compatibility_prob(mbid, mbid) == 0.95


def test_artist_related_via_first():
    mbid1 = "artist-a"
    mbid2 = "artist-b"
    related1 = {"artist-b", "artist-c"}
    prob = artist_compatibility_prob(mbid1, mbid2, related1=related1)
    assert prob == 0.70


def test_artist_related_via_second():
    mbid1 = "artist-a"
    mbid2 = "artist-b"
    related2 = {"artist-a", "artist-d"}
    prob = artist_compatibility_prob(mbid1, mbid2, related2=related2)
    assert prob == 0.70


def test_artist_no_relationship():
    prob = artist_compatibility_prob("artist-a", "artist-b")
    assert prob == 0.50


def test_artist_missing_data_returns_neutral():
    assert artist_compatibility_prob(None, "artist-b") == 0.5
    assert artist_compatibility_prob("artist-a", None) == 0.5
    assert artist_compatibility_prob(None, None) == 0.5


# ---------------------------------------------------------------------------
# Era compatibility tests
# ---------------------------------------------------------------------------


def test_era_same_year():
    assert era_compatibility_prob(2020, 2020) > 0.99


def test_era_3_years_apart():
    prob = era_compatibility_prob(2020, 2023)
    assert 0.75 < prob < 0.90, f"3 years apart should be ~83%, got {prob:.1%}"


def test_era_5_years_apart():
    prob = era_compatibility_prob(2015, 2020)
    assert 0.50 < prob < 0.70, f"5 years apart should be ~61%, got {prob:.1%}"


def test_era_10_years_apart():
    prob = era_compatibility_prob(2010, 2020)
    assert 0.05 < prob < 0.25, f"10 years apart should be ~14%, got {prob:.1%}"


def test_era_20_years_apart():
    prob = era_compatibility_prob(2000, 2020)
    assert prob < 0.02, f"20 years apart should be <1%, got {prob:.1%}"


def test_era_missing_data_returns_neutral():
    assert era_compatibility_prob(None, 2020) == 0.5
    assert era_compatibility_prob(2020, None) == 0.5
    assert era_compatibility_prob(None, None) == 0.5


# ---------------------------------------------------------------------------
# MusicBrainz genre compatibility tests
# ---------------------------------------------------------------------------


def test_mb_genre_identical_genres():
    genres = ["rock", "alternative", "indie"]
    prob = mb_genre_compatibility_prob(genres, genres)
    assert prob == 1.0


def test_mb_genre_partial_overlap():
    genres1 = ["rock", "alternative", "indie"]
    genres2 = ["rock", "punk", "indie"]
    prob = mb_genre_compatibility_prob(genres1, genres2)
    # Jaccard: {rock, indie} / {rock, alternative, indie, punk} = 2/4 = 0.5
    assert abs(prob - 0.5) < 0.01, f"Expected ~0.5, got {prob}"


def test_mb_genre_no_overlap():
    genres1 = ["rock", "metal"]
    genres2 = ["classical", "orchestral"]
    prob = mb_genre_compatibility_prob(genres1, genres2)
    assert prob == 0.0


def test_mb_genre_case_insensitive():
    genres1 = ["Rock", "ALTERNATIVE"]
    genres2 = ["rock", "alternative"]
    prob = mb_genre_compatibility_prob(genres1, genres2)
    assert prob == 1.0


def test_mb_genre_missing_data_returns_neutral():
    assert mb_genre_compatibility_prob(None, ["rock"]) == 0.5
    assert mb_genre_compatibility_prob(["rock"], None) == 0.5
    assert mb_genre_compatibility_prob(None, None) == 0.5


def test_mb_genre_empty_lists_returns_neutral():
    assert mb_genre_compatibility_prob([], ["rock"]) == 0.5
    assert mb_genre_compatibility_prob([], []) == 0.5


# ---------------------------------------------------------------------------
# Knowledge base integration tests
# ---------------------------------------------------------------------------


def test_kb_artist_same_artist_boosts_score():
    """Same artist should increase overall compatibility."""
    kb = MusicKnowledgeBase()
    kb.set_preferences(UserPreferences(artist_weight=0.20))

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )

    # Same artist MBID
    track1.artist_mbid = "83d91898-7763-47d7-b03b-faaee372db95"
    track2.artist_mbid = "83d91898-7763-47d7-b03b-faaee372db95"

    result = kb.get_compatibility(track1, track2)
    assert abs(result.artist_compatibility - 0.95) < 0.01, (
        f"Same artist should give ~0.95, got {result.artist_compatibility}"
    )


def test_kb_era_same_decade():
    """Tracks from the same era should score high on era dimension."""
    kb = MusicKnowledgeBase()
    kb.set_preferences(UserPreferences(era_weight=0.10))

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )

    track1.mb_release_year = 1979
    track2.mb_release_year = 1983

    result = kb.get_compatibility(track1, track2)
    assert result.era_compatibility > 0.70, (
        f"4 years apart should score high, got {result.era_compatibility}"
    )


def test_kb_no_mb_data_neutral_fallback():
    """Without MusicBrainz data, new dimensions should fall back to 0.5."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )

    result = kb.get_compatibility(track1, track2)
    assert abs(result.artist_compatibility - 0.5) < 0.01, (
        f"No artist data should give ~0.5, got {result.artist_compatibility}"
    )
    assert abs(result.era_compatibility - 0.5) < 0.01, (
        f"No era data should give ~0.5, got {result.era_compatibility}"
    )
    assert abs(result.mb_genre_compatibility - 0.5) < 0.01, (
        f"No MB genre data should give ~0.5, got {result.mb_genre_compatibility}"
    )


def test_kb_artist_weight_affects_scoring():
    """Higher artist weight with different artists should change score."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )

    # Different artists
    track1.artist_mbid = "artist-1"
    track2.artist_mbid = "artist-2"

    # Low artist weight
    kb.set_preferences(UserPreferences(artist_weight=0.01))
    result_low = kb.get_compatibility(track1, track2)

    # High artist weight — unrelated artists score 0.5 (neutral),
    # so this shifts the overall score toward 0.5
    kb.set_preferences(UserPreferences(artist_weight=0.40))
    result_high = kb.get_compatibility(track1, track2)

    # Scores should differ when weight changes
    assert abs(result_low.probability - result_high.probability) > 0.001, (
        f"Artist weight should affect score: "
        f"low_w={result_low.probability:.4f}, high_w={result_high.probability:.4f}"
    )
