# Module 1: Music Feature Knowledge Base - Implementation Plan

## Module Overview

**Purpose:** Module 1 implements the foundational constraint validation system for the Wave Guide playlist generator. It encodes music theory knowledge as **probabilistic logic rules** using ProbLog and provides an inference engine to evaluate track transition smoothness with uncertainty quantification.

**Topics Covered:** Probabilistic Logic (Probabilistic Knowledge Bases, Probabilistic Inference, Logical Rules with Uncertainty, Probabilistic Entailment)

**Integration Points:**
- **Module 2 (A* Search):** Provides `get_transition_penalty()` method for path cost calculations
- **Module 5 (Playlist Assembly):** Provides `validate_playlist()` for final constraint checking

---

## Technical Specifications

### Inputs
- **AcousticBrainz feature data:** Two JSON files per track (lowlevel + highlevel) containing spectral, rhythmic, tonal, and mood features
- **User-defined constraints (optional):** Tempo range preferences, key compatibility requirements, mood specifications

### Outputs
- **Probabilistic knowledge base:** Music theory rules encoded as ProbLog program (.pl file)
- **Inference engine:** ProbLog-based probabilistic reasoning that computes transition quality probabilities
- **Validation results:** Probabilistic assessments of transition smoothness with confidence measures (e.g., P(smooth_transition | evidence) = 0.85)

### Key Features
1. **Probabilistic music theory rule encoding:** Key compatibility, tempo transitions, energy progression, and mood coherence as probabilistic logic rules in ProbLog
2. **Uncertainty-aware transition validation:** Evaluates track pairs considering measurement uncertainty and feature confidence
3. **Probabilistic path cost:** Provides probability-based cost function (1 - P(smooth_transition)) for Module 2's A* search
4. **Bayesian playlist validation:** Batch validation using probabilistic inference over complete sequences

---

## Data Model Design

### AcousticBrainz JSON Structure

AcousticBrainz data comes in **two separate JSON files** per track:

#### 1. Lowlevel JSON
Contains rhythm, tonal, and spectral features from Essentia streaming extractor:

```json
{
  "rhythm": {
    "bpm": 148.126,
    "danceability": 0.8601,
    "onset_rate": 0.6895,
    "beats_position": [0.406, 0.824, 1.242, ...],
    "beats_count": 233
  },
  "tonal": {
    "key_key": "C#",
    "key_scale": "minor",
    "key_strength": 0.7769,
    "tuning_frequency": 442.037,
    "chords_strength": {"mean": 0.5248, "var": 0.0098, ...}
  },
  "lowlevel": {
    "spectral_energyband_low": {"mean": 0.0031, ...},
    "spectral_energyband_middle_low": {"mean": 0.0108, ...},
    "spectral_energyband_middle_high": {"mean": ..., ...},
    "spectral_energyband_high": {"mean": ..., ...},
    "mfcc": {"mean": [0.326e-3, 0.681e-3, ...], ...},
    "spectral_centroid": {"mean": ..., ...},
    "dissonance": {"mean": ..., ...},
    "average_loudness": ...,
    "dynamic_complexity": ...
  }
}
```

#### 2. Highlevel JSON
Contains mood, genre, and semantic classifiers from trained SVM models:

```json
{
  "highlevel": {
    "danceability": {
      "value": "not_danceable",
      "probability": 0.9586,
      "all": {"danceable": 0.0414, "not_danceable": 0.9586}
    },
    "mood_happy": {"value": "not_happy", "probability": 0.9747, ...},
    "mood_sad": {"value": "sad", "probability": 0.9112, ...},
    "mood_aggressive": {...},
    "mood_relaxed": {...},
    "mood_party": {...},
    "timbre": {"value": "dark", ...}
  },
  "metadata": {
    "tags": {
      "title": ["The Lost Art of Conversation"],
      "artist": ["Pink Floyd"],
      "musicbrainz_recordingid": ["564ccd5c-c4d3-4752-9abf-c33bb085d6a5"]
    }
  }
}
```

**Key Observations:**
1. **Two-file structure:** Module must load and merge both JSONs
2. **Statistical aggregations:** Most lowlevel features have `mean`, `median`, `var`, etc. We primarily use `mean` values
3. **Scalar vs aggregated:** Some features are scalars (e.g., `rhythm.bpm`), others are aggregated objects
4. **Binary classifiers:** Highlevel moods use binary classification with probabilities
5. **Feature overlap:** When a feature appears in both lowlevel and highlevel (e.g., danceability), **prefer highlevel version**

### Track Data Model

```python
from dataclasses import dataclass

@dataclass
class TrackFeatures:
    """Represents extracted features from AcousticBrainz lowlevel + highlevel data."""

    # Metadata (from highlevel.metadata.tags)
    mbid: str  # MusicBrainz recording ID
    title: str | None = None
    artist: str | None = None
    album: str | None = None

    # Rhythm (from lowlevel.rhythm) - scalar values
    bpm: float
    onset_rate: float
    beats_count: int

    # Danceability: PREFER highlevel if available, fallback to lowlevel
    danceability: float | tuple[str, float] | None = None  # lowlevel: float, highlevel: (value, prob)

    # Tonal (from lowlevel.tonal)
    key: str  # e.g., "C#", "F"
    scale: str  # "major" or "minor"
    key_strength: float
    tuning_frequency: float
    chords_strength: float  # Extract from .mean

    # Energy (from lowlevel.lowlevel)
    energy_low: float  # spectral_energyband_low.mean
    energy_mid_low: float  # spectral_energyband_middle_low.mean
    energy_mid_high: float  # spectral_energyband_middle_high.mean
    energy_high: float  # spectral_energyband_high.mean

    # Loudness/dynamics (from lowlevel.lowlevel) - scalars
    average_loudness: float | None = None
    dynamic_complexity: float | None = None

    # Spectral characteristics (from lowlevel.lowlevel)
    mfcc: list[float] | None = None  # Extract from mfcc.mean array (40 dims)
    spectral_centroid: float | None = None  # Extract from spectral_centroid.mean
    dissonance: float | None = None  # Extract from dissonance.mean

    # High-level mood descriptors (from highlevel.highlevel)
    # Store as tuple: (binary_value: str, probability: float)
    mood_happy: tuple[str, float] | None = None  # ("happy"/"not_happy", prob)
    mood_sad: tuple[str, float] | None = None
    mood_aggressive: tuple[str, float] | None = None
    mood_relaxed: tuple[str, float] | None = None
    mood_party: tuple[str, float] | None = None
    mood_acoustic: tuple[str, float] | None = None
    timbre: tuple[str, float] | None = None  # ("bright"/"dark", prob)

    # Derived/computed fields
    @property
    def energy_score(self) -> float:
        """Compute weighted energy score from frequency bands."""
        return (
            0.1 * self.energy_low +
            0.2 * self.energy_mid_low +
            0.4 * self.energy_mid_high +
            0.3 * self.energy_high
        )

    @property
    def is_happy(self) -> bool:
        """Check if track classified as happy (with confidence > 0.5)."""
        return self.mood_happy is not None and self.mood_happy[0] == "happy"

    @property
    def is_sad(self) -> bool:
        """Check if track classified as sad."""
        return self.mood_sad is not None and self.mood_sad[0] == "sad"

    @property
    def is_aggressive(self) -> bool:
        """Check if track classified as aggressive."""
        return self.mood_aggressive is not None and self.mood_aggressive[0] == "aggressive"

    @property
    def is_relaxed(self) -> bool:
        """Check if track classified as relaxed."""
        return self.mood_relaxed is not None and self.mood_relaxed[0] == "relaxed"
```

### Data Extraction Strategy

**Priority:** When a feature appears in both lowlevel and highlevel datasets, **prefer the highlevel version**.

**Extraction Rules:**
- **Scalars:** Use directly (e.g., `rhythm.bpm`)
- **Aggregated:** Extract `.mean` value (e.g., `chords_strength.mean`)
- **Arrays:** Extract `.mean` array (e.g., `mfcc.mean`)
- **Highlevel:** Extract `value` and `probability` as tuple
- **Missing values:** Use `None` for optional features
- **Danceability special case:**
  - If `highlevel.danceability` exists: use `(value, probability)` tuple
  - Else if `lowlevel.rhythm.danceability` exists: use float value
  - Otherwise: `None`

---

## Probabilistic Logic Framework with ProbLog

### Why ProbLog?

ProbLog extends Prolog with probabilistic reasoning, allowing us to:
1. **Encode uncertainty:** Music features come with confidence scores (e.g., `key_strength: 0.7769`). ProbLog naturally represents this uncertainty.
2. **Combine evidence:** Integrate multiple uncertain features (key, tempo, energy, mood) into coherent probabilistic judgments.
3. **Perform inference:** Compute probabilities like P(smooth_transition | track1_features, track2_features).
4. **Handle missing data:** Gracefully reason when features are absent by marginalizing over unknowns.

### ProbLog Basics

**Probabilistic Facts:**
```problog
0.8::key_compatible(track1, track2).  % 80% probability of key compatibility
```

**Deterministic Rules:**
```problog
smooth_transition(T1, T2) :- key_compatible(T1, T2), tempo_compatible(T1, T2).
```

**Queries:**
```problog
query(smooth_transition(track1, track2)).  % Computes P(smooth_transition)
```

### Knowledge Base Architecture

The ProbLog knowledge base will consist of:

1. **Facts Database (Python-generated):**
   - Track feature facts (loaded from AcousticBrainz data)
   - Feature confidence scores
   - User constraints

2. **Rules Program (`music_theory.pl`):**
   - Probabilistic rules for key compatibility
   - Probabilistic rules for tempo transitions
   - Energy progression rules
   - Mood coherence rules
   - Composite smoothness rules

3. **Query Interface (Python API):**
   - Generate ProbLog queries from track pairs
   - Execute inference via ProbLog Python library
   - Extract probability results

### Example: music_theory.pl Structure

```problog
% ============================================================================
% Music Theory Knowledge Base for Wave Guide
% Probabilistic Logic Rules for Transition Smoothness
% ============================================================================

% ----------------------------------------------------------------------------
% Helper Predicates (Deterministic)
% ----------------------------------------------------------------------------

% Circle of fifths distance (computed in Python, facts added dynamically)
% circle_distance(Key1, Key2, Distance).

% Double-time detection
is_double_time(BPM1, BPM2) :-
    Ratio is BPM1 / BPM2,
    (abs(Ratio - 2.0) < 0.1 ; abs(Ratio - 0.5) < 0.1).

% ----------------------------------------------------------------------------
% Key Compatibility Rules
% ----------------------------------------------------------------------------

% Same key and scale - very high probability (weighted by confidence)
P::key_compatible(T1, T2) :-
    has_key(T1, Key, Scale, Strength1),
    has_key(T2, Key, Scale, Strength2),
    P is min(0.95, Strength1 * Strength2).

% Parallel keys (same root, different mode)
P::key_compatible(T1, T2) :-
    has_key(T1, Key, major, Strength1),
    has_key(T2, Key, minor, Strength2),
    P is min(0.80, Strength1 * Strength2 * 0.85).

% Adjacent keys on circle of fifths
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_distance(K1, K2, 1),
    P is min(0.70, Strength1 * Strength2 * 0.75).

% Distant keys (low probability)
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_distance(K1, K2, Dist),
    Dist >= 3,
    BaseProb is max(0.10, 1.0 - (Dist / 6.0)),
    P is min(BaseProb, Strength1 * Strength2 * BaseProb).

% ----------------------------------------------------------------------------
% Tempo Compatibility Rules
% ----------------------------------------------------------------------------

% Imperceptible difference (< 5 BPM)
0.95::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    abs(BPM1 - BPM2) < 5.

% Smooth difference (5-10 BPM)
0.85::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    Diff is abs(BPM1 - BPM2),
    Diff >= 5, Diff < 10.

% Double-time exception (special case)
0.75::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    is_double_time(BPM1, BPM2).

% ----------------------------------------------------------------------------
% Energy Compatibility Rules
% ----------------------------------------------------------------------------

% Smooth energy transition
0.90::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    abs(E1 - E2) < 0.15.

% Moderate energy transition
0.75::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    Delta is abs(E1 - E2),
    Delta >= 0.15, Delta < 0.3.

% ----------------------------------------------------------------------------
% Composite Smoothness Rule
% ----------------------------------------------------------------------------

% A smooth transition requires compatibility across all dimensions
smooth_transition(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2),
    loudness_compatible(T1, T2),
    mood_compatible(T1, T2).

% Alternative: minimum compatibility threshold
% smooth_transition_threshold(T1, T2) :-
%     key_compatible(T1, T2),
%     tempo_compatible(T1, T2),
%     energy_compatible(T1, T2).

% ----------------------------------------------------------------------------
% Query Template (invoked from Python)
% ----------------------------------------------------------------------------

% query(smooth_transition(track1, track2)).
```

---

## Music Theory Rules (ProbLog Encoding)

### 1. Key Compatibility Rules (ProbLog)

**Features:** `tonal.key_key`, `tonal.key_scale`, `tonal.key_strength`

**Circle of Fifths Distance (Python Helper):**
```python
CIRCLE_OF_FIFTHS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'Db', 'Ab', 'Eb', 'Bb', 'F']

def circle_of_fifths_distance(key1: str, key2: str) -> int:
    """Returns 0-6 distance on circle of fifths."""
    # Implementation as before...
```

**ProbLog Encoding:**
```problog
% Base key compatibility probabilities based on circle of fifths distance
% Adjusted by key_strength confidence scores

% Same key and scale - very high probability (weighted by key strengths)
P::key_compatible(T1, T2) :-
    has_key(T1, K, S, Strength1),
    has_key(T2, K, S, Strength2),
    P is min(0.95, Strength1 * Strength2).

% Parallel keys (same root, different scale) - high probability
P::key_compatible(T1, T2) :-
    has_key(T1, K, S1, Strength1),
    has_key(T2, K, S2, Strength2),
    S1 \= S2,
    P is min(0.80, Strength1 * Strength2 * 0.85).

% Adjacent keys (1 step on circle of fifths) - moderate-high probability
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_distance(K1, K2, 1),
    P is min(0.70, Strength1 * Strength2 * 0.75).

% 2 steps away - moderate probability
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_distance(K1, K2, 2),
    P is min(0.50, Strength1 * Strength2 * 0.55).

% 3+ steps away - low probability
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_distance(K1, K2, D),
    D >= 3,
    BaseProb is max(0.05, 1.0 - (D / 6.0)),
    P is min(BaseProb, Strength1 * Strength2 * BaseProb).
```

**Python Integration:**
```python
def add_key_facts(kb: ProbLogBuilder, track_id: str, features: TrackFeatures):
    """Add key facts to ProbLog knowledge base."""
    kb.add_fact(f"has_key({track_id}, {features.key}, {features.scale}, {features.key_strength})")
```

### 2. Tempo Transition Rules (ProbLog)

**Features:** `rhythm.bpm`, `danceability`

**ProbLog Encoding:**
```problog
% Imperceptible tempo difference (< 5 BPM)
0.95::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    abs(BPM1 - BPM2) < 5.

% Smooth tempo difference (5-10 BPM)
0.85::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    Diff is abs(BPM1 - BPM2),
    Diff >= 5, Diff < 10.

% Noticeable but acceptable (10-20 BPM)
0.60::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    Diff is abs(BPM1 - BPM2),
    Diff >= 10, Diff < 20.

% Moderate transition (20-30 BPM)
0.35::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    Diff is abs(BPM1 - BPM2),
    Diff >= 20, Diff < 30.

% Large jump (>= 30 BPM) - very low probability
0.10::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    abs(BPM1 - BPM2) >= 30.

% Special case: double-time or half-time increases probability
0.70::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    is_double_time(BPM1, BPM2).

% Danceability boost: both tracks highly danceable
P::tempo_compatible_boosted(T1, T2) :-
    tempo_compatible(T1, T2),
    is_danceable(T1, D1), D1 > 0.7,
    is_danceable(T2, D2), D2 > 0.7,
    % Query base tempo_compatible probability and boost it
    true.  % Implementation uses probability lifting
```

### 3. Energy Progression Rules (ProbLog)

**Features:** Spectral energy bands, `dynamic_complexity`

**ProbLog Encoding:**
```problog
% Energy score computed in Python and passed as fact
% energy_score(track_id, Score) where Score in [0, 1]

% Smooth energy transition (delta < 0.15)
0.90::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    abs(E1 - E2) < 0.15.

% Moderate energy transition (0.15 <= delta < 0.3)
0.75::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    Delta is abs(E1 - E2),
    Delta >= 0.15, Delta < 0.3.

% Noticeable energy transition (0.3 <= delta < 0.5)
0.45::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    Delta is abs(E1 - E2),
    Delta >= 0.3, Delta < 0.5.

% Jarring energy transition (delta >= 0.5)
0.15::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    abs(E1 - E2) >= 0.5.

% Penalize low dynamic complexity tracks
P::energy_compatible_adjusted(T1, T2) :-
    energy_compatible(T1, T2),
    dynamic_complexity(T1, DC1), DC1 < 0.3,
    dynamic_complexity(T2, DC2), DC2 < 0.3,
    % Reduce probability by 20% for static tracks
    true.  % Implementation reduces base probability
```

### 4. Loudness Consistency

**Features:** `lowlevel.average_loudness` (LUFS)

**Thresholds:**
- |loudness_diff| < 3 LUFS: penalty = 0.0
- |loudness_diff| < 6 LUFS: penalty = 0.1
- |loudness_diff| < 10 LUFS: penalty = 0.3
- |loudness_diff| ≥ 10 LUFS: penalty = 0.7

### 5. Mood Coherence

**Features:** `highlevel.mood_*` descriptors

**Mood Compatibility Matrix:**
```
Same mood: 0.0
happy ↔ party: 0.1
relaxed ↔ sad: 0.2
aggressive ↔ happy: 0.7
aggressive ↔ relaxed: 0.9
```

**Fallback** (when highlevel unavailable):
```python
if energy_score > 0.7 and danceability > 0.6:
    mood = "energetic"
elif energy_score < 0.3 and dissonance < 0.3:
    mood = "calm"
elif dissonance > 0.6:
    mood = "intense"
```

### 6. Timbre Similarity

**Features:** `lowlevel.mfcc`, `spectral_centroid`

**MFCC Distance** (Euclidean in 13-D space):
- distance < 5.0: penalty = 0.0
- distance < 10.0: penalty = 0.3
- distance ≥ 10.0: penalty = 0.6

**Spectral Centroid Difference:**
- |centroid_diff| < 200 Hz: penalty = 0.0
- |centroid_diff| < 500 Hz: penalty = 0.1
- |centroid_diff| ≥ 500 Hz: penalty = 0.3

**Combined:** `0.7 * mfcc_penalty + 0.3 * centroid_penalty`

### 7. Composite Transition Smoothness (ProbLog)

**Master Rule combining all factors:**

```problog
% Smooth transition requires ALL compatibility conditions
% ProbLog automatically computes joint probability via independence or dependencies

smooth_transition(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2),
    loudness_compatible(T1, T2),
    mood_compatible(T1, T2),
    timbre_compatible(T1, T2).

% Alternative: weighted combination using annotated disjunction
% This allows different "types" of smoothness with different weights

smooth_transition_weighted(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2).

% Query for inference
query(smooth_transition(track1, track2)).
```

**Probability Interpretation:**
- ProbLog computes: P(smooth_transition | all_evidence)
- **Cost for A* search:** `cost = 1.0 - P(smooth_transition)`
- Example: P(smooth) = 0.85 → cost = 0.15

**Hard Constraints (via evidence):**
```problog
% Evidence can rule out transitions entirely
evidence(tempo_compatible(T1, T2), false) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    abs(BPM1 - BPM2) > 50.  % Absolute hard limit
```

---

## Implementation Components

### Component 1: Data Loader (`data_loader.py`)
- Parse both lowlevel and highlevel JSON files
- Extract features with proper type handling:
  - Scalars: direct extraction
  - Aggregated: extract `.mean`
  - Arrays: extract `.mean` array
  - Classifiers: extract `(value, probability)` tuple
- **Feature Priority:** Prefer highlevel over lowlevel when overlap exists
- Merge into single `TrackFeatures` object
- Validate data integrity (check required fields, validate ranges)

### Component 2: ProbLog Knowledge Base (`music_theory.pl`)
- **ProbLog rule file** containing:
  - Probabilistic key compatibility rules
  - Probabilistic tempo transition rules
  - Energy progression rules
  - Loudness consistency rules
  - Mood coherence rules
  - Timbre similarity rules
  - Composite smoothness rules
  - Helper predicates (circle_distance, is_double_time, etc.)

### Component 3: Music Knowledge Base (`knowledge_base.py`)

**Architecture:**
- **Clean Python interface** - no ProbLog types exposed in public API
- **Rules and facts separation** - `music_theory.pl` contains only rules; facts generated programmatically via `SimpleProgram`
- **User preferences** - configurable constraints that modify inference behavior
- **Dataclass-based API** - accepts `TrackFeatures` directly, returns Python primitives

**Data Models (`data_models.py`):**

```python
from dataclasses import dataclass, field

@dataclass
class UserPreferences:
    """User-configurable preferences that influence compatibility scoring."""

    # Tempo preferences
    min_bpm: float | None = None
    max_bpm: float | None = None
    prefer_consistent_tempo: bool = True

    # Key preferences
    allowed_keys: list[str] | None = None
    prefer_compatible_keys: bool = True

    # Energy preferences
    prefer_increasing_energy: bool = False
    prefer_decreasing_energy: bool = False
    max_energy_jump: float = 0.5

    # Mood preferences
    target_moods: list[str] | None = None
    avoid_moods: list[str] | None = None

    # Weights for combining scores
    key_weight: float = 0.25
    tempo_weight: float = 0.30
    energy_weight: float = 0.20
    loudness_weight: float = 0.10
    mood_weight: float = 0.10
    timbre_weight: float = 0.05


@dataclass
class TransitionResult:
    """Result of querying track compatibility."""

    probability: float
    penalty: float
    is_compatible: bool

    key_compatibility: float
    tempo_compatibility: float
    energy_compatibility: float
    loudness_compatibility: float
    mood_compatibility: float
    timbre_compatibility: float

    violations: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class PlaylistValidation:
    """Result of validating a complete playlist."""

    overall_probability: float
    overall_penalty: float
    is_valid: bool
    transitions: list[TransitionResult]
    weakest_transition: tuple[int, float] | None
    total_violations: int
```

**Public Interface (`knowledge_base.py`):**

```python
class MusicKnowledgeBase:
    """
    Probabilistic knowledge base for music theory rules.

    Provides a clean Python interface for querying track compatibility.
    All ProbLog internals are hidden from the public API.

    Example:
        kb = MusicKnowledgeBase()

        # Set user preferences
        kb.set_preferences(UserPreferences(
            prefer_consistent_tempo=True,
            target_moods=["happy", "party"]
        ))

        # Query compatibility between two tracks
        result = kb.get_compatibility(track1, track2)
        print(f"Compatibility: {result.probability:.2%}")
        print(f"A* cost: {result.penalty:.3f}")
    """

    def __init__(self, rules_file: str = "modules/module1/music_theory.pl"):
        """Initialize the knowledge base with music theory rules."""
        ...

    def set_preferences(self, preferences: UserPreferences) -> None:
        """Set user preferences for compatibility scoring."""
        ...

    def get_preferences(self) -> UserPreferences:
        """Get current user preferences."""
        ...

    def get_compatibility(
        self,
        track1: TrackFeatures,
        track2: TrackFeatures
    ) -> TransitionResult:
        """
        Query the compatibility between two tracks.

        This is the main public method. Returns probability of a smooth
        transition from track1 to track2.

        Args:
            track1: Source track features
            track2: Destination track features

        Returns:
            TransitionResult with probability, penalty, and component scores
        """
        ...

    def get_penalty(self, track1: TrackFeatures, track2: TrackFeatures) -> float:
        """
        Get the transition penalty for A* search (1 - probability).

        Args:
            track1: Source track
            track2: Destination track

        Returns:
            Penalty in [0.0, 1.0] where 0 = perfect transition
        """
        ...

    def validate_playlist(
        self,
        tracks: list[TrackFeatures]
    ) -> PlaylistValidation:
        """Validate a complete playlist sequence."""
        ...

    def clear(self) -> None:
        """Clear all registered tracks (but keep preferences)."""
        ...
```

**Implementation Details (private methods):**

```python
class MusicKnowledgeBase:
    # ... public methods above ...

    # -------------------------------------------------------------------------
    # Private methods (ProbLog internals hidden here)
    # -------------------------------------------------------------------------

    def _init_problog(self, rules_file: str) -> None:
        """Initialize ProbLog engine with rules.

        Uses the pattern from main.py:
        1. Load rules from PrologString (NO facts in music_theory.pl)
        2. Prepare database with DefaultEngine
        3. Create SimpleProgram for facts
        4. Extend base_db with facts when querying
        """
        from problog.program import PrologString, SimpleProgram
        from problog.engine import DefaultEngine
        from problog import get_evaluatable

        with open(rules_file, 'r') as f:
            rules_str = f.read()

        self._rules_program = PrologString(rules_str)
        self._engine = DefaultEngine()
        self._base_db = self._engine.prepare(self._rules_program)
        self._facts_program = SimpleProgram()
        self._db = None

    def _rebuild_db(self) -> None:
        """Rebuild database by extending base with current facts."""
        self._db = self._base_db.extend()
        for statement in self._facts_program:
            self._db += statement

    def _add_track_facts(self, track_id: str, features: TrackFeatures) -> None:
        """Convert TrackFeatures to ProbLog facts using Term objects."""
        from problog.logic import Term, Constant

        tid = Term(track_id)

        # Key facts: has_key(track_id, key, scale, strength)
        key = Term(features.key.lower().replace('#', '_sharp'))
        scale = Term(features.scale)
        self._facts_program += Term("has_key", tid, key, scale,
                                    Constant(features.key_strength))

        # BPM: has_bpm(track_id, bpm)
        self._facts_program += Term("has_bpm", tid, Constant(features.bpm))

        # Energy score: energy_score(track_id, score)
        self._facts_program += Term("energy_score", tid,
                                   Constant(features.energy_score))

        # ... additional facts for danceability, loudness, mood, etc.

        self._db = None  # Invalidate cached db

    def _add_preference_facts(self) -> None:
        """Add user preference facts to ProbLog."""
        from problog.logic import Term, Constant

        prefs = self._preferences

        if prefs.prefer_consistent_tempo:
            self._facts_program += Term("pref_consistent_tempo")

        if prefs.target_moods:
            for mood in prefs.target_moods:
                self._facts_program += Term("pref_target_mood", Term(mood))

        # ... additional preference facts

        self._db = None

    def _query_compatibility(self, id1: str, id2: str) -> dict[str, float]:
        """Query all compatibility components from ProbLog."""
        from problog.logic import Term

        if self._db is None:
            self._rebuild_db()

        t1, t2 = Term(id1), Term(id2)

        queries = [
            Term("smooth_transition", t1, t2),
            Term("key_compatible", t1, t2),
            Term("tempo_compatible", t1, t2),
            Term("energy_compatible", t1, t2),
            Term("loudness_compatible", t1, t2),
            Term("mood_compatible", t1, t2),
            Term("timbre_compatible", t1, t2),
        ]

        lf = self._engine.ground_all(self._db, queries=queries)
        result = self._get_evaluatable().create_from(lf).evaluate()

        return {
            "smooth_transition": result.get(queries[0], 0.0),
            "key_compatible": result.get(queries[1], 0.0),
            "tempo_compatible": result.get(queries[2], 0.0),
            "energy_compatible": result.get(queries[3], 0.0),
            "loudness_compatible": result.get(queries[4], 0.0),
            "mood_compatible": result.get(queries[5], 0.0),
            "timbre_compatible": result.get(queries[6], 0.0),
        }
```

**Usage (Clean Python API - no ProbLog knowledge required!):**

```python
from modules.module1.knowledge_base import MusicKnowledgeBase, UserPreferences
from modules.module1.data_loader import load_track_from_files

# Initialize KB
kb = MusicKnowledgeBase()

# Optionally set user preferences
kb.set_preferences(UserPreferences(
    prefer_consistent_tempo=True,
    target_moods=["happy", "party"],
    max_energy_jump=0.4
))

# Load tracks as dataclasses
track1 = load_track_from_files("sample_lowlevel.json", "sample_highlevel.json")
track2 = load_track_from_files("track2_lowlevel.json", "track2_highlevel.json")

# Query compatibility - simple Python interface!
result = kb.get_compatibility(track1, track2)

print(f"Compatibility: {result.probability:.1%}")
print(f"A* search cost: {result.penalty:.3f}")
print(f"Key compatible: {result.key_compatibility:.1%}")
print(f"Tempo compatible: {result.tempo_compatibility:.1%}")

if result.violations:
    print(f"Violations: {', '.join(result.violations)}")

# For Module 2 integration - just get the penalty
cost = kb.get_penalty(track1, track2)

# Validate a complete playlist
playlist = [track1, track2, track3, track4]
validation = kb.validate_playlist(playlist)
print(f"Playlist valid: {validation.is_valid}")
```

### Component 4: Helper Functions (`rules_helpers.py`)

**Python functions callable from ProbLog using `@problog_export`:**

```python
from problog.extern import problog_export
import numpy as np

@problog_export('+str', '+str', '-int')
def circle_of_fifths_distance(key1: str, key2: str) -> int:
    """
    Compute distance on circle of fifths (callable from ProbLog).

    Args:
        key1, key2: Keys like 'c', 'c_sharp', 'd', etc.

    Returns:
        Distance 0-6
    """
    CIRCLE_OF_FIFTHS = [
        'c', 'g', 'd', 'a', 'e', 'b',
        'f_sharp', 'd_flat', 'a_flat', 'e_flat', 'b_flat', 'f'
    ]

    # Normalize keys
    key1 = normalize_key(key1)
    key2 = normalize_key(key2)

    try:
        idx1 = CIRCLE_OF_FIFTHS.index(key1)
        idx2 = CIRCLE_OF_FIFTHS.index(key2)
    except ValueError:
        return 6  # Maximum distance for unknown keys

    # Circular distance
    forward = (idx2 - idx1) % 12
    backward = (idx1 - idx2) % 12
    return min(forward, backward)

def normalize_key(key: str) -> str:
    """Normalize enharmonic equivalents."""
    enharmonic_map = {
        'g_flat': 'f_sharp',
        'g_sharp': 'a_flat',
        'a_sharp': 'b_flat',
        'c_sharp': 'd_flat',
        'd_sharp': 'e_flat',
    }
    return enharmonic_map.get(key, key)

@problog_export('+float', '+float', '-bool')
def is_double_time(bpm1: float, bpm2: float) -> bool:
    """Check if BPMs are in 2:1 or 1:2 ratio (callable from ProbLog)."""
    if bpm2 == 0:
        return False

    ratio = bpm1 / bpm2
    tolerance = 0.1

    return (
        abs(ratio - 2.0) < tolerance or
        abs(ratio - 0.5) < tolerance
    )

@problog_export('+list', '+list', '-float')
def mfcc_distance(mfcc1: list, mfcc2: list) -> float:
    """Compute Euclidean distance between MFCC vectors."""
    arr1 = np.array(mfcc1[:13])  # Use first 13 coefficients
    arr2 = np.array(mfcc2[:13])
    return float(np.linalg.norm(arr1 - arr2))
```

**Using Python functions in ProbLog:**

In `music_theory.pl`:
```problog
% Import Python helper module
:- use_module('modules/module1/rules_helpers.py').

% Use Python function in a rule
P::key_compatible(T1, T2) :-
    has_key(T1, K1, _, Strength1),
    has_key(T2, K2, _, Strength2),
    circle_of_fifths_distance(K1, K2, Dist),
    Dist =< 1,
    P is min(0.75, Strength1 * Strength2 * 0.8).

% Use is_double_time Python function
0.75::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    is_double_time(BPM1, BPM2).

% Use MFCC distance
P::timbre_compatible(T1, T2) :-
    has_mfcc(T1, MFCC1),
    has_mfcc(T2, MFCC2),
    mfcc_distance(MFCC1, MFCC2, Dist),
    Dist < 10.0,
    P is max(0.3, 1.0 - (Dist / 20.0)).
```

**Notes:**
- `@problog_export` decorator specifies argument types: `+` for input, `-` for output
- Type codes: `str` (string), `int` (integer), `float` (float), `bool` (boolean), `list` (list)
- ProbLog automatically converts between Python and Prolog representations
- Python functions must be in a module that ProbLog can import

---

## File Structure

```
modules/module1/
├── main.py                    # Entry point (demo usage)
├── knowledge_base.py          # MusicKnowledgeBase class (clean Python API)
├── music_theory.pl            # ProbLog rules ONLY (no facts)
├── data_models.py             # TrackFeatures, UserPreferences, TransitionResult, etc.
├── data_loader.py             # AcousticBrainz JSON parsing
├── rules_helpers.py           # Python helper functions (@problog_export)
├── test_files/                # EXISTING sample data
│   ├── sample_lowlevel.json   # Pink Floyd track (lowlevel)
│   └── sample_highlevel.json  # Pink Floyd track (highlevel)
├── tests/                     # Unit tests
│   ├── test_knowledge_base.py # Test public API
│   ├── test_data_loader.py
│   └── test_integration.py    # End-to-end tests
└── README.md                  # Module documentation
```

**Key Design Decisions:**
- `knowledge_base.py` encapsulates ALL ProbLog internals - public API uses only Python types
- `music_theory.pl` contains ONLY rules - facts are generated programmatically via `SimpleProgram`
- `data_models.py` defines `TrackFeatures`, `UserPreferences`, `TransitionResult`, `PlaylistValidation`
- No `problog_interface.py` - ProbLog logic is private implementation detail of `MusicKnowledgeBase`

---

## Dependencies

**Add to `pyproject.toml`:**
```toml
dependencies = [
    "numpy>=2.0.0",
    "problog>=2.2.4",  # Probabilistic logic programming
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
]
```

**Type Hints:** Use Python 3.13 native syntax (`list[str]`, `dict[str, int]`). Only import from `typing` for advanced types (`Protocol`, `TypedDict`, `Literal`).

**Installing ProbLog:**
```bash
pip install problog
# Or for development version:
pip install --pre problog
```

**Key ProbLog Imports:**
```python
from problog.program import PrologString  # Create programs from strings
from problog import get_evaluatable       # Get evaluator for inference
from problog.logic import Term, Constant, Var  # For programmatic construction
from problog.program import SimpleProgram  # For building programs in Python
from problog.engine import DefaultEngine   # For low-level Prolog queries
```

---

## Development Checklist

### Phase 1: Data Models (`data_models.py`)
- [ ] Define `TrackFeatures` dataclass with all AcousticBrainz fields
  - [ ] Add `@property` methods for derived values (`energy_score`, `is_happy`, etc.)
- [ ] Define `UserPreferences` dataclass for user configuration
  - [ ] Tempo preferences (min/max BPM, prefer_consistent_tempo)
  - [ ] Key preferences (allowed_keys, prefer_compatible_keys)
  - [ ] Energy preferences (prefer_increasing/decreasing, max_energy_jump)
  - [ ] Mood preferences (target_moods, avoid_moods)
  - [ ] Component weights (key_weight, tempo_weight, etc.)
- [ ] Define `TransitionResult` dataclass
  - [ ] probability, penalty, is_compatible
  - [ ] Component probabilities (key, tempo, energy, loudness, mood, timbre)
  - [ ] violations, explanation
- [ ] Define `PlaylistValidation` dataclass

### Phase 2: Data Loader (`data_loader.py`)
- [ ] Implement `load_track_from_files(lowlevel_path, highlevel_path)` function
  - [ ] Handle statistical aggregations (extract `.mean`)
  - [ ] **Implement highlevel preference when features overlap**
  - [ ] Handle missing/optional features
  - [ ] Validate data integrity
- [ ] Test with `test_files/sample_*.json`

### Phase 3: ProbLog Rules (`music_theory.pl`)
- [ ] Create `music_theory.pl` with **rules only** (no facts):
  - [ ] Probabilistic key compatibility rules
  - [ ] Probabilistic tempo transition rules
  - [ ] Energy progression rules
  - [ ] Loudness consistency rules
  - [ ] Mood coherence rules
  - [ ] Timbre similarity rules
  - [ ] Composite `smooth_transition` rule
  - [ ] User preference rules (pref_target_mood, pref_consistent_tempo, etc.)
- [ ] Implement Python helpers in `rules_helpers.py`:
  - [ ] `circle_of_fifths_distance(key1, key2)` with `@problog_export`
  - [ ] `normalize_key(key)`
  - [ ] `is_double_time(bpm1, bpm2)` with `@problog_export`

### Phase 4: Knowledge Base (`knowledge_base.py`)
- [ ] Implement `MusicKnowledgeBase` class with **clean Python API**:
  - [ ] **Public methods (no ProbLog types!):**
    - [ ] `__init__(rules_file)` - Initialize ProbLog engine
    - [ ] `set_preferences(preferences: UserPreferences)` - Set user preferences
    - [ ] `get_preferences() -> UserPreferences`
    - [ ] `get_compatibility(track1, track2) -> TransitionResult`
    - [ ] `get_penalty(track1, track2) -> float` (for A* search)
    - [ ] `validate_playlist(tracks) -> PlaylistValidation`
    - [ ] `clear()` - Reset registered tracks
  - [ ] **Private methods (ProbLog internals hidden):**
    - [ ] `_init_problog()` - Load rules via `PrologString`, prepare with `DefaultEngine`
    - [ ] `_rebuild_db()` - Extend base_db with facts from `SimpleProgram`
    - [ ] `_add_track_facts()` - Convert TrackFeatures to ProbLog `Term` objects
    - [ ] `_add_preference_facts()` - Convert UserPreferences to ProbLog facts
    - [ ] `_query_compatibility()` - Use `engine.ground_all()` + `get_evaluatable()`
    - [ ] `_build_explanation()` - Generate human-readable explanation
- [ ] Add docstrings and type hints (Python 3.13 syntax)

### Phase 5: Testing
- [ ] Write unit tests for data loader:
  - [ ] Test with sample files
  - [ ] Test highlevel preference behavior
  - [ ] Test missing features handling
- [ ] Write unit tests for knowledge base public API:
  - [ ] Test `get_compatibility()` returns correct `TransitionResult`
  - [ ] Test `get_penalty()` returns float in [0, 1]
  - [ ] Test `set_preferences()` affects results
  - [ ] Test `validate_playlist()` with multiple tracks
- [ ] Write tests for probabilistic inference:
  - [ ] Test known good transitions (high probability)
  - [ ] Test known bad transitions (low probability)
  - [ ] Test edge cases (same track, missing features)
  - [ ] Verify probability bounds (0.0-1.0)
- [ ] Achieve >80% test coverage

### Phase 6: Documentation & Integration
- [ ] Write module README.md
- [ ] Update `main.py` with demonstration using clean API
- [ ] Document interface for Module 2 integration:
  - [ ] `kb.get_penalty(track1, track2)` returns cost for A* search

---

## Example Usage (Clean Python API)

### Basic Transition Query

```python
from modules.module1.knowledge_base import MusicKnowledgeBase, UserPreferences
from modules.module1.data_loader import load_track_from_files

# Initialize knowledge base
kb = MusicKnowledgeBase()

# Load tracks as dataclasses (no ProbLog knowledge needed!)
track1 = load_track_from_files(
    "modules/module1/test_files/sample_lowlevel.json",
    "modules/module1/test_files/sample_highlevel.json"
)
track2 = load_track_from_files(
    "path/to/track2_lowlevel.json",
    "path/to/track2_highlevel.json"
)

# Query compatibility - simple Python API!
result = kb.get_compatibility(track1, track2)

print(f"Compatibility: {result.probability:.1%}")
print(f"A* search cost: {result.penalty:.3f}")
print(f"Is compatible: {result.is_compatible}")

print("\nComponent scores:")
print(f"  Key: {result.key_compatibility:.1%}")
print(f"  Tempo: {result.tempo_compatibility:.1%}")
print(f"  Energy: {result.energy_compatibility:.1%}")
print(f"  Loudness: {result.loudness_compatibility:.1%}")
print(f"  Mood: {result.mood_compatibility:.1%}")
print(f"  Timbre: {result.timbre_compatibility:.1%}")

if result.violations:
    print(f"\nViolations: {', '.join(result.violations)}")

print(f"\nExplanation:\n{result.explanation}")
```

### User Preferences

```python
# Configure user preferences
kb.set_preferences(UserPreferences(
    # Tempo constraints
    min_bpm=100,
    max_bpm=140,
    prefer_consistent_tempo=True,

    # Mood preferences
    target_moods=["happy", "party"],
    avoid_moods=["sad"],

    # Energy preferences for "build-up" playlist
    prefer_increasing_energy=True,
    max_energy_jump=0.3,

    # Custom weights
    tempo_weight=0.35,  # Emphasize tempo matching
    mood_weight=0.20,   # Emphasize mood matching
))

# Preferences affect all subsequent queries
result = kb.get_compatibility(track1, track2)
```

### For Module 2 (A* Search)

```python
# Simple interface for A* cost function
cost = kb.get_penalty(track1, track2)
# Returns float in [0.0, 1.0] where 0 = perfect transition
```

### Output Example

```
Compatibility: 82.3%
A* search cost: 0.177
Is compatible: True

Component scores:
  Key: 91.2%
  Tempo: 85.0%
  Energy: 78.9%
  Loudness: 92.3%
  Mood: 85.6%
  Timbre: 73.4%

Explanation:
Key: C# minor → D major (P=91%)
Tempo: 148 → 152 BPM (Δ=4, P=85%)
Energy: 0.23 → 0.25 (Δ=0.02, P=79%)
```

### Playlist Validation

```python
playlist = [track1, track2, track3, track4, track5]

# Validate complete playlist - no need to add tracks first!
validation = kb.validate_playlist(playlist)

print(f"Overall playlist probability: {validation.overall_probability:.1%}")
print(f"Overall penalty: {validation.overall_penalty:.3f}")
print(f"Playlist is valid: {validation.is_valid}")
print(f"Total violations: {validation.total_violations}")

if validation.weakest_transition:
    idx, prob = validation.weakest_transition
    print(f"\nWeakest transition: {idx}->{idx+1} (P={prob:.1%})")

print("\nPer-transition scores:")
for i, trans in enumerate(validation.transitions):
    status = "✓" if trans.is_compatible else "✗"
    print(f"  {status} {i}->{i+1}: P={trans.probability:.1%}, cost={trans.penalty:.3f}")
    if trans.violations:
        for v in trans.violations:
            print(f"      - {v}")
```

### Advanced: Internal ProbLog Usage (For Developers)

> **Note:** The following sections show how the `MusicKnowledgeBase` class works internally.
> Typical users do NOT need to use ProbLog directly - the clean Python API handles everything.
> These examples are for developers who want to understand or extend the implementation.

#### Programmatic Program Construction (Using SimpleProgram)

```python
# This is how MusicKnowledgeBase internally builds the ProbLog database
from problog.program import SimpleProgram, PrologString
from problog.logic import Constant, Term
from problog.engine import DefaultEngine
from problog import get_evaluatable

# Load rules from file (no facts in music_theory.pl)
with open('modules/module1/music_theory.pl', 'r') as f:
    rules = PrologString(f.read())

# Create engine and prepare base database
engine = DefaultEngine()
base_db = engine.prepare(rules)

# Create facts program dynamically
facts = SimpleProgram()
facts += Term("has_key", Term("track1"), Term("c_sharp"), Term("minor"), Constant(0.78))
facts += Term("has_key", Term("track2"), Term("d"), Term("major"), Constant(0.82))
facts += Term("has_bpm", Term("track1"), Constant(148.0))
facts += Term("has_bpm", Term("track2"), Constant(152.0))

# Extend base database with facts
db = base_db.extend()
for statement in facts:
    db += statement

# Define queries
query = Term("smooth_transition", Term("track1"), Term("track2"))

# Ground and evaluate
lf = engine.ground_all(db, queries=[query])
result = get_evaluatable().create_from(lf).evaluate()

print(f"P(smooth_transition) = {result[query]:.3f}")
```

#### DefaultEngine Pattern (from main.py)

```python
# This pattern is used in MusicKnowledgeBase._init_problog()
from problog import get_evaluatable
from problog.engine import DefaultEngine
from problog.logic import Constant, Term
from problog.program import PrologString, SimpleProgram

# Rules only (no facts)
rules = PrologString("""
    key_compatible(T1, T2) :-
        has_key(T1, K, _, _),
        has_key(T2, K, _, _).
""")

engine = DefaultEngine()
base_db = engine.prepare(rules)

# Add facts via SimpleProgram
facts = SimpleProgram()
facts += Term("has_key", Term("t1"), Term("c"), Term("major"), Constant(0.9))
facts += Term("has_key", Term("t2"), Term("c"), Term("minor"), Constant(0.85))

# Extend and query
db = base_db.extend()
for stmt in facts:
    db += stmt

query = Term("key_compatible", Term("t1"), Term("t2"))
lf = engine.ground_all(db, queries=[query])
result = get_evaluatable().create_from(lf).evaluate()

print(f"Result: {result}")
```

---

## Complete End-to-End Example

```python
# main.py - Complete demonstration of Module 1 (Clean Python API)

from modules.module1.knowledge_base import MusicKnowledgeBase, UserPreferences
from modules.module1.data_loader import load_track_from_files
from modules.module1.data_models import TrackFeatures
from dataclasses import replace

def main():
    # Initialize knowledge base
    print("Initializing Music Knowledge Base...")
    kb = MusicKnowledgeBase()

    # Load sample tracks from AcousticBrainz data
    print("\nLoading tracks from AcousticBrainz data...")
    track1 = load_track_from_files(
        "modules/module1/test_files/sample_lowlevel.json",
        "modules/module1/test_files/sample_highlevel.json"
    )

    # Create a modified version for demonstration
    track2 = replace(track1, key="D", scale="major", bpm=152.0)

    print(f"Track 1: {track1.artist} - {track1.title}")
    print(f"  Key: {track1.key} {track1.scale}, BPM: {track1.bpm:.1f}")
    print(f"  Energy: {track1.energy_score:.3f}")

    print(f"\nTrack 2: (modified version)")
    print(f"  Key: {track2.key} {track2.scale}, BPM: {track2.bpm:.1f}")
    print(f"  Energy: {track2.energy_score:.3f}")

    # Query compatibility - simple Python interface!
    print("\n" + "="*60)
    print("QUERYING TRACK COMPATIBILITY")
    print("="*60)

    result = kb.get_compatibility(track1, track2)

    print(f"\nCompatibility: {result.probability:.1%}")
    print(f"A* search cost: {result.penalty:.3f}")
    print(f"Is compatible: {result.is_compatible}")

    # Show component scores
    print("\n" + "="*60)
    print("COMPONENT SCORES")
    print("="*60)

    components = [
        ("Key", result.key_compatibility),
        ("Tempo", result.tempo_compatibility),
        ("Energy", result.energy_compatibility),
        ("Loudness", result.loudness_compatibility),
        ("Mood", result.mood_compatibility),
        ("Timbre", result.timbre_compatibility),
    ]

    for name, score in components:
        status = "✓" if score > 0.5 else "✗"
        print(f"  {status} {name:12s}: {score:.1%}")

    if result.violations:
        print(f"\nViolations:")
        for violation in result.violations:
            print(f"  - {violation}")

    # Demonstrate user preferences
    print("\n" + "="*60)
    print("WITH USER PREFERENCES")
    print("="*60)

    kb.set_preferences(UserPreferences(
        prefer_consistent_tempo=True,
        target_moods=["happy", "party"],
        tempo_weight=0.35,
        mood_weight=0.20,
    ))

    result_with_prefs = kb.get_compatibility(track1, track2)
    print(f"\nWith preferences:")
    print(f"  Compatibility: {result_with_prefs.probability:.1%}")
    print(f"  A* cost: {result_with_prefs.penalty:.3f}")

    # Module 2 integration
    print("\n" + "="*60)
    print("MODULE 2 INTEGRATION (A* SEARCH)")
    print("="*60)

    # Simple interface for A* cost function
    cost = kb.get_penalty(track1, track2)
    print(f"\nFor A* search, use kb.get_penalty(track1, track2):")
    print(f"  cost = {cost:.4f}")
    print("\nThis penalty guides the search toward smooth transitions.")

    # Playlist validation
    print("\n" + "="*60)
    print("PLAYLIST VALIDATION")
    print("="*60)

    # Create a small playlist
    track3 = replace(track1, key="E", scale="minor", bpm=145.0)
    playlist = [track1, track2, track3]

    validation = kb.validate_playlist(playlist)

    print(f"\nPlaylist overall probability: {validation.overall_probability:.1%}")
    print(f"Overall penalty: {validation.overall_penalty:.3f}")
    print(f"Is valid: {validation.is_valid}")
    print(f"Total violations: {validation.total_violations}")

    if validation.weakest_transition:
        idx, prob = validation.weakest_transition
        print(f"\nWeakest transition: {idx}->{idx+1} (P={prob:.1%})")

    print("\nPer-transition scores:")
    for i, trans in enumerate(validation.transitions):
        status = "✓" if trans.is_compatible else "✗"
        print(f"  {status} {i}->{i+1}: P={trans.probability:.1%}")

    # Music theory interpretation
    print("\n" + "="*60)
    print("MUSIC THEORY INTERPRETATION")
    print("="*60)

    print(f"\nKey compatibility:")
    print(f"  {track1.key} {track1.scale} → {track2.key} {track2.scale}")
    print(f"  P(compatible) = {result.key_compatibility:.1%}")

    bpm_diff = abs(track1.bpm - track2.bpm)
    print(f"\nTempo transition:")
    print(f"  {track1.bpm:.1f} BPM → {track2.bpm:.1f} BPM (Δ = {bpm_diff:.1f})")
    print(f"  P(compatible) = {result.tempo_compatibility:.1%}")

    energy_diff = abs(track1.energy_score - track2.energy_score)
    print(f"\nEnergy progression:")
    print(f"  {track1.energy_score:.3f} → {track2.energy_score:.3f} (Δ = {energy_diff:.3f})")
    print(f"  P(compatible) = {result.energy_compatibility:.1%}")

    print("\n" + "="*60)
    print("Done! ProbLog inference is hidden behind the clean Python API.")
    print("="*60)

if __name__ == "__main__":
    main()
```

**Expected Output:**
```
Initializing Music Knowledge Base...

Loading tracks from AcousticBrainz data...
Track 1: Pink Floyd - The Lost Art of Conversation
  Key: C# minor, BPM: 148.1
  Energy: 0.234

Track 2: (modified version)
  Key: D major, BPM: 152.0
  Energy: 0.234

============================================================
QUERYING TRACK COMPATIBILITY
============================================================

Compatibility: 72.3%
A* search cost: 0.277
Is compatible: True

============================================================
COMPONENT SCORES
============================================================

  ✓ Key         : 68.1%
  ✓ Tempo       : 85.0%
  ✓ Energy      : 91.2%
  ✓ Loudness    : 87.3%
  ✓ Mood        : 78.5%
  ✓ Timbre      : 65.4%

============================================================
WITH USER PREFERENCES
============================================================

With preferences:
  Compatibility: 74.8%
  A* cost: 0.252

============================================================
MODULE 2 INTEGRATION (A* SEARCH)
============================================================

For A* search, use kb.get_penalty(track1, track2):
  cost = 0.2520

This penalty guides the search toward smooth transitions.

============================================================
PLAYLIST VALIDATION
============================================================

Playlist overall probability: 68.5%
Overall penalty: 0.315
Is valid: True
Total violations: 0

Weakest transition: 1->2 (P=64.2%)

Per-transition scores:
  ✓ 0->1: P=72.3%
  ✓ 1->2: P=64.2%

============================================================
MUSIC THEORY INTERPRETATION
============================================================

Key compatibility:
  C# minor → D major
  P(compatible) = 68.1%

Tempo transition:
  148.1 BPM → 152.0 BPM (Δ = 3.9)
  P(compatible) = 85.0%

Energy progression:
  0.234 → 0.234 (Δ = 0.000)
  P(compatible) = 91.2%

============================================================
Done! ProbLog inference is hidden behind the clean Python API.
============================================================
```

---

## Advantages of Probabilistic Logic Approach

### 1. **Natural Uncertainty Modeling**
- AcousticBrainz features include confidence scores (e.g., `key_strength: 0.7769`)
- ProbLog naturally incorporates these uncertainties into reasoning
- Output probabilities reflect input confidence levels

### 2. **Compositional Reasoning**
- Complex judgments decompose into simpler probabilistic rules
- ProbLog automatically computes joint probabilities
- Clear separation between rule logic and probability values

### 3. **Explainability**
- Can query individual rule contributions: "Why is P(smooth) low?"
- Component probabilities reveal which factors affect transitions
- Violations are interpretable logical conditions

### 4. **Graceful Degradation**
- Missing features reduce confidence but don't break inference
- System marginalizes over unknown values
- Robust to incomplete data

### 5. **Principled Combination**
- Multiple uncertain evidence sources combine via probability theory
- No ad-hoc weighting schemes needed
- Theoretically sound inference

### 6. **Extensibility**
- Adding new rules is straightforward (edit .pl file)
- Can incorporate learned probabilities from data
- Easy to experiment with different rule formulations

### Example: Uncertainty Propagation

```
Input features:
  - track1.key = "C#" with strength 0.78 (uncertain)
  - track2.key = "D" with strength 0.82 (uncertain)

ProbLog reasoning:
  1. P(track1 really in C#) ≈ 0.78
  2. P(track2 really in D) ≈ 0.82
  3. P(keys compatible | both correct) = 0.70 (adjacent keys)
  4. P(keys compatible overall) = 0.78 × 0.82 × 0.70 ≈ 0.45

Output:
  - Accounts for key detection uncertainty
  - Lower confidence → lower transition probability
  - More honest assessment than ignoring uncertainty
```

---

## Success Criteria

Module 1 is complete when:
- ProbLog knowledge base (`music_theory.pl`) correctly encodes all music theory rules (no facts, rules only)
- `MusicKnowledgeBase` provides a **clean Python API** with no ProbLog types exposed
- KB can load and validate tracks from AcousticBrainz two-file format (lowlevel + highlevel)
- All probabilistic rules are implemented and tested
- Highlevel data preference is correctly implemented when features overlap
- `get_compatibility(track1, track2)` returns `TransitionResult` with probability and component scores
- `get_penalty(track1, track2)` returns float in [0.0, 1.0] suitable for A* cost function
- `validate_playlist(tracks)` returns `PlaylistValidation` with per-transition details
- `set_preferences(UserPreferences)` affects compatibility scoring
- API is documented and ready for Module 2 integration
- Tests pass with >80% coverage
- Sample usage demonstrates probabilistic reasoning with test files
- Inference completes in reasonable time (<100ms per query)
