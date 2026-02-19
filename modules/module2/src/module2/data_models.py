"""Data models for Module 2: Beam Search Path Finding."""

from dataclasses import dataclass, field

from module1 import TransitionResult


@dataclass
class SimilarRecording:
    """A recording similar to a reference track from ListenBrainz."""

    mbid: str
    similarity_score: float  # Higher = more similar


@dataclass
class SearchState:
    """State in the beam search representing a partial path."""

    path: list[str]  # MBIDs visited in order
    cost: float  # Accumulated transition penalty

    @property
    def current_mbid(self) -> str:
        """Get the last MBID in the path (current position)."""
        return self.path[-1]

    @property
    def length(self) -> int:
        """Get the current path length."""
        return len(self.path)

    def extend(self, mbid: str, transition_cost: float) -> "SearchState":
        """Create a new state by extending this path with another MBID."""
        return SearchState(
            path=self.path + [mbid],
            cost=self.cost + transition_cost,
        )


@dataclass
class PlaylistPath:
    """Result of beam search: a complete path from source to destination."""

    mbids: list[str]  # Ordered list of MBIDs in the playlist
    total_cost: float  # Sum of transition penalties
    transitions: list[TransitionResult] = field(default_factory=list)

    @property
    def length(self) -> int:
        """Get the path length (number of tracks)."""
        return len(self.mbids)

    @property
    def average_compatibility(self) -> float:
        """Get average transition probability (1 - average_penalty)."""
        if not self.transitions:
            return 0.0
        avg_penalty = self.total_cost / len(self.transitions)
        return 1.0 - avg_penalty
