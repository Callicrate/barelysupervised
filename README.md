# BarelySupervised Codex plugin marketplace

This repository is a Codex plugin marketplace for BarelySupervised, a native explicit-only coordination skill.

## Deploy

1. Push this directory to a GitHub repository.
2. Add it as a marketplace source:

   ```text
   codex plugin marketplace add <owner>/<repo>
   ```

3. In the ChatGPT desktop app, open Plugins and enable BarelySupervised.

## Layout

- `.agents/plugins/marketplace.json` is the marketplace catalog.
- `plugins/bs/` is the plugin itself.

## What the plugin does

BarelySupervised is inert until explicitly invoked as `$bs:enable <task>`. That invocation normally coordinates at least one built-in subagent in the current thread, selecting its role, Persona, model, and reasoning effort from private references; direct work is reserved for a narrow high-confidence exception. It has no startup hooks, session-context injection, or automatic profile-installation step.
