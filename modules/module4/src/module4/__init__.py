"""Module 4: Mood Classification & Feature Mapping for Wave Guide.

This module provides supervised learning to map lowlevel audio features
to abstract mood labels (Calm, Energized, Happy, Sad, Intense, Chill).

Example:
    from module4 import MoodClassifier, MoodLabel
    from module4.training_data import generate_synthetic_data

    examples = generate_synthetic_data(n_per_class=200)
    clf = MoodClassifier()
    metrics = clf.train(examples)
    print(f"Accuracy: {metrics.accuracy:.1%}")

    clf.save("models/mood_classifier.pkl")
    clf2 = MoodClassifier.load("models/mood_classifier.pkl")
"""

from .data_models import EvalMetrics, MoodClassification, MoodLabel, TrainingExample
from .mood_classifier import MoodClassifier

__all__ = [
    "MoodClassifier",
    "MoodLabel",
    "MoodClassification",
    "TrainingExample",
    "EvalMetrics",
]
