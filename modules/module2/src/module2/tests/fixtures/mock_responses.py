"""Mock API responses for testing.

Based on real API response shapes captured from:
- AcousticBrainz API (acousticbrainz.org/api/v1)
- ListenBrainz API (api.listenbrainz.org/1)
- ListenBrainz Labs API (labs.api.listenbrainz.org)
- MusicBrainz API (musicbrainz.org/ws/2)

Data modeled after Pink Floyd recordings for consistency.
"""

# ---------------------------------------------------------------------------
# ListenBrainz: Similar recordings (labs API)
# POST /similar-recordings/json
# Real format: flat list of similar recordings with integer scores
# ---------------------------------------------------------------------------
SIMILAR_RECORDINGS_RESPONSE = [
    {
        "recording_mbid": "similar-1",
        "recording_name": "Wish You Were Here",
        "artist_credit_name": "Pink Floyd",
        "score": 22,
        "reference_mbid": "source-mbid-123",
    },
    {
        "recording_mbid": "similar-2",
        "recording_name": "Comfortably Numb",
        "artist_credit_name": "Pink Floyd",
        "score": 19,
        "reference_mbid": "source-mbid-123",
    },
    {
        "recording_mbid": "similar-3",
        "recording_name": "Shine On You Crazy Diamond",
        "artist_credit_name": "Pink Floyd",
        "score": 17,
        "reference_mbid": "source-mbid-123",
    },
    {
        "recording_mbid": "similar-4",
        "recording_name": "Time",
        "artist_credit_name": "Pink Floyd",
        "score": 15,
        "reference_mbid": "source-mbid-123",
    },
    {
        "recording_mbid": "similar-5",
        "recording_name": "Money",
        "artist_credit_name": "Pink Floyd",
        "score": 12,
        "reference_mbid": "source-mbid-123",
    },
]

# ---------------------------------------------------------------------------
# AcousticBrainz: Low-level features (bulk)
# GET /low-level?recording_ids=mbid1;mbid2
# Real format: {mbid: {"0": {metadata, rhythm, tonal, lowlevel}}}
# Captured from real AB API for Pink Floyd "The Lost Art of Conversation"
# ---------------------------------------------------------------------------
LOWLEVEL_RESPONSE = {
    "similar-1": {
        "0": {
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-1"],
                    "title": ["Wish You Were Here"],
                    "artist": ["Pink Floyd"],
                    "album": ["Wish You Were Here"],
                }
            },
            "rhythm": {
                "bpm": 120.0,
                "onset_rate": 4.5,
                "beats_count": 240,
                "danceability": 0.75,
            },
            "tonal": {
                "key_key": "C",
                "key_scale": "major",
                "key_strength": 0.85,
                "tuning_frequency": 440.0,
            },
            "lowlevel": {
                "spectral_energyband_low": {"mean": 0.1},
                "spectral_energyband_middle_low": {"mean": 0.2},
                "spectral_energyband_middle_high": {"mean": 0.3},
                "spectral_energyband_high": {"mean": 0.15},
                "average_loudness": 0.128771,  # Real value from AB
                "dynamic_complexity": 0.5,
                "mfcc": {
                    "mean": [0.0] * 13,
                    "cov": [
                        [1.0 if i == j else 0.0 for j in range(13)] for i in range(13)
                    ],
                },
                "spectral_centroid": {"mean": 1500.0},
                "dissonance": {"mean": 0.3},
            },
        }
    },
    "similar-2": {
        "0": {
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-2"],
                    "title": ["Comfortably Numb"],
                    "artist": ["Pink Floyd"],
                    "album": ["The Wall"],
                }
            },
            "rhythm": {
                "bpm": 125.0,
                "onset_rate": 4.8,
                "beats_count": 250,
                "danceability": 0.80,
            },
            "tonal": {
                "key_key": "G",
                "key_scale": "major",
                "key_strength": 0.82,
                "tuning_frequency": 440.0,
            },
            "lowlevel": {
                "spectral_energyband_low": {"mean": 0.12},
                "spectral_energyband_middle_low": {"mean": 0.22},
                "spectral_energyband_middle_high": {"mean": 0.32},
                "spectral_energyband_high": {"mean": 0.18},
                "average_loudness": 0.82,
                "dynamic_complexity": 0.55,
                "mfcc": {
                    "mean": [0.1] * 13,
                    "cov": [
                        [1.0 if i == j else 0.0 for j in range(13)] for i in range(13)
                    ],
                },
                "spectral_centroid": {"mean": 1600.0},
                "dissonance": {"mean": 0.32},
            },
        }
    },
}

# ---------------------------------------------------------------------------
# AcousticBrainz: High-level features (bulk)
# GET /high-level?recording_ids=mbid1;mbid2
# Real format: {mbid: {"0": {highlevel: {...}, metadata: {...}}}}
# ---------------------------------------------------------------------------
HIGHLEVEL_RESPONSE = {
    "similar-1": {
        "0": {
            "highlevel": {
                "danceability": {"value": "danceable", "probability": 0.85},
                "mood_happy": {"value": "happy", "probability": 0.75},
                "mood_sad": {"value": "not_sad", "probability": 0.80},
                "mood_aggressive": {"value": "not_aggressive", "probability": 0.90},
                "mood_relaxed": {"value": "not_relaxed", "probability": 0.60},
                "mood_party": {"value": "party", "probability": 0.70},
                "mood_acoustic": {"value": "not_acoustic", "probability": 0.85},
                "timbre": {"value": "bright", "probability": 0.72},
                "genre_rosamerica": {
                    "value": "roc",
                    "probability": 0.65,
                    "all": {
                        "pop": 0.10,
                        "roc": 0.65,
                        "cla": 0.05,
                        "jaz": 0.05,
                        "dan": 0.05,
                        "hip": 0.02,
                        "rhy": 0.02,
                        "spe": 0.06,
                    },
                },
            },
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-1"],
                    "title": ["Wish You Were Here"],
                    "artist": ["Pink Floyd"],
                }
            },
        }
    },
    "similar-2": {
        "0": {
            "highlevel": {
                "danceability": {"value": "danceable", "probability": 0.88},
                "mood_happy": {"value": "happy", "probability": 0.72},
                "mood_sad": {"value": "not_sad", "probability": 0.78},
                "mood_aggressive": {"value": "not_aggressive", "probability": 0.88},
                "mood_relaxed": {"value": "not_relaxed", "probability": 0.62},
                "mood_party": {"value": "party", "probability": 0.68},
                "mood_acoustic": {"value": "not_acoustic", "probability": 0.82},
                "timbre": {"value": "bright", "probability": 0.70},
                "genre_rosamerica": {
                    "value": "roc",
                    "probability": 0.60,
                    "all": {
                        "pop": 0.10,
                        "roc": 0.60,
                        "cla": 0.05,
                        "jaz": 0.05,
                        "dan": 0.10,
                        "hip": 0.02,
                        "rhy": 0.02,
                        "spe": 0.06,
                    },
                },
            },
            "metadata": {
                "tags": {
                    "musicbrainz_recordingid": ["similar-2"],
                    "title": ["Comfortably Numb"],
                    "artist": ["Pink Floyd"],
                }
            },
        }
    },
}

# ---------------------------------------------------------------------------
# ListenBrainz: Recording metadata with tags
# GET /1/metadata/recording/?recording_mbids=mbid1,mbid2&inc=tag
# Real format captured from LB API — dict keyed by MBID
# ---------------------------------------------------------------------------
LISTENBRAINZ_TAGS_RESPONSE = {
    "similar-1": {
        "recording": {
            "first_release_date": "1975-09-12",
            "length": 334000,
            "name": "Wish You Were Here",
            "rels": [
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "artist_name": "Pink Floyd",
                    "type": "performer",
                },
            ],
        },
        "tag": {
            "recording": [
                {"tag": "progressive rock", "count": 25},
                {"tag": "classic rock", "count": 18},
                {"tag": "rock", "count": 15},
            ],
            "artist": [
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "count": 55,
                    "tag": "progressive rock",
                },
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "count": 44,
                    "tag": "psychedelic rock",
                },
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "count": 30,
                    "tag": "rock",
                },
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "count": 5,
                    "tag": "classic rock",
                },
            ],
        },
    },
    "similar-2": {
        "recording": {
            "first_release_date": "1979-11-30",
            "length": 383000,
            "name": "Comfortably Numb",
        },
        "tag": {
            "recording": [
                {"tag": "progressive rock", "count": 20},
                {"tag": "rock", "count": 12},
            ],
            "artist": [
                {
                    "artist_mbid": "83d91898-7763-47d7-b03b-b92132375c47",
                    "count": 55,
                    "tag": "progressive rock",
                },
            ],
        },
    },
}

# ---------------------------------------------------------------------------
# ListenBrainz: Recording popularity
# POST /1/popularity/recording
# Body: [{"recording_mbid": "mbid1"}, ...]
# ---------------------------------------------------------------------------
LISTENBRAINZ_POPULARITY_RESPONSE = [
    {
        "recording_mbid": "similar-1",
        "total_listen_count": 150000,
        "total_user_count": 25000,
    },
    {
        "recording_mbid": "similar-2",
        "total_listen_count": 200000,
        "total_user_count": 35000,
    },
]

# ---------------------------------------------------------------------------
# MusicBrainz: Recording metadata
# GET /ws/2/recording/{mbid}?inc=releases+genres+artists&fmt=json
# Real format captured from MB API for Pink Floyd
# ---------------------------------------------------------------------------
MUSICBRAINZ_RECORDING_RESPONSE = {
    "id": "similar-1",
    "title": "Wish You Were Here",
    "artist-credit": [
        {
            "artist": {
                "id": "83d91898-7763-47d7-b03b-b92132375c47",
                "name": "Pink Floyd",
                "type": "Group",
                "sort-name": "Pink Floyd",
                "genres": [
                    {"name": "progressive rock", "id": "ae9b8279-...", "count": 55},
                    {"name": "psychedelic rock", "id": "146ef761-...", "count": 44},
                    {"name": "rock", "id": "0e3fc579-...", "count": 30},
                    {"name": "art rock", "id": "b7ef058e-...", "count": 21},
                    {"name": "space rock", "id": "532dcf83-...", "count": 15},
                ],
            },
            "name": "Pink Floyd",
            "joinphrase": "",
        }
    ],
    "releases": [
        {"date": "1975-09-12", "title": "Wish You Were Here"},
        {"date": "1997-06-10", "title": "Wish You Were Here (Remaster)"},
        {"date": "2011-11-07", "title": "Wish You Were Here (Experience Edition)"},
    ],
    "genres": [
        {"name": "art rock", "count": 3},
        {"name": "progressive rock", "count": 8},
        {"name": "rock", "count": 5},
    ],
}

# ---------------------------------------------------------------------------
# MusicBrainz: Artist relationships
# GET /ws/2/artist/{mbid}?inc=artist-rels&fmt=json
# Real format captured from MB API — Pink Floyd has 110 artist relations
# ---------------------------------------------------------------------------
MUSICBRAINZ_ARTIST_RELS_RESPONSE = {
    "id": "83d91898-7763-47d7-b03b-b92132375c47",
    "name": "Pink Floyd",
    "type": "Group",
    "relations": [
        # Real relation types from MB: instrumental supporting musician, member of band, etc.
        {
            "target-type": "artist",
            "type": "instrumental supporting musician",
            "artist": {
                "id": "e3593976-7ab7-4961-96e9-55b171412db5",
                "name": "Snowy White",
            },
        },
        {
            "target-type": "artist",
            "type": "member of band",
            "artist": {
                "id": "1dce970e-34bc-48b2-ab51-48d87544a4c2",
                "name": "David Gilmour",
            },
        },
        {
            "target-type": "artist",
            "type": "member of band",
            "artist": {
                "id": "6f7e36da-79d8-4219-990d-8e9224d04ebc",
                "name": "Richard Wright",
            },
        },
        {
            "target-type": "artist",
            "type": "member of band",
            "artist": {
                "id": "d700b3f5-45af-4d02-95ed-57d301bda93e",
                "name": "Roger Waters",
            },
        },
        {
            "target-type": "artist",
            "type": "collaboration",
            "artist": {
                "id": "c6e89016-d3cb-4272-9945-de0ec123645e",
                "name": "Guy Pratt",
            },
        },
        # Non-artist relation (should be filtered out by client)
        {
            "target-type": "url",
            "type": "official homepage",
            "url": {"resource": "https://www.pinkfloyd.com"},
        },
    ],
}
