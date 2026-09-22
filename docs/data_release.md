# Current release

The current manuscript uses `objective-main-1251-v3`, with 1,251 cases and the
explicitly instructed score S. See [current protocol](objective_protocol.md).
The sections below document earlier releases and remain for provenance.

# Dataset release boundary

Included: 377 case IDs, authority/lead/date metadata; primary settings; one exact
agent-visible instruction, contract and tariff example; aggregate results.
Not included: observation CSVs, scorer-only future targets, cached forecast outputs,
API responses, local model weights, `.env`, billing logs, or original Git history.
The example task references a catalog that will come with the separate dataset;
it is documentation, not a complete runnable real-data episode.

EIA source: reported hourly demand (MW), Form EIA-930. Source acknowledgment for the
separate observation release must identify U.S. Energy Information Administration,
acquisition/publication dates, original URLs, transformations, hashes and exclusions.
See https://www.eia.gov/about/copyrights_reuse.php and
https://www.eia.gov/electricity/gridmonitor/ . Government-data reuse is permitted
subject to the stated exceptions. Do not redistribute EIA logos or protected
third-party materials under this repository's code license.

Generated instructions/contracts and source code in this export are contributed
under Apache-2.0; numerical source-derived metadata retain their EIA provenance.
The model registry records separate model licenses. No model weights are bundled.

## Versioned distribution

Observations, tasks and separate reproduction targets are released on Hugging Face:

- Dataset: `Neurogica/forecast-workflow-bench`
- Tag: `primary-377-v1`
- Commit: `8430fbc821d21e34861b37b1aaf3f3c17deb6001`
- File manifest SHA-256: `9fc2568f4d208633ffc72c34d64bb5789f377c72532aef0b027de29dad68c6e6`

GitHub contains code, schemas, small examples, hashes and case metadata, without
duplicating observation histories or scorer targets. The public targets support
reproduction; this release is not an unseen evaluation set. Expose only one episode
to an agent, since overlapping histories can reveal targets from sibling episodes.

Hugging Face documents dataset README cards and metadata (including license) at
https://huggingface.co/docs/hub/datasets-cards . Space hosting is documented separately
at https://huggingface.co/docs/hub/spaces-overview . These hosting features do not
supply benchmark admission or hidden-test security automatically.

## Prepared primary release package

The separate `forecast-workflow-bench-dataset` package contains all 377 frozen
episodes, separate reproduction targets, a browsable case index, component terms,
source/selection provenance and per-file hashes. Its 2,262 episode files match the
archived inputs byte-for-byte. All released observations were compared to the frozen
EIA source. The free hour-of-day policy reproduced all 377 historical reference
losses exactly (macro loss 0.05270977308745507). This validates data/scorer parity,
not full TSFM or provider-wrapper equivalence. All 2,654 released files were
verified against local file hashes after upload.

## Multidomain candidate

A separate local candidate preserves all primary episode bytes and adds 874 cases:
375 August electricity, 339 February electricity, and 160 May cycle-hire cases.
The combined package has 1,251 cases. Extension directories are organized by
cohort, with isolated episodes and separate reproduction targets. The original
primary inventory is retained as provenance; the current `manifests/files.json`
covers the complete candidate. Publication requires a new revision and does not
change the frozen primary leaderboard. See [transport details](transport_extension.md)
for source acquisition, TfL-specific component terms, units and construction.
