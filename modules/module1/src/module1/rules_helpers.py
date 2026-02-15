"""Helper functions for music theory rules.

These functions are used internally by the MusicKnowledgeBase to compute
values that are then added as facts to ProbLog.
"""

import math

import numpy as np

# Krumhansl-Kessler key profiles (Cognitive Foundations of Musical Pitch, 1990)
# Probe-tone ratings measuring perceived fitness of each pitch class as tonic
# Index 0 = C, 1 = C#/Db, 2 = D, ..., 11 = B
KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Semitone offsets from C for each key name (used to rotate profiles)
KEY_SEMITONE_OFFSET = {
    "c": 0, "c_sharp": 1, "d_flat": 1, "d": 2, "d_sharp": 3, "e_flat": 3,
    "e": 4, "f": 5, "f_sharp": 6, "g_flat": 6, "g": 7, "g_sharp": 8,
    "a_flat": 8, "a": 9, "a_sharp": 10, "b_flat": 10, "b": 11,
}

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


def mfcc_distance(
    mfcc1: list[float] | None,
    mfcc2: list[float] | None,
    cov1: list[list[float]] | None = None,
    cov2: list[list[float]] | None = None,
) -> float | None:
    """
    Compute distance between two MFCC representations.

    When covariance matrices are available, uses Bhattacharyya distance to
    compare single-Gaussian models N(μ, Σ) — a distributional distance that
    accounts for both mean difference and timbral spread (Aucouturier 2002).
    Falls back to Euclidean distance on means when covariance is unavailable.

    Excludes c₀ (index 0) to avoid double-counting with loudness (Berenzweig 2004).

    Args:
        mfcc1: First MFCC mean vector
        mfcc2: Second MFCC mean vector
        cov1: First MFCC covariance matrix (13x13)
        cov2: Second MFCC covariance matrix (13x13)

    Returns:
        Distance value, or None if mean data is missing
    """
    if mfcc1 is None or mfcc2 is None:
        return None

    # Use coefficients 1-12 (skip c₀ which captures overall energy)
    n_coeffs = min(13, len(mfcc1), len(mfcc2))
    if n_coeffs <= 1:
        return None

    mu1 = np.array(mfcc1[1:n_coeffs])
    mu2 = np.array(mfcc2[1:n_coeffs])

    if cov1 is not None and cov2 is not None:
        return _bhattacharyya_distance(mu1, mu2, np.array(cov1), np.array(cov2), n_coeffs)

    # Fallback: Euclidean distance on means
    return float(np.linalg.norm(mu1 - mu2))


def _bhattacharyya_distance(
    mu1: np.ndarray,
    mu2: np.ndarray,
    cov1_full: np.ndarray,
    cov2_full: np.ndarray,
    n_coeffs: int,
) -> float:
    """
    Compute Bhattacharyya distance between two single-Gaussian MFCC models.

    D_B = (1/8)(μ₁-μ₂)ᵀ Σ_avg⁻¹ (μ₁-μ₂) + (1/2) ln(|Σ_avg| / √(|Σ₁||Σ₂|))

    The first term measures mean difference weighted by covariance.
    The second term measures how different the distribution shapes are.
    """
    # Extract submatrix: skip c₀ (row 0, col 0)
    S1 = cov1_full[1:n_coeffs, 1:n_coeffs]
    S2 = cov2_full[1:n_coeffs, 1:n_coeffs]

    # Regularize to avoid singular matrices
    eps = 1e-6
    dim = S1.shape[0]
    reg = eps * np.eye(dim)
    S1 = S1 + reg
    S2 = S2 + reg

    S_avg = (S1 + S2) / 2.0

    # Term 1: Mahalanobis-like distance on means
    diff = mu1 - mu2
    try:
        S_avg_inv = np.linalg.inv(S_avg)
    except np.linalg.LinAlgError:
        # If inversion fails, fall back to Euclidean
        return float(np.linalg.norm(diff))

    term1 = (1.0 / 8.0) * float(diff @ S_avg_inv @ diff)

    # Term 2: Distribution shape difference (using slogdet for stability)
    sign_avg, logdet_avg = np.linalg.slogdet(S_avg)
    sign1, logdet1 = np.linalg.slogdet(S1)
    sign2, logdet2 = np.linalg.slogdet(S2)

    # If any determinant is non-positive, skip term2
    if sign_avg > 0 and sign1 > 0 and sign2 > 0:
        term2 = 0.5 * (logdet_avg - 0.5 * (logdet1 + logdet2))
    else:
        term2 = 0.0

    return float(term1 + term2)


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


# ---------------------------------------------------------------------------
# Research-grounded compatibility probability functions (v6)
# ---------------------------------------------------------------------------


def _get_key_profile(key: str, scale: str) -> np.ndarray:
    """Get the Krumhansl-Kessler profile for a key, rotated to the correct tonic."""
    normalized = normalize_key(key)
    offset = KEY_SEMITONE_OFFSET.get(normalized, 0)
    base = KRUMHANSL_MAJOR if scale == "major" else KRUMHANSL_MINOR
    # Rotate so index 0 = the tonic
    rotated = base[-offset:] + base[:-offset] if offset > 0 else list(base)
    return np.array(rotated)


def key_compatibility_prob(key1: str, scale1: str, key2: str, scale2: str) -> float:
    """
    Compute key compatibility using Krumhansl-Kessler profile correlation.

    Based on "Cognitive Foundations of Musical Pitch" (Krumhansl, 1990).
    Inter-key similarity is the Pearson correlation between probe-tone profiles,
    mapped from [-1, 1] to [0, 1].
    """
    p1 = _get_key_profile(key1, scale1)
    p2 = _get_key_profile(key2, scale2)

    # Pearson correlation
    r = float(np.corrcoef(p1, p2)[0, 1])

    # Map r in [-1, 1] to probability in [0, 1]
    return (r + 1.0) / 2.0


def tempo_compatibility_prob(bpm1: float, bpm2: float) -> float:
    """
    Compute tempo compatibility using Weber's law Gaussian decay.

    Based on Drake & Botte (1993): JND for tempo ≈ 4% of reference BPM.
    Uses 3× JND as σ so that differences up to ~1 JND score ≈ 95%.
    Handles double-time/half-time relationships.
    """
    if bpm1 <= 0 or bpm2 <= 0:
        return 0.5

    avg = (bpm1 + bpm2) / 2.0

    # Relative differences: direct, double-time, half-time
    delta_direct = abs(bpm1 - bpm2) / avg
    delta_double = abs(bpm1 - 2.0 * bpm2) / ((bpm1 + 2.0 * bpm2) / 2.0)
    delta_half = abs(2.0 * bpm1 - bpm2) / ((2.0 * bpm1 + bpm2) / 2.0)

    delta = min(delta_direct, delta_double, delta_half)

    # Weber JND ≈ 4%, σ = 3 × JND = 0.12
    sigma = 0.12
    return math.exp(-(delta ** 2) / (2.0 * sigma ** 2))


def timbre_compatibility_prob(
    mfcc1: list[float] | None,
    mfcc2: list[float] | None,
    cov1: list[list[float]] | None = None,
    cov2: list[list[float]] | None = None,
) -> float:
    """
    Compute timbre compatibility as Bhattacharyya coefficient.

    BC = exp(-D_B) where D_B is the Bhattacharyya distance between
    single-Gaussian MFCC models (Aucouturier & Pachet, 2002).
    BC ∈ [0, 1] measures the overlap between two distributions.
    """
    d_b = mfcc_distance(mfcc1, mfcc2, cov1, cov2)
    if d_b is None:
        return 0.6  # neutral fallback for missing data
    return math.exp(-d_b)


def loudness_compatibility_prob(
    loud1: float | None,
    loud2: float | None,
) -> float:
    """
    Compute loudness compatibility using Gaussian decay.

    AcousticBrainz average_loudness is on a 0-1 scale.
    σ = 0.15 so that within-genre differences (~0.05) score ~95%
    and pop (0.77) vs classical (0.10) scores ~2%.
    """
    if loud1 is None or loud2 is None:
        return 0.7  # neutral fallback
    delta = abs(loud1 - loud2)
    sigma = 0.15
    return math.exp(-(delta ** 2) / (2.0 * sigma ** 2))


def energy_compatibility_prob(energy1: float, energy2: float) -> float:
    """
    Compute energy compatibility using Gaussian decay.

    AcousticBrainz spectral energy scores are typically 0.001-0.01.
    σ = 0.003 calibrated to actual data range.
    """
    delta = abs(energy1 - energy2)
    sigma = 0.003
    return math.exp(-(delta ** 2) / (2.0 * sigma ** 2))
