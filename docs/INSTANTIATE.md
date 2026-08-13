# Instantiate — run swarm-kb on your own domain

You configure ONE file and register your sources; the machine does the rest.

## 1. Take the template

GitHub *Use this template* → your new repo, or fork. Clone it. The default branch
is the single coordination plane every agent clones and pushes to.

## 2. Fill `DOMAIN.md`

This is the only domain-specific file — the spec the PLANNER plans against. Fill
every section (mission, owner, scope in/out, source tiers, event triggers,
definition-of-done) and delete the blockquote instructions. Keep it under ~10 KB;
it is read every planning session.

## 3. Register your sources

Sources come in three KINDS (`docs/design/queryable-sources.md`):

- **file** — parsed ground-truth you commit under `data/` (each with a README
  stating its **absence rule** + precedence). Preferred primary when you have it.
- **web** — pages agents fetch under fetch-discipline (quote verbatim).
- **api** — services agents *query* for computed/structured/spatial answers;
  **snapshot-cite** each answer. Host at a URL reachable from every agent host.

List them in `DOMAIN.md`'s source table and, for operational quirks
(reachability, URL shapes, fallbacks), in `kb/meta/sources-guide.md`.

## 4. Seed or bootstrap

Either drop a first task under `tasks/` (copy `tasks/_TEMPLATE.md`) or just launch
— with <5 open tasks the PLANNER role wins election and derives tasks from
`DOMAIN.md`'s definition-of-done.

## 5. Launch agents

- One agent, once: `bin/agent-run.sh` (clones fresh, elects a role, does one unit
  of work, pushes, exits). Set `PERMISSION_MODE=bypassPermissions` for unattended
  runs (safe: each agent is a throwaway clone holding no secrets).
- A scheduled swarm: install `launch/` (macOS launchd example provided;
  `bin/swarm-tick.sh` fires N agents per tick).

## 6. Watch

`python3 scripts/dashboard.py` → read-only board (open / in-progress / done),
merge queue, and a timeline, read live from your default branch.

## 7. Owner controls (while it runs)

- **DIRECTIVES.md** — append an instruction; the next planner applies it and
  moves it to Acknowledged.
- **QUESTIONS.md** — the machine never blocks on you; it asks here and proceeds
  on the safer interpretation. Answer by moving an entry to Answered.
- **DECISIONS.md** — the append-only autonomy audit trail; `git revert` any entry
  you want to roll back.

## 8. Send improvements home

Fixes you make to *mechanism* (anything but `DOMAIN.md` + your content) are
domain-agnostic — PR them back to the template. See
`docs/design/template-and-instance.md`.
