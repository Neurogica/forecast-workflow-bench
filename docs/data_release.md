# Dataset distribution and terms

The Hugging Face dataset `Neurogica/forecast-workflow-bench` distributes the
`objective-main-1251-v3/` payload: 1,251 episodes, separate reproduction targets,
source provenance, component licenses, evaluation results and file checksums.
Use the immutable `objective-main-1251-v3` tag to reproduce the paper evaluation.

GitHub contains the harness, case metadata, figures and aggregates. It does not
bundle observation histories, future targets, model weights or credentials.
The histories and targets are public reproduction data, not an unseen test set.
Isolate each episode and keep all target files outside the agent environment.

## Component licenses

Code and generated instructions/contracts: Apache-2.0. EIA electricity observations
retain U.S. Energy Information Administration provenance and reuse terms, including
exceptions for protected materials. Cycle-hire aggregates retain TfL Transport
Data Service terms; see [cycle-hire construction and attribution](transport_extension.md).
The mixed-source HF card uses `license: other` and
`license_name: fwbench-component-terms`. This is not an Apache-2.0 license for all data.
The dataset LICENSE and source-specific provenance contain the applicable terms.
Model weights have their own licenses and are downloaded separately.

Source pages: [EIA reuse](https://www.eia.gov/about/copyrights_reuse.php),
[TfL terms](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service).
Recent observation dates alone do not establish exclusion from model training.
