% ============================================================================
% Music Theory Knowledge Base for Wave Guide
% Probabilistic Logic Rules for Transition Smoothness
%
% This file contains RULES ONLY. Facts are generated programmatically
% by the Python MusicKnowledgeBase class using SimpleProgram.
% ============================================================================

% ----------------------------------------------------------------------------
% Default clauses for predicates that may not have facts
% These ensure ProbLog doesn't error when predicates are undefined
% ----------------------------------------------------------------------------

% Double-time defaults to false
is_double_time(_, _) :- fail.

% Mood predicates default to false (probabilistic facts added by Python)
mood_happy(_) :- fail.
mood_sad(_) :- fail.
mood_aggressive(_) :- fail.
mood_relaxed(_) :- fail.
mood_party(_) :- fail.
mood_acoustic(_) :- fail.
has_mood_data(_) :- fail.

% Genre predicate default (annotated disjunctions added by Python)
genre(_, _) :- fail.
has_genre_data(_) :- fail.

% User preferences default to disabled
pref_consistent_tempo :- fail.
pref_target_mood(_) :- fail.
pref_avoid_mood(_) :- fail.

% ----------------------------------------------------------------------------
% Key Compatibility Rules
% Based on circle of fifths distance and key strength confidence
% ----------------------------------------------------------------------------

% Same key and scale - very high compatibility
0.95::key_compatible(T1, T2) :-
    has_key(T1, Key, Scale, _),
    has_key(T2, Key, Scale, _).

% Parallel keys (same root, different scale) - high compatibility
0.80::key_compatible(T1, T2) :-
    has_key(T1, Key, major, _),
    has_key(T2, Key, minor, _).

0.80::key_compatible(T1, T2) :-
    has_key(T1, Key, minor, _),
    has_key(T2, Key, major, _).

% Adjacent keys on circle of fifths (1 step) - good compatibility
0.70::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 1).

% 2 steps on circle of fifths - moderate compatibility
0.50::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 2).

% 3 steps on circle of fifths - low compatibility
0.30::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 3).

% 4 steps on circle of fifths - very low compatibility
0.20::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 4).

% 5 steps on circle of fifths - poor compatibility
0.10::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 5).

% Tritone (6 steps, opposite on circle) - worst compatibility
0.05::key_compatible(T1, T2) :-
    has_key(T1, K1, _, _),
    has_key(T2, K2, _, _),
    circle_distance(K1, K2, 6).

% ----------------------------------------------------------------------------
% Tempo Compatibility Rules
% Based on BPM difference thresholds
% ----------------------------------------------------------------------------

% Imperceptible tempo difference (< 5 BPM)
0.95::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff < 5.

% Smooth tempo difference (5-10 BPM)
0.85::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff >= 5,
    Diff < 10.

% Noticeable but acceptable (10-20 BPM)
0.60::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff >= 10,
    Diff < 20.

% Moderate transition (20-30 BPM)
0.35::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff >= 20,
    Diff < 30.

% Large jump (>= 30 BPM) - very low compatibility
0.10::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff >= 30.

% Special case: double-time or half-time relationship
% Note: is_double_time fact is added by Python when applicable
0.75::tempo_compatible(T1, T2) :-
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    is_double_time(BPM1, BPM2).

% ----------------------------------------------------------------------------
% Energy Compatibility Rules
% Based on spectral energy score difference
% AcousticBrainz energy scores are typically 0.001-0.01 range
% Thresholds calibrated to actual data distribution
% ----------------------------------------------------------------------------

% Very similar energy (delta < 0.001)
0.90::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff < 0.001.

% Similar energy (0.001 <= delta < 0.003)
0.70::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.001,
    Diff < 0.003.

% Noticeable energy difference (0.003 <= delta < 0.005)
0.45::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.003,
    Diff < 0.005.

% Large energy difference (delta >= 0.005)
0.20::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.005.

% ----------------------------------------------------------------------------
% Loudness Compatibility Rules
% AcousticBrainz average_loudness is on a 0-1 scale
% Thresholds calibrated to actual data: pop ~0.77, classical 0.01-0.18
% ----------------------------------------------------------------------------

% Very consistent loudness (diff < 0.05)
0.90::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff < 0.05.

% Consistent loudness (0.05 <= diff < 0.15)
0.75::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 0.05,
    Diff < 0.15.

% Moderate loudness difference (0.15 <= diff < 0.35)
0.45::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 0.15,
    Diff < 0.35.

% Large loudness difference (diff >= 0.35)
0.15::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 0.35.

% Default if loudness data missing
0.70::loudness_compatible(T1, T2) :-
    \+ average_loudness(T1, _);
    \+ average_loudness(T2, _).

% ----------------------------------------------------------------------------
% Mood Compatibility Rules
% Uses independent probabilistic facts: mood_happy(T), mood_sad(T), etc.
% ProbLog computes noisy-OR: P = 1 - ∏(1 - P(mood_X(T1)) × P(mood_X(T2)))
% No hand-tuned cross-mood bonuses — let the data speak.
% ----------------------------------------------------------------------------

% Mood compatibility via noisy-OR over shared mood dimensions
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_happy(T1), mood_happy(T2).
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_sad(T1), mood_sad(T2).
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_aggressive(T1), mood_aggressive(T2).
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_relaxed(T1), mood_relaxed(T2).
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_party(T1), mood_party(T2).
mood_compatible(T1, T2) :- has_mood_data(T1), has_mood_data(T2), mood_acoustic(T1), mood_acoustic(T2).

% Fallback for missing mood data
0.50::mood_compatible(T1, T2) :- \+ has_mood_data(T1).
0.50::mood_compatible(T1, T2) :- \+ has_mood_data(T2).

% ----------------------------------------------------------------------------
% Timbre Compatibility Rules
% Based on Bhattacharyya distance between single-Gaussian MFCC models
% (Aucouturier & Pachet 2002; thresholds calibrated on test data)
% ----------------------------------------------------------------------------

% Very similar timbre (distance < 0.5) — same genre, similar instruments
0.90::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist < 0.5.

% Similar timbre (0.5 <= distance < 1.0) — related genres
0.70::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 0.5,
    Dist < 1.0.

% Moderate timbre difference (1.0 <= distance < 2.0) — cross-genre
0.50::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 1.0,
    Dist < 2.0.

% Very different timbre (distance >= 2.0)
0.30::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 2.0.

% Default if MFCC data missing
0.60::timbre_compatible(T1, T2) :-
    \+ mfcc_dist(T1, T2, _).

% ----------------------------------------------------------------------------
% Genre Compatibility Rules
% Uses annotated disjunctions: genre(T, G) with full probability distribution
% ProbLog computes dot product: P = Σ_g P(genre(T1,g)) × P(genre(T2,g))
% (exact computation since genre is mutually exclusive per track)
% ----------------------------------------------------------------------------

% Genre compatibility as dot product of genre distributions
genre_compatible(T1, T2) :- has_genre_data(T1), has_genre_data(T2), genre(T1, G), genre(T2, G).

% Fallback for missing genre data
0.50::genre_compatible(T1, T2) :- \+ has_genre_data(T1).
0.50::genre_compatible(T1, T2) :- \+ has_genre_data(T2).

% ----------------------------------------------------------------------------
% Composite Smoothness Rule
% A smooth transition requires compatibility across all dimensions
% ----------------------------------------------------------------------------

smooth_transition(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2),
    loudness_compatible(T1, T2),
    mood_compatible(T1, T2),
    timbre_compatible(T1, T2).

% ----------------------------------------------------------------------------
% User Preference Rules
% These are activated when user preferences are set
% ----------------------------------------------------------------------------

% Prefer consistent tempo
0.90::tempo_preference_met(T1, T2) :-
    pref_consistent_tempo,
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff < 10.

0.50::tempo_preference_met(T1, T2) :-
    pref_consistent_tempo,
    has_bpm(T1, BPM1),
    has_bpm(T2, BPM2),
    bpm_diff(BPM1, BPM2, Diff),
    Diff >= 10.

% No tempo preference - always satisfied
1.0::tempo_preference_met(_, _) :-
    \+ pref_consistent_tempo.

% Target mood preference — uses probabilistic mood facts
mood_preference_met(T1, T2) :-
    pref_target_mood(happy), mood_happy(T2).
mood_preference_met(T1, T2) :-
    pref_target_mood(sad), mood_sad(T2).
mood_preference_met(T1, T2) :-
    pref_target_mood(aggressive), mood_aggressive(T2).
mood_preference_met(T1, T2) :-
    pref_target_mood(relaxed), mood_relaxed(T2).
mood_preference_met(T1, T2) :-
    pref_target_mood(party), mood_party(T2).
mood_preference_met(T1, T2) :-
    pref_target_mood(acoustic), mood_acoustic(T2).

% Missing mood data with active preference
0.50::mood_preference_met(T1, T2) :-
    pref_target_mood(_), \+ has_mood_data(T2).

% No mood preference - always satisfied
1.0::mood_preference_met(_, _) :-
    \+ pref_target_mood(_).

% Smooth transition with preferences
smooth_transition_with_prefs(T1, T2) :-
    smooth_transition(T1, T2),
    tempo_preference_met(T1, T2),
    mood_preference_met(T1, T2).
