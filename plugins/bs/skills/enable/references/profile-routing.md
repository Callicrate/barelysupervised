# Profile Routing

Routing labels select a role, Persona, model, and reasoning effort. They are not custom agent types. Spawn every listed role in the current thread with `fork_turns: "none"`; use `worker` only for Engineers and `default` for all other roles.

| Routing label | Role | Persona | Built-in agent type | Model | Reasoning effort |
| --- | --- | --- | --- | --- | --- |
| `analyst-adaptive-sol-high` | Analyst | adaptive | `default` | `gpt-5.6-sol` | `high` |
| `analyst-evidence-terra-high` | Analyst | evidence | `default` | `gpt-5.6-terra` | `high` |
| `analyst-pragmatic-terra-medium` | Analyst | pragmatic | `default` | `gpt-5.6-terra` | `medium` |
| `analyst-structural-sol-xhigh` | Analyst | structural | `default` | `gpt-5.6-sol` | `xhigh` |
| `architect-adaptive-terra-high` | Architect | adaptive | `default` | `gpt-5.6-terra` | `high` |
| `architect-evidence-sol-xhigh` | Architect | evidence | `default` | `gpt-5.6-sol` | `xhigh` |
| `architect-pragmatic-sol-high` | Architect | pragmatic | `default` | `gpt-5.6-sol` | `high` |
| `architect-structural-terra-xhigh` | Architect | structural | `default` | `gpt-5.6-terra` | `xhigh` |
| `engineer-adaptive-sol-medium` | Engineer | adaptive | `worker` | `gpt-5.6-sol` | `medium` |
| `engineer-evidence-terra-xhigh` | Engineer | evidence | `worker` | `gpt-5.6-terra` | `xhigh` |
| `engineer-pragmatic-terra-high` | Engineer | pragmatic | `worker` | `gpt-5.6-terra` | `high` |
| `engineer-structural-sol-high` | Engineer | structural | `worker` | `gpt-5.6-sol` | `high` |
| `reviewer-critical-terra-high` | Reviewer | critical | `default` | `gpt-5.6-terra` | `high` |
| `reviewer-evidence-sol-xhigh` | Reviewer | evidence | `default` | `gpt-5.6-sol` | `xhigh` |
| `reviewer-pragmatic-sol-high` | Reviewer | pragmatic | `default` | `gpt-5.6-sol` | `high` |
| `reviewer-structural-terra-xhigh` | Reviewer | structural | `default` | `gpt-5.6-terra` | `xhigh` |
