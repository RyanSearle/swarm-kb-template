# Template ↔ instance — topology and the lessons-back loop

## The principle (now enforced, not just asserted)

`DOMAIN.md` states: *"The single file that adapts the machine to a subject. Every
other file is domain-agnostic."* An audit of the reference instance confirmed this
held in practice — grepping every mechanism file for domain terms found **zero
real leakage** outside `DOMAIN.md` and the content trees (two stray provenance
lines aside). The split below makes the principle physical: mechanism lives in the
template; a subject lives in an instance.

## What is template vs instance

| Layer | Paths | Ships in template? |
|---|---|---|
| **Mechanism** | `AGENT.md`, `procedures/`, `scripts/`, `bin/`, `launch/`, `docs/design/`, `DESIGN.md`, `protocols/CONVENTIONS.md`, `tasks/_TEMPLATE.md` | ✅ verbatim |
| **Coordination format** | `protocols/DECISIONS.md`, `DIRECTIVES.md`, `QUESTIONS.md` | ✅ **headers + format only** — entries are instance state |
| **Spec** | `DOMAIN.md` | ✅ as a **skeleton** to fill |
| **Content** | `kb/`, `data/`, `tasks/T*`, `logs/*`, protocol *entries* | ❌ instance only (template ships empty dirs) |
| **Domain tools** | `tools/` (parsers, extractors, query APIs) | ❌ instance only (template ships `tools/README.md` convention) |

Rule of thumb: **if changing the subject would change the file, it is instance.**
Everything else is mechanism and belongs upstream.

## How an instance consumes the template

The instance is a **fork / "use this template"** of this repo — not a submodule
(that would complicate the deliberately-dumb throwaway-clone launcher). One
repo, one coordination plane, no runtime coupling.

## The lessons-back loop (both directions)

- **Instance → template.** A mechanism improvement discovered while running
  (better merge-safety rule, a launcher fix, a new procedure) is domain-agnostic
  by definition → open a PR against the template. `DECISIONS.md` entries that
  amended a *procedure* (not content) are the candidate list each cycle.
- **Template → instance.** When the template gains a mechanism improvement, the
  instance pulls it in with a scoped sync — cherry-pick / merge the mechanism
  paths only (the table above), never `DOMAIN.md` or content. Because mechanism
  files carry no domain content, these merges rarely conflict.

## Extraction plan (how this template was cut from the live instance)

1. **Audit** — classify every path (table above); grep mechanism for domain
   leakage. *(Near-zero — the discipline held.)*
2. **Materialize** — copy clean mechanism verbatim; empty the stateful protocol
   logs to header+format; skeletonize `DOMAIN.md`; add product docs. *(This tree.)*
3. **Publish** — create the template repo from this tree; keep the live run on the
   instance repo untouched (the swarm never stops).
4. **Rewire** — point the instance at the template as its upstream for the
   lessons-back loop.
