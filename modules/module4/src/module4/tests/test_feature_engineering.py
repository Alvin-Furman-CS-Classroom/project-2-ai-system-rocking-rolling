"""Tests for feature_engineering.py."""

import pytest
from module1.data_models import TrackFeatures

from module4.data_models import MoodLabel
from module4.feature_engineering import (
    FEATURE_DIM,
    FEATURE_NAMES,
    extract_features,
    features_to_track,
)


def _make_track(**kwargs) -> TrackFeatures:
    defaults = dict(
        mbid="test-mbid",
        bpm=120.0,
        onset_rate=5.0,
        energy_low=0.3,
        energy_mid_low=0.4,
        energy_mid_high=0.4,
        energy_high=0.2,
        average_loudness=0.7,
        dynamic_complexity=4.0,
        dissonance=0.3,
        spectral_centroid=4000.0,
        mfcc=[
            -300.0,
            10.0,
            -5.0,
            8.0,
            -3.0,
            6.0,
            -2.0,
            4.0,
            -1.0,
            3.0,
            -1.0,
            2.0,
            -0.5,
        ],
    )
    defaults.update(kwargs)
    return TrackFeatures(**defaults)


class TestExtractFeatures:
    def test_returns_list_of_floats(self):
        track = _make_track()
        result = extract_features(track)
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_length_is_23(self):
        track = _make_track()
        result = extract_features(track)
        assert len(result) == FEATURE_DIM == 23

    def test_all_values_in_0_1(self):
        track = _make_track()
        result = extract_features(track)
        for i, v in enumerate(result):
            assert 0.0 <= v <= 1.0, f"Feature {FEATURE_NAMES[i]} out of range: {v}"

    def test_bpm_none_gives_half(self):
        track = _make_track(bpm=None)
        result = extract_features(track)
        assert result[0] == 0.5

    def test_mfcc_none_gives_all_half(self):
        track = _make_track(mfcc=None)
        result = extract_features(track)
        for i in range(10, 23):
            assert result[i] == 0.5, f"MFCC index {i} expected 0.5, got {result[i]}"

    def test_bpm_50_maps_to_zero(self):
        track = _make_track(bpm=50.0)
        result = extract_features(track)
        assert abs(result[0] - 0.0) < 1e-6

    def test_bpm_220_maps_to_one(self):
        track = _make_track(bpm=220.0)
        result = extract_features(track)
        assert abs(result[0] - 1.0) < 1e-6

    def test_bpm_135_maps_to_approx_half(self):
        track = _make_track(bpm=135.0)
        result = extract_features(track)
        # 135 = 50 + 85; 170/2 = 85 → exactly 0.5
        assert abs(result[0] - 0.5) < 1e-3

    def test_average_loudness_none_gives_half(self):
        track = _make_track(average_loudness=None)
        result = extract_features(track)
        assert result[5] == 0.5

    def test_dissonance_none_gives_half(self):
        track = _make_track(dissonance=None)
        result = extract_features(track)
        assert result[7] == 0.5

    def test_spectral_centroid_none_gives_half(self):
        track = _make_track(spectral_centroid=None)
        result = extract_features(track)
        assert result[8] == 0.5

    def test_dynamic_complexity_none_gives_half(self):
        track = _make_track(dynamic_complexity=None)
        result = extract_features(track)
        assert result[6] == 0.5


class TestFeatureNames:
    def test_feature_names_length_is_23(self):
        assert len(FEATURE_NAMES) == 23

    def test_feature_names_are_strings(self):
        assert all(isinstance(n, str) for n in FEATURE_NAMES)

    def test_feature_dim_constant(self):
        assert FEATURE_DIM == 23


class TestFeaturesToTrack:
    def test_returns_track_features(self):
        vector = [0.5] * 23
        track = features_to_track(vector)
        assert isinstance(track, TrackFeatures)

    def test_bpm_populated(self):
        vector = [0.5] * 23
        track = features_to_track(vector)
        # 0.5 * 170 + 50 = 135
        assert abs(track.bpm - 135.0) < 1e-3

    def test_mood_label_in_mbid(self):
        vector = [0.5] * 23
        track = features_to_track(vector, mood=MoodLabel.CALM)
        assert "calm" in track.mbid

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            features_to_track([0.5] * 10)
