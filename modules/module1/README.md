# Module 1: Music Feature Knowledge Base

A probabilistic knowledge base for music theory rules and track compatibility scoring, built with ProbLog and a clean Python API.

## Overview

This module encodes music theory knowledge as logical rules to evaluate transition compatibility between tracks. It serves as the foundational constraint validator for the Wave Guide playlist generation system.

**AI Topics:** Propositional Logic, Knowledge Bases, Inference, Logical Rules

## Features

- **Research-grounded compatibility functions** based on music perception literature
- **7-component scoring**: key, tempo, energy, loudness, mood, timbre, genre
- **ProbLog integration** for probabilistic inference (hidden behind clean Python API)
- **User preferences** for customizable weighting and constraints
- **Playlist validation** for multi-track sequence analysis

## Architecture

```
module1/
├── knowledge_base.py    # MusicKnowledgeBase class (public API)
├── data_models.py       # TrackFeatures, TransitionResult, UserPreferences
├── data_loader.py       # AcousticBrainz JSON parsing
├── rules_helpers.py     # Compatibility probability functions
├── music_theory.pl      # ProbLog rules (mood, genre aggregation)
└── test_main.py         # Unit tests
```

## Usage

### Basic Compatibility Query

```python
from module1 import MusicKnowledgeBase, load_track_from_files

# Initialize knowledge base
kb = MusicKnowledgeBase()

# Load tracks from AcousticBrainz JSON files
track1 = load_track_from_files("track1_low.json", "track1_high.json")
track2 = load_track_from_files("track2_low.json", "track2_high.json")

# Query compatibility
result = kb.get_compatibility(track1, track2)

print(f"Compatibility: {result.probability:.1%}")
print(f"Is Compatible: {result.is_compatible}")
print(f"Penalty (for A*): {result.penalty:.3f}")

# Component scores
print(f"Key: {result.key_compatibility:.1%}")
print(f"Tempo: {result.tempo_compatibility:.1%}")
print(f"Energy: {result.energy_compatibility:.1%}")
print(f"Mood: {result.mood_compatibility:.1%}")
```

### With User Preferences

```python
from module1 import MusicKnowledgeBase, UserPreferences

kb = MusicKnowledgeBase()

# Customize weights and constraints
kb.set_preferences(UserPreferences(
    prefer_consistent_tempo=True,
    target_moods=["relaxed", "happy"],
    mood_weight=0.25,  # Increase mood importance
    tempo_weight=0.15,
))

result = kb.get_compatibility(track1, track2)
```

### Playlist Validation

```python
# Validate a complete playlist sequence
tracks = [track1, track2, track3, track4]
validation = kb.validate_playlist(tracks)

print(f"Overall Score: {validation.overall_probability:.1%}")
print(f"Valid: {validation.is_valid}")
print(f"Weakest Transition: {validation.weakest_transition}")
```

## Compatibility Algorithms

### Key Compatibility (Krumhansl-Kessler)

Based on *Cognitive Foundations of Musical Pitch* (Krumhansl, 1990). Uses probe-tone profile correlation to measure perceived key similarity.

```python
# Pearson correlation between 12-tone profiles, mapped to [0, 1]
p_key = (correlation + 1.0) / 2.0
```

### Tempo Compatibility (Weber's Law)

Based on Drake & Botte (1993). Just-noticeable difference (JND) for tempo is ~4% of reference BPM. Uses Gaussian decay with 3x JND as sigma.

```python
# Handles double-time/half-time relationships
delta = min(direct_diff, double_time_diff, half_time_diff)
p_tempo = exp(-delta^2 / (2 * 0.12^2))
```

### Timbre Compatibility (Bhattacharyya)

Based on Aucouturier & Pachet (2002). Compares MFCC distributions using Bhattacharyya coefficient (distribution overlap measure).

```python
# BC = exp(-D_B) where D_B is Bhattacharyya distance
# Excludes c0 to avoid double-counting with loudness
p_timbre = exp(-bhattacharyya_distance(mfcc1, mfcc2))
```

### Energy & Loudness

Gaussian decay on absolute differences, with sigma values calibrated to AcousticBrainz data ranges.

## Data Models

### TrackFeatures

71-dimensional feature vector from AcousticBrainz:
- **Rhythm**: BPM, onset rate, beats count
- **Tonal**: Key, scale, key strength, chords strength
- **Energy**: Spectral energy bands (low, mid-low, mid-high, high)
- **Dynamics**: Average loudness, dynamic complexity
- **Timbre**: MFCC mean and covariance (13 coefficients)
- **Mood**: Binary classifiers (happy, sad, aggressive, relaxed, party, acoustic)
- **Genre**: 8-class distribution (rosamerica taxonomy)

### TransitionResult

```python
@dataclass
class TransitionResult:
    probability: float      # P(smooth_transition) in [0, 1]
    penalty: float          # 1 - probability, for A* search
    is_compatible: bool     # probability > threshold (0.3)

    # Component scores
    key_compatibility: float
    tempo_compatibility: float
    energy_compatibility: float
    loudness_compatibility: float
    mood_compatibility: float
    timbre_compatibility: float
    genre_compatibility: float

    violations: list[str]   # Human-readable issues
    explanation: str        # Detailed breakdown
```

### UserPreferences

```python
@dataclass
class UserPreferences:
    # Constraints
    min_bpm: float | None = None
    max_bpm: float | None = None
    prefer_consistent_tempo: bool = True

    # Mood targeting
    target_moods: list[str] | None = None
    avoid_moods: list[str] | None = None

    # Component weights (sum to ~1.0)
    key_weight: float = 0.15
    tempo_weight: float = 0.20
    energy_weight: float = 0.15
    loudness_weight: float = 0.05
    mood_weight: float = 0.15
    timbre_weight: float = 0.20
    genre_weight: float = 0.10
```

## Testing

```bash
# Run module tests
uv run pytest modules/module1 -v

# Run interactive test suite
uv run python -m module1.unit_tests
```

### Expected Results

| Scenario | Expected Compatibility |
|----------|----------------------|
| Same track twice | >90% |
| Same genre (Classical/Classical) | 70-80% |
| Cross-genre (Pop/Classical) | 40-50% |
| With matching mood preferences | +5-10% boost |

## Integration

This module provides the cost function for Module 2 (Beam Search):

```python
# In Module 2's search algorithm
def transition_cost(track1, track2):
    result = kb.get_compatibility(track1, track2)
    return result.penalty  # 1 - probability
```

## References

- Krumhansl, C. L. (1990). *Cognitive Foundations of Musical Pitch*
- Drake, C., & Botte, M. C. (1993). Tempo sensitivity in auditory sequences
- Aucouturier, J. J., & Pachet, F. (2002). Music similarity measures: What's the use?
- Berenzweig, A. et al. (2004). A large-scale evaluation of acoustic and subjective music-similarity measures
