"""Data models for Module 1: Music Feature Knowledge Base."""

from dataclasses import dataclass, field


@dataclass
class TrackFeatures:
    """Represents extracted features from AcousticBrainz lowlevel + highlevel data."""

    # Metadata (from highlevel.metadata.tags)
    mbid: str  # MusicBrainz recording ID
    title: str | None = None
    artist: str | None = None
    album: str | None = None

    # Rhythm (from lowlevel.rhythm) - scalar values
    bpm: float = 0.0
    onset_rate: float = 0.0
    beats_count: int = 0

    # Danceability: PREFER highlevel if available, fallback to lowlevel
    # lowlevel: float (0-1), highlevel: (value, prob) tuple
    danceability: float | tuple[str, float] | None = None

    # Tonal (from lowlevel.tonal)
    key: str = "C"  # e.g., "C#", "F"
    scale: str = "major"  # "major" or "minor"
    key_strength: float = 0.0
    tuning_frequency: float = 440.0
    chords_strength: float = 0.0  # Extract from .mean

    # Energy (from lowlevel.lowlevel)
    energy_low: float = 0.0  # spectral_energyband_low.mean
    energy_mid_low: float = 0.0  # spectral_energyband_middle_low.mean
    energy_mid_high: float = 0.0  # spectral_energyband_middle_high.mean
    energy_high: float = 0.0  # spectral_energyband_high.mean

    # Loudness/dynamics (from lowlevel.lowlevel) - scalars
    average_loudness: float | None = None
    dynamic_complexity: float | None = None

    # Spectral characteristics (from lowlevel.lowlevel)
    mfcc: list[float] | None = None  # Extract from mfcc.mean array
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
    genre_rosamerica: tuple[str, float] | None = None  # ("cla"/"dan"/"hip"/etc., prob)

    @property
    def energy_score(self) -> float:
        """Compute weighted energy score from frequency bands."""
        return (
            0.1 * self.energy_low
            + 0.2 * self.energy_mid_low
            + 0.4 * self.energy_mid_high
            + 0.3 * self.energy_high
        )

    @property
    def is_happy(self) -> bool:
        """Check if track classified as happy."""
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

    @property
    def is_party(self) -> bool:
        """Check if track classified as party."""
        return self.mood_party is not None and self.mood_party[0] == "party"

    @property
    def danceability_score(self) -> float:
        """Get danceability as a float score (0-1)."""
        if self.danceability is None:
            return 0.5  # Neutral default
        if isinstance(self.danceability, tuple):
            # Highlevel: ("danceable", prob) or ("not_danceable", prob)
            value, prob = self.danceability
            return prob if value == "danceable" else 1.0 - prob
        # Lowlevel: direct float
        return self.danceability


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

    # Weights for combining scores (should sum to ~1.0)
    key_weight: float = 0.15
    tempo_weight: float = 0.20
    energy_weight: float = 0.15
    loudness_weight: float = 0.05
    mood_weight: float = 0.15
    timbre_weight: float = 0.20
    genre_weight: float = 0.10


@dataclass
class TransitionResult:
    """Result of querying track compatibility."""

    probability: float  # P(smooth_transition) in [0, 1]
    penalty: float  # 1 - probability, for A* search
    is_compatible: bool  # True if probability > threshold

    # Component probabilities
    key_compatibility: float = 0.0
    tempo_compatibility: float = 0.0
    energy_compatibility: float = 0.0
    loudness_compatibility: float = 0.0
    mood_compatibility: float = 0.0
    timbre_compatibility: float = 0.0
    genre_compatibility: float = 0.0

    violations: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class PlaylistValidation:
    """Result of validating a complete playlist."""

    overall_probability: float  # Average probability across transitions
    overall_penalty: float  # Average penalty
    is_valid: bool  # True if all transitions are compatible
    transitions: list[TransitionResult] = field(default_factory=list)
    weakest_transition: tuple[int, float] | None = None  # (index, probability)
    total_violations: int = 0
