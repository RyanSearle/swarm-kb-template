# Swarm Knowledge-Base System — Design Document (v0.4)

> **Status:** single-vs-multi fork **resolved** — multi-agent concurrency is the
> committed baseline (§0.1). Ready to build against; remaining open items are the
> narrower Part D decisions. Synthesizes the learnings from the
> `poe2-kb` autonomous machine into a domain-agnostic design. Companion to
> `TEMPLATE_NOTES.md` (design rationale) and the existing `swarm-kb-template/`
> (first implementation of the concurrency mechanics).
>
> **Scope of this doc:** how to *structure information* in an arbitrary domain
> where new facts arrive continually and the corpus must *restructure itself*,
> under the hard constraint that **no single agent can hold the whole KB in its
> context window**; how to *schedule heterogeneous agent runs* as a function of
> KB *maturity*; and how to use *git as the coordination substrate* so many
> agents run at once without conflicting.
>
> **Out of scope (assumed given):** the initiator supplies the domain goal and
> the information sources (web searches, git repos, APIs, PDFs, datasets). This
> doc is about what happens *after* sources exist.

---

## 0. The one constraint that forces everything

**No agent ever holds the entire KB in context.**

Every design choice below is downstream of this single fact. The systems that
already live under this constraint — a large codebase (no one reads the whole
repo), Wikipedia (no editor reads all of it), a sharded database (no node holds
all rows) — converge on the same four moves, and so do we:

1. **Bounded units.** The atom is small enough that many fit in one context.
2. **Stable names.** References survive relocation, so structure can change
   without breaking the web of relations.
3. **Generated navigation.** The global "map" is a *build artifact*, always
   reconstructable from local metadata, never hand-maintained.
4. **Local coherence rules.** An agent editing a slice can keep it consistent
   with parts it never saw, by following conventions rather than reading globally.

If a proposed feature violates one of these, it will not survive contact with a
large corpus. Treat them as invariants, not preferences.

### 0.1 Architecture baseline — multi-agent concurrency from day one

**Decision (resolved):** the system is **multi-agent and concurrent from the
start.** We do *not* begin with a single global lease and "graduate" to
concurrency later — the git control plane of Part C is *foundational*, and the
whole design commits to it. Rationale: the coordination model is the single
hardest thing to retrofit; baking it in from day one is what makes the system
**scalable by adding agents / quota pools** rather than by rewriting the loop.
Every structural and scheduling choice below is chosen to be **conflict-free
under N concurrent writers**, not merely correct for one.

**A single agent is just the N=1 degenerate case.** With only one agent awake it
claims the integrator role, does a task, and merges its own branch serially — the
*exact same code path*, no special mode, no separate lease machinery. So
"multi-agent from the start" adds **zero** operational overhead when the KB is
small or only one quota pool is funded; it simply means nothing has to change when
the second agent wakes. **Scale is a dial** (how many agents/pools you run), not a
migration. Two consequences worth stating up front, because they ripple through
the whole design:

- There is **no global-lease / crash-recovery apparatus** (dirty-tree triage,
  orphan reconciliation, lock staleness). Branch isolation + discard-on-failure
  (C3) replaces all of it from day one.
- **No shared mutable state file.** Counters, phase, and cursors are *derived*
  from git history and per-doc frontmatter, never stored in a file every agent
  writes (C5). This is a baseline invariant, not an optimization.

---

## Part A — Structuring an arbitrary domain

### A1. The atomic unit: the bounded node doc

- One **node doc = one concept.** Self-contained, human- and LLM-readable,
  **size-capped** (a soft byte budget, e.g. target ≤ ~6–8 KB of prose; split
  when exceeded). The cap is not cosmetic — it is *what makes locality possible.*
  An agent can pull "the ~15 docs relevant to this task" into context precisely
  because each doc is small and about exactly one thing.
- Every node carries **frontmatter** = its machine-readable interface:
  - `id` / `slug` — **stable, location-independent identity** (see A2).
  - `type` — the taxonomic class (domain-defined enum).
  - `tags` — cross-cutting labels (the seeds of future structure).
  - `related` — outbound graph edges, **by id/slug, never by path**.
  - `sources` + `confidence` — provenance (see A5).
  - `last_verified` — currency cursor (freshness track).
  - `last_deep_reviewed` — quality cursor (independent of freshness; see B4).
  - `maturity` / `status` — stub | drafted | enriched | verified.
- **Body shape is a domain convention** but should be brief and act-on-able
  first, detail second. Cite sibling docs rather than restating them (redundancy
  is future drift).

> **poe2-kb evidence:** per-unique / per-gem / per-ascendancy docs. The
> ascendancy *split* (one class doc → 32 per-ascendancy nodes) is the template
> for "a node got too broad; shard it into first-class nodes." The size cap is
> what turned "class doc" into a code smell.

### A2. Two orthogonal axes — always two, never one

A single hierarchy cannot serve both retrieval and synthesis. Maintain two:

| Axis | What it answers | Physical form | Purpose |
|---|---|---|---|
| **Taxonomy** | *Where does this fact live?* | one canonical folder home per node | **retrieval** / filing |
| **Graph** | *How does this fact relate to others?* | `related:` edges → generated `## Related` blocks + a graph view | **synthesis** / discovery |

The decisive learning: **structure is by type, but value is cross-type.** The
taxonomy files a fact once; the graph is where an agent *composes* facts that the
taxonomy filed far apart. In poe2-kb this became the `kb/interactions/` layer —
each doc a named cross-type synergy (unique × gem × passive × ascendancy),
turning the graph's hubs into build-defining concepts. Every domain has this
cross-type layer; it is usually the most valuable and the last to be built.

**Why this makes self-restructuring tractable (the key idea):**

> The taxonomy *will* eventually be wrong — new information does not respect your
> initial folders. But the **graph is robust to taxonomy churn** *iff edges are
> content-addressed* (point at `id`/`slug`, not file path). You can move, split,
> merge, and re-file nodes freely and the web of relations survives the move.

This is the entire mechanism behind "restructure itself." It only holds if a
**link-integrity gate** is enforced (A4) so relocation breakage surfaces the
instant it happens instead of rotting silently.

> **poe2-kb evidence, both signs:** *negative* — 388 cross-refs had silently
> rotted before we built the gate. *positive* — after the gate, the index-rename
> (29 files) and the ascendancy-split (thousands of refs) both moved with
> `MISSING` held at **0**. Relocation stopped being scary.

### A3. Global structure is generated, never authored

- **Indexes, catalogues, topic trees, tag pages, and the `## Related` block in
  each doc are build artifacts** — regenerated from per-doc frontmatter by a
  script, never hand-edited.
- Therefore **"restructuring" = edit frontmatter on N nodes + regenerate.** No
  agent hand-maintains a global structure it cannot hold in context.
- Bonus: generated files are **not a merge-conflict source** (they're rebuilt by
  the integrator after merge — see Part C), which is why they're safe under
  concurrency.

> **Rule:** if a human or agent is tempted to *edit* an index, that index should
> have been *generated*. Author the source-of-truth field; generate the view.

### A4. The link-integrity gate (the safety rail for self-restructuring)

A small, stdlib-only script with three modes, run on **every** agent run:

- `--check` — resolve every `related:` target; **exit non-zero + list any that
  don't resolve.** This gates the run at start and end (pre/post condition).
- `--apply` — repoint resolvable-but-moved edges, regenerate each doc's
  `## Related` block between fixed markers. Run after any create / move / rename.
- default (dry-run) — report only.

Resolution ladder (most-specific first): exact id → semantic remap (a small
alias table for merged/renamed concepts) → spelling/normalization → unique-basename
fallback → **MISSING** (flagged, never silently dropped). Naming rule: **never
author a doc literally named `index.md`** — use `<folder>-index.md` so every
graph node has a unique, legible label (the "29 identical index nodes" failure).

> This is the single highest-leverage piece of infrastructure. Build it on **day
> one**, not as a rescue mission. It is what converts "structure is frozen because
> changing it breaks links" into "structure is fluid because breakage is caught."

### A5. Provenance, freshness, and the substantive-change anchor

- Every claim traces to `sources` with a **confidence tier**; a source registry
  records fetch quirks and per-source trust rules.
- **Ground-truth vs authority division of labour:** where the domain has both
  parsed ground-truth data (a repo, a dataset, an API export) *and* a
  human-readable authority (a wiki, docs), treat parsed data as primary and the
  authority as a drift-check, with precedence by export date. Portable idea:
  *parsed data is the oracle for existence/values; prose is the oracle for
  meaning; a third oracle (a validator/simulator, if any) confirms magnitudes.*
- **Distinguish the version that gates freshness from the version that is merely
  current.** Not every upstream change is a *content* change. Keep two version
  markers: `current_version` (raw latest) and `substantive_version` (the anchor
  that a node's `last_verified` is compared against). A cosmetic/QoL upstream
  release bumps `current_version` and holds `substantive_version` — seeding
  **zero** re-verify work.

> **poe2-kb evidence:** the `current_patch` vs `current_gameplay_patch` split
> (D025). Three cosmetic patches (0.5.4c/d/e) in a row correctly seeded **no**
> reverify churn because the gameplay anchor held at 0.5.4b. This one distinction
> eliminated the machine's single largest source of wasted work.

### A6. Self-restructuring as first-class work

Restructuring is a **task type**, not an emergent accident. Its triggers are
**computable from local signals or cheap generated aggregates** — which is
exactly why a context-limited agent can drive *global* reorganization: it never
needs global context to *detect* the need, only to *execute one bounded refactor.*

| Trigger (locally computable) | Refactor action |
|---|---|
| node exceeds size cap | **split** into per-subconcept nodes; original → index |
| a tag has ≥ N members and no home | **promote** the tag to a subtree + generated index |
| two nodes share ≥ X% of their edges / high text overlap | **merge** candidate (flag for review) |
| a folder exceeds N nodes | **subdivide** by a secondary facet |
| a node has zero inbound links (orphan) | **wire** it in or question its existence |
| a concept is referenced but has no node ("red link") | **create** a stub node |
| a cross-type pattern recurs across many nodes | **extract** a synthesis/interaction hub |

Feed these triggers from the **generated aggregates** (index sizes, tag counts,
orphan lists, link-overlap matrix) that the build step already produces. The
planner/curator turns them into refactor tasks; workers execute them one at a
time; the link-integrity gate keeps the graph whole across every move.

### A7. Retrieval / locality — how an agent finds its slice

Because no agent holds everything, every run starts by reading a **bounded,
generated navigational map** (a topic tree / TOC / tag catalogue, byte-capped so
it always fits in context). From the map the agent identifies the handful of
nodes its task touches and pulls only those. Two complementary retrieval modes:

1. **Structured map-first (default):** deterministic, cheap, auditable. The map
   is regenerated each build; it is the entry point for every run.
2. **Semantic index (optional, for large corpora):** an embedding index over
   node bodies for "find nodes *about* X" when the taxonomy label is unknown.
   Treat as a *derived accelerator*, never the source of truth — it too is a
   build artifact, rebuilt on change.

> Design goal: **a task spec + the map + ~15 pulled nodes is always enough to do
> the work.** If a task routinely needs more, the task is mis-scoped or a node is
> too big (→ A1/A6).

---

## Part B — Agents, roles, maturity, and scheduling

### B1. Maturity is measured, not declared

The KB moves through phases, but the phase is **computed from signals**, so it
advances (and *reverts*) on its own:

| Phase | Dominant question | Typical role mix |
|---|---|---|
| **SEED** | do we even have a skeleton? | planner + a few workers; heavy structural churn expected |
| **BUILD-OUT** | is the topic tree covered breadth-first? | many parallel workers; taxonomy still fluid |
| **ENRICH** | is each node deep + cross-linked? | workers + researchers; graph/synthesis layer grows |
| **MAINTAIN** | is it fresh, correct, and self-healing? | event-driven verifiers + never-idle floor |

Signals that place the KB on this axis (all agent-computable, no global read):

- coverage ratio = nodes / known-topics (from the map + a topic registry)
- structural-debt count = open refactor triggers (from A6 aggregates)
- staleness backlog = nodes with `last_verified` behind `substantive_version`
- unverified-claim count = nodes at low confidence / `verified:false`
- link-integrity = MISSING count (should be 0)
- question backlog = open owner questions

**Reversibility is the point:** a large new source drop reopens BUILD-OUT even in
a mature KB; the mix shifts back automatically. (This is the generalization of
poe2-kb's two-tier auto-revert: Tier-1 real work always preempts Tier-2
fallback, and resumes the moment an event surfaces work.)

### B2. Role catalogue (different tasks → different agents)

Each role is a distinct *procedure* with its **own cadence and its own tool
permissions**. Permission-per-role is a real safety and quality lever, not
bureaucracy.

| Role | Does | Web? | Source access? | Writes main? |
|---|---|---|---|---|
| **Planner** | reads map+signals; emits/retires tasks; decides refactors; sets phase | no | no | via integrator |
| **Worker / Author** | executes one content task on a slice (create/enrich) | no | no | via integrator |
| **Researcher / Scout** | source discovery; new candidate facts; cross-type synthesis | **yes** | yes | via integrator |
| **Verifier / Auditor** | event-driven freshness re-check + periodic capability self-test | limited | **yes** | via integrator |
| **Curator / Refactorer** | structural health: splits/merges/promotes; link-integrity | no | no | via integrator |
| **Groundskeeper** | never-idle quality floor: deep-review rotation | no | no | via integrator |
| **Integrator** | *the only writer of main*; serial merge; conflict bounce-back | no | no | **yes** |

> The **capability self-test** (Verifier) is the steering feedback loop: "can a
> downstream consumer accomplish the domain's end-goal from the KB *alone*?" It
> emits gap tasks and is what keeps the KB honest about its own completeness.
> Port it into every domain.

### B3. The scheduler is data, not prose

Generalize the RUNBOOK's mode-selection *if-ladder* into a **declarative policy
table** the dispatcher evaluates each slot. This is what makes the schedule
*configurable by maturity* the way you want:

```yaml
# schedule.policy.yaml  (illustrative)
priority_override: directives.priority == high     # owner can always jump the queue
tiers:
  - name: tier1_real_work         # always wins after priority override
    when: any([events_pending, coverage_gap, staleness_backlog>0, structural_debt>threshold])
    roles: [planner, worker, verifier, curator]
  - name: tier2_generative        # only when tier1 is dry
    when: tier1 == empty
    roles: [researcher, groundskeeper]   # alternated, so neither starves
cadences:
  verifier:      { trigger: [source_event, "every N runs"], cap: 2 }
  planner:       { trigger: ["backlog_empty AND (runs_since_plan>=K OR event)"] }
  curator:       { trigger: ["structural_debt>threshold"], cap: 1 }
  researcher:    { trigger: [tier2_slot], web: true }
phase_overrides:
  BUILD_OUT:  { worker.cap: 8,  researcher.cap: 0 }   # breadth first; research later
  MAINTAIN:   { worker.cap: 2,  verifier.priority: high }
```

Properties this buys you:
- **Tune the machine by editing data, not procedures.** Change the mix per phase
  without touching agent code.
- **Auto-revert built in:** `tier1.when` re-fires the instant an event lands, so
  generative work yields to real work with no manual switch.
- **Per-phase concurrency caps** (respecting the 15-file-change / run-budget
  limits) live in one legible place.

### B4. Two independent clocks — freshness vs quality (anti-churn)

The most expensive mistake to re-learn: **calendar-driven re-verification of a
growing corpus scales as corpus × window and eats the entire loop.** Prevent it
structurally:

- `last_verified` — **currency.** Advanced *only* by event-driven verification
  (a source changed). Never by a calendar sweep. `last_verified` is *provenance,
  not a scheduler.*
- `last_deep_reviewed` — **quality.** An *inexhaustible* groundskeeper floor that
  rotates through all nodes improving depth/organization, and **must never touch
  `last_verified` or the version stamp.** Its bar is a *substantive* change or a
  recorded judgment — never a bare date bump.

Keeping the two clocks fully independent is what lets the machine be "never idle"
*without* recreating busywork churn.

> **poe2-kb evidence:** D025 (kill calendar reverify) + D030 (add a substantive
> quality floor) looked contradictory but are opposite ends of one value ladder.
> Together they turned 21 idle runs into productive work with zero stamp-churn.

### B5. The event / source-change model

- Each source type has a **change detector**: git repo → new commits/tags; web →
  changelog/RSS/etag/content-hash; API → version endpoint; dataset → export hash.
- An event seeds **Tier-1 verify tasks** for directly-affected nodes **and walks
  the graph** to re-check every *synthesis* node whose `related:` references a
  changed node — a change may have *broken* a cross-type interaction, not just
  edited a leaf. (This "blast-radius into the synthesis layer" is the operational
  payoff of content-addressed edges.)
- Classify each event **substantive vs cosmetic** (A5) before seeding — cosmetic
  events seed nothing.

---

## Part C — Git as the concurrency & task substrate

This is the **foundational coordination substrate** (§0.1), not an optional
add-on. **Reframe:** content work is *embarrassingly parallel*; **all** contention
lives in the control plane. So the design goal is a control plane with almost
nothing to contend on — every mechanism below must hold for **N concurrent
writers** and degrade cleanly to the N=1 case (one agent that happens to be its
own integrator).

**Dispatch model.** Each scheduler tick (cron, or continuous) wakes one or more
agents — potentially across separate machines / quota pools. Every waking agent
independently: fetches refs → evaluates the policy table (B3) against the current
signals → **claims** the highest-priority available task (C2) → works in
isolation (C3) → pushes a ready branch (C4). No central dispatcher hands out work;
agents self-assign by winning claims. Adding capacity = waking more agents.

### C1. Sharded task ledger

- One file per task: `tasks/T####.md`, **status in its own frontmatter**
  (`todo | claimed | ready | done | bounced`). Never a monolithic backlog — that
  single file is conflict-magnet #1.
- Task specs are **fully self-contained** (goal, definition-of-done, source
  hints, affected node ids) so any agent can execute one with only the map + the
  named nodes.
- Batch related items into one task (cap-friendly), never one task per trivial item.

### C2. Claims as git refs (atomic CAS, no lock server)

- Claiming a task = create a unique empty commit (agent-id + timestamp) and push
  it to `refs/claims/T####`. **Ref creation succeeds for exactly one pusher;**
  everyone else is rejected non-fast-forward. That *is* the mutex.
- **TTL reap:** any agent deletes claims older than the TTL, so a dead agent
  orphans **one task**, not the machine.
- **Role election is just another claim:** `refs/claims/role/integrator` — first
  to claim it is the integrator for the TTL window.
- (This is `scripts/claim.sh`, already built and race-tested in the template.)

### C3. Branch-isolated work, discard-on-failure

- One **branch/worktree per task.** Work happens off main; **failure = delete the
  branch + drop the claim.** No partial state ever touches shared history.
- This **replaces the entire single-lease crash-recovery apparatus** (dirty-tree
  triage, orphan reconciliation, lock staleness). Partial work in a shared tree
  was the *only* reason that machinery existed.
- Workers push a finished branch to `refs/ready/T####` and **never touch main.**

### C4. One integrator, serial merge (the cheap serialization point)

- A single leader-elected **integrator** merges `refs/ready/*` into main
  **serially**, flips task status, rebuilds all generated artifacts (indexes,
  graph blocks, counters), runs the link-integrity `--check` gate, and commits.
- On conflict, it does a **semantic markdown merge** (LLMs are good at this) or
  **bounces** the branch back to `refs/bounced/T####` with notes for the worker.
- Rationale: **working is slow and parallel; merging is fast and serial.** We
  reintroduce a single writer *deliberately*, but only at the cheap point.
- **Does the single integrator become the bottleneck at scale?** Only if merge
  throughput can't keep up with worker output — which is far off, since a semantic
  markdown merge of one branch is seconds against content tasks that take minutes.
  Escape hatches when it ever binds: (a) **shard the integrator by subtree** — one
  integrator per top-level taxonomy branch, each owning disjoint paths; cross-subtree
  conflicts are rare *because graph edges are content-addressed, not path-coupled*
  (A2), so subtrees merge independently; (b) batch-merge queued ready branches in
  one pass. Start with a single integrator; shard only when the `refs/ready/*`
  queue visibly backs up. This is the one place the design can scale horizontally
  *later* without a redesign — everything else is already N-writer-safe.

### C5. Conflicts designed away by construction

| Conflict magnet (single-agent design) | Concurrent-design fix |
|---|---|
| monolithic backlog | shard → one file per task (C1) |
| generated indexes / catalogues | rebuilt by integrator post-merge; workers never edit them (A3) |
| **shared `STATE.json` counters** | **derive counters from git history / the run-log directory** — do not store a file every agent writes |
| owner protocols (`QUESTIONS.md`, `DIRECTIVES.md`) | shard (`questions/Q####.md`) *or* only the integrator writes them |
| run logs | append-only, **one file per writer** (`logs/<agent>-<run>.md`) |
| the single commit | only the integrator commits main |

> **No shared mutable state file** is a baseline invariant (§0.1), not a tweak: a
> stored, every-agent-written counter file is a guaranteed conflict under
> concurrency. **Counters, phase, and cursors are *derived* on demand** (from
> `git log`, the `runs/`+`tasks/` listings, and per-doc frontmatter), not stored.
> Idempotent derivation beats coordination everywhere it can.

### C6. Idempotency as a first-class rule

Under concurrency, *any* "read a watermark, act once" pattern is a latent bug (a
single misread permanently orphans the action). Make application **idempotent**:
re-running a task converges to the same state; duplicate work from a re-issued
claim is a *token cost, not corruption* (first merge wins, discard the loser);
answered-question / directive pickup checks the referenced item **directly**, not
via a timestamp watermark.

---

## Part D — Open decisions (forks to resolve before build)

1. **~~Single-lease vs full multi-agent.~~ RESOLVED → multi-agent baseline
   (§0.1).** The system commits to the git concurrency plane (Part C) from day
   one; a single agent is the N=1 degenerate case of the same code path, so there
   is no migration cost to being concurrency-native early. Scale is a dial (agents
   × quota pools), the integrator is the only component that scales horizontally
   *later* (C4), and everything else is N-writer-safe by construction. *This fork
   is closed; the remaining items below are the still-open decisions.*
2. **Semantic index: in or out for v1?** Adds a real retrieval capability for big
   corpora but also an embedding pipeline to maintain. Recommendation: **out for
   v1** (map-first is enough up to a few thousand nodes); revisit when the map
   itself stops fitting a context window.
3. **How aggressively to auto-refactor.** Splits/merges are powerful and
   destabilizing. Recommendation: **auto-execute the safe, reversible ones
   (promote-tag, create-stub, wire-orphan); flag the lossy ones (merge, big
   split) for a planner/owner decision.**
4. **Sharded vs integrator-owned owner protocols** (C5) — sharding is more
   concurrent but scatters the owner's inbox; integrator-owned keeps a single
   readable file at the cost of one more integrator responsibility. Lean
   integrator-owned for owner-facing ergonomics.
5. **Domain-config surface.** What exactly the initiator must fill: goal +
   definition-of-done + capability-test; source registry + per-source trust/quirk
   rules; node `type` enum + body conventions; the event detectors; the
   substantive-vs-cosmetic classifier. Everything else is the generic engine.

---

## Part E — Launch / compute layer

The design so far describes *what agents do* and *how they coordinate*; this part
describes *what spins them up*. The §0.1 principle makes it small: because all
coordination lives in git, **the launcher is dumb** — its only job is "wake an
agent that reads `AGENT.md`, on some cadence, N at a time." Three decoupled planes:

- **Coordination plane** — the git **remote**: the single shared source of claims
  (`refs/claims/*`), ready branches (`refs/ready/*`), and `main`. Every agent,
  wherever it runs, coordinates only through here. *Prerequisite for any
  multi-agent operation: a real remote.*
- **Compute plane** — whatever spawns sessions. Interchangeable and mixable:
  local `launchd`/cron, cloud scheduled agents, or both. Knows nothing about the
  work.
- **Policy plane** — `schedule.policy.yaml` + `DOMAIN.md` triggers, in the repo.
  Read by agents (self-limit) and optionally by the launcher (fan-out size).

### E1. The uniform entrypoint

Every agent — local or cloud — is spawned the same way: **clone the remote into a
throwaway working copy, read `AGENT.md`, do one unit, push, exit.** The throwaway
clone is what makes N local agents safe (no shared-working-tree collisions) and is
*identical* to how a cloud agent naturally starts, so the two backends run the
exact same `bin/agent-run.sh` with no divergence.

- `bin/agent-run.sh` — one agent, one unit of work (clone -> elect role -> claim
  -> work -> push -> cleanup).
- `bin/swarm-tick.sh` — the scheduled entry the launcher fires; backlog-aware
  fan-out of up to `MAX_AGENTS` parallel `agent-run.sh`, floor of 1 so an empty
  backlog still elects a planner.

### E2. Local compute (the default)

A single `launchd` job (macOS) or cron entry fires `swarm-tick.sh` on an interval.
Uses the owner's own Claude quota, runs on the owner's machine, zero new
infrastructure. `MAX_AGENTS` is the concurrency dial. Unattended operation needs a
non-prompting permission mode (`bypassPermissions`) — safe because each agent runs
in a throwaway clone holding no secrets — or a committed `.claude/settings.json`
allowlist. Limits: the machine must be on; one quota pool. See `launch/README.md`.

### E3. Cloud compute (scale-out)

The same entrypoint, fired by a scheduled cloud agent instead of `launchd`. Runs
when the local machine is off, in parallel across isolated environments, and can
draw on a second quota pool. Adopt when local throughput or uptime becomes the
bottleneck; no redesign — it clones the same remote and claims against the same
refs. Local + cloud can run at once (hybrid): they simply all claim against the
shared remote.

### E4. Scheduling by maturity

Two cheap levers, no central dispatcher:
1. Agents read `schedule.policy.yaml` and self-limit the role mix for the current
   measured phase (B1/B3).
2. `swarm-tick.sh` sizes its fan-out from a backlog probe (open-task count,
   ready-queue depth): a deep backlog wakes more agents, a quiet KB winds down to
   a single heartbeat.
3. **Source pollers** are separate scheduled jobs (one per upstream source) that
   only detect change and seed events — naturally cron-shaped, kept distinct from
   worker fan-out.

### E5. Prerequisite: a configured domain

None of this does useful work until `DOMAIN.md` is filled (subject, sources, event
triggers, definition-of-done) — the planner plans against it and bootstrap task
`T0001` reads it first. Launch infrastructure is domain-agnostic; *launching for
real* waits on the domain config.

---

## Part F — Autonomy & self-correction (fire-and-forget)

**Motivation.** An audit of the reference machine's full intervention history
(32 owner directives + 20 owner questions) found that the *largest* class of
owner interventions were fixes the machine had **correctly diagnosed but was
rule-blocked from applying** — the "raise a question before touching your own
procedures" safety rail was itself the bottleneck. Fire-and-forget means closing
that gap: the owner should only ever touch the few things that are genuinely
theirs (Part F1, Tier C). Everything else the system detects, it should fix.

### F0. The governing pattern — propose → self-verify → apply → monitor → rollback

Replace every blocking *"raise a question and wait"* with a non-blocking loop.
This is the spine of the whole part:

1. **propose** — an agent drafts the change (a procedure edit, a doc split/merge,
   a source demotion, a coverage-target extension) as a normal work branch.
2. **self-verify** — a *second, adversarial* agent tries to REFUTE it; the change
   proceeds only if ≥N independent checks pass (reuse the integrator/critic
   election — the machinery already exists).
3. **apply** — merged like any other work, through the single integrator.
4. **monitor** — a *named metric* is watched over the next K runs (churn rate,
   coverage ratio, MISSING count, contradiction count, cost/run).
5. **rollback** — if the metric regresses past a threshold, **auto-revert the
   commit** and record why. `git revert` is the universal undo; this is a core
   reason the coordination plane is git.

Every autonomous change and its monitored outcome is appended to
`protocols/DECISIONS.md` (append-only) — the owner's audit trail and override
surface. This log *replaces* the questions-and-wait bottleneck for everything
except Tier C.

### F1. Autonomy tiers — what self-heals vs what stays yours

- **Tier A — fully autonomous (detect & fix, no human):** operational and
  quality fixes — granularity review (F2), vitals/health (F3), invariant guards
  (F4), dedup/contradiction (F5), link integrity, orphan repair.
- **Tier B — autonomous-with-default (act, log to DECISIONS.md, never block):**
  coverage-map extension within already-registered sources (F7), ambiguous
  entity classification (pick the *safe* default — never delete a real entity —
  log, proceed), source health-demotion / fallback-tool adoption (F3).
- **Tier C — owner-owned, stays manual BY DESIGN:** mission / goal / scope-
  direction, provisioning external secrets·datasets·access, irreducible
  aesthetic preferences. Do not automate these — make them the *only* thing the
  owner ever touches.

### F2. No decision is frozen (continuous re-derivation)

Structure, granularity, procedures, schema, and source-trust are all
**provisional and continuously re-derivable**. An agent must never treat existing
structure as authoritative *merely because it exists*. Convergence is guaranteed
not by freezing decisions but by (a) computable triggers, (b) hysteresis /
oscillation detection, and (c) the F0 monitor→rollback loop.

- **Granularity review** (closes the one-way-ratchet gap): a curator activity that
  can **split, merge, OR re-split differently**, chosen from computable signals
  (size cap, internal cohesion, inbound-link clustering) — and it explicitly
  ignores whether a topic was split before. Anti-thrash: require a minimum
  cohesion delta and a cool-down before reversing a recent granularity change, so
  it converges instead of oscillating split↔merge every cycle. A prior split can
  never hinder a future re-granularization.

### F3. Self-monitoring / vitals — kills silent degradation

Each run runs a cheap **vitals check**: are my sources reachable? does my search
tool return non-empty results? am I producing net-new value or spinning on
identical outputs? do my derived-state invariants hold (F4)? On failure:
auto-demote a dead source, auto-adopt a working fallback tool, or throttle and
**alert loudly** in DECISIONS.md. *Evidence this is missing today:* a web-search
key ran dead for ~11 days, and wiki-403 / hallucinated-numeric-data conditions
were escalated-and-waited-on, all because nothing watched the machine's own vitals.

### F4. Invariant guards — kills scheduler runaway

The scheduler derives its state from counts; **assert the invariants it assumes**
each run (e.g. `runs_since_audit` must never exceed threshold+1). A violation
forces the affected gate and logs an anomaly. *Evidence:* an audit-cadence counter
once grew unbounded for ~19h across ~21 idle runs before a human noticed — a
one-line assertion would have caught it on run 1.

### F5. Anti-duplication & contradiction

Mandatory **pre-create existence search** — before writing a new node, search for
an existing one (dedupe; catches concurrent agents creating the same concept under
different slugs, and create-tasks whose premise is already satisfied). A periodic
**contradiction sweep** (doc-vs-doc and doc-vs-dataset) runs as curator work →
auto-fix, or a Tier-B decision when a source conflict needs a call.

### F6. Internal consumer / critic — closes the feedback loop

A **critic role** periodically attempts the domain's end-goal *from the KB alone*
(and, where an oracle engine exists, runs it) and files the gaps and
contradictions it hits as Tier-A tasks. This replaces the owner-run external
pilots that were previously the *only* source of "your docs are wrong/incomplete"
signal.

### F7. Self-extending coverage map

Agents may **extend the topic-tree and definition-of-done** when they discover a
new entity class in an *already-registered* source (Tier B: propose + default +
log). The system stops being able only to fill gaps *within* a frozen map and can
grow the map as it learns the domain — while the *mission* stays Tier C.

### F8. Self-amending procedures — highest leverage, build last

A `meta` task type may edit procedure / schema / convention files, **always**
through F0 (adversarial self-verify + monitor + auto-rollback + DECISIONS.md
entry). This is what converts the #1 intervention category to autonomous.
**Hard guard against self-granting authority:** a procedure change that would edit
the F0 loop itself, or move a Tier-C boundary, is NOT self-applicable — that
narrow class stays owner-gated. The system may improve how it works; it may not
rewrite the rules that keep it safe or redefine its own mission.

### F9. Build order

- **Pre-launch minimal set** (cheap, mechanical, kills the hardest-to-notice
  failure mode): **F3 vitals + F4 invariant guards + F2 granularity review.**
- **Next:** F5 dedup/contradiction, F7 map extension, F6 critic.
- **Highest-leverage, most care, build last:** F8 self-amending procedures and
  the F0 loop it depends on.

### F10. Guardrails that make autonomy safe

- **git revert is the universal undo** — every autonomous change is exactly one
  commit, so rollback is mechanical.
- **DECISIONS.md is an append-only audit trail** — the owner can veto or roll back
  any entry after the fact; autonomy is transparent, not opaque.
- **No self-granting of authority** (F8) — agents cannot edit the F0 loop or the
  Tier-C boundary.
- **Convergence over freezing** — hysteresis + oscillation detection on every
  reversible structure operation.
- **Cost/value governor** — vitals includes a value-vs-spend check; below a value
  floor the machine throttles rather than churns, so "never idle" never becomes
  "always spending."

---

## Appendix — poe2-kb learning → generalized principle

| Hard-won in poe2-kb | Generalized here |
|---|---|
| by-type folders + `kb/interactions/` cross-type layer | A2 two orthogonal axes (taxonomy + graph) |
| 388 silently-rotted links → link-integrity gate (D027) | A4 gate as day-one infrastructure |
| index-rename + ascendancy-split held MISSING at 0 | A2 content-addressed edges survive relocation |
| `<folder>-index.md` naming (D028) | A4 unique legible node labels |
| `current_patch` vs `current_gameplay_patch` (D025) | A5 substantive-vs-current version anchor |
| calendar reverify ate the loop (D007/D017) | B4 freshness is event-driven, not scheduled |
| `last_verified` + `last_deep_reviewed` split (D030) | B4 two independent clocks |
| phase model + two-tier auto-revert (D018/D031) | B1/B3 measured maturity + data-driven scheduler |
| research mode is web-allowed; workers are not | B2 permission-per-role |
| capability self-test emits gap tasks (Q006/D008) | B2 the steering feedback loop |
| patch → interaction blast-radius (D031 R-2) | B5 events walk the graph |
| git-ref claim CAS, integrator, discard-on-failure | C2–C5 git as the control plane |
| watermark-miss orphaned an answer (T388) | C6 idempotency over coordination |
| byte caps not line caps; one-line commits; `git add -A` | build-time invariants (see TEMPLATE_NOTES) |

---

*v0.2 — single-vs-multi fork resolved (multi-agent baseline, §0.1). Next: settle
the remaining Part D decisions (semantic index, auto-refactor aggressiveness,
protocol sharding, domain-config surface), then evolve `swarm-kb-template/` to
implement the full stack — Parts A–B (structure + scheduling) on top of the Part C
concurrency plane, which the existing `scripts/claim.sh` already seeds.*
