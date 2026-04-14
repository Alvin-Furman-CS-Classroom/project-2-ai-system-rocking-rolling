"""Feature extraction for mood classification.

Extracts a 23-dimensional normalized [0, 1] feature vector from a TrackFeatures object,
using only lowlevel audio descriptors (not AB mood classifiers).
"""

import math

from module1.data_models import TrackFeatures
from module1.rules_helpers import _log_normalize, _BAND_RANGES

from .data_models import MoodLabel

FEATURE_NAMES: list[str] = [
    "bpm",
    "energy_low",
    "energy_mid_low",
    "energy_mid_high",
    "energy_high",
    "average_loudness",
    "dynamic_complexity",
    "dissonance",
    "spectral_centroid",
    "onset_rate",
    "mfcc_0",
    "mfcc_1",
    "mfcc_2",
    "mfcc_3",
    "mfcc_4",
    "mfcc_5",
    "mfcc_6",
    "mfcc_7",
    "mfcc_8",
    "mfcc_9",
    "mfcc_10",
    "mfcc_11",
    "mfcc_12",
]

FEATURE_DIM = 23

# Normalization constants
_BPM_MIN = 50.0
_BPM_MAX = 220.0
_DYN_MAX = 10.0
_CENTROID_MAX = 11025.0
_ONSET_MAX = 30.0
_MFCC0_MIN = -800.0
_MFCC0_RANGE = 800.0
_MFCC_MIN = -200.0
_MFCC_RANGE = 400.0


def _clip01(val: float) -> float:
    return max(0.0, min(1.0, val))


def extract_features(track: TrackFeatures) -> list[float]:
    """Extract 23-dim normalized lowlevel feature vector. Missing values → 0.5."""
    features: list[float] = []

    # 0: BPM normalized to [50, 220]
    bpm = getattr(track, "bpm", None)
    if bpm is None or bpm == 0.0:
        features.append(0.5)
    else:
        features.append(_clip01((float(bpm) - _BPM_MIN) / (_BPM_MAX - _BPM_MIN)))

    # 1-4: Energy bands — log-normalized to [0, 1] using empirical AB ranges
    # (raw AB values are ~1e-5 to 0.1, so plain clip01 maps everything to ~0)
    for band_name, attr_name in [
        ("low", "energy_low"),
        ("mid_low", "energy_mid_low"),
        ("mid_high", "energy_mid_high"),
        ("high", "energy_high"),
    ]:
        val = getattr(track, attr_name, None)
        if val is None or val == 0.0:
            features.append(0.5)
        else:
            floor, ceiling = _BAND_RANGES[band_name]
            features.append(_clip01(_log_normalize(float(val), floor, ceiling)))

    # 5: average_loudness (AB stores as 0-1)
    loudness = track.average_loudness
    features.append(_clip01(float(loudness)) if loudness is not None else 0.5)

    # 6: dynamic_complexity (typical range 0-10)
    dyn = track.dynamic_complexity
    features.append(_clip01(float(dyn) / _DYN_MAX) if dyn is not None else 0.5)

    # 7: dissonance (AB stores as 0-1)
    diss = track.dissonance
    features.append(_clip01(float(diss)) if diss is not None else 0.5)

    # 8: spectral_centroid (Hz, normalize by Nyquist ~11025)
    centroid = track.spectral_centroid
    features.append(
        _clip01(float(centroid) / _CENTROID_MAX) if centroid is not None else 0.5
    )

    # 9: onset_rate (beats per second, typical 0-30)
    onset = getattr(track, "onset_rate", None)
    if onset is None or onset == 0.0:
        features.append(0.5)
    else:
        features.append(_clip01(float(onset) / _ONSET_MAX))

    # 10-22: MFCC[0:13] (13 coefficients)
    mfcc = track.mfcc
    if mfcc is None:
        features.extend([0.5] * 13)
    else:
        # mfcc[0]: energy term, range roughly -800 to 0
        mfcc0 = float(mfcc[0]) if len(mfcc) > 0 else None
        if mfcc0 is not None:
            features.append(_clip01((mfcc0 - _MFCC0_MIN) / _MFCC0_RANGE))
        else:
            features.append(0.5)
        # mfcc[1:13]: range roughly -200 to 200
        for i in range(1, 13):
            if i < len(mfcc):
                features.append(_clip01((float(mfcc[i]) - _MFCC_MIN) / _MFCC_RANGE))
            else:
                features.append(0.5)

    assert len(features) == FEATURE_DIM, (
        f"Expected {FEATURE_DIM} features, got {len(features)}"
    )
    return features


def features_to_track(
    vector: list[float], mood: MoodLabel | None = None
) -> TrackFeatures:
    """Reconstruct a minimal TrackFeatures from a 23-dim normalized vector.

    Used for centroid-based inverse mapping.
    """
    if len(vector) != FEATURE_DIM:
        raise ValueError(f"Expected {FEATURE_DIM}-dim vector, got {len(vector)}")

    # Denormalize BPM
    bpm = float(vector[0]) * (_BPM_MAX - _BPM_MIN) + _BPM_MIN

    # Denormalize dynamic_complexity
    dynamic_complexity = float(vector[6]) * _DYN_MAX

    # Denormalize spectral_centroid
    spectral_centroid = float(vector[8]) * _CENTROID_MAX

    # Denormalize onset_rate
    onset_rate = float(vector[9]) * _ONSET_MAX

    # Denormalize MFCC
    mfcc_out: list[float] = []
    mfcc0_denorm = float(vector[10]) * _MFCC0_RANGE + _MFCC0_MIN
    mfcc_out.append(mfcc0_denorm)
    for i in range(11, 23):
        mfcc_out.append(float(vector[i]) * _MFCC_RANGE + _MFCC_MIN)

    # Denormalize energy bands: invert log-normalization
    def _inv_log_normalize(norm_val: float, band: str) -> float:
        floor, ceiling = _BAND_RANGES[band]
        return math.exp(
            norm_val * (math.log(ceiling) - math.log(floor)) + math.log(floor)
        )

    return TrackFeatures(
        mbid=f"centroid_{mood.value}" if mood else "centroid",
        bpm=bpm,
        onset_rate=onset_rate,
        energy_low=_inv_log_normalize(float(vector[1]), "low"),
        energy_mid_low=_inv_log_normalize(float(vector[2]), "mid_low"),
        energy_mid_high=_inv_log_normalize(float(vector[3]), "mid_high"),
        energy_high=_inv_log_normalize(float(vector[4]), "high"),
        average_loudness=float(vector[5]),
        dynamic_complexity=dynamic_complexity,
        dissonance=float(vector[7]),
        spectral_centroid=spectral_centroid,
        mfcc=mfcc_out,
    )
