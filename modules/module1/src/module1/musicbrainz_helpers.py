"""Helper functions for MusicBrainz-derived compatibility scoring.

These functions compute compatibility probabilities from editorial metadata
provided by the MusicBrainz API. They complement the acoustic functions in
rules_helpers.py and the user-behavioral functions in listenbrainz_helpers.py.

Separation rationale:
    rules_helpers.py          — AcousticBrainz features (content-based)
    listenbrainz_helpers.py   — ListenBrainz signals (user-behavioral)
    musicbrainz_helpers.py    — MusicBrainz metadata (editorial/structural)

Research grounding:
    - Artist relationships: Korzeniowski et al. (ISMIR 2021) showed graph
      topology alone (artist-artist connections) outperforms content features
      for artist similarity (NDCG@200 = 0.45 vs 0.24).
    - Era proximity: Schweiger et al. (EPJ Data Science 2025) showed temporal
      proximity is a key factor in playlist coherence.
    - Editorial genres: Serra & Alonso (ISMIR 2022) showed editorial metadata
      from Discogs outperforms user-generated tags for music representation.
"""

import math


def artist_compatibility_prob(
    artist1_mbid: str | None,
    artist2_mbid: str | None,
    related1: set[str] | None = None,
    related2: set[str] | None = None,
) -> float:
    """
    Compute artist compatibility from MusicBrainz artist relationships.

    Korzeniowski et al. (ISMIR 2021) demonstrated that graph topology
    (artist-artist connections like band membership, collaboration,
    producer credits) is a stronger signal for artist similarity than
    content-based audio features. Most similar artists are within
    2 steps in the relationship graph (~71% of cases).

    Scoring tiers:
        - Same artist:              0.95
        - Related (1-hop):          0.70 (member-of, collaboration, producer)
        - No known relationship:    0.50 (neutral)

    Args:
        artist1_mbid: First track's artist MusicBrainz ID
        artist2_mbid: Second track's artist MusicBrainz ID
        related1: Set of artist MBIDs related to artist1
        related2: Set of artist MBIDs related to artist2

    Returns:
        Compatibility in [0, 1]. Returns 0.5 (neutral) if either
        artist MBID is missing.
    """
    if artist1_mbid is None or artist2_mbid is None:
        return 0.5

    # Same artist — very high compatibility
    if artist1_mbid == artist2_mbid:
        return 0.95

    # Check 1-hop relationships (member-of, collaboration, producer)
    if related1 and artist2_mbid in related1:
        return 0.70
    if related2 and artist1_mbid in related2:
        return 0.70

    # No known relationship — neutral
    return 0.50


def era_compatibility_prob(
    year1: int | None,
    year2: int | None,
    sigma: float = 5.0,
) -> float:
    """
    Compute era compatibility using Gaussian decay on release year difference.

    Schweiger et al. (EPJ Data Science 2025) demonstrated that temporal
    proximity is a key factor in playlist coherence. Tracks from the same
    era tend to share production aesthetics, cultural context, and sonic
    characteristics that make transitions feel natural.

    sigma = 5.0 years means:
        - Same year:        100% compatible
        - 3 years apart:     83% compatible
        - 5 years apart:     61% compatible
        - 10 years apart:    14% compatible
        - 20 years apart:    <1% compatible

    Args:
        year1: First track's release year from MusicBrainz
        year2: Second track's release year from MusicBrainz
        sigma: Standard deviation in years (default 5.0)

    Returns:
        Compatibility in [0, 1]. Returns 0.5 (neutral) if either
        release year is missing.
    """
    if year1 is None or year2 is None:
        return 0.5

    diff = abs(year1 - year2)
    return math.exp(-(diff**2) / (2.0 * sigma**2))


def mb_genre_compatibility_prob(
    genres1: list[str] | None,
    genres2: list[str] | None,
) -> float:
    """
    Compute genre compatibility using Jaccard similarity on MusicBrainz genre sets.

    MusicBrainz provides a curated editorial genre taxonomy that is richer
    and more consistent than AcousticBrainz's 8-class rosamerica classifier.
    Serra & Alonso (ISMIR 2022) showed editorial metadata outperforms
    user-generated tags for music representation learning.

    This dimension defaults to weight=0.0 because ListenBrainz user-generated
    tags already carry a strong genre signal. Enable it when you want to
    supplement with editorial curation.

    Jaccard similarity = |intersection| / |union|, naturally in [0, 1].

    Args:
        genres1: First track's genre tags from MusicBrainz
        genres2: Second track's genre tags from MusicBrainz

    Returns:
        Compatibility in [0, 1]. Returns 0.5 (neutral) if either
        track has no genre data.
    """
    if genres1 is None or genres2 is None:
        return 0.5
    if not genres1 or not genres2:
        return 0.5

    # Case-insensitive comparison
    set1 = {g.lower() for g in genres1}
    set2 = {g.lower() for g in genres2}

    intersection = set1 & set2
    union = set1 | set2

    if not union:
        return 0.5

    return len(intersection) / len(union)
