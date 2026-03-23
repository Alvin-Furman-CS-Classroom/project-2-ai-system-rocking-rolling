"""Data models for Module 4: Mood Classification & Feature Mapping."""

from dataclasses import dataclass
from enum import Enum


class MoodLabel(str, Enum):
    CALM = "calm"
    ENERGIZED = "energized"
    HAPPY = "happy"
    SAD = "sad"
    INTENSE = "intense"
    CHILL = "chill"


@dataclass
class MoodClassification:
    mood: MoodLabel
    confidence: float  # probability of predicted class
    top_3_moods: list[tuple[MoodLabel, float]]  # (mood, probability) sorted descending


@dataclass
class TrainingExample:
    features: list[float]  # 23-dim normalized vector
    label: MoodLabel
    mbid: str | None = None


@dataclass
class EvalMetrics:
    accuracy: float
    f1_macro: float
    per_class: dict[str, dict[str, float]]  # {mood: {precision, recall, f1, support}}
    confusion_matrix: list[list[int]]
