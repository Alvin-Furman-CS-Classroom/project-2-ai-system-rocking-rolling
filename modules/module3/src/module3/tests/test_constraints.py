"""Tests for Module 3 constraint satisfaction."""

import unittest

from module1 import TrackFeatures

from module3.constraints import (
    EnergyArcConstraint,
    GenreVarietyConstraint,
    MoodCoherenceConstraint,
    NoRepeatArtists,
    NoRepeatedTracks,
    TempoSmoothnessConstraint,
    evaluate_all,
)


def _make_track(
    mbid: str = "t1",
    artist: str = "Artist A",
    artist_mbid: str | None = None,
    bpm: float = 120.0,
    genre: str | None = "roc",
    energy: float = 0.005,
    mood_happy: tuple[str, float] | None = ("happy", 0.8),
    mood_sad: tuple[str, float] | None = None,
) -> TrackFeatures:
    return TrackFeatures(
        mbid=mbid,
        artist=artist,
        artist_mbid=artist_mbid,
        bpm=bpm,
        genre_rosamerica=(genre, 0.9) if genre else None,
        energy_mid_high=energy,
        mood_happy=mood_happy,
        mood_sad=mood_sad,
    )


# --- No Repeat Artists ---


class TestNoRepeatArtists(unittest.TestCase):
    def test_all_unique_artists(self):
        tracks = [
            _make_track(mbid="1", artist="A"),
            _make_track(mbid="2", artist="B"),
            _make_track(mbid="3", artist="C"),
        ]
        result = NoRepeatArtists().evaluate(tracks)
        self.assertTrue(result.satisfied)
        self.assertEqual(result.score, 1.0)

    def test_repeated_artist(self):
        tracks = [
            _make_track(mbid="1", artist="A"),
            _make_track(mbid="2", artist="B"),
            _make_track(mbid="3", artist="A"),
        ]
        result = NoRepeatArtists().evaluate(tracks)
        self.assertFalse(result.satisfied)
        self.assertEqual(len(result.violations), 1)
        self.assertIn(2, result.violating_positions)

    def test_uses_artist_mbid_when_available(self):
        tracks = [
            _make_track(mbid="1", artist="", artist_mbid="artist-1"),
            _make_track(mbid="2", artist="", artist_mbid="artist-2"),
            _make_track(mbid="3", artist="", artist_mbid="artist-1"),
        ]
        result = NoRepeatArtists().evaluate(tracks)
        self.assertFalse(result.satisfied)

    def test_case_insensitive(self):
        tracks = [
            _make_track(mbid="1", artist="Pink Floyd"),
            _make_track(mbid="2", artist="pink floyd"),
        ]
        result = NoRepeatArtists().evaluate(tracks)
        self.assertFalse(result.satisfied)


# --- No Repeated Tracks ---


class TestNoRepeatedTracks(unittest.TestCase):
    def test_all_unique(self):
        tracks = [_make_track(mbid="1"), _make_track(mbid="2"), _make_track(mbid="3")]
        result = NoRepeatedTracks().evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_repeated_track(self):
        tracks = [_make_track(mbid="1"), _make_track(mbid="2"), _make_track(mbid="1")]
        result = NoRepeatedTracks().evaluate(tracks)
        self.assertFalse(result.satisfied)
        self.assertIn(2, result.violating_positions)


# --- Energy Arc ---


class TestEnergyArcConstraint(unittest.TestCase):
    def test_rising_satisfied(self):
        tracks = [
            _make_track(energy=0.001),
            _make_track(energy=0.003),
            _make_track(energy=0.006),
        ]
        result = EnergyArcConstraint(target_arc="rising").evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_rising_violated(self):
        tracks = [
            _make_track(energy=0.006),
            _make_track(energy=0.003),
            _make_track(energy=0.001),
        ]
        result = EnergyArcConstraint(target_arc="rising").evaluate(tracks)
        self.assertFalse(result.satisfied)
        self.assertGreater(len(result.violations), 0)

    def test_falling_satisfied(self):
        tracks = [
            _make_track(energy=0.008),
            _make_track(energy=0.005),
            _make_track(energy=0.002),
        ]
        result = EnergyArcConstraint(target_arc="falling").evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_flat_satisfied(self):
        tracks = [
            _make_track(energy=0.005),
            _make_track(energy=0.005),
            _make_track(energy=0.005),
        ]
        result = EnergyArcConstraint(target_arc="flat").evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_short_playlist_always_satisfied(self):
        tracks = [_make_track(energy=0.001), _make_track(energy=0.009)]
        result = EnergyArcConstraint(target_arc="rising").evaluate(tracks)
        self.assertTrue(result.satisfied)


# --- Genre Variety ---


class TestGenreVarietyConstraint(unittest.TestCase):
    def test_varied_genres(self):
        tracks = [
            _make_track(genre="roc"),
            _make_track(genre="pop"),
            _make_track(genre="hip"),
        ]
        result = GenreVarietyConstraint(max_consecutive=2).evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_too_many_consecutive(self):
        tracks = [
            _make_track(genre="roc"),
            _make_track(genre="roc"),
            _make_track(genre="roc"),
        ]
        result = GenreVarietyConstraint(max_consecutive=2).evaluate(tracks)
        self.assertFalse(result.satisfied)

    def test_exactly_at_limit(self):
        tracks = [
            _make_track(genre="roc"),
            _make_track(genre="roc"),
            _make_track(genre="pop"),
        ]
        result = GenreVarietyConstraint(max_consecutive=2).evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_none_genres_dont_count(self):
        tracks = [
            _make_track(genre=None),
            _make_track(genre=None),
            _make_track(genre=None),
        ]
        result = GenreVarietyConstraint(max_consecutive=2).evaluate(tracks)
        self.assertTrue(result.satisfied)


# --- Tempo Smoothness ---


class TestTempoSmoothnessConstraint(unittest.TestCase):
    def test_smooth_transitions(self):
        tracks = [
            _make_track(bpm=120),
            _make_track(bpm=125),
            _make_track(bpm=130),
        ]
        result = TempoSmoothnessConstraint(max_bpm_jump=30).evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_large_jump(self):
        tracks = [
            _make_track(bpm=80),
            _make_track(bpm=140),
            _make_track(bpm=90),
        ]
        result = TempoSmoothnessConstraint(max_bpm_jump=30).evaluate(tracks)
        self.assertFalse(result.satisfied)
        self.assertEqual(len(result.violations), 2)

    def test_custom_threshold(self):
        tracks = [
            _make_track(bpm=100),
            _make_track(bpm=115),
        ]
        # 15 BPM jump, threshold 10
        result = TempoSmoothnessConstraint(max_bpm_jump=10).evaluate(tracks)
        self.assertFalse(result.satisfied)


# --- Mood Coherence ---


class TestMoodCoherenceConstraint(unittest.TestCase):
    def test_coherent_moods(self):
        tracks = [
            _make_track(mood_happy=("happy", 0.9), mood_sad=("not_sad", 0.8)),
            _make_track(mood_happy=("happy", 0.8), mood_sad=("not_sad", 0.7)),
            _make_track(mood_happy=("happy", 0.7), mood_sad=("not_sad", 0.6)),
        ]
        result = MoodCoherenceConstraint().evaluate(tracks)
        self.assertTrue(result.satisfied)

    def test_oscillating_moods(self):
        tracks = [
            _make_track(mood_happy=("happy", 0.9), mood_sad=("not_sad", 0.9)),
            _make_track(mood_happy=("not_happy", 0.9), mood_sad=("sad", 0.9)),
            _make_track(mood_happy=("happy", 0.9), mood_sad=("not_sad", 0.9)),
        ]
        result = MoodCoherenceConstraint().evaluate(tracks)
        self.assertFalse(result.satisfied)
        self.assertGreater(len(result.violations), 0)


# --- Evaluate All ---


class TestEvaluateAll(unittest.TestCase):
    def test_evaluates_default_constraints(self):
        tracks = [
            _make_track(mbid="1", artist="A", bpm=120, genre="roc"),
            _make_track(mbid="2", artist="B", bpm=125, genre="pop"),
            _make_track(mbid="3", artist="C", bpm=130, genre="hip"),
        ]
        results = evaluate_all(tracks)

        # Should evaluate 4 default constraints
        self.assertEqual(len(results), 4)
        # All should be satisfied for this clean playlist
        for r in results:
            self.assertTrue(r.satisfied, f"{r.name} should be satisfied")

    def test_custom_constraints(self):
        tracks = [_make_track(mbid="1"), _make_track(mbid="2")]
        constraints = [NoRepeatArtists(), TempoSmoothnessConstraint()]
        results = evaluate_all(tracks, constraints)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
