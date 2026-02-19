# Module 2 Changelog

## 2026-02-21 (v5) — Multi-Algorithm Neighbor Discovery

### Problem
We were querying a single ListenBrainz similarity algorithm (`session_based_days_7500`). Testing revealed that different algorithms return **partially overlapping neighbor sets** — for Florence + the Machine's "What Kind of Man":
- Each algorithm returns up to 100 neighbors
- Union across 4 algorithms = **179 unique MBIDs** (79% more)
- `days_7500` vs `days_9000`: only 72 overlap, **28 unique to each**

### Solution: query multiple algorithms, merge results
- New `get_similar_recordings_multi()` in `listenbrainz_client.py` queries 4 algorithms and deduplicates by MBID, keeping the highest similarity score per neighbor.
- `SimilarRecording` now has an `algorithm` field tracking which algorithm found each neighbor.
- `search_space.py` now uses `get_similar_recordings_multi()` instead of single-algorithm.
- `lookup.py` updated to show per-algorithm breakdown in `--check` output.

### Available algorithms (from [LB Spark jobs](https://github.com/metabrainz/listenbrainz-server))
| Algorithm | Lookback | Top-N filter | Contribution cap |
|---|---|---|---|
| `days_9000` | 24.6 years | No | 5 per user |
| `days_7500` | 20.5 years | No | 5 per user |
| `days_7500_top_n_1000` | 20.5 years | Top 1000 listeners | 5 per user |
| `days_7500_sqrt_top_n_1000` | 20.5 years | Top 1000 listeners | sqrt dampening |

### Caveat: doesn't help for songs with zero LB data
Wannabe by Spice Girls returns 0 results across ALL algorithms (including `days_9000` and MLHD endpoint). The sparsity for mainstream pop is a fundamental LB user-base issue, not an algorithm choice issue.

### Trade-off
4x more LB API calls per expansion step (~2s instead of ~0.5s). Acceptable because LB has no rate limit and the expanded search space significantly improves path-finding success.

## 2026-02-21 (v4) — Bidirectional Beam Search

### New: Bidirectional search (`find_path_bidirectional`)
- Expands from **both source and destination** simultaneously, meeting in the middle. Instead of source needing to traverse the full distance, each side only goes halfway.
- **How it works**: alternates forward and backward beam expansion rounds, checks for frontier overlap after each round, stitches best path at meeting node, re-scores full path in forward direction.
- **Asymmetric cost handling**: backward beam uses same expansion logic (costs are approximate for beam ranking), but the final stitched path is re-scored with correct forward-direction transition costs.
- **Target length splitting**: for `target_length=7`, each side aims for ~4 nodes. `fwd_target + bwd_target - 1 = target_length`.
- **Fallback**: if dest has no features or bidirectional finds nothing, falls back to unidirectional `find_path()`.
- **Now the default** in `main.py` CLI.

### Why bidirectional?
- ListenBrainz's similar-recordings graph is **very sparse** — most MBIDs have zero neighbors. Unidirectional search from source often hits dead ends before reaching destination.
- Bidirectional doubles the explored surface area: if each side explores N nodes, the chance of overlap is much higher than one side exploring 2N nodes in one direction.

### Tests
- 6 new tests: simple path, meets-in-middle, no-path, fallback, target-length, no-cycles.
- **41 total tests**, all passing in 0.28s.

## 2026-02-21 (v3) — Popularity Fix & Lookup Tool

### Bug fixes
- **ListenBrainz popularity payload fixed**: Was sending `[{"recording_mbid": "mbid1"}, ...]` (list of objects), but the API expects `{"recording_mbids": ["mbid1", ...]}` (single object with list). This caused HTTP 500 on every popularity call. Source: [ListenBrainz Popularity API docs](https://listenbrainz.readthedocs.io/en/latest/users/api/popularity.html).

### New: Lookup tool (`module2.lookup`)
- `--search "song name"`: Search MusicBrainz by name, show MBIDs, and check LB neighbor availability for top results.
- `--check <MBID>`: Check a specific MBID across all 3 APIs (MusicBrainz, ListenBrainz, AcousticBrainz).
- Supports Lucene search syntax: `--search '"Stairway to Heaven" AND artist:"Led Zeppelin"'`

### Observation — LB similar recordings is very sparse
- Most MBIDs (even famous songs like Bohemian Rhapsody) have **zero** LB neighbors.
- Only tracks with enough listening session data get indexed in the similarity graph.
- The lookup tool's `--search` command checks LB availability to help find usable MBIDs.
- Known working entry points: Pink Floyd "Lost Art of Conversation" (6 neighbors), Foo Fighters "Congregation" (59), Royal Blood "Little Monster" (89), Florence + the Machine "What Kind of Man" (100).

## 2026-02-21 — Known Limitations & Future Directions

### Data sparsity: two independent gaps

The system depends on **two independent data sources** for path finding, and each has coverage gaps:

1. **ListenBrainz similar-recordings graph** — needed for neighbor discovery (which tracks connect to which)
2. **AcousticBrainz features** — needed for transition scoring (how compatible are two tracks)

A track needs **both** to be fully usable. Missing either one limits functionality:

| Has LB neighbors? | Has AB features? | Status |
|---|---|---|
| Yes | Yes | Fully usable as source, dest, or intermediate |
| Yes | No | Can be discovered as neighbor, but can't score transitions (filtered out by `get_scoreable_neighbors`) |
| No | Yes | Can score transitions if reached, but can't be expanded (no neighbors = dead end) |
| No | No | Completely unusable (e.g., Wannabe by Spice Girls) |

### Why popular songs can have zero data

- **LB neighbors** are built from **ListenBrainz user listening sessions** — not global popularity. LB has a tiny user base (mostly open-source/music enthusiasts). Mainstream pop (Spice Girls, Taylor Swift) is underrepresented in LB sessions, so these tracks often have zero neighbors despite being globally famous.
- **AcousticBrainz** was **community-submitted** audio analysis — contributors ran Essentia on their local music files and uploaded results. Coverage is ~7M recordings, biased toward the contributor community's music taste. Archived in 2022, no new data.

### Tested examples

| Track | LB neighbors | AB data | Usable? |
|---|---|---|---|
| Wannabe — Spice Girls | 0 | No | No |
| Bohemian Rhapsody — Queen | 0 | Yes | No (no LB neighbors) |
| Stairway to Heaven — Led Zeppelin | 0 | Yes | No (no LB neighbors) |
| Lost Art of Conversation — Pink Floyd | 6 | Yes | Yes |
| Congregation — Foo Fighters | 59 | Yes | Yes |
| What Kind of Man — Florence + the Machine | 100 | Yes | Yes |

### Future: closing the AcousticBrainz gap with Essentia

AcousticBrainz was built on **[Essentia](https://essentia.upf.edu/)**, an open-source audio analysis library by MTG Barcelona. Essentia is **still actively maintained** (`pip install essentia-tensorflow`) and produces the **exact same JSON format** that AcousticBrainz stored. Module 1's `load_track_from_data()` already parses this format.

**Possible pipeline for tracks missing AB data:**

```
MBID → find audio file → run Essentia locally → parse into TrackFeatures
```

- **Step 1 (easy)**: `essentia.standard.MusicExtractor()` produces low-level features (BPM, key, MFCCs, spectral energy). Pre-trained TensorFlow models cover high-level classifiers (mood, genre, timbre, danceability). Output maps directly to our existing parser.
- **Step 2 (hard)**: No API gives audio from an MBID. Options:
  - **User's local files** tagged with MBIDs via MusicBrainz Picard (best option)
  - **YouTube via yt-dlp** (works but legally gray)
  - **Spotify 30s previews** (too short to be representative)
- **Step 3 (medium)**: Download the [AcousticBrainz data dump](https://acousticbrainz.org/download) (29.4M submissions, ~7M unique MBIDs). Index locally by MBID for offline lookups — removes dependency on archived API.

**Recommended rollout:**
1. **Now**: keep using AB API (works for ~7M recordings)
2. **Near-term**: download AB data dump for offline lookups (same coverage, no API dependency)
3. **Long-term**: Essentia pipeline for new/missing tracks (user provides audio)

### Future: closing the ListenBrainz gap

The LB neighbor gap is harder to close because similarity data requires **aggregate listening behavior** — it can't be computed locally from a single audio file. Options for Module 3:

- **Guided input**: search UI only suggests tracks with LB neighbor data
- **Proxy tracks**: when user picks a track with no LB data, suggest musically similar alternatives that DO have LB neighbors (using MB genre/era metadata to find matches)
- **Direct scoring fallback**: if both source and dest have AB features but no LB path exists, offer a direct Module 1 compatibility score instead of a multi-hop playlist

## 2026-02-20 (v2) — API Fixes & Batch Optimization

### Bug fixes
- **ListenBrainz similar-recordings endpoint fixed**: Old endpoint `POST /similar-recordings` returned 405 (Method Not Allowed). Updated to new endpoint `POST /similar-recordings/json` with `recording_mbids` (plural list) payload format. Updated default algorithm to `session_based_days_7500_session_300_contribution_5_threshold_15_limit_50_skip_30`.
- **Graceful error handling**: `get_similar_recordings()` no longer crashes on HTTP errors — logs a warning and returns empty list instead of raising `requests.exceptions.HTTPError`.
- **Response parsing updated**: New `/json` endpoint returns a flat list of recordings with integer scores (not nested under `similar_recordings` key). Scores are now normalized to 0-1 range by dividing by the max score in the batch.
- **Mock fixtures updated**: `SIMILAR_RECORDINGS_RESPONSE` now matches the real flat-list format from the `/json` endpoint.

### Performance optimization
- **MusicBrainz batch lookup via Lucene search** (25x speedup): Replaced sequential 1-req/sec individual lookups with a single Lucene search query using `rid:MBID1 OR rid:MBID2 OR ...` on the `/ws/2/recording` search endpoint. Fetches up to 25 recordings per request instead of 25 separate requests (25+ seconds → ~1 second). Falls back to individual lookups if the search fails. Added `_parse_recording_search()` to handle the slightly different search response format (`first-release-date` and `tags` instead of `releases[].date` and `genres`).
- **Source**: Lucene OR query approach discovered via [MusicBrainz API Search docs](https://musicbrainz.org/doc/MusicBrainz_API/Search) — the search index supports `rid` (recording ID) field queries with full Lucene syntax including OR operators.
- **Artist relationship lookups remain individual** (1 req/sec) — no batch endpoint exists, but caching by artist MBID minimizes redundant calls when multiple tracks share the same artist.

### API call count comparison (per expansion step, 6 neighbors)
| Before (v1) | After (v2) |
|---|---|
| LB similar: 1 call | LB similar: 1 call |
| AB batch: 2 calls | AB batch: 2 calls |
| LB tags: 1 call | LB tags: 1 call |
| LB popularity: 1 call | LB popularity: 1 call |
| **MB recordings: 6 calls (6s)** | **MB recordings: 1 call (~1s)** |
| MB artist rels: ~3 calls (3s) | MB artist rels: ~3 calls (3s) |
| **Total: ~14 calls, ~10s** | **Total: ~9 calls, ~5s** |

## 2026-02-20 (v1) — Core Implementation
- **Ported and updated** all existing code from `origin/module2` branch to `rahul` branch.
- **beam_search.py**: A*-style beam search with heap-based priority queue, cycle prevention, diversity filter (>50% different intermediate tracks for multi-path), `find_path()` and `find_paths_multi()`.
- **search_space.py**: Three-source enrichment pipeline. When neighbors are discovered, enriches in priority order: (1) AcousticBrainz batch → (2) ListenBrainz tags+popularity → (3) MusicBrainz recording metadata + artist relationships. Graceful degradation if any source fails.
- **listenbrainz_client.py**: Updated with two roles — neighborhood discovery via labs API `similar-recordings`, and track enrichment via main API (`/metadata/recording/` for tags, `/popularity/recording` for listen counts). Batch-capable for tags, sequential for popularity.
- **acousticbrainz_client.py**: Bulk fetch with 25 MBIDs/request, semicolon-separated. Combines low-level + high-level into `TrackFeatures` via Module 1's `load_track_from_data()`. Graceful handling of batch failures.
- **musicbrainz_client.py** (NEW): Fetches recording metadata (artist, release year, genres) and artist relationships. Caches by recording MBID and artist MBID to minimize API calls. Respects MB's 1 req/sec rate limit. Parses `artist-credit`, `releases` (earliest date), `genres`, and `relations` (artist-type only).
- **data_models.py**: `SimilarRecording`, `SearchState` (with path/cost/extend), `PlaylistPath` (with average_compatibility).
- **main.py**: CLI entry point with per-dimension breakdown in output.
- **Mock fixtures**: Based on real API responses captured from AcousticBrainz, ListenBrainz, and MusicBrainz (Pink Floyd data).
- **35 unit tests**, all passing in 0.38s:
  - 13 beam search tests (linear path, lowest cost, no cycles, target length, impossible paths, missing features, beam width pruning, playlist path properties)
  - 8 ListenBrainz tests (similar recordings, tags with artist fallback, popularity, 404 handling, empty inputs)
  - 5 AcousticBrainz tests (batch low/high-level, combined features, single fetch, not found)
  - 9 MusicBrainz tests (recording metadata, artist relationships, 404 handling, per-artist caching, cache stats)
- **API observation — LB similar recordings endpoint**: Algorithm names have changed since original implementation. Current valid algorithms include `session_based_days_7500_session_300_contribution_5_threshold_15_limit_50_skip_30_top_n_listeners_1000`. The endpoint also now uses `/similar-recordings/json` with `recording_mbids` (plural, list) instead of `recording_mbid` (singular string).
- **API observation — LB popularity endpoint**: POST to `/1/popularity/recording` returns 500 intermittently. May need retry logic or fallback.
- **API observation — AcousticBrainz still alive**: The archived API at `acousticbrainz.org/api/v1` still returns data for known recordings (tested with Pink Floyd MBID). Full low-level JSON response is ~50KB per recording.

## 2026-02-20 (v0) — Planning & Architecture Update
- **Updated proposal** (`plans/module2.md`) to reflect Module 1 v8's 12-dimension scoring across 3 data layers (AcousticBrainz content-based, ListenBrainz user-behavioral, MusicBrainz editorial).
- **Existing implementation** on `origin/module2` branch (commit d344c1c): beam search algorithm, search space manager, ListenBrainz similarity client, AcousticBrainz bulk client, data models, CLI entry point, and tests with mocks. ~2,000 lines across 15 files.
- **Identified gaps** between existing implementation and current Module 1:
  - Search space only enriches from AcousticBrainz — needs ListenBrainz tag/popularity enrichment and MusicBrainz artist/era/genre enrichment.
  - ListenBrainz client only does neighborhood discovery (similar recordings) — needs recording tag and popularity endpoints for track enrichment.
  - MusicBrainz client does not exist yet — needed for artist relationships, release year, curated genres.
  - AcousticBrainz client calls live API which is archived (2022) — may need data dump fallback.
- **Decision — Why ListenBrainz for neighborhood discovery (not MusicBrainz)?**: ListenBrainz similar recordings API returns behavioral similarity (users who listen to X also listen to Y) which captures cross-genre and cross-era connections that metadata alone misses. MusicBrainz has no similarity API — it's a metadata database, not a recommendation engine. AcousticBrainz had no similarity endpoint either. ListenBrainz is the only one of the three that provides "find me tracks similar to this one."
- **Decision — API speed comparison**: ListenBrainz labs API (similar recordings) is a single POST returning up to 100 results in one call. MusicBrainz API has no bulk recording endpoint and enforces strict 1 req/sec rate limiting — fetching metadata for 25 tracks takes ~25s. AcousticBrainz supports bulk (25 MBIDs per request) but requires 2 calls per batch (low-level + high-level) at ~1s each. For a neighborhood of 25 tracks: LB discovery takes ~0.5s, AB enrichment takes ~2s (1 batch), MB enrichment takes ~25s (individual calls). This is why LB is used for discovery (fast) and MB enrichment is deferred/lazy (slow but valuable).
- **Decision — Three-source enrichment order**: (1) AcousticBrainz first (batch, 7 dimensions, highest total weight), (2) ListenBrainz second (batch-capable, 2 dimensions), (3) MusicBrainz last (individual calls, 3 dimensions, lowest priority). This order reflects both API efficiency and scoring impact. MB is lazily loaded — beam search can proceed while MB data trickles in.
- **Decision — Graceful degradation strategy**: Module 1's 0.5 neutral fallback on missing data means Module 2 doesn't need all 3 sources to produce usable results. With only AB data: 7 active dimensions. With only LB+MB: 5 active dimensions (3 if popularity and MB genre are off by default). Auto-normalized weights ensure scores remain meaningful regardless of data availability.
