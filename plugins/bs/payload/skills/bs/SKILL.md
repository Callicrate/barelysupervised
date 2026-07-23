---
name: "bs"
description: "Use when a user explicitly invokes `$bs` to coordinate work through the installed BarelySupervised custom-agent profiles. Do not trigger for ordinary analysis, implementation, or review without that invocation."
metadata:
  short-description: "Coordinate explicit custom-agent work"
---

# BarelySupervised

## When to Use

Run only after the user explicitly invokes `$bs <task>`. Treat that invocation as affirmative evidence that coordinated help is wanted. Outside that invocation, do nothing.

## When NOT to Use

Do not load this skill for ordinary work. Do not substitute a generic agent when a selected BarelySupervised custom profile is unavailable.

## Workflow

1. Assess the [direct-work exception](#direct-work-exception) before substantive work. Normally delegate at least one bounded package.
2. Invoke `/goal <concise, testable end state>` for the coordinated outcome when the goal is not already active. The coordinator remains accountable for decomposition, dispatch authority, synthesis, and final delivery.
3. Discover the installed BarelySupervised custom agents from Codex's runtime-registered catalog. Select the exact custom profile whose registered name and description best fit each bounded package. Do not reconstruct selection from a roster, naming convention, or embedded behavioral knowledge.
4. Invoke Codex's native custom-agent selector with the selected runtime-registered exact name as `agent_type` and `fork_turns: "none"`. Do not pass model, effort, or instruction overrides. The installed custom profile is the sole authority for its behavior.
5. Give each child a self-contained brief beginning with its bounded `/goal`, then state the deliverable, scope and exclusions, evidence, constraints, authority, completion criteria, and escalation conditions. Never copy or reconstruct the selected profile's internal instructions.
6. Grant no more than one selected agent write ownership of a given artifact at a time. Keep every agent within its registered authority. Run independent packages in parallel only when their scopes and write ownership are disjoint.
7. Use an independent review agent after material implementation, architecture, or security work. Synthesize evidence by comparing agreements, unique evidence, assumptions, disagreements, risks, unknowns, and failure modes. Never majority-vote.
8. Stop when completion criteria are met and more delegation is unlikely to materially improve the result. Escalate when the runtime catalog cannot supply an appropriate installed custom agent or required authority is unresolved.

If the runtime cannot select a native custom profile by exact `agent_type`, report that this Codex surface is unsupported. Do not emulate profile selection, prescribe a custom spawn wrapper, or fall back to a built-in agent.

## Direct-Work Exception

Work directly only when every condition is true:

- The task is trivial, tightly coupled, or integration-only.
- No bounded agent package or independent pass can materially improve correctness, coverage, speed, or verification.
- Delegation overhead is comparable to the task itself.

If any condition is uncertain, delegate.

## Deterministic Tools

Use Codex's native custom-agent selector with the selected runtime catalog entry's exact name as `agent_type` and `fork_turns: "none"`. The installed custom profile supplies all behavior.

## References

No bundled references. Discover installed custom agents from Codex's runtime catalog.
