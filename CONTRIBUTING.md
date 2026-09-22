# Contributing to FWBench

Submit changes through a pull request targeting `main`. Direct pushes to `main`
are not permitted. Use a topic branch in this repository if you have write access,
or a fork otherwise. Maintainers merge after CI passes and review is complete.

## Development

```bash
uv sync --locked --python 3.11 --extra dev
uv run --no-sync bash scripts/check.sh
```

For changes affecting the container environment:

```bash
docker build --target test -t fwbench-test .
docker run --rm --network none fwbench-test
```

Describe the problem, the resulting behavior and relevant validation in the PR.
Keep unrelated changes separate. Update documentation when behavior changes.

## Evaluation changes

The initial release covers the Language Model track with a fixed harness, prompt,
forecasting pool and scoring protocol. Changes to these components must state their
impact on comparability and benchmark versioning. Preserve published results and
provenance; do not silently replace historical scores with a changed evaluator.

Leaderboard submissions follow the [submission protocol](docs/leaderboard.md).
Include the model configuration and evaluation evidence required there. Do not
submit only a modified aggregate score table.

For new data sources, include provenance, reuse terms and transformation details.
Do not include credentials, model weights, or data outside the declared release.
