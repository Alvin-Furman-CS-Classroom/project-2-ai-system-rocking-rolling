# Module 2: Beam Search Path Finding - Implementation Plan

## Overview

Module 2 implements beam search to find an optimal playlist path from a source song to a destination song. The algorithm discovers intermediate waypoints by exploring "neighborhoods" of similar tracks using the ListenBrainz similarity API, with transition costs computed via Module 1's knowledge base.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Module 2: BeamSearch                       │
├─────────────────────────────────────────────────────────────────────┤
│  Input: source_mbid, dest_mbid, playlist_length                     │
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐ │
│  │ ListenBrainz    │───▶│  Search Space    │───▶│ Beam Search    │ │
│  │ Similarity API  │    │  (MBID graph)    │    │ Algorithm      │ │
│  └─────────────────┘    └──────────────────┘    └───────┬────────┘ │
│           │                                              │          │
│           ▼                                              ▼          │
│  ┌─────────────────┐                           ┌────────────────┐  │
│  │ AcousticBrainz  │                           │ Module 1 KB    │  │
│  │ Bulk Feature    │                           │ get_penalty()  │  │
│  │ Fetcher         │                           └────────────────┘  │
│  └─────────────────┘                                               │
│                                                                     │
│  Output: Ordered list of MBIDs representing playlist path          │
└─────────────────────────────────────────────────────────────────────┘
```

## API Dependencies

### ListenBrainz Similarity API
- **Endpoint**: `https://labs.api.listenbrainz.org/similar-recordings`
- **Purpose**: Discover neighborhoods of similar tracks around source/destination
- **Rate Limits**: Better limits with authentication token
- **Returns**: List of MBIDs with similarity scores

### AcousticBrainz Bulk API
- **Endpoint**: `GET https://acousticbrainz.org/api/v1/high-level` and `/low-level`
- **Purpose**: Fetch audio features for tracks in search space
- **Format**: `recording_ids=mbid1;mbid2;mbid3` (semicolon-separated)
- **Rate Limits**: 10 requests per 10 seconds
- **Note**: Service archived in 2022, but existing data (~2M recordings) still accessible

## Implementation Components

### 1. ListenBrainz Client (`listenbrainz_client.py`)
```python
class ListenBrainzClient:
    def get_similar_recordings(self, mbid: str, count: int = 50) -> list[SimilarRecording]
    def get_similar_artists(self, artist_mbid: str) -> list[SimilarArtist]
```

### 2. AcousticBrainz Client (`acousticbrainz_client.py`)
```python
class AcousticBrainzClient:
    def fetch_features_bulk(self, mbids: list[str]) -> dict[str, TrackFeatures]
    def fetch_lowlevel(self, mbids: list[str]) -> dict[str, dict]
    def fetch_highlevel(self, mbids: list[str]) -> dict[str, dict]
```

### 3. Search Space Manager (`search_space.py`)
```python
class SearchSpace:
    def __init__(self, kb: MusicKnowledgeBase, lb_client, ab_client)
    def get_neighbors(self, mbid: str) -> list[str]  # Returns cached or fetches new
    def get_features(self, mbid: str) -> TrackFeatures | None
    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float
```

### 4. Beam Search Implementation (`beam_search.py`)
```python
@dataclass
class SearchState:
    path: list[str]  # MBIDs visited
    cost: float      # Accumulated transition penalty

class BeamSearch:
    def __init__(self, kb: MusicKnowledgeBase, beam_width: int = 10)
    def find_path(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7
    ) -> PlaylistPath
```

### 5. Data Models (`data_models.py`)
```python
@dataclass
class SimilarRecording:
    mbid: str
    similarity_score: float

@dataclass
class PlaylistPath:
    mbids: list[str]
    total_cost: float
    transitions: list[TransitionResult]
```

## Algorithm: Beam Search with Dynamic Neighborhood Expansion

```
1. Initialize:
   - Fetch neighborhood around source (N similar tracks from ListenBrainz)
   - Fetch neighborhood around destination (N similar tracks)
   - Fetch AcousticBrainz features for all discovered MBIDs

2. Create initial beam:
   - Start state = [source_mbid]
   - Beam = [(start_state, cost=0)]

3. Search loop (while paths haven't reached target_length):
   a. For each state in beam:
      - Get neighbors of current track (last MBID in path)
      - If neighbors not cached, fetch from ListenBrainz + AcousticBrainz

   b. Generate successors:
      - For each neighbor not already in path:
        - Compute transition cost via Module 1 KB
        - Create new state = (path + [neighbor], cost + transition_cost)

   c. Prune beam:
      - Sort all successors by cost + heuristic(distance to dest)
      - Keep top beam_width states

   d. Early termination:
      - If any path reaches destination with target_length, add to solutions

4. Return best path (lowest total cost among solutions)
```

## Heuristic Function

Use Module 1's transition score as the heuristic:
```python
def heuristic(current_mbid: str, dest_mbid: str) -> float:
    current_features = search_space.get_features(current_mbid)
    dest_features = search_space.get_features(dest_mbid)
    return kb.get_penalty(current_features, dest_features)
```

This provides an estimate of how "compatible" the current track is with the destination. Lower penalty = closer to goal.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Neighborhood size | 25 tracks | Balances search space with API efficiency |
| Missing AcousticBrainz data | Skip track | Exclude from search space; require features for scoring |
| Caching strategy | In-memory only | Simple, sufficient for single session runs |
| Heuristic | Module 1 penalty | Uses existing KB logic; estimates direct cost to destination |

## File Structure

```
modules/module2/
├── pyproject.toml
├── README.md
└── src/module2/
    ├── __init__.py
    ├── beam_search.py          # Core search algorithm
    ├── search_space.py         # Neighbor management + caching
    ├── listenbrainz_client.py  # ListenBrainz API wrapper
    ├── acousticbrainz_client.py # AcousticBrainz API wrapper
    ├── data_models.py          # SimilarRecording, PlaylistPath, etc.
    └── tests/
        ├── test_beam_search.py
        ├── test_clients.py
        └── fixtures/           # Mock API responses
```

## Integration with Module 1

Module 2 imports from Module 1:
- `MusicKnowledgeBase` for `get_penalty(track1, track2)`
- `TrackFeatures` data model
- `TransitionResult` for path validation

## Testing Strategy

1. **Unit tests**: Mock API responses, test search logic
2. **Integration tests**: Real API calls with known track pairs
3. **Edge cases**: Missing data, no path exists, very long playlists

## Dependencies

```toml
[project]
dependencies = [
    "module1",      # Internal dependency
    "requests",     # HTTP client for APIs
    "tenacity",     # Retry logic for rate limits
]
```

## Verification Plan

### Unit Tests
1. **BeamSearch logic**: Mock search space, verify path finding with controlled costs
2. **SearchSpace caching**: Verify neighbors/features are cached and reused
3. **API clients**: Mock HTTP responses, verify parsing and error handling

### Integration Tests
1. **Known track pair**: Test with two well-known tracks that have AcousticBrainz data
   - Example: Two Beethoven symphonies (from existing test_files)
   - Verify path is returned with valid transitions

2. **Playlist length constraint**: Request 5-track and 10-track playlists, verify lengths

3. **No path scenario**: Test with incompatible source/dest (may need mocking)

### Manual Testing
```bash
# Run module 2 demo with sample track MBIDs
uv run python -m module2.main \
  --source "abc123-..." \
  --dest "def456-..." \
  --length 7
```

### End-to-End Verification
1. Call `BeamSearch.find_path()` with real MBIDs
2. Verify returned path has correct length
3. Pass path to Module 1's `validate_playlist()`
4. Confirm overall compatibility score is reasonable (>0.3)

## Implementation Order

1. **API Clients** (~2 files)
   - `listenbrainz_client.py` - Fetch similar recordings
   - `acousticbrainz_client.py` - Bulk feature fetching

2. **Data Models** (~1 file)
   - `data_models.py` - SimilarRecording, PlaylistPath

3. **Search Space** (~1 file)
   - `search_space.py` - Coordinate API calls, caching, feature access

4. **Beam Search** (~1 file)
   - `beam_search.py` - Core algorithm

5. **Tests** (~2 files)
   - Unit tests with mocks
   - Integration tests with real APIs

## Example Usage

```python
from module1 import MusicKnowledgeBase
from module2 import BeamSearch

kb = MusicKnowledgeBase()
search = BeamSearch(knowledge_base=kb, beam_width=10)

# Find playlist path from Cyndi Lauper to Pink Floyd
path = search.find_path(
    source_mbid="a1b2c3d4-...",
    dest_mbid="e5f6g7h8-...",
    target_length=7
)

print(f"Path: {path.mbids}")
print(f"Total cost: {path.total_cost:.3f}")
for i, t in enumerate(path.transitions):
    print(f"  {i}: {t.probability:.1%} compatible")
```
