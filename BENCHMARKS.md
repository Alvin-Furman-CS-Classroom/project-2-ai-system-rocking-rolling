# Benchmarks

Postgres (local MusicBrainz mirror) vs Public API.

## 2026-04-01 00:32

| Query | API | Postgres | Speedup |
|-------|-----|----------|---------|
| 25 single lookups | 43.526s | 24.888s | 2x |
| 25-MBID batch | 1.160s | 0.931s | 1x |
| 5 artist rels | 6.313s | 2.331s | 3x |
| **TOTAL** | **50.999s** | **28.150s** | **2x** |

## 2026-04-01 00:43

| Query | API | Postgres | Speedup |
|-------|-----|----------|---------|
| 4 single lookups | 7.757s | 5.073s | 2x |
| 4-MBID batch | 1.749s | 0.972s | 2x |
| 5 artist rels | 5.816s | 2.106s | 3x |
| **TOTAL** | **15.322s** | **8.151s** | **2x** |

