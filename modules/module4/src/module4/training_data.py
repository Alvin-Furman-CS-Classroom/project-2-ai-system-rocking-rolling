"""Training data loading and label derivation for mood classification."""

import json
import os
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

# AcousticBrainz data directory — set via AB_DATA_DIR env var or --data-dir CLI flag
DATA_DIR = Path(os.environ.get("AB_DATA_DIR", ""))


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


# ---------------------------------------------------------------------------
# Genre → Mood mapping for building training labels from MusicBrainz tags
# ---------------------------------------------------------------------------

GENRE_TO_MOOD: dict[str, MoodLabel] = {
    # Intense — high energy, aggressive, heavy
    "metal": MoodLabel.INTENSE,
    "heavy metal": MoodLabel.INTENSE,
    "death metal": MoodLabel.INTENSE,
    "black metal": MoodLabel.INTENSE,
    "thrash metal": MoodLabel.INTENSE,
    "hardcore punk": MoodLabel.INTENSE,
    "grindcore": MoodLabel.INTENSE,
    "industrial": MoodLabel.INTENSE,
    "noise": MoodLabel.INTENSE,

    # Energized — upbeat, party, dance
    "dance": MoodLabel.ENERGIZED,
    "electronic": MoodLabel.ENERGIZED,
    "house": MoodLabel.ENERGIZED,
    "techno": MoodLabel.ENERGIZED,
    "drum and bass": MoodLabel.ENERGIZED,
    "trance": MoodLabel.ENERGIZED,
    "disco": MoodLabel.ENERGIZED,
    "funk": MoodLabel.ENERGIZED,
    "punk rock": MoodLabel.ENERGIZED,

    # Happy — bright, positive, uplifting
    "pop": MoodLabel.HAPPY,
    "pop rock": MoodLabel.HAPPY,
    "reggae": MoodLabel.HAPPY,
    "ska": MoodLabel.HAPPY,
    "soul": MoodLabel.HAPPY,
    "k-pop": MoodLabel.HAPPY,
    "gospel": MoodLabel.HAPPY,

    # Sad — melancholic, slow, emotional
    "blues": MoodLabel.SAD,
    "emo": MoodLabel.SAD,
    "gothic rock": MoodLabel.SAD,
    "slowcore": MoodLabel.SAD,
    "dark ambient": MoodLabel.SAD,
    "funeral doom metal": MoodLabel.SAD,

    # Calm — peaceful, acoustic, gentle
    "classical": MoodLabel.CALM,
    "baroque": MoodLabel.CALM,
    "chamber music": MoodLabel.CALM,
    "new age": MoodLabel.CALM,
    "meditation": MoodLabel.CALM,
    "folk": MoodLabel.CALM,

    # Chill — relaxed but with some groove
    "ambient": MoodLabel.CHILL,
    "chillout": MoodLabel.CHILL,
    "downtempo": MoodLabel.CHILL,
    "trip hop": MoodLabel.CHILL,
    "lo-fi": MoodLabel.CHILL,
    "jazz": MoodLabel.CHILL,
    "bossa nova": MoodLabel.CHILL,
    "lounge": MoodLabel.CHILL,
}


TRAINING_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def save_to_parquet(examples: list[TrainingExample], path: Path | None = None) -> Path:
    """Save training examples to a parquet file for fast reloading.

    Columns: mbid, label, f0, f1, ..., f22
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = path or (TRAINING_DATA_DIR / "training_examples.parquet")
    path.parent.mkdir(parents=True, exist_ok=True)

    mbids = [e.mbid or "" for e in examples]
    labels = [e.label.value for e in examples]
    feature_columns = {f"f{i}": [e.features[i] for e in examples] for i in range(FEATURE_DIM)}

    table = pa.table({"mbid": mbids, "label": labels, **feature_columns})
    pq.write_table(table, path)
    return path


def load_from_parquet(path: Path | None = None) -> list[TrainingExample]:
    """Load training examples from a parquet file."""
    import pyarrow.parquet as pq

    path = path or (TRAINING_DATA_DIR / "training_examples.parquet")
    if not path.exists():
        raise FileNotFoundError(f"No parquet file at {path}")

    table = pq.read_table(path)
    examples = []
    for row in range(table.num_rows):
        features = [float(table.column(f"f{i}")[row].as_py()) for i in range(FEATURE_DIM)]
        label = MoodLabel(table.column("label")[row].as_py())
        mbid = table.column("mbid")[row].as_py() or None
        examples.append(TrainingExample(features=features, label=label, mbid=mbid))

    return examples


def load_from_db(
    max_per_class: int = 200,
    random_seed: int = 42,
    save_parquet: bool = True,
) -> list[TrainingExample]:
    """Build real training data from Postgres (MusicBrainz) + AcousticBrainz API.

    Pipeline:
        1. Query Postgres for recordings with genre tags we can map to moods
        2. Fetch AcousticBrainz audio features for those recordings
        3. Extract 23-dim feature vectors
        4. Optionally save to parquet for fast reloading
        5. Return balanced list of TrainingExamples

    Requires:
        - MusicBrainz mirror accessible (via ~/.pgpass)
        - AcousticBrainz API reachable
    """
    import logging

    from module2.musicbrainz_db import MusicBrainzDB
    from module2.acousticbrainz_client import AcousticBrainzClient

    logger = logging.getLogger(__name__)

    db = MusicBrainzDB()
    ab = AcousticBrainzClient()

    # Step 1: Query recordings with genre tags, grouped by mood
    # We ask for more than max_per_class because not all will have AB data
    buffer_factor = 3
    mood_mbids: dict[MoodLabel, list[str]] = {m: [] for m in MoodLabel}

    print("Step 1/3: Querying Postgres for recordings with genre tags...")
    try:
        with db._pool.connection() as conn:
            genre_progress = tqdm(GENRE_TO_MOOD.items(), desc="Genres", unit="genre")
            for genre_name, mood in genre_progress:
                if len(mood_mbids[mood]) >= max_per_class * buffer_factor:
                    continue

                genre_progress.set_postfix(genre=genre_name, mood=mood.value)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT r.gid::text
                        FROM musicbrainz.recording_tag rt
                        JOIN musicbrainz.genre g ON rt.tag = g.id
                        JOIN musicbrainz.recording r ON rt.recording = r.id
                        WHERE g.name = %s
                        LIMIT %s
                        """,
                        (genre_name, max_per_class * buffer_factor),
                    )
                    for row in cur.fetchall():
                        if len(mood_mbids[mood]) < max_per_class * buffer_factor:
                            mood_mbids[mood].append(row[0])
    except Exception:
        logger.error("Failed to query Postgres for training data")
        db.close()
        ab.close()
        raise

    # Shuffle each mood's candidates
    rng = random.Random(random_seed)
    for mood in mood_mbids:
        rng.shuffle(mood_mbids[mood])

    total_candidates = sum(len(v) for v in mood_mbids.values())
    print(f"  Found {total_candidates} candidates across {len(MoodLabel)} moods")
    for mood in MoodLabel:
        print(f"    {mood.value:<12} {len(mood_mbids[mood])} candidates")

    # Step 2 & 3: Fetch AB features and extract training examples
    print("\nStep 2/3: Fetching AcousticBrainz features + extracting vectors...")
    examples: list[TrainingExample] = []
    counts: dict[MoodLabel, int] = {m: 0 for m in MoodLabel}
    target_total = max_per_class * len(MoodLabel)

    overall_progress = tqdm(total=target_total, desc="Training examples", unit="ex")

    for mood in MoodLabel:
        candidates = mood_mbids[mood]
        if not candidates:
            logger.warning("No candidates for mood: %s", mood.value)
            continue

        # Fetch in batches of 25 (AB batch limit)
        for i in range(0, len(candidates), 25):
            if counts[mood] >= max_per_class:
                break

            batch = candidates[i : i + 25]
            try:
                features_map = ab.fetch_features_batch(batch)
            except Exception:
                logger.warning("AB batch fetch failed, skipping %d MBIDs", len(batch))
                continue

            for mbid, track_features in features_map.items():
                if counts[mood] >= max_per_class:
                    break

                try:
                    feature_vector = extract_features(track_features)
                except Exception:
                    continue

                examples.append(
                    TrainingExample(features=feature_vector, label=mood, mbid=mbid)
                )
                counts[mood] += 1
                overall_progress.update(1)
                overall_progress.set_postfix(
                    {m.value[:3]: counts[m] for m in MoodLabel}
                )

    overall_progress.close()

    db.close()
    ab.close()

    print(f"\nBuilt {len(examples)} training examples:")
    for mood in MoodLabel:
        print(f"  {mood.value:<12} {counts[mood]}")

    # Step 3/3: Save to parquet for fast reloading
    if save_parquet and examples:
        print("\nStep 3/3: Saving to parquet...")
        parquet_path = save_to_parquet(examples)
        print(f"  Saved to {parquet_path}")

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
