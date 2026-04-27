"""Mock Essentia output data for testing.

These fixtures simulate what Essentia's MusicExtractor would produce
from a real audio file, mapped to AcousticBrainz-compatible format.
"""

# Pre-mapped lowlevel dict (as if _map_to_ab_lowlevel already ran)
MOCK_LOWLEVEL = {
    "rhythm": {
        "bpm": 128.5,
        "onset_rate": 4.2,
        "beats_count": 256,
        "danceability": 0.75,
    },
    "tonal": {
        "key_key": "A",
        "key_scale": "minor",
        "key_strength": 0.82,
        "tuning_frequency": 440.0,
        "chords_strength": {"mean": 0.45},
    },
    "lowlevel": {
        "spectral_energyband_low": {"mean": 0.0012},
        "spectral_energyband_middle_low": {"mean": 0.0034},
        "spectral_energyband_middle_high": {"mean": 0.0056},
        "spectral_energyband_high": {"mean": 0.0023},
        "average_loudness": 0.65,
        "dynamic_complexity": 3.2,
        "mfcc": {
            "mean": [
                -600.0,
                120.5,
                30.2,
                -15.8,
                8.4,
                -3.2,
                5.1,
                -2.0,
                3.5,
                -1.8,
                2.1,
                -0.9,
                1.5,
            ],
            "cov": [[1.0] * 13 for _ in range(13)],
        },
        "spectral_centroid": {"mean": 1850.3},
        "dissonance": {"mean": 0.42},
    },
}

# Highlevel dict — empty since MusicExtractor doesn't produce classifiers
MOCK_HIGHLEVEL = {"highlevel": {}}

# Complete cached feature file content
MOCK_CACHED_FEATURES = {
    "lowlevel": MOCK_LOWLEVEL,
    "highlevel": MOCK_HIGHLEVEL,
}
