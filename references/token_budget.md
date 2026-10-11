# Token budget and compaction headroom

## The three budget lines

| Line | Value | Meaning |
|---|---|---|
| **Total budget** | ~8000 tokens | the whole optimized SKILL.md (frontmatter + body) should fit |
| **Core up front** | first ~3000 tokens | hard constraints + criteria core + the five-step flow skeletons; these survive compaction |
| **Compaction headroom** | ~5000 tokens | slack reserved so the file does not blow the budget when the conversation grows |

The point is not to pack 8000 tokens of content - it is to keep the **core** in the
first ~3000 and reserve the rest as headroom for a long running conversation.

## Estimating tokens without an encoder

A good-enough rule for English prose and code: **~4 characters per token**. The
bundled linter uses this to flag:

- `body_est_tokens = len(body) // 4`
- over the budget -> **blocker** (must sink details)
- over 80% of the budget -> **low** (warning, close to the line)

To get a stricter count, run a real encoder; the linter's number is a planning
estimate, not a measurement.

## What stays in the body, what sinks to references/

Keep in the body (every turn):

- hard-constraint table
- criteria core (T/L/C/B)
- the five-step flow skeletons (input / output / fallback per step)
- the routing table that points into `references/`

Sink to `references/` (load on demand):

- per-platform frontmatter matrices
- wording templates and the changelog spec
- budget details and the token-estimation method
- worked examples beyond the three trigger cases

Rule of thumb: if a passage is not read on *every* trigger, it belongs in
`references/` with a single navigation pointer in the body.
