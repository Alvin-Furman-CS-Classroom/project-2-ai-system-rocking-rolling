"""Module 5: Playlist Orchestration and System Integration for Wave Guide.

This module is the top-level integration layer that ties together all prior modules:
- Module 1: Music Feature Knowledge Base (constraint validation)
- Module 2: Beam Search (path finding)
- Module 3: Playlist Assembly (constraints, SA optimization, explanations)
- Module 4: Mood Classification (mood-to-feature mapping)

The key addition over prior modules is support for mood-based playlist input:
users can specify a mood label (Calm, Energized, etc.) as their source or destination
instead of a specific track MBID.

Example:
    from module5 import PlaylistOrchestrator, PlaylistRequest, TrackInput

    orchestrator = PlaylistOrchestrator(knowledge_base=kb, classifier=clf)

    # Mood source → real destination
    request = PlaylistRequest(
        source=TrackInput(type="mood", mood="calm"),
        destination=TrackInput(type="mbid", mbid="<mbid>"),
        length=7,
    )
    playlist = orchestrator.generate(request)
"""

from .orchestrator import PlaylistOrchestrator, PlaylistRequest, TrackInput

__all__ = [
    "PlaylistOrchestrator",
    "PlaylistRequest",
    "TrackInput",
]
