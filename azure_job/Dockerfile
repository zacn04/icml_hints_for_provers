FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ---- system deps ----
RUN apt-get update && apt-get install -y \
    curl git ca-certificates build-essential \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# ---- python deps ----
RUN pip3 install --upgrade pip
RUN pip3 install \
    torch \
    transformers \
    accelerate \
    sentencepiece \
    rich \
    pyyaml

# ---- disable git fsmonitor globally ----
RUN git config --system core.fsmonitor false && \
    git config --system core.untrackedCache false

# ---- install elan ----
RUN curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y

ENV PATH="/root/.elan/bin:${PATH}"

# ---- workspace ----
WORKDIR /workspace

# ---- copy lean sources only ----
COPY lean /workspace/lean

WORKDIR /workspace/lean
# Fetch dependencies and download prebuilt mathlib cache (much faster than building from source)
RUN lake update && lake exe cache get && lake build

WORKDIR /workspace

