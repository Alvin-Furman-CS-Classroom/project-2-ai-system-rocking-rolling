"""Explanation and transparency for playlist generation.

Generates human-readable explanations at three levels:
1. Playlist summary — one sentence describing the musical journey
2. Per-transition explanation — top dimensions that drove each score
3. Constraint notes — how constraints shaped the final playlist
"""

from module1 import TrackFeatures, TransitionResult, UserPreferences

from .data_models import (
    ConstraintResult,
    PlaylistExplanation,
    TrackExplanation,
    TransitionExplanation,
)

DIMENSION_NAMES = [
    "key",
    "tempo",
    "energy",
    "loudness",
    "mood",
    "timbre",
    "genre",
    "tag",
    "popularity",
    "artist",
    "era",
    "mb_genre",
]

DIMENSION_LABELS = {
    "key": "Key",
    "tempo": "Tempo",
    "energy": "Energy",
    "loudness": "Loudness",
    "mood": "Mood",
    "timbre": "Timbre",
    "genre": "Genre",
    "tag": "Tags",
    "popularity": "Popularity",
    "artist": "Artist",
    "era": "Era",
    "mb_genre": "MB Genre",
}


def _get_dimension_score(transition: TransitionResult, dim: str) -> float:
    """Get the compatibility score for a dimension from a TransitionResult."""
    return getattr(transition, f"{dim}_compatibility", 0.0)


def _get_weight(prefs: UserPreferences, dim: str) -> float:
    """Get the weight for a dimension from UserPreferences."""
    return getattr(prefs, f"{dim}_weight", 0.0)


def _dimension_description(
    dim: str,
    score: float,
    track1: TrackFeatures | None = None,
    track2: TrackFeatures | None = None,
) -> str:
    """Generate a human-readable description for a dimension score."""
    label = DIMENSION_LABELS.get(dim, dim.title())

    if score >= 0.9:
        quality = "Excellent"
    elif score >= 0.7:
        quality = "Good"
    elif score >= 0.5:
        quality = "Moderate"
    elif score >= 0.3:
        quality = "Weak"
    else:
        quality = "Poor"

    # Add specifics when track data is available
    if track1 and track2:
        if dim == "tempo" and track1.bpm and track2.bpm:
            return f"{quality} tempo match ({track1.bpm:.0f} → {track2.bpm:.0f} BPM)"
        if dim == "key":
            return f"{quality} key match ({track1.key} {track1.scale} → {track2.key} {track2.scale})"
        if dim == "energy":
            return f"{quality} energy match ({track1.energy_score:.3f} → {track2.energy_score:.3f})"
        if dim == "mood":
            m1 = _get_top_mood(track1)
            m2 = _get_top_mood(track2)
            return f"{quality} mood match ({m1} → {m2})"
        if dim == "genre" and track1.genre_rosamerica and track2.genre_rosamerica:
            return f"{quality} genre match ({track1.genre_rosamerica[0]} → {track2.genre_rosamerica[0]})"
        if dim == "artist":
            a1 = track1.artist or "unknown"
            a2 = track2.artist or "unknown"
            if a1 == a2:
                return f"Same artist ({a1})"
            return f"{quality} artist relation ({a1} → {a2})"
        if dim == "era" and track1.mb_release_year and track2.mb_release_year:
            return f"{quality} era match ({track1.mb_release_year} → {track2.mb_release_year})"

    return f"{quality} {label.lower()} compatibility ({score:.0%})"


def _get_top_mood(track: TrackFeatures) -> str:
    """Get the dominant mood for a track."""
    moods = ["happy", "sad", "aggressive", "relaxed", "party", "acoustic"]
    best_mood = "unknown"
    best_prob = -1.0
    for mood_name in moods:
        prob = track.mood_positive_probability(mood_name)
        if prob is not None and prob > best_prob:
            best_prob = prob
            best_mood = mood_name
    return best_mood


def get_top_contributors(
    transition: TransitionResult,
    prefs: UserPreferences,
    n: int = 3,
    track1: TrackFeatures | None = None,
    track2: TrackFeatures | None = None,
) -> list[tuple[str, float, str]]:
    """Get the top-N dimensions that most influenced this transition score.

    Returns list of (dimension_name, raw_score, description) sorted by
    weighted contribution (score * weight), descending.
    """
    scored = []
    for dim in DIMENSION_NAMES:
        score = _get_dimension_score(transition, dim)
        weight = _get_weight(prefs, dim)
        if weight > 0:
            scored.append((dim, score, score * weight))

    scored.sort(key=lambda x: x[2], reverse=True)

    return [
        (dim, score, _dimension_description(dim, score, track1, track2))
        for dim, score, _ in scored[:n]
    ]


def get_bottom_contributors(
    transition: TransitionResult,
    prefs: UserPreferences,
    n: int = 2,
    track1: TrackFeatures | None = None,
    track2: TrackFeatures | None = None,
) -> list[tuple[str, float, str]]:
    """Get the bottom-N dimensions (weakest contributors)."""
    scored = []
    for dim in DIMENSION_NAMES:
        score = _get_dimension_score(transition, dim)
        weight = _get_weight(prefs, dim)
        if weight > 0:
            scored.append((dim, score, score * weight))

    scored.sort(key=lambda x: x[2])

    return [
        (dim, score, _dimension_description(dim, score, track1, track2))
        for dim, score, _ in scored[:n]
    ]


def explain_transition(
    transition: TransitionResult,
    prefs: UserPreferences,
    track1: TrackFeatures,
    track2: TrackFeatures,
) -> TransitionExplanation:
    """Generate a full explanation for a single transition."""
    return TransitionExplanation(
        from_title=track1.title or track1.mbid,
        to_title=track2.title or track2.mbid,
        overall_score=transition.probability,
        top_contributors=get_top_contributors(transition, prefs, 3, track1, track2),
        bottom_contributors=get_bottom_contributors(
            transition, prefs, 2, track1, track2
        ),
        raw_explanation=transition.explanation,
    )


def detect_energy_arc(tracks: list[TrackFeatures]) -> str:
    """Detect the energy arc of a playlist.

    Returns one of: "rising", "falling", "valley", "hill", "steady".
    """
    if len(tracks) < 2:
        return "steady"

    energies = [t.energy_score for t in tracks]
    first_half = energies[: len(energies) // 2]
    second_half = energies[len(energies) // 2 :]

    first_avg = sum(first_half) / len(first_half) if first_half else 0
    second_avg = sum(second_half) / len(second_half) if second_half else 0

    start_e = energies[0]
    end_e = energies[-1]
    mid_e = energies[len(energies) // 2]

    # Check for valley (starts high, dips, comes back)
    if (
        start_e > mid_e
        and end_e > mid_e
        and abs(start_e - end_e) < max(start_e, end_e) * 0.3
    ):
        return "valley"

    # Check for hill (starts low, peaks, comes back)
    if (
        mid_e > start_e
        and mid_e > end_e
        and abs(start_e - end_e) < max(start_e, end_e) * 0.3
    ):
        return "hill"

    # Rising or falling
    if second_avg > first_avg * 1.15:
        return "rising"
    if first_avg > second_avg * 1.15:
        return "falling"

    return "steady"


def detect_genre_journey(tracks: list[TrackFeatures]) -> list[str]:
    """Extract the genre journey as an ordered list of unique genres."""
    genres = []
    for t in tracks:
        genre = t.genre_rosamerica[0] if t.genre_rosamerica else None
        if genre and (not genres or genres[-1] != genre):
            genres.append(genre)
    return genres if genres else ["mixed"]


def generate_playlist_summary(
    tracks: list[TrackFeatures],
    transitions: list[TransitionResult],
) -> str:
    """Generate a one-sentence summary of the playlist's musical journey."""
    if not tracks:
        return "Empty playlist."

    genre_journey = detect_genre_journey(tracks)
    energy_arc = detect_energy_arc(tracks)

    genre_str = " \u2192 ".join(genre_journey[:4])
    if len(genre_journey) > 4:
        genre_str += " \u2192 ..."

    energy_desc = {
        "rising": "building energy",
        "falling": "winding down",
        "valley": "dipping then rising",
        "hill": "peaking in the middle",
        "steady": "maintaining steady energy",
    }.get(energy_arc, "maintaining steady energy")

    if transitions:
        avg_compat = sum(t.probability for t in transitions) / len(transitions)
        quality = f" (avg compatibility: {avg_compat:.0%})"
    else:
        quality = ""

    return (
        f"A journey through {genre_str}, {energy_desc} "
        f"across {len(tracks)} tracks{quality}."
    )


def generate_quality_metrics(
    transitions: list[TransitionResult],
) -> dict[str, float]:
    """Compute quality metrics for a playlist."""
    if not transitions:
        return {
            "avg_compatibility": 0.0,
            "weakest_transition": 0.0,
            "strongest_transition": 0.0,
        }

    probs = [t.probability for t in transitions]
    return {
        "avg_compatibility": sum(probs) / len(probs),
        "weakest_transition": min(probs),
        "strongest_transition": max(probs),
        "num_transitions": float(len(probs)),
    }


def explain_playlist(
    tracks: list[TrackFeatures],
    transitions: list[TransitionResult],
    prefs: UserPreferences,
    constraint_results: list[ConstraintResult] | None = None,
) -> PlaylistExplanation:
    """Generate a complete explanation for a playlist."""
    track_explanations = []

    for i, track in enumerate(tracks):
        if i == 0:
            role = "source"
        elif i == len(tracks) - 1:
            role = "destination"
        else:
            role = "waypoint"

        incoming = None
        outgoing = None

        if i > 0 and i - 1 < len(transitions):
            incoming = explain_transition(
                transitions[i - 1], prefs, tracks[i - 1], track
            )

        if i < len(transitions):
            outgoing = explain_transition(transitions[i], prefs, track, tracks[i + 1])

        track_explanations.append(
            TrackExplanation(
                position=i,
                mbid=track.mbid,
                title=track.title,
                artist=track.artist,
                role=role,
                incoming_transition=incoming,
                outgoing_transition=outgoing,
            )
        )

    constraint_notes = []
    if constraint_results:
        for cr in constraint_results:
            if cr.satisfied:
                constraint_notes.append(f"{cr.name}: satisfied")
            else:
                for v in cr.violations:
                    constraint_notes.append(f"{cr.name}: {v}")

    return PlaylistExplanation(
        summary=generate_playlist_summary(tracks, transitions),
        track_explanations=track_explanations,
        constraint_notes=constraint_notes,
        quality_metrics=generate_quality_metrics(transitions),
    )
