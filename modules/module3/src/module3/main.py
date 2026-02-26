"""CLI entry point for Module 3 playlist assembly.

Usage:
    uv run --package module3 python -m module3.main \
        --source <MBID> --dest <MBID> --length 7 --beam-width 10
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from module1 import MusicKnowledgeBase
from module2 import SearchSpace

from .essentia_client import EssentiaClient
from .playlist_assembler import PlaylistAssembler
from .proxy_pool import ProxyPool


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a playlist path between two tracks"
    )
    parser.add_argument("--source", required=True, help="Source track MBID")
    parser.add_argument("--dest", required=True, help="Destination track MBID")
    parser.add_argument("--length", type=int, default=7, help="Target playlist length")
    parser.add_argument("--beam-width", type=int, default=10, help="Beam search width")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--no-essentia", action="store_true", help="Disable Essentia fallback"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    kb = MusicKnowledgeBase()
    search_space = SearchSpace(kb)

    essentia = None
    if not args.no_essentia:
        essentia = EssentiaClient()
        if not essentia.is_available:
            print("Note: Essentia not installed — audio analysis fallback disabled")
            essentia = None

    proxy_pool = ProxyPool(knowledge_base=kb)
    print(f"Proxy pool: {proxy_pool.size} tracks with known LB connectivity")

    assembler = PlaylistAssembler(
        knowledge_base=kb,
        search_space=search_space,
        essentia_client=essentia,
        beam_width=args.beam_width,
        proxy_pool=proxy_pool,
    )

    print(f"Finding playlist path: {args.source} → {args.dest}")
    print(f"Target length: {args.length}, beam width: {args.beam_width}")
    print()

    playlist = assembler.generate_playlist(
        args.source, args.dest, target_length=args.length
    )

    if playlist is None:
        print("No path found. Possible reasons:")
        print("  - Both tracks have no LB neighbors and no proxy could be found")
        print("  - The graph is too sparse to connect these tracks")
        print("  - API connection issues (try with --verbose for details)")
        sys.exit(1)

    if args.json:
        print(json.dumps(playlist.to_static_output(), indent=2))
        return

    # Pretty-print output
    print(f"=== Playlist ({playlist.length} tracks) ===")
    print(f"Summary: {playlist.explanation.summary}")
    print()

    for te in playlist.explanation.track_explanations:
        role_tag = f" [{te.role}]" if te.role != "waypoint" else ""
        print(f"  {te.position + 1}. {te.title or te.mbid} — {te.artist or 'Unknown'}{role_tag}")

        if te.incoming_transition:
            it = te.incoming_transition
            print(f"     ↑ compatibility: {it.overall_score:.0%}")
            for _dim, _score, desc in it.top_contributors:
                print(f"       • {desc}")

    print()

    # Quality metrics
    qm = playlist.explanation.quality_metrics
    print(f"Quality: avg={qm.get('avg_compatibility', 0):.0%}, "
          f"weakest={qm.get('weakest_transition', 0):.0%}, "
          f"strongest={qm.get('strongest_transition', 0):.0%}")

    # Constraint results
    if playlist.constraints_applied:
        print()
        print("Constraints:")
        for cr in playlist.constraints_applied:
            status = "✓" if cr.satisfied else "✗"
            print(f"  {status} {cr.name} (score: {cr.score:.0%})")
            for v in cr.violations:
                print(f"    - {v}")

    # Proxy pool stats
    print(f"\nProxy pool: {proxy_pool.size} tracks (auto-growing)")


if __name__ == "__main__":
    main()
