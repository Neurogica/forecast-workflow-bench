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

# Forecast Workflow Bench (FWBench)

Neurogica's Language Model track leaderboard: ten model configurations on
the same 1,251 electricity and cycle-hire cases. Rank uses the explicitly instructed loss–cost objective S and fixed domain-balanced cohort weights. Raw loss, validity and
forecast credits are reported alongside it; fixed policies are separate.

[Code](https://github.com/Neurogica/forecast-workflow-bench) ·
[Dataset](https://huggingface.co/datasets/Neurogica/forecast-workflow-bench) ·
[Neurogica](https://neurogica.com/)

These are author-reported results, not independent certifications. This Space does
not run models, make paid API calls or accept automatic submissions. Evaluation
scope and participation details are available in the application and code repository.

The objective-main-1251-v3 evaluation is complete. The primary-377-v1 dataset tag
remains available for reproducing the earlier release.

## Local preview

```bash
pip install -r requirements.txt
python app.py
```

The Space root requires `app.py`, `view.py`, `styles.css`, `results.json`,
`release-status.json`, `requirements.txt`, this README, `LICENSE`, and the complete `assets/` directory.
SSR is disabled to avoid the private-Space server-rendering failure observed during
initial deployment. Hugging Face repository access controls remain unchanged.

## Assets

The presentation follows Neurogica's white and midnight-blue palette. Inter,
Space Grotesk and IBM Plex Mono are bundled under their accompanying SIL Open Font
Licenses. Asset sources are recorded in `assets/provenance.json`. The Neurogica logo
is a company brand asset and is not licensed under the application's Apache-2.0
license. Experimental results and ranking rules are unchanged by presentation updates.

The city background was supplied by the maintainer for this Space. It is a
presentation asset; the application license does not grant additional image rights.
