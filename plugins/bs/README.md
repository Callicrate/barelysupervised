# BarelySupervised plugin

This plugin provides one explicit-only coordination skill: `$bs:enable <task>`, plus a trusted SessionStart hook that installs its named custom agent profiles.

## Contents

- `agents/` holds the 16 named custom-agent TOMLs.
- `hooks/` holds the installation-only SessionStart hook.
- `skills/enable/` holds the registered coordination skill, its UI metadata, and private role, Persona, and routing references.
- `assets/` holds the plugin icons used by the marketplace interface.

## Behavior

The coordination workflow does nothing until its explicit invocation. After the hook is trusted with `/hooks` and a session is started or resumed, it installs missing bundled TOMLs into `.codex/agents` without overwriting existing files. `$bs:enable` then dispatches the exact installed profile named in its routing table. The hook is fail-open and never injects coordination context. Set `BARELYSUPERVISED_SKIP_AGENT_INSTALL` to skip profile installation.
