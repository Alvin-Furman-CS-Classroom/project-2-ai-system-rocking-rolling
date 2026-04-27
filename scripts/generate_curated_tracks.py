"""
Generate curated_tracks.json and genre_artists.json for the Wave Guide demo presentation.

Pipeline:
  1. ListenBrainz sitewide top-1k artists        → candidate artist MBIDs
  2. MusicBrainz PostgreSQL                       → genre tags for artists → bucket + select
  3. ListenBrainz popularity API                  → top recordings per selected artists
  4. AcousticBrainz API (with disk cache)         → filter to available tracks + fetch features
  5. Module 4 mood classifier                     → mood label per track
  6. Cell cap (genre × mood, max 8/cell)          → output JSON files

Usage:
  uv run python scripts/generate_curated_tracks.py \\
    --out-dir presentation/src/data \\
    --model modules/module4/models/mood_classifier.pkl \\
    --mb-host 192.168.1.10 --mb-port 5432 \\
    --mb-user metabrainz --mb-password metabrainz --mb-role musicbrainz_readonly
"""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import psycopg2
import requests
from liblistenbrainz import ListenBrainz
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Genre bucketing
# ---------------------------------------------------------------------------

GENRE_BUCKETS: dict[str, list[str]] = {
    "rock":       ["rock", "alternative", "indie", "punk", "grunge", "metal", "hard rock"],
    "pop":        ["pop", "synth-pop", "dance-pop", "electropop", "k-pop", "j-pop"],
    "electronic": ["electronic", "ambient", "techno", "house", "edm", "trance",
                   "drum and bass", "idm", "downtempo", "chillwave", "trip-hop"],
    "hip-hop":    ["hip-hop", "hip hop", "rap", "trap", "r&b", "soul", "funk"],
    "jazz":       ["jazz", "bebop", "fusion", "blues", "swing", "bossa nova"],
    "classical":  ["classical", "orchestral", "baroque", "chamber", "opera", "contemporary classical"],
    "folk":       ["folk", "country", "americana", "singer-songwriter", "acoustic", "bluegrass"],
}


def bucket_from_tags(tags: list[str]) -> str | None:
    tags_lower = [t.lower() for t in tags]
    for bucket, keywords in GENRE_BUCKETS.items():
        if any(any(kw in tag for kw in keywords) for tag in tags_lower):
            return bucket
    return None


# ---------------------------------------------------------------------------
# Step 1: ListenBrainz sitewide top artists
# ---------------------------------------------------------------------------

def fetch_top_artists(client: ListenBrainz, count: int = 1000) -> list[dict]:
    """Returns [{artist_mbid, artist_name, rank}, ...] sorted by descending popularity."""
    print(f"[1/6] Fetching top {count} artists from ListenBrainz…")
    artists: list[dict] = []
    page_size = 100
    for offset in range(0, count, page_size):
        batch = min(page_size, count - offset)
        data = client._get(
            "/1/stats/sitewide/artists",
            params={"count": batch, "offset": offset, "range": "all_time"},
        )
        for item in data.get("payload", {}).get("artists", []):
            mbid = item.get("artist_mbid")
            if mbid:
                artists.append({
                    "artist_mbid": mbid,
                    "artist_name": item.get("artist_name", ""),
                    "rank": len(artists),
                })
        time.sleep(0.3)
    print(f"    → {len(artists)} artists retrieved")
    return artists


# ---------------------------------------------------------------------------
# Step 2: Genre bucketing via MusicBrainz DB (artist-level)
# ---------------------------------------------------------------------------

def fetch_artist_genres(
    artists: list[dict],
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str = "musicbrainz",
    role: str | None = None,
) -> dict[str, str]:
    """Returns {artist_mbid: genre_bucket} for artists that match a genre bucket."""
    mbids = [a["artist_mbid"] for a in artists]
    print(f"[2/6] Querying MusicBrainz DB for genre tags on {len(mbids)} artists…")
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    try:
        with conn.cursor() as cur:
            if role:
                cur.execute(f"SET ROLE {role}")
            cur.execute("SET search_path TO musicbrainz, public")
            cur.execute(
                """
                SELECT a.gid::text,
                       array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) AS tags
                FROM artist a
                LEFT JOIN artist_tag at ON at.artist = a.id
                LEFT JOIN tag t ON at.tag = t.id
                WHERE a.gid = ANY(%s::uuid[])
                GROUP BY a.gid
                """,
                (mbids,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    result: dict[str, str] = {}
    for mbid, tags in rows:
        bucket = bucket_from_tags(tags or [])
        if bucket:
            result[mbid] = bucket
    print(f"    → {len(result)} artists matched a genre bucket")
    return result


def select_artists_by_genre(
    artists: list[dict],
    artist_genres: dict[str, str],
    artists_per_genre: int = 20,
) -> dict[str, list[dict]]:
    """Returns {genre: [artist_dicts]} with at most artists_per_genre per genre, sorted by rank."""
    by_genre: dict[str, list[dict]] = defaultdict(list)
    for a in artists:  # already in rank order
        genre = artist_genres.get(a["artist_mbid"])
        if genre and len(by_genre[genre]) < artists_per_genre:
            by_genre[genre].append(a)

    print("    Selected artists per genre:")
    for genre, lst in sorted(by_genre.items()):
        print(f"      {genre:14} {len(lst)}")
    return dict(by_genre)


def apply_genre_overrides(
    artists_by_genre: dict[str, list[dict]],
    overrides: dict[str, list[str]],
) -> dict[str, list[dict]]:
    """
    Replace the artist list for any genre present in `overrides` with the
    provided MBIDs.  Genres not in `overrides` are left unchanged.
    """
    result = dict(artists_by_genre)
    for genre, mbids in overrides.items():
        result[genre] = [
            {"artist_mbid": mbid, "artist_name": "", "rank": i}
            for i, mbid in enumerate(mbids)
        ]
        print(f"    Override applied: {genre:14} {len(mbids)} artists (from file)")
    return result


# ---------------------------------------------------------------------------
# Step 3: ListenBrainz popularity API — top recordings per artist
# ---------------------------------------------------------------------------

def fetch_top_recordings_for_artists(
    client: ListenBrainz,
    artists_by_genre: dict[str, list[dict]],
    tracks_per_artist: int = 10,
) -> list[dict]:
    """
    Returns [{mbid, title, artist, genre, _rank}, ...] deduplicated by mbid.
    _rank encodes artist popularity (lower = more popular) + position within artist.
    """
    total_artists = sum(len(v) for v in artists_by_genre.values())
    print(f"[3/6] Fetching top recordings for {total_artists} artists…")

    seen: set[str] = set()
    candidates: list[dict] = []

    with tqdm(total=total_artists, unit="artist", dynamic_ncols=True) as bar:
        for genre, artist_list in artists_by_genre.items():
            for artist in artist_list:
                artist_mbid = artist["artist_mbid"]
                bar.set_description(artist["artist_name"][:30])
                try:
                    recordings = client._get(
                        f"/1/popularity/top-recordings-for-artist/{artist_mbid}",
                    )
                    for i, rec in enumerate(recordings[:tracks_per_artist]):
                        rec_mbid = rec.get("recording_mbid")
                        if rec_mbid and rec_mbid not in seen:
                            seen.add(rec_mbid)
                            candidates.append({
                                "mbid": rec_mbid,
                                "title": rec.get("recording_name"),
                                "artist": rec.get("artist_name"),
                                "genre": genre,
                                "_rank": artist["rank"] * 1000 + i,
                            })
                except Exception:
                    pass
                bar.update(1)
                time.sleep(0.1)

    print(f"    → {len(candidates)} candidate recordings")
    return candidates


# ---------------------------------------------------------------------------
# Step 4: AcousticBrainz availability + feature fetch (with disk cache)
# ---------------------------------------------------------------------------

AB_BASE = "https://acousticbrainz.org/api/v1"


def fetch_acousticbrainz(mbid: str) -> tuple[dict, dict] | None:
    try:
        low = requests.get(f"{AB_BASE}/{mbid}/low-level", timeout=10)
        if low.status_code != 200:
            return None
        high = requests.get(f"{AB_BASE}/{mbid}/high-level", timeout=10)
        if high.status_code != 200:
            return None
        return low.json(), high.json()
    except requests.RequestException:
        return None


def _cache_path(cache_dir: Path, mbid: str) -> Path:
    return cache_dir / f"{mbid}.json"


def _load_cache(cache_dir: Path, mbid: str) -> tuple[dict, dict] | None:
    p = _cache_path(cache_dir, mbid)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return data["low"], data["high"]
    except (KeyError, json.JSONDecodeError):
        return None


def _save_cache(cache_dir: Path, mbid: str, low: dict, high: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_path(cache_dir, mbid).write_text(
        json.dumps({"low": low, "high": high}, ensure_ascii=False)
    )


def filter_by_acousticbrainz(
    mbids: list[str],
    cache_dir: Path | None = None,
) -> dict[str, tuple[dict, dict]]:
    print(f"[4/6] Checking AcousticBrainz availability for {len(mbids)} MBIDs…")
    if cache_dir:
        print(f"      (cache: {cache_dir})")
    available: dict[str, tuple[dict, dict]] = {}
    cache_hits = 0

    with tqdm(mbids, unit="track", dynamic_ncols=True) as bar:
        for i, mbid in enumerate(bar):
            if cache_dir:
                cached = _load_cache(cache_dir, mbid)
                if cached is not None:
                    available[mbid] = cached
                    cache_hits += 1
                    bar.set_postfix(found=len(available), cached=cache_hits)
                    continue

            result = fetch_acousticbrainz(mbid)
            if result:
                available[mbid] = result
                if cache_dir:
                    _save_cache(cache_dir, mbid, result[0], result[1])
            bar.set_postfix(found=len(available), cached=cache_hits)
            time.sleep(0.1)
            if i > 0 and i % 25 == 0:
                time.sleep(0.3)

    print(f"    → {len(available)} tracks available in AcousticBrainz ({cache_hits} from cache)")
    return available


# ---------------------------------------------------------------------------
# Step 5: Module 4 mood classification
# ---------------------------------------------------------------------------

def classify_moods(
    ab_data: dict[str, tuple[dict, dict]],
    model_path: str,
) -> dict[str, dict]:
    """Returns {mbid: {mood, bpm, key, scale}} for classifiable tracks."""
    print(f"[5/6] Classifying moods for {len(ab_data)} tracks using Module 4…")
    from module1.data_loader import load_track_from_data
    from module4 import MoodClassifier

    classifier = MoodClassifier.load(model_path)

    results: dict[str, dict] = {}
    errors = 0

    with tqdm(ab_data.items(), total=len(ab_data), unit="track", dynamic_ncols=True) as bar:
        for mbid, (lowlevel, highlevel) in bar:
            try:
                features = load_track_from_data(lowlevel, highlevel)
                classification = classifier.classify_track(features)
                results[mbid] = {
                    "mood": classification.mood.value,
                    "bpm": features.bpm,
                    "key": features.key,
                    "scale": features.scale,
                }
            except Exception:
                errors += 1
            bar.set_postfix(ok=len(results), err=errors)

    print(f"    → {len(results)} classified, {errors} errors")
    return results


# ---------------------------------------------------------------------------
# Step 6: Assemble output, cap cells, write JSON
# ---------------------------------------------------------------------------

def assemble_and_write(
    candidates_by_mbid: dict[str, dict],
    mood_data: dict[str, dict],
    out_dir: Path,
    max_per_cell: int = 8,
) -> None:
    print("[6/6] Assembling dataset…")

    tracks = []
    for mbid, mood_info in tqdm(mood_data.items(), desc="  Assembling", unit="track", dynamic_ncols=True):
        cand = candidates_by_mbid.get(mbid, {})
        tracks.append({
            "mbid": mbid,
            "title": cand.get("title"),
            "artist": cand.get("artist"),
            "genre": cand.get("genre"),
            "genre_tags": [],
            "mood": mood_info["mood"],
            "bpm": round(mood_info["bpm"]) if mood_info["bpm"] else None,
            "key": mood_info["key"],
            "scale": mood_info["scale"],
            "_rank": cand.get("_rank", 9999),
        })

    # Drop tracks missing genre (shouldn't happen, but guard anyway)
    tracks = [t for t in tracks if t["genre"]]

    # Sort by rank (lower = more popular) within each cell
    tracks.sort(key=lambda t: t["_rank"])

    # Cap cells: max_per_cell per (genre, mood) combination
    cell_counts: dict[tuple[str, str], int] = defaultdict(int)
    capped: list[dict] = []
    for t in tracks:
        cell = (t["genre"], t["mood"])
        if cell_counts[cell] < max_per_cell:
            cell_counts[cell] += 1
            capped.append(t)

    for t in capped:
        del t["_rank"]

    # Print coverage table
    all_genres = sorted(GENRE_BUCKETS.keys())
    all_moods = ["calm", "energized", "happy", "sad", "intense", "chill"]
    print(f"\n  Coverage table (tracks per genre × mood, max {max_per_cell}):\n")
    header = f"{'':14}" + "".join(f"{m:12}" for m in all_moods) + f"{'TOTAL':8}"
    print(f"  {header}")
    print(f"  {'-' * len(header)}")
    for g in all_genres:
        row = f"  {g:14}"
        total = 0
        for m in all_moods:
            n = cell_counts.get((g, m), 0)
            row += f"{n:<12}"
            total += n
        row += f"{total:<8}"
        print(row)
    print(f"  {'-' * len(header)}")
    grand = sum(cell_counts.values())
    col_totals = "".join(
        f"{sum(cell_counts.get((g, m), 0) for g in all_genres):<12}" for m in all_moods
    )
    print(f"  {'TOTAL':14}{col_totals}{grand:<8}\n")

    # Build genre_artists.json: genre → artist → [mbids]
    genre_artists: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for t in capped:
        if t["artist"]:
            genre_artists[t["genre"]][t["artist"]].append(t["mbid"])

    out_dir.mkdir(parents=True, exist_ok=True)

    tracks_path = out_dir / "curated_tracks.json"
    with open(tracks_path, "w") as f:
        json.dump(capped, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(capped)} tracks → {tracks_path}")

    artists_path = out_dir / "genre_artists.json"
    with open(artists_path, "w") as f:
        json.dump({g: dict(a) for g, a in genre_artists.items()}, f, indent=2, ensure_ascii=False)
    print(f"  Wrote genre_artists.json → {artists_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Wave Guide demo track dataset")
    parser.add_argument("--out-dir", default="presentation/src/data", help="Output directory")
    parser.add_argument("--model", default="modules/module4/models/mood_classifier.pkl", help="Path to mood classifier .pkl")
    parser.add_argument("--mb-host", default="192.168.1.10")
    parser.add_argument("--mb-port", type=int, default=5432)
    parser.add_argument("--mb-user", default="metabrainz")
    parser.add_argument("--mb-password", default="metabrainz")
    parser.add_argument("--mb-role", default="musicbrainz_readonly")
    parser.add_argument("--lb-artists", type=int, default=1000, help="Number of sitewide top artists to fetch")
    parser.add_argument("--artists-per-genre", type=int, default=20, help="Max artists to select per genre bucket")
    parser.add_argument("--tracks-per-artist", type=int, default=10, help="Top recordings to fetch per artist")
    parser.add_argument("--max-per-cell", type=int, default=8, help="Max tracks per (genre, mood) cell")
    parser.add_argument("--cache-dir", default=".cache/acousticbrainz", help="Directory for AcousticBrainz response cache (set to '' to disable)")
    parser.add_argument("--genre-artists", default="", help="Path to JSON file with genre → [artist_mbids] overrides for underrepresented genres")
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    conn_args = dict(
        host=args.mb_host, port=args.mb_port,
        user=args.mb_user, password=args.mb_password,
        role=args.mb_role,
    )

    client = ListenBrainz()

    # Step 1: Top artists
    artists = fetch_top_artists(client, count=args.lb_artists)

    # Step 2: Genre bucketing via MB DB
    artist_genres = fetch_artist_genres(artists, **conn_args)
    artists_by_genre = select_artists_by_genre(artists, artist_genres, args.artists_per_genre)
    if args.genre_artists:
        overrides = json.loads(Path(args.genre_artists).read_text())
        artists_by_genre = apply_genre_overrides(artists_by_genre, overrides)
    if not artists_by_genre:
        print("ERROR: No artists matched any genre bucket. Check MB DB connectivity.")
        return

    # Step 3: Top recordings per artist
    candidates = fetch_top_recordings_for_artists(client, artists_by_genre, args.tracks_per_artist)
    if not candidates:
        print("ERROR: No candidate recordings retrieved. Check ListenBrainz connectivity.")
        return
    candidates_by_mbid = {c["mbid"]: c for c in candidates}

    # Step 4: AcousticBrainz filter
    mbids = list(candidates_by_mbid.keys())
    ab_data = filter_by_acousticbrainz(mbids, cache_dir=cache_dir)
    if not ab_data:
        print("ERROR: No tracks found in AcousticBrainz. Check network connectivity.")
        return

    # Step 5: Mood classification
    mood_data = classify_moods(ab_data, args.model)
    if not mood_data:
        print("ERROR: No tracks classified. Check model path.")
        return

    # Step 6: Assemble + write
    assemble_and_write(
        candidates_by_mbid=candidates_by_mbid,
        mood_data=mood_data,
        out_dir=Path(args.out_dir),
        max_per_cell=args.max_per_cell,
    )

    print("Done.")


if __name__ == "__main__":
    main()
