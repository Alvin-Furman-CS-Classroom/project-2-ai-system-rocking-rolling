"""Module 2: Beam Search Path Finding.

This module implements beam search to find optimal paths through music
feature space. Given source and destination tracks, it discovers waypoint
sequences that satisfy transition compatibility rules from the knowledge base.

Inputs:
    - Source/destination MusicBrainz recording IDs
    - Preferred playlist length
    - Knowledge base rules from Module 1

Outputs:
    - Ordered waypoint sequence representing the playlist path

Example:
    from module1 import MusicKnowledgeBase
    from module2 import BeamSearch

    kb = MusicKnowledgeBase()
    search = BeamSearch(knowledge_base=kb, beam_width=10)
    path = search.find_path(source_mbid, dest_mbid, target_length=7)

    if path:
        print(f"Found path with {path.length} tracks")
        print(f"Total cost: {path.total_cost:.3f}")
        print(f"Average compatibility: {path.average_compatibility:.1%}")
"""

from .acousticbrainz_client import AcousticBrainzClient, AcousticBrainzConfig
from .beam_search import BeamSearch
from .data_models import PlaylistPath, SearchState, SimilarRecording
from .listenbrainz_client import ListenBrainzClient, ListenBrainzConfig
from .musicbrainz_client import MusicBrainzClient, MusicBrainzConfig
from .musicbrainz_db import MusicBrainzDB, MusicBrainzDBConfig
from .search_space import SearchSpace, SearchSpaceProtocol

__all__ = [
    # Core algorithm
    "BeamSearch",
    "SearchSpace",
    "SearchSpaceProtocol",
    # Data models
    "PlaylistPath",
    "SearchState",
    "SimilarRecording",
    # API clients
    "ListenBrainzClient",
    "ListenBrainzConfig",
    "AcousticBrainzClient",
    "AcousticBrainzConfig",
    "MusicBrainzClient",
    "MusicBrainzConfig",
    # Postgres-backed client
    "MusicBrainzDB",
    "MusicBrainzDBConfig",
]
