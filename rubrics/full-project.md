# Wave Guide — Full Project Code Review

**Review Date:** April 16, 2026
**Project:** Wave Guide — AI-Powered Music Playlist System
**Checkpoints Covered:** 1–5 (all modules + integration)
**Branch:** `presentation` (current)

---

## Summary

Wave Guide is an exceptional end-to-end AI system. Five modules form a coherent pipeline: Module 1 provides probabilistic music compatibility scoring via ProbLog; Module 2 discovers optimal paths using bidirectional beam search; Module 3 assembles playlists with CSP-style constraints and EMA user modeling; Module 4 classifies mood from 23-dimensional audio feature vectors using supervised learning; and the Flask API + React/p5.js presentation layer ties everything together in a live interactive demo. The codebase is consistently well-engineered — clean architecture, thorough testing (293+ passing tests across all modules), comprehensive documentation, and meaningful git history. Scores across all five checkpoints are near-perfect. Outstanding work throughout.

---

## Checkpoint Scores

| Checkpoint | Module | Score | Max |
|------------|--------|-------|-----|
| Checkpoint 1 | Module 1: Music Feature Knowledge Base | 46 | 50 |
| Checkpoint 2 | Module 2: Beam Search Playlist Path Finding | 50 | 50 |
| Checkpoint 3 | Module 3: Playlist Assembly & Constraint Satisfaction | 50 | 50 |
| Checkpoint 4 | Module 4: Mood Classification (Supervised Learning) | 49 | 50 |
| Checkpoint 5 | Integration, Demo & Presentation | 48 | 50 |
| **Total** | | **243** | **250** |

---

## Part 1: Source Code Review — All Modules

### 1.1 Functionality (8 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 8/8 | All compatibility features work correctly. Handles missing data, singular matrices, lowlevel-only tracks. |
| CP2 — Module 2 | 8/8 | Full beam search: unidirectional, bidirectional, multi-path. Handles disconnected graphs, cycle prevention, graceful degradation. |
| CP3 — Module 3 | 8/8 | Complete pipeline: beam search integration, 6 constraints, min-conflicts resolver, Essentia fallback, EMA user modeling, 3-level explanations. |
| CP4 — Module 4 | 8/8 | Full ML pipeline: 23-dim feature extraction, 3 model types with CV training, hyperparameter tuning, model persistence, centroid computation, 3-source data pipeline. |
| CP5 — Integration | 8/8 | Full demo loop: genre/artist selection, mood journey, curated track suggestions, live `/api/playlist` with beam search animation, results display. ETL pipeline + Flask API correct. |

**Section Total: 40/40**

---

### 1.2 Code Elegance & Quality (7 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 6/7 | Excellent structure. Minor: a couple helper functions reserved for future use. |
| CP2 — Module 2 | 7/7 | Exemplary. Protocol-based abstractions, immutable `SearchState.extend()`, 10-module separation, all functions under 30 lines. |
| CP3 — Module 3 | 7/7 | Exemplary. ABC for constraints, 7-module separation, DRY test helpers, TYPE_CHECKING guards for circular imports. |
| CP4 — Module 4 | 6/7 | Clean 5-module separation. Minor: some longer methods in `training_data.py` for DB loading (`load_from_db` ~130 lines). |
| CP5 — Integration | 6/7 | TypeScript: centralized types, well-extracted sub-components. Python: cleanly isolated pipeline steps. Minor: `DemoGenerating.tsx` `useEffect` dependency array underspecified; bare `except Exception: pass` silently drops errors. |

**Section Total: 32/35**

---

### 1.3 Documentation (4 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 4/4 | Comprehensive docstrings, README with algorithm citations, CHANGELOG. |
| CP2 — Module 2 | 4/4 | All 72 public items documented. CHANGELOG explains design decisions. USAGE.md with examples. |
| CP3 — Module 3 | 4/4 | Module/class docstrings, USAGE.md, CHANGELOG for v1 breakdown, inline comments for complex logic. |
| CP4 — Module 4 | 4/4 | Docstrings with Args/Returns. CHANGELOG with known limitations + improvement roadmap. USAGE.md for setup/training/usage. |
| CP5 — Integration | 4/4 | Exemplary module docstring in ETL script with pipeline description and copy-paste usage example. All functions documented. |

**Section Total: 20/20**

---

### 1.4 I/O Clarity (3 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 3/3 | `TrackFeatures` and `TransitionResult` dataclasses with full type hints. |
| CP2 — Module 2 | 3/3 | Clear `SearchState`, `PlaylistPath`, `SimilarRecording`. Config classes follow `{Service}Config` pattern. |
| CP3 — Module 3 | 3/3 | Rich dataclasses: `AssembledPlaylist`, `ConstraintResult`, `PlaylistExplanation`. `to_static_output()` for JSON serialization. |
| CP4 — Module 4 | 3/3 | `MoodLabel` enum, `TrainingExample`, `MoodClassification` (top-3 predictions), `EvalMetrics`. `FEATURE_NAMES`/`FEATURE_DIM` self-documenting. |
| CP5 — Integration | 3/3 | `demo-types.ts` centralizes all shared interfaces. API response shape matches TypeScript types exactly. `argparse` CLI self-documenting. |

**Section Total: 15/15**

---

### 1.5 Topic Engagement (5 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 5/5 | ProbLog for probabilistic inference, noisy-OR for mood aggregation, annotated disjunctions, research-grounded algorithms (Krumhansl-Kessler, Weber's law, Bhattacharyya distance). |
| CP2 — Module 2 | 5/5 | Bidirectional beam search addresses graph sparsity. A*-style heuristic using Module 1 transition cost. Multi-algorithm neighbor discovery improves coverage 50-80%. |
| CP3 — Module 3 | 5/5 | CSP with hard/soft constraints, min-conflicts local search. EMA learning with 12-dimension weight adaptation. Energy arc detection with 5 patterns. |
| CP4 — Module 4 | 5/5 | Stratified K-fold CV, soft-voting ensemble, GridSearchCV, music-aware normalization (BPM 50-220, spectral centroid 0-11025 Hz). Mood derivation with conflict-penalized scoring. |
| CP5 — Integration | 5/5 | p5.js beam search animation mirrors the algorithm. Demo flow encodes full AI pipeline. Cell capping shows dataset balance awareness. Compatibility arc visualizes transition probabilities. |

**Section Total: 25/25**

**Part 1 Subtotal: 132/135**

---

## Part 2: Testing Review — All Modules

### 2.1 Test Coverage & Design (6 pts per checkpoint)

| Checkpoint | Score | Tests | Justification |
|------------|-------|-------|---------------|
| CP1 — Module 1 | 5/6 | 6 | Good coverage: same-track, cross-genre, same-genre, lowlevel-only scenarios. Could add more edge cases. |
| CP2 — Module 2 | 6/6 | 41 | Covers beam search (uni/bi/multi-path), all 3 API clients, data models, edge cases. Mock-based. |
| CP3 — Module 3 | 6/6 | 80 | 5 test files covering all components: constraints (22), explainer (22), essentia (18), user model (12), assembler (6). |
| CP4 — Module 4 | 6/6 | ~140 | 3 test files. Accuracy threshold assertions (LR >70%, MLP >75%). Serialization roundtrips. Reproducibility checks. |
| CP5 — Integration | 6/6 | 26 | 12 Flask test-client tests (all 3 endpoints + error paths). 14 unit tests for ETL helpers. All passing. |

**Section Total: 29/30**

---

### 2.2 Test Quality & Correctness (5 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 4/5 | All 6 tests pass with meaningful scenarios. Assertions verify valid probability range. Could add expected-value ranges. |
| CP2 — Module 2 | 5/5 | Validates cost optimization, cycle prevention, beam width enforcement, target length, no-path scenarios. Passes in 0.28s. |
| CP3 — Module 3 | 5/5 | Specific behavior validation: case-insensitive matching, energy tolerance (15%), weight clamping, cache corruption cleanup. |
| CP4 — Module 4 | 5/5 | Feature range [0,1], mood label derivation rules, serialization roundtrip with precision checks, reproducibility with seeds. |
| CP5 — Integration | 5/5 | HTTP error codes by exception type, `beam_width`/`target_length` forwarded via `assert_called_once_with`, cell-cap invariant, `_rank` stripped. |

**Section Total: 24/25**

---

### 2.3 Test Documentation & Organization (4 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 4/4 | Clear test names describing scenarios. `_print_result` helper. Test fixtures in `test_files/`. |
| CP2 — Module 2 | 4/4 | Clear classes (TestSearchState, TestBeamSearch, TestBidirectionalBeamSearch). Fixtures in dedicated module. |
| CP3 — Module 3 | 4/4 | Descriptive names (`test_rising_satisfied`). DRY fixtures. Dedicated `mock_essentia.py`. |
| CP4 — Module 4 | 4/4 | Clear classes (TestTrainAccuracy, TestClassify, TestCentroid). Descriptive names. Reusable fixtures. |
| CP5 — Integration | 4/4 | Named classes per endpoint/function. Shared fixture helpers. Descriptive test names. |

**Section Total: 20/20**

**Part 2 Subtotal: 73/75**

---

## Part 3: GitHub Practices — All Checkpoints

### 3.1 Commit Quality & History (4 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 4/4 | Meaningful commits: "feat: v6, key, tempo, timbre research grounded". Iterative development visible. |
| CP2 — Module 2 | 4/4 | Clean progression: scaffold → full implementation → bug fixes → linting → Postgres integration. |
| CP3 — Module 3 | 4/4 | Iterative development from skeleton to production-ready. Conventional commit messages throughout. |
| CP4 — Module 4 | 4/4 | Clear progression: initial impl → DB pipeline → bug fixes (CV metrics). Conventional format. |
| CP5 — Integration | 4/4 | Conventional commit format throughout: `feat: add problog slide`, `fix(radar): add album art`. |

**Section Total: 20/20**

---

### 3.2 Collaboration Practices (4 pts per checkpoint)

| Checkpoint | Score | Justification |
|------------|-------|---------------|
| CP1 — Module 1 | 3/4 | PR #4 merged for web UI. Work distributed. Could add more visible code review comments. |
| CP2 — Module 2 | 4/4 | Feature branches (db-integration). Merge commits visible. PRs used for integration. Multiple contributors. |
| CP3 — Module 3 | 4/4 | Web UI on separate branches with merge commits. Multiple contributors. PRs for major integrations. |
| CP4 — Module 4 | 4/4 | Feature branch (module4-training-with-db). Merge from db-integration visible. Collaborative infrastructure sharing. |
| CP5 — Integration | 3/4 | Feature branch (`presentation`) for all demo work. Visible progression. Minor: no PR/code review visible in branch history. |

**Section Total: 18/20**

**Part 3 Subtotal: 38/40**

---

## Grand Total

| Part | Score | Max |
|------|-------|-----|
| Part 1: Source Code Review | 132 | 135 |
| Part 2: Testing Review | 73 | 75 |
| Part 3: GitHub Practices | 38 | 40 |
| **Total** | **243** | **250** |

---

## System Architecture

```
Presentation Layer (React + p5.js + Reveal.js)
    ↓ /api/playlist, /api/compare (HTTP, Vite proxy)
Flask API (modules/api/src/api/app.py)
    ├── AcousticBrainz API → load_track_from_data()     [Module 1]
    ├── KnowledgeBase.get_compatibility()                [Module 1]
    ├── BeamSearch / SearchSpace                         [Module 2]
    └── PlaylistAssembler (constraints + CSP)            [Module 3]

Offline Mood Classification
    └── MoodClassifier.classify_track()                  [Module 4]
         → curated_tracks.json (via generate_curated_tracks.py)

Data Sources
    ├── AcousticBrainz REST API (audio features)
    ├── ListenBrainz API (similar recordings)
    ├── MusicBrainz PostgreSQL (metadata, genres)
    └── Essentia (local audio fallback)
```

---

## Test Summary

| Module | Tests | Status |
|--------|-------|--------|
| Module 1 | 6 | All passing |
| Module 2 | 41 | All passing (0.28s) |
| Module 3 | 80 | All passing (2.85s) |
| Module 4 | ~140 | All passing |
| API (Flask) | 12 | All passing |
| ETL Scripts | 14 | All passing |
| **Total** | **~293+** | **All passing** |

---

## Open Action Items

From prior checkpoints, outstanding (non-blocking):

- [ ] Replace bare `except Exception: pass` at `scripts/generate_curated_tracks.py:205` with error counter
- [ ] Fix `useEffect` dependency array in `presentation/src/slides/DemoGenerating.tsx:53`
- [ ] Change argparse defaults for `--mb-password`/`--mb-user` to `None`
- [ ] Split `load_from_db` in `modules/module4/src/module4/training_data.py` into pipeline stages
- [ ] Split `_map_to_ab_lowlevel` in `modules/module3/src/module3/essentia_client.py` into helpers
- [ ] Add `ORDER BY RANDOM()` to Module 4 DB queries for unbiased sampling
