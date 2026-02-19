"""Look up MusicBrainz recording IDs and check data availability."""

import argparse
import sys
import time

import requests

MB_HEADERS = {
    "User-Agent": "WaveGuide/1.0 (https://github.com/waveguide)",
    "Accept": "application/json",
}
LB_ALGOS = [
    "session_based_days_9000_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30",
    "session_based_days_7500_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30",
    "session_based_days_7500_session_300"
    "_contribution_5_threshold_15_limit_50_skip_30"
    "_top_n_listeners_1000",
    "session_based_days_7500_session_300"
    "_contribution_sqrt_threshold_15_limit_50_skip_30"
    "_top_n_listeners_1000",
]


def search_recording(query: str) -> None:
    """Search MusicBrainz for a recording by name and show MBIDs."""
    url = "https://musicbrainz.org/ws/2/recording"
    params = {"query": query, "fmt": "json", "limit": 10}

    resp = requests.get(url, params=params, headers=MB_HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"Search failed (HTTP {resp.status_code})")
        return

    recordings = resp.json().get("recordings", [])
    if not recordings:
        print("No results found.")
        return

    print(f"Results for: {query}\n")
    for i, rec in enumerate(recordings):
        title = rec.get("title", "?")
        artist = rec.get("artist-credit", [{}])[0].get("name", "?")
        mbid = rec.get("id", "?")
        date = rec.get("first-release-date", "")
        print(f"  {i + 1}. {title} - {artist} ({date})")
        print(f"     MBID: {mbid}")

    # Check LB neighbor availability for top 5 (across all algorithms)
    print("\nListenBrainz neighbor check (multi-algorithm):")
    lb_url = "https://labs.api.listenbrainz.org/similar-recordings/json"
    for rec in recordings[:5]:
        mbid = rec.get("id", "")
        title = rec.get("title", "?")
        artist = rec.get("artist-credit", [{}])[0].get("name", "?")
        seen_mbids: set[str] = set()
        algo_hits = 0
        for algo in LB_ALGOS:
            payload = [{"recording_mbids": [mbid], "algorithm": algo}]
            try:
                r = requests.post(lb_url, json=payload, timeout=10)
                data = r.json() if r.status_code == 200 else []
                new = {x["recording_mbid"] for x in data} - seen_mbids
                if new:
                    algo_hits += 1
                seen_mbids.update(x["recording_mbid"] for x in data)
            except Exception:
                pass
        if seen_mbids:
            print(f"  {title} - {artist}: {len(seen_mbids)} neighbors ({algo_hits} algos)")
        else:
            print(f"  {title} - {artist}: no LB data")


def check_mbid(mbid: str) -> None:
    """Check data availability for a given MBID across all 3 APIs."""
    print(f"Checking MBID: {mbid}\n")

    # MusicBrainz
    url = f"https://musicbrainz.org/ws/2/recording/{mbid}"
    resp = requests.get(
        url,
        params={"fmt": "json", "inc": "artists"},
        headers=MB_HEADERS,
        timeout=10,
    )
    if resp.status_code == 200:
        d = resp.json()
        artist = d.get("artist-credit", [{}])[0].get("name", "?")
        print(f"  MusicBrainz: {d.get('title', '?')} by {artist}")
    else:
        print(f"  MusicBrainz: NOT FOUND (HTTP {resp.status_code})")
        return

    time.sleep(1)

    # ListenBrainz neighbors (multi-algorithm)
    lb_url = "https://labs.api.listenbrainz.org/similar-recordings/json"
    all_neighbors: dict[str, dict] = {}
    algo_counts: dict[str, int] = {}
    for algo in LB_ALGOS:
        short_name = algo.split("days_")[1].split("_session")[0] if "days_" in algo else algo[:20]
        payload = [{"recording_mbids": [mbid], "algorithm": algo}]
        try:
            r = requests.post(lb_url, json=payload, timeout=10)
            data = r.json() if r.status_code == 200 else []
            algo_counts[short_name] = len(data)
            for n in data:
                n_mbid = n.get("recording_mbid", "")
                if n_mbid and (n_mbid not in all_neighbors or n.get("score", 0) > all_neighbors[n_mbid].get("score", 0)):
                    n["_algo"] = short_name
                    all_neighbors[n_mbid] = n
        except Exception:
            algo_counts[short_name] = 0

    print(f"  ListenBrainz neighbors: {len(all_neighbors)} (merged from {len(LB_ALGOS)} algorithms)")
    for name, count in algo_counts.items():
        print(f"    days_{name}: {count}")
    top = sorted(all_neighbors.values(), key=lambda x: -x.get("score", 0))[:5]
    for n in top:
        print(
            f"    {n.get('recording_name', '?')} by "
            f"{n.get('artist_credit_name', '?')} "
            f"(score={n.get('score')}, algo=days_{n.get('_algo', '?')})"
        )

    # AcousticBrainz
    ab_url = f"https://acousticbrainz.org/api/v1/low-level?recording_ids={mbid}"
    try:
        r = requests.get(ab_url, timeout=10)
        has_ab = mbid in r.json() if r.status_code == 200 else False
    except Exception:
        has_ab = False
    print(f"  AcousticBrainz: {'YES' if has_ab else 'NO'}")

    if not all_neighbors:
        print("\n  This MBID has no LB neighbors -- cannot be used as source/dest.")
        print("  Try: uv run python -m module2.lookup --search 'song name'")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Look up MusicBrainz recording IDs and check data availability."
    )
    parser.add_argument(
        "--search", type=str, help="Search for a recording by name (e.g. 'Bohemian Rhapsody Queen')"
    )
    parser.add_argument(
        "--check", type=str, help="Check data availability for a specific MBID"
    )

    args = parser.parse_args()

    if not args.search and not args.check:
        parser.print_help()
        return 1

    if args.search:
        search_recording(args.search)

    if args.check:
        check_mbid(args.check)

    return 0


if __name__ == "__main__":
    sys.exit(main())
