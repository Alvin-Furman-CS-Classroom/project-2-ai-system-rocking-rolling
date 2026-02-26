# Module 3 Changelog

## 2026-02-26 (v1.2) — Proxy Pool Implementation

### New: Proxy Pool (`proxy_pool.py`)
- Solves the "zero LB neighbors" problem for mainstream tracks (e.g., Wannabe, Bohemian Rhapsody)
- Auto-growing pool of tracks known to have LB neighbors + features
- Seeded with 4 known-good tracks (Foo Fighters, Royal Blood, Florence + the Machine, Pink Floyd)
- `find_proxy()` scores target track against every pool entry using Module 1's 12-dimension compatibility
- `add_from_neighbors()` grows the pool automatically after each beam search
- Pool persisted at `~/.waveguide/proxy_pool.json`

### Updated: Playlist Assembler (`playlist_assembler.py`)
- Full proxy integration in the generate pipeline:
  1. Check if source/dest have LB neighbors
  2. Find proxies via `ProxyPool.find_proxy()` if not
  3. Run beam search between proxies
  4. Swap proxies back out — user's original songs stay at endpoints
  5. Re-score transitions with final track list
- Feature resolution fallback chain: AcousticBrainz → Essentia → MusicBrainz metadata
- Pool growth hook: discovered neighbors auto-added after search

### Tests — 94 total (was 80), all passing in ~5s
- **14 new proxy pool tests**: pool loading/saving, seed tracks, proxy discovery,
  pool growth from neighbors, compatibility scoring, exclude logic, persistence
- Full breakdown:
  - Explainer: 22
  - Constraints: 22
  - Essentia: 18
  - Proxy Pool: 14
  - User Model: 12
  - Assembler: 6

### Cross-module test totals: 179 (was 159)
- Module 1: 44 (scoring, knowledge base, MB/LB integration)
- Module 2: 41 (beam search, clients, LB neighbor algorithms)
- Module 3: 94 (assembly, constraints, essentia, proxy, user model, explainer)

---

## 2026-02-25 (v1.1) — Essentia Validation & No-Neighbor Strategy

### Validated: yt-dlp audio acquisition timing
- Tested yt-dlp download for "Wannabe" by Spice Girls: **~9 seconds** (search + download + convert to ogg, 4.2 MB)
- Estimated full Essentia pipeline per track: **~30-40 seconds** first time (yt-dlp + MusicExtractor), instant on cache hit
- Audio cached at `~/.waveguide/audio_cache/{mbid}.ogg`, features at `~/.waveguide/essentia_cache/{mbid}.json`

### Essentia output: what we get vs what's missing

| Dimension | Source | Status |
|-----------|--------|--------|
| Key | Essentia `tonal.key_edma` | Real data |
| Tempo | Essentia `rhythm.bpm` | Real data |
| Energy | Essentia `lowlevel.spectral_energyband_*` | Real data |
| Loudness | Essentia `lowlevel.average_loudness` | Real data |
| Timbre | Essentia `lowlevel.mfcc.mean` + cov | Real data |
| Mood | Needs TF classifier models | Falls back to 0.5 |
| Genre | Needs TF classifier models | Falls back to 0.5 |
| Tags | ListenBrainz API | Separate source |
| Popularity | ListenBrainz API | Weight 0.0 (disabled) |
| Artist | MusicBrainz API | Separate source |
| Era | MusicBrainz API | Separate source |
| MB Genre | MusicBrainz API | Separate source |

Current Essentia gives **5 of 12** dimensions with real audio data. TF classifiers (not yet wired) would add mood + genre for **7 of 12**. Remaining 5 come from APIs regardless.

### Design: Proxy Track Strategy (for tracks with 0 LB neighbors)

Tracks like Wannabe and Bohemian Rhapsody exist in MusicBrainz but have **zero** ListenBrainz neighbors (no edges in the similarity graph). Beam search cannot use them as source/dest. The decided strategy:

1. **Keep the user's chosen songs** in the playlist (never substitute them out)
2. **Extract features** for both songs via Essentia (yt-dlp + MusicExtractor)
3. **Find proxy tracks** — the most sonically similar tracks that DO have LB neighbors
4. **Run beam search** between the two proxies (fills in the middle of the playlist)
5. **Swap proxies back out** — user's songs stay at position 1 and last
6. **Re-score edge transitions** using Essentia-extracted features

```
User picks: Wannabe → Bohemian Rhapsody (both 0 LB neighbors)

Internal:
  Wannabe → [proxy A] ─── beam search ─── [proxy B] → Bohemian Rhapsody
                          (LB graph)

Final playlist:
  1. Wannabe              ← user's pick (kept)
  2. [from beam search]   ← found via proxy A's neighbors
  3. [from beam search]
  4. [from beam search]
  5. Bohemian Rhapsody     ← user's pick (kept)
```

Proxy discovery requires a **candidate pool** of tracks with known LB neighbors and features. Options: lazy collection (grows as system is used), seeded crawl from known working MBIDs, or genre-filtered MB search.

### Decision: Popularity dimension not worth pursuing
- `popularity_weight` already defaults to `0.0` (disabled)
- LB listen counts reflect LB's niche user base, not actual global popularity
- "Similar popularity" between tracks is the weakest signal for playlist quality
- Keep in codebase (zero cost), but not worth chasing better data

### Build changes
- `python-pptx` and `matplotlib` moved to optional dependencies: `uv sync --extra ppt`
- Presentation generation script: `build_ppt.py`

### Estimated pipeline timing (worst case: both tracks no LB, no AB)

| Phase | Time |
|-------|------|
| Essentia extraction x2 (parallel) | ~30-40s |
| Proxy discovery | ~0.1s |
| Beam search (~4 rounds) | ~50-100s |
| Feature resolution | ~5-10s |
| Constraints + explanation | <0.1s |
| **Total first run** | **~1.5-2.5 min** |
| **Cached/repeat run** | **~1-2 min** |

Bottleneck: MusicBrainz 1 req/sec rate limit during beam search expansion.

---

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
