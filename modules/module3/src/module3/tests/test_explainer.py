"""Tests for Module 3 explainer."""

import unittest

from module1 import TrackFeatures, TransitionResult, UserPreferences

from module3.explainer import (
    detect_energy_arc,
    detect_genre_journey,
    explain_playlist,
    explain_transition,
    generate_playlist_summary,
    generate_quality_metrics,
    get_bottom_contributors,
    get_top_contributors,
)


def _make_track(
    mbid: str = "test-mbid",
    title: str = "Test Track",
    artist: str = "Test Artist",
    bpm: float = 120.0,
    key: str = "C",
    scale: str = "major",
    energy: float = 0.005,
    genre: str | None = "roc",
    mood_happy: tuple[str, float] | None = ("happy", 0.8),
    release_year: int | None = None,
) -> TrackFeatures:
    """Create a TrackFeatures with sensible defaults for testing."""
    return TrackFeatures(
        mbid=mbid,
        title=title,
        artist=artist,
        bpm=bpm,
        key=key,
        scale=scale,
        energy_mid_high=energy,
        genre_rosamerica=(genre, 0.9) if genre else None,
        mood_happy=mood_happy,
        mb_release_year=release_year,
    )


def _make_transition(
    probability: float = 0.8,
    key: float = 0.9,
    tempo: float = 0.85,
    energy: float = 0.7,
    mood: float = 0.8,
    timbre: float = 0.6,
    genre: float = 0.5,
    tag: float = 0.7,
    artist: float = 0.5,
    era: float = 0.5,
) -> TransitionResult:
    """Create a TransitionResult with given dimension scores."""
    return TransitionResult(
        probability=probability,
        penalty=1 - probability,
        is_compatible=probability > 0.3,
        key_compatibility=key,
        tempo_compatibility=tempo,
        energy_compatibility=energy,
        loudness_compatibility=0.5,
        mood_compatibility=mood,
        timbre_compatibility=timbre,
        genre_compatibility=genre,
        tag_compatibility=tag,
        popularity_compatibility=0.5,
        artist_compatibility=artist,
        era_compatibility=era,
        mb_genre_compatibility=0.5,
        explanation="Test explanation",
    )


class TestGetTopContributors(unittest.TestCase):
    def test_returns_top_n_by_weighted_score(self):
        """Top contributors should be sorted by score * weight, descending."""
        tr = _make_transition(tempo=0.95, key=0.5, mood=0.3)
        prefs = UserPreferences()  # tempo=0.20, key=0.15, mood=0.15
        top = get_top_contributors(tr, prefs, n=3)

        self.assertEqual(len(top), 3)
        # Tempo (0.95 * 0.20 = 0.19) should rank high
        dim_names = [name for name, _, _ in top]
        self.assertEqual(dim_names[0], "tempo")

    def test_excludes_zero_weight_dimensions(self):
        """Dimensions with weight=0 should not appear."""
        tr = _make_transition()
        prefs = UserPreferences()  # popularity_weight=0.0, mb_genre_weight=0.0
        top = get_top_contributors(tr, prefs, n=20)

        dim_names = [name for name, _, _ in top]
        self.assertNotIn("popularity", dim_names)
        self.assertNotIn("mb_genre", dim_names)

    def test_includes_description(self):
        """Each contributor should have a human-readable description."""
        tr = _make_transition(tempo=0.95)
        prefs = UserPreferences()
        track1 = _make_track(bpm=120)
        track2 = _make_track(bpm=122)
        top = get_top_contributors(tr, prefs, n=1, track1=track1, track2=track2)

        _, _, desc = top[0]
        self.assertIn("120", desc)
        self.assertIn("122", desc)


class TestGetBottomContributors(unittest.TestCase):
    def test_returns_weakest_dimensions(self):
        """Bottom contributors should be the weakest weighted scores."""
        tr = _make_transition(key=0.1, tempo=0.95, energy=0.05)
        prefs = UserPreferences()
        bottom = get_bottom_contributors(tr, prefs, n=2)

        dim_names = [name for name, _, _ in bottom]
        # energy (0.05 * 0.15 = 0.0075) and key (0.1 * 0.15 = 0.015) should be bottom
        self.assertIn("energy", dim_names)


class TestDetectEnergyArc(unittest.TestCase):
    def test_rising(self):
        tracks = [
            _make_track(energy=0.001),
            _make_track(energy=0.003),
            _make_track(energy=0.005),
            _make_track(energy=0.008),
        ]
        self.assertEqual(detect_energy_arc(tracks), "rising")

    def test_falling(self):
        tracks = [
            _make_track(energy=0.008),
            _make_track(energy=0.005),
            _make_track(energy=0.003),
            _make_track(energy=0.001),
        ]
        self.assertEqual(detect_energy_arc(tracks), "falling")

    def test_steady(self):
        tracks = [
            _make_track(energy=0.005),
            _make_track(energy=0.005),
            _make_track(energy=0.005),
            _make_track(energy=0.005),
        ]
        self.assertEqual(detect_energy_arc(tracks), "steady")

    def test_single_track(self):
        self.assertEqual(detect_energy_arc([_make_track()]), "steady")

    def test_valley(self):
        tracks = [
            _make_track(energy=0.008),
            _make_track(energy=0.002),
            _make_track(energy=0.001),
            _make_track(energy=0.003),
            _make_track(energy=0.008),
        ]
        self.assertEqual(detect_energy_arc(tracks), "valley")

    def test_hill(self):
        tracks = [
            _make_track(energy=0.001),
            _make_track(energy=0.005),
            _make_track(energy=0.009),
            _make_track(energy=0.004),
            _make_track(energy=0.001),
        ]
        self.assertEqual(detect_energy_arc(tracks), "hill")


class TestDetectGenreJourney(unittest.TestCase):
    def test_deduplicates_consecutive(self):
        tracks = [
            _make_track(genre="roc"),
            _make_track(genre="roc"),
            _make_track(genre="pop"),
            _make_track(genre="pop"),
            _make_track(genre="hip"),
        ]
        journey = detect_genre_journey(tracks)
        self.assertEqual(journey, ["roc", "pop", "hip"])

    def test_no_genre_data(self):
        tracks = [_make_track(genre=None), _make_track(genre=None)]
        self.assertEqual(detect_genre_journey(tracks), ["mixed"])

    def test_single_genre(self):
        tracks = [_make_track(genre="roc"), _make_track(genre="roc")]
        self.assertEqual(detect_genre_journey(tracks), ["roc"])


class TestGeneratePlaylistSummary(unittest.TestCase):
    def test_includes_genre_and_energy(self):
        tracks = [
            _make_track(genre="roc", energy=0.001),
            _make_track(genre="pop", energy=0.003),
            _make_track(genre="dan", energy=0.008),
        ]
        transitions = [_make_transition(0.8), _make_transition(0.7)]
        summary = generate_playlist_summary(tracks, transitions)

        self.assertIn("roc", summary)
        self.assertIn("3 tracks", summary)

    def test_empty_playlist(self):
        self.assertEqual(generate_playlist_summary([], []), "Empty playlist.")


class TestGenerateQualityMetrics(unittest.TestCase):
    def test_computes_metrics(self):
        transitions = [
            _make_transition(0.8),
            _make_transition(0.6),
            _make_transition(0.9),
        ]
        metrics = generate_quality_metrics(transitions)

        self.assertAlmostEqual(metrics["avg_compatibility"], 0.7666, places=3)
        self.assertAlmostEqual(metrics["weakest_transition"], 0.6)
        self.assertAlmostEqual(metrics["strongest_transition"], 0.9)

    def test_empty_transitions(self):
        metrics = generate_quality_metrics([])
        self.assertEqual(metrics["avg_compatibility"], 0.0)


class TestExplainTransition(unittest.TestCase):
    def test_produces_valid_explanation(self):
        tr = _make_transition(0.85, tempo=0.95, key=0.9)
        prefs = UserPreferences()
        track1 = _make_track(title="Song A", bpm=120)
        track2 = _make_track(title="Song B", bpm=122)

        exp = explain_transition(tr, prefs, track1, track2)

        self.assertEqual(exp.from_title, "Song A")
        self.assertEqual(exp.to_title, "Song B")
        self.assertAlmostEqual(exp.overall_score, 0.85)
        self.assertEqual(len(exp.top_contributors), 3)
        self.assertEqual(len(exp.bottom_contributors), 2)


class TestExplainPlaylist(unittest.TestCase):
    def test_full_explanation(self):
        tracks = [
            _make_track(mbid="a", title="Start", artist="A"),
            _make_track(mbid="b", title="Middle", artist="B"),
            _make_track(mbid="c", title="End", artist="C"),
        ]
        transitions = [_make_transition(0.8), _make_transition(0.7)]
        prefs = UserPreferences()

        exp = explain_playlist(tracks, transitions, prefs)

        self.assertEqual(len(exp.track_explanations), 3)
        self.assertEqual(exp.track_explanations[0].role, "source")
        self.assertEqual(exp.track_explanations[1].role, "waypoint")
        self.assertEqual(exp.track_explanations[2].role, "destination")
        self.assertIn("3 tracks", exp.summary)
        self.assertGreater(exp.quality_metrics["avg_compatibility"], 0)

    def test_source_has_no_incoming(self):
        tracks = [_make_track(mbid="a"), _make_track(mbid="b")]
        transitions = [_make_transition(0.8)]
        prefs = UserPreferences()

        exp = explain_playlist(tracks, transitions, prefs)

        self.assertIsNone(exp.track_explanations[0].incoming_transition)
        self.assertIsNotNone(exp.track_explanations[0].outgoing_transition)

    def test_dest_has_no_outgoing(self):
        tracks = [_make_track(mbid="a"), _make_track(mbid="b")]
        transitions = [_make_transition(0.8)]
        prefs = UserPreferences()

        exp = explain_playlist(tracks, transitions, prefs)

        self.assertIsNotNone(exp.track_explanations[1].incoming_transition)
        self.assertIsNone(exp.track_explanations[1].outgoing_transition)

    def test_constraint_notes_included(self):
        from module3.data_models import ConstraintResult

        tracks = [_make_track(mbid="a"), _make_track(mbid="b")]
        transitions = [_make_transition(0.8)]
        prefs = UserPreferences()
        constraints = [
            ConstraintResult("No repeat artists", True, 1.0),
            ConstraintResult("Energy arc", False, 0.6, ["Energy not rising"], [2]),
        ]

        exp = explain_playlist(tracks, transitions, prefs, constraints)

        self.assertEqual(len(exp.constraint_notes), 2)
        self.assertIn("satisfied", exp.constraint_notes[0])
        self.assertIn("Energy not rising", exp.constraint_notes[1])


if __name__ == "__main__":
    unittest.main()
