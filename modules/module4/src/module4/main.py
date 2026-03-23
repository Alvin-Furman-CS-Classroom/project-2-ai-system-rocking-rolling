"""Training script for Module 4: Mood Classification.

Usage:
    python -m module4.main [--data-dir PATH] [--max-per-class N] [--model {lr,mlp,both,ensemble}] [--tune]
"""

import argparse
import sys
from pathlib import Path

from .data_models import MoodLabel
from .feature_engineering import FEATURE_NAMES
from .mood_classifier import MoodClassifier
from .training_data import DATA_DIR, load_from_data_dir


def _print_metrics(metrics, model_name: str) -> None:
    print(f"\n--- {model_name} ---")
    print(f"Test accuracy: {metrics.accuracy:.3f}, F1-macro: {metrics.f1_macro:.3f}")
    print(f"{'':>12} {'precision':>10} {'recall':>8} {'f1':>8} {'support':>8}")
    for mood_name, m in sorted(metrics.per_class.items()):
        print(
            f"  {mood_name:<10}  {m['precision']:>9.2f}  {m['recall']:>7.2f}  {m['f1']:>7.2f}  {int(m['support']):>7}"
        )


def _print_lr_feature_importance(clf: MoodClassifier) -> None:
    """Print top-5 features by absolute coefficient magnitude for each class."""
    from sklearn.linear_model import LogisticRegression

    model = clf._model
    if not isinstance(model, LogisticRegression):
        return

    classes = clf._label_encoder.classes_
    coef = model.coef_  # shape (n_classes, n_features)

    print("\nTop features per class (logistic regression coefficients):")
    for i, cls_name in enumerate(classes):
        abs_coef = abs(coef[i])
        top5_idx = abs_coef.argsort()[::-1][:5]
        parts = [f"{FEATURE_NAMES[j]} ({coef[i][j]:.2f})" for j in top5_idx]
        print(f"  {cls_name}: {', '.join(parts)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train mood classifier")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--max-per-class", type=int, default=1000)
    parser.add_argument(
        "--model", choices=["lr", "mlp", "both", "ensemble"], default="both"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run GridSearchCV to find best hyperparameters before training",
    )
    args = parser.parse_args()

    print(f"Loading training data from {args.data_dir} ...")
    try:
        examples = load_from_data_dir(
            data_dir=args.data_dir,
            max_per_class=args.max_per_class,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not examples:
        print("No training examples found. Check the data directory.", file=sys.stderr)
        sys.exit(1)

    # Class distribution
    from collections import Counter

    counts = Counter(e.label.value for e in examples)
    dist_str = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"Loaded {len(examples)} examples ({dist_str})")

    best_model: MoodClassifier | None = None
    best_f1 = -1.0
    best_name = ""

    if args.model in ("lr", "both"):
        clf_lr = MoodClassifier(model_type="logistic_regression")
        if args.tune:
            clf_lr.tune_hyperparameters(examples)
        metrics_lr = clf_lr.train(examples, n_cv_folds=5)
        _print_metrics(metrics_lr, "Logistic Regression (5-fold CV)")
        _print_lr_feature_importance(clf_lr)
        if metrics_lr.f1_macro > best_f1:
            best_f1 = metrics_lr.f1_macro
            best_model = clf_lr
            best_name = "Logistic Regression"

    if args.model in ("mlp", "both"):
        clf_mlp = MoodClassifier(model_type="mlp")
        if args.tune:
            clf_mlp.tune_hyperparameters(examples)
        metrics_mlp = clf_mlp.train(examples, n_cv_folds=5)
        _print_metrics(metrics_mlp, "MLP (256→128, 5-fold CV)")
        if metrics_mlp.f1_macro > best_f1:
            best_f1 = metrics_mlp.f1_macro
            best_model = clf_mlp
            best_name = "MLP"

    if args.model == "ensemble":
        clf_ens = MoodClassifier(model_type="ensemble")
        metrics_ens = clf_ens.train(examples, n_cv_folds=5)
        _print_metrics(metrics_ens, "Ensemble (LR + MLP, 5-fold CV)")
        if metrics_ens.f1_macro > best_f1:
            best_f1 = metrics_ens.f1_macro
            best_model = clf_ens
            best_name = "Ensemble"

    if args.model in ("both", "ensemble"):
        print(f"\nBest model: {best_name} (F1-macro: {best_f1:.3f})")

    # Save best model
    model_path = Path(__file__).parent.parent.parent / "models" / "mood_classifier.pkl"
    if best_model is not None:
        best_model.save(model_path)
        print(f"\nSaved best model to {model_path}")

    # Demo: classify using centroid tracks
    if best_model is not None:
        print("\n--- Demo: mood centroids ---")
        for mood in MoodLabel:
            centroid_track = best_model.get_centroid_track(mood)
            result = best_model.classify_track(centroid_track)
            top3_str = ", ".join(f"{m.value}={p:.2f}" for m, p in result.top_3_moods)
            print(
                f"  {mood.value:<10} → predicted: {result.mood.value:<10} conf={result.confidence:.2f}  top3=[{top3_str}]"
            )


if __name__ == "__main__":
    main()
