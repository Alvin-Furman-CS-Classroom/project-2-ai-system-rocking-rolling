"""Tests for mood_classifier.py."""

import tempfile
from pathlib import Path

import pytest

from module4.data_models import MoodLabel
from module4.mood_classifier import MoodClassifier
from module4.training_data import _SYNTHETIC_CENTROIDS, generate_synthetic_data


def _trained_lr() -> MoodClassifier:
    examples = generate_synthetic_data(n_per_class=200, random_seed=42)
    clf = MoodClassifier(model_type="logistic_regression")
    clf.train(examples, random_seed=42)
    return clf


def _trained_mlp() -> MoodClassifier:
    examples = generate_synthetic_data(n_per_class=200, random_seed=42)
    clf = MoodClassifier(model_type="mlp")
    clf.train(examples, random_seed=42)
    return clf


class TestTrainAccuracy:
    def test_lr_accuracy_above_threshold(self):
        examples = generate_synthetic_data(n_per_class=200, random_seed=42)
        clf = MoodClassifier(model_type="logistic_regression")
        metrics = clf.train(examples, random_seed=42)
        assert metrics.accuracy > 0.70, f"LR accuracy too low: {metrics.accuracy:.3f}"

    def test_mlp_accuracy_above_threshold(self):
        examples = generate_synthetic_data(n_per_class=200, random_seed=42)
        clf = MoodClassifier(model_type="mlp")
        metrics = clf.train(examples, random_seed=42)
        assert metrics.accuracy > 0.75, f"MLP accuracy too low: {metrics.accuracy:.3f}"

    def test_eval_metrics_accuracy_in_0_1(self):
        clf = _trained_lr()
        examples = generate_synthetic_data(n_per_class=50, random_seed=99)
        metrics = clf.evaluate(examples)
        assert 0.0 <= metrics.accuracy <= 1.0

    def test_eval_metrics_has_all_6_classes(self):
        clf = _trained_lr()
        examples = generate_synthetic_data(n_per_class=50, random_seed=99)
        metrics = clf.evaluate(examples)
        expected = {m.value for m in MoodLabel}
        assert set(metrics.per_class.keys()) == expected


class TestClassify:
    def test_classify_returns_mood_classification(self):
        clf = _trained_lr()
        result = clf.classify([0.5] * 23)
        from module4.data_models import MoodClassification

        assert isinstance(result, MoodClassification)

    def test_confidence_in_0_1(self):
        clf = _trained_lr()
        result = clf.classify([0.5] * 23)
        assert 0.0 <= result.confidence <= 1.0

    def test_top_3_moods_length(self):
        clf = _trained_lr()
        result = clf.classify([0.5] * 23)
        assert len(result.top_3_moods) == 3

    def test_top_3_probs_leq_1(self):
        clf = _trained_lr()
        result = clf.classify([0.5] * 23)
        total = sum(p for _, p in result.top_3_moods)
        assert total <= 1.0 + 1e-6

    def test_strongly_happy_track(self):
        clf = _trained_lr()
        features = _SYNTHETIC_CENTROIDS[MoodLabel.HAPPY].copy()
        result = clf.classify(features)
        assert result.mood == MoodLabel.HAPPY

    def test_strongly_intense_track(self):
        clf = _trained_lr()
        features = _SYNTHETIC_CENTROIDS[MoodLabel.INTENSE].copy()
        result = clf.classify(features)
        assert result.mood == MoodLabel.INTENSE

    def test_strongly_sad_track(self):
        clf = _trained_lr()
        features = _SYNTHETIC_CENTROIDS[MoodLabel.SAD].copy()
        result = clf.classify(features)
        assert result.mood == MoodLabel.SAD

    def test_classify_before_train_raises(self):
        clf = MoodClassifier()
        with pytest.raises(RuntimeError):
            clf.classify([0.5] * 23)


class TestCentroid:
    def test_get_centroid_returns_list(self):
        clf = _trained_lr()
        centroid = clf.get_centroid(MoodLabel.CALM)
        assert isinstance(centroid, list)

    def test_get_centroid_length_23(self):
        clf = _trained_lr()
        centroid = clf.get_centroid(MoodLabel.CALM)
        assert len(centroid) == 23

    def test_get_centroid_values_in_0_1(self):
        clf = _trained_lr()
        for mood in MoodLabel:
            centroid = clf.get_centroid(mood)
            for v in centroid:
                assert 0.0 <= v <= 1.0, f"{mood.value} centroid out of range: {v}"

    def test_get_centroid_before_train_raises(self):
        clf = MoodClassifier()
        with pytest.raises(RuntimeError):
            clf.get_centroid(MoodLabel.CALM)


class TestSaveLoad:
    def test_save_load_roundtrip(self):
        clf = _trained_lr()
        features = _SYNTHETIC_CENTROIDS[MoodLabel.HAPPY].copy()
        original_result = clf.classify(features)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            clf.save(tmp_path)
            clf2 = MoodClassifier.load(tmp_path)
            loaded_result = clf2.classify(features)
            assert loaded_result.mood == original_result.mood
            assert abs(loaded_result.confidence - original_result.confidence) < 1e-6
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_loaded_model_get_centroid(self):
        clf = _trained_lr()
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            tmp_path = Path(f.name)
        try:
            clf.save(tmp_path)
            clf2 = MoodClassifier.load(tmp_path)
            centroid = clf2.get_centroid(MoodLabel.CALM)
            assert len(centroid) == 23
        finally:
            tmp_path.unlink(missing_ok=True)


class TestMLP:
    def test_mlp_classify_returns_valid_result(self):
        clf = _trained_mlp()
        features = _SYNTHETIC_CENTROIDS[MoodLabel.ENERGIZED].copy()
        result = clf.classify(features)
        assert result.mood == MoodLabel.ENERGIZED

    def test_mlp_confidence_in_range(self):
        clf = _trained_mlp()
        result = clf.classify([0.5] * 23)
        assert 0.0 <= result.confidence <= 1.0
