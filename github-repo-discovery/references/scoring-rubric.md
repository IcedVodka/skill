# 📊 Scoring Rubric

The composite quality score for a candidate repo. Read this when scoring
inline (without the Python script), tuning weights, or interpreting a score
breakdown.

## Why not just stars

A 2024 Carnegie Mellon study counted ~6 million suspected fake stars across
18,617 repos — by July 2024, 16.66% of repos with 50+ stars showed fake-star
activity. Premium stargazer accounts sell for up to $5,000. Stars are
gameable; they cannot be the dominant signal.

The strongest single fake-star tell: **fork-to-star ratio <5% on a 1000+star
repo**. Bots star, they don't fork. Healthy projects sit at 10-25%.

## Composite formula

Computable in ≤3 GitHub API calls per candidate plus 1 optional OpenSSF
Scorecard call.

```
score = 100 * (
    0.25 * activity      # recency + issue close health
  + 0.20 * health        # README/LICENSE/CI/tests presence
  + 0.20 * relevance     # topic match + description match
  + 0.15 * trust         # fork ratio + watcher ratio
  + 0.10 * popularity    # log-scaled stars
  + 0.10 * scorecard     # OpenSSF aggregate / 10 (default 0.5 if unavailable)
) * age_growth_penalty   # 0.3 if stars/day > 200 AND age < 60d, else 1.0
- slop_penalty           # 0..15, hard subtract for AI-slop signatures
```

Each subscore is normalised 0-1 before weighting. Stars enter only via
`popularity` (log-scaled, capped) — they cannot dominate.

## API call budget per candidate

1. `GET /repos/{owner}/{repo}` — identity, dates, counts, topics, language, license
2. `GET /repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1` — file presence
3. `GET /search/issues?q=repo:{o}/{r}+is:issue+is:closed&per_page=1` (and same for `is:open`)
4. *(Optional)* `GET https://api.securityscorecards.dev/projects/github.com/{o}/{r}` — free, no auth, ~1M repos pre-computed

Optional 5th: `GET /repos/{o}/{r}/contributors?per_page=10` for contributor diversity.

## Per-signal computation

| Signal | Weight | Formula | Source |
|---|---|---|---|
| Recency | inside `activity` (8) | `max(0, 1 - days_since_pushed_at / 365)` | Call 1 — `pushed_at` |
| Issue close health | inside `activity` (9) | `closed / max(1, closed + open)` | Call 3 |
| README + LICENSE present | inside `health` (4) | `0.5 * has_readme + 0.5 * has_license` | Call 2 — file tree |
| CI + tests present | inside `health` (6) | `0.5 * has_workflows + 0.5 * has_test_dir_or_files` | Call 2 — file tree |
| OpenSSF Scorecard | 10 | `score / 10` (default 0.5 if not in dataset) | Optional Scorecard call |
| Topic match | inside `relevance` (6) | `1.0 if any keyword in topics else 0.0` | Call 1 |
| Description match | inside `relevance` (6) | `1.0 if any keyword in description else 0.0` | Call 1 |
| README relevance | inside `relevance` (8) | keyword density vs category terms | Call 2 — README blob |
| Fork-to-star ratio | inside `trust` (8) | `min(1, forks / max(1, stars * 0.10))` | Call 1 |
| Watcher-to-star ratio | inside `trust` (4) | `min(1, watchers / max(1, stars * 0.01))` | Call 1 — `subscribers_count` |
| Contributor diversity | inside `trust` (5) | `1 - top_contributor_share` | Optional contributors call |
| Age-vs-growth sanity | multiplier (-70%) | if `stars/day > 200` AND age `< 60d`, multiply by 0.3 | Call 1 |
| Popularity (log stars) | 6 | `log10(1 + stars) / log10(100000)`, capped at 1 | Call 1 |
| Verified owner | inside `trust` (2) | `1.0 if organization.is_verified else 0.0` | Optional GraphQL |
| Default branch protection | inside `trust` (4) | `1.0 if branchProtectionRules non-empty else 0.0` | Optional GraphQL |
| **Slop penalty** | -15 max | sum of slop signals (see below), capped at 15 | Call 2 (README content) |

The script in `scripts/score_repo.py` collapses some of these into `activity`,
`health`, `trust`, `relevance` super-buckets to keep the API budget tight.

## Slop penalty signals (subtracted)

Each detected pattern adds to the penalty up to a cap of 15:

| Pattern | Subtract |
|---|---|
| Emoji density >0.5% of README characters | 3 |
| README opens with "🚀 Awesome" or similar | 3 |
| ≥2 superlative claims with no benchmarks ("blazing fast", "revolutionary", "the best") | 2 |
| "Not just X, but Y" rhetorical structure ≥2 times (LLM tic) | 2 |
| <2 commits beyond initial | 5 |
| All PRs from one bot/owner | 2 |
| LLM-voice tells: "it's worth noting", "in essence", "delve into" | 1 each, capped at 3 |

Slop subtracts AFTER the weighted sum, so a slop repo cannot exceed ~85 even
with otherwise-perfect signals — and typically lands far lower because slop
repos also fail the activity, contributor-diversity, and age-vs-growth
checks simultaneously.

## Reading a score

| Score | Interpretation |
|---|---|
| 80-100 | High confidence — present without caveats |
| 60-79 | Solid — present with brief caveats noted |
| 40-59 | Mixed — present only if user asked for breadth, flag concerns |
| 20-39 | Risky — exclude unless niche-specific reason to include |
| 0-19 | Reject — abandoned, slop, or fake-stars-driven |

## Sources

- [Six Million (Suspected) Fake Stars in GitHub — arXiv 2412.13459](https://arxiv.org/abs/2412.13459)
- [OpenSSF Scorecard — scorecard.dev](https://scorecard.dev/)
- [npms.io scoring methodology](https://npms.io/about) — quality 30 / popularity 35 / maintenance 35
- [Libraries.io SourceRank docs](https://docs.libraries.io/overview.html)
