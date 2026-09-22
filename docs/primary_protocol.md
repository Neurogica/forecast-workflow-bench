# Primary electricity track

`benchmark/primary-377/cases.json` freezes the 377 evaluated cases. Fifty balancing
authorities, target starts July 24–27, 2026, one-day/seven-day leads. Source screening
removed 15 of 400 candidates; eight exploratory cases were also excluded. Each
case exposes 336 hourly observations and requires eight three-hour capacities.

For hourly normalized demand y and capacity a, the loss is the mean of
`0.3 * max(a-y, 0) + priority[h] * max(y-a, 0)`. The scale is the visible-history
mean. Capacities lie on 0.4:0.05:2.0 times that scale and adjacent normalized
capacities differ by at most 0.3. There is no total-capacity constraint in this
track. The strict grader retains a declared penalty for invalid submissions.

The last visible hour starts three hours before decision time. Forecasts require
50 or 194 hours to cover the target day. Agents choose model/context/horizon and
whether to use historical validation. They may return a shared tool's optimized
plan or construct actions themselves. No mandatory tool sequence is scored.

The service pool comprises Chronos-2, TimesFM 2.5, Chronos-Bolt Tiny, a priced
seasonal empirical forecast service, and eight free classical plans. See
`forecast_budget.example.json` for the frozen three-TSFM tariff. Budget = 113726;
max calls = 12; max output tokens = 16384 per response. Historical replay consumes
credits too. The main budget limits access to expensive services, including TimesFM.

Code entry points:

- `forecast_workflow.tools.server`: primary MCP server, also available as `fwb serve`
  or `fwb-mcp`. Requires a public episode directory containing catalog, visible
  series, quantile configuration, tariff, and contract. The stdio entry point uses
  `FWB_EPISODE_DIR` and `FWB_AS_OF`.
- `forecast_workflow.decision`: identical classical forecasts and grid/ramp optimizer.
- `forecast_workflow.evaluation.grading.grade(submission, contract, actual)`: strict
  realized-loss scoring. `actual` is a scorer-only array of 24 hourly MW values.
- `forecast_workflow.evaluation.normalization`: frozen terminal-answer format policy.
- `forecast_workflow.agents.runtime.episode`: bounded MCP interaction loop.
- `forecast_workflow.agents.local`: loopback-only model transport, no hosted fallback.

`fwb run` invokes one episode and stores result, final-text trace and service ledger
in a new output directory. `fwb score` normalizes a saved final answer and grades it
without network or LLM access. The loop never receives target observations.

The full evaluation additionally requires the separate episode dataset, scorer-only
observations and pinned backend configuration. The current package reorganization
is not an exact replay of all historical provider wrappers, and new code identities
must be recorded. Paper results retain their original source identity. Model weights
and data do not download implicitly on installation or during unit tests.
