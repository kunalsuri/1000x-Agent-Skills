# `.claude/` — Claude Code project configuration

`CLAUDE.md` at the repository root is the instruction file Claude Code reads
on every session. This directory holds the project-scoped configuration that
sits alongside it, mirroring `.agents/` for the other supported assistants.

| Path | Purpose |
|---|---|
| `.claude/settings.json` | Project-scoped Claude Code settings, when the repository needs any. Absent until then. |
| `.claude/skills/` | Project-local skills, if any are added. The published catalogue lives in `skills/`, not here. |

Two things this directory is deliberately **not**:

- **Not the install target.** `python scripts/install_to_agent.py --target claude`
  writes to `~/.claude/skills/` in your home directory, never into the
  repository. Installing into a checkout would put unversioned copies of every
  skill inside the tree the digests are computed over.
- **Not a second source of truth.** `skills/custom/` is canonical. `.agents/skills/`
  is a byte-identical mirror enforced by `tests/unit/test_agents_mirror_parity.py`.
  Adding a third copy here would give drift somewhere new to hide.
