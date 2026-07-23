# BarelySupervised Codex plugin marketplace

This repository is the hook-only Codex plugin marketplace for BarelySupervised. Python 3.11 or newer is required for its bootstrap.

## Install

1. Add this repository as a marketplace source:

   ```text
   codex plugin marketplace add <owner>/<repo>
   ```

2. Restart the Codex app.
3. Install and enable BarelySupervised from Plugins.
4. Open `/hooks` and trust the BarelySupervised `SessionStart` hook.
5. Start a bootstrap session. The hook installs the global payload.
6. Start a fresh session so Codex discovers the profiles and skill.
7. Invoke `$bs <task>`.

## Layout

- `.gitattributes` preserves LF payload bytes and marks PNG assets binary.
- `.agents/plugins/marketplace.json` is the marketplace catalog.
- `plugins/bs/` is the plugin itself.

## What the plugin does

The trusted hook installs all 16 bundled profiles into `${CODEX_HOME}/agents`, or `~/.codex/agents` when `CODEX_HOME` is unset. When set, `CODEX_HOME` must be an absolute path; a relative value fails open before any bootstrap files are created. It always installs the explicit-only skill to `~/.agents/skills/bs`, independent of the plugin name. First install takes over and replaces the entire existing global `~/.agents/skills/bs` path. Per-`CODEX_HOME` agent authority is recorded in `${CODEX_HOME}/barelysupervised-install.json`, or the fallback under `~/.codex`. HOME-wide skill authority is recorded in `~/.agents/barelysupervised-skill-install.json`. Matching persistent locks serialize both independent version decisions and the transaction. Write-ahead version floors prevent an older payload from downgrading an interrupted or complete newer domain. A new `CODEX_HOME` may install its agents while retaining a verified newer shared skill; neither domain is downgraded. Unrelated global files remain untouched. The hook emits no developer context and successful exact repeat starts are no-ops.

> Uninstalling the plugin does not remove the global profiles or skill. There is no uninstall or cleanup feature.
