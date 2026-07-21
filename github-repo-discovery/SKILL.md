---
name: github-repo-discovery
description: >
  Find and classify the top GitHub repositories in any category. Picks the right `gh` search strategy per category, dispatches parallel sub-agents across established/rising/niche lanes, and scores candidates with a slop-aware rubric that survives fake-star inflation. **Use this skill whenever the user mentions any of: "find me a repo for X", "top GitHub repos for Y", "best library for X", "what's the best framework for Y", "find a Claude Code skill that...", "is there a plugin for X", "what MCP servers do Y", "find an open-source X", "top trending in Y", "what tool does X", "compare repos for Y", "GitHub repo discovery", "search GitHub for X", "find me a tool to Y", "any good repos for Z", "what's everyone using for X", "spring clean / tidy up my repos list", or any variation expressing the desire to discover, compare, or classify open-source projects on GitHub.** Don't wait for the user to say "GitHub" explicitly — if they signal intent to find or compare open-source projects, this is the right skill. For Claude Code capabilities specifically, the skill code-searches inside `SKILL.md` and `plugin.json` files, which is the difference between zero hits and twenty real candidates (the magic query that beats repo-name search).
---

# 🔍 GitHub Repo Discovery

Help the user find and classify the top GitHub repositories in any category.
The skill assumes you have `gh` CLI authenticated (via `GITHUB_PERSONAL_ACCESS_TOKEN`
or `gh auth login`) and access to parallel sub-agents.

## 🎯 The core insight (read first)

The right query *type* matters more than a smarter ranker. For niche
capabilities, a naive `gh search repos "<natural-language description>"`
often returns zero hits because no repo's *name* contains the phrase the
user used. The same intent expressed as a code search inside a fixed
filename — `gh search code "<keyword>" --filename SKILL.md` for Claude Code
skills, `--filename plugin.json` for plugins, `--filename Cargo.toml` for
Rust libraries — typically returns dozens of real candidates. Picking the
wrong query type returns nothing even when the answer exists. Always start
by classifying the category and choosing a strategy before searching.

A second non-obvious thing: stars are an unreliable single signal. A 2024
CMU study found ~6 million suspected fake stars, with 16.66% of repos
holding 50+ stars showing fake-star activity. Always log-scale stars and
combine with fork-to-star ratio (the strongest single fake-star tell), recency,
and an OpenSSF Scorecard call.

## 🗺️ Step 1 — Classify the category and pick a strategy

Read the user's category. Match against this table; pick ONE primary
strategy and announce it before searching so the user can redirect.

| Category signal | Primary strategy | Reference |
|---|---|---|
| "claude code skill", "skill that <verb>", any Claude Code capability | `gh search code "<keyword>" --filename SKILL.md --limit 20` | `references/claude-code-ecosystem-recipes.md` |
| "claude code plugin", "marketplace", an Anthropic-managed thing | `gh api repos/anthropics/claude-plugins-official/contents/plugins`, then `gh search code "<keyword>" --filename plugin.json` | `references/claude-code-ecosystem-recipes.md` |
| Language + tool type ("rust cli", "python orchestrator") | `gh search repos --topic <type> --language <lang> --stars '>500' --pushed '>=YYYY-MM-DD'` | `references/search-api-cheatsheet.md` |
| Generic category ("AI agent frameworks", "vector database") | Topic search with star floor + freshness, plus `awesome-<topic>` lookup | `references/search-api-cheatsheet.md` |
| Returns >1000 results | Partition on `stars:` ranges (binary-search the cutoff so each slice ≤1000) | `references/search-api-cheatsheet.md` |

Read the linked reference file before running the strategy if you are not
already confident on the syntax. Reading after a wrong query wastes time.

## 🔎 Step 2 — Run the primary query

Shell out via `gh` CLI (auth handled, JSON output, jq-friendly). Always
explicit-sort — never trust `best-match`, GitHub does not document its
ranking and changes it without notice.

```bash
gh search repos --topic <topic> --language <lang> --stars '>500' \
  --pushed '>=2025-10-01' --archived=false --sort stars --limit 100 \
  --json fullName,description,stargazersCount,forksCount,pushedAt,url,license
```

For Claude Code skill discovery, the magic query:

```bash
gh search code "<keyword>" --filename SKILL.md --limit 20 \
  --json repository,path,textMatches
```

If `total_count` exceeds 1000, partition on `stars:` (or `created:`) ranges —
GitHub caps any single search at 1000 results regardless of paging.

## 🤖 Step 3 — Decide whether to dispatch parallel sub-agents

Use this rule:

- **≤10 high-quality candidates** from the primary query → score them
  directly, skip sub-agents. Faster, cheaper, less noise.
- **>10 candidates OR clear sub-lanes** in the category → dispatch N=3
  parallel sub-agents using the brief in
  `references/sub-agent-brief-template.md`. The lanes:
  - **Agent A — Established:** ≥1000 stars, created ≥2y ago, pushed in last 90d
  - **Agent B — Rising:** ≥100 stars, created ≤12mo ago, pushed in last 30d, sort by stars-per-day
  - **Agent C — Niche:** lower star floor, broader topic match, code search inside `SKILL.md` / `plugin.json`

Every brief MUST include the `## What other agents are covering — DO NOT
DUPLICATE` block listing the other lanes verbatim. Anthropic's own
multi-agent post-mortem identified vague-brief duplication as the #1
failure mode for parallel research, so this is non-negotiable. Read
`references/sub-agent-brief-template.md` for the full template.

If a sub-agent returns its result with **zero tool calls fired**, reject
the output and re-run — that pattern is training-data fabrication, not
real research.

## 📊 Step 4 — Score candidates

Run the scoring script for each candidate:

```bash
python skill/scripts/score_repo.py owner/repo --keywords "kw1,kw2,kw3"
```

Returns JSON with a 0-100 score plus a per-signal breakdown. The script
implements the rubric in `references/scoring-rubric.md`:

- Stars are log-scaled and capped — they cannot dominate the score
- Slop penalty is a hard subtract (up to -15) so a high-star slop repo
  cannot sneak through
- OpenSSF Scorecard adds a free quality signal when the repo is in the
  dataset (~1M repos pre-computed at `api.securityscorecards.dev`)

You may compute the score inline (without the script) if Python is
unavailable, but follow the same weights and the same slop subtract — the
script is the canonical implementation.

## ✅ Step 5 — Verify before presenting

These four checks catch fabrications and dead links:

1. **Spot-check 2 of every 5 returned URLs** with `WebFetch` or `curl`. Use
   `skill/scripts/verify_urls.sh url1 url2 ...` for a quick pass. Reject 404s.
2. **Auto-flag** any repo with <10 stars OR last commit >2 years for manual
   review. Don't silently drop — the agent may have found a real but
   unmaintained gem.
3. **Reject zero-tool-call sub-agent outputs** (training-data fabrications).
4. **Note duplicate repos across agents** — if two lanes returned the same
   repo, log it (signals brief leakage to fix next run).

## 📤 Step 6 — Present

Use this structure. Brief is good — the user wants the answer, not an essay.

```markdown
# 🔍 Top {N} repos for "{category}"

| # | Repo | Stars | Last push | Score | Why |
|---|---|---|---|---|---|
| 1 | [owner/repo](url) | 15.1k | 2026-04-01 | 87 | one-line rationale |
| 2 | ... |

## Detail per repo

### owner/repo (score: 87)
- License, default branch, top contributor share, scorecard
- Slop signals detected (if any)
- Caveats (deprecation, fork-of, abandoned-but-popular, etc.)

## Search log
- Strategy used: <strategy>
- Queries fired: <N>
- Candidates considered: <N>
- Filtered: <N> (reason breakdown)
- URLs spot-checked: <verified>/<checked>
```

The search log is important — it lets the user re-run the discovery,
adjust thresholds, or notice that the strategy missed a sub-niche.

## 🚫 Anti-patterns to avoid

- **Trusting `best-match` sort** — opaque, undocumented, changes without
  notice. Always explicit-sort.
- **Treating star count as ground truth** — 16.66% of 50+star repos show
  fake-star activity. Combine with fork-to-star ratio (<5% on a 1000+star
  repo is the strongest single fake tell).
- **Skipping the category router** — going straight to repo-name search for
  a Claude Code capability returns zero hits even when 20 real answers
  exist via `--filename SKILL.md`.
- **Vague sub-agent briefs** — without explicit "do NOT duplicate" and
  lane definitions, agents converge on the same canonical repos and
  the dispatch was wasted.
- **Inflating scope** — N=3 sub-agents is the sweet spot for a single
  category. N=5+ only when the category genuinely fans into orthogonal
  sub-categories.

## 🔗 Reference files

| File | When to read |
|------|-------------|
| `references/search-api-cheatsheet.md` | Building a `gh search repos` query, hitting the 1000-result cap, choosing REST vs GraphQL |
| `references/scoring-rubric.md` | Understanding what `score_repo.py` computes, scoring inline without the script, tweaking weights |
| `references/claude-code-ecosystem-recipes.md` | Any Claude Code skill/plugin/agent search; awesome-list locations; the official Anthropic marketplace |
| `references/sub-agent-brief-template.md` | Constructing the briefs for the three parallel sub-agents (read every time you dispatch) |

## 🛠️ Bundled scripts

| Script | Purpose |
|--------|---------|
| `scripts/score_repo.py` | Compute composite 0-100 quality score for `owner/repo`. Args: `--keywords` for relevance scoring. Requires `gh` CLI. |
| `scripts/verify_urls.sh` | Spot-check that GitHub URLs return 200/301/302. Use after each sub-agent returns. |
