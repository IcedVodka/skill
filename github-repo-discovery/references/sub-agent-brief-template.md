# 🤖 Sub-Agent Brief Template

Use this template every time you dispatch one of the three discovery
sub-agents. The mandatory sections — particularly `## What other agents are
covering — DO NOT DUPLICATE` — exist because Anthropic's own multi-agent
research post-mortem identified vague-brief duplication as the #1 failure
mode. Three agents researching the same canonical repos is wasted budget.

## When to use N=3

- **N=2** is enough for narrow sub-niche categories (e.g. "S3 client libraries in Rust")
- **N=3** is the sweet spot for a single category with breadth (the default)
- **N=5+** only when the category genuinely fans into orthogonal sub-categories (e.g. "agent frameworks" → orchestration / memory / eval / browser-control / coding)

Do not fan out below N=2 — that's a single agent with extra steps.

## The three lanes

| Lane | Filters | Looking for |
|---|---|---|
| **A — Established** | `stars:>1000`, `created:<2yrs`, `pushed:>=90d` | Canonical / widely-adopted repos |
| **B — Rising** | `stars:>100`, `created:>=12mo ago`, `pushed:>=30d`, sort by stars-per-day | Newer repos with momentum |
| **C — Niche** | lower star floor, broader topic match, code search inside `SKILL.md` / `plugin.json` | Specialised or hyper-targeted repos that pure star sorts miss |

## Template (copy-paste, fill placeholders)

```text
ROLE: You are sub-agent {AGENT_INDEX} of {N_AGENTS} in a repo-discovery sweep.

OBJECTIVE
Find and classify {max_results} GitHub repos in the category: "{category}".
Your specific lane: {lane_for_this_agent}

WHAT OTHER AGENTS ARE COVERING — DO NOT DUPLICATE
{lanes_for_other_agents}
If a repo arguably fits another lane, leave it for them.

QUALITY THRESHOLD
- Minimum stars: {quality_threshold.min_stars}
- Last commit within: {recency_window}
- License: OSI-approved (MIT, Apache-2.0, BSD-*, MPL-2.0)
- Active = >=1 commit in the last {recency_window} OR >=1 release in last 12 months

TOOLS YOU MAY USE
- Bash with `gh search code "<keyword>" --filename SKILL.md --limit 20`
  (and equivalent for plugin.json) for Agent Skill capabilities
- Bash with `gh search repos --topic <topic> --stars '>N' --pushed '>=YYYY-MM-DD' --json fullName,...`
- Bash with `gh api repos/{o}/{r}` for verification
- Codex web browsing or `gh api` on GitHub URLs for spot-checks
You MUST run at least one live query or fetch per repo you list. No live
evidence means no answer.

DO NOT
- Invent URLs. Every URL must be one you fetched in this session.
- Cite "based on common knowledge" or training-data recall.
- List repos you cannot verify against a live fetch.
- Exceed your lane.

OUTPUT FORMAT (Markdown, hard cap 800 words)
For each repo:
### {repo-name}
- URL: https://github.com/owner/repo
- Stars: N (verified {date})
- Last commit: YYYY-MM-DD
- License: <spdx-id>
- One-liner: <one sentence, your words>
- Why it qualifies for "{category}": <one sentence, evidence-based>
- Caveats: <maintenance concerns, deprecations, known forks — or "none">

End with a `## Self-check` block listing:
- Tool calls made: N
- URLs verified: N
- Repos dropped because unverifiable: N

Return the markdown in your final message. Do not write to disk unless the
parent agent told you to.
```

## Filling the placeholders for the standard 3-agent dispatch

```text
{N_AGENTS} = 3

# Agent A
{AGENT_INDEX} = 1
{lane_for_this_agent} = ESTABLISHED — repos with >=1000 stars, created at least 2 years ago,
  with at least one commit in the last 90 days. Look for canonical / widely-adopted projects.
{lanes_for_other_agents} =
  - Agent B (Rising): newer repos (created within last 12 months) with momentum (sort by stars-per-day)
  - Agent C (Niche): lower-star repos with specific topic or code-search matches inside SKILL.md / plugin.json
{quality_threshold.min_stars} = 1000
{recency_window} = 90 days

# Agent B
{AGENT_INDEX} = 2
{lane_for_this_agent} = RISING — repos created in the last 12 months, with at least 100 stars,
  active in the last 30 days. Look for momentum; sort candidates by stars-per-day.
{lanes_for_other_agents} =
  - Agent A (Established): canonical >=1000-star repos older than 2 years
  - Agent C (Niche): specific topic / code-search hits regardless of momentum
{quality_threshold.min_stars} = 100
{recency_window} = 30 days

# Agent C
{AGENT_INDEX} = 3
{lane_for_this_agent} = NICHE — specialised or hyper-targeted repos that pure star/momentum
  sorts would miss. Use code search inside SKILL.md and plugin.json. Lower star floor (10+).
{lanes_for_other_agents} =
  - Agent A (Established): canonical >=1000-star repos
  - Agent B (Rising): new repos with momentum
{quality_threshold.min_stars} = 10
{recency_window} = 12 months
```

## Anti-patterns the brief structure prevents

1. **Phantom repos** — agent invents `github.com/<plausible-name>/<plausible-name>` URLs that 404. The "every URL must be one you fetched in this session" line + post-dispatch URL verification catches this.
2. **SEO-farm laundering** — agents prefer SEO-optimised "top 10" listicles over authoritative sources. The tool restriction to `github.com` blocks this.
3. **Training-data drift** — listing 2024-popular repos as if current. The "Last commit within {recency_window}" requirement catches it.
4. **Lane-jumping** — agent expands scope to "also relevant" repos covered by another sub-agent. The explicit `do NOT duplicate` block + named other lanes catches this.
5. **Toolless armchair research** — agent returns a confident answer without a live search or fetch. The parent agent rejects outputs without a query log and verified URLs.

## Verification step (parent-agent side, after sub-agents return)

1. Spot-check 2 of every 5 returned URLs with Codex web browsing, `gh api`, or `verify_urls.sh`. Flag 404s.
2. Auto-flag repos with <10 stars OR last commit >2 years for manual review (don't silently drop — may be a real but unmaintained gem).
3. Reject any sub-agent output without a query log and verified source URLs.
4. Cross-check overlap: if two agents returned the same repo, keep one and note the duplicate (signals brief leakage to fix next run).

## Sources

- Anthropic — [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Anthropic — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Claude Code docs — [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- Simon Willison — [Anthropic: How we built our multi-agent research system](https://simonwillison.net/2025/Jun/14/multi-agent-research-system/)
