# Objective-aligned Language Model evaluation

Version: `objective-main-1251-v3`. This is the current manuscript evaluation:
1,251 cases, two hosted and eight local configurations, and 22,518 conversations
including paired local TSFM-removal runs.

Agents minimize S = 0.5 * ((loss - F) / sigma + credits / B), where F is the
minimum feasible loss with known target demand, sigma is the calibrated domain
scale, and B = 113726. Prompts omit the action-independent F. Invalid plans retain
penalties. Cohort weights are 1/6 for each of three electricity cohorts and 1/2
for cycle hire; cases are averaged within series and lead before cohort weighting.
Credits measure forecast-tool expenditure, excluding language-model inference.

The dataset's `objective-main-1251-v3/` directory contains the exact full-tool
instructions, histories, contracts, tariffs, separate reproduction targets,
per-case results, and integrity manifest. These public targets support reproduction, not hidden-test evaluation.
Give each agent only its isolated episode; never expose sibling episodes or targets.
The full-tool main ranking has ten configurations. The eight local configurations
also have no-TSFM controls in the results summary. Forecast-tool removal changes
available actions and is not a pure test of forecast accuracy.

Data terms remain component-specific: EIA provenance and TfL Transport Data
Service terms apply to their respective observations. Apache-2.0 covers contributed
code and generated materials, not a relicensing of the source observations.
