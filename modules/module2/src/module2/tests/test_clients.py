"""Tests for API clients."""

import unittest
from unittest.mock import MagicMock, patch

from module2.listenbrainz_client import ListenBrainzClient, ListenBrainzConfig
from module2.acousticbrainz_client import AcousticBrainzClient, AcousticBrainzConfig
from module2.data_models import SimilarRecording

from .fixtures.mock_responses import (
    SIMILAR_RECORDINGS_RESPONSE,
    LOWLEVEL_RESPONSE,
    HIGHLEVEL_RESPONSE,
)


class TestListenBrainzClient(unittest.TestCase):
    """Tests for ListenBrainzClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = ListenBrainzConfig(min_request_interval=0.0)
        self.client = ListenBrainzClient(config=self.config)

    def tearDown(self):
        """Clean up."""
        self.client.close()

    @patch("requests.Session.post")
    def test_get_similar_recordings_success(self, mock_post):
        """Test successful similar recordings fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SIMILAR_RECORDINGS_RESPONSE
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("source-mbid-123", count=5)

        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], SimilarRecording)
        self.assertEqual(result[0].mbid, "similar-1")
        self.assertAlmostEqual(result[0].similarity_score, 0.95)

    @patch("requests.Session.post")
    def test_get_similar_recordings_404(self, mock_post):
        """Test 404 response returns empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("unknown-mbid")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_get_similar_recordings_respects_count(self, mock_post):
        """Test that count parameter limits results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SIMILAR_RECORDINGS_RESPONSE
        mock_post.return_value = mock_response

        result = self.client.get_similar_recordings("source-mbid-123", count=2)

        self.assertEqual(len(result), 2)


class TestAcousticBrainzClient(unittest.TestCase):
    """Tests for AcousticBrainzClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AcousticBrainzConfig(min_request_interval=0.0)
        self.client = AcousticBrainzClient(config=self.config)

    def tearDown(self):
        """Clean up."""
        self.client.close()

    @patch("requests.Session.get")
    def test_fetch_lowlevel_batch_success(self, mock_get):
        """Test successful low-level batch fetch."""
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
        """Test successful high-level batch fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = HIGHLEVEL_RESPONSE
        mock_get.return_value = mock_response

        result = self.client.fetch_highlevel_batch(["similar-1", "similar-2"])

        self.assertEqual(len(result), 2)
        self.assertIn("similar-1", result)

    @patch("requests.Session.get")
    def test_fetch_features_batch_combines_data(self, mock_get):
        """Test that features batch combines low and high level data."""

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
        # Check that features have both low-level and high-level data
        track = result["similar-1"]
        self.assertAlmostEqual(track.bpm, 120.0)
        self.assertEqual(track.key, "C")
        assert track.mood_happy is not None
        self.assertEqual(track.mood_happy[0], "happy")

    @patch("requests.Session.get")
    def test_fetch_features_single(self, mock_get):
        """Test fetching features for a single recording."""

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
        """Test fetching features for non-existent recording."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.fetch_features("unknown-mbid")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
