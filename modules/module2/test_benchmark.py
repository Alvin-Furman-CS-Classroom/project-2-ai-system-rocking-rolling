"""Benchmark: Postgres (MusicBrainzDB) vs Public API (MusicBrainzClient)

Run from project root:
    uv run python modules/module2/test_benchmark.py
"""

import sys
import time

sys.path.insert(0, "modules/module2/src")
sys.path.insert(0, "modules/module1/src")

from module2.musicbrainz_db import MusicBrainzDB
from module2.musicbrainz_client import MusicBrainzClient

# Real MBIDs — proxy pool seeds + well-known tracks verified in both DB and public API
TEST_MBIDS = [
    "1eac49da-3399-4d34-bbf3-a98a91e2758b",  # Congregation - Foo Fighters
    "80c24793-6a40-4edb-b1bb-5a4e3946901e",  # Little Monster - Royal Blood
    "ffcb45c3-7f32-427d-b3d4-287664bbcdb9",  # What Kind of Man - Florence + the Machine
    "564ccd5c-c4d3-4752-9abf-c33bb085d6a5",  # The Lost Art of Conversation - Pink Floyd
]

ARTIST_MBIDS = [
    "67f66c07-6e61-4026-ade5-7e782fad3a5d",  # Foo Fighters
    "aa62b28e-b6d4-4086-91d4-e5fac1ed56f3",  # Royal Blood
    "5fee3020-513b-48c2-b1f7-4681b01db0c6",  # Florence + the Machine
    "83d91898-7763-47d7-b03b-b92132375c47",  # Pink Floyd
    "a74b1b7f-71a5-4011-9441-d0b5e4122711",  # Radiohead
]


def bench(name, fn):
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    print(f"  {name}: {elapsed:.3f}s")
    return elapsed


def run_postgres(mbids):
    print("\n=== Postgres (MusicBrainzDB) ===")
    db = MusicBrainzDB()
    times = {}

    times["4 single lookups"] = bench(
        "4 single lookups",
        lambda: [db.get_recording_metadata(m) for m in mbids],
    )
    db.clear_cache()

    times["4-MBID batch"] = bench(
        "4-MBID batch",
        lambda: db.get_recording_metadata_batch(mbids),
    )
    db.clear_cache()

    times["5 artist rels"] = bench(
        "5 artist rels",
        lambda: [db.get_artist_relationships(a) for a in ARTIST_MBIDS],
    )

    db.close()
    return times


def run_api(mbids):
    print("\n=== Public API (MusicBrainzClient) ===")
    print("  (this will take ~10s+ due to 1 req/sec rate limit)")
    api = MusicBrainzClient()
    times = {}

    times["4 single lookups"] = bench(
        "4 single lookups",
        lambda: [api.get_recording_metadata(m) for m in mbids],
    )
    api.clear_cache()

    times["4-MBID batch"] = bench(
        "4-MBID batch",
        lambda: api.get_recording_metadata_batch(mbids),
    )
    api.clear_cache()

    times["5 artist rels"] = bench(
        "5 artist rels",
        lambda: [api.get_artist_relationships(a) for a in ARTIST_MBIDS],
    )

    api.close()
    return times


if __name__ == "__main__":
    mbids = TEST_MBIDS

    # Run Postgres first (fast)
    pg_times = run_postgres(mbids)

    # Run API (slow — rate limited)
    api_times = run_api(mbids)

    # Results
    print(f"\n{'Query':<25} {'API':>10} {'Postgres':>10} {'Speedup':>10}")
    print("=" * 55)
    for name in pg_times:
        old = api_times[name]
        new = pg_times[name]
        speedup = old / new if new > 0 else float("inf")
        print(f"{name:<25} {old:>9.3f}s {new:>9.3f}s {speedup:>9.0f}x")

    total_api = sum(api_times.values())
    total_pg = sum(pg_times.values())
    print("-" * 55)
    print(
        f"{'TOTAL':<25} {total_api:>9.3f}s {total_pg:>9.3f}s {total_api / total_pg:>9.0f}x"
    )

    # Save results to markdown
    from datetime import datetime
    from pathlib import Path

    out = Path(__file__).resolve().parent.parent.parent / "BENCHMARKS.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    is_new = not out.exists()

    with open(out, "a") as f:
        if is_new:
            f.write("# Benchmarks\n\n")
            f.write("Postgres (local MusicBrainz mirror) vs Public API.\n\n")

        f.write(f"## {timestamp}\n\n")
        f.write("| Query | API | Postgres | Speedup |\n")
        f.write("|-------|-----|----------|---------|\n")
        for name in pg_times:
            old = api_times[name]
            new = pg_times[name]
            speedup = old / new if new > 0 else float("inf")
            f.write(f"| {name} | {old:.3f}s | {new:.3f}s | {speedup:.0f}x |\n")
        f.write(
            f"| **TOTAL** | **{total_api:.3f}s** | **{total_pg:.3f}s** | **{total_api / total_pg:.0f}x** |\n"
        )
        f.write("\n")

    print(f"\nResults saved to {out}")
