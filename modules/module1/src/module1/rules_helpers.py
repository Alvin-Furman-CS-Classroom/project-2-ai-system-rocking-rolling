"""Helper functions for music theory rules.

These functions are used internally by the MusicKnowledgeBase to compute
values that are then added as facts to ProbLog.
"""

import numpy as np

# Circle of fifths in order (normalized to lowercase with underscores)
CIRCLE_OF_FIFTHS = [
    "c",
    "g",
    "d",
    "a",
    "e",
    "b",
    "f_sharp",
    "d_flat",
    "a_flat",
    "e_flat",
    "b_flat",
    "f",
]

# Enharmonic equivalents mapping
ENHARMONIC_MAP = {
    "g_flat": "f_sharp",
    "c_sharp": "d_flat",
    "g_sharp": "a_flat",
    "d_sharp": "e_flat",
    "a_sharp": "b_flat",
    # Handle uppercase and different formats
    "Gb": "f_sharp",
    "C#": "d_flat",
    "G#": "a_flat",
    "D#": "e_flat",
    "A#": "b_flat",
    "F#": "f_sharp",
    "Db": "d_flat",
    "Ab": "a_flat",
    "Eb": "e_flat",
    "Bb": "b_flat",
}


def normalize_key(key: str) -> str:
    """
    Normalize a key name to lowercase with underscores for ProbLog.

    Examples:
        "C#" -> "c_sharp"
        "Gb" -> "f_sharp" (enharmonic equivalent)
        "C" -> "c"
    """
    # First check enharmonic map
    if key in ENHARMONIC_MAP:
        return ENHARMONIC_MAP[key]

    # Convert to lowercase and replace # with _sharp
    normalized = key.lower().replace("#", "_sharp").replace("b", "_flat")

    # Handle edge case: 'b' note should stay as 'b', not 'b_flat'
    if normalized == "_flat":
        normalized = "b"

    # Check enharmonic again
    if normalized in ENHARMONIC_MAP:
        return ENHARMONIC_MAP[normalized]

    return normalized


def circle_of_fifths_distance(key1: str, key2: str) -> int:
    """
    Calculate the minimum distance between two keys on the circle of fifths.

    Args:
        key1: First key (e.g., "C", "C#", "Db")
        key2: Second key

    Returns:
        Distance from 0 (same key) to 6 (tritone/opposite)
    """
    k1 = normalize_key(key1)
    k2 = normalize_key(key2)

    try:
        idx1 = CIRCLE_OF_FIFTHS.index(k1)
        idx2 = CIRCLE_OF_FIFTHS.index(k2)
    except ValueError:
        # Unknown key, return maximum distance
        return 6

    # Calculate circular distance (shortest path around circle)
    forward = (idx2 - idx1) % 12
    backward = (idx1 - idx2) % 12
    return min(forward, backward)


def is_double_time(bpm1: float, bpm2: float, tolerance: float = 5.0) -> bool:
    """
    Check if two BPMs are in a 2:1 or 1:2 ratio (double-time/half-time).

    Args:
        bpm1: First BPM
        bpm2: Second BPM
        tolerance: Allowed deviation in BPM

    Returns:
        True if the BPMs are in a double-time relationship
    """
    if bpm2 == 0 or bpm1 == 0:
        return False

    ratio = bpm1 / bpm2

    # Check for 2:1 ratio
    if abs(ratio - 2.0) < tolerance / bpm2:
        return True

    # Check for 1:2 ratio
    if abs(ratio - 0.5) < tolerance / bpm1:
        return True

    return False


def mfcc_distance(mfcc1: list[float] | None, mfcc2: list[float] | None) -> float | None:
    """
    Compute Euclidean distance between two MFCC vectors.

    Excludes c₀ (index 0) which captures overall energy/loudness,
    to avoid double-counting with the loudness component (Berenzweig 2004).

    Args:
        mfcc1: First MFCC vector (typically 13-40 dimensions)
        mfcc2: Second MFCC vector

    Returns:
        Euclidean distance, or None if either input is None
    """
    if mfcc1 is None or mfcc2 is None:
        return None

    # Use coefficients 1-12 (skip c₀ which captures overall energy)
    n_coeffs = min(13, len(mfcc1), len(mfcc2))
    if n_coeffs <= 1:
        return None

    arr1 = np.array(mfcc1[1:n_coeffs])
    arr2 = np.array(mfcc2[1:n_coeffs])

    return float(np.linalg.norm(arr1 - arr2))


def compute_energy_score(
    energy_low: float,
    energy_mid_low: float,
    energy_mid_high: float,
    energy_high: float,
) -> float:
    """
    Compute weighted energy score from spectral energy bands.

    Args:
        energy_low: Low frequency band energy
        energy_mid_low: Mid-low frequency band energy
        energy_mid_high: Mid-high frequency band energy
        energy_high: High frequency band energy

    Returns:
        Weighted energy score
    """
    return (
        0.1 * energy_low
        + 0.2 * energy_mid_low
        + 0.4 * energy_mid_high
        + 0.3 * energy_high
    )


def derive_mood_from_features(
    energy_score: float,
    danceability: float,
    dissonance: float | None,
) -> str:
    """
    Derive a mood classification from lowlevel features when highlevel is unavailable.

    Args:
        energy_score: Computed energy score (0-1)
        danceability: Danceability score (0-1)
        dissonance: Dissonance value (0-1) or None

    Returns:
        Derived mood string: "energetic", "calm", "intense", or "neutral"
    """
    if energy_score > 0.7 and danceability > 0.6:
        return "energetic"
    elif energy_score < 0.3 and (dissonance is None or dissonance < 0.3):
        return "calm"
    elif dissonance is not None and dissonance > 0.6:
        return "intense"
    else:
        return "neutral"
