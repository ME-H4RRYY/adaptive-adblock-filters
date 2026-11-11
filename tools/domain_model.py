"""Dependency-free, character n-gram multinomial Naive Bayes for domain labels."""
from __future__ import annotations

import math
import re
import hashlib
from collections import Counter


def features(domain: str) -> set[str]:
    labels = [label.lower() for label in domain.split(".") if label]
    result: set[str] = set()
    for label in labels:
        padded = f"^{label}$"
        for width in (2, 3, 4):
            result.update(padded[i:i + width] for i in range(max(0, len(padded) - width + 1)))
        if label in {"ad", "ads", "advert", "track", "tracker", "analytics", "pixel", "metrics", "banner", "promo"}:
            result.add(f"word:{label}")
    return result


def _split_samples(samples: set[str]) -> tuple[set[str], set[str]]:
    ordered = sorted(samples, key=lambda domain: hashlib.sha256(domain.encode("ascii")).hexdigest())
    holdout = set(ordered[::5])
    return samples - holdout, holdout


def train_model(positive: set[str], negative: set[str]) -> tuple[dict, dict]:
    overlap = positive & negative
    positive = positive - overlap
    negative = negative - overlap
    total_positive, total_negative = len(positive), len(negative)
    if min(total_positive, total_negative) < 50:
        return {"status": "insufficient_labels", "positiveCount": total_positive, "negativeCount": total_negative}, {
            "status": "insufficient_labels", "overlapRemoved": len(overlap),
        }

    # Balance class priors and cap CI work while sampling deterministically.
    sample_size = min(12000, total_positive, total_negative)
    positive = set(sorted(positive, key=lambda domain: hashlib.sha256(("p:" + domain).encode("ascii")).hexdigest())[:sample_size])
    negative = set(sorted(negative, key=lambda domain: hashlib.sha256(("n:" + domain).encode("ascii")).hexdigest())[:sample_size])

    train_pos, test_pos = _split_samples(positive)
    train_neg, test_neg = _split_samples(negative)
    # Keep both labels represented in both partitions for a meaningful evaluation.
    if len(train_pos) < 5 or len(train_neg) < 5 or not test_pos or not test_neg:
        return {"status": "insufficient_split", "positiveCount": len(positive), "negativeCount": len(negative)}, {
            "status": "insufficient_split", "overlapRemoved": len(overlap),
        }

    class_counts = {1: Counter(), 0: Counter()}
    totals = Counter()
    for label, samples in ((1, train_pos), (0, train_neg)):
        for domain in samples:
            for feature in features(domain):
                class_counts[label][feature] += 1
                totals[label] += 1
    vocabulary = set(class_counts[1]) | set(class_counts[0])
    vocabulary_size = max(1, len(vocabulary))
    model = {
        "status": "ready",
        "algorithm": "multinomial-naive-bayes-char-ngram",
        "version": 1,
        "positiveCount": total_positive,
        "negativeCount": total_negative,
        "trainingSampleSizePerClass": sample_size,
        "overlapRemoved": len(overlap),
        "logPriorPositive": math.log(len(train_pos) / (len(train_pos) + len(train_neg))),
        "logPriorNegative": math.log(len(train_neg) / (len(train_pos) + len(train_neg))),
        "vocabularySize": vocabulary_size,
        "positiveTokenTotal": totals[1],
        "negativeTokenTotal": totals[0],
        "features": {
            feature: [
                math.log((class_counts[1][feature] + 1) / (totals[1] + vocabulary_size)),
                math.log((class_counts[0][feature] + 1) / (totals[0] + vocabulary_size)),
            ]
            for feature in vocabulary
        },
    }
    probabilities = [(score_domain(model, domain), 1) for domain in test_pos]
    probabilities.extend((score_domain(model, domain), 0) for domain in test_neg)
    predictions = [(probability >= 0.5, label) for probability, label in probabilities]
    tp = sum(predicted and label == 1 for predicted, label in predictions)
    tn = sum(not predicted and label == 0 for predicted, label in predictions)
    fp = sum(predicted and label == 0 for predicted, label in predictions)
    fn = sum(not predicted and label == 1 for predicted, label in predictions)
    metrics = {
        "status": "evaluated",
        "holdoutExamples": len(probabilities),
        "accuracy": round((tp + tn) / max(1, len(probabilities)), 4),
        "precision": round(tp / max(1, tp + fp), 4),
        "recall": round(tp / max(1, tp + fn), 4),
        "truePositives": tp,
        "trueNegatives": tn,
        "falsePositives": fp,
        "falseNegatives": fn,
        "overlapRemoved": len(overlap),
    }
    return model, metrics


def score_domain(model: dict, domain: str) -> float:
    if model.get("status") != "ready":
        return 0.0
    features_map = model["features"]
    positive = model["logPriorPositive"]
    negative = model["logPriorNegative"]
    for feature in features(domain):
        log_probabilities = features_map.get(feature)
        if log_probabilities:
            positive += log_probabilities[0]
            negative += log_probabilities[1]
    delta = max(-700.0, min(700.0, negative - positive))
    return 1.0 / (1.0 + math.exp(delta))


def exact_domain_label(line: str) -> tuple[str, int] | None:
    line = line.strip()
    label = 1
    if line.startswith("@@"):
        label = 0
        line = line[2:]
    match = re.fullmatch(r"\|\|([a-z0-9.-]+)(\^|/)(?:[^$]*)?(?:\$(.*))?", line)
    if not match:
        return None
    domain = match.group(1).lower().rstrip(".")
    if not domain or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in domain.split(".")):
        return None
    if label == 1 and match.group(2) != "^":
        return None
    options = set((match.group(3) or "").split(",")) - {""}
    supported = {"third-party", "script", "image", "stylesheet", "font", "media", "xmlhttprequest", "subdocument", "ping", "object", "other"}
    if any(option.startswith(("~", "redirect", "removeparam", "badfilter", "csp", "permissions", "method=")) for option in options):
        return None
    if label == 1 and (any(option.startswith("domain=") for option in options) or options - supported):
        return None
    if label == 0 and any(option not in supported and not option.startswith("domain=") for option in options):
        return None
    return domain, label
