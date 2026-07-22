# BarelySupervised Codex plugin marketplace

This repository is a Codex plugin marketplace for BarelySupervised, an explicit-only coordination skill with installable custom agent profiles.

## Deploy

1. Push this directory to a GitHub repository.
2. Add it as a marketplace source:

   ```text
   codex plugin marketplace add <owner>/<repo>
   ```

3. In the ChatGPT desktop app, open Plugins and enable BarelySupervised.
4. Trust the plugin hook with `/hooks`, then start or resume a session so it installs missing profiles into the project's `.codex/agents` directory.

## Layout

- `.agents/plugins/marketplace.json` is the marketplace catalog.
- `plugins/bs/` is the plugin itself.

## What the plugin does

BarelySupervised is inert until explicitly invoked as `$bs:enable <task>`. A trusted SessionStart hook installs any missing bundled custom-agent profiles into `.codex/agents` without overwriting existing files, but does not inject coordination context. The explicit skill selects and dispatches the exact installed profile for its role and Persona; direct work is reserved for a narrow high-confidence exception.
