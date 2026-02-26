# Module 2 — How to Run

## Tests

```bash
# Run all tests (Module 1 + Module 2) — 79 tests
just test

# Run only Module 2 tests — 35 tests
uv run pytest modules/module2/ -v

# Run specific test file
uv run pytest modules/module2/src/module2/tests/test_beam_search.py -v
uv run pytest modules/module2/src/module2/tests/test_clients.py -v

# Run a single test by name
uv run pytest modules/module2/ -v -k "test_find_path_simple_linear"

# Run with print output visible (shows compatibility scores)
uv run pytest modules/module2/ -v -s
```

## CLI — Find a Playlist Path

```bash
# Basic usage: find a 7-track path between two songs
uv run python -m module2.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID>

# Customize path length and beam width
uv run python -m module2.main \
  --source <SOURCE_MBID> \
  --dest <DEST_MBID> \
  --length 5 \
  --beam-width 15
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | required | MusicBrainz recording ID of the starting track |
| `--dest` | required | MusicBrainz recording ID of the destination track |
| `--length` | 7 | Target number of tracks in the playlist |
| `--beam-width` | 10 | Search breadth (higher = slower but better paths) |

### Example with Real MBIDs

```bash
# Pink Floyd "The Lost Art of Conversation" → another track
uv run python -m module2.main \
  --source 564ccd5c-c4d3-4752-9abf-c33bb085d6a5 \
  --dest 832b2377-74db-4fa7-99f3-1b8f9e654102

# Note: Both tracks need AcousticBrainz data AND ListenBrainz similar recordings
# to find a path. If either source is missing, you'll get "No path found".
```

## Python API — Use in Code

```python
from module1 import MusicKnowledgeBase
from module2 import BeamSearch, SearchSpace

# Initialize
kb = MusicKnowledgeBase()
space = SearchSpace(knowledge_base=kb)
search = BeamSearch(knowledge_base=kb, search_space=space, beam_width=10)

# Find a single path
path = search.find_path(
    source_mbid="<MBID1>",
    dest_mbid="<MBID2>",
    target_length=7,
)

if path:
    print(f"Found {path.length}-track path")
    print(f"Average compatibility: {path.average_compatibility:.1%}")
    for i, mbid in enumerate(path.mbids):
        features = space.get_features(mbid)
        print(f"  {i+1}. {features.title} - {features.artist}" if features else f"  {i+1}. {mbid}")

# Find multiple diverse paths
paths = search.find_paths_multi(
    source_mbid="<MBID1>",
    dest_mbid="<MBID2>",
    target_length=7,
    num_paths=3,
)
for i, p in enumerate(paths):
    print(f"Path {i+1}: cost={p.total_cost:.3f}, compat={p.average_compatibility:.1%}")
```

## Individual API Clients

```python
# ListenBrainz: discover similar tracks
from module2 import ListenBrainzClient
lb = ListenBrainzClient()
similar = lb.get_similar_recordings("564ccd5c-c4d3-4752-9abf-c33bb085d6a5", count=10)
for s in similar:
    print(f"  {s.mbid} (score={s.similarity_score:.3f})")

# ListenBrainz: get tags and popularity
tags = lb.get_recording_tags(["<MBID1>", "<MBID2>"])
popularity = lb.get_recording_popularity(["<MBID1>", "<MBID2>"])

# AcousticBrainz: fetch audio features
from module2 import AcousticBrainzClient
ab = AcousticBrainzClient()
features = ab.fetch_features("564ccd5c-c4d3-4752-9abf-c33bb085d6a5")
if features:
    print(f"BPM={features.bpm}, Key={features.key} {features.scale}")

# AcousticBrainz: batch fetch (up to 25 per request)
batch = ab.fetch_features_batch(["<MBID1>", "<MBID2>", "<MBID3>"])

# MusicBrainz: recording metadata + artist relationships
from module2 import MusicBrainzClient
mb = MusicBrainzClient()
meta = mb.get_recording_metadata("564ccd5c-c4d3-4752-9abf-c33bb085d6a5")
print(f"Artist: {meta.artist_mbid}, Year: {meta.release_year}, Genres: {meta.genre_tags}")

related = mb.get_artist_relationships("83d91898-7763-47d7-b03b-b92132375c47")
print(f"Related artists: {len(related)}")
```

## Linting & Type Checking

```bash
just lint          # Ruff linter
just fmt           # Auto-format with Ruff
just typecheck     # Type check with ty
just default       # Run all: test + lint + typecheck
```

## How to Find MBIDs

### Lookup Tool

```bash
# Search by song name
uv run python -m module2.lookup --search "Bohemian Rhapsody Queen"

# Search with Lucene syntax for exact matches
uv run python -m module2.lookup --search '"Stairway to Heaven" AND artist:"Led Zeppelin"'

# Check if a specific MBID has data across all 3 APIs
uv run python -m module2.lookup --check 564ccd5c-c4d3-4752-9abf-c33bb085d6a5
```

The lookup tool shows MusicBrainz search results AND checks ListenBrainz neighbor
availability — only MBIDs with LB neighbors can be used as source/dest for beam search.

### Manual Lookup

MusicBrainz recording IDs (MBIDs) can be found at:
- https://musicbrainz.org — search for a song, the recording page URL contains the MBID
- Example: `https://musicbrainz.org/recording/564ccd5c-c4d3-4752-9abf-c33bb085d6a5`

### Known Working MBIDs (with ListenBrainz neighbors)

| Track | MBID | LB Neighbors |
|-------|------|-------------|
| Pink Floyd — The Lost Art of Conversation | `564ccd5c-c4d3-4752-9abf-c33bb085d6a5` | 6 |
| Foo Fighters — Congregation | `1eac49da-3399-4d34-bbf3-a98a91e2758b` | 59 |
| Royal Blood — Little Monster | `80c24793-6a40-4edb-b1bb-5a4e3946901e` | 89 |
| Florence + the Machine — What Kind of Man | `ffcb45c3-7f32-427d-b3d4-287664bbcdb9` | 100 |

> **Important**: Both source AND destination must have ListenBrainz neighbor data.
> Most MBIDs (even for famous songs) have no LB data — use `--search` to find ones that do.
> AcousticBrainz was archived in 2022, so only pre-2022 recordings have audio feature data.
> Tracks without AB data will use Module 1's 0.5 neutral fallback for 7 dimensions.
