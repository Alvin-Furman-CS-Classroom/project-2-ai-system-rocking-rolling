"""Tests for PlaylistOrchestrator.

All tests are offline — no API calls are made. Module 3's PlaylistAssembler
and Module 2's BeamSearch are patched to avoid network I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult
from module2 import PlaylistPath
from module3 import AssembledPlaylist
from module3.data_models import PlaylistExplanation
from module4 import MoodClassifier
from module4.training_data import generate_synthetic_data

from module5 import PlaylistOrchestrator, PlaylistRequest, TrackInput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _tr(prob: float = 0.8) -> TransitionResult:
    return TransitionResult(probability=prob, penalty=1.0 - prob, is_compatible=prob >= 0.3)


def _make_playlist(mbids: list[str]) -> AssembledPlaylist:
    """Build a minimal AssembledPlaylist for use in mocks."""
    tracks = [TrackFeatures(mbid=m) for m in mbids]
    transitions = [_tr() for _ in range(len(mbids) - 1)]
    path = PlaylistPath(
        mbids=mbids,
        total_cost=0.2 * (len(mbids) - 1),
        transitions=transitions,
    )
    explanation = PlaylistExplanation(summary="Test playlist")
    return AssembledPlaylist(
        path=path,
        tracks=tracks,
        explanation=explanation,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def kb() -> MusicKnowledgeBase:
    return MusicKnowledgeBase()


@pytest.fixture
def classifier() -> MoodClassifier:
    examples = generate_synthetic_data(n_per_class=50, random_seed=0)
    clf = MoodClassifier()
    clf.train(examples, random_seed=0)
    return clf


@pytest.fixture
def orchestrator(kb, classifier) -> PlaylistOrchestrator:
    return PlaylistOrchestrator(knowledge_base=kb, classifier=classifier)


# ---------------------------------------------------------------------------
# TrackInput resolution
# ---------------------------------------------------------------------------


class TestResolveInput:
    def test_mbid_input_returns_mbid_no_synthetic(self, orchestrator):
        mbid, synthetic = orchestrator._resolve_input(
            TrackInput(type="mbid", mbid="abc-123")
        )
        assert mbid == "abc-123"
        assert synthetic is None

    def test_mood_input_returns_centroid_mbid(self, orchestrator):
        mbid, synthetic = orchestrator._resolve_input(
            TrackInput(type="mood", mood="calm")
        )
        assert mbid == "centroid_calm"
        assert isinstance(synthetic, TrackFeatures)
        assert synthetic.mbid == "centroid_calm"

    def test_mood_input_case_insensitive(self, orchestrator):
        mbid, _ = orchestrator._resolve_input(TrackInput(type="mood", mood="CALM"))
        assert mbid == "centroid_calm"

    def test_unknown_mood_returns_none(self, orchestrator):
        mbid, synthetic = orchestrator._resolve_input(
            TrackInput(type="mood", mood="grumpy")
        )
        assert mbid is None
        assert synthetic is None

    def test_mbid_input_missing_mbid_returns_none(self, orchestrator):
        mbid, synthetic = orchestrator._resolve_input(TrackInput(type="mbid"))
        assert mbid is None
        assert synthetic is None


# ---------------------------------------------------------------------------
# generate() — both real tracks
# ---------------------------------------------------------------------------


class TestGenerateBothReal:
    def test_delegates_to_assembler(self, orchestrator):
        expected = _make_playlist(["src", "mid", "dst"])
        with patch(
            "module5.orchestrator.PlaylistAssembler"
        ) as MockAssembler:
            MockAssembler.return_value.generate_playlist.return_value = expected

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mbid", mbid="src"),
                    destination=TrackInput(type="mbid", mbid="dst"),
                    length=3,
                )
            )

        assert result is expected
        MockAssembler.return_value.generate_playlist.assert_called_once_with(
            source_mbid="src",
            dest_mbid="dst",
            target_length=3,
        )

    def test_returns_none_when_assembler_returns_none(self, orchestrator):
        with patch(
            "module5.orchestrator.PlaylistAssembler"
        ) as MockAssembler:
            MockAssembler.return_value.generate_playlist.return_value = None

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mbid", mbid="src"),
                    destination=TrackInput(type="mbid", mbid="dst"),
                )
            )

        assert result is None


# ---------------------------------------------------------------------------
# generate() — both moods (unsupported)
# ---------------------------------------------------------------------------


class TestGenerateBothMoods:
    def test_returns_none_for_both_moods(self, orchestrator):
        result = orchestrator.generate(
            PlaylistRequest(
                source=TrackInput(type="mood", mood="calm"),
                destination=TrackInput(type="mood", mood="energized"),
            )
        )
        assert result is None


# ---------------------------------------------------------------------------
# generate() — mood destination
# ---------------------------------------------------------------------------


class TestGenerateMoodDest:
    def test_assembler_called_with_centroid_as_dest(self, orchestrator):
        expected = _make_playlist(["src", "mid", "centroid_calm"])
        with patch(
            "module5.orchestrator.PlaylistAssembler"
        ) as MockAssembler:
            MockAssembler.return_value.generate_playlist.return_value = expected

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mbid", mbid="src"),
                    destination=TrackInput(type="mood", mood="calm"),
                    length=3,
                )
            )

        _, kwargs = MockAssembler.return_value.generate_playlist.call_args
        assert kwargs["dest_mbid"] == "centroid_calm"
        # Synthetic node stripped from end
        assert result is not None
        assert all(t.mbid != "centroid_calm" for t in result.tracks)

    def test_no_strip_when_last_track_is_real(self, orchestrator):
        playlist = _make_playlist(["src", "mid", "real-end"])
        with patch(
            "module5.orchestrator.PlaylistAssembler"
        ) as MockAssembler:
            MockAssembler.return_value.generate_playlist.return_value = playlist

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mbid", mbid="src"),
                    destination=TrackInput(type="mood", mood="calm"),
                )
            )

        assert result is not None
        assert result.tracks[-1].mbid == "real-end"


# ---------------------------------------------------------------------------
# generate() — mood source
# ---------------------------------------------------------------------------


class TestGenerateMoodSource:
    def test_reverse_search_result_is_flipped(self, orchestrator):
        # BeamSearch.find_path is called with dest as source, centroid as dest
        # Returned path: [dest, mid, centroid_calm]
        # Expected output: [mid, dest]  (reversed, centroid stripped)
        reverse_path = PlaylistPath(
            mbids=["real-dest", "real-mid", "centroid_calm"],
            total_cost=0.4,
            transitions=[_tr(0.8), _tr(0.7)],
        )

        with (
            patch("module5.orchestrator.BeamSearch") as MockBeam,
            patch(
                "module5.orchestrator.SearchSpace"
            ) as MockSearchSpace,
            patch("module5.orchestrator.resolve_constraints") as mock_resolve,
            patch("module5.orchestrator.explain_playlist") as mock_explain,
        ):
            MockBeam.return_value.find_path.return_value = reverse_path

            # get_transition_result returns a valid result for every pair
            MockSearchSpace.return_value.get_transition_result.return_value = _tr(0.75)
            MockSearchSpace.return_value.get_features.side_effect = (
                lambda mbid: TrackFeatures(mbid=mbid)
            )
            MockSearchSpace.return_value.add_features.return_value = None

            tracks_out = [TrackFeatures(mbid="real-mid"), TrackFeatures(mbid="real-dest")]
            mock_resolve.return_value = (tracks_out, [])
            mock_explain.return_value = PlaylistExplanation(summary="ok")

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mood", mood="calm"),
                    destination=TrackInput(type="mbid", mbid="real-dest"),
                    length=3,
                )
            )

        assert result is not None
        # Centroid should not appear in the final playlist
        assert all(t.mbid != "centroid_calm" for t in result.tracks)

        # BeamSearch was called with dest as source and centroid as dest
        call_kwargs = MockBeam.return_value.find_path.call_args
        assert call_kwargs.kwargs["source_mbid"] == "real-dest"
        assert call_kwargs.kwargs["dest_mbid"] == "centroid_calm"

    def test_returns_none_when_reverse_search_fails(self, orchestrator):
        with (
            patch("module5.orchestrator.BeamSearch") as MockBeam,
            patch("module5.orchestrator.SearchSpace"),
        ):
            MockBeam.return_value.find_path.return_value = None

            result = orchestrator.generate(
                PlaylistRequest(
                    source=TrackInput(type="mood", mood="calm"),
                    destination=TrackInput(type="mbid", mbid="real-dest"),
                )
            )

        assert result is None
