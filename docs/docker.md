# Docker and reproducibility

The supplied image fixes the **core evaluation harness**, including the scorer,
CLI and runtime dependencies. It is not yet a full forecasting-service image.

## Build and verify

```bash
docker build -t fwbench .
docker run --rm --network none fwbench --help
docker run --rm --network none fwbench results --input leaderboard/results.json

docker build --target test -t fwbench-test .
docker run --rm --network none fwbench-test
```

Building downloads dependencies. Test execution uses synthetic fixtures with no
network, paid API calls, model weights or observation dataset. The test image
passed all 76 tests on Linux amd64. The default image runs as an
unprivileged user. `.dockerignore` excludes credentials and unrelated local files.
The CI workflow builds and tests images without publishing them.

## What is fixed

- Python 3.11 Debian Bookworm base, pinned by image digest in `Dockerfile`.
- uv 0.11.8 and resolved Python packages from `uv.lock`, installed with `--locked`.
- The code and frozen protocol files copied from the build checkout.

For an evaluation, record the code revision, lockfile hash, image ID, platform,
dataset revision and hashes, model revisions, quantization, prompt and protocol:

```bash
docker image inspect fwbench --format '{{.Id}} {{.Os}}/{{.Architecture}}'
sha256sum uv.lock
```

A locally built image ID identifies that build; a published registry digest is a
separate identifier. No container image has been published by this project yet.

## Score local files offline

Place the contract, future-observation JSON array, and terminal answer text in an
input directory. Create a separate output directory. For example, on Linux:

```bash
mkdir -p outputs
docker run --rm --network none --user "$(id -u):$(id -g)" \
  --mount type=bind,src="$(pwd)/inputs",dst=/inputs,readonly \
  --mount type=bind,src="$(pwd)/outputs",dst=/outputs \
  fwbench score --contract /inputs/contract.json \
  --actual /inputs/actual.json --answer /inputs/answer.txt \
  --output /outputs/score.json
```

Scorer targets must not be mounted into the agent's environment. API keys are not
needed for scoring; never bake `.env` or credentials into an image.

## Remaining scope

The default image does **not** install Torch, Chronos or TimesFM, bundle weights,
or include the separately distributed observation dataset. A complete primary-track agent run
still needs pinned forecasting backends and the frozen data. The current image
therefore does not, by itself, reproduce the full paper experiment.

Before distributing a full service image, lock all three forecasting backends and
weight revisions and validate their outputs against the frozen evaluation. Docker
does not fix the host GPU/driver, hardware-dependent numerical behavior, model
quantization, or a hosted API's model updates. Record those separately; bitwise
cross-hardware equivalence is not claimed. A cached-forecast track would also need
its own declared protocol rather than silently replacing live forecasting.

References: [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/)
and [Docker build practices](https://docs.docker.com/build/building/best-practices/).
