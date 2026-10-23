# syntax=docker/dockerfile:1
# Python image digest resolved on 2026-09-15. Update intentionally, with validation.
FROM python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84 AS dependencies
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
WORKDIR /opt/fwbench
COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /uvx /usr/local/bin/
COPY scripts/security/check_build_tls_trust.py scripts/security/check_build_tls_trust.py
# DLA-4845-1: update the signed Bookworm CA package before package downloads.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade ca-certificates \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' ca-certificates)" ge '20250419~deb12u2' \
    && rm -rf /var/lib/apt/lists/* \
    && python scripts/security/check_build_tls_trust.py system uv
# Patched uv bootstraps pip without invoking the base image's old pip CA bundle.
RUN uv pip install --system --no-cache pip==26.2.2 \
    && python scripts/security/check_build_tls_trust.py system pip uv
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM dependencies AS runtime
COPY configs ./configs
COPY leaderboard ./leaderboard
ENV PATH="/opt/fwbench/.venv/bin:$PATH" HOME=/tmp
USER 10001:10001
ENTRYPOINT ["fwb"]
CMD ["--help"]

FROM runtime AS test
USER root
COPY tests ./tests
RUN uv sync --locked --extra dev --no-editable
USER 10001:10001
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-q", "-p", "no:cacheprovider"]

FROM runtime AS final
