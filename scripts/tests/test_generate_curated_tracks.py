"""Unit tests for generate_curated_tracks.py helper functions."""

import json

import pytest

from generate_curated_tracks import (
    assemble_and_write,
    bucket_from_tags,
    select_artists_by_genre,
)


# ── bucket_from_tags ──────────────────────────────────────────────────────────


class TestBucketFromTags:
    def test_exact_genre_match_returns_bucket(self):
        assert bucket_from_tags(["rock"]) == "rock"
        assert bucket_from_tags(["jazz"]) == "jazz"
        assert bucket_from_tags(["classical"]) == "classical"

    def test_subgenre_keyword_returns_parent_bucket(self):
        assert bucket_from_tags(["alternative"]) == "rock"
        assert bucket_from_tags(["techno"]) == "electronic"
        assert bucket_from_tags(["bebop"]) == "jazz"
        assert bucket_from_tags(["trap"]) == "hip-hop"

    def test_no_matching_tags_returns_none(self):
        assert bucket_from_tags([]) is None
        assert bucket_from_tags(["spoken word", "podcast"]) is None

    def test_matching_is_case_insensitive(self):
        assert bucket_from_tags(["ROCK"]) == "rock"
        assert bucket_from_tags(["Hip-Hop"]) == "hip-hop"
        assert bucket_from_tags(["Electronic"]) == "electronic"

    def test_substring_keyword_match(self):
        # "hard rock" contains keyword "rock"
        assert bucket_from_tags(["hard rock"]) == "rock"
        # "ambient electronic" contains keyword "electronic"
        assert bucket_from_tags(["ambient electronic"]) == "electronic"


# ── select_artists_by_genre ───────────────────────────────────────────────────


class TestSelectArtistsByGenre:
    def _make_artists(self, n: int) -> list[dict]:
        return [
            {"artist_mbid": f"mbid-{i}", "artist_name": f"Artist {i}", "rank": i}
            for i in range(n)
        ]

    def test_groups_artists_by_bucket(self):
        artists = self._make_artists(4)
        genres = {
            "mbid-0": "rock", "mbid-1": "jazz",
            "mbid-2": "rock", "mbid-3": "pop",
        }
        result = select_artists_by_genre(artists, genres, artists_per_genre=10)
        assert set(result.keys()) == {"rock", "jazz", "pop"}
        assert len(result["rock"]) == 2
        assert len(result["jazz"]) == 1

    def test_caps_at_artists_per_genre(self):
        artists = self._make_artists(10)
        genres = {f"mbid-{i}": "rock" for i in range(10)}
        result = select_artists_by_genre(artists, genres, artists_per_genre=3)
        assert len(result["rock"]) == 3

    def test_preserves_rank_order(self):
        artists = self._make_artists(5)
        genres = {f"mbid-{i}": "pop" for i in range(5)}
        result = select_artists_by_genre(artists, genres, artists_per_genre=5)
        ranks = [a["rank"] for a in result["pop"]]
        assert ranks == sorted(ranks)

    def test_unrecognized_artists_are_excluded(self):
        artists = self._make_artists(3)
        genres = {"mbid-0": "rock"}  # only first artist mapped
        result = select_artists_by_genre(artists, genres, artists_per_genre=10)
        assert list(result.keys()) == ["rock"]
        assert len(result["rock"]) == 1


# ── assemble_and_write ────────────────────────────────────────────────────────


def _make_candidates() -> dict[str, dict]:
    return {
        "mbid-rock-happy-1": {"title": "Rock Happy 1", "artist": "Artist A", "genre": "rock", "_rank": 0},
        "mbid-rock-happy-2": {"title": "Rock Happy 2", "artist": "Artist B", "genre": "rock", "_rank": 1},
        "mbid-jazz-calm-1":  {"title": "Jazz Calm 1",  "artist": "Artist C", "genre": "jazz", "_rank": 0},
    }


def _make_moods() -> dict[str, dict]:
    return {
        "mbid-rock-happy-1": {"mood": "happy", "bpm": 128.0, "key": "G", "scale": "major"},
        "mbid-rock-happy-2": {"mood": "happy", "bpm": 135.0, "key": "A", "scale": "minor"},
        "mbid-jazz-calm-1":  {"mood": "calm",  "bpm": 90.0,  "key": "D", "scale": "major"},
    }


class TestAssembleAndWrite:
    def test_writes_curated_tracks_json(self, tmp_path):
        assemble_and_write(_make_candidates(), _make_moods(), tmp_path)
        out = tmp_path / "curated_tracks.json"
        assert out.exists()
        tracks = json.loads(out.read_text())
        assert len(tracks) == 3
        assert {t["mbid"] for t in tracks} == {
            "mbid-rock-happy-1", "mbid-rock-happy-2", "mbid-jazz-calm-1"
        }

    def test_track_fields_are_correct(self, tmp_path):
        assemble_and_write(_make_candidates(), _make_moods(), tmp_path)
        tracks = json.loads((tmp_path / "curated_tracks.json").read_text())
        jazz_track = next(t for t in tracks if t["mbid"] == "mbid-jazz-calm-1")
        assert jazz_track["title"] == "Jazz Calm 1"
        assert jazz_track["artist"] == "Artist C"
        assert jazz_track["genre"] == "jazz"
        assert jazz_track["mood"] == "calm"
        assert jazz_track["bpm"] == 90
        assert jazz_track["key"] == "D"
        assert jazz_track["scale"] == "major"
        assert "_rank" not in jazz_track  # internal field must be stripped

    def test_cell_cap_limits_tracks_per_genre_mood(self, tmp_path):
        candidates = {
            f"mbid-{i}": {"title": f"T{i}", "artist": f"A{i}", "genre": "rock", "_rank": i}
            for i in range(5)
        }
        moods = {
            f"mbid-{i}": {"mood": "happy", "bpm": 120.0, "key": "C", "scale": "major"}
            for i in range(5)
        }
        assemble_and_write(candidates, moods, tmp_path, max_per_cell=2)
        tracks = json.loads((tmp_path / "curated_tracks.json").read_text())
        rock_happy = [t for t in tracks if t["genre"] == "rock" and t["mood"] == "happy"]
        assert len(rock_happy) == 2

    def test_writes_genre_artists_json(self, tmp_path):
        assemble_and_write(_make_candidates(), _make_moods(), tmp_path)
        out = tmp_path / "genre_artists.json"
        assert out.exists()
        genre_artists = json.loads(out.read_text())
        assert "rock" in genre_artists
        assert "jazz" in genre_artists
        assert "Artist A" in genre_artists["rock"]
        assert "mbid-rock-happy-1" in genre_artists["rock"]["Artist A"]

    def test_drops_tracks_with_missing_genre(self, tmp_path):
        candidates = {
            "mbid-good": {"title": "Good", "artist": "A", "genre": "rock", "_rank": 0},
            "mbid-bad":  {"title": "Bad",  "artist": "B", "genre": None,   "_rank": 1},
        }
        moods = {
            "mbid-good": {"mood": "happy", "bpm": 120.0, "key": "C", "scale": "major"},
            "mbid-bad":  {"mood": "happy", "bpm": 100.0, "key": "D", "scale": "minor"},
        }
        assemble_and_write(candidates, moods, tmp_path)
        tracks = json.loads((tmp_path / "curated_tracks.json").read_text())
        assert len(tracks) == 1
        assert tracks[0]["mbid"] == "mbid-good"
