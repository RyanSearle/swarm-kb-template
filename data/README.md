# data/ — ground-truth datasets

Optional but powerful: parsed, machine-derived datasets (from game files, API
dumps, official data exports) collapse research tasks into merge-and-drift-
check tasks — in the source machine this made whole work streams ~10x faster.

Each dataset directory MUST contain a README stating:
1. provenance (tool, upstream version, export date),
2. regeneration recipe,
3. **its absence rule** — does "not in this dataset" mean "does not exist"?
   (differs per dataset; conflating these creates confident errors),
4. precedence vs other sources (releases newer than the export supersede it),
5. jargon policy — which fields are citable vs verification-only.
