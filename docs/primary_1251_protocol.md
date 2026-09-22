# Primary-1251-v2 Language Model track

The main set contains 1,251 cases: 377 July, 339 February and 375 August
EIA electricity cases, plus 160 TfL cycle-hire cases. It replaces the case set
for the new version; `primary-377-v1` remains a separate historical result.
All twelve model configurations completed the main evaluation. Partial submissions cannot be ranked.

The fixed case budget is 113,726 credits, with 12 calls, 16,384 response output
tokens and the same three pinned forecast-model services. Local decoding uses
seed 1701 and the previously declared model-specific quantizations. The 377
historical outcomes are retained; all 874 additional cases receive fresh runs.
Pilot ablations are never used as best-of candidates for the main comparison.
Electricity extension prompts explicitly identify the existing eight classical
tools. Those exact bytes are distributed with the evaluated episodes.

## Aggregation and ranking

Within each cohort, average dates within series × lead, then equally average
those groups. The three electricity cohorts receive 1/6 each and cycle hire 1/2.
For a case, J = loss + lambda × credits / B. Subtract the minimum affordable
J among eight classical and three full-context TSFM plans, then aggregate using
the same frozen weights. The default lambda is 0.01; the sensitivity grid is
0, 0.001, 0.003, 0.01, 0.03 and 0.1. Increasing expenditure at fixed loss
strictly worsens G for positive lambda, including on an oracle plateau.

The coefficient and domain balance were selected after exploratory results were
available; they are not preregistered or externally calibrated economic prices.
G ranks models identically to J on the same complete cohort because the oracle
is common. Report loss, credits, validity, cohort breakdowns and case-weighted
loss alongside G. The finite-menu oracle uses future targets, counts selected
execution cost rather than search, and can be beaten by a plan outside its menu.

## Reproduction

Download `Neurogica/forecast-workflow-bench` at the `primary-1251-v2` dataset tag.
Read `manifests/settings.json`, `manifests/cases.json` and `manifests/files.json`.
The dataset viewer is a case index; executable inputs are in `episodes/`.
Expose only one episode to an agent; never expose targets or sibling histories.
Public targets support reproducibility, not claims of hidden-test generalization.

Electricity observations retain EIA source terms. Cycle-hire aggregates retain
TfL Transport Data Service terms, including the required attribution. Original
benchmark code and contributions are Apache-2.0; the complete dataset is not
blanket Apache-2.0. The data card and component license contain the full notices.
Cycle-hire service capacity is a simulated departure rate, not bike inventory
or unmet rental demand. Post-checkpoint observation dates do not establish that
all language-model or forecast-model training excluded these observations.
