"""Data models for Module 3: Playlist Assembly."""

from dataclasses import dataclass, field
from uuid import uuid4

from module1 import TrackFeatures, TransitionResult, UserPreferences
from module2 import PlaylistPath


# --- Constraint models ---


@dataclass
class ConstraintResult:
    """Result of evaluating a single constraint on a playlist."""

    name: str
    satisfied: bool
    score: float  # 0.0 = fully violated, 1.0 = fully satisfied
    violations: list[str] = field(default_factory=list)
    violating_positions: list[int] = field(default_factory=list)


# --- Explanation models ---


@dataclass
class TransitionExplanation:
    """Human-readable explanation of a single transition."""

    from_title: str
    to_title: str
    overall_score: float
    top_contributors: list[tuple[str, float, str]]  # (dim, score, description)
    bottom_contributors: list[tuple[str, float, str]]
    raw_explanation: str  # From Module 1


@dataclass
class TrackExplanation:
    """Explanation for why a track appears at a specific position."""

    position: int
    mbid: str
    title: str | None
    artist: str | None
    role: str  # "source", "destination", "waypoint"
    incoming_transition: TransitionExplanation | None = None
    outgoing_transition: TransitionExplanation | None = None


@dataclass
class PlaylistExplanation:
    """Complete explanation for a generated playlist."""

    summary: str
    track_explanations: list[TrackExplanation] = field(default_factory=list)
    constraint_notes: list[str] = field(default_factory=list)
    quality_metrics: dict[str, float] = field(default_factory=dict)


# --- User modeling ---


@dataclass
class PlaylistFeedback:
    """User feedback on a generated playlist."""

    playlist_id: str
    overall_rating: float  # 1-5
    transition_ratings: dict[int, float] = field(default_factory=dict)
    liked_tracks: list[str] = field(default_factory=list)
    disliked_tracks: list[str] = field(default_factory=list)


@dataclass
class UserProfile:
    """Persisted user preferences learned from feedback."""

    dimension_weights: dict[str, float] = field(default_factory=lambda: {
        "key": 0.15, "tempo": 0.20, "energy": 0.15, "loudness": 0.05,
        "mood": 0.15, "timbre": 0.15, "genre": 0.05, "tag": 0.10,
        "popularity": 0.0, "artist": 0.10, "era": 0.05, "mb_genre": 0.0,
    })
    preferred_genres: dict[str, float] = field(default_factory=dict)
    preferred_energy_arc: str = "flat"
    feedback_history: list[PlaylistFeedback] = field(default_factory=list)

    def to_user_preferences(self) -> UserPreferences:
        """Convert learned profile to Module 1's UserPreferences."""
        return UserPreferences(
            key_weight=self.dimension_weights.get("key", 0.15),
            tempo_weight=self.dimension_weights.get("tempo", 0.20),
            energy_weight=self.dimension_weights.get("energy", 0.15),
            loudness_weight=self.dimension_weights.get("loudness", 0.05),
            mood_weight=self.dimension_weights.get("mood", 0.15),
            timbre_weight=self.dimension_weights.get("timbre", 0.15),
            genre_weight=self.dimension_weights.get("genre", 0.05),
            tag_weight=self.dimension_weights.get("tag", 0.10),
            popularity_weight=self.dimension_weights.get("popularity", 0.0),
            artist_weight=self.dimension_weights.get("artist", 0.10),
            era_weight=self.dimension_weights.get("era", 0.05),
            mb_genre_weight=self.dimension_weights.get("mb_genre", 0.0),
        )


# --- Assembled playlist output ---


@dataclass
class AssembledPlaylist:
    """Final assembled playlist with all metadata."""

    path: PlaylistPath
    tracks: list[TrackFeatures]
    explanation: PlaylistExplanation
    constraints_applied: list[ConstraintResult] = field(default_factory=list)
    playlist_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = ""

    @property
    def length(self) -> int:
        return len(self.tracks)

    def to_static_output(self) -> dict:
        """Serialize for static playlist output (JSON)."""
        tracks_out = []
        for i, t in enumerate(self.tracks):
            track_dict = {
                "position": i + 1,
                "mbid": t.mbid,
                "title": t.title or "Unknown",
                "artist": t.artist or "Unknown",
            }
            if t.bpm:
                track_dict["bpm"] = round(t.bpm)
            if t.key:
                track_dict["key"] = f"{t.key} {t.scale}"
            if t.genre_rosamerica:
                track_dict["genre"] = t.genre_rosamerica[0]
            tracks_out.append(track_dict)

        transitions_out = []
        for i, tr in enumerate(self.path.transitions):
            trans_dict = {
                "from_position": i + 1,
                "to_position": i + 2,
                "compatibility": round(tr.probability, 3),
            }
            # Add top contributors from explanation if available
            if i + 1 < len(self.explanation.track_explanations):
                te = self.explanation.track_explanations[i + 1]
                if te.incoming_transition:
                    trans_dict["top_dimensions"] = [
                        {"name": n, "score": round(s, 3), "reason": d}
                        for n, s, d in te.incoming_transition.top_contributors
                    ]
            transitions_out.append(trans_dict)

        return {
            "playlist_id": self.playlist_id,
            "tracks": tracks_out,
            "transitions": transitions_out,
            "summary": self.explanation.summary,
            "quality": self.explanation.quality_metrics,
            "constraints": [
                {"name": c.name, "satisfied": c.satisfied, "score": round(c.score, 3)}
                for c in self.constraints_applied
            ],
        }
