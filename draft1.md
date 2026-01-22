# Wave Guide: Intelligent Music Journey Generation

## System Overview

Wave Guide creates personalized music playlists that take listeners on a "journey" from a starting track to a destination track, discovering new music along the way. Unlike traditional recommendation systems that optimize for similarity alone, Wave Guide treats playlist generation as a path-finding problem through multidimensional audio feature space.

The system addresses a critical limitation in existing music platforms: Spotify recently restricted API access to recommendation endpoints, making proprietary solutions unsustainable. Wave Guide leverages AcousticBrainz, an open-source database containing acoustic analysis for millions of tracks (71-dimensional feature vectors including energy, valence, timbre, rhythm, and tonal characteristics).

Users specify source and destination tracks (or moods). The system encodes music theory knowledge and transition smoothness rules as a propositional logic knowledge base, then uses A* search to find optimal paths through feature space that satisfy these constraints. For each waypoint along the path, vector similarity retrieval identifies real tracks from AcousticBrainz. A machine learning classifier enables mood-based queries by mapping abstract moods to concrete feature vectors. The final playlist balances smooth transitions, stylistic diversity, and adherence to music theory principles—creating journeys that feel intentional rather than algorithmically random. This integrated approach demonstrates how multiple AI techniques combine to solve a real-world problem: making music discovery both systematic and serendipitous.

(Word count: 210)

## Modules

### Module 1: Music Feature Knowledge Base

**Topics:** Propositional Logic (Knowledge Bases, Inference, Logical Rules, Entailment)

**Input:** AcousticBrainz high-level and low-level feature data (JSON format containing 71-dimensional vectors: mood features, genre probabilities, danceability, acousticness, energy, valence, timbre coefficients, rhythm patterns). User-defined constraints (optional): tempo range, key compatibility preferences, mood requirements.

**Output:** A propositional knowledge base encoding music theory rules and transition compatibility constraints. Rules represented as logical clauses (e.g., "IF energy > 0.8 AND valence < 0.3 THEN mood = intense" or "IF |tempo_diff| > 30 THEN transition_rough = true"). Includes inference engine capable of validating whether a proposed track sequence satisfies encoded constraints.

**Integration:** This module serves as the foundational constraint validator for the entire system. Module 2 (A* Search) queries this KB to evaluate path validity—paths violating KB rules incur higher costs. Module 5 (Playlist Assembly) performs final validation, ensuring the complete playlist satisfies all logical constraints before presentation to the user.

**Prerequisites:** Propositional Logic content (Weeks 1-1.5). No prior modules required—this is the foundational module establishing system constraints.

(Word count: 172)

---

### Module 2: Optimal Path Search

**Topics:** Search Algorithms (A* Search, Heuristics, Informed Search)

**Input:** Source track feature vector (71-dimensional), destination track feature vector (71-dimensional), knowledge base rules from Module 1, playlist length parameter (default: 7 tracks including bookends).

**Output:** Ordered sequence of intermediate feature vectors representing optimal path through audio feature space. For a 7-track playlist: [source_vector, waypoint1, waypoint2, waypoint3, waypoint4, waypoint5, destination_vector]. Each waypoint is a point in 71-dimensional space satisfying KB constraints while minimizing total path cost.

**Integration:** Receives source/destination from user input (or Module 4 if mood-based). Queries Module 1's KB during search to evaluate state validity. Outputs waypoint vectors to Module 3 for track retrieval. Improves upon naive linear interpolation by finding paths that avoid KB rule violations and minimize perceptual "roughness" in transitions.

**Prerequisites:** Search content (Weeks 2.5-4). Requires Module 1 (KB must exist to evaluate path validity).

**Algorithm Details:** Search space is continuous 71-dimensional feature space discretized into grid cells. Heuristic function: Euclidean distance to destination weighted by KB rule violation penalties. Cost function: Cumulative distance plus transition smoothness penalty derived from feature delta magnitudes.

(Word count: 193)

---

### Module 3: Track Retrieval via Vector Similarity

**Topics:** Optimization (Search Space Exploration), Vector Databases (Qdrant integration with cosine similarity)

**Input:** Target feature vector (71-dimensional) from Module 2 representing a waypoint in the playlist. Previously selected track IDs (to avoid duplicates). Optional filters: release country, artist diversity constraints.

**Output:** Single track metadata object including: MusicBrainz recording ID, track title, artist name, album, feature vector, and ISRC code (for future cross-platform playback compatibility). Selected track is the closest match to the target vector that hasn't been used yet.

**Integration:** Called iteratively by Module 5 for each waypoint vector produced by Module 2. Uses Qdrant Cloud vector database (pre-populated with AcousticBrainz data) to perform cosine similarity search. Returns matched tracks to Module 5 for playlist assembly. Future enhancement: replace simple nearest-neighbor with genetic algorithm optimizing similarity + diversity + popularity.

**Prerequisites:** Optimization content (Weeks 6.5-7.5) for understanding search space exploration. Module 2 must complete first to provide target vectors.

**Implementation Note:** Qdrant handles the heavy lifting; this module focuses on query formulation, filter application, and result ranking refinement.

(Word count: 173)

---

### Module 4: Mood Classification and Feature Mapping

**Topics:** Machine Learning (Supervised Learning: Logistic Regression or Neural Networks, Feature Engineering, Model Evaluation)

**Input:** Training data: AcousticBrainz tracks with manually labeled moods (Calm, Energized, Happy, Sad, Intense, Chill—approximately 1000+ labeled examples per mood). Inference input: Either a track's 71-dimensional feature vector OR a mood label string.

**Output:**
- **Training phase**: Trained classifier model saved as pickle file with evaluation metrics (accuracy, precision, recall, F1-score per mood class).
- **Inference phase**: If given features → mood label with confidence score. If given mood label → representative feature vector (cluster centroid) for that mood category.

**Integration:** Enables mood-based playlist creation. When users select "Calm" as source and "Energized" as destination, this module converts mood labels to feature vectors, which then feed into Module 2 (A* Search) as source/destination points. Allows users to specify abstract emotional journeys rather than requiring knowledge of specific tracks.

**Prerequisites:** Machine Learning content (Week 12+). Can be developed independently from other modules initially, integrated later. For early checkpoints, hardcode mood-to-feature mappings; replace with trained model by Checkpoint 4.

(Word count: 189)

---

### Module 5: Playlist Assembly and Validation

**Topics:** System Integration, Constraint Satisfaction

**Input:** Source and destination tracks (IDs or mood labels), user preferences (playlist length, optional filters). Waypoint feature vectors from Module 2. Track metadata from Module 3 for each waypoint.

**Output:** Complete playlist object containing: ordered list of track metadata (title, artist, album, ISRC), playlist name generated from source/destination labels, feature progression graph (visualizing energy/valence/danceability journey), validation report confirming KB rule compliance from Module 1.

**Integration:** This is the orchestration module that ties the entire system together. Workflow: (1) If mood-based input, query Module 4 for feature vectors; (2) Pass features to Module 2 for A* path generation; (3) For each waypoint, call Module 3 to retrieve matching track; (4) Validate final sequence against Module 1's KB; (5) If validation fails, request alternative tracks from Module 3; (6) Format output for user presentation. Handles edge cases: no valid path exists, insufficient tracks in database, user interrupts generation.

**Prerequisites:** No new AI topics—integration logic only. Requires all prior modules (1-4) to be functional. Suitable for final checkpoint after all components exist.

(Word count: 186)

---

## Feasibility Study

| Module | Required Topic(s)                          | Topic Covered By | Checkpoint Due     |
| ------ | ------------------------------------------ | ---------------- | ------------------ |
| 1      | Propositional Logic (KB, Inference, Rules) | Week 1.5         | Checkpoint 1 (Feb 11) |
| 2      | Search (A*, Heuristics)                    | Week 4           | Checkpoint 1 (Feb 11) |
| 3      | Optimization (Search Space Exploration)    | Week 7.5         | Checkpoint 2 (Feb 26) |
| 4      | Machine Learning (Supervised Learning)     | Week 12+         | Checkpoint 4 (Apr 2)  |
| 5      | System Integration                         | N/A              | Checkpoint 5 (Apr 16) |

**Timeline Rationale:**
- Modules 1-2 tackle required topics (Logic + Search) early, establishing core path-finding functionality by Checkpoint 1.
- Module 3 leverages optimization concepts taught mid-semester, allowing refinement of track matching by Checkpoint 2.
- Module 4 waits for ML content (Week 12+), providing ample time for data labeling and model training by Checkpoint 4.
- Module 5 integrates all components in final checkpoint, with buffer time for debugging and polish before demo (Apr 23).

## Coverage Rationale

**Why these topics fit Wave Guide:**

The music journey metaphor naturally maps to AI search problems—playlists are paths through feature space. **A* search** (required) improves naive interpolation by avoiding "rough" transitions that violate music theory rules. **Propositional logic** (required) encodes domain knowledge: key compatibility, tempo constraints, and mood coherence rules that human DJs intuitively apply.

**Optimization** enhances track retrieval beyond simple nearest-neighbor, balancing similarity with diversity (avoiding artist repetition). **Machine Learning** enables mood-based queries, making the system accessible to users unfamiliar with specific tracks. This transforms abstract emotional intent ("take me from calm to energized") into concrete audio features.

**Trade-offs considered:** Initially considered Reinforcement Learning for user feedback loops (Q-learning to adjust playlist generation from like/dislike signals), but deferred as optional future work due to timeline constraints and complexity of reward function design. Also considered NLP for lyrics analysis to inform mood classification, but AcousticBrainz's acoustic features provide sufficient signal without adding text processing overhead.

The selected topics create a complete system where each module addresses a distinct challenge: knowledge representation (Logic), pathfinding (Search), retrieval (Optimization), and user interface abstraction (ML). This demonstrates how multiple AI techniques synergize to solve a real problem—systematic music discovery—in a domain where Spotify's API restrictions have created an open-source opportunity.

(Word count: 246)
