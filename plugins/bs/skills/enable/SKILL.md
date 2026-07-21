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

Do not load this skill for ordinary work, or treat its routing labels as available custom agent types.

## Workflow

1. Treat the invocation as a request for coordinated work. Before substantive work, identify bounded packages where a role, independent pass, or review could materially improve the result. If that judgment is uncertain, delegate.
2. Use the [direct-work exception](#direct-work-exception) only when every condition is met. Otherwise invoke `/goal <concise, testable end state>` and dispatch at least one subagent. The coordinator remains accountable for decomposition, authority, synthesis, and delivery.
3. Classify each delegated package as Analyst, Architect, Engineer, or Reviewer. Choose its Persona by task shape, then select one exact routing label from [profile routing](references/profile-routing.md).
4. Before dispatching a role for the first time, read its complete contract in [role contracts](references/role-contracts.md) and its complete Persona in [personas](references/personas.md). Select an Engineer only for bounded production edits and grant it exclusive write ownership of those artifacts.
5. Spawn built-in agents in this thread with `fork_turns: "none"`. Use `agent_type: "worker"` only for Engineers; use `agent_type: "default"` for Analysts, Architects, and Reviewers. Pass the routing label's exact `model` and `reasoning_effort` overrides. Routing labels are selection aliases, not custom `agent_type` values.
6. Give each subagent a self-contained brief beginning with its bounded `/goal`, followed by its deliverable, scope and exclusions, evidence, constraints, authority, completion criteria, and escalation conditions. Paste the selected complete role contract and complete Persona into that brief.
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

Use the runtime's `spawn_agent` action with the exact built-in agent type, model, reasoning effort, and `fork_turns` values in the selected routing row.

## References

- [Role contracts](references/role-contracts.md)
- [Personas](references/personas.md)
- [Profile routing](references/profile-routing.md)
