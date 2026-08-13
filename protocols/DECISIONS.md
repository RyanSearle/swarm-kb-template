# DECISIONS — autonomous-decision log (append-only)

The audit trail for everything the machine changes about ITSELF or its structure
without asking the owner (DESIGN.md Part F). Append-only; newest at top. The owner
reads this to audit autonomy and may veto or roll back any entry after the fact
(`git revert` the referenced commit).

Logged here: doc split/merge/re-split (F2), source demotion or fallback-tool
adoption (F3), forced-gate anomalies / invariant violations (F4), and — once
enabled — dedup/contradiction fixes (F5), coverage-map extensions (F7), and
procedure/schema self-amendments (F8).

NOT logged here: ordinary content work — that lives in the run/session logs.

## Entry format

    ### <ISO-timestamp> · <agent-id> · <F2|F3|F4|F5|F7|F8>
    - change:    <one line: what changed>
    - trigger:   <the computable signal that fired>
    - verify:    <the refute-check that passed, or n/a for pure detection>
    - monitor:   <metric watched> over <K> runs; regression threshold <...>
    - commit:    <sha, once merged>
    - outcome:   <pending | held | auto-reverted @<sha> because <metric> regressed>

## Log

_(empty — no autonomous decisions logged yet.)_
