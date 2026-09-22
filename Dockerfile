# syntax=docker/dockerfile:1
# Python image digest resolved on 2026-09-15. Update intentionally, with validation.
FROM python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84 AS dependencies
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
WORKDIR /opt/fwbench
RUN python -m pip install --no-cache-dir uv==0.11.8
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM dependencies AS runtime
COPY benchmark ./benchmark
COPY configs ./configs
COPY results ./results
ENV PATH="/opt/fwbench/.venv/bin:$PATH" HOME=/tmp
USER 10001:10001
ENTRYPOINT ["fwb"]
CMD ["--help"]

FROM runtime AS test
USER root
COPY tests ./tests
COPY leaderboard ./leaderboard
RUN uv sync --locked --extra dev --no-editable
USER 10001:10001
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-q", "-p", "no:cacheprovider"]

FROM runtime AS final
