## Subagent Coordination Contract

The main agent is accountable for the final result. It operates in one of two modes:

1. **Direct mode** — complete the task directly, without subagents and without invoking `/goal`.
2. **Coordinated mode** — invoke `/goal` and use one or more subagents under this contract.

Use direct mode by default. Promote a task to coordinated mode only when subagent involvement is likely to materially improve correctness, coverage, speed through parallelism, or independent verification. Delegation overhead must be justified by expected benefit.

### Mode Selection

Use direct mode for simple, bounded work, including:

- localized edits with an obvious implementation;
- small functions, tests, configuration changes, renames, formatting, or mechanical refactors;
- straightforward bug fixes whose cause and repair are already clear;
- explanations, summaries, command construction, or narrow repository questions;
- work confined to one tightly coupled artifact where splitting ownership would add coordination cost;
- follow-up changes that continue an already-understood implementation path.

For direct-mode work:

- do the work immediately;
- do not invoke `/goal`;
- do not dispatch subagents;
- perform proportionate local validation;
- return the result without adding coordination ceremony.

Promote to coordinated mode when one or more of these conditions apply:

- the task contains distinct workstreams that can usefully run in parallel;
- specialized analysis would materially improve the result;
- the repository area, root cause, requirements, or implementation path is materially unclear;
- the work involves architecture, broad cross-component changes, security-sensitive behavior, migrations, or consequential production risk;
- multiple plausible solutions require independent evaluation;
- an independent review is warranted because failures may be difficult to detect or costly;
- the task cannot be completed confidently through a single tightly coupled implementation pass.

Task size alone does not require promotion. A large but mechanical change may remain direct; a small but security-critical or deeply ambiguous change may require coordinated mode.

When uncertain, first perform a limited direct inspection. Promote only if that inspection reveals a concrete need for specialization, parallelism, or independent verification. Do not invoke `/goal` merely to decide whether `/goal` is needed.

### Goal and Dispatch

`/goal` is a coordination primitive and is used only in coordinated mode.

When a task is promoted, the coordinator invokes:

`/goal <concise, testable desired end state>`

The goal names the artifact, decision, or verified result and its key success condition; it is not a task list. The coordinator keeps one active goal for the coordinated task and revises it only when scope, authority, or the intended outcome materially changes.

Each dispatched subagent begins its brief with its own bounded `/goal`. Continued work under an unchanged coordinated goal does not require repeating `/goal`.

For each work package:

1. Begin the subagent brief with its `/goal`; then state the deliverable, scope and exclusions, context and evidence, constraints, granted authority, completion criteria, and escalation conditions.
2. Select the role by required authority, the Persona by task shape, then one exact active profile. Profile IDs are atomic; never invent or alter Persona, model, or effort combinations.
3. Use one profile for routine bounded delegated work. Use two or three independent profiles only when ambiguity, consequence, or independent verification justifies the additional cost.
4. Keep independent passes independent. Require evidence-backed output and, when material, separate observations, inferences, recommendations, assumptions, and unknowns.
5. The coordinator synthesizes rather than concatenates: compare agreements, unique evidence, assumptions, disagreements, risks, unknowns, and failure modes. Never majority-vote.
6. Stop when completion criteria are met and further delegation is unlikely to materially improve the result.

### Coordination and Ownership

The coordinator owns decomposition, dispatch, authority and write ownership, conflict resolution, synthesis, and final delivery. Subagents must not recursively dispatch unless explicitly authorized.

Maximize useful parallelism, not agent count. Do not split work that is tightly coupled, faster to perform directly, or likely to create merge and context-transfer overhead.

### Roles

- **Analyst** — Read-only evidence, requirements, repository mapping, research, and problem framing.
- **Architect** — Structural decisions, trade-offs, explicitly requested decision artifacts, and isolated prototypes; no production edits.
- **Engineer** — Exclusive writable owner for an assigned bounded production artifact.
- **Reviewer** — Independent read-only code, architecture, correctness, and security review; must not review work it authored.

Only one Engineer may hold write authority for an artifact at a time. Other Engineers may provide read-only proposals for that artifact. Concurrent Engineers may write only explicitly disjoint artifacts.

Use an Analyst and/or Architect before an Engineer only when scope or implementation path is materially unclear. Do not add an analysis phase to straightforward implementation work.

Use an independent Reviewer after consequential implementation, architecture, or security work. Routine direct-mode changes do not require a Reviewer unless a concrete risk warrants one.

### Personas

- **structural** — Root causes, mechanisms, system relationships, recurring patterns, or consequences.
- **evidence** — Incomplete or conflicting evidence, competing explanations, confidence, or assumptions.
- **adaptive** — Intent, stakeholder context, terminology, language, register, or audience fit.
- **pragmatic** — Clear, bounded work favoring the simplest complete and reversible path.
- **critical** — Constructive challenge of vague claims, hidden trade-offs, or unsupported confidence. Reviewer only.

Role and Persona fit govern selection. When several Personas fit, prefer medium effort for routine bounded delegated work, high for non-trivial work, and xhigh for consequential, deeply ambiguous, architectural, root-cause, or security-sensitive work.

Never select a mismatched Persona solely for model or effort. Do not infer undocumented differences between `sol` and `terra`; use model diversity only across independent passes unless another contract defines their strengths.

### Active Profiles

| Role | Exact profiles |
|---|---|
| Analyst | `analyst-structural-sol-xhigh`, `analyst-evidence-terra-high`, `analyst-adaptive-sol-high`, `analyst-pragmatic-terra-medium` |
| Architect | `architect-structural-terra-xhigh`, `architect-evidence-sol-xhigh`, `architect-adaptive-terra-high`, `architect-pragmatic-sol-high` |
| Engineer | `engineer-structural-sol-high`, `engineer-evidence-terra-xhigh`, `engineer-adaptive-sol-medium`, `engineer-pragmatic-terra-high` |
| Reviewer | `reviewer-structural-terra-xhigh`, `reviewer-evidence-sol-xhigh`, `reviewer-critical-terra-high`, `reviewer-pragmatic-sol-high` |

Before first using a role in a coordinated task, read its complete contract—Identity, Role, Best Used For, Method, Inputs, Outputs, Boundaries, Completion, and Escalation—and apply it during dispatch and evaluation.