# Module 4: Mood Classification — Usage Guide

## Setup

```bash
uv lock --refresh && uv sync
```

## Training

### From Postgres + AcousticBrainz (recommended)

Uses real recordings from the MusicBrainz mirror, fetches audio features from AcousticBrainz, and maps genres to mood labels.

Requires `~/.pgpass` configured for the MusicBrainz Postgres mirror.

```bash
# Train both models with 200 examples per mood class (1,200 total)
uv run python -m module4.main --from-db --max-per-class 200 --model both

# Train only logistic regression, smaller dataset
uv run python -m module4.main --from-db --max-per-class 50 --model lr

# Train with hyperparameter tuning (GridSearchCV)
uv run python -m module4.main --from-db --max-per-class 200 --model both --tune
```

First run fetches from the API and saves a parquet cache at `modules/module4/data/training_examples.parquet`. Subsequent runs can load from parquet instantly.

### From synthetic data (no external deps)

Good for testing the pipeline without a database or API connection.

```bash
uv run python -m module4.main --synthetic --max-per-class 200 --model both
```

### From AcousticBrainz JSON files

If you have local AB data dumps:

```bash
export AB_DATA_DIR=/path/to/data  # must have highlevel/ and lowlevel/ subdirs
uv run python -m module4.main --data-dir $AB_DATA_DIR --max-per-class 500
```

### Default behavior

If no flag is given, tries Postgres first, falls back to synthetic:

```bash
uv run python -m module4.main
```

## Output

Training prints per-class metrics:

```
--- Logistic Regression (5-fold CV) ---
Test accuracy: 0.892, F1-macro: 0.887
              precision    recall       f1   support
  calm            0.91      0.88     0.89        40
  chill           0.85      0.82     0.84        40
  energized       0.92      0.95     0.93        40
  happy           0.87      0.85     0.86        40
  intense         0.95      0.97     0.96        40
  sad             0.83      0.85     0.84        40
```

Best model is saved to `modules/module4/models/mood_classifier.pkl`.

## Using a trained model

```python
from module4 import MoodClassifier, MoodLabel

# Load saved model
clf = MoodClassifier.load("modules/module4/models/mood_classifier.pkl")

# Classify a track (from Module 1's TrackFeatures)
result = clf.classify_track(track_features)
print(f"Mood: {result.mood.value}, confidence: {result.confidence:.2f}")
print(f"Top 3: {[(m.value, f'{p:.2f}') for m, p in result.top_3_moods]}")

# Get centroid track for mood-based playlist input
# (use as source/dest for Module 2's beam search)
calm_track = clf.get_centroid_track(MoodLabel.CALM)
energized_track = clf.get_centroid_track(MoodLabel.ENERGIZED)
```

## Parquet cache

After `--from-db` training, examples are cached at:

```
modules/module4/data/training_examples.parquet
```

Load directly in Python:

```python
from module4.training_data import load_from_parquet

examples = load_from_parquet()
print(f"Loaded {len(examples)} cached examples")
```

## Models

| Model | Flag | Notes |
|-------|------|-------|
| Logistic Regression | `--model lr` | Fast, interpretable, prints feature importance |
| MLP (256→128) | `--model mlp` | Better accuracy, slower to train |
| Both | `--model both` | Trains both, saves the best |
| Ensemble (LR+MLP) | `--model ensemble` | Soft voting, best accuracy |

## Tests

```bash
uv run python -m pytest modules/module4/ --tb=short -q
```

## Mood labels

| Mood | Example genres |
|------|---------------|
| Calm | classical, folk, new age, baroque |
| Chill | ambient, jazz, trip hop, lo-fi |
| Sad | blues, emo, gothic rock, dark ambient |
| Happy | pop, reggae, soul, k-pop |
| Energized | dance, techno, house, funk |
| Intense | metal, industrial, hardcore punk |
