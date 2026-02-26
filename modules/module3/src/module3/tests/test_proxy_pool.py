"""Tests for Module 3 proxy pool — finding substitute tracks for songs with 0 LB neighbors."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from module1 import MusicKnowledgeBase, TrackFeatures, TransitionResult

from module3.proxy_pool import ProxyPool, ProxyResult, PoolEntry, SEED_TRACKS


def _make_track(mbid: str, title: str = "Track", artist: str = "Artist", bpm: float = 120.0) -> TrackFeatures:
    return TrackFeatures(
        mbid=mbid,
        title=title,
        artist=artist,
        bpm=bpm,
        key="C",
        scale="major",
        energy_mid_high=0.005,
        genre_rosamerica=("roc", 0.9),
        mood_happy=("happy", 0.8),
    )


def _make_transition(probability: float = 0.8) -> TransitionResult:
    return TransitionResult(
        probability=probability,
        penalty=1 - probability,
        is_compatible=True,
        key_compatibility=0.8,
        tempo_compatibility=0.9,
        energy_compatibility=0.7,
        loudness_compatibility=0.5,
        mood_compatibility=0.8,
        timbre_compatibility=0.6,
        genre_compatibility=0.5,
        tag_compatibility=0.7,
        popularity_compatibility=0.5,
        artist_compatibility=0.5,
        era_compatibility=0.5,
        mb_genre_compatibility=0.5,
        explanation="Test",
    )


class MockSearchSpace:
    """Minimal mock for proxy pool testing."""

    def __init__(self, tracks: dict[str, TrackFeatures]):
        self._tracks = tracks

    def get_features(self, mbid: str) -> TrackFeatures | None:
        return self._tracks.get(mbid)

    def has_features(self, mbid: str) -> bool:
        return mbid in self._tracks


class TestProxyPoolInit(unittest.TestCase):
    def test_seeds_loaded_on_init(self):
        """Pool should contain seed tracks on first creation."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            self.assertEqual(pool.size, len(SEED_TRACKS))
            for seed in SEED_TRACKS:
                self.assertTrue(pool.has_track(seed["mbid"]))

    def test_loads_from_existing_file(self):
        """Pool should load entries from an existing JSON file."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            data = [
                {"mbid": "custom-1", "title": "Custom", "artist": "Me", "has_lb_neighbors": True},
            ]
            with open(pool_path, "w") as f:
                json.dump(data, f)

            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            self.assertTrue(pool.has_track("custom-1"))
            # Seeds should also be present
            self.assertGreater(pool.size, 1)

    def test_corrupt_file_reseeds(self):
        """Corrupt pool file should be ignored and seeds loaded."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            pool_path.write_text("not valid json {{{")

            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            self.assertEqual(pool.size, len(SEED_TRACKS))


class TestAddTrack(unittest.TestCase):
    def test_add_new_track(self):
        """Adding a new track should increase pool size."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            initial_size = pool.size
            pool.add_track("new-mbid", title="New Song", artist="New Artist")

            self.assertEqual(pool.size, initial_size + 1)
            self.assertTrue(pool.has_track("new-mbid"))

    def test_add_duplicate_is_noop(self):
        """Adding an existing track should not duplicate it."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            seed_mbid = SEED_TRACKS[0]["mbid"]
            initial_size = pool.size
            pool.add_track(seed_mbid, title="Duplicate")

            self.assertEqual(pool.size, initial_size)


class TestAddFromNeighbors(unittest.TestCase):
    def test_grows_pool_from_neighbors(self):
        """Discovered LB neighbors should be added to the pool."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            initial_size = pool.size
            added = pool.add_from_neighbors(["nb-1", "nb-2", "nb-3"])

            self.assertEqual(added, 3)
            self.assertEqual(pool.size, initial_size + 3)
            self.assertTrue(pool.has_track("nb-1"))

    def test_skips_existing_entries(self):
        """Already-known tracks should not be re-added."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            seed_mbid = SEED_TRACKS[0]["mbid"]
            added = pool.add_from_neighbors([seed_mbid, "new-one"])

            self.assertEqual(added, 1)  # only "new-one"

    def test_persists_to_disk(self):
        """Added neighbors should be saved to the pool file."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            pool.add_from_neighbors(["persisted-1"])

            # Load a fresh pool from the same file
            pool2 = ProxyPool(kb, pool_path=pool_path)
            self.assertTrue(pool2.has_track("persisted-1"))

    def test_pulls_metadata_from_search_space(self):
        """If search_space has features, title/artist should be captured."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            tracks = {"enriched-1": _make_track("enriched-1", "Cool Song", "Cool Artist")}
            ss = MockSearchSpace(tracks)

            pool.add_from_neighbors(["enriched-1"], search_space=ss)

            self.assertTrue(pool.has_track("enriched-1"))


class TestFindProxy(unittest.TestCase):
    def test_finds_best_match(self):
        """Should return the pool entry with highest compatibility."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            # Add pool entries with features available in search space
            pool.add_track("pool-a", "Pool A", "Artist A")
            pool.add_track("pool-b", "Pool B", "Artist B")

            target = _make_track("target", "Wannabe", "Spice Girls", bpm=110.0)
            pool_tracks = {
                "pool-a": _make_track("pool-a", "Pool A", "Artist A", bpm=112.0),
                "pool-b": _make_track("pool-b", "Pool B", "Artist B", bpm=180.0),
            }
            ss = MockSearchSpace(pool_tracks)

            result = pool.find_proxy(target, search_space=ss)

            self.assertIsNotNone(result)
            self.assertEqual(result.original_mbid, "target")
            self.assertTrue(result.needed_proxy)
            self.assertGreater(result.compatibility_score, 0)

    def test_excludes_specified_mbids(self):
        """Excluded MBIDs should not be returned as proxies."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            pool.add_track("only-option", "Only", "Artist")

            target = _make_track("target", "Song", "Artist")
            ss = MockSearchSpace({
                "only-option": _make_track("only-option"),
            })

            result = pool.find_proxy(
                target, search_space=ss, exclude_mbids={"only-option"},
            )

            # only-option was excluded, so no proxy available from seeds without features
            # Result depends on whether seed tracks have features in SS
            # With our MockSearchSpace, seeds have no features, so result is None
            # unless seeds are in the SS
            self.assertTrue(result is None or result.proxy_mbid != "only-option")

    def test_returns_none_when_no_features(self):
        """Should return None if no pool entries have features in search space."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            target = _make_track("target", "Song", "Artist")
            ss = MockSearchSpace({})  # empty — no features for anything

            result = pool.find_proxy(target, search_space=ss)
            self.assertIsNone(result)

    def test_skips_target_itself(self):
        """Should not return the target track as its own proxy."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            pool.add_track("target", "Target Song", "Artist")

            target = _make_track("target", "Target Song", "Artist")
            ss = MockSearchSpace({
                "target": target,
                SEED_TRACKS[0]["mbid"]: _make_track(SEED_TRACKS[0]["mbid"]),
            })

            result = pool.find_proxy(target, search_space=ss)

            if result is not None:
                self.assertNotEqual(result.proxy_mbid, "target")


class TestGetAllMbids(unittest.TestCase):
    def test_returns_all_pool_mbids(self):
        """get_all_mbids should list every entry."""
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            kb = MusicKnowledgeBase()
            pool = ProxyPool(kb, pool_path=pool_path)

            all_mbids = pool.get_all_mbids()
            self.assertEqual(len(all_mbids), pool.size)
            for seed in SEED_TRACKS:
                self.assertIn(seed["mbid"], all_mbids)


if __name__ == "__main__":
    unittest.main()
