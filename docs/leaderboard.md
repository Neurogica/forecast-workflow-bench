# Leaderboard operation

## Roles

The intended scalable workflow is participant-run, maintainer-verified evaluation.
A language-model developer or researcher runs the frozen harness on their own
compute and pays their own model inference costs. Maintainers own task versions,
forecast-service revisions, tariffs, scoring and admission policy. They verify
submissions and publish admitted rows; the Space only displays these rows.

Maintainer-run full evaluations can be offered for selected open models or releases,
but are not promised for every submitted model. This avoids making the benchmark
operator fund an unbounded set of hosted LLM evaluations.

## Submission evidence

A complete submission must identify the track/case manifest, dataset revision,
code revision, prompt and tool-schema hashes, forecast weight revisions, decoding
settings, all attempts/recovery reasons, terminal answers, per-case scores and
resource ledgers. No API keys or credentials are submitted. Incomplete grids and
best-of-selected attempts cannot enter the primary ranking. Protocol changes,
extra calls, new prompts or extra tools define separate tracks.

Maintainers recompute losses from submitted actions, check case coverage and
ledgers, inspect traces for target exposure or undeclared tools, and reproduce a
sample where feasible. Verified metrics are not proof that a participant had no
prior exposure to public targets. Verification status and protocol version must
be displayed separately from score. Initial admission is manual; an automatic
submission/verification service is not implemented in this candidate.

## Public versus held-out evaluation

The July primary cohort is the paper-reproduction track. If its observations and
answers are released, it must be labelled public rather than unseen. Participants
can self-score it, and maintainers can reproduce scores without paying LLM costs.

A future held-out track requires separately frozen fresh dates and restricted
agent inputs. Participants submit actions for maintainer-side scoring; stronger
claims need controlled execution, not merely a hidden answer file. EIA observations
are public at source and can be retrieved outside a controlled environment.
Repeated submissions need a declared attempt policy and must retain attempts;
no daily submission quota is silently imposed on the paper's existing results.

## Present implementation

`leaderboard/` displays author-reported paper aggregates. It does not accept uploads,
run participant code, host TSFMs or provide independent certification. A production
submission flow, verification queue and fresh held-out dataset remain release work.
Running the Space therefore does not require a GPU for model evaluation.

## Recommended release design

Use a participant-run, maintainer-reviewed submission route rather than a permanently
closed table. Initially keep the author-reported paper results visible and separate
from externally submitted results. Open intake only after the dataset, a complete
batch runner and submission validator are released. The current candidate does not
implement that intake or an automatic refresh pipeline.

A submission PR should contain a model/configuration manifest, per-case terminal
actions, per-case scores and credit ledgers, plus links and hashes for trace and
replication artifacts. Large artifacts should live in a versioned dataset repository,
not Git history. Maintainers recompute scores, validate the full case set and budget,
and check evidence before merging. A subsequent Space deployment displays accepted
records. The submitter's compute/API account funds inference; the Space needs only
CPU resources for display. Never run arbitrary participant code in the Space.

The proposed interface has three views:

1. **Leaderboard:** track/version selector; loss rank; valid cases; macro-averaged
   forecast credits; local/hosted deployment; model total/active parameters where
   disclosed; submission date; code/model links; verification status.
2. **Cost and reliability:** loss versus credits, validity and calls per case. Budget
   and call-limit tracks stay separate; do not invent a loss-plus-cost score.
3. **Tool use:** requested backend shares, non-error returns, errors, call counts and
   selected public traces. Always display denominators and retain failed cases.

Verification labels should distinguish author-reported, independently rescored and
maintainer-reproduced results. Rescoring proves score consistency, not absence of
target leakage. Keep public-reproduction and future held-out tracks separate.

## Adoption priorities

Release a runnable evaluation before advertising open submissions: frozen data with
license notices, a small smoke example, batch evaluation and resume support, a
submission validator and one documented adapter for adding a model. Preserve the
paper cohort and scoring versions; create new tracks for changed contracts or fresh
dates. Publish releases and a changelog, link the eventual paper in CITATION.cff,
and archive a versioned release with a DOI when available. Never invent a paper or
DOI placeholder that looks real. Provide a short contribution guide and submission
example; review outside contributions with a documented process. Recognition and
citations cannot be guaranteed, but reusable data and low-friction reproduction
make the benchmark useful beyond its initial result table.

Precedent checked September 15, 2026: [GIFT-Eval's submission instructions](https://github.com/SalesforceAIResearch/gift-eval#submitting-your-results)
ask participants to run evaluations and open a PR containing results and model
metadata. FWBench additionally needs action and budget evidence for decision scoring.

## Initial release scope

Only the Language Model track will be released initially. Entrants use the frozen
harness, prompt, forecasting pool and scoring protocol. Changes to model adapters
require declared configuration and compatibility review; they must not silently
change the agent policy. Custom agent harnesses are outside this release. Historical
provider wrappers retain their original identities; equivalence to the reorganized
SDK must be established before claiming exact reproducibility.
