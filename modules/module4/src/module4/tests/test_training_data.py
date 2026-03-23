"""Tests for training_data.py."""

from module4.data_models import MoodLabel
from module4.training_data import derive_mood_label, generate_synthetic_data


def _hl(
    aggressive=0.1, sad=0.1, happy=0.1, party=0.1, relaxed=0.1, acoustic=0.1
) -> dict:
    """Build a minimal highlevel dict for testing derive_mood_label."""
    return {
        "highlevel": {
            "mood_aggressive": {
                "all": {"aggressive": aggressive, "not_aggressive": 1.0 - aggressive}
            },
            "mood_sad": {"all": {"sad": sad, "not_sad": 1.0 - sad}},
            "mood_happy": {"all": {"happy": happy, "not_happy": 1.0 - happy}},
            "mood_party": {"all": {"party": party, "not_party": 1.0 - party}},
            "mood_relaxed": {"all": {"relaxed": relaxed, "not_relaxed": 1.0 - relaxed}},
            "mood_acoustic": {
                "all": {"acoustic": acoustic, "not_acoustic": 1.0 - acoustic}
            },
        }
    }


class TestDeriveMoodLabel:
    def test_strongly_happy_gives_happy(self):
        hl = _hl(happy=0.85, aggressive=0.10)
        assert derive_mood_label(hl) == MoodLabel.HAPPY

    def test_ambiguous_gives_none(self):
        hl = _hl(
            aggressive=0.5, sad=0.5, happy=0.5, party=0.5, relaxed=0.5, acoustic=0.5
        )
        assert derive_mood_label(hl) is None

    def test_aggressive_gives_intense(self):
        hl = _hl(aggressive=0.85)
        assert derive_mood_label(hl) == MoodLabel.INTENSE

    def test_sad_gives_sad(self):
        hl = _hl(sad=0.80)
        assert derive_mood_label(hl) == MoodLabel.SAD

    def test_party_gives_energized(self):
        hl = _hl(party=0.80, sad=0.10)
        assert derive_mood_label(hl) == MoodLabel.ENERGIZED

    def test_relaxed_not_acoustic_gives_calm(self):
        hl = _hl(relaxed=0.80, party=0.10, acoustic=0.30)
        assert derive_mood_label(hl) == MoodLabel.CALM

    def test_relaxed_acoustic_gives_chill(self):
        hl = _hl(relaxed=0.70, acoustic=0.65)
        assert derive_mood_label(hl) == MoodLabel.CHILL

    def test_aggressive_takes_priority_over_sad(self):
        # Both > 0.70, aggressive checked first
        hl = _hl(aggressive=0.80, sad=0.80)
        assert derive_mood_label(hl) == MoodLabel.INTENSE

    def test_happy_blocked_by_aggressive(self):
        # happy > 0.70 but aggressive >= 0.40 → not HAPPY
        hl = _hl(happy=0.80, aggressive=0.50)
        # Should not be HAPPY; falls through to check other rules
        result = derive_mood_label(hl)
        assert result != MoodLabel.HAPPY

    def test_low_thresholds_give_none(self):
        hl = _hl(
            aggressive=0.30,
            sad=0.30,
            happy=0.30,
            party=0.30,
            relaxed=0.30,
            acoustic=0.30,
        )
        assert derive_mood_label(hl) is None


class TestGenerateSyntheticData:
    def test_returns_correct_total_count(self):
        examples = generate_synthetic_data(n_per_class=50)
        assert len(examples) == 300  # 50 × 6

    def test_each_class_has_n_per_class(self):
        n = 50
        examples = generate_synthetic_data(n_per_class=n)
        from collections import Counter

        counts = Counter(e.label for e in examples)
        for mood in MoodLabel:
            assert counts[mood] == n, f"{mood.value}: expected {n}, got {counts[mood]}"

    def test_all_features_in_0_1(self):
        examples = generate_synthetic_data(n_per_class=20)
        for ex in examples:
            for i, v in enumerate(ex.features):
                assert 0.0 <= v <= 1.0, f"Feature {i} out of range: {v}"

    def test_labels_are_valid_mood_labels(self):
        examples = generate_synthetic_data(n_per_class=10)
        valid = set(MoodLabel)
        for ex in examples:
            assert ex.label in valid

    def test_feature_vector_length(self):
        examples = generate_synthetic_data(n_per_class=10)
        for ex in examples:
            assert len(ex.features) == 23

    def test_reproducible_with_seed(self):
        ex1 = generate_synthetic_data(n_per_class=10, random_seed=1)
        ex2 = generate_synthetic_data(n_per_class=10, random_seed=1)
        for a, b in zip(ex1, ex2):
            assert a.features == b.features
            assert a.label == b.label

    def test_different_seeds_give_different_data(self):
        ex1 = generate_synthetic_data(n_per_class=10, random_seed=1)
        ex2 = generate_synthetic_data(n_per_class=10, random_seed=2)
        # At least some features should differ
        any_diff = any(a.features != b.features for a, b in zip(ex1, ex2))
        assert any_diff
