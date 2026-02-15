# Wave Guide: Your Personal Music Journey

## Overview

Wave Guide creates personalized music playlists that take listeners on a "journey" from a starting track to a destination track, discovering new music along the way. Unlike traditional recommendation systems that optimize for similarity alone, Wave Guide treats playlist generation as a path-finding problem through multidimensional audio feature space.

The system addresses a critical limitation in existing music platforms: Spotify recently restricted API access to recommendation endpoints, making proprietary solutions unsustainable. Wave Guide leverages AcousticBrainz, an open-source database containing acoustic analysis for millions of tracks (71-dimensional feature vectors including energy, valence, timbre, rhythm, and tonal characteristics).

Users specify source and destination tracks (or moods). The system encodes music theory knowledge and transition smoothness rules as a propositional logic knowledge base, then uses search algorithms to find optimal paths through feature space that satisfy these constraints. The final playlist balances smooth transitions, stylistic diversity, and adherence to music theory principles.

## Team

- Michael Thomas
- Rahul Ranjan Sah
- Mohammed Ibrahim

## Proposal

See [PROPOSAL.md](./PROPOSAL.md) for the full system proposal including detailed module specifications and feasibility study.

## Module Plan

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Probabalistic Logic (KB, Inference, Rules) | AcousticBrainz feature JSON, user constraints | Knowledge base with compatibility scoring | None | 1 |
| 2 | Search (Beam Search) | Source/dest feature vectors, KB rules | Ordered waypoint sequence | Module 1 | 1 |
| 3 | Simulated Annealing | Playlist with metadata | Optimized playlist ordering | Module 2 | 2 |
| 4 | Machine Learning (Supervised) | Feature vectors or mood labels | Mood classification / feature mapping | None | 4 |
| 5 | System Integration | User input, all module outputs | Complete validated playlist | Modules 1-4 | 5 |

## Repository Layout

```
wave-guide/
├── modules/
│   ├── module1/                      # Music Feature Knowledge Base
│   │   ├── src/module1/
│   │   │   ├── knowledge_base.py     # ProbLog-based KB with Python API
│   │   │   ├── data_models.py        # TrackFeatures, TransitionResult, etc.
│   │   │   ├── data_loader.py        # AcousticBrainz JSON parsing
│   │   │   ├── rules_helpers.py      # Research-grounded compatibility functions
│   │   │   ├── music_theory.pl       # ProbLog rules
│   │   │   └── test_main.py          # Unit tests
│   │   └── test_files/               # Sample AcousticBrainz data
│   └── api/                          # Flask REST API wrapper
│       └── src/api/app.py
├── web/                              # React TypeScript frontend
│   └── src/App.tsx
├── plans/                            # Module planning documentation
├── .claude/skills/code-review/       # Rubric-based review skill
├── PROPOSAL.md                       # Detailed system proposal
├── AGENTS.md                         # LLM agent instructions
├── UNIT_TEST_RESULTS.md              # Test execution summary
└── README.md                         # This file
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ and pnpm (for web frontend)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd project-2-ai-system-rocking-rolling

# Install Python dependencies
uv sync

# Install web dependencies (optional, for frontend)
cd web && pnpm install && cd ..
```

### Environment

No environment variables required for core functionality. The system fetches data from the public AcousticBrainz API.

## Running

### Interactive Demo

```bash
# Run the Module 1 interactive demo
uv run python -m module1.main
```

### Web Interface

```bash
# Run both Flask API and React frontend
just serve
```

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/compare?recording_id_1=<MBID>&recording_id_2=<MBID>` - Compare two tracks by MusicBrainz ID

## Testing

### Run All Tests

```bash
just test
```

### Test Coverage

Module 1 includes 6 pytest tests covering:
- Same track comparison (expects >70% compatibility)
- Cross-genre comparison (Pop vs Classical)
- Same-genre comparison (Classical vs Classical)
- Low-level only data handling
- Component score validation

See [UNIT_TEST_RESULTS.md](./UNIT_TEST_RESULTS.md) for detailed test results and interpretation guide.

### Linting and Type Checking

```bash
just lint       # Check with ruff
just typecheck  # Type check with ty
just fmt        # Format code
```

## Checkpoint Log

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 | Feb 11 | Module 1 | Complete | 6 tests passing, research-grounded algorithms |
| 2 | Feb 26 | Module 3 | Pending | |
| 3 | Mar 12 | | Pending | |
| 4 | Apr 2 | Module 4 | Pending | |

## References

### Data Sources
- [AcousticBrainz](https://acousticbrainz.org/) - Open music feature database (71-dimensional vectors)
- [MusicBrainz](https://musicbrainz.org/) - Music metadata database

### Research
- Krumhansl, C. L. (1990). *Cognitive Foundations of Musical Pitch*. Oxford University Press.
- Drake, C., & Botte, M. C. (1993). Tempo sensitivity in auditory sequences. *Perception & Psychophysics*.
- Aucouturier, J. J., & Pachet, F. (2002). Music similarity measures: What's the use? *ISMIR*.

### Libraries
- [ProbLog](https://dtai.cs.kuleuven.be/problog/) - Probabilistic logic programming
- [NumPy](https://numpy.org/) - Numerical computing
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [React](https://react.dev/) - Frontend framework
