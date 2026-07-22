# Profile Routing

Each profile ID is the exact installed custom agent name. Spawn it in the current thread with `fork_turns: "none"`. The matching TOML supplies the model, reasoning effort, role contract, and Persona.

| Custom agent name | Role | Persona | Model | Reasoning effort |
| --- | --- | --- | --- | --- |
| `analyst-adaptive-sol-high` | Analyst | adaptive | `gpt-5.6-sol` | `high` |
| `analyst-evidence-terra-high` | Analyst | evidence | `gpt-5.6-terra` | `high` |
| `analyst-pragmatic-terra-medium` | Analyst | pragmatic | `gpt-5.6-terra` | `medium` |
| `analyst-structural-sol-xhigh` | Analyst | structural | `gpt-5.6-sol` | `xhigh` |
| `architect-adaptive-terra-high` | Architect | adaptive | `gpt-5.6-terra` | `high` |
| `architect-evidence-sol-xhigh` | Architect | evidence | `gpt-5.6-sol` | `xhigh` |
| `architect-pragmatic-sol-high` | Architect | pragmatic | `gpt-5.6-sol` | `high` |
| `architect-structural-terra-xhigh` | Architect | structural | `gpt-5.6-terra` | `xhigh` |
| `engineer-adaptive-sol-medium` | Engineer | adaptive | `gpt-5.6-sol` | `medium` |
| `engineer-evidence-terra-xhigh` | Engineer | evidence | `gpt-5.6-terra` | `xhigh` |
| `engineer-pragmatic-terra-high` | Engineer | pragmatic | `gpt-5.6-terra` | `high` |
| `engineer-structural-sol-high` | Engineer | structural | `gpt-5.6-sol` | `high` |
| `reviewer-critical-terra-high` | Reviewer | critical | `gpt-5.6-terra` | `high` |
| `reviewer-evidence-sol-xhigh` | Reviewer | evidence | `gpt-5.6-sol` | `xhigh` |
| `reviewer-pragmatic-sol-high` | Reviewer | pragmatic | `gpt-5.6-sol` | `high` |
| `reviewer-structural-terra-xhigh` | Reviewer | structural | `gpt-5.6-terra` | `xhigh` |
