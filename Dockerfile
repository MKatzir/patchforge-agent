FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    git \
    openjdk-17-jre-headless \
    python3 \
    python3-pip \
    unzip \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir ghidriff litellm

ARG GHIDRA_VERSION=11.0.3
RUN mkdir -p /opt/ghidra \
    && curl -Lf "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.0.3_build/ghidra_11.0.3_PUBLIC_20240410.zip" -o /tmp/ghidra.zip \
    && unzip /tmp/ghidra.zip -d /opt/ghidra \
    && rm /tmp/ghidra.zip

WORKDIR /app

RUN npm install -g opencode-ai

CMD ["/bin/bash"]