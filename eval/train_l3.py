"""Train L3 candidates and evaluate the frozen choice once on held-out servers."""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, make_pipeline

from gateway.config import load as load_config
from gateway.l3 import ENCODER, MAX_TOKENS, REVISION, Scorer

from .l3_data import examples
from .mcptox_ingest import RAW, ROOT, load
from .split import OUT as SPLIT_PATH, SEED, load_split

FOLDS = 5
FP_LIMIT = 0.05


def classifier():
    return LogisticRegression(class_weight="balanced", solver="liblinear", random_state=SEED, max_iter=1000)


def text_model():
    features = FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
    ])
    return make_pipeline(features, classifier())


def mask(rows, predicate):
    return np.array([predicate(row) for row in rows], dtype=bool)


def operating_point(rows, scores):
    baseline_allowed = mask(rows, lambda row: not row.baseline_removed)
    benign = mask(rows, lambda row: row.label == 0) & baseline_allowed
    misses = mask(rows, lambda row: row.label == 1 and not row.l2_flag) & baseline_allowed
    # The threshold 1+epsilon includes the valid option of issuing no flags.
    thresholds = [*np.unique(scores), np.nextafter(1.0, 2.0)]
    best = max(
        (int((misses & (scores >= threshold)).sum()), -int((benign & (scores >= threshold)).sum()), threshold)
        for threshold in thresholds
        if (benign & (scores >= threshold)).sum() <= FP_LIMIT * benign.sum()
    )
    return float(best[2])


def results(rows, scores, threshold):
    pos = mask(rows, lambda row: row.label == 1)
    baseline_removed = mask(rows, lambda row: row.baseline_removed)
    l2_flag = mask(rows, lambda row: row.l2_flag)
    predicted = scores >= threshold
    tp = int((predicted & pos).sum())
    fp = int((predicted & ~pos).sum())
    fn = int((~predicted & pos).sum())
    return {
        "poisoned": int(pos.sum()), "authentic": int((~pos).sum()),
        "poisoned_flagged": tp, "authentic_flagged": fp,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "average_precision": float(average_precision_score(pos, scores)) if pos.any() else None,
        "direct_l2_misses": int((~l2_flag & pos).sum()),
        "direct_l2_misses_flagged": int((~l2_flag & pos & predicted).sum()),
        "baseline_poisoned_served": int((~baseline_removed & pos).sum()),
        "additional_poisoned_flagged": int((~baseline_removed & pos & predicted).sum()),
        "baseline_authentic_served": int((~baseline_removed & ~pos).sum()),
        "additional_authentic_flagged": int((~baseline_removed & ~pos & predicted).sum()),
        "combined_authentic_flagged": int(((baseline_removed | predicted) & ~pos).sum()),
    }


def train(output, device, text_only, description_only=False):
    from . import l3_semantic

    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(f"Choose a new output directory. An artifact already exists at {output}.")

    split = load_split()
    dataset = load()["servers"]
    k = load_config().k
    training = examples(dataset, split["train_servers"], k)
    labels = np.array([row.label for row in training])
    def model_text(row):
        return row.text.rsplit("\nSchema: ", 1)[0] if description_only else row.text

    views = {False: np.array([model_text(row) for row in training]),
             True: np.array([row.context_text for row in training])}
    groups = [row.server for row in training]
    folds = list(StratifiedGroupKFold(FOLDS, shuffle=True, random_state=SEED).split(views[False], labels, groups))

    candidates = []
    for kind, context in [("tfidf", False), ("frozen_e5", False),
                          ("finetuned_e5", False), ("frozen_e5", True)]:
        if (text_only or description_only) and kind != "tfidf":
            continue
        now = time.perf_counter()
        epochs = [1, 2] if kind == "finetuned_e5" else [0]
        oof = np.zeros((len(epochs), len(training)))
        texts = views[context]
        features = l3_semantic.features(texts, device) if kind == "frozen_e5" else texts
        for fold_number, (fit, validate) in enumerate(folds, start=1):
            if kind == "finetuned_e5":
                oof[:, validate] = l3_semantic.finetune(texts[fit], labels[fit], device, max(epochs), texts[validate])
            else:
                model = text_model() if kind == "tfidf" else classifier()
                model.fit(features[fit], labels[fit])
                oof[0, validate] = model.predict_proba(features[validate])[:, 1]
            print(f"{kind} context={context}: completed fold {fold_number}/{FOLDS}", file=sys.stderr, flush=True)
        for epoch, predictions in zip(epochs, oof, strict=True):
            threshold = operating_point(training, predictions)
            candidate = {"model": kind, "context": context, "epochs": epoch, "threshold": threshold,
                         "validation": results(training, predictions, threshold),
                         "elapsed_seconds": round(time.perf_counter() - now, 2)}
            candidates.append(candidate)
            print(json.dumps(candidate), flush=True)

    def rank(candidate):
        validation = candidate["validation"]
        # Prefer simpler/faster inference if two candidates achieve the same counts.
        complexity = {"tfidf": 0, "frozen_e5": 1, "finetuned_e5": 2}[candidate["model"]]
        return (validation["additional_poisoned_flagged"], -validation["additional_authentic_flagged"],
                -complexity, -candidate["context"], -candidate["epochs"])

    chosen = max(candidates, key=rank)
    kind = chosen["model"]
    texts = views[chosen["context"]]
    if kind == "finetuned_e5":
        l3_semantic.finetune(texts, labels, device, chosen["epochs"], output=output)
    else:
        if kind == "tfidf":
            model = text_model().fit(texts, labels)
        else:
            model = classifier().fit(l3_semantic.features(texts, device), labels)
            l3_semantic.save_encoder(output)
        joblib.dump(model, output / "classifier.joblib")
    manifest = {**chosen, "description_only": description_only, "seed": SEED, "folds": FOLDS, "fp_limit": FP_LIMIT, "k": k,
                "encoder": ENCODER if kind != "tfidf" else None,
                "encoder_revision": REVISION if kind != "tfidf" else None,
                "max_tokens": MAX_TOKENS, "scikit_learn": sklearn.__version__,
                "dataset_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                "split_sha256": hashlib.sha256(SPLIT_PATH.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # Held-out data does not participate in any choice above.
    heldout = examples(dataset, split["heldout_servers"], k)
    now = time.perf_counter()
    scorer = Scorer(output, device=device if kind != "tfidf" else "cpu")
    load_ms = (time.perf_counter() - now) * 1000
    test_texts = [row.context_text if chosen["context"] else model_text(row) for row in heldout]
    scores = np.asarray(scorer.probabilities(test_texts))
    threshold = chosen["threshold"]
    training_keys = {row.text for row in training}
    overlap = mask(heldout, lambda row: row.text in training_keys)
    template_keys = {template_key(row.text) for row in training}
    template_overlap = mask(heldout, lambda row: template_key(row.text) in template_keys)
    timings = {}
    for count in (1, 12):
        sample = test_texts[:count]
        repeats = []
        for _ in range(20):
            now = time.perf_counter()
            scorer.probabilities(sample)
            repeats.append((time.perf_counter() - now) * 1000)
        timings[count] = {"median_ms": float(np.median(repeats)), "p95_ms": float(np.percentile(repeats, 95))}
    report = {
        "chosen": manifest, "candidates": candidates,
        "heldout": results(heldout, scores, threshold),
        "heldout_by_server": grouped_results(heldout, scores, threshold, "server"),
        "heldout_by_risk": grouped_results(heldout, scores, threshold, "risk"),
        "exact_training_overlap": int(overlap.sum()),
        "heldout_without_exact_training_overlap": subset_results(heldout, scores, threshold, ~overlap),
        "normalized_training_overlap": int(template_overlap.sum()),
        "heldout_without_normalized_training_overlap": subset_results(heldout, scores, threshold, ~template_overlap),
        "inference": {"device": scorer.device, "load_ms": load_ms, "latency_by_tool_count": timings},
    }
    if kind != "tfidf":
        lengths = scorer.tokenizer(
            ["query: " + text for text in test_texts], truncation=False, verbose=False, return_length=True
        )["length"]
        report["heldout_inputs_exceeding_encoder_limit"] = sum(length > MAX_TOKENS for length in lengths)
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"chosen": kind, "heldout": report["heldout"], "artifact": str(output)}, indent=2))


def subset_results(rows, scores, threshold, selected):
    return results([row for row, keep in zip(rows, selected, strict=True) if keep], scores[selected], threshold)


def template_key(text):
    """A conservative overlap check that ignores case, whitespace, and numeric values."""
    return " ".join(re.sub(r"\d+", "#", text.casefold()).split())


def grouped_results(rows, scores, threshold, field):
    return {
        value: subset_results(rows, scores, threshold, mask(rows, lambda row: getattr(row, field) == value))
        for value in sorted({getattr(row, field) for row in rows})
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "var" / "l3")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--text-only", action="store_true")
    parser.add_argument("--description-only", action="store_true", help="TF–IDF diagnostic using name and description")
    args = parser.parse_args()
    train(args.output, args.device, args.text_only, args.description_only)


if __name__ == "__main__":
    main()
