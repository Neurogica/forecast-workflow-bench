# Transport extension

The May 2026 extension adds 160 cycle-hire service-capacity cases: 20 London
stations, four target days (May 3, 11, 19, 27), and one- and seven-day leads.
It is a separate evaluation cohort, not a replacement for `primary-377-v1`.
All 160 candidates passed the declared quality criteria. The preceding electricity
extensions contain 375 August and 339 February cases; the four cohorts total 1,251.
Do not merge their losses into an unregistered leaderboard score.

## Source and permitted distribution

TfL's [official open-data directory](https://tfl.gov.uk/info-for/open-data-users/our-open-data)
links the cycle-hire trip archives. The
[Transport Data Service terms](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service)
permit copying, adaptation, publication, distribution and commercial use subject
to their conditions. These are TfL-specific terms based on OGL 2.0, not unmodified
OGL, CC0, or the source code's Apache-2.0 license. Preserve the component terms and:

- Powered by TfL Open Data
- Contains OS data © Crown copyright and database rights 2016
- Geomni UK Map data © and database rights [2019]

No endorsement or rights to logos, branding or personal data are implied. The
release contains hourly aggregates, not individual trip or bicycle identifiers.
Keep `license: other` and `license_name: fwbench-component-terms` on the mixed-source
dataset card. The archived license HTML, source page, file listing, acquisition
timestamps and checksums accompany the separate dataset candidate.

Citi Bike was rejected: its data-sharing agreement prohibits distribution as a
stand-alone dataset. Availability for download alone is not permission to rehost.

## Construction

1. Acquire official extracts 441--444 (April and May 2026). Verify checksums and
   byte counts against the source inventory.
2. Select the 20 most active departure stations during April 1--7, before any
   evaluation origin. Break ties by station ID. Freeze this rule before forecasting.
3. Validate journey IDs and source coverage, convert London timestamps to UTC,
   and count recorded departures per hour. All selected dates are in BST; missing
   or ambiguous timestamps fail validation. Retain zero-count hours rather than
   interpolating them. The source contains observations in every system-wide hour;
   this does not prove that every individual journey was recorded.
4. Use 336 visible hours, a three-hour observation gap, and 24 local target-day
   hours. Require departures on every *complete* local calendar day in history;
   partial boundary days are not used for this check. No target-loss filtering.
5. Store each isolated episode separately from its reproduction targets. An
   independent crosstab recount verified all 57,600 selected observations.

The histories are completed rentals, not unconstrained rental demand. The
contract simulates a service rate in departures/hour, not an inventory of bicycles.
It has no inventory conservation or rebalancing dynamics. Prices, priority weights
and ramp limits are simulated, not estimates of TfL's operational economics.

Observation dates follow the pinned TSFM checkpoint releases, but this does not
prove complete training exclusion. Preserve exact model revisions and source
timestamps; do not describe retrospective archives as as-published vintages.

## Reproduction and code layout

`forecast_workflow.datasets.transport` performs source aggregation and construction.
`forecast_workflow.decision.units` handles generic physical units and validates
compatibility with the frozen MW schema. Optimizer, scorer and MCP tools use the
same accessors. `scale` / `capacity_grid` / `unit` are used for transport; historical
`scale_mw` / `capacity_grid_mw` inputs remain supported. Conflicting aliases fail.

After downloading the four raw archives and the matching `acquisition.json` and
license evidence from the dataset provenance, run:

```bash
python scripts/data/build_transport.py \
  --source data/sources/tfl-cycle-hire/2026-snapshot \
  --output data/cohorts/transport/tfl-cycle-hire-may-v1
```

The output path must not exist. This construction command performs no model or
API calls. The public builder reproduced all 960 evaluated episode files and
160 target records exactly (JSON value equality; byte equality for histories).
Provenance manifests differ when the builder's own file hash changes.

## Interpretation of the results

Fixed Chronos-2, Bolt and free hour-of-day empirical plans had mean losses
0.5553, 0.5632 and 0.5744. The perfect-demand optimum was 0.5192: the shared
three-hour grid/ramp constraints imposed a substantial floor on spiky rental
counts. Above this floor, Chronos-2 reduced empirical excess loss by 34.5%.
The full-menu hindsight oracle reached 0.5415 at 29,040 credits, versus 108,766
for fixed Chronos-2. It used free classical plans in 95 of 160 cases.

Always report the raw loss and the perfect-demand floor with excess loss.
Oracle selection uses future targets and pays only for the selected plan, not
for searching the menu. It is a diagnostic reference, not a deployable policy.
Smaller matched agent panels must be labeled with their own sample counts.

## Matched language-model panels

| Model | Paired cases | With TSFMs | Without TSFMs | Valid with/without |
|---|---:|---:|---:|---:|
| Qwen3 4B Q8 | 16 | 0.8272 | 0.8242 | 15/15 |
| Gemma 4 E4B QAT Q4 | 16 | 0.7234 | 0.8929 | 15/14 |
| GPT-6 Astra, high effort | 8 | 0.7060 | 0.7065 | 8/8 |

These are matched **within-model** comparisons. Astra's eight-case panel differs
from the local sixteen-case panel, so the rows are not a model ranking. All
invalid outcomes are included in the losses. The fixed normalizer, decoding
settings, source hashes and per-case tariff ledgers were retained. No-TSFM
conditions retained the classical tools and seasonal empirical forecast service.
Astra showed little tool-access benefit on this panel; the fixed-model improvement
does not establish that an agent reliably captures that improvement.

[Machine-readable aggregate results](../results/extension-references.json) include
all four cohorts, oracle budgets and the conditional station-bootstrap interval.
