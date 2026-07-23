# BarelySupervised plugin

This hook-only plugin installs 16 global custom-agent profiles and the explicit-only `bs` skill.

## Contents

- `hooks/` contains the trusted `SessionStart` bootstrap.
- `payload/agents/` contains exactly 16 custom-agent TOMLs.
- `payload/skills/bs/` contains the unregistered global skill payload.
- `assets/` holds the plugin icon used by the marketplace interface.

## Bootstrap

Trust the hook with `/hooks`, then start or resume a session. The hook writes agents to `${CODEX_HOME}/agents` or `~/.codex/agents` when `CODEX_HOME` is unset. When set, `CODEX_HOME` must be an absolute path; a relative value fails open before any bootstrap files are created. It always installs the skill at `~/.agents/skills/bs`. Start a fresh session after the bootstrap, then invoke `$bs <task>`.

Python 3.11 or newer is required. The hook uses `python3` and `py -3` on Windows. It preflights every source and target. First install never overwrites an unowned profile. First install takes over and replaces the entire existing global `~/.agents/skills/bs` path. Per-`CODEX_HOME` agent authority is recorded in `barelysupervised-install.json`; shared skill authority is recorded in `~/.agents/barelysupervised-skill-install.json`. Matching persistent locks serialize both independent version decisions and writes. The hook publishes write-ahead version floors before payload replacement, so older payloads cannot downgrade an interrupted or complete newer domain. A new `CODEX_HOME` may install its agents while retaining a verified newer shared skill. Unrelated global files remain untouched. Uninstalling the plugin does not remove these global files. There is no uninstall or cleanup feature.
