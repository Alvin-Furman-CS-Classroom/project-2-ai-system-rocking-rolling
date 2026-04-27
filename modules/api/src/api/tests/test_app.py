"""Tests for the Flask API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
import requests as req

from api.app import app
from module1.data_models import TrackFeatures, TransitionResult
from module2.data_models import PlaylistPath
from module3.data_models import AssembledPlaylist, ConstraintResult, PlaylistExplanation


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_track(mbid: str = "test-mbid-1234") -> TrackFeatures:
    return TrackFeatures(
        mbid=mbid,
        title="Test Track",
        artist="Test Artist",
        bpm=120.0,
        key="C",
        scale="major",
    )


def _make_transition(probability: float = 0.8) -> TransitionResult:
    return TransitionResult(
        probability=probability,
        penalty=round(1 - probability, 4),
        is_compatible=probability >= 0.5,
        key_compatibility=0.8,
        tempo_compatibility=0.9,
        energy_compatibility=0.7,
        loudness_compatibility=0.5,
        mood_compatibility=0.8,
        timbre_compatibility=0.6,
        genre_compatibility=0.5,
    )


def _make_assembled_playlist(
    source_mbid: str = "src", dest_mbid: str = "dst"
) -> AssembledPlaylist:
    mbids = [source_mbid, "mid-1", dest_mbid]
    transitions = [_make_transition(0.8), _make_transition(0.75)]
    # total_cost = 0.2 + 0.25 = 0.45 → average_compatibility = 1 - 0.45/2 = 0.775
    path = PlaylistPath(mbids=mbids, total_cost=0.45, transitions=transitions)
    explanation = PlaylistExplanation(
        summary="A smooth 3-track journey.",
        quality_metrics={"avg_compatibility": 0.775},
    )
    tracks = [_make_track(m) for m in mbids]
    constraints = [
        ConstraintResult(name="NoRepeatArtists", satisfied=True, score=1.0),
        ConstraintResult(name="TempoSmoothness", satisfied=True, score=0.9),
    ]
    return AssembledPlaylist(
        path=path,
        tracks=tracks,
        explanation=explanation,
        constraints_applied=constraints,
    )


# ── /api/health ───────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_200_with_ok_status(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


# ── /api/compare ──────────────────────────────────────────────────────────────


class TestCompare:
    def test_missing_both_params_returns_400(self, client):
        resp = client.get("/api/compare")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_second_param_returns_400(self, client):
        resp = client.get("/api/compare?recording_id_1=abc")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_success_returns_compatibility_shape(self, client):
        with (
            patch("api.app.fetch_acousticbrainz", return_value=({}, {})),
            patch("api.app.load_track_from_data", return_value=_make_track()),
            patch("api.app.kb") as mock_kb,
        ):
            mock_kb.get_compatibility.return_value = _make_transition(0.75)
            resp = client.get("/api/compare?recording_id_1=aaa&recording_id_2=bbb")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["score"] == 0.75
        assert data["is_compatible"] is True
        assert set(data["components"]) == {
            "key", "tempo", "energy", "loudness", "mood", "timbre", "genre"
        }
        assert data["recording_id_1"] == "aaa"
        assert data["recording_id_2"] == "bbb"

    def test_acousticbrainz_connection_error_returns_502(self, client):
        with patch("api.app.fetch_acousticbrainz", side_effect=req.ConnectionError):
            resp = client.get("/api/compare?recording_id_1=aaa&recording_id_2=bbb")
        assert resp.status_code == 502
        assert "error" in resp.get_json()

    def test_acousticbrainz_http_error_returns_502(self, client):
        err = req.HTTPError(response=MagicMock(status_code=404))
        with patch("api.app.fetch_acousticbrainz", side_effect=err):
            resp = client.get("/api/compare?recording_id_1=aaa&recording_id_2=bbb")
        assert resp.status_code == 502
        assert "error" in resp.get_json()


# ── /api/playlist ─────────────────────────────────────────────────────────────


class TestPlaylist:
    def test_missing_both_params_returns_400(self, client):
        resp = client.get("/api/playlist")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_dest_param_returns_400(self, client):
        resp = client.get("/api/playlist?source_mbid=abc")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_success_returns_full_playlist_shape(self, client):
        playlist = _make_assembled_playlist("src-id", "dst-id")
        with (
            patch("api.app.fetch_acousticbrainz", return_value=({}, {})),
            patch("api.app.load_track_from_data", return_value=_make_track()),
            patch("api.app.SearchSpace"),
            patch("api.app.PlaylistAssembler") as mock_pa_cls,
        ):
            mock_pa_cls.return_value.generate_playlist.return_value = playlist
            resp = client.get("/api/playlist?source_mbid=src-id&dest_mbid=dst-id")

        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["tracks"]) == 3
        assert len(data["transitions"]) == 2
        assert len(data["constraints"]) == 2
        assert data["summary"] == "A smooth 3-track journey."
        assert data["average_compatibility"] == 0.775
        # Each track should have required fields
        for track in data["tracks"]:
            assert "position" in track
            assert "mbid" in track

    def test_no_path_found_returns_404(self, client):
        with (
            patch("api.app.fetch_acousticbrainz", return_value=({}, {})),
            patch("api.app.load_track_from_data", return_value=_make_track()),
            patch("api.app.SearchSpace"),
            patch("api.app.PlaylistAssembler") as mock_pa_cls,
        ):
            mock_pa_cls.return_value.generate_playlist.return_value = None
            resp = client.get("/api/playlist?source_mbid=aaa&dest_mbid=bbb")

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_acousticbrainz_failure_returns_502(self, client):
        with patch("api.app.fetch_acousticbrainz", side_effect=req.ConnectionError):
            resp = client.get("/api/playlist?source_mbid=aaa&dest_mbid=bbb")
        assert resp.status_code == 502
        assert "error" in resp.get_json()

    def test_custom_length_and_beam_width_forwarded(self, client):
        playlist = _make_assembled_playlist()
        with (
            patch("api.app.fetch_acousticbrainz", return_value=({}, {})),
            patch("api.app.load_track_from_data", return_value=_make_track()),
            patch("api.app.SearchSpace"),
            patch("api.app.PlaylistAssembler") as mock_pa_cls,
        ):
            mock_pa_cls.return_value.generate_playlist.return_value = playlist
            resp = client.get(
                "/api/playlist?source_mbid=a&dest_mbid=b&length=5&beam_width=20"
            )

        assert resp.status_code == 200
        # Verify beam_width was passed to PlaylistAssembler constructor
        _, kwargs = mock_pa_cls.call_args
        assert kwargs.get("beam_width") == 20
        # Verify target_length was forwarded to generate_playlist
        mock_pa_cls.return_value.generate_playlist.assert_called_once_with(
            source_mbid="a", dest_mbid="b", target_length=5
        )
