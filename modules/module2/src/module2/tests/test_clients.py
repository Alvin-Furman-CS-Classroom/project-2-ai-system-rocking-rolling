"""Tests for API clients (ListenBrainz, AcousticBrainz, MusicBrainz)."""

import unittest
from unittest.mock import MagicMock, patch

from module2.listenbrainz_client import ListenBrainzClient, ListenBrainzConfig
from module2.acousticbrainz_client import AcousticBrainzClient, AcousticBrainzConfig
from module2.musicbrainz_client import MusicBrainzClient, MusicBrainzConfig
from module2.data_models import SimilarRecording

from .fixtures.mock_responses import (
    SIMILAR_RECORDINGS_RESPONSE,
    LOWLEVEL_RESPONSE,
    HIGHLEVEL_RESPONSE,
    LISTENBRAINZ_TAGS_RESPONSE,
    LISTENBRAINZ_POPULARITY_RESPONSE,
    MUSICBRAINZ_RECORDING_RESPONSE,
    MUSICBRAINZ_ARTIST_RELS_RESPONSE,
)


# -------------------------------------------------------------------------
# ListenBrainz client tests
# -------------------------------------------------------------------------


class TestListenBrainzSimilarRecordings(unittest.TestCase):
    """Tests for ListenBrainz similar recordings (neighborhood discovery)."""

    def setUp(self):
        self.config = ListenBrainzConfig(min_request_interval=0.0)
        self.client = ListenBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.post")
    def test_get_similar_recordings_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SIMILAR_RECORDINGS_RESPONSE
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("source-mbid-123", count=5)

        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], SimilarRecording)
        self.assertEqual(result[0].mbid, "similar-1")
        # Score is normalized: 22/22 = 1.0 (highest score)
        self.assertAlmostEqual(result[0].similarity_score, 1.0)

    @patch("requests.Session.post")
    def test_get_similar_recordings_404(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("unknown-mbid")
        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_get_similar_recordings_respects_count(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SIMILAR_RECORDINGS_RESPONSE
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("source-mbid-123", count=2)
        self.assertEqual(len(result), 2)


class TestListenBrainzTags(unittest.TestCase):
    """Tests for ListenBrainz tag enrichment."""

    def setUp(self):
        self.config = ListenBrainzConfig(min_request_interval=0.0)
        self.client = ListenBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.get")
    def test_get_recording_tags_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = LISTENBRAINZ_TAGS_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.get_recording_tags(["similar-1", "similar-2"])

        self.assertIn("similar-1", result)
        self.assertIn("similar-2", result)
        # Recording tags should be present
        tags_1 = result["similar-1"]
        self.assertIn("progressive rock", tags_1)
        self.assertEqual(tags_1["progressive rock"], 25)

    @patch("requests.Session.get")
    def test_get_recording_tags_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.get_recording_tags(["unknown"])
        self.assertEqual(result, {})

    @patch("requests.Session.get")
    def test_get_recording_tags_includes_artist_fallback(self, mock_get):
        """Artist tags should be included when not duplicating recording tags."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = LISTENBRAINZ_TAGS_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.get_recording_tags(["similar-1"])

        tags = result["similar-1"]
        # "psychedelic rock" is an artist-level tag (not in recording tags)
        self.assertIn("psychedelic rock", tags)

    def test_get_recording_tags_empty_list(self):
        result = self.client.get_recording_tags([])
        self.assertEqual(result, {})


class TestListenBrainzPopularity(unittest.TestCase):
    """Tests for ListenBrainz popularity enrichment."""

    def setUp(self):
        self.config = ListenBrainzConfig(min_request_interval=0.0)
        self.client = ListenBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.post")
    def test_get_recording_popularity_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = LISTENBRAINZ_POPULARITY_RESPONSE
        mock_post.return_value = mock_response

        result = self.client.get_recording_popularity(["similar-1", "similar-2"])

        self.assertIn("similar-1", result)
        self.assertEqual(result["similar-1"]["listen_count"], 150000)
        self.assertEqual(result["similar-1"]["user_count"], 25000)

    @patch("requests.Session.post")
    def test_get_recording_popularity_404(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = self.client.get_recording_popularity(["unknown"])
        self.assertEqual(result, {})

    def test_get_recording_popularity_empty_list(self):
        result = self.client.get_recording_popularity([])
        self.assertEqual(result, {})


# -------------------------------------------------------------------------
# AcousticBrainz client tests
# -------------------------------------------------------------------------


class TestAcousticBrainzClient(unittest.TestCase):
    """Tests for AcousticBrainz feature client."""

    def setUp(self):
        self.config = AcousticBrainzConfig(min_request_interval=0.0)
        self.client = AcousticBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.get")
    def test_fetch_lowlevel_batch_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = LOWLEVEL_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.fetch_lowlevel_batch(["similar-1", "similar-2"])

        self.assertEqual(len(result), 2)
        self.assertIn("similar-1", result)
        self.assertIn("similar-2", result)

    @patch("requests.Session.get")
    def test_fetch_highlevel_batch_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = HIGHLEVEL_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.fetch_highlevel_batch(["similar-1", "similar-2"])

        self.assertEqual(len(result), 2)
        self.assertIn("similar-1", result)

    @patch("requests.Session.get")
    def test_fetch_features_batch_combines_data(self, mock_get):
        def side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            if "low-level" in url:
                mock_response.json.return_value = LOWLEVEL_RESPONSE
            else:
                mock_response.json.return_value = HIGHLEVEL_RESPONSE
            return mock_response

        mock_get.side_effect = side_effect

        result = self.client.fetch_features_batch(["similar-1", "similar-2"])

        self.assertEqual(len(result), 2)
        track = result["similar-1"]
        self.assertAlmostEqual(track.bpm, 120.0)
        self.assertEqual(track.key, "C")
        assert track.mood_happy is not None
        self.assertEqual(track.mood_happy[0], "happy")

    @patch("requests.Session.get")
    def test_fetch_features_single(self, mock_get):
        def side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            if "low-level" in url:
                mock_response.json.return_value = {
                    "similar-1": LOWLEVEL_RESPONSE["similar-1"]
                }
            else:
                mock_response.json.return_value = {
                    "similar-1": HIGHLEVEL_RESPONSE["similar-1"]
                }
            return mock_response

        mock_get.side_effect = side_effect

        result = self.client.fetch_features("similar-1")

        assert result is not None
        self.assertEqual(result.mbid, "similar-1")

    @patch("requests.Session.get")
    def test_fetch_features_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.fetch_features("unknown-mbid")
        self.assertIsNone(result)


# -------------------------------------------------------------------------
# MusicBrainz client tests
# -------------------------------------------------------------------------


class TestMusicBrainzRecording(unittest.TestCase):
    """Tests for MusicBrainz recording metadata."""

    def setUp(self):
        self.config = MusicBrainzConfig(min_request_interval=0.0)
        self.client = MusicBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.get")
    def test_get_recording_metadata_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MUSICBRAINZ_RECORDING_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.get_recording_metadata("similar-1")

        self.assertEqual(result.artist_mbid, "83d91898-7763-47d7-b03b-b92132375c47")
        self.assertEqual(result.release_year, 1975)
        self.assertIn("progressive rock", result.genre_tags)
        self.assertIn("art rock", result.genre_tags)

    @patch("requests.Session.get")
    def test_get_recording_metadata_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.get_recording_metadata("unknown-mbid")

        self.assertIsNone(result.artist_mbid)
        self.assertIsNone(result.release_year)
        self.assertEqual(result.genre_tags, [])

    @patch("requests.Session.get")
    def test_get_recording_metadata_caches(self, mock_get):
        """Second call should use cache, not make another API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MUSICBRAINZ_RECORDING_RESPONSE
        mock_get.return_value = mock_response

        self.client.get_recording_metadata("similar-1")
        self.client.get_recording_metadata("similar-1")

        # Should only make 1 API call due to caching
        self.assertEqual(mock_get.call_count, 1)


class TestMusicBrainzArtistRels(unittest.TestCase):
    """Tests for MusicBrainz artist relationships."""

    def setUp(self):
        self.config = MusicBrainzConfig(min_request_interval=0.0)
        self.client = MusicBrainzClient(config=self.config)

    def tearDown(self):
        self.client.close()

    @patch("requests.Session.get")
    def test_get_artist_relationships_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MUSICBRAINZ_ARTIST_RELS_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.get_artist_relationships(
            "83d91898-7763-47d7-b03b-b92132375c47"
        )

        # Should include artist relations only (not URL relations)
        self.assertIn("1dce970e-34bc-48b2-ab51-48d87544a4c2", result)  # David Gilmour
        self.assertIn("6f7e36da-79d8-4219-990d-8e9224d04ebc", result)  # Richard Wright
        self.assertIn("d700b3f5-45af-4d02-95ed-57d301bda93e", result)  # Roger Waters
        # URL relation should NOT be in results
        self.assertEqual(len(result), 5)  # 5 artist relations, not 6 total

    @patch("requests.Session.get")
    def test_get_artist_relationships_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.get_artist_relationships("unknown-artist")
        self.assertEqual(result, set())

    @patch("requests.Session.get")
    def test_get_artist_relationships_caches_by_artist(self, mock_get):
        """Artist rels are cached per-artist to avoid redundant calls."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MUSICBRAINZ_ARTIST_RELS_RESPONSE
        mock_get.return_value = mock_response

        self.client.get_artist_relationships("83d91898-7763-47d7-b03b-b92132375c47")
        self.client.get_artist_relationships("83d91898-7763-47d7-b03b-b92132375c47")

        # Only 1 API call despite 2 lookups
        self.assertEqual(mock_get.call_count, 1)

    def test_cache_stats(self):
        """Cache stats should track cached entries."""
        stats = self.client.cache_stats()
        self.assertEqual(stats["recordings_cached"], 0)
        self.assertEqual(stats["artists_cached"], 0)


if __name__ == "__main__":
    unittest.main()
