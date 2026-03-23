"""Tests for Module 3 playlist assembler."""

import unittest
from unittest.mock import MagicMock, patch

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult, UserPreferences
from module2 import PlaylistPath

from module3.constraints import NoRepeatArtists, NoRepeatedTracks
from module3.data_models import AssembledPlaylist, PlaylistFeedback, UserProfile
from module3.playlist_assembler import PlaylistAssembler


def _make_track(
    mbid: str, title: str = "Track", artist: str = "Artist"
) -> TrackFeatures:
    return TrackFeatures(
        mbid=mbid,
        title=title,
        artist=artist,
        bpm=120.0,
        key="C",
        scale="major",
        energy_mid_high=0.005,
        genre_rosamerica=("roc", 0.9),
        mood_happy=("happy", 0.8),
    )


def _make_transition(probability: float = 0.8) -> TransitionResult:
    return TransitionResult(
        probability=probability,
        penalty=1 - probability,
        is_compatible=True,
        key_compatibility=0.8,
        tempo_compatibility=0.9,
        energy_compatibility=0.7,
        loudness_compatibility=0.5,
        mood_compatibility=0.8,
        timbre_compatibility=0.6,
        genre_compatibility=0.5,
        tag_compatibility=0.7,
        popularity_compatibility=0.5,
        artist_compatibility=0.5,
        era_compatibility=0.5,
        mb_genre_compatibility=0.5,
        explanation="Test",
    )


class MockSearchSpace:
    """Mock search space for testing the assembler."""

    def __init__(self, tracks: dict[str, TrackFeatures]):
        self._tracks = tracks

    def get_features(self, mbid: str) -> TrackFeatures | None:
        return self._tracks.get(mbid)

    def has_features(self, mbid: str) -> bool:
        return mbid in self._tracks

    def add_features(self, mbid: str, features: TrackFeatures) -> None:
        self._tracks[mbid] = features

    def get_scoreable_neighbors(self, mbid: str) -> list[str]:
        return [m for m in self._tracks if m != mbid]

    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None:
        return 0.2

    def get_transition_result(
        self, from_mbid: str, to_mbid: str
    ) -> TransitionResult | None:
        return _make_transition()


class TestPlaylistAssembler(unittest.TestCase):
    def setUp(self):
        self.tracks = {
            "a": _make_track("a", "Start", "Artist A"),
            "b": _make_track("b", "Middle", "Artist B"),
            "c": _make_track("c", "End", "Artist C"),
        }
        self.search_space = MockSearchSpace(self.tracks)
        self.kb = MusicKnowledgeBase()

    @patch.object(
        MusicKnowledgeBase, "get_compatibility", return_value=_make_transition(0.8)
    )
    @patch("module3.playlist_assembler.BeamSearch")
    def test_generates_playlist(self, mock_beam_cls, mock_compat):
        """Full pipeline should produce an AssembledPlaylist."""
        mock_beam = MagicMock()
        mock_beam.find_path_bidirectional.return_value = PlaylistPath(
            mbids=["a", "b", "c"],
            total_cost=0.4,
            transitions=[_make_transition(0.8), _make_transition(0.7)],
        )
        mock_beam_cls.return_value = mock_beam

        assembler = PlaylistAssembler(
            knowledge_base=self.kb,
            search_space=self.search_space,
        )

        result = assembler.generate_playlist("a", "c", target_length=3)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, AssembledPlaylist)
        self.assertEqual(result.length, 3)
        self.assertIn("3 tracks", result.explanation.summary)
        self.assertGreater(len(result.constraints_applied), 0)

    @patch("module3.playlist_assembler.BeamSearch")
    def test_returns_none_when_no_path(self, mock_beam_cls):
        """Should return None if beam search finds no path."""
        mock_beam = MagicMock()
        mock_beam.find_path_bidirectional.return_value = None
        mock_beam_cls.return_value = mock_beam

        assembler = PlaylistAssembler(
            knowledge_base=self.kb,
            search_space=self.search_space,
        )

        result = assembler.generate_playlist("a", "c")
        self.assertIsNone(result)

    @patch.object(
        MusicKnowledgeBase, "get_compatibility", return_value=_make_transition(0.8)
    )
    @patch("module3.playlist_assembler.BeamSearch")
    def test_applies_user_profile(self, mock_beam_cls, mock_compat):
        """User profile should be converted to preferences."""
        mock_beam = MagicMock()
        mock_beam.find_path_bidirectional.return_value = PlaylistPath(
            mbids=["a", "b", "c"],
            total_cost=0.4,
            transitions=[_make_transition(), _make_transition()],
        )
        mock_beam_cls.return_value = mock_beam

        profile = UserProfile()
        profile.dimension_weights["tempo"] = 0.5

        assembler = PlaylistAssembler(
            knowledge_base=self.kb,
            search_space=self.search_space,
            user_profile=profile,
        )

        result = assembler.generate_playlist("a", "c", target_length=3)
        self.assertIsNotNone(result)

    @patch.object(
        MusicKnowledgeBase, "get_compatibility", return_value=_make_transition(0.8)
    )
    @patch("module3.playlist_assembler.BeamSearch")
    def test_to_static_output(self, mock_beam_cls, mock_compat):
        """Static output should be JSON-serializable."""
        mock_beam = MagicMock()
        mock_beam.find_path_bidirectional.return_value = PlaylistPath(
            mbids=["a", "b", "c"],
            total_cost=0.4,
            transitions=[_make_transition(0.8), _make_transition(0.7)],
        )
        mock_beam_cls.return_value = mock_beam

        assembler = PlaylistAssembler(
            knowledge_base=self.kb,
            search_space=self.search_space,
        )

        result = assembler.generate_playlist("a", "c", target_length=3)
        output = result.to_static_output()

        self.assertIn("playlist_id", output)
        self.assertIn("tracks", output)
        self.assertIn("transitions", output)
        self.assertIn("summary", output)
        self.assertIn("quality", output)
        self.assertEqual(len(output["tracks"]), 3)
        self.assertEqual(output["tracks"][0]["title"], "Start")


class TestFeedbackSubmission(unittest.TestCase):
    def test_submit_feedback_updates_profile(self):
        """Submitting feedback should update user profile weights."""
        assembler = PlaylistAssembler()
        assembler.user_profile = UserProfile()
        original_tempo = assembler.user_profile.dimension_weights["tempo"]

        feedback = PlaylistFeedback(playlist_id="test", overall_rating=5.0)
        transitions = [_make_transition(0.9)]

        assembler.submit_feedback(feedback, transitions, learning_rate=0.2)

        self.assertNotEqual(
            assembler.user_profile.dimension_weights["tempo"], original_tempo
        )
        self.assertEqual(len(assembler.user_profile.feedback_history), 1)

    def test_submit_feedback_creates_profile_if_none(self):
        """Feedback submission should create a profile if none exists."""
        assembler = PlaylistAssembler()
        self.assertIsNone(assembler.user_profile)

        feedback = PlaylistFeedback(playlist_id="test", overall_rating=4.0)
        assembler.submit_feedback(feedback, [])

        self.assertIsNotNone(assembler.user_profile)


if __name__ == "__main__":
    unittest.main()
