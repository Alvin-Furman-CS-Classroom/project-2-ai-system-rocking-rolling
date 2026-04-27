"""MusicBrainz Postgres client — direct database queries, no rate limits.

Drop-in replacement for MusicBrainzClient. Same interface, same return types,
but queries a local MusicBrainz mirror via psycopg + connection pool instead
of the REST API.

Connection configurable via MusicBrainzDBConfig or MB_DB_* environment variables.
Requires ~/.pgpass for passwordless auth.

Usage:
    # Uses env vars / defaults
    db = MusicBrainzDB()
    meta = db.get_recording_metadata("1eac49da-3399-4d34-bbf3-a98a91e2758b")

    # Custom config
    db = MusicBrainzDB(MusicBrainzDBConfig(host="10.0.0.5", schema="canonical"))

    # Context manager (auto-closes pool)
    with MusicBrainzDB() as db:
        meta = db.get_recording_metadata(mbid)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from psycopg_pool import ConnectionPool

from .musicbrainz_client import RecordingMetadata

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class MusicBrainzDBConfig:
    """Configuration for direct Postgres connection.

    All fields can be overridden via environment variables (MB_DB_*) or
    passed directly. Password is read from ~/.pgpass — never stored here.
    """

    host: str = ""
    port: int = 0
    dbname: str = ""
    user: str = ""
    schema: str = ""

    # Connection pool sizing
    pool_min: int = 1
    pool_max: int = 5

    def __post_init__(self):
        self.host = self.host or os.environ.get("MB_DB_HOST", "localhost")
        self.port = self.port or int(os.environ.get("MB_DB_PORT", "5432"))
        self.dbname = self.dbname or os.environ.get("MB_DB_NAME", "musicbrainz")
        self.user = self.user or os.environ.get("MB_DB_USER", "musicbrainz")
        self.schema = self.schema or os.environ.get("MB_DB_SCHEMA", "musicbrainz")

    @property
    def conninfo(self) -> str:
        """Build psycopg connection string (password via ~/.pgpass)."""
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} user={self.user}"
        )


# =============================================================================
# SQL Queries — parameterized, schema-prefixed
# =============================================================================


def _q(schema: str) -> dict[str, str]:
    """Build all SQL queries with the configured schema prefix."""
    s = schema

    return {
        "recording_single": f"""\
            SELECT
                a.gid::text    AS artist_mbid,
                rfrd.year      AS release_year,
                array_agg(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL) AS genres
            FROM {s}.recording r
            JOIN {s}.artist_credit_name acn ON r.artist_credit = acn.artist_credit
            JOIN {s}.artist a ON acn.artist = a.id
            LEFT JOIN {s}.recording_first_release_date rfrd ON r.id = rfrd.recording
            LEFT JOIN {s}.recording_tag rt ON r.id = rt.recording
            LEFT JOIN {s}.genre g ON rt.tag = g.id
            WHERE r.gid = %s
            GROUP BY a.gid, rfrd.year
            LIMIT 1
        """,
        "recording_batch": f"""\
            SELECT
                r.gid::text    AS recording_mbid,
                a.gid::text    AS artist_mbid,
                rfrd.year      AS release_year,
                array_agg(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL) AS genres
            FROM {s}.recording r
            JOIN {s}.artist_credit_name acn ON r.artist_credit = acn.artist_credit
            JOIN {s}.artist a ON acn.artist = a.id
            LEFT JOIN {s}.recording_first_release_date rfrd ON r.id = rfrd.recording
            LEFT JOIN {s}.recording_tag rt ON r.id = rt.recording
            LEFT JOIN {s}.genre g ON rt.tag = g.id
            WHERE r.gid = ANY(%s)
            GROUP BY r.gid, a.gid, rfrd.year
        """,
        "artist_rels": f"""\
            SELECT a2.gid::text
            FROM {s}.l_artist_artist laa
            JOIN {s}.artist a1 ON laa.entity0 = a1.id
            JOIN {s}.artist a2 ON laa.entity1 = a2.id
            WHERE a1.gid = %s
            UNION
            SELECT a1.gid::text
            FROM {s}.l_artist_artist laa
            JOIN {s}.artist a1 ON laa.entity0 = a1.id
            JOIN {s}.artist a2 ON laa.entity1 = a2.id
            WHERE a2.gid = %s
        """,
    }


# =============================================================================
# Client
# =============================================================================

_BATCH_CHUNK_SIZE = 100  # max MBIDs per batch query


class MusicBrainzDB:
    """Postgres-backed MusicBrainz client.

    Drop-in replacement for MusicBrainzClient — same methods, same return
    types, but queries the local mirror directly via a connection pool.
    No rate limiting needed.
    """

    def __init__(self, config: MusicBrainzDBConfig | None = None):
        self.config = config or MusicBrainzDBConfig()
        self._sql = _q(self.config.schema)
        self._pool = ConnectionPool(
            conninfo=self.config.conninfo,
            min_size=self.config.pool_min,
            max_size=self.config.pool_max,
            open=True,
        )

        # Same caches as MusicBrainzClient
        self._artist_rels_cache: dict[str, set[str]] = {}
        self._recording_cache: dict[str, RecordingMetadata] = {}

    # -------------------------------------------------------------------------
    # Recording metadata
    # -------------------------------------------------------------------------

    def get_recording_metadata(self, mbid: str) -> RecordingMetadata:
        """Fetch recording metadata from local Postgres mirror."""
        if mbid in self._recording_cache:
            return self._recording_cache[mbid]

        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(self._sql["recording_single"], (mbid,))
                    row = cur.fetchone()
        except Exception:
            logger.warning("MusicBrainzDB recording lookup failed for %s", mbid)
            return RecordingMetadata()

        if row is None:
            meta = RecordingMetadata()
        else:
            artist_mbid, release_year, genres = row
            meta = RecordingMetadata(
                artist_mbid=artist_mbid,
                release_year=release_year,
                genre_tags=genres or [],
            )

        self._recording_cache[mbid] = meta
        return meta

    def get_recording_metadata_batch(
        self,
        mbids: list[str],
    ) -> dict[str, RecordingMetadata]:
        """Fetch recording metadata for multiple MBIDs in one query.

        Replaces the Lucene-based batch search from MusicBrainzClient.
        Chunks large lists to avoid oversized queries.
        """
        results: dict[str, RecordingMetadata] = {}
        if not mbids:
            return results

        # Check cache first
        uncached: list[str] = []
        for mbid in mbids:
            if mbid in self._recording_cache:
                results[mbid] = self._recording_cache[mbid]
            else:
                uncached.append(mbid)

        if not uncached:
            return results

        # Query in chunks
        for i in range(0, len(uncached), _BATCH_CHUNK_SIZE):
            chunk = uncached[i : i + _BATCH_CHUNK_SIZE]
            try:
                with self._pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(self._sql["recording_batch"], (chunk,))
                        for row in cur.fetchall():
                            rec_mbid, artist_mbid, release_year, genres = row
                            meta = RecordingMetadata(
                                artist_mbid=artist_mbid,
                                release_year=release_year,
                                genre_tags=genres or [],
                            )
                            self._recording_cache[rec_mbid] = meta
                            results[rec_mbid] = meta
            except Exception:
                logger.warning(
                    "MusicBrainzDB batch lookup failed for %d MBIDs",
                    len(chunk),
                )

        # Cache empty metadata for MBIDs not found
        for mbid in uncached:
            if mbid not in results:
                meta = RecordingMetadata()
                self._recording_cache[mbid] = meta
                results[mbid] = meta

        return results

    # -------------------------------------------------------------------------
    # Artist relationships
    # -------------------------------------------------------------------------

    def get_artist_relationships(self, artist_mbid: str) -> set[str]:
        """Fetch related artist MBIDs from local Postgres mirror.

        Queries both directions of l_artist_artist (entity0→entity1 and
        entity1→entity0) to get the full relationship graph.
        """
        if artist_mbid in self._artist_rels_cache:
            return self._artist_rels_cache[artist_mbid]

        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        self._sql["artist_rels"],
                        (artist_mbid, artist_mbid),
                    )
                    related = {row[0] for row in cur.fetchall()}
        except Exception:
            logger.warning("MusicBrainzDB artist lookup failed for %s", artist_mbid)
            return set()

        self._artist_rels_cache[artist_mbid] = related
        return related

    # -------------------------------------------------------------------------
    # Cache management
    # -------------------------------------------------------------------------

    def cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "recordings_cached": len(self._recording_cache),
            "artists_cached": len(self._artist_rels_cache),
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._recording_cache.clear()
        self._artist_rels_cache.clear()

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.close()

    def __enter__(self) -> MusicBrainzDB:
        return self

    def __exit__(self, *args) -> None:
        self.close()
