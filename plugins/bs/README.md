# BarelySupervised plugin

This native plugin provides one explicit-only coordination skill: `$bs:enable <task>`.

## Contents

- `skills/enable/` holds the registered coordination skill, its UI metadata, and private role, Persona, and routing references.
- `assets/` holds the plugin icons used by the marketplace interface.

## Behavior

The plugin does nothing until the explicit invocation. That invocation normally delegates to at least one current built-in agent in the same thread; direct work is reserved for the skill's narrow high-confidence exception. Engineers use the built-in `worker` agent type; Analysts, Architects, and Reviewers use `default`. Routing labels supply only the selected Persona, model, and reasoning effort.
