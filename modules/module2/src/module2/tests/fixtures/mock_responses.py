"""Mock API responses for testing."""

# Sample ListenBrainz similar recordings response
SIMILAR_RECORDINGS_RESPONSE = [
    {
        "recording_mbid": "source-mbid-123",
        "similar_recordings": [
            {"recording_mbid": "similar-1", "score": 0.95},
            {"recording_mbid": "similar-2", "score": 0.88},
            {"recording_mbid": "similar-3", "score": 0.82},
            {"recording_mbid": "similar-4", "score": 0.75},
            {"recording_mbid": "similar-5", "score": 0.70},
        ],
    }
]

# Sample AcousticBrainz low-level response (simplified)
LOWLEVEL_RESPONSE = {
    "similar-1": {
        "0": {
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-1"],
                    "title": ["Similar Track 1"],
                    "artist": ["Test Artist"],
                }
            },
            "rhythm": {
                "bpm": 120.0,
                "onset_rate": 4.5,
                "beats_count": 240,
                "danceability": 0.75,
            },
            "tonal": {
                "key_key": "C",
                "key_scale": "major",
                "key_strength": 0.85,
                "tuning_frequency": 440.0,
            },
            "lowlevel": {
                "spectral_energyband_low": {"mean": 0.1},
                "spectral_energyband_middle_low": {"mean": 0.2},
                "spectral_energyband_middle_high": {"mean": 0.3},
                "spectral_energyband_high": {"mean": 0.15},
                "average_loudness": 0.8,
                "dynamic_complexity": 0.5,
                "mfcc": {
                    "mean": [0.0] * 13,
                    "cov": [[1.0 if i == j else 0.0 for j in range(13)] for i in range(13)],
                },
                "spectral_centroid": {"mean": 1500.0},
                "dissonance": {"mean": 0.3},
            },
        }
    },
    "similar-2": {
        "0": {
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-2"],
                    "title": ["Similar Track 2"],
                    "artist": ["Test Artist"],
                }
            },
            "rhythm": {
                "bpm": 125.0,
                "onset_rate": 4.8,
                "beats_count": 250,
                "danceability": 0.80,
            },
            "tonal": {
                "key_key": "G",
                "key_scale": "major",
                "key_strength": 0.82,
                "tuning_frequency": 440.0,
            },
            "lowlevel": {
                "spectral_energyband_low": {"mean": 0.12},
                "spectral_energyband_middle_low": {"mean": 0.22},
                "spectral_energyband_middle_high": {"mean": 0.32},
                "spectral_energyband_high": {"mean": 0.18},
                "average_loudness": 0.82,
                "dynamic_complexity": 0.55,
                "mfcc": {
                    "mean": [0.1] * 13,
                    "cov": [[1.0 if i == j else 0.0 for j in range(13)] for i in range(13)],
                },
                "spectral_centroid": {"mean": 1600.0},
                "dissonance": {"mean": 0.32},
            },
        }
    },
}

# Sample AcousticBrainz high-level response
HIGHLEVEL_RESPONSE = {
    "similar-1": {
        "0": {
            "highlevel": {
                "danceability": {"value": "danceable", "probability": 0.85},
                "mood_happy": {"value": "happy", "probability": 0.75},
                "mood_sad": {"value": "not_sad", "probability": 0.80},
                "mood_aggressive": {"value": "not_aggressive", "probability": 0.90},
                "mood_relaxed": {"value": "not_relaxed", "probability": 0.60},
                "mood_party": {"value": "party", "probability": 0.70},
                "mood_acoustic": {"value": "not_acoustic", "probability": 0.85},
                "timbre": {"value": "bright", "probability": 0.72},
                "genre_rosamerica": {
                    "value": "pop",
                    "probability": 0.65,
                    "all": {
                        "pop": 0.65,
                        "roc": 0.15,
                        "cla": 0.05,
                        "jaz": 0.05,
                        "dan": 0.05,
                        "hip": 0.02,
                        "rhy": 0.02,
                        "spe": 0.01,
                    },
                },
            },
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-1"],
                    "title": ["Similar Track 1"],
                    "artist": ["Test Artist"],
                }
            },
        }
    },
    "similar-2": {
        "0": {
            "highlevel": {
                "danceability": {"value": "danceable", "probability": 0.88},
                "mood_happy": {"value": "happy", "probability": 0.72},
                "mood_sad": {"value": "not_sad", "probability": 0.78},
                "mood_aggressive": {"value": "not_aggressive", "probability": 0.88},
                "mood_relaxed": {"value": "not_relaxed", "probability": 0.62},
                "mood_party": {"value": "party", "probability": 0.68},
                "mood_acoustic": {"value": "not_acoustic", "probability": 0.82},
                "timbre": {"value": "bright", "probability": 0.70},
                "genre_rosamerica": {
                    "value": "pop",
                    "probability": 0.60,
                    "all": {
                        "pop": 0.60,
                        "roc": 0.20,
                        "cla": 0.05,
                        "jaz": 0.05,
                        "dan": 0.05,
                        "hip": 0.02,
                        "rhy": 0.02,
                        "spe": 0.01,
                    },
                },
            },
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-2"],
                    "title": ["Similar Track 2"],
                    "artist": ["Test Artist"],
                }
            },
        }
    },
}
