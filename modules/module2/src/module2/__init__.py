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
    from modules.module2 import BeamSearch

    search = BeamSearch(knowledge_base=kb, beam_width=10)
    path = search.find_path(source_id, dest_id, length=8)
"""

__all__: list[str] = []
