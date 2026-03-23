"""Essentia audio feature extraction client.

Closes the AcousticBrainz gap by extracting equivalent audio features
locally using Essentia. When a track has an MBID but no AcousticBrainz
data, this client:

1. Acquires audio (from cache or via yt-dlp)
2. Extracts features using Essentia's MusicExtractor
3. Maps output to AcousticBrainz-compatible format
4. Feeds into Module 1's load_track_from_data() parser

Essentia (essentia-tensorflow) is an optional dependency. The client
gracefully degrades if Essentia is not installed.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from module1 import TrackFeatures
from module1.data_loader import load_track_from_data

logger = logging.getLogger(__name__)

# Guard Essentia import — it's an optional heavy dependency
try:
    import essentia.standard as es

    ESSENTIA_AVAILABLE = True
except ImportError:
    ESSENTIA_AVAILABLE = False


@dataclass
class EssentiaConfig:
    """Configuration for the Essentia client."""

    cache_dir: str = "~/.waveguide/essentia_cache"
    audio_cache_dir: str = "~/.waveguide/audio_cache"
    yt_dlp_path: str = "yt-dlp"
    max_audio_duration: int = 600  # seconds
    cleanup_audio: bool = True
    yt_dlp_timeout: int = 60  # seconds


class EssentiaClient:
    """Extract audio features using Essentia as a fallback for AcousticBrainz."""

    def __init__(self, config: EssentiaConfig | None = None):
        self.config = config or EssentiaConfig()
        self._cache_dir = Path(self.config.cache_dir).expanduser()
        self._audio_dir = Path(self.config.audio_cache_dir).expanduser()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"cache_hits": 0, "extractions": 0, "failures": 0}

    @property
    def is_available(self) -> bool:
        """Check if Essentia is installed and usable."""
        return ESSENTIA_AVAILABLE

    def fetch_features(
        self,
        mbid: str,
        title: str | None = None,
        artist: str | None = None,
    ) -> TrackFeatures | None:
        """Extract features for a track, using cache when available.

        Args:
            mbid: MusicBrainz recording ID
            title: Track title (for yt-dlp search if audio not cached)
            artist: Artist name (for yt-dlp search)

        Returns:
            TrackFeatures if extraction succeeds, None otherwise.
        """
        # Step 1: Check feature cache
        cached = self._load_cached_features(mbid)
        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached

        if not ESSENTIA_AVAILABLE:
            logger.warning(
                "Essentia not installed — cannot extract features for %s", mbid
            )
            self._stats["failures"] += 1
            return None

        # Step 2: Acquire audio
        audio_path = self._acquire_audio(mbid, title, artist)
        if audio_path is None:
            self._stats["failures"] += 1
            return None

        # Step 3: Extract features
        try:
            lowlevel, highlevel = self._extract_features(audio_path)
        except Exception:
            logger.exception("Essentia extraction failed for %s", mbid)
            self._stats["failures"] += 1
            return None

        # Step 4: Parse into TrackFeatures via Module 1
        try:
            features = load_track_from_data(lowlevel, highlevel)
            features.mbid = mbid
            if title:
                features.title = title
            if artist:
                features.artist = artist
        except Exception:
            logger.exception("Failed to parse Essentia output for %s", mbid)
            self._stats["failures"] += 1
            return None

        # Step 5: Cache the result
        self._save_cached_features(mbid, lowlevel, highlevel)
        self._stats["extractions"] += 1

        # Step 6: Cleanup audio if configured
        if self.config.cleanup_audio and audio_path.exists():
            audio_path.unlink()

        return features

    def _load_cached_features(self, mbid: str) -> TrackFeatures | None:
        """Load previously extracted features from cache."""
        cache_file = self._cache_dir / f"{mbid}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)
            return load_track_from_data(
                data.get("lowlevel", {}),
                data.get("highlevel", {}),
            )
        except Exception:
            logger.warning("Corrupt cache file for %s, removing", mbid)
            cache_file.unlink(missing_ok=True)
            return None

    def _save_cached_features(self, mbid: str, lowlevel: dict, highlevel: dict) -> None:
        """Save extracted features to cache."""
        cache_file = self._cache_dir / f"{mbid}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({"lowlevel": lowlevel, "highlevel": highlevel}, f)
        except Exception:
            logger.warning("Failed to cache features for %s", mbid)

    def _acquire_audio(
        self,
        mbid: str,
        title: str | None,
        artist: str | None,
    ) -> Path | None:
        """Get audio file for a track, downloading via yt-dlp if needed."""
        # Check audio cache
        for ext in ("ogg", "opus", "mp3", "m4a", "wav"):
            cached = self._audio_dir / f"{mbid}.{ext}"
            if cached.exists():
                return cached

        # Need title+artist for YouTube search
        if not title:
            logger.warning("No title for %s — cannot search YouTube", mbid)
            return None

        search_query = f"{artist} {title}" if artist else title
        output_template = str(self._audio_dir / f"{mbid}.%(ext)s")

        try:
            result = subprocess.run(
                [
                    self.config.yt_dlp_path,
                    "--extract-audio",
                    "--audio-format",
                    "vorbis",
                    "--audio-quality",
                    "5",
                    "--no-playlist",
                    "--max-downloads",
                    "1",
                    "-o",
                    output_template,
                    f"ytsearch1:{search_query}",
                ],
                capture_output=True,
                text=True,
                timeout=self.config.yt_dlp_timeout,
            )

            if result.returncode != 0:
                logger.warning(
                    "yt-dlp failed for '%s': %s",
                    search_query,
                    result.stderr[:200],
                )
                return None

        except FileNotFoundError:
            logger.warning("yt-dlp not found at '%s'", self.config.yt_dlp_path)
            return None
        except subprocess.TimeoutExpired:
            logger.warning("yt-dlp timed out for '%s'", search_query)
            return None

        # Find the downloaded file
        for ext in ("ogg", "opus", "mp3", "m4a", "wav"):
            downloaded = self._audio_dir / f"{mbid}.{ext}"
            if downloaded.exists():
                return downloaded

        logger.warning("yt-dlp completed but no audio file found for %s", mbid)
        return None

    def _extract_features(self, audio_path: Path) -> tuple[dict, dict]:
        """Extract features using Essentia's MusicExtractor.

        Returns (lowlevel_dict, highlevel_dict) in AcousticBrainz-compatible format.
        """
        if not ESSENTIA_AVAILABLE:
            raise RuntimeError("Essentia is not installed")

        # Run MusicExtractor
        extractor = es.MusicExtractor()
        features, frames = extractor(str(audio_path))

        # Map to AcousticBrainz format
        lowlevel = self._map_to_ab_lowlevel(features)
        highlevel = self._map_to_ab_highlevel(features)

        return lowlevel, highlevel

    def _map_to_ab_lowlevel(self, features) -> dict:
        """Map Essentia MusicExtractor output to AB lowlevel format.

        Essentia's MusicExtractor uses keys like:
          tonal.key_key, tonal.key_scale, tonal.key_strength
          rhythm.bpm, rhythm.onset_rate, rhythm.beats_count
          lowlevel.mfcc.mean, lowlevel.mfcc.cov
          lowlevel.spectral_energyband_low.mean
          lowlevel.average_loudness
          lowlevel.dynamic_complexity
          lowlevel.spectral_centroid.mean
          lowlevel.dissonance.mean
        """

        def _safe_get(key, default=None):
            try:
                val = features[key]
                # Convert numpy arrays to lists
                if hasattr(val, "tolist"):
                    return val.tolist()
                return val
            except (KeyError, RuntimeError):
                return default

        lowlevel = {
            "rhythm": {
                "bpm": _safe_get("rhythm.bpm", 0.0),
                "onset_rate": _safe_get("rhythm.onset_rate", 0.0),
                "beats_count": _safe_get("rhythm.beats_count", 0),
                "danceability": _safe_get("rhythm.danceability", None),
            },
            "tonal": {
                "key_key": _safe_get(
                    "tonal.key_edma.key", _safe_get("tonal.key_key", "C")
                ),
                "key_scale": _safe_get(
                    "tonal.key_edma.scale", _safe_get("tonal.key_scale", "major")
                ),
                "key_strength": _safe_get(
                    "tonal.key_edma.strength", _safe_get("tonal.key_strength", 0.0)
                ),
                "tuning_frequency": _safe_get("tonal.tuning_frequency", 440.0),
                "chords_strength": {
                    "mean": _safe_get("tonal.chords_strength.mean", 0.0)
                },
            },
            "lowlevel": {
                "spectral_energyband_low": {
                    "mean": _safe_get("lowlevel.spectral_energyband_low.mean", 0.0)
                },
                "spectral_energyband_middle_low": {
                    "mean": _safe_get(
                        "lowlevel.spectral_energyband_middle_low.mean", 0.0
                    )
                },
                "spectral_energyband_middle_high": {
                    "mean": _safe_get(
                        "lowlevel.spectral_energyband_middle_high.mean", 0.0
                    )
                },
                "spectral_energyband_high": {
                    "mean": _safe_get("lowlevel.spectral_energyband_high.mean", 0.0)
                },
                "average_loudness": _safe_get("lowlevel.average_loudness", None),
                "dynamic_complexity": _safe_get("lowlevel.dynamic_complexity", None),
                "mfcc": {
                    "mean": _safe_get("lowlevel.mfcc.mean", None),
                    "cov": _safe_get("lowlevel.mfcc.cov", None),
                },
                "spectral_centroid": {
                    "mean": _safe_get("lowlevel.spectral_centroid.mean", 0.0)
                },
                "dissonance": {"mean": _safe_get("lowlevel.dissonance.mean", 0.0)},
            },
        }

        return lowlevel

    def _map_to_ab_highlevel(self, features) -> dict:
        """Map Essentia MusicExtractor output to AB highlevel format.

        Note: MusicExtractor does NOT produce highlevel classifiers
        (mood, genre, timbre) by default — those require separate TF models.
        When we only have MusicExtractor output, the highlevel dict will
        be mostly empty, and Module 1 will use 0.5 neutral fallback for
        those dimensions. This is acceptable — we still get 5 low-level
        dimensions (key, tempo, energy, loudness, timbre/MFCC) which is
        better than zero.
        """
        return {"highlevel": {}}

    def cache_stats(self) -> dict[str, int]:
        """Return cache and extraction statistics."""
        cached_count = len(list(self._cache_dir.glob("*.json")))
        return {
            "cached_features": cached_count,
            **self._stats,
        }
