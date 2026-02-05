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
% Based on energy score difference
% ----------------------------------------------------------------------------

% Smooth energy transition (delta < 0.15)
0.90::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff < 0.15.

% Moderate energy transition (0.15 <= delta < 0.3)
0.75::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.15,
    Diff < 0.3.

% Noticeable energy transition (0.3 <= delta < 0.5)
0.45::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.3,
    Diff < 0.5.

% Jarring energy transition (delta >= 0.5)
0.15::energy_compatible(T1, T2) :-
    energy_score(T1, E1),
    energy_score(T2, E2),
    energy_diff(E1, E2, Diff),
    Diff >= 0.5.

% ----------------------------------------------------------------------------
% Loudness Compatibility Rules
% Based on average loudness difference
% ----------------------------------------------------------------------------

% Very consistent loudness (< 3 units)
0.95::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff < 3.

% Consistent loudness (3-6 units)
0.85::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 3,
    Diff < 6.

% Moderate loudness difference (6-10 units)
0.60::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 6,
    Diff < 10.

% Large loudness difference (>= 10 units)
0.30::loudness_compatible(T1, T2) :-
    average_loudness(T1, L1),
    average_loudness(T2, L2),
    loudness_diff(L1, L2, Diff),
    Diff >= 10.

% Default if loudness data missing
0.70::loudness_compatible(T1, T2) :-
    \+ average_loudness(T1, _);
    \+ average_loudness(T2, _).

% ----------------------------------------------------------------------------
% Mood Compatibility Rules
% Based on highlevel mood classifiers
% ----------------------------------------------------------------------------

% Same mood classification - very compatible
0.90::mood_compatible(T1, T2) :-
    has_mood(T1, Mood),
    has_mood(T2, Mood).

% Happy and party - compatible
0.80::mood_compatible(T1, T2) :-
    has_mood(T1, happy),
    has_mood(T2, party).

0.80::mood_compatible(T1, T2) :-
    has_mood(T1, party),
    has_mood(T2, happy).

% Relaxed and sad - compatible
0.75::mood_compatible(T1, T2) :-
    has_mood(T1, relaxed),
    has_mood(T2, sad).

0.75::mood_compatible(T1, T2) :-
    has_mood(T1, sad),
    has_mood(T2, relaxed).

% Aggressive and happy - somewhat incompatible
0.30::mood_compatible(T1, T2) :-
    has_mood(T1, aggressive),
    has_mood(T2, happy).

0.30::mood_compatible(T1, T2) :-
    has_mood(T1, happy),
    has_mood(T2, aggressive).

% Aggressive and relaxed - very incompatible
0.10::mood_compatible(T1, T2) :-
    has_mood(T1, aggressive),
    has_mood(T2, relaxed).

0.10::mood_compatible(T1, T2) :-
    has_mood(T1, relaxed),
    has_mood(T2, aggressive).

% Default mood compatibility for other combinations
0.60::mood_compatible(T1, T2) :-
    has_mood(T1, M1),
    has_mood(T2, M2),
    M1 \= M2.

% If mood data missing, use neutral probability
0.70::mood_compatible(T1, T2) :-
    \+ has_mood(T1, _);
    \+ has_mood(T2, _).

% ----------------------------------------------------------------------------
% Timbre Compatibility Rules
% Based on MFCC distance and spectral characteristics
% ----------------------------------------------------------------------------

% Very similar timbre (distance < 5)
0.90::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist < 5.

% Similar timbre (5 <= distance < 10)
0.70::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 5,
    Dist < 10.

% Moderate timbre difference (10 <= distance < 15)
0.50::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 10,
    Dist < 15.

% Different timbre (distance >= 15)
0.30::timbre_compatible(T1, T2) :-
    mfcc_dist(T1, T2, Dist),
    Dist >= 15.

% Default if MFCC data missing
0.60::timbre_compatible(T1, T2) :-
    \+ mfcc_dist(T1, T2, _).

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

% Target mood preference
0.95::mood_preference_met(T1, T2) :-
    pref_target_mood(Mood),
    has_mood(T2, Mood).

0.40::mood_preference_met(T1, T2) :-
    pref_target_mood(Mood),
    has_mood(T2, M2),
    M2 \= Mood.

% No mood preference - always satisfied
1.0::mood_preference_met(_, _) :-
    \+ pref_target_mood(_).

% Smooth transition with preferences
smooth_transition_with_prefs(T1, T2) :-
    smooth_transition(T1, T2),
    tempo_preference_met(T1, T2),
    mood_preference_met(T1, T2).
