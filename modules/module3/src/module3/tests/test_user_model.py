"""Tests for Module 3 user modeling."""

import json
import tempfile
import unittest
from pathlib import Path

from module1 import TransitionResult, UserPreferences

from module3.data_models import PlaylistFeedback, UserProfile
from module3.user_model import (
    load_profile,
    save_profile,
    update_from_feedback,
    update_weights_from_transition,
)


def _make_transition(
    key: float = 0.5,
    tempo: float = 0.5,
    energy: float = 0.5,
    mood: float = 0.5,
    tag: float = 0.5,
    artist: float = 0.5,
) -> TransitionResult:
    return TransitionResult(
        probability=0.7,
        penalty=0.3,
        is_compatible=True,
        key_compatibility=key,
        tempo_compatibility=tempo,
        energy_compatibility=energy,
        loudness_compatibility=0.5,
        mood_compatibility=mood,
        timbre_compatibility=0.5,
        genre_compatibility=0.5,
        tag_compatibility=tag,
        popularity_compatibility=0.5,
        artist_compatibility=artist,
        era_compatibility=0.5,
        mb_genre_compatibility=0.5,
    )


class TestUpdateWeights(unittest.TestCase):
    def test_high_rating_high_score_increases_weight(self):
        """If user liked it and dim scored high, weight should increase."""
        profile = UserProfile()
        original_tempo = profile.dimension_weights["tempo"]

        tr = _make_transition(tempo=0.95)
        update_weights_from_transition(profile, tr, rating=5.0, learning_rate=0.2)

        # Rating=5 → normalized=1.0, score=0.95 → agreement=0.95
        # Weight should increase
        self.assertGreater(profile.dimension_weights["tempo"], original_tempo)

    def test_low_rating_high_score_decreases_weight(self):
        """If user disliked it but dim scored high, weight should decrease."""
        profile = UserProfile()
        original_tempo = profile.dimension_weights["tempo"]

        tr = _make_transition(tempo=0.95)
        update_weights_from_transition(profile, tr, rating=1.0, learning_rate=0.2)

        # Rating=1 → normalized=0.0, score=0.95 → agreement=0.05
        # Low agreement → weight decreases
        self.assertLess(profile.dimension_weights["tempo"], original_tempo)

    def test_neutral_rating_high_agreement(self):
        """Rating of 3 (neutral) with neutral scores has high agreement."""
        profile = UserProfile()

        tr = _make_transition()  # All 0.5 scores
        update_weights_from_transition(profile, tr, rating=3.0, learning_rate=0.1)

        # Rating=3 → normalized=0.5, score=0.5 → agreement=1.0
        # new_weight = old * 0.9 + 1.0 * 0.1
        # For tempo (0.20): 0.20 * 0.9 + 0.1 = 0.28
        self.assertAlmostEqual(profile.dimension_weights["tempo"], 0.28, places=2)
        # For key (0.15): 0.15 * 0.9 + 0.1 = 0.235
        self.assertAlmostEqual(profile.dimension_weights["key"], 0.235, places=2)

    def test_learning_rate_controls_speed(self):
        """Higher learning rate = bigger changes."""
        p_fast = UserProfile()
        p_slow = UserProfile()

        tr = _make_transition(tempo=0.95)
        update_weights_from_transition(p_fast, tr, rating=5.0, learning_rate=0.5)
        update_weights_from_transition(p_slow, tr, rating=5.0, learning_rate=0.05)

        fast_delta = abs(p_fast.dimension_weights["tempo"] - 0.20)
        slow_delta = abs(p_slow.dimension_weights["tempo"] - 0.20)
        self.assertGreater(fast_delta, slow_delta)

    def test_weights_clamped_to_valid_range(self):
        """Weights should stay in [0.0, 1.0]."""
        profile = UserProfile()
        profile.dimension_weights["tempo"] = 0.99

        tr = _make_transition(tempo=0.99)
        # Many updates with high agreement
        for _ in range(50):
            update_weights_from_transition(profile, tr, rating=5.0, learning_rate=0.5)

        self.assertLessEqual(profile.dimension_weights["tempo"], 1.0)
        self.assertGreaterEqual(profile.dimension_weights["tempo"], 0.0)


class TestUpdateFromFeedback(unittest.TestCase):
    def test_uses_overall_rating(self):
        """Without per-transition ratings, use overall rating."""
        profile = UserProfile()
        original_tempo = profile.dimension_weights["tempo"]

        feedback = PlaylistFeedback(playlist_id="test", overall_rating=5.0)
        transitions = [_make_transition(tempo=0.95)]
        update_from_feedback(profile, feedback, transitions, learning_rate=0.2)

        self.assertGreater(profile.dimension_weights["tempo"], original_tempo)
        self.assertEqual(len(profile.feedback_history), 1)

    def test_uses_per_transition_ratings(self):
        """Per-transition ratings override overall rating."""
        profile = UserProfile()

        feedback = PlaylistFeedback(
            playlist_id="test",
            overall_rating=3.0,
            transition_ratings={0: 5.0},  # Rate first transition as 5
        )
        transitions = [_make_transition(tempo=0.95)]
        original = profile.dimension_weights["tempo"]
        update_from_feedback(profile, feedback, transitions, learning_rate=0.2)

        # Per-transition rating=5 should increase tempo weight
        self.assertGreater(profile.dimension_weights["tempo"], original)

    def test_caps_history(self):
        """Feedback history should be capped at 100 entries."""
        profile = UserProfile()
        profile.feedback_history = [
            PlaylistFeedback(playlist_id=f"old-{i}", overall_rating=3.0)
            for i in range(100)
        ]

        feedback = PlaylistFeedback(playlist_id="new", overall_rating=4.0)
        update_from_feedback(profile, feedback, [], learning_rate=0.1)

        self.assertEqual(len(profile.feedback_history), 100)
        self.assertEqual(profile.feedback_history[-1].playlist_id, "new")


class TestPersistence(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        """Profile should survive save/load cycle."""
        tmpfile = Path(tempfile.mkdtemp()) / "profile.json"

        profile = UserProfile()
        profile.dimension_weights["tempo"] = 0.42
        profile.preferred_genres = {"rock": 0.8}
        profile.preferred_energy_arc = "rising"
        profile.feedback_history = [
            PlaylistFeedback(
                playlist_id="test-1",
                overall_rating=4.0,
                liked_tracks=["mbid-1"],
            )
        ]

        save_profile(profile, tmpfile)
        loaded = load_profile(tmpfile)

        self.assertAlmostEqual(loaded.dimension_weights["tempo"], 0.42)
        self.assertEqual(loaded.preferred_genres, {"rock": 0.8})
        self.assertEqual(loaded.preferred_energy_arc, "rising")
        self.assertEqual(len(loaded.feedback_history), 1)
        self.assertEqual(loaded.feedback_history[0].playlist_id, "test-1")

    def test_load_missing_file_returns_default(self):
        """Loading from a nonexistent file returns default profile."""
        profile = load_profile(Path("/nonexistent/profile.json"))
        self.assertEqual(profile.dimension_weights["tempo"], 0.20)

    def test_load_corrupt_file_returns_default(self):
        """Loading a corrupt file returns default profile."""
        tmpfile = Path(tempfile.mkdtemp()) / "bad.json"
        tmpfile.write_text("not valid json {{{")

        profile = load_profile(tmpfile)
        self.assertEqual(profile.dimension_weights["tempo"], 0.20)


class TestToUserPreferences(unittest.TestCase):
    def test_converts_correctly(self):
        """UserProfile should convert to Module 1's UserPreferences."""
        profile = UserProfile()
        profile.dimension_weights["tempo"] = 0.42
        profile.dimension_weights["key"] = 0.33

        prefs = profile.to_user_preferences()

        self.assertIsInstance(prefs, UserPreferences)
        self.assertAlmostEqual(prefs.tempo_weight, 0.42)
        self.assertAlmostEqual(prefs.key_weight, 0.33)


if __name__ == "__main__":
    unittest.main()
