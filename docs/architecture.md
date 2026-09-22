# Architecture

Public APIs follow responsibilities, not experiment chronology. Imports flow from
schemas/I/O and tariffs to forecasting and decision functions, then to the MCP
server and agent loop. Offline evaluation is separate from the online tool server:
only the scorer receives actual future observations.

- `core`: data records, tasks/submissions and deterministic JSON/hash utilities.
- `data`: load only checksum-verified observations beneath the episode directory.
- `budget`: quote/charge/finish ledger operations. No LLM API price constants.
- `forecasting`: backend adapters, visible-history processing and native quantiles.
- `decision`: eight classical predictive distributions and exact grid/ramp optimization.
- `tools.server`: one primary MCP server, combining forecast and classical plan tools.
  Tool names, argument schemas and descriptions were retained from the original
  primary v2/v3 composition; the package layout is new.
- `tools.forecast`: lower-level forecast-only MCP server, used by integration tests;
  not the primary track's tool catalog.
- `agents`: bounded tool loop and local transport. No campaign scheduling or secret targets.
- `evaluation`: strict contract grading and gold-blind terminal normalization.
- `cli`: explicit orchestration. Importing the package does not launch experiments.

Old weather generators, alternate contracts, development searches, quota polling,
spending campaigns, reporting glue and version-stacked server wrappers were removed
from the public tree. They remain in the private research archive. Package and CLI
names remain `forecast_workflow` and `fwb`; internal imports changed and are not
backward-compatible with the experimental flat module layout.

Paper aggregate results were not recomputed or changed by this refactor. Unit,
integration and numerical parity checks are recorded under `provenance/`. A new
code hash must never masquerade as the original paper's run hash.
