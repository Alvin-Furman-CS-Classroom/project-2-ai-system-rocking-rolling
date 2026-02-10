# Module 1 Changelog

## 2026-02-10 (v4)
- Recalibrated loudness thresholds from wrong scale (0-10+ units) to actual AcousticBrainz 0-1 scale: <0.05 (very consistent), 0.05–0.15, 0.15–0.35, ≥0.35 (large). Pop at 0.77 vs classical at 0.01–0.18 now correctly shows as incompatible.
- Recalibrated energy thresholds from 0.15/0.3/0.5 to 0.001/0.003/0.005 matching actual spectral energy band range (~0.003–0.007).

## 2026-02-10 (v3)
- Replaced Euclidean MFCC distance with Bhattacharyya distance using full covariance matrices from AcousticBrainz; models each song as single Gaussian N(μ,Σ) — captures timbral spread, not just mean (Aucouturier & Pachet 2002).
- Recalibrated ProbLog timbre thresholds for Bhattacharyya scale: <0.5 (very similar), 0.5–1.0 (similar), 1.0–2.0 (cross-genre), ≥2.0 (very different).

## 2026-02-10 (v2)
- Dropped c₀ from MFCC distance to avoid double-counting with loudness (Berenzweig 2004).
- Reweighted defaults: timbre 5%→20%, key 25%→15%, tempo 30%→20%, energy 20%→15%, loudness 10%→5%, mood 10%→15%, added genre 10% (papers: MFCCs are dominant similarity signal).
- Added genre compatibility component using AcousticBrainz rosamerica classifier; ProbLog rules: same genre=0.90, different=0.50, missing=0.70 (Aucouturier & Pachet 2002).

## 2026-02-10 (v1)
- Replaced ProbLog conjunction (multiplicative) overall score with weighted average of component probabilities, computed in Python using UserPreferences weights. ProbLog still handles all individual component inference.
- Added `load_track_from_lowlevel` for tracks without high-level JSON; metadata now falls back to low-level tags.
