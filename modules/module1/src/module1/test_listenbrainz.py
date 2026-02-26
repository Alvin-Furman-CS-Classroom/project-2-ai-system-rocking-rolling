"""Tests for ListenBrainz-enhanced compatibility scoring.

Tests tag_compatibility_prob, popularity_compatibility_prob, and the
integration of ListenBrainz signals into the knowledge base heuristic.
"""

from pathlib import Path

from .data_loader import load_track_from_files
from .data_models import UserPreferences
from .knowledge_base import MusicKnowledgeBase
from .listenbrainz_helpers import popularity_compatibility_prob, tag_compatibility_prob


TEST_FILES = Path(__file__).parent.parent.parent / "test_files"


# ---------------------------------------------------------------------------
# Tag compatibility tests
# ---------------------------------------------------------------------------


def test_tag_same_tags_perfect_similarity():
    tags = {"rock": 50, "alternative": 30, "indie": 20}
    assert tag_compatibility_prob(tags, tags) > 0.99


def test_tag_similar_genres_high_similarity():
    tags1 = {"rock": 50, "alternative": 30, "indie": 20}
    tags2 = {"rock": 40, "alternative": 35, "punk": 15}
    prob = tag_compatibility_prob(tags1, tags2)
    assert 0.6 < prob < 1.0, f"Expected moderate-high similarity, got {prob}"


def test_tag_different_genres_low_similarity():
    tags1 = {"rock": 50, "alternative": 30, "indie": 20}
    tags2 = {"classical": 80, "orchestral": 40}
    prob = tag_compatibility_prob(tags1, tags2)
    assert prob < 0.2, f"Expected low similarity for rock vs classical, got {prob}"


def test_tag_missing_data_returns_neutral():
    tags = {"rock": 50}
    assert tag_compatibility_prob(tags, None) == 0.5
    assert tag_compatibility_prob(None, tags) == 0.5
    assert tag_compatibility_prob(None, None) == 0.5


def test_tag_empty_dicts_returns_neutral():
    assert tag_compatibility_prob({}, {"rock": 10}) == 0.5
    assert tag_compatibility_prob({}, {}) == 0.5


def test_tag_single_shared_tag():
    tags1 = {"jazz": 100}
    tags2 = {"jazz": 50, "blues": 30}
    prob = tag_compatibility_prob(tags1, tags2)
    assert prob > 0.7, f"Single shared tag should score high, got {prob}"


# ---------------------------------------------------------------------------
# Popularity compatibility tests
# ---------------------------------------------------------------------------


def test_popularity_same_count():
    assert popularity_compatibility_prob(10000, 10000) > 0.99


def test_popularity_same_tier():
    prob = popularity_compatibility_prob(10000, 12000)
    assert prob > 0.95, f"Same tier should be very compatible, got {prob}"


def test_popularity_10x_difference():
    prob = popularity_compatibility_prob(1000, 10000)
    assert 0.4 < prob < 0.7, f"10x diff should be moderate, got {prob}"


def test_popularity_1000x_difference():
    prob = popularity_compatibility_prob(50, 50000)
    assert prob < 0.05, f"1000x diff should be very low, got {prob}"


def test_popularity_missing_data_returns_neutral():
    assert popularity_compatibility_prob(None, 10000) == 0.5
    assert popularity_compatibility_prob(10000, None) == 0.5
    assert popularity_compatibility_prob(None, None) == 0.5


def test_popularity_zero_listens_returns_neutral():
    assert popularity_compatibility_prob(0, 10000) == 0.5


# ---------------------------------------------------------------------------
# Knowledge base integration tests
# ---------------------------------------------------------------------------


def test_kb_with_listenbrainz_tags():
    """Test that tags flow through to compatibility scoring."""
    kb = MusicKnowledgeBase()
    kb.set_preferences(UserPreferences(tag_weight=0.20, genre_weight=0.0))

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )

    # Enrich with matching tags
    track1.tags = {"rock": 80, "progressive rock": 60, "psychedelic": 40}
    track2.tags = {"rock": 70, "progressive rock": 55, "art rock": 30}

    result = kb.get_compatibility(track1, track2)
    assert result.tag_compatibility > 0.7, (
        f"Similar rock tags should score high, got {result.tag_compatibility}"
    )


def test_kb_tags_vs_no_tags():
    """Without tags, tag_compatible falls back to 0.5 (neutral)."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )

    # No tags set — should fall back to neutral (ProbLog may introduce float noise)
    result = kb.get_compatibility(track1, track2)
    assert abs(result.tag_compatibility - 0.5) < 0.01, (
        f"Missing tags should give ~0.5, got {result.tag_compatibility}"
    )


def test_kb_discovery_mode_suppresses_popularity():
    """In discovery mode, popularity weight should be zero."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )

    # Set wildly different popularity
    track1.popularity_listen_count = 1000000
    track2.popularity_listen_count = 10

    # Without discovery mode, with high popularity weight
    kb.set_preferences(
        UserPreferences(
            popularity_weight=0.30,
            discovery_mode=False,
        )
    )
    result_normal = kb.get_compatibility(track1, track2)

    # With discovery mode
    kb.set_preferences(
        UserPreferences(
            popularity_weight=0.30,
            discovery_mode=True,
        )
    )
    result_discovery = kb.get_compatibility(track1, track2)

    # Discovery mode should ignore the popularity penalty
    assert result_discovery.probability > result_normal.probability, (
        f"Discovery mode ({result_discovery.probability:.3f}) should score higher "
        f"than normal ({result_normal.probability:.3f}) when popularity differs wildly"
    )


def test_kb_weight_normalization():
    """Weights are normalized, so doubling all weights shouldn't change scores."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )

    # Default weights
    kb.set_preferences(UserPreferences())
    result1 = kb.get_compatibility(track1, track2)

    # Doubled weights (should normalize to same result)
    kb.set_preferences(
        UserPreferences(
            key_weight=0.30,
            tempo_weight=0.40,
            energy_weight=0.30,
            loudness_weight=0.10,
            mood_weight=0.30,
            timbre_weight=0.30,
            genre_weight=0.10,
            tag_weight=0.20,
        )
    )
    result2 = kb.get_compatibility(track1, track2)

    assert abs(result1.probability - result2.probability) < 0.01, (
        f"Doubled weights should normalize to same score: "
        f"{result1.probability:.4f} vs {result2.probability:.4f}"
    )


def test_kb_tag_weight_affects_scoring():
    """Increasing tag weight should change the score when tags differ."""
    kb = MusicKnowledgeBase()

    track1 = load_track_from_files(
        TEST_FILES / "pink_floyd_low.json",
        TEST_FILES / "pink_floyd_high.json",
    )
    track2 = load_track_from_files(
        TEST_FILES / "cindy_lauper_low.json",
        TEST_FILES / "cindy_lauper_high.json",
    )

    # Give them very different tags
    track1.tags = {"rock": 80, "progressive": 60}
    track2.tags = {"pop": 90, "dance": 40}

    # Low tag weight
    kb.set_preferences(UserPreferences(tag_weight=0.01))
    result_low = kb.get_compatibility(track1, track2)

    # High tag weight
    kb.set_preferences(UserPreferences(tag_weight=0.40))
    result_high = kb.get_compatibility(track1, track2)

    # With very different tags, higher tag weight should lower the score
    assert result_high.probability < result_low.probability, (
        f"Higher tag weight with different tags should lower score: "
        f"low_w={result_low.probability:.3f}, high_w={result_high.probability:.3f}"
    )
