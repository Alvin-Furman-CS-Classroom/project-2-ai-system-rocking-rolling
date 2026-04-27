"""Training data loading and label derivation for mood classification."""

import json
import random
from pathlib import Path

import numpy as np
from module1.data_loader import load_track_from_data
from tqdm import tqdm

from .data_models import MoodLabel, TrainingExample
from .feature_engineering import FEATURE_DIM, extract_features

# Per-mood synthetic feature centroids (23-dim, all in [0, 1])
# Features: [bpm, e_low, e_mid_low, e_mid_high, e_high, loudness, dyn_complex,
#            dissonance, spec_centroid, onset_rate, mfcc_0..12]
_SYNTHETIC_CENTROIDS: dict[MoodLabel, list[float]] = {
    MoodLabel.CALM: [
        0.25,
        0.15,
        0.15,
        0.10,
        0.05,  # bpm, energy bands
        0.30,
        0.20,
        0.15,
        0.25,
        0.20,  # loudness, dyn, dissonance, centroid, onset
        0.30,
        0.50,
        0.55,
        0.50,
        0.55,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,  # mfcc 0-12
    ],
    MoodLabel.CHILL: [
        0.35,
        0.35,
        0.25,
        0.15,
        0.10,
        0.40,
        0.20,
        0.25,
        0.35,
        0.30,
        0.38,
        0.45,
        0.55,
        0.55,
        0.45,
        0.50,
        0.45,
        0.55,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
    ],
    MoodLabel.SAD: [
        0.18,
        0.20,
        0.15,
        0.10,
        0.05,
        0.25,
        0.15,
        0.70,
        0.20,
        0.15,
        0.22,
        0.35,
        0.45,
        0.65,
        0.45,
        0.45,
        0.45,
        0.45,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
    ],
    MoodLabel.HAPPY: [
        0.55,
        0.45,
        0.50,
        0.45,
        0.35,
        0.65,
        0.45,
        0.25,
        0.55,
        0.50,
        0.62,
        0.55,
        0.45,
        0.45,
        0.55,
        0.55,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
    ],
    MoodLabel.ENERGIZED: [
        0.75,
        0.65,
        0.65,
        0.65,
        0.55,
        0.75,
        0.55,
        0.35,
        0.70,
        0.70,
        0.75,
        0.55,
        0.45,
        0.45,
        0.55,
        0.50,
        0.55,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
    ],
    MoodLabel.INTENSE: [
        0.85,
        0.80,
        0.75,
        0.80,
        0.80,
        0.85,
        0.75,
        0.82,
        0.80,
        0.80,
        0.87,
        0.60,
        0.40,
        0.40,
        0.60,
        0.55,
        0.55,
        0.55,
        0.50,
        0.50,
        0.50,
        0.50,
        0.50,
    ],
}

# Per-feature standard deviations for synthetic data
_SYNTHETIC_STD = 0.08

# Default AcousticBrainz data directory (override with --data-dir CLI flag)
DATA_DIR = Path.home() / "Projects" / "metabrains-api" / "data"


def derive_mood_label(highlevel: dict) -> MoodLabel | None:
    """Apply rule-based mapping from AB mood probabilities to MoodLabel.

    Returns None if the track is ambiguous (no rule matches).
    Rules are checked in order; first match wins.
    """
    hl = highlevel.get("highlevel", {})

    def _prob(mood_key: str, class_name: str) -> float:
        mood = hl.get(mood_key, {})
        return float(mood.get("all", {}).get(class_name, 0.0))

    aggressive = _prob("mood_aggressive", "aggressive")
    sad = _prob("mood_sad", "sad")
    happy = _prob("mood_happy", "happy")
    party = _prob("mood_party", "party")
    relaxed = _prob("mood_relaxed", "relaxed")
    acoustic = _prob("mood_acoustic", "acoustic")

    # Soft-score each mood using conflict-penalised products of relevant probabilities.
    # This accepts tracks that would be rejected by hard thresholds while still
    # returning None for genuinely ambiguous cases.
    scores: dict[MoodLabel, float] = {
        MoodLabel.INTENSE:   aggressive * (1.0 - 0.5 * sad),
        MoodLabel.SAD:       sad * (1.0 - aggressive),
        MoodLabel.HAPPY:     happy * (1.0 - aggressive),
        MoodLabel.ENERGIZED: party * (1.0 - sad),
        MoodLabel.CALM:      relaxed * (1.0 - party) * (1.0 - acoustic),
        MoodLabel.CHILL:     relaxed * acoustic,
    }

    best_mood = max(scores, key=lambda m: scores[m])
    best_score = scores[best_mood]
    runner_up = sorted(scores.values(), reverse=True)[1]

    if best_score < 0.40 or (best_score - runner_up) < 0.10:
        return None
    return best_mood


def load_from_data_dir(
    data_dir: Path,
    max_per_class: int = 1000,
    random_seed: int = 42,
) -> list[TrainingExample]:
    """Load training examples from AcousticBrainz data directory.

    Scans highlevel/ directory, derives labels, loads paired lowlevel/ files,
    extracts features, and returns a balanced list of TrainingExamples.
    Stops each class once max_per_class is reached.
    """
    rng = random.Random(random_seed)

    highlevel_dir = data_dir / "highlevel"
    lowlevel_dir = data_dir / "lowlevel"

    if not highlevel_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {highlevel_dir}")

    # Collect all highlevel files and shuffle for random sampling
    all_hl_files = list(highlevel_dir.rglob("*-0.json"))
    rng.shuffle(all_hl_files)

    counts: dict[MoodLabel, int] = {m: 0 for m in MoodLabel}
    examples: list[TrainingExample] = []
    target_total = max_per_class * len(MoodLabel)

    with tqdm(total=target_total, desc="Loading examples", unit="ex") as pbar:
        for hl_path in all_hl_files:
            # Check if all classes are full
            if all(counts[m] >= max_per_class for m in MoodLabel):
                break

            try:
                with open(hl_path) as f:
                    highlevel = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            label = derive_mood_label(highlevel)
            if label is None:
                continue

            if counts[label] >= max_per_class:
                continue

            # Construct matching lowlevel path from highlevel path
            rel = hl_path.relative_to(highlevel_dir)
            ll_path = lowlevel_dir / rel
            if not ll_path.exists():
                continue

            try:
                with open(ll_path) as f:
                    lowlevel = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            try:
                track = load_track_from_data(lowlevel, highlevel)
                features = extract_features(track)
            except Exception:
                continue

            mbid = track.mbid
            examples.append(TrainingExample(features=features, label=label, mbid=mbid))
            counts[label] += 1
            pbar.update(1)
            pbar.set_postfix({m.value[:3]: counts[m] for m in MoodLabel})

    return examples


def generate_synthetic_data(
    n_per_class: int = 200,
    random_seed: int = 42,
) -> list[TrainingExample]:
    """Generate synthetic training data for unit testing (no file I/O).

    Uses Gaussian distributions around per-mood feature centroids.
    """
    rng = np.random.default_rng(random_seed)
    examples: list[TrainingExample] = []

    for mood, centroid in _SYNTHETIC_CENTROIDS.items():
        for _ in range(n_per_class):
            # Sample from Gaussian around centroid, clip to [0, 1]
            features = rng.normal(loc=centroid, scale=_SYNTHETIC_STD, size=FEATURE_DIM)
            features = np.clip(features, 0.0, 1.0).tolist()
            examples.append(TrainingExample(features=features, label=mood))

    return examples
