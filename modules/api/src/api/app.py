"""Flask API for computing song similarity scores using Module 1."""

import logging
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from module1 import MusicKnowledgeBase
from module1.data_loader import load_track_from_data
from module2 import SearchSpace
from module3 import PlaylistAssembler

logger = logging.getLogger(__name__)

app = Flask(__name__)

ACOUSTICBRAINZ_BASE = "https://acousticbrainz.org/api/v1"

kb = MusicKnowledgeBase()

# ── Module 4: load trained mood classifier (optional, graceful fallback) ──
MOOD_MODEL_PATH = (
    Path(__file__).resolve().parents[3] / "module4" / "models" / "mood_classifier.pkl"
)
mood_classifier = None
try:
    from module4.mood_classifier import MoodClassifier

    if MOOD_MODEL_PATH.exists() and MOOD_MODEL_PATH.stat().st_size > 0:
        mood_classifier = MoodClassifier.load(MOOD_MODEL_PATH)
        logger.info("Loaded mood classifier from %s", MOOD_MODEL_PATH)
    else:
        logger.warning("No trained mood classifier at %s", MOOD_MODEL_PATH)
except Exception as exc:
    logger.warning("Mood classifier unavailable: %s", exc)


VALID_MOODS = {"calm", "chill", "sad", "happy", "energized", "intense"}


def fetch_acousticbrainz(mbid: str) -> tuple[dict, dict]:
    """Fetch low-level and high-level features from AcousticBrainz for a recording MBID."""
    low_resp = requests.get(f"{ACOUSTICBRAINZ_BASE}/{mbid}/low-level", timeout=15)
    low_resp.raise_for_status()
    lowlevel = low_resp.json()

    high_resp = requests.get(f"{ACOUSTICBRAINZ_BASE}/{mbid}/high-level", timeout=15)
    high_resp.raise_for_status()
    highlevel = high_resp.json()

    return lowlevel, highlevel


@app.get("/api/compare")
def compare():
    """Compare two songs by their MusicBrainz recording IDs.

    Query params:
        recording_id_1: MBID of the first recording
        recording_id_2: MBID of the second recording

    Returns:
        JSON with similarity score and component breakdown.
    """
    rid1 = request.args.get("recording_id_1")
    rid2 = request.args.get("recording_id_2")

    if not rid1 or not rid2:
        return jsonify(
            {"error": "Both recording_id_1 and recording_id_2 are required."}
        ), 400

    try:
        low1, high1 = fetch_acousticbrainz(rid1)
    except requests.HTTPError as e:
        return jsonify(
            {"error": f"Failed to fetch AcousticBrainz data for recording_id_1: {e}"}
        ), 502
    except requests.ConnectionError:
        return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    try:
        low2, high2 = fetch_acousticbrainz(rid2)
    except requests.HTTPError as e:
        return jsonify(
            {"error": f"Failed to fetch AcousticBrainz data for recording_id_2: {e}"}
        ), 502
    except requests.ConnectionError:
        return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    track1 = load_track_from_data(low1, high1)
    track2 = load_track_from_data(low2, high2)

    result = kb.get_compatibility(track1, track2)

    return jsonify(
        {
            "recording_id_1": rid1,
            "recording_id_2": rid2,
            "score": round(result.probability, 4),
            "is_compatible": result.is_compatible,
            "components": {
                "key": round(result.key_compatibility, 4),
                "tempo": round(result.tempo_compatibility, 4),
                "energy": round(result.energy_compatibility, 4),
                "loudness": round(result.loudness_compatibility, 4),
                "mood": round(result.mood_compatibility, 4),
                "timbre": round(result.timbre_compatibility, 4),
                "genre": round(result.genre_compatibility, 4),
            },
            "violations": result.violations,
            "explanation": result.explanation,
        }
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/playlist")
def playlist():
    """Generate a playlist path between two songs using Module 2 beam search.

    Query params (provide either an MBID OR a mood label per endpoint):
        source_mbid:  MBID of the source/starting track
        source_mood:  Mood label (calm | chill | sad | happy | energized | intense)
        dest_mbid:    MBID of the destination/ending track
        dest_mood:    Mood label
        length:       Desired playlist length (default: 7)
        beam_width:   Beam width for search (default: 10)

    Returns:
        JSON with playlist metadata including track MBIDs, transitions,
        and compatibility scores.
    """
    source_mbid = request.args.get("source_mbid")
    dest_mbid = request.args.get("dest_mbid")
    source_mood = request.args.get("source_mood")
    dest_mood = request.args.get("dest_mood")
    length_str = request.args.get("length", "7")
    beam_width_str = request.args.get("beam_width", "10")
    length = int(length_str)
    beam_width = int(beam_width_str)

    # Validate that exactly one source spec and one dest spec was given
    if not source_mbid and not source_mood:
        return jsonify({"error": "Either source_mbid or source_mood is required."}), 400
    if not dest_mbid and not dest_mood:
        return jsonify({"error": "Either dest_mbid or dest_mood is required."}), 400

    # Validate mood labels
    for label, val in [("source_mood", source_mood), ("dest_mood", dest_mood)]:
        if val and val not in VALID_MOODS:
            return jsonify(
                {"error": f"Invalid {label}: '{val}'. Must be one of {sorted(VALID_MOODS)}."}
            ), 400

    if (source_mood or dest_mood) and mood_classifier is None:
        return jsonify(
            {"error": "Mood-based seeds requested but no trained MoodClassifier is loaded."}
        ), 503

    # Build the search space; for MBID seeds, fetch AcousticBrainz first.
    search_space = SearchSpace(knowledge_base=kb)

    if source_mbid:
        try:
            source_low, source_high = fetch_acousticbrainz(source_mbid)
            source_track = load_track_from_data(source_low, source_high)
            source_track.mbid = source_mbid
            search_space.add_features(source_mbid, source_track)
        except requests.HTTPError as e:
            return jsonify(
                {"error": f"Failed to fetch AcousticBrainz data for source_mbid: {e}"}
            ), 502
        except requests.ConnectionError:
            return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    if dest_mbid:
        try:
            dest_low, dest_high = fetch_acousticbrainz(dest_mbid)
            dest_track = load_track_from_data(dest_low, dest_high)
            dest_track.mbid = dest_mbid
            search_space.add_features(dest_mbid, dest_track)
        except requests.HTTPError as e:
            return jsonify(
                {"error": f"Failed to fetch AcousticBrainz data for dest_mbid: {e}"}
            ), 502
        except requests.ConnectionError:
            return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    try:
        # Run full Module 3 pipeline (beam search + constraints + explanations)
        assembler = PlaylistAssembler(
            knowledge_base=kb,
            search_space=search_space,
            beam_width=beam_width,
            mood_classifier=mood_classifier,
        )

        playlist = assembler.generate_playlist(
            source_mbid=source_mbid,
            dest_mbid=dest_mbid,
            source_mood=source_mood,
            dest_mood=dest_mood,
            target_length=length,
        )

        if playlist is None:
            return jsonify(
                {
                    "error": "No path found between the specified tracks.",
                    "details": (
                        "Possible reasons: source/destination not in AcousticBrainz, "
                        "no similar recordings available, or search space too sparse."
                    ),
                }
            ), 404

        # Build response with playlist metadata
        tracks = []
        transitions_data = []

        for i, track in enumerate(playlist.tracks):
            track_info = {
                "position": i + 1,
                "mbid": track.mbid,
                "title": track.title,
                "artist": track.artist,
                "album": None,
                "bpm": track.bpm,
                "key": track.key,
                "scale": track.scale,
            }
            tracks.append(track_info)

        path = playlist.path
        for i, t in enumerate(path.transitions):
            transitions_data.append(
                {
                    "from_mbid": path.mbids[i],
                    "to_mbid": path.mbids[i + 1],
                    "probability": round(t.probability, 4),
                    "penalty": round(t.penalty, 4),
                    "is_compatible": t.is_compatible,
                    "components": {
                        "key": round(t.key_compatibility, 4),
                        "tempo": round(t.tempo_compatibility, 4),
                        "energy": round(t.energy_compatibility, 4),
                        "loudness": round(t.loudness_compatibility, 4),
                        "mood": round(t.mood_compatibility, 4),
                        "timbre": round(t.timbre_compatibility, 4),
                        "genre": round(t.genre_compatibility, 4),
                    },
                    "violations": t.violations,
                }
            )

        return jsonify(
            {
                "source_mbid": source_mbid,
                "dest_mbid": dest_mbid,
                "source_mood": source_mood,
                "dest_mood": dest_mood,
                "requested_length": length,
                "actual_length": path.length,
                "total_cost": round(path.total_cost, 4),
                "average_compatibility": round(path.average_compatibility, 4),
                "tracks": tracks,
                "transitions": transitions_data,
                "summary": playlist.explanation.summary,
                "constraints": [
                    {"name": c.name, "satisfied": c.satisfied, "score": round(c.score, 3)}
                    for c in playlist.constraints_applied
                ],
                "quality": playlist.explanation.quality_metrics,
            }
        )

    except Exception as e:
        return jsonify(
            {"error": f"Internal error during playlist generation: {e}"}
        ), 500
