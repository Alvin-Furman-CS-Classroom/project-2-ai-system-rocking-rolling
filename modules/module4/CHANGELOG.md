# Module 4 Changelog

## 2026-04-01 — DB Training Pipeline + Bug Fixes

### Fixed: Cross-validation per-class metrics were all zeros
- `_train_cv()` returned empty per-class precision/recall/f1 after CV
- Now evaluates on the refitted model to produce real per-class breakdown
- CV accuracy/F1-macro (reliable) are kept; per-class comes from full refit

### New: `load_from_db()` — real training data from Postgres + AcousticBrainz
- Queries the local MusicBrainz mirror for recordings with genre tags
- Maps 58 genres → 6 mood labels via `GENRE_TO_MOOD` dict
- Fetches AcousticBrainz audio features in batches of 25
- Extracts 23-dim feature vectors using `extract_features()`
- tqdm progress bars for genre query + feature extraction steps
- CLI: `uv run python -m module4.main --from-db --max-per-class 200`

### New: Parquet cache for training data
- `save_to_parquet()` / `load_from_parquet()` for fast reloading
- Saved to `modules/module4/data/training_examples.parquet`
- First `--from-db` run builds the cache; subsequent runs can reuse it

### Fixed: Hardcoded `DATA_DIR` path
- Was `~/Projects/metabrains-api/data` (Michael's local filesystem)
- Now reads from `AB_DATA_DIR` environment variable, no default path

### New: `--from-db`, `--synthetic`, `--data-dir` CLI flags
- Three mutually exclusive data sources
- Default: tries DB first, falls back to synthetic
- `--synthetic` works standalone with no external dependencies

### Added: module2 as dependency
- `load_from_db()` imports `MusicBrainzDB` and `AcousticBrainzClient`
- `pyproject.toml` now lists `module2` as workspace dependency

---

## Training Data Representativeness — Known Limitations

### What the current pipeline does NOT capture well

**Genre ≠ Mood.** The pipeline uses MusicBrainz genre tags as a proxy for mood labels. This introduces systematic label noise:
- A "blues" track is labeled "sad", but many blues tracks are upbeat
- "Pop" → "happy", but pop includes sad ballads, intense anthems, chill tracks
- "Jazz" → "chill", but free jazz and bebop are anything but chill

**Genre imbalance.** The MusicBrainz database has uneven genre coverage:
- "Rock" and "pop" have millions of tagged recordings
- "Slowcore", "funeral doom metal", "bossa nova" have hundreds
- Result: some mood classes draw from 1-2 dominant genres

**AB coverage gaps.** Not all MB recordings have AcousticBrainz features:
- AB archived in 2022 with ~2M recordings analyzed
- MB has 38M recordings — most won't have AB data
- The pipeline silently skips tracks without AB features, biasing toward well-covered genres

**No randomization in DB query.** The Postgres query returns deterministic results:
- `LIMIT N` without `ORDER BY RANDOM()` gives the same recordings every time
- Training set doesn't represent the full diversity within each genre

### What IS representative

- The **23-dim feature vector** is well-designed — uses real audio descriptors (BPM, energy bands, MFCC, loudness, etc.)
- The **model architecture** (LR + MLP) is appropriate for this feature space
- The **centroid-based inverse mapping** correctly reconstructs TrackFeatures from mood labels
- The **AB features themselves** are high-quality when available (extracted by Essentia)

### How to improve representativeness

1. **Use AB highlevel mood classifiers** instead of genre tags — AB has `mood_happy`, `mood_sad`, `mood_aggressive`, `mood_relaxed`, `mood_party` probabilities. These are direct mood signals, not genre proxies. The `derive_mood_label()` function already supports this path.

2. **Add `ORDER BY RANDOM()` to the DB query** — ensures genre diversity within each mood class.

3. **Increase `max_per_class` to 500-1000** — more data smooths out per-genre bias.

4. **Multi-label genre sampling** — instead of mapping one genre per recording, sample recordings that appear under multiple mood-relevant genres (e.g., a track tagged both "blues" and "rock" gives a more nuanced signal).

5. **Load the AB data dump into Postgres** — once available, eliminates the API bottleneck and gives access to the full ~2M recordings with features.

---

## 2026-03-31 (v1) — Core Implementation

### New: Mood Classifier (`mood_classifier.py`)
- Three model types: Logistic Regression, MLP (256→128), Ensemble (LR+MLP soft voting)
- 5-fold stratified cross-validation
- GridSearchCV hyperparameter tuning (`--tune`)
- Model persistence via pickle (save/load)
- `classify_track(TrackFeatures)` → `MoodClassification` (mood + confidence + top-3)
- `get_centroid_track(MoodLabel)` → `TrackFeatures` for mood-based playlist input

### New: Feature Engineering (`feature_engineering.py`)
- 23-dim normalized [0,1] feature vector from TrackFeatures
- BPM, 4 energy bands, loudness, dynamic complexity, dissonance, spectral centroid, onset rate, 13 MFCCs
- Music-aware normalization ranges (BPM 50-220, centroid 0-11025 Hz, etc.)
- Inverse mapping: `features_to_track()` for centroid reconstruction

### New: Training Data (`training_data.py`)
- `generate_synthetic_data()` — Gaussian around per-mood centroids
- `load_from_data_dir()` — loads from AB JSON files with rule-based mood derivation
- `derive_mood_label()` — soft-scored mapping from AB mood probabilities

### 6 Mood Labels
- Calm, Chill, Sad, Happy, Energized, Intense

### Tests
- `test_feature_engineering.py` — extraction, normalization, inverse mapping
- `test_mood_classifier.py` — train, classify, save/load, evaluate
- `test_training_data.py` — synthetic generation, label derivation
