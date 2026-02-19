"""
UNIT TESTS EXECUTION SUMMARY
Music Knowledge Base - Compatibility Metric Tests

==============================================================================
TEST RESULTS OVERVIEW (v8 — MusicBrainz Integration)
==============================================================================

All 44 pytest tests pass across 3 test files.

Test suite covers:
- Core compatibility metric (6 tests — test_main.py)
- ListenBrainz tag compatibility (6 tests — test_listenbrainz.py)
- ListenBrainz popularity compatibility (6 tests — test_listenbrainz.py)
- Knowledge base integration with ListenBrainz (5 tests — test_listenbrainz.py)
- MusicBrainz artist compatibility (5 tests — test_musicbrainz.py)
- MusicBrainz era compatibility (6 tests — test_musicbrainz.py)
- MusicBrainz genre compatibility (6 tests — test_musicbrainz.py)
- Knowledge base integration with MusicBrainz (4 tests — test_musicbrainz.py)

Additionally, 9 manual scenario tests exist in unit_tests.py (not pytest-collected).

==============================================================================
PYTEST RESULTS — test_main.py (6 tests)
==============================================================================

test_main                           PASSED  — end-to-end demo runs without error
test_cindy_lauper_vs_pink_floyd     PASSED  — pop vs rock compatibility
test_cindy_lauper_vs_beethoven      PASSED  — pop vs classical compatibility
test_beethoven_vs_beethoven         PASSED  — same-genre classical compatibility
test_beethoven_lowlevel_only        PASSED  — graceful degradation without highlevel
test_symphony_35_vs_itself          PASSED  — identical track self-compatibility

==============================================================================
PYTEST RESULTS — test_listenbrainz.py (17 tests)
==============================================================================

Tag Compatibility (cosine similarity on user-generated tag vectors):
  test_tag_same_tags_perfect_similarity    PASSED  — identical tags > 0.99
  test_tag_similar_genres_high_similarity   PASSED  — rock/alt overlap 0.6-1.0
  test_tag_different_genres_low_similarity  PASSED  — rock vs classical < 0.2
  test_tag_missing_data_returns_neutral     PASSED  — None → 0.5
  test_tag_empty_dicts_returns_neutral      PASSED  — {} → 0.5
  test_tag_single_shared_tag               PASSED  — one shared tag > 0.7

Popularity Compatibility (Gaussian decay on log-scale listen count diff):
  test_popularity_same_count               PASSED  — same count > 0.99
  test_popularity_same_tier                PASSED  — 10K vs 12K > 0.95
  test_popularity_10x_difference           PASSED  — 1K vs 10K ∈ (0.4, 0.7)
  test_popularity_1000x_difference         PASSED  — 50 vs 50K < 0.05
  test_popularity_missing_data_returns_neutral  PASSED  — None → 0.5
  test_popularity_zero_listens_returns_neutral  PASSED  — 0 → 0.5

Knowledge Base Integration:
  test_kb_with_listenbrainz_tags           PASSED  — tags flow through to scoring
  test_kb_tags_vs_no_tags                  PASSED  — missing tags → 0.5 neutral
  test_kb_discovery_mode_suppresses_popularity  PASSED  — discovery > normal when pop differs
  test_kb_weight_normalization             PASSED  — doubled weights normalize to same score
  test_kb_tag_weight_affects_scoring       PASSED  — higher tag weight + different tags → lower score

==============================================================================
PYTEST RESULTS — test_musicbrainz.py (21 tests)
==============================================================================

Artist Compatibility (graph topology on artist relationships):
  test_artist_same_artist                  PASSED  — same MBID → 0.95
  test_artist_related_via_first            PASSED  — 1-hop related → 0.70
  test_artist_related_via_second           PASSED  — 1-hop related (reverse) → 0.70
  test_artist_no_relationship              PASSED  — unrelated → 0.50
  test_artist_missing_data_returns_neutral PASSED  — None → 0.5

Era Compatibility (Gaussian decay on release year difference, σ=5yr):
  test_era_same_year                       PASSED  — same year > 0.99
  test_era_3_years_apart                   PASSED  — 3yr apart ∈ (0.75, 0.90)
  test_era_5_years_apart                   PASSED  — 5yr apart ∈ (0.50, 0.70)
  test_era_10_years_apart                  PASSED  — 10yr apart ∈ (0.05, 0.25)
  test_era_20_years_apart                  PASSED  — 20yr apart < 0.02
  test_era_missing_data_returns_neutral    PASSED  — None → 0.5

MusicBrainz Genre Compatibility (Jaccard similarity on curated taxonomy):
  test_mb_genre_identical_genres           PASSED  — identical genres → 1.0
  test_mb_genre_partial_overlap            PASSED  — 2/4 shared → 0.5
  test_mb_genre_no_overlap                 PASSED  — no overlap → 0.0
  test_mb_genre_case_insensitive           PASSED  — case-insensitive match
  test_mb_genre_missing_data_returns_neutral PASSED — None → 0.5
  test_mb_genre_empty_lists_returns_neutral PASSED  — [] → 0.5

Knowledge Base Integration:
  test_kb_artist_same_artist_boosts_score  PASSED  — same artist → ~0.95 component
  test_kb_era_same_decade                  PASSED  — 4yr apart > 0.70
  test_kb_no_mb_data_neutral_fallback      PASSED  — no MB data → ~0.5 on all 3 dims
  test_kb_artist_weight_affects_scoring    PASSED  — weight change affects overall score

==============================================================================
MANUAL SCENARIO TESTS — unit_tests.py (9 tests)
==============================================================================

These are run via `python -m module1.unit_tests` (not collected by pytest).
They provide verbose output with component breakdowns for manual inspection.

Test 1: Same piece (Cyndi Lauper) — >70% ✓
Test 2: Pop vs Classical (different artists)
Test 3: Electronic vs Classical
Test 4: Similar classical pieces (Beethoven x2)
Test 5: Rock vs Classical (Pink Floyd vs Beethoven)
Test 6: Different classical pieces
Test 7: With user preferences (relaxed mood)
Test 8: Rock piece (Pink Floyd) twice — >70% ✓
Test 9: Pop vs Classical (repeat)

==============================================================================
SCORING DIMENSIONS (v8)
==============================================================================

12 compatibility dimensions, all computed as probabilities in [0, 1]:

Content-based (AcousticBrainz):
  1.  Key         — Krumhansl-Kessler profile correlation (weight: 0.15)
  2.  Tempo       — Weber's law Gaussian decay (weight: 0.20)
  3.  Energy      — Gaussian decay on spectral bands (weight: 0.15)
  4.  Loudness    — Gaussian decay on 0-1 scale (weight: 0.05)
  5.  Mood        — ProbLog noisy-OR over 6 mood classifiers (weight: 0.15)
  6.  Timbre      — Bhattacharyya coefficient on MFCC (weight: 0.15)
  7.  Genre       — ProbLog dot product on rosamerica 8-class (weight: 0.05)

User-behavioral (ListenBrainz):
  8.  Tags        — Cosine similarity on user-generated tag vectors (weight: 0.10)
  9.  Popularity  — Log-Gaussian decay on listen counts (weight: 0.00, off by default)

Editorial/structural (MusicBrainz) — NEW in v8:
  10. Artist      — Graph topology on artist relationships (weight: 0.10)
  11. Era         — Gaussian decay on release year difference (weight: 0.05)
  12. MB Genre    — Jaccard similarity on curated genre taxonomy (weight: 0.00, off by default)

All weights auto-normalize. Discovery mode forces popularity weight to 0.

==============================================================================
KEY FINDINGS
==============================================================================

1. SAME PIECE COMPARISON: ✓
   Identical pieces achieve ~92% compatibility across all dimensions.

2. SAME GENRE COMPATIBILITY: ✓
   Classical + Classical = ~74%. Tempo, mood, and energy are primary signals.

3. DIFFERENT GENRE COMPATIBILITY: ✓
   Pop vs Classical = 40-41%. Rock vs Classical = ~71%.

4. USER PREFERENCES: ✓
   Mood-focused preferences increase compatibility (74% → 83%).

5. LISTENBRAINZ TAG INTEGRATION: ✓
   - Identical tags: >99%. Similar genres: 60-100%. Different genres: <20%.
   - Missing data gracefully falls back to 0.5 (neutral).
   - Tag weight demonstrably affects overall scoring.

6. POPULARITY INTEGRATION: ✓
   - Same tier: >95%. 10x difference: ~52%. 1000x difference: <5%.
   - Off by default (weight=0.0) for discovery-friendly behavior.
   - Discovery mode correctly suppresses popularity penalty.

7. WEIGHT NORMALIZATION: ✓
   Doubling all weights produces identical scores (normalization is correct).

8. MUSICBRAINZ ARTIST COMPATIBILITY: ✓ (NEW)
   - Same artist: 0.95. Related (1-hop): 0.70. Unrelated: 0.50 (neutral).
   - Missing data gracefully falls back to 0.5.
   - Weight demonstrably affects overall scoring.

9. MUSICBRAINZ ERA COMPATIBILITY: ✓ (NEW)
   - Same year: >99%. 3yr: ~83%. 5yr: ~61%. 10yr: ~14%. 20yr: <2%.
   - Missing data gracefully falls back to 0.5.

10. MUSICBRAINZ GENRE COMPATIBILITY: ✓ (NEW)
    - Identical genres: 1.0. Partial overlap (2/4): 0.5. No overlap: 0.0.
    - Case-insensitive. Off by default (LB tags carry genre signal).

==============================================================================
TEST EXECUTION DETAILS
==============================================================================

Test Framework: pytest 9.0.2
Python: 3.13.12
Date: February 20, 2026
Status: ALL PASSED (0 failures, 44 passed)
Total Tests: 44 (pytest) + 9 (manual)
Execution Time: ~1.9s
Success Rate: 100%

Test Coverage (pytest):
- Core compatibility:          6/6   ✓
- Tag compatibility:           6/6   ✓
- Popularity compatibility:    6/6   ✓
- LB KB integration:           5/5   ✓
- Artist compatibility:        5/5   ✓ (NEW)
- Era compatibility:           6/6   ✓ (NEW)
- MB genre compatibility:      6/6   ✓ (NEW)
- MB KB integration:           4/4   ✓ (NEW)

Component Testing:
- Key compatibility:          ✓
- Tempo compatibility:        ✓
- Energy compatibility:       ✓
- Loudness compatibility:     ✓
- Mood compatibility:         ✓
- Timbre compatibility:       ✓
- Genre compatibility:        ✓
- Tag compatibility:          ✓
- Popularity compatibility:   ✓
- Artist compatibility:       ✓ (NEW)
- Era compatibility:          ✓ (NEW)
- MB genre compatibility:     ✓ (NEW)
- Weight normalization:       ✓
- Discovery mode:             ✓
- Overall probability:        ✓
- Is_compatible flag:         ✓
"""
