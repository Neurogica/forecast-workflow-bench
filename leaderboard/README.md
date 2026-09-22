---
title: FWBench | Neurogica
emoji: 📊
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.15.1
app_file: app.py
license: apache-2.0
---

# FWBench Leaderboard

[Dataset](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench) ·
[Code and documentation](https://github.com/Neurogica/forecast-workflow-bench) ·
[Neurogica](https://neurogica.com/)

Compare ten language-model configurations on 1,251 electricity and cycle-hire
cases. The ranking uses **S**, the combined decision-loss and forecast-cost
objective stated in the agent instructions. Lower scores are better. Decision
loss, valid plans and forecast credits are shown alongside the rank; forecasting
reference policies are displayed separately.

Filter by SLM, larger local model or hosted LLM, and sort by score, loss, credits
or validity. Filtering and sorting preserve each model's overall rank.

## Run with uv

From a checkout of the code repository:

```bash
uv sync --locked --extra leaderboard
uv run --no-sync python leaderboard/app.py
```

Open `http://127.0.0.1:7860`. No GPU, model weights or API credentials are required.
The application displays the paper's results; it does not execute evaluations.
See the code repository for the evaluation protocol and submission requirements.

## License

Application code: [Apache-2.0](LICENSE). Bundled fonts retain their SIL Open Font
Licenses; see [asset notices](assets/NOTICE.md). Neurogica branding and the
background illustration are not included in the code license.
