#!/usr/bin/env python3
"""BarelySupervised plugin SessionStart hook.

Injects the main-agent routing context into the session and installs the
bundled subagent profiles into the project's .codex/agents directory. The hook
never overwrites existing files and fails open so it can never block a session.
Set BARELYSUPERVISED_SKIP_AGENT_INSTALL to skip writing subagent files.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _read_event() -> dict:
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _plugin_root() -> Path:
    configured = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent


def _install_agents(plugin_root: Path, project: Path) -> list[str]:
    source = plugin_root / "agents"
    if not source.is_dir():
        return []
    target = project / ".codex" / "agents"
    installed: list[str] = []
    for toml in sorted(source.glob("*.toml")):
        destination = target / toml.name
        if destination.exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(toml.read_bytes())
        installed.append(toml.stem)
    return installed


def main() -> int:
    event = _read_event()
    plugin_root = _plugin_root()
    cwd = event.get("cwd")
    project = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()

    try:
        context = (plugin_root / "hooks" / "context.md").read_text(encoding="utf-8")
    except Exception:
        context = ""

    installed: list[str] = []
    if not os.environ.get("BARELYSUPERVISED_SKIP_AGENT_INSTALL"):
        try:
            installed = _install_agents(plugin_root, project)
        except Exception:
            installed = []

    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    if installed:
        output["systemMessage"] = (
            f"BarelySupervised installed {len(installed)} subagent "
            "profiles into .codex/agents."
        )
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0)
