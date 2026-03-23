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
        self.kb = knowledge_base
        self.search_space = search_space or SearchSpace(knowledge_base)
        self.beam_width = beam_width
        self.max_expansions = max_expansions

    def _heuristic(self, current_mbid: str, dest_mbid: str) -> float:
        """Estimate cost from current track to destination."""
        cost = self.search_space.get_transition_cost(current_mbid, dest_mbid)
        if cost is None:
            return 0.9
        return cost

    def _score_state(self, state: SearchState, dest_mbid: str) -> float:
        """Compute f(n) = g(n) + h(n) for A*-style beam search."""
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
        """Find a path from source to destination track."""
        if source_features:
            self.search_space.add_features(source_mbid, source_features)
        if dest_features:
            self.search_space.add_features(dest_mbid, dest_features)

        if not self.search_space.has_features(source_mbid):
            return None

        initial_state = SearchState(path=[source_mbid], cost=0.0)
        beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(initial_state, dest_mbid),
                state=initial_state,
            )
        ]

        solutions: list[SearchState] = []
        expansions = 0

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

                # Try direct connection to destination when close to target
                if state.length >= target_length - 1:
                    if dest_mbid not in state.path:
                        cost = self.search_space.get_transition_cost(
                            state.current_mbid, dest_mbid
                        )
                        if cost is not None:
                            final_state = state.extend(dest_mbid, cost)
                            solutions.append(final_state)

            beam = heapq.nsmallest(self.beam_width, next_beam)

            if len(solutions) >= self.beam_width:
                break

        if not solutions:
            return None

        best = min(solutions, key=lambda s: s.cost)
        return self._build_path(best)

    def _build_path(self, state: SearchState) -> PlaylistPath:
        """Convert a search state to a PlaylistPath with transition details."""
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

    def find_path_bidirectional(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        source_features: TrackFeatures | None = None,
        dest_features: TrackFeatures | None = None,
    ) -> PlaylistPath | None:
        """Find a path using bidirectional beam search.

        Expands from both source and destination simultaneously. When the
        two frontiers overlap at a meeting node, stitches the best path
        and re-scores it in the forward direction.

        Falls back to unidirectional find_path() if bidirectional fails.
        """
        if source_features:
            self.search_space.add_features(source_mbid, source_features)
        if dest_features:
            self.search_space.add_features(dest_mbid, dest_features)

        # Need features for both endpoints to do bidirectional
        if not self.search_space.has_features(source_mbid):
            return None
        if not self.search_space.has_features(dest_mbid):
            return self.find_path(source_mbid, dest_mbid, target_length)

        # Split target: each side aims for roughly half the path
        # fwd_target + bwd_target - 1 = target_length
        fwd_target = (target_length + 2) // 2
        bwd_target = target_length + 1 - fwd_target

        # Initialize beams
        fwd_initial = SearchState(path=[source_mbid], cost=0.0)
        bwd_initial = SearchState(path=[dest_mbid], cost=0.0)

        fwd_beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(fwd_initial, dest_mbid),
                state=fwd_initial,
            )
        ]
        bwd_beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(bwd_initial, source_mbid),
                state=bwd_initial,
            )
        ]

        # Track the lowest-cost state reaching each MBID tip
        fwd_reached: dict[str, SearchState] = {source_mbid: fwd_initial}
        bwd_reached: dict[str, SearchState] = {dest_mbid: bwd_initial}

        expansions = 0

        while expansions < self.max_expansions and (fwd_beam or bwd_beam):
            # Expand forward beam one round
            if fwd_beam:
                fwd_beam = self._expand_beam_round(
                    fwd_beam, dest_mbid, fwd_target, fwd_reached
                )
                expansions += 1

            # Check for meeting after forward expansion
            path = self._check_meeting(fwd_reached, bwd_reached, target_length)
            if path is not None:
                return path

            # Expand backward beam one round
            if bwd_beam:
                bwd_beam = self._expand_beam_round(
                    bwd_beam, source_mbid, bwd_target, bwd_reached
                )
                expansions += 1

            # Check for meeting after backward expansion
            path = self._check_meeting(fwd_reached, bwd_reached, target_length)
            if path is not None:
                return path

        # Fallback to unidirectional
        return self.find_path(source_mbid, dest_mbid, target_length)

    def _expand_beam_round(
        self,
        beam: list[PrioritizedState],
        target_mbid: str,
        max_path_length: int,
        reached: dict[str, SearchState],
    ) -> list[PrioritizedState]:
        """Expand all states in a beam by one step."""
        next_beam: list[PrioritizedState] = []

        for pstate in beam:
            state = pstate.state

            if state.length >= max_path_length:
                continue

            neighbors = self.search_space.get_scoreable_neighbors(state.current_mbid)

            for neighbor_mbid in neighbors:
                if neighbor_mbid in state.path:
                    continue

                cost = self.search_space.get_transition_cost(
                    state.current_mbid, neighbor_mbid
                )
                if cost is None:
                    continue

                new_state = state.extend(neighbor_mbid, cost)
                priority = self._score_state(new_state, target_mbid)
                heapq.heappush(
                    next_beam,
                    PrioritizedState(priority=priority, state=new_state),
                )

                # Keep lowest-cost state for each MBID tip
                tip = new_state.current_mbid
                if tip not in reached or new_state.cost < reached[tip].cost:
                    reached[tip] = new_state

        return heapq.nsmallest(self.beam_width, next_beam)

    def _check_meeting(
        self,
        fwd_reached: dict[str, SearchState],
        bwd_reached: dict[str, SearchState],
        target_length: int,
    ) -> PlaylistPath | None:
        """Check if frontiers overlap and return the best stitched path."""
        meeting_nodes = fwd_reached.keys() & bwd_reached.keys()
        if not meeting_nodes:
            return None

        candidates: list[SearchState] = []

        for meeting_mbid in meeting_nodes:
            fwd_state = fwd_reached[meeting_mbid]
            bwd_state = bwd_reached[meeting_mbid]

            # Stitch: forward + reversed backward (minus duplicate meeting)
            bwd_reversed = list(reversed(bwd_state.path))
            full_mbids = fwd_state.path + bwd_reversed[1:]

            # Reject if cycles exist
            if len(full_mbids) != len(set(full_mbids)):
                continue

            # Need at least 3 nodes for a meaningful playlist
            if len(full_mbids) < 3:
                continue

            # Re-score the full path in forward direction
            stitched = self._rescore_path(full_mbids)
            if stitched is not None:
                candidates.append(stitched)

        if not candidates:
            return None

        # Prefer paths closer to target_length, then lowest cost
        best = min(
            candidates,
            key=lambda s: (abs(len(s.path) - target_length), s.cost),
        )
        return self._build_path(best)

    def _rescore_path(self, mbids: list[str]) -> SearchState | None:
        """Re-compute total cost for a path in forward direction."""
        total_cost = 0.0
        for i in range(len(mbids) - 1):
            cost = self.search_space.get_transition_cost(mbids[i], mbids[i + 1])
            if cost is None:
                return None
            total_cost += cost
        return SearchState(path=mbids, cost=total_cost)

    def find_paths_multi(
        self,
        source_mbid: str,
        dest_mbid: str,
        target_length: int = 7,
        num_paths: int = 3,
    ) -> list[PlaylistPath]:
        """Find multiple diverse paths from source to destination."""
        if not self.search_space.has_features(source_mbid):
            return []

        initial_state = SearchState(path=[source_mbid], cost=0.0)
        beam: list[PrioritizedState] = [
            PrioritizedState(
                priority=self._score_state(initial_state, dest_mbid),
                state=initial_state,
            )
        ]

        solutions: list[SearchState] = []
        expansions = 0
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

        paths = [self._build_path(s) for s in solutions]
        paths.sort(key=lambda p: p.total_cost)

        # Return diverse paths (>50% different intermediate tracks)
        diverse_paths: list[PlaylistPath] = []
        for path in paths:
            is_diverse = True
            for existing in diverse_paths:
                path_set = set(path.mbids[1:-1])
                existing_set = set(existing.mbids[1:-1])
                if path_set and existing_set:
                    overlap = len(path_set & existing_set) / len(
                        path_set | existing_set
                    )
                    if overlap > 0.5:
                        is_diverse = False
                        break

            if is_diverse:
                diverse_paths.append(path)
                if len(diverse_paths) >= num_paths:
                    break

        return diverse_paths
