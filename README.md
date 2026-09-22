# Forecast Workflow Bench (FWBench)

[![Dataset](https://img.shields.io/badge/Dataset-1%2C251_cases-c58b44)](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-Space-687f72)](https://huggingface.co/spaces/Neurogica/forecast-workflow-bench-leaderboard)
[![License](https://img.shields.io/badge/Code-Apache--2.0-808080)](LICENSE)

**Evaluating LLM and SLM decisions with budgeted time-series forecast tools.**

Fixed forecasting tools and a common loss–cost objective measure how forecast
selection affects capacity decisions. The current evaluation covers 1,251
electricity and cycle-hire cases, two hosted and eight local configurations.
Code and data support reproducible comparisons and the development of SLMs for
local forecast-based decisions. No conference acceptance is claimed.

<p align="center"><img src="docs/assets/benchmark_overview.png" width="420" alt="FWBench inputs, forecast tools and capacity evaluation"></p>

## Current results

Version: `objective-main-1251-v3`. Lower S is better. Thinking on/off are separate
configurations. Credits exclude language-model inference cost.

| Configuration | Valid / 1,251 | Loss ↓ | Credits ↓ | S ↓ |
| --- | ---: | ---: | ---: | ---: |
| GPT-6 Astra | 1251 | 0.3044 | 2801.7 | 0.3964 |
| Gemma 4 E4B (thinking) | 1251 | 0.3649 | 1209.0 | 1.0465 |
| Qwen3 4B (thinking) | 1237 | 0.5196 | 0.0 | 2.5232 |
| GPT-5.4 nano | 1139 | 0.5160 | 2885.6 | 2.6411 |
| Qwen3 4B | 1242 | 0.7175 | 0.0 | 4.5478 |
| Gemma 4 E4B | 1019 | 0.7074 | 74.1 | 4.6294 |
| Gemma 4 12B | 766 | 0.9611 | 46091.1 | 7.3281 |
| Gemma 4 12B (thinking) | 490 | 1.2837 | 58103.6 | 10.6358 |
| Qwen3.6 35B-A3B (thinking) | 160 | 1.8533 | 1464.2 | 16.4632 |
| Qwen3.6 35B-A3B | 3 | 2.0080 | 1176.3 | 17.9773 |

[Protocol and scoring](docs/objective_protocol.md) · [Results](results/objective-main-1251-v3.json) · [Installation and usage](docs/archived-primary1251-readme.md#-getting-started)

The older [v2 evaluation](docs/archived-primary1251-readme.md) is preserved for
reproduction; its G ranking and loss-only instructions are not the current track.

## Dataset and reproduction

Download the `objective-main-1251-v3/` directory from the Hugging Face dataset.
Inputs and reproduction targets are separate. Targets are public and must never
be exposed to evaluated agents. Verify the payload with its `examples/verify.py`.
The source repository excludes observation histories, targets, model weights and credentials.

Powered by TfL Open Data. Contains OS data © Crown copyright and database rights
2016. Geomni UK Map data © and database rights [2019]. Electricity observations:
U.S. Energy Information Administration. See [component terms](docs/transport_extension.md).

## Figures

<p align="center"><img src="docs/assets/qualitative_comparison.png" width="650" alt="Observed demand and submitted capacities"></p>
<p align="center"><img src="docs/assets/objective_frontier.png" width="650" alt="Decision loss and forecast expenditure"></p>

## Contributing and license

Submit changes through pull requests; see [CONTRIBUTING](CONTRIBUTING.md).
Code: Apache-2.0. Data: source-specific component terms. See [LICENSE](LICENSE)
and the Hugging Face dataset license. Citation metadata is in [CITATION.cff](CITATION.cff).
