# 🎯 Agent Skill Ecosystems — Search Recipes

When the user asks for a Codex or Claude Code skill, plugin, agent, MCP
server, hook, or sub-agent, read this file first. Both ecosystems use
`SKILL.md`; plugin manifests distinguish `.codex-plugin/plugin.json` from
`.claude-plugin/plugin.json`. These fixed filenames surface candidates that
repo-name search cannot find.

## The magic query (works for almost any niche capability)

```bash
gh search code "<keyword>" --filename SKILL.md --limit 20 \
  --json repository,path,textMatches
```

Why it works: Agent Skills normally live in a file named `SKILL.md`.
That gives you a precision filter that repo-name search doesn't have. The
same intent expressed as a repo-name search will frequently return zero
hits because repo names rarely contain the natural-language phrases users
use to describe a capability — switching to a code search inside the
fixed filename surfaces real candidates that exist but were invisible to
the wrong query type.

Variations:

```bash
# Check plugin wrappers too
gh search code "<keyword>" --filename plugin.json --limit 10

# Look inside frontmatter descriptions
gh search code "name: <keyword>" --filename SKILL.md
gh search code "description: <keyword>" --filename SKILL.md
```

## Step-by-step recipe

1. **Start in the canonical awesome-list** — `gh api repos/hesreallyhim/awesome-claude-code/contents/README.md` then base64-decode and grep. Curated quality bar > raw search.
2. **For Claude Code, check the official Anthropic marketplace** — two repos:
   - `anthropics/claude-plugins-official` — gated, version-pinned plugins exposed in Claude Code's installer (33 plugins as of April 2026, including `commit-commands`, `frontend-design`, `hookify`, `code-review`)
   - `anthropics/skills` — public Agent Skills repo with `skills/` (17 official skills) and `template/SKILL.md`
3. **Code-search SKILL.md files** — the magic query above. Highest signal per query.
4. **Code-search `plugin.json`** — catches plugin-wrapped variants of the same skill.
5. **Topic search with star floor** — `gh search repos --topic claude-skills --stars '>50' --pushed '>=YYYY-MM-DD' --limit 50`. Choose the date from the requested freshness window; topics without star/freshness filters drown you in spam.
6. **Cross-reference secondary awesome-lists** — `VoltAgent/awesome-agent-skills`, `sickn33/antigravity-awesome-skills`. Same data, different curators.
7. **For Codex plugins, verify the manifest** — require
   `.codex-plugin/plugin.json`; treat `skills/`, `agents/`, `apps/`, and MCP
   configuration as optional plugin contents.
8. **Verify before recommending** — open `SKILL.md` or the plugin manifest,
   confirm its shape and last push, and ensure it supports the runtime the
   user requested.

## Live awesome-lists (verified 2026-04-25)

| Repo | Stars | Last push | What it indexes |
|---|---|---|---|
| `hesreallyhim/awesome-claude-code` | 40.9k | active | Canonical curated list |
| `VoltAgent/awesome-claude-code-subagents` | 18.3k | active | 100+ subagent prompts |
| `VoltAgent/awesome-agent-skills` | 18.7k | active | 1000+ multi-agent skills |
| `sickn33/antigravity-awesome-skills` | 35k | active | 1400+ installable skills with CLI installer |
| `ComposioHQ/awesome-claude-plugins` | 1.5k | active | Plugins-system focused |
| `travisvn/awesome-claude-skills` | 11.7k | slightly stale | Skills only |

Avoid: `ccplugins/awesome-claude-code-plugins` (stale, last push 2025-10).

## Topics in active use

| Topic | Notes |
|---|---|
| `claude-code` | Broadest; includes installers and harnesses |
| `claude-skills`, `claude-code-skills` | Most precise for SKILL.md-based skills |
| `claude-agents`, `claude-subagents` | Sub-agent prompts |
| `claude-plugins` | Plugin-system entries |
| `claude-hooks` | Lifecycle hooks |
| `claude-mcp` | MCP servers for Claude |

Topic discovery is decent for breadth but noisy at the top — many sub-1k
star repos use topics for SEO. Always combine with a star floor.

## Canonical layouts to look for

```
<repo>/
  .claude-plugin/
    plugin.json          # name, description, version, author
  skills/<skill-name>/
    SKILL.md             # frontmatter: name, description, allowed-tools, user-invocable
    scripts/             # optional helper scripts
    references/          # optional doc fragments
```

```text
<repo>/
  .codex-plugin/
    plugin.json          # required Codex plugin manifest
  skills/<skill-name>/
    SKILL.md             # optional plugin-contributed skill
    scripts/             # optional helper scripts
    references/          # optional reference material
```

A candidate without the requested ecosystem's plugin manifest and without
`SKILL.md` is probably a generic prompt collection, not an installable skill
or plugin.

## Caveats

- **Pre-skills-system relics** — anything pushed before mid-2025 likely
  predates the SKILL.md spec; uses raw prompts in README. Filter on
  `pushedAt > 2025-09-01`.
- **Cross-platform "skills" that aren't Claude-native** — many entries on
  `sickn33/antigravity-awesome-skills` market to "Claude Code, Cursor, Codex
  CLI, Gemini CLI, Antigravity." They work but lack Claude-specific
  frontmatter (`allowed-tools`).
- **Fake "claude" branding for SEO** — repos like `<random>/Claude-Zeroclaw`
  with short READMEs and no `.claude-plugin/` are repo-spam.
- **Wrong namespace collisions** — keyword search frequently surfaces
  repos that share a name with the target capability but live in a
  different ecosystem (a Python library with the same name as a Claude
  Code skill, a Codex tool with the same name as a writing-tone skill, an
  audio plugin with the same name as a CLI tool). Always verify by reading
  the README before recommending.
- **Inflated star counts** — single-author harnesses with 100k+ stars are
  almost always inflated or include fork/aggregator counts. Cross-check
  fork ratio and contributor count.
