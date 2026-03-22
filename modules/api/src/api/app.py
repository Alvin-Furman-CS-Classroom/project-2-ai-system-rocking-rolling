"""Flask API for computing song similarity scores using Module 1."""

import requests
from flask import Flask, jsonify, request
from module1 import MusicKnowledgeBase
from module1.data_loader import load_track_from_data

app = Flask(__name__)

ACOUSTICBRAINZ_BASE = "https://acousticbrainz.org/api/v1"

kb = MusicKnowledgeBase()


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
