#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 ME-H4RRYY
"""Compile a conservative, domain-only subset of EasyList/EasyPrivacy to DNR data."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from domain_model import exact_domain_label, score_domain, train_model

SOURCES = {
    "EasyList": "https://easylist.to/easylist/easylist.txt",
    "EasyPrivacy": "https://easylist.to/easylist/easyprivacy.txt",
}
COMPILER_VERSION = 2
DOMAIN_RULE = re.compile(r"^\|\|([a-z0-9.-]+)\^(?:\$(.*))?$")
ALLOWED_OPTIONS = {"third-party", "script", "image", "stylesheet", "font", "media", "xmlhttprequest", "subdocument", "ping", "object", "other"}
RESOURCE_TYPES = {
    "script": "script", "image": "image", "stylesheet": "stylesheet", "font": "font",
    "media": "media", "xmlhttprequest": "xmlhttprequest", "subdocument": "sub_frame",
    "ping": "ping", "object": "object", "other": "other",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "AdaptiveAdBlocker-FilterCompiler/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        content = response.read(32 * 1024 * 1024 + 1)
    if len(content) > 32 * 1024 * 1024:
        raise ValueError(f"Filter source exceeds the 32 MiB limit: {url}")
    return content


def compile_lines(lines: list[str]) -> set[str]:
    domains: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("!", "[", "#", "@@", "/")):
            continue
        match = DOMAIN_RULE.fullmatch(line)
        if not match:
            continue
        domain = match.group(1).lower().rstrip(".")
        if len(domain) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in domain.split(".")):
            continue
        options = set((match.group(2) or "").split(",")) - {""}
        if any(option.startswith(("~", "domain=", "redirect", "removeparam", "badfilter", "csp", "permissions", "method=")) for option in options):
            continue
        if options - ALLOWED_OPTIONS:
            continue
        # This compact feed intentionally limits domain rules to third-party requests.
        # It avoids converting a broad host rule into a first-party site breakage rule.
        domains.add(domain)
    return domains


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("extension/remote-rules.json"))
    parser.add_argument("--input", type=Path, action="append", help="Local filter file, for repeatable/offline builds")
    args = parser.parse_args()
    try:
        sources: dict[str, str] = {}
        source_provenance: list[dict[str, object]] = []
        files = args.input or []
        if files:
            for path in files:
                raw = path.read_bytes()
                sources[path.name] = raw.decode("utf-8", errors="replace")
                source_provenance.append({
                    "name": path.name,
                    "origin": "local input file",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "sizeBytes": len(raw),
                })
        else:
            for name, url in SOURCES.items():
                raw = fetch(url)
                sources[name] = raw.decode("utf-8", errors="replace")
                source_provenance.append({
                    "name": name,
                    "url": url,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "sizeBytes": len(raw),
                })
        merged: set[str] = set()
        positive_labels: set[str] = set()
        negative_labels: set[str] = set()
        counts: dict[str, int] = {}
        for name, contents in sources.items():
            lines = contents.splitlines()
            domains = compile_lines(lines)
            for line in lines:
                labeled = exact_domain_label(line)
                if labeled:
                    (positive_labels if labeled[1] else negative_labels).add(labeled[0])
            counts[name] = len(domains)
            merged.update(domains)
        if len(merged) < 50:
            raise ValueError(f"Only {len(merged)} usable domains were found; refusing to publish an empty update.")
        if len(merged) > 250_000:
            raise ValueError(f"{len(merged)} candidates exceed the compiler's hard safety limit.")
        model, metrics = train_model(positive_labels, negative_labels)
        if model.get("status") == "ready":
            scores = [(score_domain(model, domain), domain) for domain in merged]
            ml_summary = {
                "status": "ready",
                "algorithm": model["algorithm"],
                "positiveTrainingExamples": model["positiveCount"],
                "negativeTrainingExamples": model["negativeCount"],
                "holdout": metrics,
                "candidateCount": len(merged),
                "retainedCount": len(merged),
                "omittedForRuleLimit": 0,
                "lowConfidenceCandidates": [domain for score, domain in sorted(scores)[:20]],
                "decisionRole": "advisory quality review only; published filter rules remain authoritative",
            }
        else:
            ml_summary = {
                "status": model.get("status", "unavailable"),
                "positiveTrainingExamples": model.get("positiveCount", 0),
                "negativeTrainingExamples": model.get("negativeCount", 0),
                "holdout": metrics,
                "candidateCount": len(merged),
                "retainedCount": len(merged),
                "omittedForRuleLimit": 0,
                "decisionRole": "advisory; maintained filter rules remain authoritative",
            }
        generated_at = datetime.now(timezone.utc).isoformat()
        provenance = {
            "compilerVersion": COMPILER_VERSION,
            "generatedAt": generated_at,
            "sources": source_provenance,
        }
        artifact = {
            "schemaVersion": 1,
            "generatedAt": generated_at,
            "sources": list(SOURCES.values()) if not files else [str(path) for path in files],
            "sourceProvenance": provenance,
            "sourceAttribution": "EasyList authors (https://easylist.to/)",
            "sourceDomainCounts": counts,
            "mlReview": ml_summary,
            "domains": sorted(merged),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        model_path = args.output.with_name("domain-model.json")
        model_path.write_text(json.dumps({"model": model, "evaluation": metrics, "sourceProvenance": provenance}, indent=2) + "\n", encoding="utf-8")
        print(f"ML review: {ml_summary['status']} ({model.get('positiveCount', 0)} positive, {model.get('negativeCount', 0)} negative labels)")
        print(f"Compiled {len(merged)} domains from {len(sources)} source(s) into {args.output}")
        return 0
    except Exception as error:  # Fail closed: the workflow must not publish partial data.
        print(f"Filter compilation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
