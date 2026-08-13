# DOMAIN — <your-instance-name>

> The single file that adapts the machine to a subject. **Every other file is
> domain-agnostic.** The PLANNER treats this file as the specification it plans
> against. Keep it under ~10 KB — it is read every planning session.
>
> This is the TEMPLATE skeleton. Fill every section for your domain, then delete
> these blockquote instructions. Walkthrough: `docs/INSTANTIATE.md`.

## Mission

<One paragraph. What knowledge base, for whom, and dense/cross-linked enough that
WHAT consumer can do WHAT from it ALONE. Name the consumer and the top-down axis
they read by (e.g. by scenario / entity / task).>

## Owner

<Name>. The DIRECTIVES / QUESTIONS / DECISIONS protocols address them.

## Scope (in)

- <One bullet per KIND of real-world atom this KB covers.>

## Scope (out)

- <Explicitly excluded: volatile / ephemeral / off-mission content. Being
  explicit here stops the planner wandering.>

## Primary sources (by confidence tier)

> Three source KINDS exist (see `docs/design/queryable-sources.md`): **file** you
> read (`data/`), **web** you fetch, **api** you query. Tier is per-source.

| Tier | Source | Notes / fetch quirks |
|---|---|---|
| official | <authoritative-for-CHANGES source> | classify each release before seeding tasks |
| dataset | <parsed ground-truth files in `data/`, if any> | PRIMARY values/existence. State each dataset's ABSENCE RULE + precedence. |
| api | <queryable sources> | interrogated not read; **snapshot-cite** answers; tier as its provenance warrants |
| datamine | <high-trust data-mined web source, if any> | fetch discipline: quote verbatim, navigate by URL shape |
| reference | <community reference> | medium confidence, prose/meaning |
| community | <guides / creators> | LOW; heuristics only, NEVER numbers |

**Two-oracle rule:** <values/existence oracle> = existence & values; prose =
meaning; a simulator/API, where available, = magnitude verification. Never assert
a magnitude from a community claim — mark it community-claimed + unverified.

## Release/event triggers (what re-validates existing content)

- <What EVENT forces re-validation, and how to derive tasks FROM the event's
  CONTENT (not a blanket re-sweep). Classify substantive vs cosmetic first.>
- Nothing is re-validated merely for being old (event-driven freshness).

## Definition of done (coverage targets — enumerable, fine-grained)

Granularity: **one doc per real-world atom** — small, self-contained nodes so the
interaction layer can link precisely and no agent needs the whole KB in context.

- <Enumerate coverage targets: every X has a doc; every Y covered; an index +
  leaf docs per Z subsystem; an interactions/ layer of named cross-type links.>
- **Capability self-audit:** periodically, can the consumer accomplish <the
  mission task> FROM THE KB ALONE? Each gap it hits → a task.
