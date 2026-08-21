**What & why**

**Design-constraint check** (see CONTRIBUTING.md):
- [ ] All coordination stays in git (no launcher smarts, no shared state files)
- [ ] Nothing domain-specific outside `problems/` / docs
- [ ] `bash -n bin/*.sh scripts/*.sh && python3 -m py_compile scripts/*.py` passes

**Tested how** (instance run, agent pass, or n/a for docs):
