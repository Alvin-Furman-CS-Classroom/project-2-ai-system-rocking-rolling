# Wave Guide — Speaker Notes

> Each section maps to one slide. Estimated runtime: ~15 min (10 min content + 5 min demo).

---

## Slide 1 — Title: Wave Guide

- AI-powered playlist generation system
- Builds smooth musical journeys between any two songs
- Introduce both team members: Michael Thomas & Rahul Ranjan Sah

---

## Slide 2 — Problem: The Perfect Playlist

- Manual playlist sequencing is hard — abrupt jumps feel jarring
- Good DJs bridge gaps instinctively; we want to automate that
- Framed as a **path-finding problem**: given Track A and Track B, find the best sequence of waypoints between them
- The Catmull-Rom spline on screen reflects the smooth interpolation we're aiming for musically

---

## Slide 3 — Architecture

- Four modules, each handling a distinct layer of the problem:
  - **Module 1** — encodes music theory as a knowledge base; answers "how compatible are these two tracks?"
  - **Module 2** — runs beam search over a similarity graph to find candidate paths
  - **Module 3** — assembles the final playlist: constraint solving, conflict resolution, explanations
  - **API / Frontend** — ties everything together; powers the live demo
- Entirely open-source infrastructure — no proprietary music APIs

---

## Slide 4 — Infrastructure: 38 Million Recordings

- Three open data sources, each contributing a different layer:
  - **MusicBrainz** — metadata backbone; 38M recordings, 2.8M artists, local Postgres mirror
  - **AcousticBrainz** — ~7M tracks with audio features (BPM, key, MFCC, energy bands, mood, genre); now archived
  - **ListenBrainz** — live similarity graph (edges); merges four similarity algorithms
- Together: MusicBrainz + AcousticBrainz = *nodes*; ListenBrainz = *edges*
- AcousticBrainz being archived is the motivation for Essentia integration on the roadmap

---

## Slide 5 — Radar: A Musical Fingerprint

- Every track is an **11-dimensional feature vector**: Key, Tempo, Energy, Loudness, Mood, Timbre, Tags, Popularity, Artist, Era, Genre
- The radar chart shows the "shape" of a track across those dimensions
- Cycle through the four demo songs to illustrate contrast:
  - **Girls Just Wanna Have Fun** — high energy, high popularity, pop-skewed
  - **Comfortably Numb** — high timbre complexity, moderate energy, strong era signature
  - **Mozart Symphony No. 35** — high key/genre purity, low popularity and tags
  - **Bohemian Rhapsody** — unusually balanced across nearly all dimensions
- These are computed values, not manual labels — they feed directly into compatibility scoring

---

## Slide 6 — ProbLog: Music Theory Compatibility Rules

- Module 1 encodes music theory as **probabilistic logic** via ProbLog (Prolog + probabilities)
- Key distinction: facts carry confidence scores, not just true/false (e.g., `0.82::key_compatible(t1, t2)`)
- `smooth_transition(T1, T2)` requires all 11 dimensions; ProbLog propagates uncertainty through the conjunction and returns a single probability
- Python computes continuous probabilities per dimension, asserts them as ProbLog facts
- Notable dimension strategies:
  - **Mood** — noisy-OR: multiple weak signals can combine into a strong match
  - **Genre** — dot product on rosamerica 8-class distributions
  - **Era** — Gaussian decay: nearby eras compatible, distant ones penalised

---

## Slide 7 — Compatibility: Track Compatibility

- Shows two example tracks scored across all 11 dimensions
- Some dimensions will be high (shared era, similar energy), others low (different key or mood)
- The weighted combination of all dimensions produces the final compatibility score in [0, 1]
- This score becomes the **edge weight** Module 2 searches over

---

## Slide 8 — Beam Search: Finding the Path

- Full graph search over 38M nodes is intractable — use **bidirectional beam search with A\***
- Visualization key:
  - Orange = forward frontier expanding from source
  - White = backward frontier expanding from destination
  - Search terminates when frontiers meet
- At each step, keep only the top `beam_width` nodes (default: 10) — prunes the search space
- A\* heuristic: Module 1 compatibility penalty — prefer paths that look compatible at each hop

---

## Slide 9 — Frontier Widening: Discovering New Tracks

- Beam search only navigates edges that already exist in the local similarity graph — if the beam runs out of good neighbours, it stalls
- When the surviving frontier is too narrow, the system queries the **ListenBrainz similar-tracks API** to fetch new candidates and insert them as live nodes
- Visualization key:
  - **Orange columns** — forward frontier expanding level-by-level from the source track
  - **Dark columns** — backward frontier expanding level-by-level from the destination track
  - Both sides advance simultaneously, one beam-width layer per step
  - **Ringed nodes** — tracks discovered via ListenBrainz, not present in the local graph; added on-the-fly
  - After three levels each, frontiers overlap and cross-edges appear; the orange path traces the winning route through the merged graph
- The winning path deliberately passes through a ListenBrainz-discovered node — showing that widening was load-bearing, not cosmetic

---

## Slide 10 — Constraints: Shaping the Playlist

- Beam search produces a *candidate* path; Module 3 refines it with constraints
- **Hard constraints** (must be satisfied) — resolved via min-conflicts CSP:
  - No repeat artists — violating track swapped for best alternative
  - No repeated tracks — deduplication by MusicBrainz ID
- **Soft constraints** (shape quality):
  - **Energy Arc** — smooth rise or fall, no random spikes
  - **Genre Variety** — mix of genres preferred over a monotone list
  - **Tempo Smoothness** — adjacent BPM values should be close
  - **Mood Coherence** — mood sequence should make emotional sense
- The highlighted track 3 on-screen demonstrates the repeat-artist violation and the swap

---

## Slide 11 — Preferences: Learning Your Taste

- System learns from star ratings using **exponential moving average** on dimension weights
- Formula: `w_{t+1} = α · w_{feedback} + (1 - α) · w_t`
- Example on screen: user loved tempo flow, found mood off → tempo weight ↑, mood weight ↓
- α ≈ 0.1 — gradual learning; one bad rating doesn't undo the model
- No explicit preference settings needed — personalisation emerges from feedback over time

---

## Slide 12 — Mood: Mood to Music

- Lets users start from a **feeling** rather than a specific track
- Classifier input: 23-dimensional feature vector (BPM, energy bands, loudness, dynamic complexity, dissonance, spectral centroid, onset rate, 13 MFCCs)
- 6 output labels: Calm, Chill, Sad, Happy, Energized, Intense
- Models trained: Logistic Regression, MLP, ensemble — **best validation accuracy: 64.7%**
  - Meaningful given inherent subjectivity of mood labels
- Selected mood → **centroid** of that mood's training data → fed to Module 2 as beam search source
  - Navigating toward the mood's center of mass in feature space, not a single arbitrary track

---

## Slide 13 — Demo Cover

- Transition point — pause before moving forward
- Introduce the live demo section

---

## Slide 14 — Demo: Pick Your Genres

- User selects one or more genres to seed the artist and track pool
- Suggested selection for demo: **Rock + Pop** — good breadth of bridging artists

---

## Slide 15 — Demo: Pick Your Artists

- Artist list pulled from MusicBrainz filtered to those with audio feature data available
- Suggested selection: a mix like **David Bowie, Radiohead, Madonna** — stylistically distinct for interesting paths
- Changing genre selection resets downstream state

---

## Slide 16 — Demo: Your Taste Profile

- Confirms selected genres and artists before proceeding
- In a real deployment this profile would persist across sessions
- Click "Set Your Mood Journey" to continue

---

## Slide 17 — Demo: Your Mood Journey

- User picks a **start mood** and **end mood** — defines the emotional arc
- Suggested pairing for demo: **Energized → Calm** (wind-down) or **Chill → Intense** (build-up)
- Each mood becomes a centroid in feature space; these seed the two ends of the beam search

---

## Slide 18 — Demo: Pick Your Anchor Tracks

- System surfaces tracks matching the selected moods, filtered by chosen artists/genres
- Each card shows: title, artist, BPM, key/scale, mood classification
- Select one start track (left column) and one end track (right column)
- These two MBIDs become the hard endpoints; everything in between is generated

---

## Slide 19 — Demo: Generating Your Playlist

- Live API call to Flask backend: `source_mbid`, `dest_mbid`, `length=7`, `beam_width=10`
- Background animation shows beam search frontier expanding from both ends
- Real ProbLog evaluations running against the music knowledge base
- Generation typically takes 3–8 seconds

---

## Slide 20 — Demo: Your Playlist

- **Left** — 7-track sequence with title, artist, key, BPM per track
- **Right top** — compatibility arc (SVG): transition probabilities between consecutive tracks; highlights where connections are strong or weak
- **Right bottom** — constraint scorecard: all 6 constraints with pass/fail and scores
- **Bottom** — auto-generated summary: human-readable description of the musical journey
- Average compatibility shown top-right; live result — every run may vary slightly

---

## Slide 21 — Future: What's Next

- **Essentia Integration** — replace archived AcousticBrainz; Module 3 already has scaffolding; yt-dlp fetches audio, Essentia extracts features
- **Weight Optimisation** — current dimension weights manually calibrated; fitting against the Spotify Million Playlist Dataset would give a principled baseline
- **Real-Time Analysis** — stream audio features during playback; update playlist dynamically rather than generating once upfront
- **Multi-Modal Input** — natural language goals ("chill morning to party night"); LLM → mood trajectory mapping is a natural extension

---

## Slide 22 — Thank You

- Recap the stack: open-source data, probabilistic logic, beam search, constraint satisfaction, mood classification
- Core goal: a playlist that feels like a journey, not a shuffle
- Open for questions
