# Module 1 Changelog

## 2026-02-10 (v2)
- Dropped c₀ from MFCC distance to avoid double-counting with loudness (Berenzweig 2004).
- Reweighted defaults: timbre 5%→20%, key 25%→15%, tempo 30%→20%, energy 20%→15%, loudness 10%→5%, mood 10%→15%, added genre 10% (papers: MFCCs are dominant similarity signal).
- Added genre compatibility component using AcousticBrainz rosamerica classifier; ProbLog rules: same genre=0.90, different=0.50, missing=0.70 (Aucouturier & Pachet 2002).

## 2026-02-10 (v1)
- Replaced ProbLog conjunction (multiplicative) overall score with weighted average of component probabilities, computed in Python using UserPreferences weights. ProbLog still handles all individual component inference.
- Added `load_track_from_lowlevel` for tracks without high-level JSON; metadata now falls back to low-level tags.
