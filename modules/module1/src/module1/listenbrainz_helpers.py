"""Helper functions for ListenBrainz-derived compatibility scoring.

These functions compute compatibility probabilities from user-behavioral data
(tags, popularity) provided by the ListenBrainz API. They complement the
acoustic compatibility functions in rules_helpers.py.

Separation rationale:
    rules_helpers.py    — AcousticBrainz features (content-based, popularity-blind)
    listenbrainz_helpers.py — ListenBrainz signals (user-behavioral, context-aware)
"""

import math


def tag_compatibility_prob(
    tags1: dict[str, int] | None,
    tags2: dict[str, int] | None,
) -> float:
    """
    Compute tag compatibility as cosine similarity of tag count vectors.

    ListenBrainz metadata provides user-generated tags with occurrence counts,
    e.g. {"shoegaze": 45, "dreampop": 32, "ambient": 18}. This is far richer
    than AcousticBrainz's 8-class rosamerica genre classifier.

    Cosine similarity ranges [0, 1] for non-negative count vectors, mapping
    directly to a probability interpretation.

    Args:
        tags1: First track's tag counts from /1/metadata/recording/?inc=tag
        tags2: Second track's tag counts

    Returns:
        Compatibility in [0, 1]. Returns 0.5 (neutral) if either track
        has no tag data.
    """
    if tags1 is None or tags2 is None:
        return 0.5
    if not tags1 or not tags2:
        return 0.5

    # Build vectors over the union of tag keys
    all_tags = set(tags1.keys()) | set(tags2.keys())
    dot = 0.0
    norm1_sq = 0.0
    norm2_sq = 0.0

    for tag in all_tags:
        v1 = tags1.get(tag, 0)
        v2 = tags2.get(tag, 0)
        dot += v1 * v2
        norm1_sq += v1 * v1
        norm2_sq += v2 * v2

    norm1 = math.sqrt(norm1_sq)
    norm2 = math.sqrt(norm2_sq)

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.5

    return dot / (norm1 * norm2)


def popularity_compatibility_prob(
    pop1: int | None,
    pop2: int | None,
) -> float:
    """
    Compute popularity compatibility using Gaussian decay on log-scale difference.

    Tracks with similar popularity levels tend to flow better in playlists.
    Using log-scale because popularity follows a power law distribution —
    the difference between 100 and 200 listens matters more than between
    100,000 and 100,100.

    sigma = 2.0 on log-scale means:
        - Same order of magnitude: ~100% compatible
        - 10x difference (e.g., 1K vs 10K): ~52% compatible
        - 100x difference (e.g., 100 vs 10K): ~7% compatible
        - 1000x difference (e.g., 50 vs 50K): <1% compatible

    Note: This dimension defaults to weight=0.0 (off). It's available for
    users who want popularity-aware playlists, but the system is
    discovery-friendly by default.

    Args:
        pop1: First track's total listen count from ListenBrainz
        pop2: Second track's total listen count

    Returns:
        Compatibility in [0, 1]. Returns 0.5 (neutral) if either track
        has no popularity data.
    """
    if pop1 is None or pop2 is None:
        return 0.5
    if pop1 <= 0 or pop2 <= 0:
        return 0.5

    log_diff = abs(math.log(pop1 + 1) - math.log(pop2 + 1))
    sigma = 2.0
    return math.exp(-(log_diff**2) / (2.0 * sigma**2))
