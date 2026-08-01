# 🔌 Search API Cheatsheet

Condensed reference for shelling `gh` CLI / curl against GitHub search.
Read this when constructing a query or hitting an edge case.

## Recommended primary path

`gh search repos` — auth pre-handled, JSON output, jq-friendly. Use it
unless you specifically need GraphQL's richer per-repo fields in one hop.

```bash
gh search repos "<free-text>" \
  --topic <topic> \
  --language <lang> \
  --stars '>500' \
  --pushed '>=<YYYY-MM-DD>' \
  --created '>=2024-01-01' \
  --license mit \
  --archived=false \
  --sort stars \
  --limit 100 \
  --json fullName,description,stargazersCount,forksCount,pushedAt,url,license
```

Useful flags: `--topic`, `--language`, `--stars`, `--forks`, `--pushed`,
`--created`, `--license`, `--archived=false`, `--owner`,
`--match name,description,readme`, `--sort {stars,forks,updated,best-match}`,
`--limit N` (caps at 1000), `--json <fields>`.

For code search inside specific filenames:

```bash
gh search code "<keyword>" --filename SKILL.md --limit 20 \
  --json repository,path,textMatches
```

## Qualifier reference (use in `q` / free-text)

| Qualifier | Example |
|---|---|
| `stars:>N`, `stars:N..M` | `stars:>5000`, `stars:1000..5000` |
| `forks:>N` | `forks:>500` |
| `language:` | `language:rust` |
| `topic:` (repeat for AND) | `topic:cli topic:rust` |
| `topics:>=N` | `topics:>=3` |
| `pushed:>=YYYY-MM-DD` | `pushed:>=2026-01-01` |
| `created:` | `created:2024-01-01..2024-12-31` |
| `archived:false` | always include for quality results |
| `mirror:false` | excludes mirror repos |
| `license:` (SPDX) | `license:apache-2.0`, `license:mit` |
| `size:` (KB) | `size:>1000` |
| `in:name,description,readme` | restrict free-text scope |
| `org:` / `user:` | `org:vercel`, `user:tj` |

## The 1000-result cap (and how to beat it)

Both REST and GraphQL search return at most 1000 results per query. REST
allows `per_page` up to 100; pages 11+ return 422 once you would cross 1000.

**Workaround:** partition the query on a numeric or date range. Slice until
each segment's `total_count` ≤ 1000, then union the results.

```bash
# By star ranges (binary-search the cutoff):
gh search repos --topic ai-agents --stars '500..1499' --limit 100 ...
gh search repos --topic ai-agents --stars '1500..4999' --limit 100 ...
gh search repos --topic ai-agents --stars '>=5000' --limit 100 ...

# By creation date:
gh search repos --topic rag --created '2024-01-01..2024-06-30' ...
gh search repos --topic rag --created '2024-07-01..2024-12-31' ...
```

## Rate limits

- REST search: **30 req/min authenticated** (10/min unauth) — separate from
  the 5000/hr core limit
- GraphQL: unified 5000-points/hr budget; search costs more points than node
  fetches. Inspect via `rateLimit { cost remaining resetAt }` in any query

Always authenticate. `gh` handles this automatically when `gh auth login` has
been run or `GITHUB_PERSONAL_ACCESS_TOKEN` is set. Honour `Retry-After` on
403/429.

## When to switch to GraphQL

GraphQL beats REST when you need rich per-repo fields in one round-trip
(stars + forks + last-commit + topics + license + primary language + branch
protection). Same query DSL, same 1000-result cap.

```bash
gh api graphql -F q="topic:rag stars:>500 pushed:>=<YYYY-MM-DD> archived:false" \
  -f query='
    query($q: String!) {
      search(query: $q, type: REPOSITORY, first: 100) {
        repositoryCount
        nodes {
          ... on Repository {
            nameWithOwner url description
            stargazerCount forkCount pushedAt
            primaryLanguage { name }
            licenseInfo { spdxId }
            repositoryTopics(first: 10) { nodes { topic { name } } }
            defaultBranchRef { target { ... on Commit { committedDate } } }
          }
        }
      }
    }'
```

## Reliability gotchas

- **Indexing lag** — newly pushed READMEs and freshly applied topics are not
  searchable for minutes to hours. For very recent activity, fall back to
  `gh api repos/{o}/{r}` for ground truth.
- **`best-match` is opaque** — always explicit-sort.
- **`topic:` false negatives** — many otherwise-relevant repos never apply
  topics. Cross-search with `<keyword> in:name,description` and union, or
  treat topics as a precision filter (not a recall filter).
- **Forks and mirrors** — search excludes forks unless `fork:true`, but
  mirror repos and vendored copies still appear. Add `mirror:false`.
- **`pushed_at` is repo-level, not branch-level** — a bot updating a stale
  branch counts. Pair with `defaultBranchRef.target.committedDate` (GraphQL)
  for real freshness.
