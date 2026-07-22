#!/usr/bin/env python3
"""Install bundled agent profiles into the current project without overwriting files."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def _read_event() -> dict[str, Any]:
    """Return the SessionStart event payload, or an empty payload on invalid input."""
    try:
        raw = sys.stdin.read()
        value = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _plugin_root() -> Path:
    """Resolve the plugin root while preserving legacy environment compatibility."""
    configured = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(configured) if configured else Path(__file__).resolve().parent.parent


def _project_root(event: dict[str, Any]) -> Path:
    """Use the event working directory when available, otherwise the process directory."""
    cwd = event.get("cwd")
    return Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()


def _install_agents(plugin_root: Path, project_root: Path) -> list[str]:
    """Copy missing bundled TOMLs using exclusive creation to preserve existing profiles."""
    source_dir = plugin_root / "agents"
    if not source_dir.is_dir():
        return []

    target_dir = project_root / ".codex" / "agents"
    installed: list[str] = []
    for source in sorted(source_dir.glob("*.toml")):
        target = target_dir / source.name
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as source_file, target.open("xb") as target_file:
                target_file.write(source_file.read())
        except FileExistsError:
            continue
        except OSError:
            continue
        installed.append(source.stem)
    return installed


def main() -> int:
    """Install profiles if enabled, returning success even when installation is unavailable."""
    if os.environ.get("BARELYSUPERVISED_SKIP_AGENT_INSTALL"):
        return 0

    try:
        installed = _install_agents(_plugin_root(), _project_root(_read_event()))
    except OSError:
        installed = []

    if installed:
        output = {
            "systemMessage": (
                f"BarelySupervised installed {len(installed)} agent profiles into .codex/agents."
            )
        }
        sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception:
        exit_code = 0
    raise SystemExit(exit_code)
