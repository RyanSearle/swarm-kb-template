# CONVENTIONS — the load-bearing rules

Distilled from a reference instance's production lessons (the poe2-build-kb
run — see README). Everything here exists because its absence cost something
once; it is domain-agnostic and applies to any instance.

## Autonomy & self-correction (DESIGN.md Part F — the fire-and-forget rules)

The owner should only ever touch Tier C (mission; secrets/access; irreducible
aesthetics). Everything the system can DETECT, it FIXES — it never diagnoses a fix
and then waits for permission.

- **F0 loop for any change that is not a plain content edit** (a procedure/schema
  edit, a doc split/merge, a source demotion, a coverage-map extension):
  **propose -> adversarial self-verify (a second agent tries to refute) -> apply ->
  monitor a named metric -> auto-rollback (git revert) on regression.** Log it in
  protocols/DECISIONS.md.
- **No decision is frozen.** Structure, granularity, source-trust — and later,
  procedures — are provisional and continuously re-derivable. Never treat existing
  structure as authoritative merely because it exists. Convergence comes from
  computable triggers + hysteresis + the monitor->rollback loop, not from freezing.
- **Never fabricate to hide a failed vital.** A dead source, an empty search, a
  broken invariant is a finding to act on and log — never something to paper over.
- **protocols/DECISIONS.md is the append-only autonomy audit trail** — every self-
  made structural/operational decision plus the metric it was judged on. The owner
  reads it to audit and may veto/rollback any entry after the fact.
- **No self-granting of authority.** Self-amending procedures (Part F8, not yet
  enabled) may never edit the F0 loop or move a Tier-C boundary.

## Merge safety (why this machine can run concurrently at all)

1. **Sharded ledger** — one file per task. No agent ever edits a shared
   status list. The queue is a directory listing.
2. **Generated indexes** — index/catalogue pages are build artifacts
   (scripts/build_indexes.py, integrator-run). Hand-editing one is a bug.
3. **Derived state** — no counters file. Counts come from listing tasks/,
   grepping logs/. Nothing to conflict, nothing to drift.
4. **Append-only, one-file-per-writer logs** — logs/<agent-id>.md.
5. **Idempotent protocol processing** — set-comparisons against the file's
   current content, never "newer than my watermark" filters.
6. **Workers never touch main.** The integrator is the only writer — one
   serial choke point at the cheapest stage.
7. **Duplicates are a token cost, not corruption** — first merge wins;
   integrator discards losers without ceremony.
8. **Discard-on-failure** — no recovery of half-done branches. Keep tasks
   small enough that discarding one is cheap.

## Claims

- Claim TTL ≈ 3× a typical session duration ({{CLAIM_TTL_MIN:45}} minutes
  default — tune in scripts/claim.sh). Staleness by claim-creation age; no
  heartbeats (they only pay when sessions can legitimately outlive the TTL —
  if yours can, split the work instead).
- Anyone may reap expired claims. Reaping is always safe: the original
  worker's branch merges or gets discarded at the integrator, never in place.

## Content freshness

- **Event-driven, never age-driven.** `last_verified` and `volatility` are
  provenance/metadata. Re-validation tasks come from release contents,
  dataset diffs, and self-audit findings — except in MAINTENANCE phase, where
  age-rotation is exactly what idle capacity is for.
- Coverage of missing content outranks re-validation of existing content.

## Datasets (data/)

- Parsed ground-truth datasets are the preferred primary source; external
  authority (wiki/official prose) is the drift-check. Precedence: releases
  dated after the dataset export supersede it; at matching version the
  dataset beats transcribed prose.
- **Every dataset README must state its absence rule** ("absent = nonexistent"
  vs "absent = maybe generated/special") — they genuinely differ per dataset
  and conflating them creates confident errors in both directions.
- **Jargon policy**: machine-internal identifiers never reach the citable
  layer. Keep them in a verification-only artifact; human phrasing comes from
  human-facing sources. Fluent-but-wrong translation is worse than absence.

## Writing discipline

- Commit messages: one line, ≤200 chars. Detail lives in the session log.
- Plans/specs: BYTE caps, not line caps (line caps get gamed by long lines).
- Provenance taxonomies over raw fields (classify acquisition/origin enums
  where a bare number would mislead an LLM reader).
