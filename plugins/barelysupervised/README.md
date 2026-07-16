# BarelySupervised plugin

This Codex plugin bundles the BarelySupervised roster as skills plus a SessionStart hook.

## Contents

- `skills/` holds one coordination skill and one skill per role.
- `agents/` holds the rendered subagent profiles as Codex TOML.
- `hooks/` holds the SessionStart hook that injects the routing context and installs the subagent profiles into the project `.codex/agents` directory.

## Hook behavior

The hook never overwrites existing files and fails open. Set `BARELYSUPERVISED_SKIP_AGENT_INSTALL` to inject context without writing subagent files. Codex requires you to trust the hook with `/hooks` before it runs.
