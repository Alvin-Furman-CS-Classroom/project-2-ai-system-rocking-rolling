# Wave Guide: Your Personal Music Journey

## Overview

Wave Guide creates personalized music playlists that take listeners on a "journey" from a starting track to a destination track, discovering new music along the way. Unlike traditional recommendation systems that optimize for similarity alone, Wave Guide treats playlist generation as a path-finding problem through multidimensional audio feature space.

The system addresses a critical limitation in existing music platforms: Spotify recently restricted API access to recommendation endpoints, making proprietary solutions unsustainable. Wave Guide leverages open-source music databases (MusicBrainz, AcousticBrainz, ListenBrainz) and a self-hosted MusicBrainz Postgres mirror for fast, rate-limit-free access to 38M+ recordings.

Users specify source and destination tracks (or moods). The system encodes music theory knowledge and transition smoothness rules as a probabilistic logic knowledge base, uses bidirectional beam search to find optimal paths through the ListenBrainz similarity graph, applies CSP constraints and user preference learning, and generates human-readable explanations for every playlist decision.

## Team

- Michael Thomas
- Rahul Ranjan Sah
- Mohammed Ibrahim

## Proposal

See [PROPOSAL.md](./PROPOSAL.md) for the full system proposal.

## Architecture

```
User Input (source + dest tracks or moods)
    |
    v
Module 4: Mood Classification (mood label -> feature centroid)
    |
    v
Module 2: Path Finding (bidirectional beam search over LB graph)
    |   Uses: MusicBrainzDB (Postgres) | AcousticBrainzClient | ListenBrainzClient
    v
Module 1: Scoring (12-dimension compatibility via ProbLog KB)
    |
    v
Module 3: Assembly (constraints + user model + explanations)
    |
    v
Flask API -> React Web UI
```

## Modules

| Module | Topic | What it does | Tests |
|--------|-------|-------------|-------|
| 1 | Probabilistic Logic | 12-dimension compatibility scoring via ProbLog KB | 44 |
| 2 | Search | Bidirectional beam search, MusicBrainzDB (Postgres), AB/LB clients | 41 |
| 3 | Constraint Satisfaction | CSP constraints, user model, Essentia fallback, proxy pool, explanations | 94 |
| 4 | Machine Learning | Mood classification (LR/MLP), genre-to-mood mapping, DB training pipeline | 3 test files |
| API | Integration | Flask REST API for compare + playlist generation | - |
| Web | Frontend | React/TypeScript UI with song search, comparison, playlist generation | - |

**Total: 179+ tests, 7,500+ lines of source code across 4 modules.**

## Module Plan

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Probabilistic Logic (KB, Inference, Rules) | AcousticBrainz feature JSON, user constraints | Knowledge base with compatibility scoring | None | 1 |
| 2 | Search (Beam Search) | Source/dest feature vectors, KB rules | Ordered waypoint sequence | Module 1 | 1 |
| 3 | Constraint Satisfaction | Playlist with metadata, user feedback | Optimized playlist with explanations | Module 2 | 2 |
| 4 | Machine Learning (Supervised) | Feature vectors or mood labels | Mood classification / feature mapping | Module 1 | 4 |
| 5 | System Integration | User input, all module outputs | Complete validated playlist | Modules 1-4 | 5 |

## Repository Layout

```
wave-guide/
├── modules/
│   ├── module1/                        # Music Feature Knowledge Base
│   │   ├── src/module1/
│   │   │   ├── knowledge_base.py       # ProbLog-based KB with Python API
│   │   │   ├── data_models.py          # TrackFeatures, TransitionResult, UserPreferences
│   │   │   ├── data_loader.py          # AcousticBrainz JSON parsing
│   │   │   └── rules_helpers.py        # Research-grounded compatibility functions
│   │   └── CHANGELOG.md
│   ├── module2/                        # Path Finding + Data Clients
│   │   ├── src/module2/
│   │   │   ├── beam_search.py          # Bidirectional beam search with A* priority
│   │   │   ├── musicbrainz_db.py       # Postgres-backed MB client (no rate limits)
│   │   │   ├── musicbrainz_client.py   # Public MB API client (1 req/sec fallback)
│   │   │   ├── acousticbrainz_client.py # AB batch feature API
│   │   │   ├── listenbrainz_client.py  # LB neighbor discovery (4 algorithms)
│   │   │   └── search_space.py         # Orchestrates all data sources
│   │   ├── test_benchmark.py           # Postgres vs API performance comparison
│   │   └── CHANGELOG.md
│   ├── module3/                        # Playlist Assembly
│   │   ├── src/module3/
│   │   │   ├── playlist_assembler.py   # Full pipeline orchestrator
│   │   │   ├── constraints.py          # 6 CSP constraint types + min-conflicts
│   │   │   ├── explainer.py            # 3-level explanation system
│   │   │   ├── essentia_client.py      # Audio analysis fallback (yt-dlp + Essentia)
│   │   │   ├── proxy_pool.py           # Auto-growing pool for zero-neighbor tracks
│   │   │   └── user_model.py           # Online preference learning (EMA)
│   │   ├── USAGE.md
│   │   └── CHANGELOG.md
│   ├── module4/                        # Mood Classification
│   │   ├── src/module4/
│   │   │   ├── mood_classifier.py      # LR / MLP / Ensemble classifiers
│   │   │   ├── feature_engineering.py  # 23-dim normalized feature extraction
│   │   │   ├── training_data.py        # DB pipeline, synthetic data, parquet cache
│   │   │   └── data_models.py          # MoodLabel, TrainingExample, EvalMetrics
│   │   ├── USAGE.md
│   │   └── CHANGELOG.md
│   └── api/                            # Flask REST API
│       └── src/api/app.py
├── web/                                # React TypeScript frontend
│   └── src/
│       ├── App.tsx
│       ├── hooks/                      # useCompare, usePlaylistGenerator, useRecordingSearch
│       ├── components/                 # SongPicker, PlaylistResults, TransitionBar, etc.
│       └── api/                        # OpenAPI client
├── plans/                              # Module planning documentation
├── rubrics/                            # Checkpoint review rubrics
├── PROPOSAL.md                         # Detailed system proposal
├── AGENTS.md                           # LLM agent instructions
└── pyproject.toml                      # Root workspace config
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- [direnv](https://direnv.net/) (for auto-loading environment variables)
- Node.js 18+ and pnpm (for web frontend)
- PostgreSQL access to MusicBrainz mirror (optional, for fast lookups)

### Installation

```bash
git clone <repo-url>
cd project-2-ai-system-rocking-rolling

# Install all Python dependencies (all 4 modules)
uv lock && uv sync

# Install web dependencies (optional)
cd web && pnpm install && cd ..
```

### Environment

Create a `.env` file at the project root (gitignored) with your MusicBrainz mirror credentials:

```bash
MB_DB_HOST=<your-db-host>
MB_DB_USER=<your-db-user>
MB_DB_NAME=musicbrainz
MB_DB_SCHEMA=musicbrainz
MB_DB_PORT=5432
```

Set up [direnv](https://direnv.net/) to auto-load env vars when you enter the project:

```bash
echo 'dotenv' > .envrc
direnv allow
```

Configure `~/.pgpass` for passwordless Postgres auth (see [PostgreSQL docs](https://www.postgresql.org/docs/current/libpq-pgpass.html)):

```
<host>:<port>:<dbname>:<user>:<password>
```

Without Postgres access, the system falls back to the public MusicBrainz API (1 req/sec rate limit).

## Running

### Playlist Generation (CLI)

```bash
# Generate a playlist between two tracks
uv run python -m module3.main <source_mbid> <dest_mbid>

# JSON output
uv run python -m module3.main <source_mbid> <dest_mbid> --json
```

### Mood Classifier Training

```bash
# Train from Postgres + AcousticBrainz (recommended)
uv run python -m module4.main --from-db --max-per-class 200 --model both

# Train from synthetic data (no external deps)
uv run python -m module4.main --synthetic --model both
```

See [modules/module4/USAGE.md](./modules/module4/USAGE.md) for full training options.

### Web Interface

```bash
just serve
```

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/compare?recording_id_1=<MBID>&recording_id_2=<MBID>` - Compare two tracks
- `GET /api/playlist?source_mbid=<MBID>&dest_mbid=<MBID>&length=7` - Generate playlist

### Benchmarking (Postgres vs API)

```bash
uv run python modules/module2/test_benchmark.py
```

Results are saved to `BENCHMARKS.md`.

## Testing

```bash
# All modules
uv run python -m pytest modules/ --tb=short -q

# Individual modules
uv run python -m pytest modules/module1/ -q
uv run python -m pytest modules/module2/ -q
uv run python -m pytest modules/module3/ -q
uv run python -m pytest modules/module4/ -q
```

### Linting and Type Checking

```bash
just lint       # Check with ruff
just typecheck  # Type check with ty
just fmt        # Format code
```

## Database Infrastructure

The project uses a self-hosted MusicBrainz Postgres mirror for fast metadata access:

| Data | Records | Source |
|------|---------|--------|
| Recordings | 38M | MusicBrainz mirror (Postgres) |
| Artists | 2.8M | MusicBrainz mirror |
| Genre tags | 6.8M | MusicBrainz mirror |
| Canonical search | 30M | Pre-joined table with GIN full-text index |
| Audio features | ~2M | AcousticBrainz API (archived, batch access) |
| Similarity graph | Live | ListenBrainz API (no rate limit) |

See [dblearn/README.md](./dblearn/README.md) for full database documentation.

## Checkpoint Log

| Checkpoint | Date | Modules | Status | Evidence |
|------------|------|---------|--------|----------|
| 1 | Feb 11 | Module 1 | Complete | 44 tests, research-grounded algorithms, [rubric](./rubrics/checkpoint-1.md) |
| 2 | Feb 26 | Module 2 + 3 | Complete | 135 tests, [rubric](./rubrics/checkpoint-2.md) |
| 3 | Mar 12 | DB Integration | In Progress | Postgres-backed MB client, benchmark suite |
| 4 | Apr 2 | Module 4 | In Progress | Mood classifier, DB training pipeline |

## References

### Data Sources
- [MusicBrainz](https://musicbrainz.org/) - Open music metadata (38M+ recordings)
- [AcousticBrainz](https://acousticbrainz.org/) - Audio feature database (archived 2022, ~2M recordings)
- [ListenBrainz](https://listenbrainz.org/) - User listening data and similarity graph

### Research
- Krumhansl, C. L. (1990). *Cognitive Foundations of Musical Pitch*. Oxford University Press.
- Drake, C., & Botte, M. C. (1993). Tempo sensitivity in auditory sequences. *Perception & Psychophysics*.
- Aucouturier, J. J., & Pachet, F. (2002). Music similarity measures: What's the use? *ISMIR*.

### Libraries
- [ProbLog](https://dtai.cs.kuleuven.be/problog/) - Probabilistic logic programming
- [scikit-learn](https://scikit-learn.org/) - Machine learning (mood classification)
- [psycopg](https://www.psycopg.org/) - PostgreSQL adapter (connection pooling)
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [React](https://react.dev/) - Frontend framework
