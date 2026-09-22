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
  Its tools expose forecast quotes, predictive plans and historical replay.
- `tools.forecast`: lower-level forecast-only MCP server, used by integration tests;
  not the primary track's tool catalog.
- `agents`: bounded tool loop and local transport. No campaign scheduling or secret targets.
- `evaluation`: strict contract grading and gold-blind terminal normalization.
- `cli`: explicit orchestration. Importing the package does not launch experiments.
