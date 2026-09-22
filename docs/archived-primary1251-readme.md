# Forecast Workflow Bench (FWBench)

[![Manuscript](https://img.shields.io/badge/Manuscript-in_preparation-566b84)](#-abstract)
[![Dataset](https://img.shields.io/badge/Dataset-primary--1251--v2-c58b44)](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench/tree/primary-1251-v2)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-Space-687f72)](https://huggingface.co/spaces/Neurogica/forecast-workflow-bench-leaderboard)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](pyproject.toml)
[![Docker](https://img.shields.io/badge/Docker-fixed_harness-526d82)](docs/docker.md)
[![License](https://img.shields.io/badge/Code-Apache--2.0-808080)](LICENSE)

**From forecasting to decisions: evaluating how language-model agents use forecasting tools.**

FWBench evaluates LLMs and SLMs that select forecast models, histories and horizons,
then submit constrained capacity plans. Forecasting services and scoring rules stay
fixed so that agents can be compared under a common service budget.


> **Expanded main evaluation:** `primary-1251-v2` contains 1,251 cases across
> winter, July and August electricity and cycle hire. All twelve model
> configurations completed the same cases; the complete results appear below.
> [Expanded protocol](docs/primary_1251_protocol.md) ·
> [Dataset](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench/tree/primary-1251-v2)

<p align="center">
  <img src="docs/assets/benchmark_overview.png" width="420" alt="Paper Figure 1: observed demand and operating contract, agent with forecasting tools, and evaluation against hidden demand">
  <br><em>Figure 1 from the manuscript. The language model is the evaluated agent; forecasting models are its tools.</em>
</p>

Cycle-hire observations: Powered by TfL Open Data. Contains OS data © Crown copyright
and database rights 2016. Geomni UK Map data © and database rights [2019].
See [component terms](docs/transport_extension.md).


**Release status.** This repository contains code, paper figures, aggregate
results and frozen metadata. The observation/target dataset is **available on Hugging Face** as
[`primary-1251-v2`](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench/tree/primary-1251-v2), with the earlier tag preserved. The Space provides a read-only results viewer.
Offline tests and result viewing work now; full reproduction requires the separate
dataset and pinned forecasting backends.
No conference acceptance or PyPI release is claimed.

[Getting started](#-getting-started) · [Results](#-results) ·
[Data](#-dataset) · [Leaderboard](#-leaderboard) · [Citation](#-citation)

## 📖 Abstract

<details>
<summary>Read the manuscript abstract</summary>

Recent advances in time-series foundation models have enabled forecasting
without task-specific training. Whether AI agents can use these models to make
decisions under operational constraints remains insufficiently evaluated.
We present Forecast Workflow Bench (FWBench), which evaluates language models
using fixed forecasting tools under a service budget. Its 1,251 cases combine
real electricity demand and cycle-hire departures with simulated capacity
contracts. Agents select models, histories and horizons, then submit feasible
capacities. We evaluated four hosted and eight local model configurations
through decision loss, validity and forecast expenditure. The best agent
approached fixed-policy decision quality but did not improve the observed
loss–cost frontier. A hindsight catalog oracle achieved lower loss with fewer
credits than fixed TSFM use, indicating room for better tool selection.
Local models differed substantially in feasibility and decision quality;
controlled comparisons showed that TSFM access alone did not ensure improvement.
We release the code and dataset for reproducible evaluation.

</details>

## ✨ Benchmark at a glance

The published **primary-1251-v2** dataset includes 1,091 electricity cases across winter, July and August and 160 cycle-hire cases. All twelve configurations completed the main evaluation; primary-377-v1 remains archived. See [transport construction, terms and results](docs/transport_extension.md).

**Initial release: Language Model track only.** The harness, prompts, forecasting
services and scoring protocol are fixed. Custom harnesses, prompts, agent loops
and multi-agent systems are not admitted to this track. Historical results retain
their recorded provider/transport configurations; new runs must identify their
exact harness version.

- **1,251 cases, two domains:** real electricity demand and cycle-hire departures paired with simulated capacity contracts; twelve model configurations fully evaluated.
- **Fixed forecasting tools:** Chronos-Bolt Tiny, Chronos-2 and TimesFM 2.5, with classical alternatives.
- **Operational decisions:** capacity plans must satisfy capacity-grid and ramp constraints.
- **Forecast-service budget:** model choice, context and horizon affect credits; credits are neither LLM API dollars nor measured runtime.
- **Local agents included:** evaluation of progress toward forecasting and decision support on local hardware.

The expanded ranking minimizes cost-aware G with an explicit forecast-credit penalty
and fixed domain-balanced weights, under a **113,726-credit budget and 12-call limit
per case**. See the [versioned protocol](docs/primary_1251_protocol.md). Invalid answers
remain in the loss. The archived 377-case table used loss-only ranking. Validity, raw
loss and credits are also reported. Fixed forecasting
policies are references outside the agent ranking.
See the [evaluation protocol](docs/primary_protocol.md). Offline [oracle diagnostics](docs/oracle_reference.md) quantify selection headroom without changing the published ranking.

## 🏆 Results

<details>
<summary>All 12 agent configurations and fixed forecasting references</summary>

| Agent | Valid ↑ | Loss ↓ | Forecast credits ↓ | G ↓ |
|:--|--:|--:|--:|--:|
| *Small local language models (SLMs)* | | | | |
| Qwen3 0.6B | 542/1,251 | 1.6675 | **0** | 1.3782 |
| Qwen3 1.7B | 184/1,251 | 1.6466 | 74,037 | 1.3638 |
| Gemma 4 E4B | 947/1,251 | 0.7828 | 22,620 | 0.4955 |
| Gemma 4 E2B | 900/1,251 | 0.7195 | 75,142 | 0.4369 |
| Qwen3 4B | 1,227/1,251 | 0.7105 | 784 | 0.4213 |
| *Larger local language models* | | | | |
| Qwen3.6 35B-A3B | 12/1,251 | 2.0133 | 7,059 | 1.7246 |
| Qwen3.6 27B | 14/1,251 | 2.0090 | 6,256 | 1.7202 |
| Gemma 4 12B | 1,072/1,251 | 0.5817 | 54,692 | 0.2973 |
| *Large language models (LLMs)* | | | | |
| GPT-5.4 mini | 750/1,251 | 0.9941 | 7,279 | 0.7055 |
| GPT-5 nano | 1,200/1,251 | 0.5036 | 21,008 | 0.2162 |
| GPT-5.4 nano | 1,172/1,251 | 0.4711 | 33,577 | 0.1848 |
| GPT-6 Astra | **1,251/1,251** | **0.3062** | 112,429 | **0.0269** |
| *Fixed forecasting policies (separate references)* | | | | |
| Hour-of-day empirical | 1,251/1,251 | 0.3165 | 0 | 0.0273 |
| Fixed routing reference | 1,251/1,251 | 0.3085 | 51,727 | 0.0238 |
| Fixed Chronos-2 | 1,251/1,251 | 0.3050 | 108,783 | 0.0253 |

All models were scored on the same 1,251 cases. Loss, forecast credits and G
use the frozen domain-balanced means; credits are per-case expenditure, not
totals. Bold compares agents only. The default G uses lambda = 0.01.
[Complete results](results/primary-1251.json) ·
[Cost-weight sensitivity](results/primary-1251-sensitivity.json) ·
[Pareto comparisons](results/primary-1251-preference-robustness.json) ·
[Uncertainty and lead breakdowns](results/primary-1251-uncertainty-and-leads.json) ·
[Archived 377-case results](results/primary-377.json).

</details>

Astra achieved the lowest agent loss and G. Fixed Chronos-2 had lower observed
loss and credits than Astra, and fixed routing had the lowest G among fixed
policies at the default coefficient. These are sample-level comparisons;
the paired interval for Astra minus routing included zero.

<p align="center">
  <img src="docs/assets/loss-credit-comparison.png" width="520" alt="Decision loss by model group and the region with lower loss and fewer forecast credits than fixed routing">
  <br><em>All twelve configurations on 1,251 cases. Lower positions indicate lower loss; diamonds identify the lowest-loss model in each group. The star is the hindsight cost-aware oracle.</em>
</p>

### Archived 377-case tool-call composition

<p align="center">
  <img src="docs/assets/tool-call-composition-aligned.png" width="640" alt="Archived 377-case share of captured tool calls by agent, including errors">
  <br><em>Archived tool-call composition, rendered with the same geometry as the two model-share figures.</em>
</p>

### Which forecast models did agents request?

<p align="center">
  <img src="docs/assets/forecast-model-requested-aligned.png" width="640" alt="Requested forecast-model shares for each agent">
</p>

Shares among `forecast_and_plan` and `replay_forecast` requests, **including errors**.
Counts beside the bars cover all 377 cases. Quotes and direct classical-plan calls
are excluded; classical models requested through a forecast tool remain separate.

### Which forecast models returned without tool errors?

<p align="center">
  <img src="docs/assets/forecast-model-returned-aligned.png" width="640" alt="Model shares among forecast requests returned without tool errors">
</p>

The denominator here is requests **returned without a tool error**. Zero denominators
are N/A. A returned result does not establish new inference, forecast accuracy, or
use in the final plan. Both figures include cases with invalid final answers and
follow the paper's model order and Liberation Serif font.
[Counts and definitions](results/forecast-model-usage.json) ·
[Rendering source](docs/assets/render_forecast_usage.py)

## 🛠️ Getting started

### Docker (fixed evaluation harness)

From this checkout, or after cloning the repository once it is published:

```bash
docker build -t fwbench .
docker run --rm --network none fwbench --help
docker run --rm --network none fwbench results --input results/primary-377.json

# Offline tests; no model downloads or paid calls during test execution.
docker build --target test -t fwbench-test .
docker run --rm --network none fwbench-test
```

The image pins the Python base by digest, uv by version, and Python dependencies
through `uv.lock`. It contains the **core harness and scorer**, without model weights
or the separately distributed dataset. See [Docker and reproducibility](docs/docker.md) for the
tested scope and GPU limitations.

<details>
<summary>Local development without Docker</summary>

With uv 0.11.8 installed:

```bash
uv sync --locked --python 3.11 --extra dev
uv run --no-sync bash scripts/check.sh
uv run --no-sync fwb --help
```

The SDK version is `0.3.0.dev4`. The original run identity is preserved in
`benchmark/primary-377/settings.json`; refactoring is not a new experiment.

</details>

### Evaluate an agent

After installing the separate episode data and pinned forecasting backends:

```bash
fwb run --provider local --model YOUR_MODEL \
  --endpoint http://127.0.0.1:8080 \
  --episode PATH_TO_PUBLIC_EPISODE --output runs/example

fwb score --contract PATH_TO_CONTRACT_JSON \
  --actual PATH_TO_SCORER_ONLY_24_HOUR_ARRAY \
  --answer PATH_TO_TERMINAL_ANSWER_TEXT --output runs/score.json
```

Future observations belong to the scorer and must not be visible to the agent.
Local inference has no hosted fallback. `--provider openai` explicitly selects paid
inference and requires `OPENAI_API_KEY` in the environment or a local `.env`.
Runs never overwrite existing output directories. A single episode is not a complete
submission. The publication track requires frozen settings, not arbitrary CLI defaults;
the cleaned CLI does not assert historical rerun parity for every provider wrapper.

## 📊 Dataset

**Distribution: a versioned Hugging Face Dataset.** Repository ID:
`Neurogica/forecast-workflow-bench`.
The [Dataset repository](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench)
contains the **`primary-1251-v2`** dataset and complete evaluation results.
The earlier `primary-377-v1` tag remains available separately.

| Location | Contents | Status |
|:--|:--|:--|
| GitHub checkout | Code, tests, schema, case manifest, tiny examples, aggregate results | Prepared locally |
| Hugging Face Dataset | Observation histories, tasks, provenance, data card, separate reproduction targets | Released as `primary-1251-v2` |
| Hugging Face Space | Read-only leaderboard | Deployed; visibility controlled by the maintainer |

Download the data into a separate directory:

```bash
hf download Neurogica/forecast-workflow-bench --repo-type dataset \
  --revision primary-1251-v2 \
  --local-dir ../fwbench-data
python3 ../fwbench-data/examples/verify.py ../fwbench-data
```

GitHub will not duplicate the full dataset. Dataset revisions and hashes
identify the evaluation snapshot. Public-reproduction targets are separate
from agent-visible histories; this cohort is not an unseen test after release.

Electricity observations originate from U.S. EIA Form EIA-930; cycle-hire departures originate from TfL. Their reuse terms and
protected-material exceptions apply separately from the code's Apache-2.0 license.
Recent dates alone do not guarantee exclusion from all model training.
[Source terms and release requirements](docs/data_release.md).

## 🏅 Leaderboard

**Participants run their agents; maintainers review submissions and update the
leaderboard.** The Space displays results rather than running arbitrary models or
paying for their API calls. Submissions need the complete frozen case set, settings,
traces, scores and budget ledgers. Automatic submission admission is not implemented.

The [Space](https://huggingface.co/spaces/Neurogica/forecast-workflow-bench-leaderboard)
is deployed as a read-only results viewer. See the [participation protocol](docs/leaderboard.md) and
[local Space instructions](leaderboard/README.md).

## 🗂️ Repository layout

```text
forecast-workflow-bench/
├── src/forecast_workflow/  # agents, budget, core, data, decision,
│                          # evaluation, forecasting, tools, and CLI
├── benchmark/             # Frozen settings, case manifest, small examples
├── configs/               # Model and response-format registries
├── results/               # Paper aggregates and tool-use statistics
├── leaderboard/           # Read-only Hugging Face Space
├── docs/                  # Documentation and paper-style figures
├── provenance/            # Source hashes and refactor audit
├── tests/                 # Offline verification
├── scripts/check.sh       # Local checks
├── Dockerfile             # Pinned core harness and test image
└── uv.lock                # Resolved Python dependencies
```

[Architecture](docs/architecture.md) · [Contributing](CONTRIBUTING.md)

## 📝 Citation

Use [CITATION.cff](CITATION.cff) for software metadata. Manuscript bibliographic
information will be added when a public paper identifier is available.

## 📄 License

Code and generated instructions/contracts: [Apache-2.0](LICENSE).
EIA-derived data retain their source provenance and reuse terms. Model weights
retain their own licenses and are not bundled.
