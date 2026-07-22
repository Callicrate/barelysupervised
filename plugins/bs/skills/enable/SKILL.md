---
name: "enable"
description: "Use when a user explicitly invokes `$bs:enable <task>` to coordinate a task with subagents. Do not trigger for ordinary analysis, planning, implementation, or review without that invocation."
metadata:
  short-description: "Explicit multi-role task coordination"
---

# BarelySupervised

## When to Use

Run only after the user explicitly invokes `$bs:enable <task>`. That invocation is affirmative evidence that the user wants coordinated help, so default to useful subagent delegation before substantive work. Outside that invocation, do nothing.

## When NOT to Use

Do not load this skill for ordinary work, or substitute generic built-in agents when an installed custom profile is unavailable.

## Workflow

1. Treat the invocation as a request for coordinated work. Before substantive work, identify bounded packages where a role, independent pass, or review could materially improve the result. If that judgment is uncertain, delegate.
2. Use the [direct-work exception](#direct-work-exception) only when every condition is met. Otherwise invoke `/goal <concise, testable end state>` and dispatch at least one subagent. The coordinator remains accountable for decomposition, authority, synthesis, and delivery.
3. Classify each delegated package as Analyst, Architect, Engineer, or Reviewer. Choose its Persona by task shape, then select the exact custom agent name from [profile routing](references/profile-routing.md).
4. Confirm that `.codex/agents/<profile-id>.toml` is installed before dispatching. If it is absent, do not substitute `default`, `worker`, or another generic agent. Tell the user to trust the plugin hook with `/hooks`, then start or resume a session so it can install the bundled profiles.
5. Spawn the exact installed custom agent profile in this thread with `fork_turns: "none"`. The TOML carries its model, reasoning effort, role contract, and Persona, so do not copy those instructions into the dispatch brief.
6. Give each subagent a self-contained brief beginning with its bounded `/goal`, followed by its deliverable, scope and exclusions, evidence, constraints, authority, completion criteria, and escalation conditions. Select an Engineer only for bounded production edits and grant it exclusive write ownership of those artifacts.
7. Run independent packages in parallel when their scope and write ownership are disjoint. Use an independent Reviewer for material implementation. Use one focused subagent for a routine single package; add agents only when independence or verification materially improves the result.
8. Synthesize evidence rather than majority-voting: compare agreements, unique evidence, assumptions, disagreements, risks, unknowns, and failure modes. Run or request proportionate validation before delivering the result.

## Direct-Work Exception

Direct execution is allowed only when the coordinator is highly confident that all of the following are true:

- The task is truly trivial, tightly coupled, or integration-only.
- No bounded role or independent pass can materially improve correctness, coverage, speed, or verification.
- Delegation overhead is comparable to the task itself.

This is a narrow exception, not a reason to avoid coordination. If any condition is uncertain, dispatch a subagent.

## Dispatch Template

```text
/goal <bounded, testable subagent outcome>

Deliverable: <concrete output>
Scope and exclusions: <owned paths or read-only boundary>
Context and evidence: <requirements, paths, tests, prior findings>
Constraints and authority: <including write ownership, if any>
Completion criteria: <observable proof>
Escalate when: <unresolved authority, semantics, or consequential boundary>

<paste the selected complete role contract>

<paste the selected complete Persona>
```

## Deterministic Tools

Use the runtime's `spawn_agent` action with the exact installed custom agent name from the selected routing row and `fork_turns: "none"`.

## References

- [Role contracts](references/role-contracts.md)
- [Personas](references/personas.md)
- [Profile routing](references/profile-routing.md)
