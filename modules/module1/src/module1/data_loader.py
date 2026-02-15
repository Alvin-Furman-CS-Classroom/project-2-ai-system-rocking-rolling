"""Data loader for AcousticBrainz JSON files."""

import json
from pathlib import Path

from .data_models import TrackFeatures


def _get_nested(data: dict, *keys, default=None):
    """Safely get nested dictionary values."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _get_mean(data: dict, *keys, default: float = 0.0) -> float:
    """Get the mean value from a nested statistical aggregation."""
    value = _get_nested(data, *keys)
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get("mean", default)
    return float(value)


def _get_classifier(data: dict, *keys) -> tuple[str, float] | None:
    """Get a highlevel classifier as (value, probability) tuple."""
    classifier = _get_nested(data, *keys)
    if classifier is None:
        return None
    value = classifier.get("value")
    prob = classifier.get("probability")
    if value is None or prob is None:
        return None
    return (value, prob)


def _get_classifier_all(data: dict, *keys) -> dict[str, float] | None:
    """Get the full probability distribution from a highlevel classifier's 'all' field."""
    classifier = _get_nested(data, *keys)
    if classifier is None:
        return None
    all_field = classifier.get("all")
    if all_field is None or not isinstance(all_field, dict):
        return None
    return {k: float(v) for k, v in all_field.items()}


def _get_first_tag(data: dict, tag_name: str) -> str | None:
    """Get the first value of a tag list, or None."""
    tags = _get_nested(data, "metadata", "tags", tag_name)
    if tags and isinstance(tags, list) and len(tags) > 0:
        return tags[0]
    return None


def load_track_from_files(
    lowlevel_path: str | Path,
    highlevel_path: str | Path,
) -> TrackFeatures:
    """
    Load a track from AcousticBrainz lowlevel and highlevel JSON files.

    Args:
        lowlevel_path: Path to the lowlevel JSON file
        highlevel_path: Path to the highlevel JSON file

    Returns:
        TrackFeatures dataclass with extracted features

    Raises:
        FileNotFoundError: If either file doesn't exist
        json.JSONDecodeError: If either file is not valid JSON
        ValueError: If required fields are missing
    """
    lowlevel_path = Path(lowlevel_path)
    highlevel_path = Path(highlevel_path)

    with open(lowlevel_path) as f:
        lowlevel = json.load(f)

    with open(highlevel_path) as f:
        highlevel = json.load(f)

    return load_track_from_data(lowlevel, highlevel)


def load_track_from_data(
    lowlevel: dict,
    highlevel: dict,
) -> TrackFeatures:
    """
    Load a track from already-parsed AcousticBrainz data dictionaries.

    Args:
        lowlevel: Parsed lowlevel JSON data
        highlevel: Parsed highlevel JSON data

    Returns:
        TrackFeatures dataclass with extracted features
    """
    # Get metadata: prefer highlevel, fallback to lowlevel
    mbid = _get_first_tag(highlevel, "musicbrainz_recordingid") or _get_first_tag(lowlevel, "musicbrainz_recordingid") or "unknown"
    title = _get_first_tag(highlevel, "title") or _get_first_tag(lowlevel, "title")
    artist = _get_first_tag(highlevel, "artist") or _get_first_tag(lowlevel, "artist")
    album = _get_first_tag(highlevel, "album") or _get_first_tag(lowlevel, "album")

    # Rhythm features from lowlevel
    bpm = _get_nested(lowlevel, "rhythm", "bpm") or 0.0
    onset_rate = _get_nested(lowlevel, "rhythm", "onset_rate") or 0.0
    beats_count = _get_nested(lowlevel, "rhythm", "beats_count") or 0

    # Danceability: PREFER highlevel if available
    hl_danceability = _get_classifier(highlevel, "highlevel", "danceability")
    ll_danceability = _get_nested(lowlevel, "rhythm", "danceability")
    danceability: float | tuple[str, float] | None
    if hl_danceability is not None:
        danceability = hl_danceability
    elif ll_danceability is not None:
        danceability = float(ll_danceability)
    else:
        danceability = None

    # Tonal features from lowlevel
    key = _get_nested(lowlevel, "tonal", "key_key") or "C"
    scale = _get_nested(lowlevel, "tonal", "key_scale") or "major"
    key_strength = _get_nested(lowlevel, "tonal", "key_strength") or 0.0
    tuning_frequency = _get_nested(lowlevel, "tonal", "tuning_frequency") or 440.0
    chords_strength = _get_mean(lowlevel, "tonal", "chords_strength")

    # Energy bands from lowlevel.lowlevel
    energy_low = _get_mean(lowlevel, "lowlevel", "spectral_energyband_low")
    energy_mid_low = _get_mean(lowlevel, "lowlevel", "spectral_energyband_middle_low")
    energy_mid_high = _get_mean(lowlevel, "lowlevel", "spectral_energyband_middle_high")
    energy_high = _get_mean(lowlevel, "lowlevel", "spectral_energyband_high")

    # Loudness and dynamics from lowlevel.lowlevel
    average_loudness = _get_nested(lowlevel, "lowlevel", "average_loudness")
    dynamic_complexity = _get_nested(lowlevel, "lowlevel", "dynamic_complexity")

    # Spectral features from lowlevel.lowlevel
    mfcc_data = _get_nested(lowlevel, "lowlevel", "mfcc")
    mfcc: list[float] | None = None
    mfcc_cov: list[list[float]] | None = None
    if mfcc_data and isinstance(mfcc_data, dict):
        mfcc_mean = mfcc_data.get("mean")
        if mfcc_mean and isinstance(mfcc_mean, list):
            mfcc = [float(x) for x in mfcc_mean]
        mfcc_cov_raw = mfcc_data.get("cov")
        if mfcc_cov_raw and isinstance(mfcc_cov_raw, list):
            mfcc_cov = [[float(x) for x in row] for row in mfcc_cov_raw]

    spectral_centroid = _get_mean(lowlevel, "lowlevel", "spectral_centroid")
    dissonance = _get_mean(lowlevel, "lowlevel", "dissonance")

    # Highlevel mood descriptors
    mood_happy = _get_classifier(highlevel, "highlevel", "mood_happy")
    mood_sad = _get_classifier(highlevel, "highlevel", "mood_sad")
    mood_aggressive = _get_classifier(highlevel, "highlevel", "mood_aggressive")
    mood_relaxed = _get_classifier(highlevel, "highlevel", "mood_relaxed")
    mood_party = _get_classifier(highlevel, "highlevel", "mood_party")
    mood_acoustic = _get_classifier(highlevel, "highlevel", "mood_acoustic")
    timbre = _get_classifier(highlevel, "highlevel", "timbre")
    genre_rosamerica = _get_classifier(highlevel, "highlevel", "genre_rosamerica")
    genre_rosamerica_all = _get_classifier_all(highlevel, "highlevel", "genre_rosamerica")

    return TrackFeatures(
        mbid=mbid,
        title=title,
        artist=artist,
        album=album,
        bpm=bpm,
        onset_rate=onset_rate,
        beats_count=beats_count,
        danceability=danceability,
        key=key,
        scale=scale,
        key_strength=key_strength,
        tuning_frequency=tuning_frequency,
        chords_strength=chords_strength,
        energy_low=energy_low,
        energy_mid_low=energy_mid_low,
        energy_mid_high=energy_mid_high,
        energy_high=energy_high,
        average_loudness=average_loudness,
        dynamic_complexity=dynamic_complexity,
        mfcc=mfcc,
        mfcc_cov=mfcc_cov,
        spectral_centroid=spectral_centroid,
        dissonance=dissonance,
        mood_happy=mood_happy,
        mood_sad=mood_sad,
        mood_aggressive=mood_aggressive,
        mood_relaxed=mood_relaxed,
        mood_party=mood_party,
        mood_acoustic=mood_acoustic,
        timbre=timbre,
        genre_rosamerica=genre_rosamerica,
        genre_rosamerica_all=genre_rosamerica_all,
    )


def load_track_from_lowlevel(lowlevel_path: str | Path) -> TrackFeatures:
    """
    Load a track from only a lowlevel JSON file (no highlevel data).

    High-level classifiers (mood, timbre, danceability) will be None.

    Args:
        lowlevel_path: Path to the lowlevel JSON file

    Returns:
        TrackFeatures dataclass with low-level features only
    """
    lowlevel_path = Path(lowlevel_path)
    with open(lowlevel_path) as f:
        lowlevel = json.load(f)

    return load_track_from_data(lowlevel, highlevel={})


def load_tracks_batch(
    file_pairs: list[tuple[str | Path, str | Path]],
) -> list[TrackFeatures]:
    """
    Load multiple tracks from file pairs.

    Args:
        file_pairs: List of (lowlevel_path, highlevel_path) tuples

    Returns:
        List of TrackFeatures
    """
    return [load_track_from_files(ll, hl) for ll, hl in file_pairs]
