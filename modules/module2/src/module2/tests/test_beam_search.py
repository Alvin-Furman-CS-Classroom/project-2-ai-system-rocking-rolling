"""Tests for beam search algorithm."""

import unittest

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from module2.beam_search import BeamSearch
from module2.search_space import SearchSpaceProtocol
from module2.data_models import PlaylistPath, SearchState


class MockSearchSpace(SearchSpaceProtocol):
    """Mock search space for testing beam search logic."""

    def __init__(
        self, graph: dict[str, list[str]], costs: dict[tuple[str, str], float]
    ):
        self.graph = graph
        self.costs = costs
        self._features: dict[str, TrackFeatures] = {}

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
        state = SearchState(path=["a", "b", "c"], cost=0.5)
        self.assertEqual(state.current_mbid, "c")

    def test_length(self):
        state = SearchState(path=["a", "b", "c"], cost=0.5)
        self.assertEqual(state.length, 3)

    def test_extend(self):
        state = SearchState(path=["a", "b"], cost=0.3)
        new_state = state.extend("c", 0.2)

        self.assertEqual(state.path, ["a", "b"])
        self.assertAlmostEqual(state.cost, 0.3)

        self.assertEqual(new_state.path, ["a", "b", "c"])
        self.assertAlmostEqual(new_state.cost, 0.5)


class TestBeamSearch(unittest.TestCase):
    """Tests for BeamSearch algorithm."""

    def setUp(self):
        self.kb = MusicKnowledgeBase()

    def tearDown(self):
        self.kb.clear()

    def test_find_path_simple_linear(self):
        """A -> B -> C -> D linear path."""
        graph = {"A": ["B"], "B": ["C"], "C": ["D"]}
        costs = {
            ("A", "B"): 0.1,
            ("B", "C"): 0.1,
            ("C", "D"): 0.1,
            ("A", "D"): 0.9,
            ("B", "D"): 0.6,
        }
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path("A", "D", target_length=4)

        assert path is not None
        self.assertEqual(path.mbids, ["A", "B", "C", "D"])
        self.assertAlmostEqual(path.total_cost, 0.3)

    def test_find_path_chooses_lowest_cost(self):
        """Two paths: A->B->D (cost 0.8) and A->C->D (cost 0.4)."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
        costs = {
            ("A", "B"): 0.4,
            ("A", "C"): 0.2,
            ("B", "D"): 0.4,
            ("C", "D"): 0.2,
            ("A", "D"): 0.5,
        }
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path("A", "D", target_length=3)

        assert path is not None
        self.assertEqual(path.mbids, ["A", "C", "D"])
        self.assertAlmostEqual(path.total_cost, 0.4)

    def test_find_path_no_cycles(self):
        """Paths don't revisit nodes."""
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
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path("A", "D", target_length=4)

        assert path is not None
        self.assertEqual(len(path.mbids), len(set(path.mbids)))

    def test_find_path_respects_target_length(self):
        graph = {
            "A": ["B", "E"],
            "B": ["C", "E"],
            "C": ["D", "E"],
            "D": ["E"],
        }
        costs = {(f, t): 0.1 for f in graph for t in graph.get(f, [])}
        for node in ["A", "B", "C", "D"]:
            costs[(node, "E")] = 0.1
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path("A", "E", target_length=4)

        assert path is not None
        self.assertGreaterEqual(path.length, 3)
        self.assertLessEqual(path.length, 5)

    def test_find_path_returns_none_for_impossible(self):
        graph = {"A": ["B"], "B": [], "C": ["D"]}
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
            max_expansions=50,
        )

        path = search.find_path("A", "D", target_length=5)
        self.assertIsNone(path)

    def test_find_path_no_source_features(self):
        graph = {"A": ["B"]}
        costs = {("A", "B"): 0.1}
        mock_space = MockSearchSpace(graph, costs)
        del mock_space._features["A"]

        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path("A", "B", target_length=2)
        self.assertIsNone(path)

    def test_beam_width_limits_states(self):
        neighbors = [f"N{i}" for i in range(20)]
        graph = {"A": neighbors}
        for n in neighbors:
            graph[n] = ["D"]

        costs = {}
        for i, n in enumerate(neighbors):
            costs[("A", n)] = 0.5 + i * 0.01
            costs[(n, "D")] = 0.1
            costs[("A", "D")] = 0.9

        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=3,
        )

        path = search.find_path("A", "D", target_length=3)

        assert path is not None
        self.assertIn(path.mbids[1], neighbors[:5])


class TestPlaylistPath(unittest.TestCase):
    def test_length_property(self):
        path = PlaylistPath(mbids=["a", "b", "c"], total_cost=0.4)
        self.assertEqual(path.length, 3)

    def test_average_compatibility_empty(self):
        path = PlaylistPath(mbids=["a"], total_cost=0.0)
        self.assertAlmostEqual(path.average_compatibility, 0.0)

    def test_average_compatibility_calculated(self):
        transitions = [
            TransitionResult(probability=0.8, penalty=0.2, is_compatible=True),
            TransitionResult(probability=0.6, penalty=0.4, is_compatible=True),
        ]
        path = PlaylistPath(
            mbids=["a", "b", "c"],
            total_cost=0.6,
            transitions=transitions,
        )
        self.assertAlmostEqual(path.average_compatibility, 0.7)


class TestBidirectionalBeamSearch(unittest.TestCase):
    """Tests for bidirectional beam search."""

    def setUp(self):
        self.kb = MusicKnowledgeBase()

    def tearDown(self):
        self.kb.clear()

    def test_bidirectional_simple(self):
        """A -> B -> C -> D with edges in both directions."""
        graph = {
            "A": ["B"],
            "B": ["A", "C"],
            "D": ["C"],
            "C": ["B", "D"],
        }
        costs = {
            ("A", "B"): 0.1,
            ("B", "C"): 0.1,
            ("C", "D"): 0.1,
            ("B", "A"): 0.1,
            ("C", "B"): 0.1,
            ("D", "C"): 0.1,
            ("A", "D"): 0.5,
            ("B", "D"): 0.3,
            ("C", "A"): 0.3,
            ("D", "A"): 0.5,
        }
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path_bidirectional("A", "D", target_length=4)

        assert path is not None
        self.assertEqual(path.mbids[0], "A")
        self.assertEqual(path.mbids[-1], "D")
        self.assertEqual(path.length, 4)

    def test_bidirectional_meets_in_middle(self):
        """Forward from A reaches C, backward from E reaches C."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "E": ["D"],
            "D": ["C"],
        }
        costs = {
            ("A", "B"): 0.1,
            ("B", "C"): 0.1,
            ("E", "D"): 0.1,
            ("D", "C"): 0.1,
            # Forward-direction costs for rescoring stitched path
            ("C", "D"): 0.1,
            ("D", "E"): 0.1,
            # Heuristic estimates
            ("A", "E"): 0.9,
            ("B", "E"): 0.6,
            ("C", "E"): 0.3,
            ("E", "A"): 0.9,
            ("D", "A"): 0.6,
            ("C", "A"): 0.3,
        }
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path_bidirectional("A", "E", target_length=5)

        assert path is not None
        self.assertEqual(path.mbids, ["A", "B", "C", "D", "E"])
        self.assertAlmostEqual(path.total_cost, 0.4)

    def test_bidirectional_no_path(self):
        """Completely disconnected graph returns None."""
        graph = {"A": ["B"], "B": [], "C": ["D"], "D": []}
        costs = {("A", "B"): 0.1, ("C", "D"): 0.1}
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb,
            search_space=mock_space,
            beam_width=5,
            max_expansions=20,
        )

        path = search.find_path_bidirectional("A", "D", target_length=4)
        self.assertIsNone(path)

    def test_bidirectional_falls_back_when_dest_lacks_features(self):
        """When dest has no features, falls back to unidirectional."""
        graph = {"A": ["B"], "B": ["C"]}
        costs = {("A", "B"): 0.1, ("B", "C"): 0.1, ("A", "C"): 0.5}
        mock_space = MockSearchSpace(graph, costs)
        del mock_space._features["C"]

        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        # Falls back to unidirectional (mock costs don't check features)
        path = search.find_path_bidirectional("A", "C", target_length=3)

        assert path is not None
        self.assertEqual(path.mbids[-1], "C")

    def test_bidirectional_respects_target_length(self):
        """Stitched path is close to target_length."""
        nodes = ["A", "B", "C", "D", "E", "F", "G"]
        graph = {}
        costs = {}
        for i, n1 in enumerate(nodes):
            graph[n1] = [n2 for j, n2 in enumerate(nodes) if i != j]
            for j, n2 in enumerate(nodes):
                if i != j:
                    costs[(n1, n2)] = 0.1 + abs(i - j) * 0.05
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path_bidirectional("A", "G", target_length=5)

        assert path is not None
        self.assertGreaterEqual(path.length, 3)
        self.assertLessEqual(path.length, 7)
        self.assertEqual(path.mbids[0], "A")
        self.assertEqual(path.mbids[-1], "G")

    def test_bidirectional_no_cycles(self):
        """Stitched paths don't contain duplicate nodes."""
        graph = {
            "A": ["B", "C"],
            "B": ["C"],
            "D": ["B", "C"],
            "C": ["B"],
        }
        costs = {
            ("A", "B"): 0.1,
            ("A", "C"): 0.2,
            ("B", "C"): 0.1,
            ("C", "B"): 0.1,
            ("D", "B"): 0.1,
            ("D", "C"): 0.2,
            ("B", "D"): 0.1,
            ("C", "D"): 0.2,
            ("A", "D"): 0.5,
            ("D", "A"): 0.5,
            ("B", "A"): 0.3,
            ("C", "A"): 0.3,
        }
        mock_space = MockSearchSpace(graph, costs)
        search = BeamSearch(
            knowledge_base=self.kb, search_space=mock_space, beam_width=5
        )

        path = search.find_path_bidirectional("A", "D", target_length=3)

        if path is not None:
            self.assertEqual(len(path.mbids), len(set(path.mbids)))


if __name__ == "__main__":
    unittest.main()
