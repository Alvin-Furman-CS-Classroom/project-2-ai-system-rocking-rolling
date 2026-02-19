"""Tests for beam search algorithm."""

import unittest

from module1 import MusicKnowledgeBase, TrackFeatures

from module2.beam_search import BeamSearch, SearchSpaceProtocol
from module2.data_models import PlaylistPath, SearchState


class MockSearchSpace(SearchSpaceProtocol):
    """Mock search space for testing beam search logic.

    Implements SearchSpaceProtocol for type-safe testing.
    """

    def __init__(
        self, graph: dict[str, list[str]], costs: dict[tuple[str, str], float]
    ):
        """Initialize with a predefined graph and costs.

        Args:
            graph: Adjacency list {mbid: [neighbor_mbids]}
            costs: Cost matrix {(from, to): cost}
        """
        self.graph = graph
        self.costs = costs
        self._features: dict[str, TrackFeatures] = {}

        # Create dummy features for all nodes
        for mbid in set(graph.keys()) | {
            n for neighbors in graph.values() for n in neighbors
        }:
            self._features[mbid] = TrackFeatures(
                mbid=mbid,
                title=f"Track {mbid}",
                bpm=120.0,
                key="C",
                scale="major",
            )

    def get_scoreable_neighbors(self, mbid: str) -> list[str]:
        return self.graph.get(mbid, [])

    def get_transition_cost(self, from_mbid: str, to_mbid: str) -> float | None:
        return self.costs.get((from_mbid, to_mbid))

    def get_transition_result(self, from_mbid: str, to_mbid: str):
        cost = self.costs.get((from_mbid, to_mbid))
        if cost is None:
            return None
        from module1 import TransitionResult

        return TransitionResult(
            probability=1.0 - cost,
            penalty=cost,
            is_compatible=cost < 0.7,
        )

    def get_features(self, mbid: str) -> TrackFeatures | None:
        return self._features.get(mbid)

    def has_features(self, mbid: str) -> bool:
        return mbid in self._features

    def add_features(self, mbid: str, features: TrackFeatures) -> None:
        self._features[mbid] = features


class TestSearchState(unittest.TestCase):
    """Tests for SearchState dataclass."""

    def test_current_mbid(self):
        """Test current_mbid property."""
        state = SearchState(path=["a", "b", "c"], cost=0.5)
        self.assertEqual(state.current_mbid, "c")

    def test_length(self):
        """Test length property."""
        state = SearchState(path=["a", "b", "c"], cost=0.5)
        self.assertEqual(state.length, 3)

    def test_extend(self):
        """Test extend method creates new state."""
        state = SearchState(path=["a", "b"], cost=0.3)
        new_state = state.extend("c", 0.2)

        # Original unchanged
        self.assertEqual(state.path, ["a", "b"])
        self.assertAlmostEqual(state.cost, 0.3)

        # New state updated
        self.assertEqual(new_state.path, ["a", "b", "c"])
        self.assertAlmostEqual(new_state.cost, 0.5)


class TestBeamSearch(unittest.TestCase):
    """Tests for BeamSearch algorithm."""

    def setUp(self):
        """Set up test fixtures."""
        self.kb = MusicKnowledgeBase()

    def tearDown(self):
        """Clean up."""
        self.kb.clear()

    def test_find_path_simple_linear(self):
        """Test finding path in simple linear graph: A -> B -> C -> D."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["D"],
        }
        costs = {
            ("A", "B"): 0.1,
            ("B", "C"): 0.1,
            ("C", "D"): 0.1,
            ("A", "D"): 0.9,  # Heuristic cost
            ("B", "D"): 0.6,
        }
        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
        )

        path = search.find_path("A", "D", target_length=4)

        assert path is not None
        self.assertEqual(path.mbids, ["A", "B", "C", "D"])
        self.assertAlmostEqual(path.total_cost, 0.3)

    def test_find_path_chooses_lowest_cost(self):
        """Test that search chooses lowest cost path."""
        # Two paths: A->B->D (cost 0.8) and A->C->D (cost 0.4)
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
        }
        costs = {
            ("A", "B"): 0.4,
            ("A", "C"): 0.2,
            ("B", "D"): 0.4,
            ("C", "D"): 0.2,
            ("A", "D"): 0.5,  # Heuristic
        }
        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
        )

        path = search.find_path("A", "D", target_length=3)

        assert path is not None
        self.assertEqual(path.mbids, ["A", "C", "D"])
        self.assertAlmostEqual(path.total_cost, 0.4)

    def test_find_path_no_cycles(self):
        """Test that paths don't contain cycles."""
        # Graph with potential for cycles
        graph = {
            "A": ["B", "C"],
            "B": ["A", "C", "D"],
            "C": ["A", "B", "D"],
        }
        costs = {
            ("A", "B"): 0.1,
            ("A", "C"): 0.1,
            ("B", "A"): 0.1,
            ("B", "C"): 0.1,
            ("B", "D"): 0.1,
            ("C", "A"): 0.1,
            ("C", "B"): 0.1,
            ("C", "D"): 0.1,
            ("A", "D"): 0.3,
        }
        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
        )

        path = search.find_path("A", "D", target_length=4)

        assert path is not None
        # Check no duplicates
        self.assertEqual(len(path.mbids), len(set(path.mbids)))

    def test_find_path_respects_target_length(self):
        """Test that path approximately matches target length."""
        graph = {
            "A": ["B", "E"],
            "B": ["C", "E"],
            "C": ["D", "E"],
            "D": ["E"],
        }
        costs = {(f, t): 0.1 for f in graph for t in graph.get(f, [])}
        # Add heuristic costs to E
        for node in ["A", "B", "C", "D"]:
            costs[(node, "E")] = 0.1
        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
        )

        path = search.find_path("A", "E", target_length=4)

        assert path is not None
        # Should be close to target length (within reason)
        self.assertGreaterEqual(path.length, 3)
        self.assertLessEqual(path.length, 5)

    def test_find_path_returns_none_for_impossible(self):
        """Test that None is returned when no path exists."""
        graph = {
            "A": ["B"],
            "B": [],  # Dead end
            "C": ["D"],  # Disconnected
        }
        costs = {
            ("A", "B"): 0.1,
            ("C", "D"): 0.1,
            ("A", "D"): 0.9,
            ("B", "D"): 0.9,
        }
        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
            max_expansions=50,  # Limit search
        )

        path = search.find_path("A", "D", target_length=5)

        self.assertIsNone(path)

    def test_find_path_no_source_features(self):
        """Test that None is returned when source has no features."""
        graph = {"A": ["B"]}
        costs = {("A", "B"): 0.1}
        mock_space = MockSearchSpace(graph, costs)

        # Remove source features
        del mock_space._features["A"]

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
        )

        path = search.find_path("A", "B", target_length=2)

        self.assertIsNone(path)

    def test_beam_width_limits_states(self):
        """Test that beam width properly limits explored states."""
        # Wide graph to test pruning
        neighbors = [f"N{i}" for i in range(20)]
        graph = {"A": neighbors}
        for n in neighbors:
            graph[n] = ["D"]

        costs = {}
        for i, n in enumerate(neighbors):
            costs[("A", n)] = 0.5 + i * 0.01  # Varying costs
            costs[(n, "D")] = 0.1
            costs[("A", "D")] = 0.9  # Heuristic
            costs[(n, "D")] = 0.1

        mock_space = MockSearchSpace(graph, costs)

        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=3,  # Only keep top 3
        )

        path = search.find_path("A", "D", target_length=3)

        assert path is not None
        # Should find one of the low-cost paths
        self.assertIn(path.mbids[1], neighbors[:5])


class TestPlaylistPath(unittest.TestCase):
    """Tests for PlaylistPath dataclass."""

    def test_length_property(self):
        """Test length property."""
        path = PlaylistPath(mbids=["a", "b", "c"], total_cost=0.4)
        self.assertEqual(path.length, 3)

    def test_average_compatibility_empty(self):
        """Test average compatibility with no transitions."""
        path = PlaylistPath(mbids=["a"], total_cost=0.0)
        self.assertAlmostEqual(path.average_compatibility, 0.0)

    def test_average_compatibility_calculated(self):
        """Test average compatibility calculation."""
        from module1 import TransitionResult

        transitions = [
            TransitionResult(probability=0.8, penalty=0.2, is_compatible=True),
            TransitionResult(probability=0.6, penalty=0.4, is_compatible=True),
        ]
        path = PlaylistPath(
            mbids=["a", "b", "c"],
            total_cost=0.6,  # 0.2 + 0.4
            transitions=transitions,
        )

        # Average penalty = 0.6 / 2 = 0.3
        # Average compatibility = 1 - 0.3 = 0.7
        self.assertAlmostEqual(path.average_compatibility, 0.7)


if __name__ == "__main__":
    unittest.main()
