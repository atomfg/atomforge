# syntax=docker/dockerfile:1.7
#
# An image with an atomforge host environment and preloaded worker
# environments. See "Containers, design" in the engineering log.
#
# The build context is a host project: a pyproject.toml and uv.lock that
# install atomforge and the model plugins, plus any local sources they refer
# to by relative path. PRELOAD is passed to `atomforge env preload`:
#
#   docker buildx build --platform linux/amd64 \
#       --file atomforge/containers/Dockerfile \
#       --build-arg PRELOAD="orb-v3 mace-mp --task single_point" \
#       --secret id=github_token,env=GITHUB_TOKEN \
#       --tag atomforge:study --load path/to/host-project
#
# The github_token secret is needed only for private git dependencies; it is
# never stored in a layer. Set --build-arg UV_NO_SOURCES=true when the plugins
# are installed from git and declare relative path sources for the workspace.
#
# At run time, bind a writable directory to /cache: checkpoints are
# downloaded there, and environments that were not preloaded are built there
# (with a warning). Local weights must be bound at the absolute path the spec
# records.

ARG BASE_IMAGE=debian:bookworm-slim
ARG UV_VERSION=0.11.33

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${BASE_IMAGE}

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

ARG UV_NO_SOURCES=false
# uv's Python inside the image, so that the environments' interpreters
# resolve at run time; bytecode compiled at build time, since the image is
# read-only at run time.
ENV UV_PYTHON_INSTALL_DIR=/opt/atomforge/python \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_SOURCES=${UV_NO_SOURCES} \
    UV_NO_PROGRESS=1

WORKDIR /opt/atomforge/host
COPY . /opt/atomforge/host

# The host environment. The uv cache lives in this layer only for the step
# and is removed at its end.
RUN --mount=type=secret,id=github_token,required=false \
    set -eu; \
    if [ -s /run/secrets/github_token ]; then \
        export GIT_CONFIG_COUNT=1 \
            GIT_CONFIG_KEY_0="url.https://x-access-token:$(cat /run/secrets/github_token)@github.com/.insteadOf" \
            GIT_CONFIG_VALUE_0="https://github.com/"; \
    fi; \
    UV_CACHE_DIR=/opt/atomforge/uv-cache uv sync --locked --no-dev; \
    rm -rf /opt/atomforge/uv-cache

ENV PATH=/opt/atomforge/host/.venv/bin:${PATH}

# The worker environments, built in one step with one cache, so that the
# environments hardlink the files they share (torch, for instance) and the
# layer stores them once.
ARG PRELOAD
RUN --mount=type=secret,id=github_token,required=false \
    set -eu; \
    if [ -z "${PRELOAD:-}" ]; then echo "PRELOAD is empty" >&2; exit 1; fi; \
    if [ -s /run/secrets/github_token ]; then \
        export GIT_CONFIG_COUNT=1 \
            GIT_CONFIG_KEY_0="url.https://x-access-token:$(cat /run/secrets/github_token)@github.com/.insteadOf" \
            GIT_CONFIG_VALUE_0="https://github.com/"; \
    fi; \
    export ATOMFORGE_ENV_INSTALL_PATH=/opt/atomforge/envs \
        ATOMFORGE_ENV_SEARCH_PATHS=/opt/atomforge/envs \
        UV_CACHE_DIR=/opt/atomforge/uv-cache \
        UV_LINK_MODE=hardlink; \
    atomforge env preload ${PRELOAD}; \
    rm -rf /opt/atomforge/uv-cache; \
    atomforge env list

RUN mkdir -p /cache && chmod 1777 /cache

ENV ATOMFORGE_ENV_SEARCH_PATHS=/opt/atomforge/envs \
    ATOMFORGE_ENV_INSTALL_PATH=/cache/atomforge/envs \
    UV_CACHE_DIR=/cache/uv \
    XDG_CACHE_HOME=/cache \
    HF_HOME=/cache/huggingface \
    TORCH_HOME=/cache/torch

WORKDIR /
