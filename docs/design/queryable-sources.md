# Queryable sources — a third kind of knowledge source

Status: PROPOSAL (2026-08-13). Owner review pending. Destined for the template
(domain-agnostic); the passive tree is the worked example only.

## Why

The source registry (`DOMAIN.md` tier table + `kb/meta/sources-guide.md`) today
knows two *kinds* of source:

- **file-source** — the agent *reads* a committed file. `data/` (parsed PoB2
  exports). Static, versioned, citable verbatim.
- **web-source** — the agent *fetches* a human page and extracts values under
  fetch discipline. poe2db, wiki, game8. Semi-structured, reachability risk.

Both assume the knowledge is *text an agent can read*. Some knowledge is not.
The passive tree is a graph with spatial structure: 3000+ nodes with x/y
coordinates, edges, regions, and distances. Dumping that as text
(`data/passive-tree/`) produces a file no agent can reason over — you cannot
eyeball "which keystones are cheapest from the Witch start" out of a hop-table,
and you certainly cannot *solve* "allocate these 6 targets in <=40 points" by
reading. That work wants to be **computed on demand**, not read.

So we add a third kind:

- **queryable-source (API)** — the agent *interrogates* a service with
  parameters and gets a **structured, ground-truth answer** back. Dynamic,
  computed, spatial/graph/solver queries that cannot be text-dumped.

Once this kind exists, **web is just a queryable-source with a fetch transport
and a low tier** — the registry unifies. This doc defines the kind so the tree
API (its first instance) drops into an existing slot instead of being a
one-off.

## The three kinds, side by side

| | file-source | web-source | **queryable-source (API)** |
|---|---|---|---|
| access | read a file | fetch + extract | call with params, get structured result |
| shape | static text | semi-structured HTML | structured JSON / typed answer |
| best for | stable enumerable data | discovery, prose, gap-fill | spatial/graph/computed/solver answers |
| citation | quote the file | quote the page verbatim | **snapshot** the call (below) |
| reachability | none (local) | site up/down (F3) | service up/down (F3) |
| examples | `data/*` | poe2db, game8 | tree API, a build simulator |

The **two-oracle rule is unchanged**: an API answer is a *values/existence*
oracle (like a file or a page), meaning still comes from prose, and magnitudes
are still simulator-verified where it matters. An API does not get a free pass
on corroboration just because it returned JSON — its *tier* decides how much
corroboration a value needs, exactly as for the other kinds.

## Manifest — how a queryable-source is registered

Every source (all three kinds) is declared in the registry with a uniform
manifest. Queryable-sources add the `endpoints` and `transport` fields. Proposed
shape (lives in `kb/meta/sources-guide.md` frontmatter + a row in `DOMAIN.md`):

```yaml
- id: passive-tree-api
  kind: api                      # file | web | api
  transport: http               # http | mcp | (fetch, for web)
  base: https://<host>/tree     # a URL reachable from ANY agent host (see Bridge)
  auth: bearer-token | none
  tier: dataset                 # SAME tiering as file/web sources
  version_anchor: PoB 0.23.1    # what game/data version the answers reflect
  answers:                      # the contract — what an agent may ask
    - "GET /keystones -> [{id,name,x,y,region,nearest_starts:[{class,hops}]}]"
    - "GET /node/{id} -> full node (stats, coords, neighbours)"
    - "GET /near?class=&stat= -> notables near a class start granting a stat"
    - "GET /distance?from=&to= -> min hop cost between two nodes"
    - "POST /solve {targets,budget} -> {allocated:[ids], points_used}"
  absence: "a node absent from /keystones does not exist in the 0_5 tree"
  health: reachable              # F3 auto-demote applies, same as web-sources
  citation: snapshot             # see below
```

The `answers` block is the **contract**: it tells a worker what it may ask
*without* the worker needing to reverse-engineer the API. It is the queryable
analogue of a web-source's "navigate by `/us/<Entity_Name>` URL shape" note.

## Citation & provenance — making an ephemeral answer citable

A file quote is reproducible forever; an API answer is a moment in time. To keep
KB claims citable and auditable we **snapshot** the call:

> A KB doc that rests on an API answer records: `source_id`, the exact request
> (endpoint + params), the response value quoted, the `version_anchor`, and the
> UTC timestamp of the call — the same verbatim-quote discipline used for
> poe2db pages. The snapshot is the citation.

This means: **an agent never cites "the tree API" in the abstract** — it cites
*"passive-tree-api `GET /distance?from=WitchStart&to=CI` -> 7 hops, PoB 0.23.1,
2026-08-13"*. Snapshots make a value survive the API going down or changing, and
make drift detectable on re-export (the same query returning a different answer
is exactly the signal that seeds a reconciliation task).

## Confidence tier — where does an API sit?

Tier is **per-source, declared in the manifest**, not a property of "being an
API." The tree API is **dataset-tier** because it is derived from the *same PoB
parse* as `data/passive-tree/` — it is the dataset, served computed. A
third-party build API of unknown provenance would sit at `datamine` or lower.
The existing tier ladder (official > dataset > datamine > reference > community)
absorbs API sources unchanged.

## Bridge — how a fired worker reaches an API

`bin/agent-run.sh` is deliberately dumb: fresh clone -> `claude -p …
--permission-mode`, and it "runs identically locally or in a cloud
environment." Two transports, and one hard constraint:

**Hard constraint:** the API must be reachable at a **stable URL from any host
an agent runs on** — a `localhost` service works for local agents but is
invisible to cloud agents. So the API is a *networked, authed* service (or a
tunnel), not a localhost bind. This is a hosting decision independent of
transport.

- **HTTP + curl (recommended to start).** The API is a networked service; a
  registry source-doc documents the `answers` contract; workers call it with
  `curl` under Bash (which bypassPermissions workers already have). **Zero
  launcher change**, works today, cloud-safe once the service is networked, and
  the provenance story is identical to web-source fetch discipline (quote the
  response verbatim, snapshot it). This is the natural first step: an API source
  is a web-source with a stable structured contract.
- **MCP wrapper (ergonomic upgrade, later).** Commit a project `.mcp.json` so
  every fresh clone auto-carries the tool, pre-approved via a committed
  `.claude/settings.json` (`enableAllProjectMcpServers`) so bypassPermissions
  workers just *have* it. Tool-native: schema-enforced args, structured results,
  no URL construction, discoverable in the tool list. Cost: a small approval
  addition to the otherwise-dumb launcher, and an MCP server process wrapping the
  HTTP service. Worth doing once the contract is stable and the ergonomics
  matter — not required to prove the concept.

Recommendation: **ship HTTP+curl first, keep "easily launch workers" true, add
the MCP wrapper as a later ergonomic layer** once the tree API contract has
settled. The registry manifest's `transport` field lets a source move from
`http` to `mcp` without changing what it *is*.

## Health & degradation

Reuse the existing **F3 source-health auto-demote**: the planner's vitals pass
probes each API's health endpoint exactly as it probes web-sources; N
consecutive failures demote/flag it with a re-promotion path, same as the wiki
demotion in `DECISIONS.md`. An API source is not special — it can be down, and
the swarm already knows how to route around a dead source.

## Division of labour — API vs KB

The point of the API is to **stop text-dumping what can be computed**. The line:

- **API answers** (live, never stored as KB prose): exact coordinates, hop
  distances, adjacency, region membership, and *allocation* — `solve(targets,
  budget) -> what got allocated`. An agent *asks* these.
- **KB stores** (durable, citable): what stats *exist* on the tree; keystone and
  notable *semantics* (what each does + build role); a *prose* map of where
  stat clusters and keystones sit *relative to each class start*; and the
  *findings* workers derive by querying the API. Plus a pointer telling agents
  *the API can answer* coords/paths/solving so they know to ask.

The end-state workflow this enables: a build-designing agent decides *which*
keystones and stats it wants (from the KB's semantics + region map), hands the
targets to the tree API's solver, and gets back a concrete allocation and point
cost — instead of trying to reason over a graph in text.

## Worked example — the passive tree API

- **Source:** `passive-tree-api`, kind `api`, transport `http`, tier `dataset`,
  backed by the same PoB parse as `data/passive-tree/` (kept as the API's
  backing data + verification layer, no longer citable KB).
- **Host:** natural home is on/beside the existing headless POBAI server the
  cron machine already runs for build sims (which also owns PoB's own
  pathfinding — the `/solve` endpoint can wrap it rather than reimplementing a
  Steiner solver). Must be exposed at a networked, authed URL for cloud agents.
- **Contract:** the `answers` block above.
- **KB reshape:** driven by Directive **D002** — tree docs stop embedding
  coords/hop-tables and capture stats-available + keystone semantics +
  region-relative-to-start prose + pointers to the API.

## Sequencing (this primitive -> the rest)

1. **This doc + D002** — define the kind, steer the live swarm's tree sweeps to
   the new shape now (no infra needed; workers write KB that won't need
   rewriting once the API lands).
2. **Build the tree API** (HTTP+curl) on/beside POBAI; register it; slim
   `data/passive-tree/` to backing+verification.
3. **Hoist the primitive into the template** during the template/instance split
   — the manifest, the snapshot-citation rule, the F3 health hook, and the
   bridge doc are all domain-agnostic and belong in the product; the specific
   `passive-tree-api` source stays in the instance.

## Open decisions (for owner, when we build)

- **Transport at build time:** confirm HTTP+curl first vs jump straight to MCP.
- **Solver scope:** wrap PoB's own pathfinder via POBAI vs a purpose-built
  target+budget solver (start by wrapping).
- **Hosting/auth:** how the networked API is exposed to cloud agents (tunnel vs
  hosted vs same-host-only for now — gates whether cloud workers can use it).
