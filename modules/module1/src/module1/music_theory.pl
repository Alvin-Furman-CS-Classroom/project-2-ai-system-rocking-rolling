% ============================================================================
% Music Theory Knowledge Base for Wave Guide
% Probabilistic Logic Rules for Transition Smoothness
%
% This file contains RULES and DEFAULT CLAUSES only.
% Facts are generated programmatically by the Python MusicKnowledgeBase class.
%
% v8: Key, tempo, energy, loudness, timbre compatibility probabilities are
%     computed in Python using research-grounded continuous functions and
%     asserted as probabilistic facts. ProbLog handles mood (noisy-OR)
%     and genre (dot product via annotated disjunctions).
%
%     ListenBrainz integration: tag_compatible and popularity_compatible
%     are computed in Python (cosine similarity and log-Gaussian) from
%     user-behavioral data and asserted as probabilistic facts.
%
%     MusicBrainz integration: artist_compatible (graph topology),
%     era_compatible (Gaussian decay on year), mb_genre_compatible
%     (Jaccard on curated taxonomy) — all computed in Python.
% ============================================================================

% ----------------------------------------------------------------------------
% Default clauses for predicates that may not have facts
% These ensure ProbLog doesn't error when predicates are undefined
% ----------------------------------------------------------------------------

% Compatibility predicates — asserted as probabilistic facts from Python
% Defaults to false when not asserted (e.g., missing data edge cases)
key_compatible(_, _) :- fail.
tempo_compatible(_, _) :- fail.
energy_compatible(_, _) :- fail.
loudness_compatible(_, _) :- fail.
timbre_compatible(_, _) :- fail.

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

% ListenBrainz-enriched predicates — asserted as probabilistic facts from Python
% tag_compatible: cosine similarity of user-generated tag vectors
% popularity_compatible: log-Gaussian decay on listen count difference
tag_compatible(_, _) :- fail.
has_tag_data(_) :- fail.
popularity_compatible(_, _) :- fail.
has_popularity_data(_) :- fail.

% MusicBrainz editorial metadata — asserted as probabilistic facts from Python
% artist_compatible: graph topology on artist relationships (Korzeniowski 2021)
% era_compatible: Gaussian decay on release year difference (Schweiger 2025)
% mb_genre_compatible: Jaccard similarity on curated genre taxonomy (Serra 2022)
artist_compatible(_, _) :- fail.
era_compatible(_, _) :- fail.
mb_genre_compatible(_, _) :- fail.

% User preferences default to disabled
pref_consistent_tempo :- fail.
pref_target_mood(_) :- fail.
pref_avoid_mood(_) :- fail.

% ----------------------------------------------------------------------------
% Mood Compatibility Rules
% Uses independent probabilistic facts: mood_happy(T), mood_sad(T), etc.
% ProbLog computes noisy-OR: P = 1 - ∏(1 - P(mood_X(T1)) × P(mood_X(T2)))
% No hand-tuned cross-mood bonuses — let the data speak.
% ----------------------------------------------------------------------------

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
% Genre Compatibility Rules
% Uses annotated disjunctions: genre(T, G) with full probability distribution
% ProbLog computes dot product: P = Σ_g P(genre(T1,g)) × P(genre(T2,g))
% (exact computation since genre is mutually exclusive per track)
% ----------------------------------------------------------------------------

genre_compatible(T1, T2) :- has_genre_data(T1), has_genre_data(T2), genre(T1, G), genre(T2, G).

% Fallback for missing genre data
0.50::genre_compatible(T1, T2) :- \+ has_genre_data(T1).
0.50::genre_compatible(T1, T2) :- \+ has_genre_data(T2).

% ----------------------------------------------------------------------------
% Composite Smoothness Rule
% A smooth transition requires compatibility across all dimensions.
% NOTE: Python computes the actual weighted score via knowledge_base.py.
% This rule exists for structural completeness and direct ProbLog queries.
% ----------------------------------------------------------------------------

smooth_transition(T1, T2) :-
    key_compatible(T1, T2),
    tempo_compatible(T1, T2),
    energy_compatible(T1, T2),
    loudness_compatible(T1, T2),
    mood_compatible(T1, T2),
    timbre_compatible(T1, T2),
    tag_compatible(T1, T2),
    popularity_compatible(T1, T2),
    artist_compatible(T1, T2),
    era_compatible(T1, T2),
    mb_genre_compatible(T1, T2).

% ----------------------------------------------------------------------------
% User Preference Rules
% These are activated when user preferences are set
% ----------------------------------------------------------------------------

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
    mood_preference_met(T1, T2).
