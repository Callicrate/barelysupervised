#!/usr/bin/env python3
"""Install or upgrade the versioned BarelySupervised global payload."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping

import tomllib

if os.name == "nt":
    import msvcrt
else:
    import fcntl

PROFILE_COUNT = 16
SKILL_NAME = "bs"
STATE_NAME = "barelysupervised-install.json"
SKILL_STATE_NAME = "barelysupervised-skill-install.json"
PAYLOAD_SCHEMA_VERSION = 1
AGENT_SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
SKILL_SCHEMA_VERSION = 1
LOCK_NAME = "barelysupervised-install.lock"
SKILL_LOCK_NAME = "barelysupervised-skill-install.lock"
LOCK_TIMEOUT_SECONDS = 5.0
LOCK_POLL_SECONDS = 0.05


class PreflightError(RuntimeError):
    """Raised when source or target state makes a zero-write bootstrap unsafe."""


@dataclass(frozen=True, slots=True)
class FilePayload:
    """One validated source file and its exact bytes."""

    relative: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class Payload:
    """The complete versioned plugin payload."""

    version: str
    agents: tuple[FilePayload, ...]
    skill_files: tuple[FilePayload, ...]
    skill_directories: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TargetChange:
    """One exact managed agent target selected for atomic replacement."""

    target: Path
    payload: bytes
    existed: bool


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """A fully preflighted transactional global install or upgrade."""

    payload: Payload
    agents_root: Path
    agent_changes: tuple[TargetChange, ...]
    all_agents: tuple[tuple[Path, bytes], ...]
    skill_root: Path
    replace_skill: bool
    state_path: Path
    state_payload: bytes
    skill_state_path: Path
    skill_state_payload: bytes
    retained_agent_version: str | None = None
    retained_skill_version: str | None = None


def resolve_targets(
    environment: Mapping[str, str], home: Path
) -> tuple[Path, Path, Path]:
    """Resolve global agent, skill, and ownership-state destinations."""
    if not home.is_absolute():
        raise PreflightError(f"home directory must be an absolute path: {home}")
    configured = environment.get("CODEX_HOME", "").strip()
    if configured:
        codex_home = Path(configured).expanduser()
        if not codex_home.is_absolute():
            raise PreflightError(f"CODEX_HOME must be an absolute path: {configured!r}")
    else:
        codex_home = home / ".codex"
    return (
        codex_home / "agents",
        home / ".agents" / "skills" / SKILL_NAME,
        codex_home / STATE_NAME,
    )


def plugin_root(environment: Mapping[str, str]) -> Path:
    """Resolve the installed plugin root from the hook environment or this file."""
    configured = environment.get("PLUGIN_ROOT", "").strip()
    return Path(configured) if configured else Path(__file__).resolve().parent.parent


def preflight(
    plugin: Path, agents_root: Path, skill_root: Path, state_path: Path
) -> InstallPlan:
    """Validate both ownership domains and every target before publishing floors."""
    payload = _load_payload(plugin / "payload")
    _validate_target_ancestors(agents_root, include_target=True)
    _validate_target_ancestors(skill_root, include_target=False)
    _validate_target_ancestors(state_path, include_target=True)
    skill_state_path = _skill_state_path(skill_root)
    _validate_target_ancestors(skill_state_path, include_target=True)

    raw_agent_state = _load_state(state_path, "agent ownership state")
    agent_authority, legacy = _agent_authority(
        raw_agent_state, payload, agents_root, skill_root
    )
    raw_skill_state = _load_state(skill_state_path, "skill ownership state")
    if raw_skill_state is not None:
        skill_authority = _skill_authority(raw_skill_state, payload, skill_root)
    else:
        skill_authority = _legacy_skill_authority(legacy, skill_root)
        if skill_authority is not None:
            try:
                _validate_skill_install(
                    skill_authority, skill_root, "legacy shared skill candidate"
                )
            except PreflightError as exc:
                raise PreflightError(
                    f"ambiguous legacy skill migration: {exc}"
                ) from exc

    agent_changes, all_agents, state_payload, retained_agent = _plan_agent_domain(
        payload, agents_root, state_path, agent_authority, legacy is not None
    )
    replace_skill, skill_state_payload, retained_skill = _plan_skill_domain(
        payload,
        skill_root,
        skill_state_path,
        skill_authority,
        raw_skill_state is None and skill_authority is not None,
    )
    return InstallPlan(
        payload=payload,
        agents_root=agents_root,
        agent_changes=agent_changes,
        all_agents=all_agents,
        skill_root=skill_root,
        replace_skill=replace_skill,
        state_path=state_path,
        state_payload=state_payload,
        skill_state_path=skill_state_path,
        skill_state_payload=skill_state_payload,
        retained_agent_version=retained_agent,
        retained_skill_version=retained_skill,
    )


def install(plan: InstallPlan) -> bool:
    """Publish write-ahead ownership floors, then apply both payload domains."""
    if not any(
        (
            plan.agent_changes,
            plan.replace_skill,
            plan.state_payload,
            plan.skill_state_payload,
        )
    ):
        return False

    _make_directory(plan.state_path.parent)
    _make_directory(plan.agents_root)
    _make_directory(plan.skill_root.parent)
    _make_directory(plan.skill_state_path.parent)
    transaction = Path(
        tempfile.mkdtemp(prefix=".bs-transaction-", dir=plan.state_path.parent)
    )
    skill_stage: Path | None = None
    agent_backups: list[tuple[Path, Path | None]] = []
    state_stages: list[Path] = []
    state_backups: list[tuple[Path, Path | None]] = []
    skill_backup: Path | None = None
    skill_committed = False
    committed = False
    preserve_recovery = False
    try:
        agent_stage = transaction / "agents"
        agent_stage.mkdir()
        for change in plan.agent_changes:
            _write_exclusive(agent_stage / change.target.name, change.payload)
        if plan.replace_skill:
            skill_stage = Path(
                tempfile.mkdtemp(prefix=".bs-stage-", dir=plan.skill_root.parent)
            )
            _populate_skill(
                skill_stage, plan.payload.skill_files, plan.payload.skill_directories
            )

        floors: list[tuple[Path, Path]] = []
        for target, payload in (
            (plan.state_path, plan.state_payload),
            (plan.skill_state_path, plan.skill_state_payload),
        ):
            if payload:
                stage = target.parent / f".bs-state-stage-{uuid.uuid4().hex}"
                _write_exclusive(stage, payload)
                state_stages.append(stage)
                floors.append((target, stage))
        for target, stage in floors:
            _publish_state_floor(target, stage, state_backups)

        backups = transaction / "backups"
        backups.mkdir()
        for change in plan.agent_changes:
            staged = agent_stage / change.target.name
            backup: Path | None = None
            if change.existed:
                backup = backups / change.target.name
                os.replace(change.target, backup)
                agent_backups.append((change.target, backup))
                os.replace(staged, change.target)
            else:
                os.link(staged, change.target)
                agent_backups.append((change.target, None))
                staged.unlink()

        for target, expected in plan.all_agents:
            _require_regular_file(target, "installed agent")
            if _read_bytes(target, "installed agent") != expected:
                raise OSError(f"installed agent verification failed: {target.name}")

        if plan.replace_skill:
            assert skill_stage is not None
            if _path_exists(plan.skill_root):
                skill_backup = plan.skill_root.parent / f".bs-backup-{uuid.uuid4().hex}"
                os.replace(plan.skill_root, skill_backup)
            os.rename(skill_stage, plan.skill_root)
            skill_stage = None
            skill_committed = True
            _verify_skill_payload(plan.skill_root, plan.payload)
        committed = True
    except (OSError, PreflightError) as exc:
        rollback_errors = _rollback(plan, agent_backups, skill_backup, skill_committed)
        if rollback_errors:
            preserve_recovery = True
        else:
            state_errors = _rollback_states(state_backups)
            rollback_errors.extend(state_errors)
            preserve_recovery = bool(state_errors)
        detail = (
            f"; rollback warning: {'; '.join(rollback_errors)}"
            if rollback_errors
            else ""
        )
        raise OSError(f"transaction failed: {exc}{detail}") from exc
    finally:
        for stage in state_stages:
            _remove_path(stage)
        if skill_stage is not None:
            _remove_path(skill_stage)
        if committed:
            if skill_backup is not None:
                try:
                    _remove_path(skill_backup)
                except OSError:
                    pass
            for _, backup in state_backups:
                if backup is not None:
                    try:
                        _remove_path(backup)
                    except OSError:
                        pass
        if not preserve_recovery:
            shutil.rmtree(transaction, ignore_errors=True)
    return True


def bootstrap(
    plugin: Path, agents_root: Path, skill_root: Path, state_path: Path
) -> str | None:
    """Run the fail-open bootstrap and return an optional hook system message."""
    try:
        with _bootstrap_locks(_lock_paths(state_path, skill_root)):
            plan = preflight(plugin, agents_root, skill_root, state_path)
            changed = install(plan)
    except PreflightError as exc:
        return (
            f"BarelySupervised bootstrap skipped: {exc}. "
            "Managed agent, skill, and ownership files were not changed."
        )
    except OSError as exc:
        return f"BarelySupervised bootstrap warning: {exc}. Managed files were recovered when possible."
    retained = _retained_message(plan)
    if retained is not None:
        return retained
    if not changed:
        return None
    return (
        f"BarelySupervised global install is current at {plan.payload.version} with 16 custom "
        "agents and $bs. Start a fresh session to discover changes."
    )


def main() -> int:
    """Run as a SessionStart hook and always fail open to Codex."""
    try:
        agents_root, skill_root, state_path = resolve_targets(os.environ, Path.home())
        message = bootstrap(
            plugin_root(os.environ), agents_root, skill_root, state_path
        )
    except PreflightError as exc:
        message = (
            f"BarelySupervised bootstrap skipped: {exc}. "
            "Managed agent, skill, and ownership files were not changed."
        )
    except (
        Exception
    ) as exc:  # The hook must never prevent a Codex session from starting.
        message = f"BarelySupervised bootstrap warning: unexpected error: {exc}."
    if message:
        sys.stdout.write(json.dumps({"systemMessage": message}, ensure_ascii=False))
    return 0


def _load_payload(root: Path) -> Payload:
    agents = _load_agent_payload(root / "agents")
    skill_files, skill_directories = _load_skill_payload(root / "skills" / SKILL_NAME)
    manifest_path = root / "manifest.json"
    _require_regular_file(manifest_path, "payload manifest")
    try:
        manifest = json.loads(
            _read_bytes(manifest_path, "payload manifest").decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"invalid payload manifest: {exc}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != PAYLOAD_SCHEMA_VERSION
    ):
        raise PreflightError("invalid payload manifest schema")
    version = _required_version(manifest.get("plugin_version"), "payload manifest")
    expected_agents = {item.relative: _sha256(item.payload) for item in agents}
    expected_skill = {item.relative: _sha256(item.payload) for item in skill_files}
    if (
        manifest.get("agents") != expected_agents
        or manifest.get("skill") != expected_skill
    ):
        raise PreflightError("payload manifest digests do not match bundled files")
    return Payload(version, agents, skill_files, skill_directories)


def _load_agent_payload(root: Path) -> tuple[FilePayload, ...]:
    entries = _directory_entries(root)
    if len(entries) != PROFILE_COUNT:
        raise PreflightError(
            f"payload must contain exactly {PROFILE_COUNT} agent TOMLs"
        )
    agents: list[FilePayload] = []
    names: set[str] = set()
    for path in entries:
        if path.suffix != ".toml":
            raise PreflightError(f"unexpected agent payload entry: {path.name}")
        _require_regular_file(path, "agent payload")
        payload = _read_bytes(path, "agent payload")
        try:
            value = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PreflightError(f"invalid agent payload {path.name}: {exc}") from exc
        if not isinstance(value, dict) or value.get("name") != path.stem:
            raise PreflightError(f"agent payload name must match filename: {path.name}")
        folded = path.name.casefold()
        if folded in names:
            raise PreflightError(f"duplicate agent payload name: {path.name}")
        names.add(folded)
        agents.append(FilePayload(path.name, payload))
    return tuple(sorted(agents, key=lambda item: item.relative))


def _load_skill_payload(root: Path) -> tuple[tuple[FilePayload, ...], tuple[str, ...]]:
    files, directories = _scan_tree(root, "skill payload")
    by_name = {item.relative: item.payload for item in files}
    skill = by_name.get("SKILL.md")
    if skill is None:
        raise PreflightError("skill payload is missing SKILL.md")
    try:
        text = skill.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError("skill payload SKILL.md must be UTF-8") from exc
    if "\r" in text:
        raise PreflightError("skill payload SKILL.md must use LF line endings")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise PreflightError("skill payload SKILL.md has invalid frontmatter")
    frontmatter = text[4:].split("\n---\n", 1)[0]
    if [line for line in frontmatter.splitlines() if line.startswith("name:")] != [
        'name: "bs"'
    ]:
        raise PreflightError('skill payload SKILL.md must declare name: "bs"')
    return files, directories


def _load_state(path: Path, label: str) -> dict[str, object] | None:
    if not _path_exists(path):
        return None
    _require_regular_file(path, label)
    try:
        value = json.loads(_read_bytes(path, label).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"invalid {label} structure")
    return value


def _agent_authority(
    value: dict[str, object] | None,
    payload: Payload,
    agents_root: Path,
    skill_root: Path,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    if value is None:
        return None, None
    if value.get("schema_version") == AGENT_SCHEMA_VERSION:
        _validate_agent_state(value, payload, agents_root)
        return value, None
    if value.get("schema_version") == LEGACY_SCHEMA_VERSION:
        _validate_legacy_state(value, payload, agents_root, skill_root)
        authority = {
            "plugin_version": value["plugin_version"],
            "agents_root": value["agents_root"],
            "agents": value["agents"],
        }
        return authority, value
    raise PreflightError("invalid agent ownership state schema")


def _validate_agent_state(
    value: dict[str, object], payload: Payload, agents_root: Path
) -> str:
    expected_keys = {
        "schema_version",
        "kind",
        "plugin_version",
        "agents_root",
        "agents",
    }
    version = _required_version(value.get("plugin_version"), "agent ownership state")
    agents = value.get("agents")
    expected_names = {item.relative for item in payload.agents}
    if (
        set(value) != expected_keys
        or value.get("schema_version") != AGENT_SCHEMA_VERSION
        or value.get("kind") != "agents"
        or value.get("agents_root") != str(agents_root)
        or not isinstance(agents, dict)
        or set(agents) != expected_names
        or any(not _valid_digest(digest) for digest in agents.values())
    ):
        raise PreflightError("agent ownership state does not match this CODEX_HOME")
    return version


def _validate_legacy_state(
    value: dict[str, object], payload: Payload, agents_root: Path, skill_root: Path
) -> str:
    expected_keys = {
        "schema_version",
        "plugin_version",
        "agents_root",
        "skill_root",
        "agents",
        "skill",
    }
    version = _required_version(value.get("plugin_version"), "legacy ownership state")
    agents = value.get("agents")
    skill = value.get("skill")
    expected_names = {item.relative for item in payload.agents}
    expected_skill_names = {item.relative for item in payload.skill_files}
    if (
        set(value) != expected_keys
        or value.get("schema_version") != LEGACY_SCHEMA_VERSION
        or value.get("agents_root") != str(agents_root)
        or value.get("skill_root") != str(skill_root)
        or not isinstance(agents, dict)
        or set(agents) != expected_names
        or any(not _valid_digest(digest) for digest in agents.values())
        or not isinstance(skill, dict)
        or set(skill) != expected_skill_names
        or any(
            not _valid_relative_path(path) or not _valid_digest(digest)
            for path, digest in skill.items()
        )
        or len({path.casefold() for path in skill}) != len(skill)
    ):
        raise PreflightError(
            "legacy ownership state does not match this global installation"
        )
    return version


def _skill_authority(
    value: dict[str, object], payload: Payload, skill_root: Path
) -> dict[str, object]:
    expected_keys = {
        "schema_version",
        "kind",
        "plugin_version",
        "skill_root",
        "files",
        "directories",
    }
    _required_version(value.get("plugin_version"), "skill ownership state")
    files = value.get("files")
    directories = value.get("directories")
    expected_files = {item.relative for item in payload.skill_files}
    if (
        set(value) != expected_keys
        or value.get("schema_version") != SKILL_SCHEMA_VERSION
        or value.get("kind") != "skill"
        or value.get("skill_root") != str(skill_root)
        or not isinstance(files, dict)
        or set(files) != expected_files
        or any(
            not _valid_relative_path(path) or not _valid_digest(digest)
            for path, digest in files.items()
        )
        or not isinstance(directories, list)
        or directories != sorted(set(directories))
        or any(not _valid_relative_path(path) for path in directories)
        or tuple(directories) != payload.skill_directories
    ):
        raise PreflightError("skill ownership state does not match this HOME")
    return value


def _legacy_skill_authority(
    legacy: dict[str, object] | None, skill_root: Path
) -> dict[str, object] | None:
    if legacy is None or legacy.get("skill_root") != str(skill_root):
        return None
    skill = legacy["skill"]
    assert isinstance(skill, dict)
    return {
        "plugin_version": legacy["plugin_version"],
        "skill_root": legacy["skill_root"],
        "files": skill,
        "directories": list(_implied_directories(skill)),
    }


def _validate_agent_install(
    authority: dict[str, object], agents_root: Path, label: str
) -> None:
    agents = authority["agents"]
    assert isinstance(agents, dict)
    try:
        entries = _directory_entries(agents_root)
        expected_folds = {relative.casefold() for relative in agents}
        by_fold: dict[str, Path] = {}
        for entry in entries:
            folded = entry.name.casefold()
            if folded in expected_folds and folded in by_fold:
                raise PreflightError(f"managed agent collides by case: {entry.name}")
            by_fold[folded] = entry
        for relative, expected in agents.items():
            target = by_fold.get(relative.casefold())
            if target is None:
                raise PreflightError(f"missing managed agent: {relative}")
            if target.name != relative:
                raise PreflightError(f"managed agent collides by case: {target.name}")
            _require_regular_file(target, "managed agent")
            if _sha256(_read_bytes(target, "managed agent")) != expected:
                raise PreflightError(f"managed agent digest mismatch: {relative}")
    except (OSError, PreflightError) as exc:
        raise PreflightError(f"{label} is incomplete or corrupt: {exc}") from exc


def _validate_skill_install(
    authority: dict[str, object], skill_root: Path, label: str
) -> None:
    files = authority["files"]
    directories = authority["directories"]
    assert isinstance(files, dict)
    assert isinstance(directories, list)
    try:
        actual_files, actual_directories = _scan_tree(skill_root, "managed skill")
        actual = {item.relative: _sha256(item.payload) for item in actual_files}
        if actual != files or actual_directories != tuple(directories):
            raise PreflightError("managed skill inventory or digest mismatch")
    except (OSError, PreflightError) as exc:
        raise PreflightError(f"{label} is incomplete or corrupt: {exc}") from exc


def _plan_agent_domain(
    payload: Payload,
    agents_root: Path,
    state_path: Path,
    authority: dict[str, object] | None,
    migrating: bool,
) -> tuple[tuple[TargetChange, ...], tuple[tuple[Path, bytes], ...], bytes, str | None]:
    incoming = {item.relative: _sha256(item.payload) for item in payload.agents}
    recorded_version: str | None = None
    upgrading = False
    if authority is not None:
        recorded_version = str(authority["plugin_version"])
        recorded = authority["agents"]
        assert isinstance(recorded, dict)
        relation = _compare_versions(recorded_version, payload.version)
        if relation == 0 and recorded != incoming:
            raise PreflightError(
                f"agent state version {payload.version} has different payload digests"
            )
        if relation > 0:
            _validate_agent_install(authority, agents_root, "newer agent installation")
            state_payload = _agent_state_bytes(recorded_version, agents_root, recorded)
            return (), (), state_payload if migrating else b"", recorded_version
        upgrading = relation < 0

    existing_agents = _directory_entries(agents_root, allow_missing=True)
    by_fold = {entry.name.casefold(): entry for entry in existing_agents}
    changes: list[TargetChange] = []
    all_agents: list[tuple[Path, bytes]] = []
    for item in payload.agents:
        target = agents_root / item.relative
        all_agents.append((target, item.payload))
        existing = by_fold.get(item.relative.casefold())
        if existing is None:
            changes.append(TargetChange(target, item.payload, False))
            continue
        if existing.name != item.relative:
            raise PreflightError(f"agent target collides by case: {existing.name}")
        _require_regular_file(existing, "agent target")
        actual = _read_bytes(existing, "agent target")
        if upgrading or actual != item.payload:
            if authority is None:
                raise PreflightError(f"unowned agent target differs: {item.relative}")
            changes.append(TargetChange(target, item.payload, True))

    desired = _agent_state_bytes(payload.version, agents_root, incoming)
    state_payload = b"" if _state_matches(state_path, desired) else desired
    return tuple(changes), tuple(all_agents), state_payload, None


def _plan_skill_domain(
    payload: Payload,
    skill_root: Path,
    state_path: Path,
    authority: dict[str, object] | None,
    migrating: bool,
) -> tuple[bool, bytes, str | None]:
    incoming = {item.relative: _sha256(item.payload) for item in payload.skill_files}
    if authority is not None:
        recorded_version = str(authority["plugin_version"])
        recorded_files = authority["files"]
        recorded_directories = authority["directories"]
        assert isinstance(recorded_files, dict)
        assert isinstance(recorded_directories, list)
        relation = _compare_versions(recorded_version, payload.version)
        if relation == 0 and (
            recorded_files != incoming
            or tuple(recorded_directories) != payload.skill_directories
        ):
            raise PreflightError(
                f"skill state version {payload.version} has different payload digests"
            )
        if relation > 0:
            _validate_skill_install(authority, skill_root, "newer shared skill")
            desired = _skill_state_bytes(
                recorded_version,
                skill_root,
                recorded_files,
                tuple(recorded_directories),
            )
            return False, desired if migrating else b"", recorded_version
        unconditional = relation < 0
    else:
        unconditional = True

    replace = _skill_needs_replacement(
        skill_root,
        payload.skill_files,
        payload.skill_directories,
        unconditional=unconditional,
    )
    desired = _skill_state_bytes(
        payload.version, skill_root, incoming, payload.skill_directories
    )
    state_payload = b"" if _state_matches(state_path, desired) else desired
    return replace, state_payload, None


def _agent_state_bytes(
    version: str, agents_root: Path, agents: Mapping[str, object]
) -> bytes:
    value = {
        "schema_version": AGENT_SCHEMA_VERSION,
        "kind": "agents",
        "plugin_version": version,
        "agents_root": str(agents_root),
        "agents": dict(agents),
    }
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _skill_state_bytes(
    version: str,
    skill_root: Path,
    files: Mapping[str, object],
    directories: tuple[str, ...],
) -> bytes:
    value = {
        "schema_version": SKILL_SCHEMA_VERSION,
        "kind": "skill",
        "plugin_version": version,
        "skill_root": str(skill_root),
        "files": dict(files),
        "directories": list(directories),
    }
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _state_matches(path: Path, expected: bytes) -> bool:
    return (
        path.is_file()
        and not _is_link_or_reparse(path)
        and _read_bytes(path, "ownership state") == expected
    )


def _skill_needs_replacement(
    root: Path,
    expected_files: tuple[FilePayload, ...],
    expected_directories: tuple[str, ...],
    *,
    unconditional: bool,
) -> bool:
    if not _path_exists(root):
        return True
    if unconditional or _is_link_or_reparse(root) or not root.is_dir():
        return True
    try:
        actual_files, actual_directories = _scan_tree(root, "skill target")
    except PreflightError:
        return True
    return actual_directories != expected_directories or {
        item.relative: item.payload for item in actual_files
    } != {item.relative: item.payload for item in expected_files}


def _scan_tree(
    root: Path, label: str
) -> tuple[tuple[FilePayload, ...], tuple[str, ...]]:
    _require_directory(root, label)
    files: list[FilePayload] = []
    directories: list[str] = []

    def visit(directory: Path, relative: PurePosixPath) -> None:
        for path in _directory_entries(directory):
            child = relative / path.name
            if _is_link_or_reparse(path):
                raise PreflightError(
                    f"{label} contains linked or reparse path: {child.as_posix()}"
                )
            metadata = _stat(path, label)
            if stat.S_ISDIR(metadata.st_mode):
                directories.append(child.as_posix())
                visit(path, child)
            elif stat.S_ISREG(metadata.st_mode):
                files.append(FilePayload(child.as_posix(), _read_bytes(path, label)))
            else:
                raise PreflightError(
                    f"{label} contains non-regular path: {child.as_posix()}"
                )

    visit(root, PurePosixPath())
    return tuple(sorted(files, key=lambda item: item.relative)), tuple(
        sorted(directories)
    )


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise PreflightError(f"invalid version: {value!r}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _compare_versions(left: str, right: str) -> int:
    left_value = _version_tuple(left)
    right_value = _version_tuple(right)
    return (left_value > right_value) - (left_value < right_value)


def _required_version(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise PreflightError(f"{label} has no valid plugin_version")
    _version_tuple(value)
    return value


def _implied_directories(files: Mapping[str, object]) -> tuple[str, ...]:
    directories: set[str] = set()
    for relative in files:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return tuple(sorted(directories))


def _valid_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _lock_path(state_path: Path) -> Path:
    return state_path.with_name(LOCK_NAME)


def _skill_state_path(skill_root: Path) -> Path:
    return skill_root.parent.parent / SKILL_STATE_NAME


def _skill_lock_path(skill_root: Path) -> Path:
    return skill_root.parent.parent / SKILL_LOCK_NAME


def _lock_paths(state_path: Path, skill_root: Path) -> tuple[Path, ...]:
    paths = (_lock_path(state_path), _skill_lock_path(skill_root))
    unique = {os.path.normcase(os.path.abspath(path)): path for path in paths}
    return tuple(unique[key] for key in sorted(unique))


@contextmanager
def _bootstrap_locks(paths: tuple[Path, ...]) -> Iterator[None]:
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    with ExitStack() as stack:
        for path in paths:
            remaining = max(0.0, deadline - time.monotonic())
            stack.enter_context(_bootstrap_lock(path, timeout=remaining))
        yield


def _retained_message(plan: InstallPlan) -> str | None:
    agent_version = plan.retained_agent_version
    skill_version = plan.retained_skill_version
    if agent_version is None and skill_version is None:
        return None
    if agent_version is not None and skill_version is not None:
        return (
            f"BarelySupervised bootstrap skipped older payload {plan.payload.version}; "
            f"agents {agent_version} and shared $bs skill {skill_version} are newer."
        )
    if agent_version is not None:
        return (
            f"BarelySupervised bootstrap skipped older payload {plan.payload.version} "
            f"for this CODEX_HOME's agents {agent_version}; shared $bs is current at "
            f"{plan.payload.version}."
        )
    return (
        f"BarelySupervised agents in this CODEX_HOME are current at {plan.payload.version}; "
        f"newer shared $bs skill {skill_version} was retained. Start a fresh session "
        "to discover changes."
    )


@contextmanager
def _bootstrap_lock(path: Path, *, timeout: float | None = None) -> Iterator[None]:
    """Hold one crash-released interprocess lock for the complete bootstrap decision."""
    _validate_target_ancestors(path, include_target=True)
    _make_directory(path.parent)
    if _path_exists(path):
        _require_regular_file(path, "bootstrap lock")
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags, 0o600)
    locked = False
    try:
        metadata = os.fstat(descriptor)
        private_mode = os.name == "nt" or stat.S_IMODE(metadata.st_mode) & 0o077 == 0
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not private_mode
            or _is_link_or_reparse(path)
        ):
            raise PreflightError(
                f"bootstrap lock is not a private regular file: {path}"
            )
        if metadata.st_size == 0:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
        wait_seconds = LOCK_TIMEOUT_SECONDS if timeout is None else timeout
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                _try_lock(descriptor)
                locked = True
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise OSError(
                        f"timed out waiting {wait_seconds:g}s for bootstrap lock"
                    ) from exc
                time.sleep(LOCK_POLL_SECONDS)
        yield
    finally:
        if locked:
            _unlock(descriptor)
        os.close(descriptor)


def _try_lock(descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _validate_target_ancestors(target: Path, *, include_target: bool) -> None:
    candidates = [target, *target.parents] if include_target else list(target.parents)
    for path in reversed(candidates):
        if not _path_exists(path):
            continue
        if _is_link_or_reparse(path):
            raise PreflightError(f"target uses linked or reparse parent: {path}")
        if path != target and not path.is_dir():
            raise PreflightError(f"target parent is not a directory: {path}")


def _directory_entries(root: Path, *, allow_missing: bool = False) -> tuple[Path, ...]:
    if not _path_exists(root):
        if allow_missing:
            return ()
        raise PreflightError(f"missing directory: {root}")
    _require_directory(root, "directory")
    try:
        return tuple(sorted(root.iterdir(), key=lambda path: path.name))
    except OSError as exc:
        raise OSError(f"cannot list directory {root}: {exc}") from exc


def _require_directory(path: Path, label: str) -> None:
    if _is_link_or_reparse(path):
        raise PreflightError(f"{label} is linked or reparse: {path}")
    if not stat.S_ISDIR(_stat(path, label).st_mode):
        raise PreflightError(f"{label} is not a directory: {path}")


def _require_regular_file(path: Path, label: str) -> None:
    if _is_link_or_reparse(path):
        raise PreflightError(f"{label} is linked or reparse: {path.name}")
    if not stat.S_ISREG(_stat(path, label).st_mode):
        raise PreflightError(f"{label} is not a regular file: {path.name}")


def _stat(path: Path, label: str) -> os.stat_result:
    try:
        return path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise PreflightError(f"{label} is missing: {path}") from exc
    except OSError as exc:
        raise OSError(f"cannot inspect {label} {path}: {exc}") from exc


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise OSError(f"cannot inspect path {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction is not None and is_junction():
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise OSError(f"cannot read {label} {path}: {exc}") from exc


def _make_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"cannot create directory {path}: {exc}") from exc
    _require_directory(path, "created target directory")


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        created = True
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written == 0:
                raise OSError(f"short write for {path}")
            view = view[written:]
        os.fsync(descriptor)
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
            descriptor = None
        if created:
            try:
                path.unlink()
            except OSError:
                pass
        raise OSError(f"cannot stage {path.name}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _populate_skill(
    stage: Path, files: tuple[FilePayload, ...], directories: tuple[str, ...]
) -> None:
    for relative in directories:
        (stage / PurePosixPath(relative)).mkdir()
    for item in files:
        _write_exclusive(stage / PurePosixPath(item.relative), item.payload)


def _publish_state_floor(
    target: Path,
    stage: Path,
    journal: list[tuple[Path, Path | None]],
) -> None:
    backup: Path | None = None
    if _path_exists(target):
        _require_regular_file(target, "ownership state")
        backup = target.parent / f".bs-state-backup-{uuid.uuid4().hex}"
        _write_exclusive(backup, _read_bytes(target, "ownership state"))
        journal.append((target, backup))
    else:
        os.replace(stage, target)
        journal.append((target, None))
        return
    os.replace(stage, target)


def _verify_skill_payload(root: Path, payload: Payload) -> None:
    files, directories = _scan_tree(root, "installed skill")
    actual = {item.relative: item.payload for item in files}
    expected = {item.relative: item.payload for item in payload.skill_files}
    if actual != expected or directories != payload.skill_directories:
        raise OSError("installed skill verification failed")


def _rollback_states(journal: list[tuple[Path, Path | None]]) -> list[str]:
    errors: list[str] = []
    for target, backup in reversed(journal):
        try:
            if backup is not None:
                os.replace(backup, target)
            elif _path_exists(target):
                target.unlink()
        except OSError as exc:
            errors.append(f"{target.name}: {exc}")
    return errors


def _rollback(
    plan: InstallPlan,
    agent_backups: list[tuple[Path, Path | None]],
    skill_backup: Path | None,
    skill_committed: bool,
) -> list[str]:
    errors: list[str] = []
    if skill_committed:
        try:
            _remove_path(plan.skill_root)
            if skill_backup is not None:
                os.replace(skill_backup, plan.skill_root)
        except OSError as exc:
            errors.append(f"skill: {exc}")
    elif skill_backup is not None and _path_exists(skill_backup):
        try:
            os.replace(skill_backup, plan.skill_root)
        except OSError as exc:
            errors.append(f"skill backup: {exc}")
    for target, backup in reversed(agent_backups):
        try:
            if _path_exists(target):
                target.unlink()
            if backup is not None:
                os.replace(backup, target)
        except OSError as exc:
            errors.append(f"{target.name}: {exc}")
    return errors


def _remove_path(path: Path) -> None:
    if not _path_exists(path):
        return
    if _is_link_or_reparse(path) or not path.is_dir():
        path.unlink()
    else:
        shutil.rmtree(path)


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _valid_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


if __name__ == "__main__":
    raise SystemExit(main())
