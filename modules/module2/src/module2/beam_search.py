"""Beam search algorithm for finding optimal playlist paths.

Implements beam search with dynamic neighborhood expansion to find
paths from a source track to a destination track.
"""

import heapq
from dataclasses import dataclass, field

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from .data_models import PlaylistPath, SearchState
from .search_space import SearchSpace, SearchSpaceProtocol


@dataclass(order=True)
class PrioritizedState:
    """Search state with priority for heap operations."""

    priority: float
    state: SearchState = field(compare=False)


class BeamSearch:
    """Beam search algorithm for playlist path finding.

    Uses beam search with A*-style heuristics to find paths from a source
    track to a destination track. The heuristic estimates the cost of
    reaching the destination using Module 1's transition penalty.
    """

    def __init__(
        self,
        knowledge_base: MusicKnowledgeBase,
        search_space: SearchSpaceProtocol | None = None,
        beam_width: int = 10,
        max_expansions: int = 1000,
    ):
        """Initialize the beam search.

        Args:
            knowledge_base: Module 1 KB for computing transition costs.
            search_space: Search space manager implementing SearchSpaceProtocol.
                         Creates default SearchSpace if not provided.
            beam_width: Number of best states to keep at each step.
            max_expansions: Maximum number of state expansions before giving up.
        """
        self.kb = knowledge_base
        self.search_space = search_space or SearchSpace(knowledge_base)
        self.beam_width = beam_width
        self.max_expansions = max_expansions

    def _heuristic(self, current_mbid: str, dest_mbid: str) -> float:
        """Estimate cost from current track to destination.

        Uses Module 1's transition penalty as the heuristic.
        Returns a high cost if features aren't available.

        Args:
            current_mbid: Current track MBID.
            dest_mbid: Destination track MBID.

        Returns:
            Estimated cost to destination.
        """
        cost = self.search_space.get_transition_cost(current_mbid, dest_mbid)
        if cost is None:
            # High penalty for tracks without features
            return 0.9
        return cost

    def _score_state(self, state: SearchState, dest_mbid: str) -> float:
        """Compute f(n) = g(n) + h(n) for A*-style beam search.

        Args:
            state: Current search state.
            dest_mbid: Destination track MBID.

        Returns:
            Combined cost + heuristic score.
        """
        g = state.cost
        h = self._heuristic(state.current_mbid, dest_mbid)
        return g + h

    def find_path(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        source_features: TrackFeatures | None = None,
        dest_features: TrackFeatures | None = None,
    ) -> PlaylistPath | None:
        """Find a path from source to destination track.

        Args:
            source_mbid: Starting track MBID.
            dest_mbid: Target track MBID.
            target_length: Desired playlist length (number of tracks).
            source_features: Optional pre-loaded source features.
            dest_features: Optional pre-loaded destination features.

        Returns:
            PlaylistPath if a path is found, None otherwise.
        """
        # Pre-load source and destination features if provided
        if source_features:
            self.search_space.add_features(source_mbid, source_features)
        if dest_features:
            self.search_space.add_features(dest_mbid, dest_features)

        # Ensure source has features
        if not self.search_space.has_features(source_mbid):
            return None

        # Initialize beam with starting state
        initial_state = SearchState(path=[source_mbid], cost=0.0)
        beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(initial_state, dest_mbid),
                state=initial_state,
            )
        ]

        solutions: list[SearchState] = []
        expansions = 0

        # Search until we find solutions or exhaust the search
        while beam and expansions < self.max_expansions:
            next_beam: list[PrioritizedState] = []

            for pstate in beam:
                state = pstate.state
                expansions += 1

                # Check if we've reached target length
                if state.length >= target_length:
                    # Force connection to destination if not already there
                    if state.current_mbid == dest_mbid:
                        solutions.append(state)
                    else:
                        # Try to end at destination
                        final_cost = self.search_space.get_transition_cost(
                            state.current_mbid, dest_mbid
                        )
                        if final_cost is not None:
                            final_state = state.extend(dest_mbid, final_cost)
                            solutions.append(final_state)
                    continue

                # Expand: get neighbors of current track
                neighbors = self.search_space.get_scoreable_neighbors(
                    state.current_mbid
                )

                for neighbor_mbid in neighbors:
                    # Skip if already in path (no cycles)
                    if neighbor_mbid in state.path:
                        continue

                    # Compute transition cost
                    cost = self.search_space.get_transition_cost(
                        state.current_mbid, neighbor_mbid
                    )
                    if cost is None:
                        continue

                    # Create successor state
                    new_state = state.extend(neighbor_mbid, cost)
                    priority = self._score_state(new_state, dest_mbid)

                    heapq.heappush(
                        next_beam,
                        PrioritizedState(priority=priority, state=new_state),
                    )

                # Also consider jumping directly to destination if close to target
                if state.length >= target_length - 1:
                    if dest_mbid not in state.path:
                        cost = self.search_space.get_transition_cost(
                            state.current_mbid, dest_mbid
                        )
                        if cost is not None:
                            final_state = state.extend(dest_mbid, cost)
                            solutions.append(final_state)

            # Prune to beam width
            beam = heapq.nsmallest(self.beam_width, next_beam)

            # Stop if we have enough solutions
            if len(solutions) >= self.beam_width:
                break

        if not solutions:
            return None

        # Return best solution (lowest cost)
        best = min(solutions, key=lambda s: s.cost)
        return self._build_path(best)

    def _build_path(self, state: SearchState) -> PlaylistPath:
        """Convert a search state to a PlaylistPath with transition details.

        Args:
            state: Final search state.

        Returns:
            PlaylistPath with full transition information.
        """
        transitions: list[TransitionResult] = []

        for i in range(len(state.path) - 1):
            from_mbid = state.path[i]
            to_mbid = state.path[i + 1]
            result = self.search_space.get_transition_result(from_mbid, to_mbid)
            if result:
                transitions.append(result)

        return PlaylistPath(
            mbids=state.path,
            total_cost=state.cost,
            transitions=transitions,
        )

    def find_paths_multi(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        num_paths: int = 3,
    ) -> list[PlaylistPath]:
        """Find multiple diverse paths from source to destination.

        Args:
            source_mbid: Starting track MBID.
            dest_mbid: Target track MBID.
            target_length: Desired playlist length.
            num_paths: Number of paths to return.

        Returns:
            List of PlaylistPaths, sorted by cost.
        """
        # Ensure source has features
        if not self.search_space.has_features(source_mbid):
            return []

        # Initialize beam with starting state
        initial_state = SearchState(path=[source_mbid], cost=0.0)
        beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(initial_state, dest_mbid),
                state=initial_state,
            )
        ]

        solutions: list[SearchState] = []
        expansions = 0

        # Use wider beam to get more diverse solutions
        effective_beam_width = self.beam_width * 2

        while beam and expansions < self.max_expansions:
            next_beam: list[PrioritizedState] = []

            for pstate in beam:
                state = pstate.state
                expansions += 1

                if state.length >= target_length:
                    if state.current_mbid == dest_mbid:
                        solutions.append(state)
                    else:
                        final_cost = self.search_space.get_transition_cost(
                            state.current_mbid, dest_mbid
                        )
                        if final_cost is not None:
                            final_state = state.extend(dest_mbid, final_cost)
                            solutions.append(final_state)
                    continue

                neighbors = self.search_space.get_scoreable_neighbors(
                    state.current_mbid
                )

                for neighbor_mbid in neighbors:
                    if neighbor_mbid in state.path:
                        continue

                    cost = self.search_space.get_transition_cost(
                        state.current_mbid, neighbor_mbid
                    )
                    if cost is None:
                        continue

                    new_state = state.extend(neighbor_mbid, cost)
                    priority = self._score_state(new_state, dest_mbid)

                    heapq.heappush(
                        next_beam,
                        PrioritizedState(priority=priority, state=new_state),
                    )

                if state.length >= target_length - 1:
                    if dest_mbid not in state.path:
                        cost = self.search_space.get_transition_cost(
                            state.current_mbid, dest_mbid
                        )
                        if cost is not None:
                            final_state = state.extend(dest_mbid, cost)
                            solutions.append(final_state)

            beam = heapq.nsmallest(effective_beam_width, next_beam)

            if len(solutions) >= num_paths * 2:
                break

        # Build and return sorted paths
        paths = [self._build_path(s) for s in solutions]
        paths.sort(key=lambda p: p.total_cost)

        # Return diverse paths (avoid too-similar paths)
        diverse_paths: list[PlaylistPath] = []
        for path in paths:
            # Check path diversity (different intermediate tracks)
            is_diverse = True
            for existing in diverse_paths:
                # Compute overlap ratio
                path_set = set(path.mbids[1:-1])  # Exclude source/dest
                existing_set = set(existing.mbids[1:-1])
                if path_set and existing_set:
                    overlap = len(path_set & existing_set) / len(
                        path_set | existing_set
                    )
                    if overlap > 0.5:  # More than 50% overlap
                        is_diverse = False
                        break

            if is_diverse:
                diverse_paths.append(path)
                if len(diverse_paths) >= num_paths:
                    break

        return diverse_paths
