"""Main entry point for Module 2 demos and CLI usage."""

import argparse
import sys

from module1 import MusicKnowledgeBase

from .beam_search import BeamSearch
from .search_space import SearchSpace


def find_playlist_path(
    source_mbid: str,
    dest_mbid: str,
    target_length: int = 7,
    beam_width: int = 10,
) -> None:
    """Find and display a playlist path between two tracks."""
    print(f"Finding path from {source_mbid} to {dest_mbid}")
    print(f"Target length: {target_length} tracks")
    print(f"Beam width: {beam_width}")
    print("-" * 60)

    kb = MusicKnowledgeBase()
    search_space = SearchSpace(knowledge_base=kb)
    search = BeamSearch(
        knowledge_base=kb,
        search_space=search_space,
        beam_width=beam_width,
    )

    try:
        print("Searching for path (bidirectional)...")
        path = search.find_path_bidirectional(
            source_mbid=source_mbid,
            dest_mbid=dest_mbid,
            target_length=target_length,
        )

        if path is None:
            print("\nNo path found!")
            print("Possible reasons:")
            print("  - Source or destination track not in AcousticBrainz")
            print("  - No similar recordings available in ListenBrainz")
            print("  - Search space too sparse")
            return

        print(f"\nFound path with {path.length} tracks:")
        print(f"Total cost: {path.total_cost:.3f}")
        print(f"Average compatibility: {path.average_compatibility:.1%}")
        print("\nPath:")

        for i, mbid in enumerate(path.mbids):
            features = search_space.get_features(mbid)
            if features:
                title = features.title or "Unknown"
                artist = features.artist or "Unknown"
                print(f"  {i + 1}. {title} - {artist}")
                print(f"      MBID: {mbid}")
            else:
                print(f"  {i + 1}. {mbid}")

            if i < len(path.transitions):
                t = path.transitions[i]
                compat = "+" if t.is_compatible else "-"
                print(f"      -> [{compat}] {t.probability:.1%} compatible")
                # Show per-dimension breakdown
                dims = [
                    ("key", t.key_compatibility),
                    ("tempo", t.tempo_compatibility),
                    ("energy", t.energy_compatibility),
                    ("mood", t.mood_compatibility),
                    ("timbre", t.timbre_compatibility),
                    ("tags", t.tag_compatibility),
                    ("artist", t.artist_compatibility),
                ]
                active = [f"{n}={v:.0%}" for n, v in dims if v > 0.01]
                if active:
                    print(f"         {', '.join(active)}")

        stats = search_space.cache_stats()
        print("\nCache stats:")
        print(f"  Neighbors cached: {stats['neighbors_cached']}")
        print(f"  Features cached: {stats['features_cached']}")

    finally:
        kb.clear()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Find a playlist path between two tracks using beam search."
    )
    parser.add_argument(
        "--source", required=True, help="Source track MusicBrainz recording ID"
    )
    parser.add_argument(
        "--dest", required=True, help="Destination track MusicBrainz recording ID"
    )
    parser.add_argument(
        "--length", type=int, default=7, help="Target playlist length (default: 7)"
    )
    parser.add_argument(
        "--beam-width", type=int, default=10, help="Beam width for search (default: 10)"
    )

    args = parser.parse_args()

    find_playlist_path(
        source_mbid=args.source,
        dest_mbid=args.dest,
        target_length=args.length,
        beam_width=args.beam_width,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
