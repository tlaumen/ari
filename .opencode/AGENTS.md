# AGENTS.md

This file is loaded by opencode on every run. All agents must follow these rules.

## Workflow Order

Steps must be run in sequence. An agent must not proceed if its preconditions are unmet.

```
step-0-define           →  docs/features/00_definition.md
step-1-research         →  docs/features/01_research.md
step-2-architect        →  docs/features/02_architecture.md
                            src/stubs/
step-3-specify          →  docs/features/03_spec.md
                            tests/test_<feature>.py
step-4-implement        →  src/ (final implementation)
step-5a-review-quality  →  docs/features/05a_review_quality.md
step-5b-review-security →  docs/features/05b_review_security.md
```

The two review agents (5a and 5b) are independent of each other but both require step 4 to be complete. Run 5a before 5b as a convention — quality issues resolved first means the security reviewer is not reading noise.

## Universal Rules

- Always read `CODING_STANDARDS.md` before writing any code.
- Never write output files until the user has explicitly approved the draft.
- Never skip a step or merge two steps into one action.
- `00_definition.md` is frozen after `step-1-research` begins. Do not modify it without explicit user instruction and re-running downstream steps.
- Architectural deviations from `02_architecture.md` must be flagged to the user, not silently made.
- Every spec step in `03_spec.md` must have at least one corresponding test before implementation begins.
- Review agents (5a, 5b) do not rewrite code unilaterally — they report, discuss, and act only on approval.

## File Ownership by Step

| File | Owned by | Frozen after |
|---|---|---|
| `00_definition.md` | step-0-define | step-1-research starts |
| `01_research.md` | step-1-research | step-2-architect starts |
| `02_architecture.md` | step-2-architect | step-4-implement starts* |
| `src/stubs/<feature>/` | step-2-architect | step-4-implement starts* |
| `03_spec.md` | step-3-specify | step-4-implement starts* |
| `tests/<feature>/` | step-3-specify | step-4-implement (additive only) |
| `src/` (implementation) | step-4-implement | — |
| `05a_review_quality.md` | step-5a-review-quality | — |
| `05b_review_security.md` | step-5b-review-security | — |

*Can be updated by step-4-implement only via explicit user-approved revision, not silently.

## Interaction Protocol

Each agent must:
1. Present its draft output to the user.
2. Wait for feedback and iterate.
3. Receive explicit approval ("approved", "looks good", "write it", etc.) before writing any files.
4. Confirm which files were written after doing so.
