# Module 3 Changelog

## 2026-02-25 (v1) — Core Implementation

### New: Playlist Assembler (`playlist_assembler.py`)
- Full pipeline orchestrator: beam search → feature resolution → constraints → explanation
- Integrates all components: Module 1 (scoring), Module 2 (path finding), Essentia (fallback), user model, constraints
- CLI entry point (`main.py`) with `--json` output mode and `--no-essentia` flag
- `AssembledPlaylist.to_static_output()` for JSON-serializable playlist output

### New: Essentia Audio Analysis Pipeline (`essentia_client.py`)
- Closes the AcousticBrainz gap: when AB data is missing, extract equivalent features locally using Essentia
- Three-step pipeline: audio acquisition (yt-dlp) → feature extraction (MusicExtractor) → AB-format mapping
- `_map_to_ab_lowlevel()` maps Essentia output to AcousticBrainz-compatible dict format that feeds directly into Module 1's `load_track_from_data()`
- Feature caching at `~/.waveguide/essentia_cache/{mbid}.json`
- Audio caching at `~/.waveguide/audio_cache/{mbid}.ogg`
- `essentia-tensorflow` is optional — client gracefully degrades with `ESSENTIA_AVAILABLE` guard
- `yt-dlp` invoked as subprocess with timeout, search query built from MusicBrainz title+artist

### New: CSP-style Constraint Satisfaction (`constraints.py`)
- **Hard constraints** (violations trigger track replacement):
  - `NoRepeatArtists` — case-insensitive, uses artist_mbid when available
  - `NoRepeatedTracks` — belt-and-suspenders MBID dedup
- **Soft constraints** (penalize violations):
  - `EnergyArcConstraint` — supports "rising", "falling", "valley", "hill", "flat" target arcs
  - `GenreVarietyConstraint` — no more than N consecutive same-genre tracks
  - `TempoSmoothnessConstraint` — BPM jumps within configurable threshold
  - `MoodCoherenceConstraint` — detects A→B→A mood oscillation patterns
- `resolve_constraints()` uses min-conflicts local search: find violations, try alternative tracks from SearchSpace, accept swaps within 20% cost threshold
- Educational mapping: variables = track positions, domains = candidate tracks, resolution = min-conflicts heuristic

### New: User Preference Learning (`user_model.py`)
- Exponential moving average on dimension weights from playlist feedback
- Learning rule: agreement = 1 - |normalized_rating - dim_score|, then blend old and new weight
- `UserProfile` persistence as JSON at `~/.waveguide/user_profile.json`
- `to_user_preferences()` converts learned profile to Module 1's `UserPreferences`
- Cold start: defaults to Module 1's default weights
- History capped at 100 feedback entries

### New: Explanation & Transparency (`explainer.py`)
- Three levels of explanation:
  1. **Playlist summary**: "A journey through roc → pop → dan, building energy across 7 tracks (avg compatibility: 78%)"
  2. **Per-transition**: top 3 and bottom 2 weighted dimension contributors with human-readable descriptions
  3. **Constraint notes**: which constraints were satisfied/violated
- `detect_energy_arc()`: classifies playlist energy as rising/falling/valley/hill/steady
- `detect_genre_journey()`: ordered list of unique consecutive genres
- `get_top_contributors()`: sorts dimensions by weighted contribution (score × weight)

### Tests
- **80 tests total**, all passing in 2.85s:
  - 22 explainer tests (top contributors, energy arc detection, genre journey, summary, full explanation)
  - 22 constraint tests (6 constraint types, evaluation, resolution)
  - 18 Essentia tests (caching, yt-dlp subprocess, format mapping, full pipeline, availability)
  - 12 user model tests (weight updates, learning rate, persistence, conversion)
  - 6 assembler tests (full pipeline, no-path, user profile, static output, feedback)
- All tests run without Essentia installed (mocked)

### Architecture

```
PlaylistAssembler.generate_playlist(source, dest)
  │
  ├── 1. Apply UserProfile → UserPreferences
  ├── 2. BeamSearch.find_path_bidirectional()  [Module 2]
  ├── 3. Resolve features (SearchSpace → Essentia fallback)
  ├── 4. resolve_constraints() [CSP local search]
  ├── 5. explain_playlist() [3-level explanations]
  └── 6. Return AssembledPlaylist
```

### Dependencies
- `module1` (workspace): scoring, TrackFeatures, UserPreferences
- `module2` (workspace): BeamSearch, SearchSpace, PlaylistPath
- `requests`: HTTP client
- `essentia-tensorflow` (optional): audio feature extraction
- `yt-dlp` (optional, subprocess): audio acquisition
