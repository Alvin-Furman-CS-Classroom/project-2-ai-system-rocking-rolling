# Module 3 — How to Run

## Prerequisites

```bash
# Sync the workspace (from project root)
uv sync

# Optional: install essentia-tensorflow for local audio analysis
pip install essentia-tensorflow

# Optional: install yt-dlp for audio acquisition
pip install yt-dlp
# or: sudo pacman -S yt-dlp  (Arch)
```

## Tests

```bash
# Run all Module 3 tests — 80 tests
uv run --package module3 pytest modules/module3/src/module3/tests/ -v

# Run a specific test file
uv run --package module3 pytest modules/module3/src/module3/tests/test_explainer.py -v
uv run --package module3 pytest modules/module3/src/module3/tests/test_constraints.py -v
uv run --package module3 pytest modules/module3/src/module3/tests/test_essentia.py -v
uv run --package module3 pytest modules/module3/src/module3/tests/test_user_model.py -v
uv run --package module3 pytest modules/module3/src/module3/tests/test_assembler.py -v

# Run a single test by name
uv run --package module3 pytest modules/module3/src/module3/tests/ -v -k "test_generates_playlist"

# With print output visible
uv run --package module3 pytest modules/module3/src/module3/tests/ -v -s
```

> **Note**: All tests run WITHOUT Essentia or yt-dlp installed — everything is mocked.
> Use `--package module3` so uv resolves workspace deps (module1, module2).

## CLI — Generate a Playlist

```bash
# Basic usage
uv run --package module3 python -m module3.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID>

# With options
uv run --package module3 python -m module3.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID> \
  --length 5 \
  --beam-width 15

# JSON output (for piping to file or another tool)
uv run --package module3 python -m module3.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID> \
  --json

# Skip Essentia fallback (only use AcousticBrainz data)
uv run --package module3 python -m module3.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID> \
  --no-essentia
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | required | MusicBrainz recording ID of the starting track |
| `--dest` | required | MusicBrainz recording ID of the destination track |
| `--length` | 7 | Target number of tracks in the playlist |
| `--beam-width` | 10 | Search breadth (higher = slower but better paths) |
| `--json` | off | Output as JSON instead of pretty-print |
| `--no-essentia` | off | Disable Essentia audio analysis fallback |

### Example with Real MBIDs

```bash
# Foo Fighters "Congregation" → Royal Blood "Little Monster"
uv run --package module3 python -m module3.main \
  --source 1eac49da-3399-4d34-bbf3-a98a91e2758b \
  --dest 80c24793-6a40-4edb-b1bb-5a4e3946901e \
  --length 5

# Pink Floyd "Lost Art of Conversation" → Florence "What Kind of Man"
uv run --package module3 python -m module3.main \
  --source 564ccd5c-c4d3-4752-9abf-c33bb085d6a5 \
  --dest ffcb45c3-7f32-427d-b3d4-287664bbcdb9

# Same thing but as JSON
uv run --package module3 python -m module3.main \
  --source 564ccd5c-c4d3-4752-9abf-c33bb085d6a5 \
  --dest ffcb45c3-7f32-427d-b3d4-287664bbcdb9 \
  --json > playlist.json
```

---

## Testing Individual Components

### 1. Test yt-dlp Audio Acquisition

First check that yt-dlp is installed and working:

```bash
# Verify yt-dlp is installed
yt-dlp --version

# Test a YouTube search (what the Essentia client does internally)
yt-dlp --extract-audio --audio-format vorbis --audio-quality 5 \
  --no-playlist --max-downloads 1 \
  -o "/tmp/test_audio.%(ext)s" \
  "ytsearch1:Spice Girls Wannabe"

# Check the output
ls -la /tmp/test_audio.*

# Clean up
rm /tmp/test_audio.*
```

Test yt-dlp through the Essentia client (even without Essentia installed — it will download audio but skip extraction):

```python
uv run --package module3 python3 -c "
from module3.essentia_client import EssentiaClient, EssentiaConfig

config = EssentiaConfig(
    audio_cache_dir='/tmp/waveguide_test_audio',
    cleanup_audio=False,  # keep the file so we can inspect it
)
client = EssentiaClient(config)

print(f'Essentia available: {client.is_available}')

# Test audio acquisition directly
# Wannabe by Spice Girls — has 0 ListenBrainz neighbors, but yt-dlp can find it
audio = client._acquire_audio(
    'a8e40e56-d5e7-4d40-a589-5765bbc1e428',  # Wannabe MBID
    title='Wannabe',
    artist='Spice Girls',
)
if audio:
    print(f'Audio downloaded: {audio}')
    print(f'File size: {audio.stat().st_size / 1024:.0f} KB')
else:
    print('Audio acquisition failed (check yt-dlp installation)')
"
```

### 2. Test Essentia Feature Extraction

Requires `essentia-tensorflow` installed:

```python
uv run --package module3 python3 -c "
from module3.essentia_client import EssentiaClient, EssentiaConfig, ESSENTIA_AVAILABLE

print(f'Essentia available: {ESSENTIA_AVAILABLE}')

if not ESSENTIA_AVAILABLE:
    print('Install essentia-tensorflow: pip install essentia-tensorflow')
    exit()

config = EssentiaConfig(
    cache_dir='/tmp/waveguide_test_cache',
    audio_cache_dir='/tmp/waveguide_test_audio',
    cleanup_audio=False,
)
client = EssentiaClient(config)

# Full pipeline: yt-dlp download → Essentia extraction → AB format mapping
# Try with Wannabe (no AB data, no LB neighbors — pure Essentia)
features = client.fetch_features(
    'a8e40e56-d5e7-4d40-a589-5765bbc1e428',
    title='Wannabe',
    artist='Spice Girls',
)

if features:
    print(f'Track: {features.title} - {features.artist}')
    print(f'BPM: {features.bpm:.1f}')
    print(f'Key: {features.key} {features.scale}')
    print(f'Energy: {features.energy_score:.4f}')
    print(f'Genre: {features.genre_rosamerica}')
    print(f'Mood: happy={features.mood_happy}')
    print()
    print(f'Stats: {client.cache_stats()}')
else:
    print('Feature extraction failed')
"
```

Check the cached features:

```bash
# Feature cache (JSON, human-readable)
cat ~/.waveguide/essentia_cache/a8e40e56-d5e7-4d40-a589-5765bbc1e428.json | python3 -m json.tool

# Audio cache
ls -la ~/.waveguide/audio_cache/
```

### 3. Test Explainer

The explainer works with any `TrackFeatures` and `TransitionResult` — no APIs needed:

```python
uv run --package module3 python3 -c "
from module1 import MusicKnowledgeBase, TrackFeatures, UserPreferences
from module3 import (
    explain_playlist, explain_transition,
    get_top_contributors, get_bottom_contributors,
    detect_energy_arc, detect_genre_journey,
    generate_playlist_summary,
)

# Create some test tracks
tracks = [
    TrackFeatures(mbid='a', title='Start', artist='Artist A',
                  bpm=120, key='C', scale='major',
                  energy_mid_high=0.003, genre_rosamerica=('roc', 0.9)),
    TrackFeatures(mbid='b', title='Middle', artist='Artist B',
                  bpm=128, key='D', scale='minor',
                  energy_mid_high=0.005, genre_rosamerica=('pop', 0.8)),
    TrackFeatures(mbid='c', title='End', artist='Artist C',
                  bpm=135, key='E', scale='major',
                  energy_mid_high=0.008, genre_rosamerica=('dan', 0.7)),
]

# Score transitions
kb = MusicKnowledgeBase()
t1 = kb.get_compatibility(tracks[0], tracks[1])
t2 = kb.get_compatibility(tracks[1], tracks[2])
transitions = [t1, t2]

# Detect patterns
print('Energy arc:', detect_energy_arc(tracks))
print('Genre journey:', ' → '.join(detect_genre_journey(tracks)))
print()

# Summary
print('Summary:', generate_playlist_summary(tracks, transitions))
print()

# Per-transition breakdown
prefs = UserPreferences()
for i, tr in enumerate(transitions):
    top = get_top_contributors(tr, prefs, n=3, track1=tracks[i], track2=tracks[i+1])
    bot = get_bottom_contributors(tr, prefs, n=2, track1=tracks[i], track2=tracks[i+1])

    print(f'Transition {i+1}: {tracks[i].title} → {tracks[i+1].title} ({tr.probability:.0%})')
    print('  Top contributors:')
    for dim, score, desc in top:
        print(f'    + {desc}')
    print('  Weakest:')
    for dim, score, desc in bot:
        print(f'    - {desc}')
    print()
"
```

### 4. Test Constraints

```python
uv run --package module3 python3 -c "
from module1 import TrackFeatures
from module3 import (
    NoRepeatArtists, NoRepeatedTracks,
    EnergyArcConstraint, GenreVarietyConstraint,
    TempoSmoothnessConstraint, MoodCoherenceConstraint,
    evaluate_all, DEFAULT_CONSTRAINTS,
)

# Playlist with a repeated artist (should violate NoRepeatArtists)
tracks = [
    TrackFeatures(mbid='1', title='Song A', artist='Radiohead', bpm=120,
                  key='C', scale='major', energy_mid_high=0.003, genre_rosamerica=('roc', 0.9)),
    TrackFeatures(mbid='2', title='Song B', artist='Muse', bpm=130,
                  key='D', scale='minor', energy_mid_high=0.005, genre_rosamerica=('roc', 0.8)),
    TrackFeatures(mbid='3', title='Song C', artist='Radiohead', bpm=140,
                  key='E', scale='major', energy_mid_high=0.008, genre_rosamerica=('roc', 0.7)),
    TrackFeatures(mbid='4', title='Song D', artist='Coldplay', bpm=100,
                  key='A', scale='minor', energy_mid_high=0.002, genre_rosamerica=('pop', 0.8)),
]

# Evaluate with default constraints
results = evaluate_all(tracks, DEFAULT_CONSTRAINTS)
for r in results:
    status = '✓' if r.satisfied else '✗'
    print(f'{status} {r.name} (score: {r.score:.0%})')
    for v in r.violations:
        print(f'    {v}')
print()

# Try specific constraints
energy_rising = EnergyArcConstraint(target_arc='rising')
result = energy_rising.evaluate(tracks)
print(f'Energy arc (rising): {\"satisfied\" if result.satisfied else \"violated\"} — score {result.score:.0%}')

mood = MoodCoherenceConstraint()
result = mood.evaluate(tracks)
print(f'Mood coherence: {\"satisfied\" if result.satisfied else \"violated\"} — score {result.score:.0%}')
"
```

### 5. Test User Model

```python
uv run --package module3 python3 -c "
from module1 import TransitionResult
from module3 import UserProfile, PlaylistFeedback
from module3.user_model import update_from_feedback, save_profile, load_profile
from pathlib import Path

# Start with default profile
profile = UserProfile()
print('Initial weights:')
for dim, w in sorted(profile.dimension_weights.items()):
    print(f'  {dim}: {w:.3f}')
print()

# Simulate feedback on a transition the user loved (5/5)
transition = TransitionResult(
    probability=0.85, penalty=0.15, is_compatible=True,
    key_compatibility=0.9, tempo_compatibility=0.95,
    energy_compatibility=0.8, loudness_compatibility=0.6,
    mood_compatibility=0.7, timbre_compatibility=0.5,
    genre_compatibility=0.3, tag_compatibility=0.8,
    popularity_compatibility=0.5, artist_compatibility=0.4,
    era_compatibility=0.6, mb_genre_compatibility=0.5,
    explanation='Test',
)

feedback = PlaylistFeedback(playlist_id='test-1', overall_rating=5.0)
update_from_feedback(profile, feedback, [transition], learning_rate=0.2)

print('After positive feedback (5/5):')
for dim, w in sorted(profile.dimension_weights.items()):
    print(f'  {dim}: {w:.3f}')
print()

# Save and reload
test_path = Path('/tmp/waveguide_test_profile.json')
save_profile(profile, test_path)
reloaded = load_profile(test_path)
print(f'Profile saved to {test_path}')
print(f'Feedback history: {len(reloaded.feedback_history)} entries')

# Convert to Module 1 preferences
prefs = profile.to_user_preferences()
print(f'Converted to UserPreferences: tempo_weight={prefs.tempo_weight:.3f}, key_weight={prefs.key_weight:.3f}')
"
```

### 6. Test Essentia Client Cache & Stats

```python
uv run --package module3 python3 -c "
from module3.essentia_client import EssentiaClient, EssentiaConfig, ESSENTIA_AVAILABLE

config = EssentiaConfig()
client = EssentiaClient(config)

print(f'Essentia installed: {ESSENTIA_AVAILABLE}')
print(f'Feature cache dir: {config.cache_dir}')
print(f'Audio cache dir: {config.audio_cache_dir}')
print(f'Cache stats: {client.cache_stats()}')

# If you've already extracted features for Wannabe, this will hit cache
if ESSENTIA_AVAILABLE:
    features = client.fetch_features(
        'a8e40e56-d5e7-4d40-a589-5765bbc1e428',
        title='Wannabe', artist='Spice Girls',
    )
    if features:
        print(f'Got features: BPM={features.bpm:.1f}, Key={features.key} {features.scale}')
    print(f'Stats after: {client.cache_stats()}')
"
```

---

## Full Pipeline — End to End

This runs the complete pipeline: beam search → feature resolution → constraints → explanation.

```bash
# 1. Find working MBIDs with the Module 2 lookup tool
uv run --package module2 python -m module2.lookup --search "Foo Fighters Congregation"
uv run --package module2 python -m module2.lookup --search "Royal Blood Little Monster"

# 2. Check data availability
uv run --package module2 python -m module2.lookup --check 1eac49da-3399-4d34-bbf3-a98a91e2758b
uv run --package module2 python -m module2.lookup --check 80c24793-6a40-4edb-b1bb-5a4e3946901e

# 3. Generate playlist (pretty-print)
uv run --package module3 python -m module3.main \
  --source 1eac49da-3399-4d34-bbf3-a98a91e2758b \
  --dest 80c24793-6a40-4edb-b1bb-5a4e3946901e \
  --length 5

# 4. Generate playlist (JSON, save to file)
uv run --package module3 python -m module3.main \
  --source 1eac49da-3399-4d34-bbf3-a98a91e2758b \
  --dest 80c24793-6a40-4edb-b1bb-5a4e3946901e \
  --length 5 --json > playlist.json

cat playlist.json | python3 -m json.tool
```

### Full Pipeline via Python API

```python
uv run --package module3 python3 -c "
from module1 import MusicKnowledgeBase
from module2 import SearchSpace
from module3 import PlaylistAssembler
import json

kb = MusicKnowledgeBase()
space = SearchSpace(kb)

assembler = PlaylistAssembler(
    knowledge_base=kb,
    search_space=space,
    beam_width=10,
)

# Foo Fighters → Royal Blood
playlist = assembler.generate_playlist(
    '1eac49da-3399-4d34-bbf3-a98a91e2758b',
    '80c24793-6a40-4edb-b1bb-5a4e3946901e',
    target_length=5,
)

if playlist:
    print(f'Summary: {playlist.explanation.summary}')
    print()

    for te in playlist.explanation.track_explanations:
        role = f' [{te.role}]' if te.role != 'waypoint' else ''
        print(f'  {te.position+1}. {te.title or te.mbid} — {te.artist or \"Unknown\"}{role}')
        if te.incoming_transition:
            print(f'     ↑ compatibility: {te.incoming_transition.overall_score:.0%}')
            for dim, score, desc in te.incoming_transition.top_contributors:
                print(f'       • {desc}')

    print()
    print('Constraints:')
    for cr in playlist.constraints_applied:
        status = '✓' if cr.satisfied else '✗'
        print(f'  {status} {cr.name} (score: {cr.score:.0%})')

    print()
    print('JSON output:')
    print(json.dumps(playlist.to_static_output(), indent=2))
else:
    print('No path found — both tracks need ListenBrainz neighbor data')
"
```

---

## The "Wannabe Problem" — Songs with No Data

Many popular songs (even massive hits) have **zero** ListenBrainz neighbor data because LB is built from a small user base. Spice Girls "Wannabe" is a classic example.

```bash
# Check Wannabe's data availability
uv run --package module2 python -m module2.lookup --search "Spice Girls Wannabe"
# → Will find the MBID but likely show 0 LB neighbors
```

**What happens at each level:**

| Layer | Without Essentia | With Essentia |
|-------|-----------------|---------------|
| **LB neighbors** | 0 — cannot be used as source/dest for beam search | Same — Essentia doesn't help with neighbors |
| **AB features** | Missing — Module 1 uses 0.5 neutral fallback | Essentia extracts real features (BPM, key, energy, loudness, MFCC) |
| **As waypoint** | Only if it appears in another track's neighbor list | Same, but with real features instead of fallback |

**Essentia helps when**: a track appears in someone else's LB neighbor list but has no AB data. Essentia fills in the audio features so Module 1 can score transitions properly instead of falling back to 0.5 across 7 dimensions.

**Essentia does NOT help when**: a track has 0 LB neighbors. It still can't be a beam search source/destination because there are no edges in the graph. This is a data coverage problem, not a feature problem.

---

## Known Working MBIDs

| Track | MBID | LB Neighbors |
|-------|------|-------------|
| Pink Floyd — The Lost Art of Conversation | `564ccd5c-c4d3-4752-9abf-c33bb085d6a5` | 6 |
| Foo Fighters — Congregation | `1eac49da-3399-4d34-bbf3-a98a91e2758b` | 59 |
| Royal Blood — Little Monster | `80c24793-6a40-4edb-b1bb-5a4e3946901e` | 89 |
| Florence + the Machine — What Kind of Man | `ffcb45c3-7f32-427d-b3d4-287664bbcdb9` | 100 |

> Both source AND destination must have LB neighbors. Use `uv run --package module2 python -m module2.lookup --search "..."` to find tracks with data.

## How to Find MBIDs

```bash
# Search by name
uv run --package module2 python -m module2.lookup --search "Bohemian Rhapsody Queen"

# Lucene syntax for precise matches
uv run --package module2 python -m module2.lookup --search '"Stairway to Heaven" AND artist:"Led Zeppelin"'

# Check a known MBID across all 3 APIs
uv run --package module2 python -m module2.lookup --check 564ccd5c-c4d3-4752-9abf-c33bb085d6a5
```

## File Layout

```
modules/module3/
├── pyproject.toml
├── CHANGELOG.md
├── USAGE.md
└── src/module3/
    ├── __init__.py               # Public API exports
    ├── data_models.py            # AssembledPlaylist, UserProfile, ConstraintResult, etc.
    ├── essentia_client.py        # Essentia + yt-dlp audio pipeline
    ├── constraints.py            # 6 constraint types + CSP solver
    ├── user_model.py             # EMA preference learning from feedback
    ├── explainer.py              # 3-level explanations + arc/genre detection
    ├── playlist_assembler.py     # Orchestrator: search → constrain → explain
    ├── main.py                   # CLI entry point
    └── tests/
        ├── test_explainer.py     # 22 tests
        ├── test_constraints.py   # 22 tests
        ├── test_essentia.py      # 18 tests
        ├── test_user_model.py    # 12 tests
        ├── test_assembler.py     #  6 tests
        └── fixtures/
            └── mock_essentia.py  # Mock Essentia outputs for testing
```
