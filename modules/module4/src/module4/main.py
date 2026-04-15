"""Training script for Module 4: Mood Classification.

Usage:
    python -m module4.main --from-db [--max-per-class N] [--model {lr,mlp,both,ensemble}] [--tune]
    python -m module4.main --synthetic [--max-per-class N] [--model both]
    python -m module4.main [--data-dir PATH] [--max-per-class N] [--model both]
"""

import argparse
import sys
from pathlib import Path

from .data_models import MoodLabel
from .feature_engineering import FEATURE_NAMES
from .mood_classifier import MoodClassifier
from .training_data import DATA_DIR, generate_synthetic_data, load_from_data_dir, load_from_db


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
    parser.add_argument("--max-per-class", type=int, default=200)
    parser.add_argument(
        "--model", choices=["lr", "mlp", "both", "ensemble"], default="both"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run GridSearchCV to find best hyperparameters before training",
    )

    # Data source — pick one
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--from-db",
        action="store_true",
        help="Build training data from Postgres (MusicBrainz) + AcousticBrainz API",
    )
    source.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic training data (for testing, no external deps)",
    )
    source.add_argument("--data-dir", type=Path, default=None)

    args = parser.parse_args()

    # Load training data from the chosen source
    if args.from_db:
        print("Building training data from Postgres + AcousticBrainz...")
        import logging
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        examples = load_from_db(max_per_class=args.max_per_class)

    elif args.synthetic:
        print(f"Generating {args.max_per_class * 6} synthetic examples...")
        examples = generate_synthetic_data(n_per_class=args.max_per_class)

    elif args.data_dir and args.data_dir != Path(""):
        print(f"Loading training data from {args.data_dir} ...")
        try:
            examples = load_from_data_dir(
                data_dir=args.data_dir,
                max_per_class=args.max_per_class,
            )
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Default: try DB, fall back to synthetic
        print("No data source specified. Trying Postgres, then synthetic fallback...")
        try:
            import logging
            logging.basicConfig(level=logging.INFO, format="%(message)s")
            examples = load_from_db(max_per_class=args.max_per_class)
        except Exception as e:
            print(f"DB unavailable ({e}), falling back to synthetic data...")
            examples = generate_synthetic_data(n_per_class=args.max_per_class)

    if not examples:
        print("No training examples found.", file=sys.stderr)
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
