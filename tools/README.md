# tools/ — domain data-tools (instance-provided)

Convention slot for the tools that turn a domain's raw sources into what the KB
and agents consume: dataset **extractors/parsers**, and **query APIs** that serve
knowledge agents interrogate rather than read (see
`docs/design/queryable-sources.md`).

**This directory is instance-specific** — the template ships only this note. Put
your domain's tooling here and register any API it exposes in `DOMAIN.md`'s source
table + `kb/meta/sources-guide.md`.

Reference instance (poe2-build-kb) ships, for example:
- `tools/extractors/` — stdlib parsers turning a Path of Building 2 checkout into
  the `data/` datasets (passive tree, skill/support gems, uniques).
- `tools/tree-api/` — a queryable source: the passive tree served as structured
  JSON (keystone/notable lookup, hop-distance, allocation) instead of a text graph
  dump agents can't reason over.
