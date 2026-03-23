"""Tests for Module 3 Essentia client.

All tests mock the Essentia library and yt-dlp subprocess — no real
audio processing or downloads happen during testing.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from module1 import TrackFeatures

from module3.essentia_client import EssentiaClient, EssentiaConfig

from .fixtures.mock_essentia import MOCK_CACHED_FEATURES, MOCK_HIGHLEVEL, MOCK_LOWLEVEL


class TestEssentiaClientCaching(unittest.TestCase):
    """Test feature caching behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = EssentiaConfig(
            cache_dir=f"{self.tmpdir}/cache",
            audio_cache_dir=f"{self.tmpdir}/audio",
        )
        self.client = EssentiaClient(self.config)

    def test_loads_from_cache(self):
        """If features are cached, return them without extraction."""
        cache_file = Path(self.config.cache_dir) / "test-mbid.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(MOCK_CACHED_FEATURES, f)

        result = self.client.fetch_features("test-mbid")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, TrackFeatures)
        assert isinstance(result, TrackFeatures)
        self.assertAlmostEqual(result.bpm, 128.5)
        self.assertEqual(result.key, "A")
        self.assertEqual(result.scale, "minor")
        self.assertEqual(self.client._stats["cache_hits"], 1)

    def test_corrupt_cache_is_removed(self):
        """Corrupt cache files should be deleted and return None."""
        cache_file = Path(self.config.cache_dir) / "bad-mbid.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("not valid json {{{")

        result = self.client._load_cached_features("bad-mbid")

        self.assertIsNone(result)
        self.assertFalse(cache_file.exists())

    def test_saves_to_cache_after_extraction(self):
        """After successful extraction, features should be cached."""
        cache_file = Path(self.config.cache_dir) / "new-mbid.json"
        self.assertFalse(cache_file.exists())

        self.client._save_cached_features("new-mbid", MOCK_LOWLEVEL, MOCK_HIGHLEVEL)

        self.assertTrue(cache_file.exists())
        with open(cache_file) as f:
            data = json.load(f)
        self.assertIn("lowlevel", data)
        self.assertIn("highlevel", data)


class TestAudioAcquisition(unittest.TestCase):
    """Test yt-dlp audio download behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = EssentiaConfig(
            cache_dir=f"{self.tmpdir}/cache",
            audio_cache_dir=f"{self.tmpdir}/audio",
        )
        self.client = EssentiaClient(self.config)

    def test_returns_cached_audio(self):
        """If audio file exists in cache, return it directly."""
        audio_file = Path(self.config.audio_cache_dir) / "cached-mbid.ogg"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_text("fake audio data")

        result = self.client._acquire_audio("cached-mbid", "Title", "Artist")

        self.assertIsNotNone(result)
        self.assertEqual(result, audio_file)

    def test_no_title_returns_none(self):
        """Without a title, we can't search YouTube."""
        result = self.client._acquire_audio("mbid", None, "Artist")
        self.assertIsNone(result)

    @patch("module3.essentia_client.subprocess.run")
    def test_ytdlp_success(self, mock_run):
        """Successful yt-dlp download should return the audio path."""
        audio_file = Path(self.config.audio_cache_dir) / "dl-mbid.ogg"

        def side_effect(*args, **kwargs):
            # Simulate yt-dlp creating the file
            audio_file.write_text("fake audio")
            return MagicMock(returncode=0, stderr="")

        mock_run.side_effect = side_effect

        result = self.client._acquire_audio("dl-mbid", "Test Song", "Test Artist")

        self.assertIsNotNone(result)
        mock_run.assert_called_once()
        # Verify yt-dlp was called with correct search query
        call_args = mock_run.call_args[0][0]
        self.assertIn("ytsearch1:Test Artist Test Song", call_args)

    @patch("module3.essentia_client.subprocess.run")
    def test_ytdlp_failure(self, mock_run):
        """Failed yt-dlp should return None."""
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: no results")

        result = self.client._acquire_audio("fail-mbid", "Song", "Artist")

        self.assertIsNone(result)

    @patch("module3.essentia_client.subprocess.run", side_effect=FileNotFoundError)
    def test_ytdlp_not_installed(self, mock_run):
        """Missing yt-dlp should return None gracefully."""
        result = self.client._acquire_audio("mbid", "Song", "Artist")
        self.assertIsNone(result)

    @patch(
        "module3.essentia_client.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="yt-dlp", timeout=60),
    )
    def test_ytdlp_timeout(self, mock_run):
        """yt-dlp timeout should return None gracefully."""
        result = self.client._acquire_audio("mbid", "Song", "Artist")
        self.assertIsNone(result)


class TestFeatureExtraction(unittest.TestCase):
    """Test Essentia feature extraction and AB format mapping."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = EssentiaConfig(
            cache_dir=f"{self.tmpdir}/cache",
            audio_cache_dir=f"{self.tmpdir}/audio",
        )
        self.client = EssentiaClient(self.config)

    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", False)
    def test_not_available_returns_none(self):
        """If Essentia is not installed, fetch_features returns None."""
        client = EssentiaClient(self.config)
        result = client.fetch_features("mbid", "Title", "Artist")
        self.assertIsNone(result)

    def test_map_to_ab_lowlevel_structure(self):
        """Mapped lowlevel output should have correct AB structure."""
        # Create a mock features object that supports key access
        mock_features = {
            "rhythm.bpm": 130.0,
            "rhythm.onset_rate": 3.5,
            "rhythm.beats_count": 200,
            "rhythm.danceability": 0.6,
            "tonal.key_key": "D",
            "tonal.key_scale": "minor",
            "tonal.key_strength": 0.75,
            "tonal.tuning_frequency": 440.0,
            "tonal.chords_strength.mean": 0.5,
            "lowlevel.spectral_energyband_low.mean": 0.001,
            "lowlevel.spectral_energyband_middle_low.mean": 0.003,
            "lowlevel.spectral_energyband_middle_high.mean": 0.005,
            "lowlevel.spectral_energyband_high.mean": 0.002,
            "lowlevel.average_loudness": 0.7,
            "lowlevel.dynamic_complexity": 2.5,
            "lowlevel.mfcc.mean": [-500.0] + [0.0] * 12,
            "lowlevel.mfcc.cov": [[1.0] * 13 for _ in range(13)],
            "lowlevel.spectral_centroid.mean": 2000.0,
            "lowlevel.dissonance.mean": 0.35,
        }

        # Mock the features object to support dict-like access
        class MockPool:
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                if key not in self._data:
                    raise KeyError(key)
                return self._data[key]

        lowlevel = self.client._map_to_ab_lowlevel(MockPool(mock_features))

        # Verify structure matches what load_track_from_data expects
        self.assertEqual(lowlevel["rhythm"]["bpm"], 130.0)
        self.assertEqual(lowlevel["tonal"]["key_key"], "D")
        self.assertEqual(lowlevel["tonal"]["key_scale"], "minor")
        self.assertIn("mean", lowlevel["lowlevel"]["spectral_energyband_low"])
        self.assertIn("mean", lowlevel["lowlevel"]["mfcc"])
        self.assertIn("cov", lowlevel["lowlevel"]["mfcc"])
        self.assertEqual(lowlevel["lowlevel"]["average_loudness"], 0.7)

    def test_map_to_ab_lowlevel_feeds_into_load_track(self):
        """Mapped lowlevel should be parseable by Module 1's loader."""
        from module1.data_loader import load_track_from_data

        features = load_track_from_data(MOCK_LOWLEVEL, MOCK_HIGHLEVEL)

        self.assertAlmostEqual(features.bpm, 128.5)
        self.assertEqual(features.key, "A")
        self.assertEqual(features.scale, "minor")
        assert features.average_loudness is not None
        self.assertAlmostEqual(features.average_loudness, 0.65)
        assert features.mfcc is not None
        self.assertIsNotNone(features.mfcc)
        self.assertEqual(len(features.mfcc), 13)


class TestFullPipeline(unittest.TestCase):
    """Test the complete fetch_features pipeline with mocks."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = EssentiaConfig(
            cache_dir=f"{self.tmpdir}/cache",
            audio_cache_dir=f"{self.tmpdir}/audio",
            cleanup_audio=False,
        )
        self.client = EssentiaClient(self.config)

    @patch.object(EssentiaClient, "_extract_features")
    @patch.object(EssentiaClient, "_acquire_audio")
    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", True)
    def test_full_pipeline_success(self, mock_acquire, mock_extract):
        """Full pipeline: acquire → extract → parse → cache."""
        audio_path = Path(self.tmpdir) / "test.ogg"
        audio_path.write_text("fake audio")
        mock_acquire.return_value = audio_path
        mock_extract.return_value = (MOCK_LOWLEVEL, MOCK_HIGHLEVEL)

        result = self.client.fetch_features("pipe-mbid", "Test Song", "Test Artist")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, TrackFeatures)
        assert isinstance(result, TrackFeatures)
        self.assertEqual(result.mbid, "pipe-mbid")
        self.assertEqual(result.title, "Test Song")
        self.assertEqual(result.artist, "Test Artist")
        self.assertAlmostEqual(result.bpm, 128.5)
        self.assertEqual(self.client._stats["extractions"], 1)

        # Verify cache was written
        cache_file = Path(self.config.cache_dir) / "pipe-mbid.json"
        self.assertTrue(cache_file.exists())

    @patch.object(EssentiaClient, "_acquire_audio", return_value=None)
    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", True)
    def test_audio_acquisition_failure(self, mock_acquire):
        """If audio can't be acquired, return None."""
        result = self.client.fetch_features("no-audio", "Song", "Artist")
        self.assertIsNone(result)
        self.assertEqual(self.client._stats["failures"], 1)

    @patch.object(
        EssentiaClient,
        "_extract_features",
        side_effect=RuntimeError("extraction failed"),
    )
    @patch.object(EssentiaClient, "_acquire_audio")
    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", True)
    def test_extraction_failure(self, mock_acquire, mock_extract):
        """If extraction fails, return None gracefully."""
        audio_path = Path(self.tmpdir) / "test.ogg"
        audio_path.write_text("fake audio")
        mock_acquire.return_value = audio_path

        result = self.client.fetch_features("fail-mbid", "Song", "Artist")
        self.assertIsNone(result)
        self.assertEqual(self.client._stats["failures"], 1)


class TestCacheStats(unittest.TestCase):
    def test_stats_tracking(self):
        tmpdir = tempfile.mkdtemp()
        config = EssentiaConfig(
            cache_dir=f"{tmpdir}/cache",
            audio_cache_dir=f"{tmpdir}/audio",
        )
        client = EssentiaClient(config)

        stats = client.cache_stats()
        self.assertEqual(stats["cached_features"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["extractions"], 0)
        self.assertEqual(stats["failures"], 0)


class TestIsAvailable(unittest.TestCase):
    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", True)
    def test_available_when_installed(self):
        tmpdir = tempfile.mkdtemp()
        client = EssentiaClient(
            EssentiaConfig(
                cache_dir=f"{tmpdir}/cache",
                audio_cache_dir=f"{tmpdir}/audio",
            )
        )
        self.assertTrue(client.is_available)

    @patch("module3.essentia_client.ESSENTIA_AVAILABLE", False)
    def test_not_available_when_missing(self):
        tmpdir = tempfile.mkdtemp()
        client = EssentiaClient(
            EssentiaConfig(
                cache_dir=f"{tmpdir}/cache",
                audio_cache_dir=f"{tmpdir}/audio",
            )
        )
        self.assertFalse(client.is_available)


if __name__ == "__main__":
    unittest.main()
