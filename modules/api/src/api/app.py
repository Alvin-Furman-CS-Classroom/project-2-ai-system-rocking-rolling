"""Flask API for Wave Guide — song similarity, playlist generation, and mood support."""

from pathlib import Path

import requests
from flask import Flask, jsonify, request
from module1 import MusicKnowledgeBase
from module1.data_loader import load_track_from_data
from module2 import SearchSpace
from module4 import MoodClassifier, MoodLabel
from module5 import PlaylistOrchestrator, PlaylistRequest, TrackInput

app = Flask(__name__)

ACOUSTICBRAINZ_BASE = "https://acousticbrainz.org/api/v1"

_MODEL_PATH = Path(__file__).parents[3] / "module4" / "models" / "mood_classifier.pkl"

kb = MusicKnowledgeBase()
classifier = MoodClassifier.load(_MODEL_PATH)
orchestrator = PlaylistOrchestrator(knowledge_base=kb, classifier=classifier)


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


@app.get("/api/moods")
def moods():
    """Return the list of available mood labels for mood-based playlist input."""
    return jsonify({"moods": [m.value for m in MoodLabel]})


@app.get("/api/playlist")
def playlist():
    """Generate a playlist path between two tracks or moods.

    Exactly one of source_mbid / source_mood must be provided, and exactly one
    of dest_mbid / dest_mood must be provided.

    Query params:
        source_mbid:  MBID of the source/starting track  (mutually exclusive with source_mood)
        source_mood:  Mood label for the source           (mutually exclusive with source_mbid)
        dest_mbid:    MBID of the destination track       (mutually exclusive with dest_mood)
        dest_mood:    Mood label for the destination      (mutually exclusive with dest_mbid)
        length:       Desired playlist length (default: 7)
        beam_width:   Beam width for search (default: 10)

    Returns:
        JSON with playlist metadata including track MBIDs, transitions,
        compatibility scores, and per-track feature data for visualization.
    """
    source_mbid = request.args.get("source_mbid")
    source_mood = request.args.get("source_mood")
    dest_mbid = request.args.get("dest_mbid")
    dest_mood = request.args.get("dest_mood")
    length = int(request.args.get("length", "7"))
    beam_width = int(request.args.get("beam_width", "10"))

    # Validate: exactly one source and one destination
    if not source_mbid and not source_mood:
        return jsonify({"error": "Provide either source_mbid or source_mood."}), 400
    if source_mbid and source_mood:
        return jsonify({"error": "Provide only one of source_mbid or source_mood."}), 400
    if not dest_mbid and not dest_mood:
        return jsonify({"error": "Provide either dest_mbid or dest_mood."}), 400
    if dest_mbid and dest_mood:
        return jsonify({"error": "Provide only one of dest_mbid or dest_mood."}), 400

    # Validate mood labels
    valid_moods = {m.value for m in MoodLabel}
    if source_mood and source_mood.lower() not in valid_moods:
        return jsonify({"error": f"Unknown source_mood '{source_mood}'. Valid: {sorted(valid_moods)}"}), 400
    if dest_mood and dest_mood.lower() not in valid_moods:
        return jsonify({"error": f"Unknown dest_mood '{dest_mood}'. Valid: {sorted(valid_moods)}"}), 400

    # For MBID inputs, pre-fetch AcousticBrainz features and seed the search space
    # so the assembler doesn't need to re-fetch them.
    seed_search_space = SearchSpace(knowledge_base=kb)

    if source_mbid:
        try:
            src_low, src_high = fetch_acousticbrainz(source_mbid)
            src_track = load_track_from_data(src_low, src_high)
            src_track.mbid = source_mbid
            seed_search_space.add_features(source_mbid, src_track)
        except requests.HTTPError as e:
            return jsonify({"error": f"Failed to fetch AcousticBrainz data for source: {e}"}), 502
        except requests.ConnectionError:
            return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    if dest_mbid:
        try:
            dst_low, dst_high = fetch_acousticbrainz(dest_mbid)
            dst_track = load_track_from_data(dst_low, dst_high)
            dst_track.mbid = dest_mbid
            seed_search_space.add_features(dest_mbid, dst_track)
        except requests.HTTPError as e:
            return jsonify({"error": f"Failed to fetch AcousticBrainz data for destination: {e}"}), 502
        except requests.ConnectionError:
            return jsonify({"error": "Could not connect to AcousticBrainz API."}), 502

    # Build TrackInputs
    source_input = (
        TrackInput(type="mbid", mbid=source_mbid)
        if source_mbid
        else TrackInput(type="mood", mood=source_mood)
    )
    dest_input = (
        TrackInput(type="mbid", mbid=dest_mbid)
        if dest_mbid
        else TrackInput(type="mood", mood=dest_mood)
    )

    try:
        playlist = orchestrator.generate(
            PlaylistRequest(
                source=source_input,
                destination=dest_input,
                length=length,
                beam_width=beam_width,
            ),
            search_space=seed_search_space,
        )

        if playlist is None:
            return jsonify(
                {
                    "error": "No path found between the specified tracks or moods.",
                    "details": (
                        "Possible reasons: source/destination not in AcousticBrainz, "
                        "no similar recordings available, or search space too sparse."
                    ),
                }
            ), 404

        # Build response
        tracks_data = []
        for i, track in enumerate(playlist.tracks):
            # Compute per-track mood classification for visualization
            mood_label = None
            mood_confidence = None
            try:
                classification = classifier.classify_track(track)
                mood_label = classification.mood.value
                mood_confidence = round(classification.confidence, 4)
            except Exception:
                pass

            # Combined energy score (average of energy bands)
            energy = None
            bands = [track.energy_low, track.energy_mid_low, track.energy_mid_high, track.energy_high]
            valid_bands = [b for b in bands if b is not None]
            if valid_bands:
                energy = round(sum(valid_bands) / len(valid_bands), 4)

            tracks_data.append(
                {
                    "position": i + 1,
                    "mbid": track.mbid,
                    "title": track.title,
                    "artist": track.artist,
                    "album": None,
                    "bpm": round(track.bpm) if track.bpm else None,
                    "key": track.key,
                    "scale": track.scale,
                    "energy": energy,
                    "mood_label": mood_label,
                    "mood_confidence": mood_confidence,
                }
            )

        path = playlist.path
        transitions_data = []
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
                "source_mood": source_mood,
                "dest_mbid": dest_mbid,
                "dest_mood": dest_mood,
                "requested_length": length,
                "actual_length": path.length,
                "total_cost": round(path.total_cost, 4),
                "average_compatibility": round(path.average_compatibility, 4),
                "tracks": tracks_data,
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
        return jsonify({"error": f"Internal error during playlist generation: {e}"}), 500
