# Leaderboard and submissions

The Language Model track fixes the harness, instructions, forecasting tools,
contracts and scoring. It evaluates model configurations under a common budget.
SLMs are local models with fewer than 10B total parameters; larger local models
have at least 10B. Hosted models are grouped as LLMs because sizes may be undisclosed.

The Space displays author-reported results ranked by the combined score S (lower
is better), together with validity, decision loss and forecast credits. Filtering
or sorting does not change the global rank. Reference policies are shown separately.
See [protocol](objective_protocol.md) for scoring and aggregation.

## Participation

Participants execute the evaluation on their own compute. Maintainers review
submitted evidence before adding results. The Space does not execute models,
accept arbitrary code or provide an automatic submission service.

A submission must cover all 1,251 cases and include model and harness revisions,
dataset revision, prompts, tool schemas, decoding settings, terminal actions,
per-case scores, tool traces and credit ledgers. Record failed attempts and any
infrastructure recovery. Do not submit credentials. Use a GitHub issue to discuss
an evaluation, then a pull request with the configuration and artifact references.
Maintainers check coverage, recompute scores, inspect budget and target isolation,
and reproduce a sample where feasible. Accepted results identify verification status.

These are public reproduction cases. Score verification does not establish that
models have never seen the targets. Custom prompts, harnesses, additional tools
or budgets require separate evaluation conditions and must not enter this ranking.
