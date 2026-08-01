---
name: github-repo-discovery
description: >
  Find and classify the top GitHub repositories in any category. Select the right `gh` search strategy, optionally dispatch parallel sub-agents across established/rising/niche lanes, and score candidates with a slop-aware rubric that resists fake-star inflation. Use when the user asks to find, compare, rank, or classify GitHub repositories, open-source tools, libraries, frameworks, Agent Skills, Codex or Claude Code plugins, MCP servers, or trending projects, even when they do not explicitly mention GitHub.
---

# 🔍 GitHub Repo Discovery

Help the user find and classify the top GitHub repositories in any category.
The skill assumes `gh` CLI is authenticated via `gh auth login` or a supported
token. Parallel sub-agents are optional; use them only when available and useful.

## 🎯 The core insight (read first)

The right query *type* matters more than a smarter ranker. For niche
capabilities, a naive `gh search repos "<natural-language description>"`
often returns zero hits because no repo's *name* contains the phrase the
user used. The same intent expressed as a code search inside a fixed
filename — `gh search code "<keyword>" --filename SKILL.md` for Agent Skills,
`--filename plugin.json` for plugins, `--filename Cargo.toml` for
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
| "agent skill", "codex skill", "claude code skill", "skill that <verb>" | `gh search code "<keyword>" --filename SKILL.md --limit 20` | `references/agent-skill-ecosystem-recipes.md` |
| "claude code plugin", "marketplace", an Anthropic-managed thing | `gh api repos/anthropics/claude-plugins-official/contents/plugins`, then `gh search code "<keyword>" --filename plugin.json` | `references/agent-skill-ecosystem-recipes.md` |
| "codex plugin", a Codex-managed thing | `gh search code "<keyword>" --filename plugin.json`, then verify `.codex-plugin/plugin.json` | `references/agent-skill-ecosystem-recipes.md` |
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
  --pushed '>=<YYYY-MM-DD>' --archived=false --sort stars --limit 100 \
  --json fullName,description,stargazersCount,forksCount,pushedAt,url,license
```

For Agent Skill discovery, the high-signal query is:

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
- **>10 candidates OR clear sub-lanes** in the category → when collaboration
  tools and enough slots are available, dispatch up to N=3 parallel sub-agents
  using the brief in
  `references/sub-agent-brief-template.md`. The lanes:
  - **Agent A — Established:** ≥1000 stars, created ≥2y ago, pushed in last 90d
  - **Agent B — Rising:** ≥100 stars, created ≤12mo ago, pushed in last 30d, sort by stars-per-day
  - **Agent C — Niche:** lower star floor, broader topic match, code search inside `SKILL.md` / `plugin.json`

If parallel sub-agents are unavailable, run the same lanes sequentially in
the current agent. Do not turn tool availability into a blocker.

Every delegated brief MUST include the `## What other agents are covering — DO NOT
DUPLICATE` block listing the other lanes verbatim. Anthropic's own
multi-agent post-mortem identified vague-brief duplication as the #1
failure mode for parallel research, so this is non-negotiable. Read
`references/sub-agent-brief-template.md` for the full template.

Require each sub-agent to return its query log and verified source URLs. If
the result has no live-search evidence, reject it and re-run the lane.

## 📊 Step 4 — Score candidates

Run the scoring script for each candidate:

```bash
python3 <skill-dir>/scripts/score_repo.py owner/repo --keywords "kw1,kw2,kw3"
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

1. **Spot-check 2 of every 5 returned URLs** with Codex web browsing or
   `curl`. Use `<skill-dir>/scripts/verify_urls.sh url1 url2 ...` for a quick
   pass. Reject 404s.
2. **Auto-flag** any repo with <10 stars OR last commit >2 years for manual
   review. Don't silently drop — the agent may have found a real but
   unmaintained gem.
3. **Reject sub-agent outputs without a query log and verified source URLs.**
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
| `references/agent-skill-ecosystem-recipes.md` | Any Agent Skill or Codex/Claude plugin search; ecosystem layouts and high-signal code searches |
| `references/sub-agent-brief-template.md` | Constructing the briefs for the three parallel sub-agents (read every time you dispatch) |

## 🛠️ Bundled scripts

| Script | Purpose |
|--------|---------|
| `scripts/score_repo.py` | Compute composite 0-100 quality score for `owner/repo`. Args: `--keywords` for relevance scoring. Requires `gh` CLI. |
| `scripts/verify_urls.sh` | Spot-check that GitHub URLs return 200/301/302. Use after each sub-agent returns. |
