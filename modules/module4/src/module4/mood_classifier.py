"""Mood classifier using scikit-learn models."""

import pickle
from pathlib import Path
from typing import Literal

import numpy as np
from tqdm import tqdm
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
    confusion_matrix,
)
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_validate,
    GridSearchCV,
)
from sklearn.pipeline import Pipeline

from module1.data_models import TrackFeatures

from .data_models import EvalMetrics, MoodClassification, MoodLabel, TrainingExample
from .feature_engineering import extract_features, features_to_track


class MoodClassifier:
    """Supervised mood classifier mapping lowlevel audio features → MoodLabel."""

    def __init__(
        self,
        model_type: Literal["logistic_regression", "mlp", "ensemble"] = "logistic_regression",
    ):
        self._model_type = model_type
        self._scaler = StandardScaler()
        self._label_encoder = LabelEncoder()
        self._centroids: dict[str, list[float]] = {}
        self._is_trained = False

        if model_type == "logistic_regression":
            self._model = LogisticRegression(
                max_iter=1000,
                C=1.0,
                solver="lbfgs",
                class_weight="balanced",
            )
        elif model_type == "mlp":
            self._model = MLPClassifier(
                hidden_layer_sizes=(256, 128),
                activation="relu",
                max_iter=500,
                early_stopping=True,
                random_state=42,
            )
        else:
            from sklearn.ensemble import VotingClassifier

            _lr = LogisticRegression(
                max_iter=1000,
                C=1.0,
                solver="lbfgs",
                class_weight="balanced",
            )
            _mlp = MLPClassifier(
                hidden_layer_sizes=(256, 128),
                activation="relu",
                max_iter=500,
                early_stopping=True,
                random_state=42,
            )
            self._model = VotingClassifier(
                estimators=[("lr", _lr), ("mlp", _mlp)],
                voting="soft",
            )

    def train(
        self,
        examples: list[TrainingExample],
        test_split: float = 0.2,
        random_seed: int = 42,
        n_cv_folds: int = 1,
    ) -> EvalMetrics:
        """Stratified train/test split → StandardScaler → fit model.

        Computes centroids from training set. Returns EvalMetrics on held-out test set.
        When n_cv_folds > 1, uses StratifiedKFold cross-validation for a more reliable
        accuracy estimate, then refits on the full dataset for deployment.
        """
        X = np.array([e.features for e in examples], dtype=float)
        y_raw = [e.label.value for e in examples]
        y = self._label_encoder.fit_transform(y_raw)

        if n_cv_folds > 1:
            return self._train_cv(X, y, n_cv_folds, random_seed)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, random_state=random_seed, stratify=y
        )

        label = self._model_type.replace("_", " ").title()
        steps = ["scaling", "fitting", "centroids", "evaluating"]
        with tqdm(steps, desc=f"Training {label}", unit="step", leave=False) as pbar:
            pbar.set_description(f"Training {label} — scaling")
            X_train_scaled = self._scaler.fit_transform(X_train)
            X_test_scaled = self._scaler.transform(X_test)
            pbar.update(1)

            pbar.set_description(f"Training {label} — fitting")
            self._model.fit(X_train_scaled, y_train)
            self._is_trained = True
            pbar.update(1)

            pbar.set_description(f"Training {label} — centroids")
            classes = self._label_encoder.classes_
            for i, cls_name in enumerate(classes):
                mask = y_train == i
                if mask.any():
                    self._centroids[cls_name] = X_train[mask].mean(axis=0).tolist()
                else:
                    self._centroids[cls_name] = [0.5] * X_train.shape[1]
            pbar.update(1)

            pbar.set_description(f"Training {label} — evaluating")
            metrics = self._compute_metrics(X_test_scaled, y_test)
            pbar.update(1)

        return metrics

    def _train_cv(
        self, X: np.ndarray, y: np.ndarray, n_cv_folds: int, random_seed: int
    ) -> EvalMetrics:
        """Cross-validate, then refit on full data for deployment."""
        label = self._model_type.replace("_", " ").title()
        pipe = Pipeline([("scaler", StandardScaler()), ("clf", self._model)])
        skf = StratifiedKFold(n_splits=n_cv_folds, shuffle=True, random_state=random_seed)

        print(f"Training {label} — {n_cv_folds}-fold cross-validation...")
        cv_results = cross_validate(
            pipe, X, y, cv=skf, scoring=["accuracy", "f1_macro"]
        )
        mean_acc = float(np.mean(cv_results["test_accuracy"]))
        mean_f1 = float(np.mean(cv_results["test_f1_macro"]))

        # Refit on full data for deployment
        print(f"Training {label} — refitting on full dataset...")
        X_scaled = self._scaler.fit_transform(X)
        self._model.fit(X_scaled, y)
        self._is_trained = True

        classes = self._label_encoder.classes_
        for i, cls_name in enumerate(classes):
            mask = y == i
            if mask.any():
                self._centroids[cls_name] = X[mask].mean(axis=0).tolist()
            else:
                self._centroids[cls_name] = [0.5] * X.shape[1]

        per_class = {
            cls: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0.0}
            for cls in classes
        }
        return EvalMetrics(
            accuracy=mean_acc,
            f1_macro=mean_f1,
            per_class=per_class,
            confusion_matrix=[],
        )

    def tune_hyperparameters(
        self,
        examples: list[TrainingExample],
        n_folds: int = 3,
        random_seed: int = 42,
    ) -> None:
        """Run GridSearchCV and update self._model with the best found parameters.

        Call this before train() to find better hyperparameters for the current dataset.
        Not supported for the ensemble model type.
        """
        if self._model_type == "ensemble":
            raise ValueError("tune_hyperparameters is not supported for ensemble models.")

        X = np.array([e.features for e in examples], dtype=float)
        y = self._label_encoder.fit_transform([e.label.value for e in examples])

        pipe = Pipeline([("scaler", StandardScaler()), ("clf", self._model)])

        if self._model_type == "logistic_regression":
            param_grid: dict = {"clf__C": [0.01, 0.1, 1.0, 10.0, 100.0]}
        else:
            param_grid = {
                "clf__hidden_layer_sizes": [(64,), (64, 32), (128, 64), (128, 64, 32)],
                "clf__alpha": [0.0001, 0.001, 0.01],
            }

        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_seed)
        gs = GridSearchCV(pipe, param_grid, cv=cv, scoring="f1_macro", n_jobs=-1)
        print(f"Tuning hyperparameters ({n_folds}-fold CV)...")
        gs.fit(X, y)

        best_params = {k.replace("clf__", ""): v for k, v in gs.best_params_.items()}
        print(f"Best params: {best_params} (f1_macro={gs.best_score_:.3f})")
        self._model.set_params(**best_params)
        # Reset label encoder so train() can refit cleanly
        self._label_encoder = LabelEncoder()

    def classify(self, features: list[float]) -> MoodClassification:
        """Predict mood label + per-class probabilities from a 23-dim feature vector."""
        if not self._is_trained:
            raise RuntimeError("Classifier has not been trained. Call train() first.")

        X = np.array([features], dtype=float)
        X_scaled = self._scaler.transform(X)

        proba = self._model.predict_proba(X_scaled)[0]
        pred_idx = int(np.argmax(proba))
        predicted_label = MoodLabel(self._label_encoder.classes_[pred_idx])
        confidence = float(proba[pred_idx])

        # Build top-3 list
        top_indices = np.argsort(proba)[::-1][:3]
        top_3 = [
            (MoodLabel(self._label_encoder.classes_[i]), float(proba[i]))
            for i in top_indices
        ]

        return MoodClassification(
            mood=predicted_label,
            confidence=confidence,
            top_3_moods=top_3,
        )

    def classify_track(self, track: TrackFeatures) -> MoodClassification:
        """Extract features from TrackFeatures then classify."""
        return self.classify(extract_features(track))

    def get_centroid(self, mood: MoodLabel) -> list[float]:
        """Return mean feature vector of training examples for this mood class."""
        if not self._is_trained:
            raise RuntimeError("Classifier has not been trained. Call train() first.")
        centroid = self._centroids.get(mood.value)
        if centroid is None:
            raise ValueError(f"No centroid found for mood: {mood}")
        return centroid

    def get_centroid_track(self, mood: MoodLabel) -> TrackFeatures:
        """Return a TrackFeatures instance at the mood's centroid."""
        return features_to_track(self.get_centroid(mood), mood)

    def evaluate(self, examples: list[TrainingExample]) -> EvalMetrics:
        """Evaluate on a list of examples."""
        if not self._is_trained:
            raise RuntimeError("Classifier has not been trained. Call train() first.")

        X = np.array([e.features for e in examples], dtype=float)
        y_raw = [e.label.value for e in examples]
        y = self._label_encoder.transform(y_raw)
        X_scaled = self._scaler.transform(X)

        return self._compute_metrics(X_scaled, y)

    def _compute_metrics(self, X_scaled: np.ndarray, y_true: np.ndarray) -> EvalMetrics:
        y_pred = self._model.predict(X_scaled)

        accuracy = float(accuracy_score(y_true, y_pred))
        f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

        classes = self._label_encoder.classes_
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=list(range(len(classes))), zero_division=0
        )

        per_class: dict[str, dict[str, float]] = {}
        for i, cls_name in enumerate(classes):
            per_class[cls_name] = {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": float(support[i]),
            }

        cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes)))).tolist()

        return EvalMetrics(
            accuracy=accuracy,
            f1_macro=f1_macro,
            per_class=per_class,
            confusion_matrix=cm,
        )

    def save(self, path: str | Path) -> None:
        """Pickle model, scaler, encoder, and centroids to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_type": self._model_type,
            "model": self._model,
            "scaler": self._scaler,
            "label_encoder": self._label_encoder,
            "centroids": self._centroids,
            "is_trained": self._is_trained,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, path: str | Path) -> "MoodClassifier":
        """Load a trained MoodClassifier from a pickle file."""
        with open(path, "rb") as f:
            payload = pickle.load(f)
        obj = cls.__new__(cls)
        obj._model_type = payload["model_type"]
        obj._model = payload["model"]
        obj._scaler = payload["scaler"]
        obj._label_encoder = payload["label_encoder"]
        obj._centroids = payload["centroids"]
        obj._is_trained = payload["is_trained"]
        return obj
