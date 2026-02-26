# Module 2: Beam Search Path Finding — Final State

## Module Overview

**Purpose:** Module 2 implements beam search to find optimal playlist paths from a source track to a destination track. It discovers intermediate waypoints by exploring neighborhoods of similar tracks from external APIs, enriches them with audio/behavioral/editorial metadata from 3 data sources, and uses Module 1's 12-dimension knowledge base to score transitions.

**Topics Covered:** Search Algorithms (Beam Search, A*-style Heuristics, Bidirectional Search), API Integration (REST Clients, Rate Limiting, Batch Processing, Lucene Search), Caching Strategies, Graph Exploration

**Integration Points:**
- **Module 1 (Knowledge Base):** Provides `get_penalty(track1, track2)` → `float [0.0, 1.0]` for path cost. Provides `get_compatibility(track1, track2)` → `TransitionResult` with 12-dimension breakdown.
- **Module 3 (Playlist Assembly & UI):** Consumes `PlaylistPath` output for final playlist construction and presentation.

---

## Status: COMPLETE (v5)

All planned functionality has been implemented and tested. The module is at v5 with 5 iterations of improvements.

### What Was Built

| File | Lines | Description |
|------|-------|-------------|
| `beam_search.py` | ~450 | A*-style beam search with bidirectional mode, cycle prevention, diversity filter |
| `search_space.py` | ~240 | Three-source enrichment pipeline, caching, scoring interface |
| `listenbrainz_client.py` | ~330 | Neighborhood discovery (4 algorithms, merged) + tag/popularity enrichment |
| `acousticbrainz_client.py` | ~140 | Batch audio feature fetching from archived API |
| `musicbrainz_client.py` | ~345 | Recording metadata (Lucene batch, 25x speedup) + artist relationship caching |
| `data_models.py` | ~60 | SimilarRecording, SearchState, PlaylistPath |
| `main.py` | ~120 | CLI entry point with bidirectional search as default |
| `lookup.py` | ~170 | MBID search tool + data availability checker |
| Tests | ~500 | 35+ tests (21 beam search, 14+ client), all passing in 0.28s |

### Version History

| Version | Date | Key Addition |
|---------|------|-------------|
| v1 | 2026-02-20 | Core: beam search, 3-source enrichment, 35 tests |
| v2 | 2026-02-20 | MusicBrainz Lucene batch (25x speedup), error handling |
| v3 | 2026-02-21 | LB popularity payload fix, lookup tool |
| v4 | 2026-02-21 | Bidirectional beam search (doubles explored surface) |
| v5 | 2026-02-21 | Multi-algorithm neighbor discovery (50-80% more neighbors) |

---

## Architecture

```
Input: source_mbid, dest_mbid, playlist_length, UserPreferences
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Module 2: Beam Search Engine                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BeamSearch.find_path_bidirectional()                               │
│    ├── Forward beam: expand from source                             │
│    ├── Backward beam: expand from destination                       │
│    ├── Check frontier overlap after each round                      │
│    ├── Stitch path at meeting node                                  │
│    └── Re-score full path in forward direction                      │
│                                                                     │
│  SearchSpace: Discover & Enrich Neighbors                           │
│    1. ListenBrainz Labs → get_similar_recordings_multi()            │
│       (4 algorithms, merge by MBID, keep highest score)             │
│    2. AcousticBrainz Batch → fetch_features_batch()                 │
│       (25 MBIDs/request, parse → TrackFeatures, 7 dimensions)      │
│    3. ListenBrainz Main → get_recording_tags/popularity()           │
│       (tags + listen counts, 2 dimensions)                          │
│    4. MusicBrainz Batch → get_recording_metadata_batch()            │
│       (Lucene OR search, 25x speedup, 3 dimensions)                │
│       + get_artist_relationships() (cached per artist)              │
│                                                                     │
│  Module 1 KB: get_penalty(track1, track2) → float [0.0, 1.0]      │
│    12 dimensions, auto-normalized weights, 0.5 neutral fallback     │
│                                                                     │
│  Output: PlaylistPath(mbids, total_cost, transitions)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Three-Layer Data Architecture (Implemented)

### Layer 1: Content-Based — AcousticBrainz (7 dimensions)
- **Client:** `acousticbrainz_client.py`
- **Batch:** 25 MBIDs/request, semicolon-separated
- **Dimensions:** key, tempo, energy, loudness, mood, timbre, genre (rosamerica)
- **Status:** Archived 2022, ~7M recordings. API still serves cached data.
- **Graceful degradation:** All 7 dimensions fall back to 0.5 when missing.

### Layer 2: User-Behavioral — ListenBrainz (2 dimensions)
- **Client:** `listenbrainz_client.py`
- **Dual role:** Neighborhood discovery (labs API) + enrichment (main API)
- **Dimensions:** tags (cosine similarity), popularity (log-Gaussian)
- **Multi-algorithm discovery:** Queries 4 algorithms, merges results (50-80% more neighbors)

### Layer 3: Editorial — MusicBrainz (3 dimensions)
- **Client:** `musicbrainz_client.py`
- **Batch optimization:** Lucene OR search for recording metadata (25x speedup)
- **Dimensions:** artist relationships (graph topology), era (Gaussian decay), MB genre (Jaccard)
- **Caching:** Per-artist relationship caching (many tracks share artists)

---

## Key Algorithms

### Bidirectional Beam Search (Default)
- Expands from both source and destination simultaneously
- Alternates forward/backward expansion rounds
- Checks frontier overlap after each round
- Stitches path at meeting node, re-scores in forward direction
- Falls back to unidirectional if destination lacks features
- **Why:** LB similarity graph is very sparse; bidirectional doubles explored surface area

### Multi-Algorithm Neighbor Discovery
- Queries 4 LB algorithms: `days_9000`, `days_7500`, `days_7500_top_n_1000`, `days_7500_sqrt_top_n_1000`
- Deduplicates by MBID, keeps highest similarity score per neighbor
- Florence + Machine "What Kind of Man": 179 unique neighbors vs 100 per algorithm
- **Trade-off:** 4x more LB API calls (~2s vs ~0.5s), acceptable for expanded search space

---

## Known Limitations & Lessons Learned

### Data Sparsity — The Fundamental Challenge

The system depends on two independent data sources, each with coverage gaps:

| Has LB Neighbors? | Has AB Features? | Status |
|---|---|---|
| Yes | Yes | Fully usable |
| Yes | No | Discoverable, can't score transitions |
| No | Yes | Can score if reached, but dead end (no neighbors) |
| No | No | Completely unusable |

**Most popular songs have zero LB data.** LB similarity is built from LB user listening sessions (small, niche user base), not global popularity. Spice Girls, Queen, Led Zeppelin → 0 neighbors.

**Known working entry points:**
- Pink Floyd "Lost Art of Conversation" — 6 LB neighbors
- Foo Fighters "Congregation" — 59 LB neighbors
- Royal Blood "Little Monster" — 89 LB neighbors
- Florence + Machine "What Kind of Man" — 100 LB neighbors

### AcousticBrainz Dependency Risk
- Archived 2022, API may go offline at any time
- **Mitigation path:** AcousticBrainz data dump (29.4M submissions) → local index → Essentia pipeline for new tracks
- Module 1's scoring functions are agnostic to data source (AB API vs dump vs Essentia)

### Performance Budget
| Step | Time |
|------|------|
| LB neighborhood (multi-algo) | ~2s per expansion |
| AB batch features | ~1s per batch |
| MB batch metadata (Lucene) | ~1s per batch |
| Module 1 scoring | <100ms per pair |
| **Typical end-to-end** | **~15-30s** |

---

## CLI Usage

```bash
# Find a playlist path
uv run python -m module2.main \
  --source 564ccd5c-c4d3-4752-9abf-c33bb085d6a5 \
  --dest 832b2377-74db-4fa7-99f3-1b8f9e654102 \
  --length 7 --beam-width 10

# Search for MBIDs
uv run python -m module2.lookup --search "Bohemian Rhapsody Queen"

# Check data availability
uv run python -m module2.lookup --check 564ccd5c-c4d3-4752-9abf-c33bb085d6a5
```

---

## Dependencies

```toml
[project]
dependencies = ["module1", "requests>=2.31.0"]
```

---

## Success Criteria — All Met

- [x] Beam search finds paths between tracks with available data
- [x] Bidirectional search doubles explored surface area
- [x] Multi-algorithm discovery expands neighbor set by 50-80%
- [x] Tracks enriched from all 3 data sources (AB + LB + MB)
- [x] All 12 Module 1 dimensions populated when data is available
- [x] Missing data handled gracefully (0.5 neutral fallback)
- [x] Rate limiting respected on all 3 APIs
- [x] MusicBrainz Lucene batch (25x speedup over individual calls)
- [x] Per-artist relationship caching prevents redundant calls
- [x] 35+ unit tests passing in 0.28s
- [x] CLI produces output with path and per-transition scores
- [x] Lookup tool for finding usable MBIDs and checking data availability

---

## Open Issues for Module 3

These are not Module 2 bugs — they are architectural realities that Module 3 must handle:

1. **Input validation:** Users will pick songs with no LB/AB data. Module 3 needs guided input or proxy track suggestions.
2. **Failure UX:** Beam search can return `None` if no path exists. Module 3 needs graceful failure messaging.
3. **Direct scoring fallback:** If both tracks have AB features but no LB path, offer a direct Module 1 compatibility score instead of a multi-hop playlist.
4. **Workspace dependency:** `module1` import requires proper `uv sync` workspace setup. Tests fail without it.
