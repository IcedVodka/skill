#!/usr/bin/env python3
"""score_repo.py — compute a composite quality score for a GitHub repo.

Implements the rubric documented in references/scoring-rubric.md. Returns a
0-100 score plus a per-signal breakdown so the caller can show evidence and
catch fake-star inflation, abandoned-but-popular projects, and AI slop.

Usage:
    python score_repo.py owner/repo [--keywords kw1,kw2,...]

Requires `gh` CLI authenticated (or GITHUB_PERSONAL_ACCESS_TOKEN in env).
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def gh(args: list[str]) -> str:
    """Shell to gh CLI; raise on non-zero."""
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def gh_json(args: list[str]) -> Any:
    return json.loads(gh(args))


def days_since(iso: str) -> int:
    if not iso:
        return 9999
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


@dataclass
class Breakdown:
    recency: float = 0.0
    issue_health: float = 0.5
    activity: float = 0.0
    health_files: float = 0.5
    scorecard: float | None = None
    relevance: float = 0.0
    fork_ratio: float = 0.0
    watcher_ratio: float = 0.0
    age_growth_multiplier: float = 1.0
    popularity: float = 0.0
    slop_penalty: float = 0.0
    slop_notes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def fetch_issue_counts(owner_repo: str) -> tuple[int, int]:
    """Return (closed, open) issue counts. Defaults to (0, 0) on error."""
    try:
        closed = gh_json([
            "api",
            f"search/issues?q=repo:{owner_repo}+is:issue+is:closed&per_page=1",
        ])["total_count"]
        open_ = gh_json([
            "api",
            f"search/issues?q=repo:{owner_repo}+is:issue+is:open&per_page=1",
        ])["total_count"]
        return closed, open_
    except Exception:
        return 0, 0


def fetch_tree(owner_repo: str, branch: str) -> list[str]:
    """Return list of file paths in the default branch (lowercased)."""
    try:
        data = gh_json([
            "api",
            f"repos/{owner_repo}/git/trees/{branch}?recursive=1",
        ])
        return [t["path"].lower() for t in data.get("tree", [])]
    except Exception:
        return []


def fetch_readme(owner_repo: str) -> str:
    """Return the decoded README contents, or empty string on failure."""
    try:
        out = gh(["api", f"repos/{owner_repo}/readme", "--jq", ".content"]).strip()
        return base64.b64decode(out).decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_scorecard(owner_repo: str) -> float | None:
    """Return OpenSSF Scorecard aggregate (0-10) or None if not in dataset."""
    url = f"https://api.securityscorecards.dev/projects/github.com/{owner_repo}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return float(json.loads(r.read()).get("score"))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError):
        return None


def health_from_tree(files: list[str]) -> float:
    has_readme = any(f.startswith("readme") for f in files)
    has_license = any(f.startswith(("license", "licence", "copying")) for f in files)
    has_ci = any(
        f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))
        for f in files
    )
    has_tests = any(
        f.startswith(("test/", "tests/", "spec/", "__tests__/"))
        or "_test." in f
        or ".test." in f
        or ".spec." in f
        for f in files
    )
    docs = 0.5 * (0.5 * has_readme + 0.5 * has_license)
    ci_tests = 0.5 * (0.5 * has_ci + 0.5 * has_tests)
    return docs + ci_tests


def relevance_from_meta(
    description: str, topics: list[str], readme: str, keywords: list[str]
) -> float:
    if not keywords:
        return 0.5  # neutral when no keywords passed
    kw_lower = [k.lower() for k in keywords]
    topic_match = 1.0 if any(k in topics for k in kw_lower) else 0.0
    desc_match = 1.0 if any(k in description for k in kw_lower) else 0.0
    if readme:
        rl = readme.lower()
        hits = sum(rl.count(k) for k in kw_lower)
        density = hits / max(1, len(rl.split()))
        readme_match = min(1.0, density * 200)  # ~0.5% density saturates
    else:
        readme_match = 0.0
    return 0.4 * topic_match + 0.3 * desc_match + 0.3 * readme_match


SUPERLATIVES = (
    "blazing-fast", "blazing fast", "revolutionary", "the best",
    "next-generation", "cutting-edge", "world's first", "the ultimate",
    "lightning-fast", "lightning fast",
)
LLM_TICS = ("it's worth noting", "in essence", "delve into", "delving into")


def slop_signals(readme: str) -> tuple[float, list[str]]:
    if not readme:
        return 0.0, []
    penalty = 0.0
    notes: list[str] = []
    text_len = len(readme)

    emoji_count = sum(
        1 for c in readme
        if 0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF
    )
    if text_len > 200 and emoji_count / text_len > 0.005:
        penalty += 3
        notes.append(f"high emoji density ({emoji_count} emojis)")

    first_500 = readme[:500].lower()
    if "🚀 awesome" in first_500 or "awesome 🚀" in first_500:
        penalty += 3
        notes.append("'🚀 Awesome' opener")

    rl = readme.lower()
    super_hits = sum(rl.count(s) for s in SUPERLATIVES)
    if super_hits >= 2:
        penalty += 2
        notes.append(f"{super_hits} superlative claims")

    if len(re.findall(r"not just \w+,? but\b", readme, re.IGNORECASE)) >= 2:
        penalty += 2
        notes.append("'not just X, but Y' tic")

    tic_hits = sum(rl.count(t) for t in LLM_TICS)
    if tic_hits:
        penalty += min(3, tic_hits)
        notes.append(f"LLM-voice tells x{tic_hits}")

    return min(15.0, penalty), notes


def score_repo(owner_repo: str, keywords: list[str]) -> dict[str, Any]:
    repo = gh_json(["api", f"repos/{owner_repo}"])

    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    watchers = repo.get("subscribers_count", 0)
    pushed_at = repo.get("pushed_at", "")
    created_at = repo.get("created_at", "")
    description = (repo.get("description") or "").lower()
    topics = [t.lower() for t in (repo.get("topics") or [])]
    archived = bool(repo.get("archived"))
    default_branch = repo.get("default_branch", "main")
    license_id = ((repo.get("license") or {}).get("spdx_id")) or "NOASSERTION"

    bd = Breakdown()

    # --- Activity (recency + issue health, 0-1) ---
    bd.recency = max(0.0, 1.0 - days_since(pushed_at) / 365.0)
    closed, open_ = fetch_issue_counts(owner_repo)
    if closed + open_ > 0:
        bd.issue_health = closed / (closed + open_)
    bd.activity = 0.5 * bd.recency + 0.5 * bd.issue_health

    # --- Health (file presence) ---
    files = fetch_tree(owner_repo, default_branch)
    bd.health_files = health_from_tree(files) if files else 0.5

    # --- Relevance (topic + description + readme keyword density) ---
    readme = fetch_readme(owner_repo)
    bd.relevance = relevance_from_meta(description, topics, readme, keywords)

    # --- Trust (fork ratio + watcher ratio) ---
    bd.fork_ratio = min(1.0, forks / max(1.0, stars * 0.10)) if stars else 0.0
    bd.watcher_ratio = min(1.0, watchers / max(1.0, stars * 0.01)) if stars else 0.0
    trust = 0.5 * bd.fork_ratio + 0.5 * bd.watcher_ratio

    # --- Age vs growth sanity ---
    if created_at and stars:
        age = max(1, days_since(created_at))
        if age < 60 and stars / age > 200:
            bd.age_growth_multiplier = 0.3
            bd.notes.append(
                f"suspicious growth ({stars / age:.0f} stars/day at {age}d age)"
            )

    # --- Popularity (log-scaled stars) ---
    bd.popularity = min(1.0, math.log10(1 + stars) / math.log10(100000))

    # --- Scorecard (optional) ---
    scorecard = fetch_scorecard(owner_repo)
    bd.scorecard = scorecard
    scorecard_norm = (scorecard / 10.0) if scorecard is not None else 0.5

    # --- Slop penalty ---
    bd.slop_penalty, bd.slop_notes = slop_signals(readme)

    # --- Composite ---
    composite = 100.0 * (
        0.25 * bd.activity
        + 0.20 * bd.health_files
        + 0.20 * bd.relevance
        + 0.15 * trust
        + 0.10 * bd.popularity
        + 0.10 * scorecard_norm
    )
    composite *= bd.age_growth_multiplier
    composite -= bd.slop_penalty
    composite = max(0.0, min(100.0, composite))

    return {
        "repo": owner_repo,
        "score": round(composite, 1),
        "stars": stars,
        "forks": forks,
        "subscribers": watchers,
        "pushed_at": pushed_at,
        "created_at": created_at,
        "archived": archived,
        "license": license_id,
        "topics": topics,
        "breakdown": {
            "recency": round(bd.recency, 3),
            "issue_health": round(bd.issue_health, 3),
            "activity": round(bd.activity, 3),
            "health_files": round(bd.health_files, 3),
            "relevance": round(bd.relevance, 3),
            "fork_ratio": round(bd.fork_ratio, 3),
            "watcher_ratio": round(bd.watcher_ratio, 3),
            "trust": round(trust, 3),
            "popularity": round(bd.popularity, 3),
            "scorecard": bd.scorecard,
            "scorecard_norm": round(scorecard_norm, 3),
            "age_growth_multiplier": bd.age_growth_multiplier,
            "slop_penalty": round(bd.slop_penalty, 1),
            "slop_notes": bd.slop_notes,
            "notes": bd.notes,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Score a GitHub repo on quality + relevance."
    )
    p.add_argument("owner_repo", help="owner/repo (e.g. octocat/hello-world)")
    p.add_argument(
        "--keywords",
        default="",
        help="Comma-separated category keywords for relevance scoring.",
    )
    args = p.parse_args()

    if "/" not in args.owner_repo:
        print("error: argument must be in 'owner/repo' form", file=sys.stderr)
        sys.exit(2)

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    if not (
        os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    ):
        print(
            "warning: no GITHUB_PERSONAL_ACCESS_TOKEN / GH_TOKEN / GITHUB_TOKEN in env. "
            "gh CLI must be authenticated for higher rate limits.",
            file=sys.stderr,
        )

    try:
        result = score_repo(args.owner_repo, keywords=keywords)
    except Exception as e:
        print(json.dumps({"error": str(e), "repo": args.owner_repo}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
