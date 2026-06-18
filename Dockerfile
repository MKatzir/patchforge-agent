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
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir ghidriff litellm

ARG GHIDRA_VERSION=11.2.1
RUN mkdir -p /opt/ghidra \
    && curl -Lf "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.0.3_build/ghidra_11.0.3_PUBLIC_20240410.zip" -o /tmp/ghidra.zip \
    && unzip /tmp/ghidra.zip -d /opt/ghidra \
    && rm /tmp/ghidra.zip
WORKDIR /app
# 1. Update apt and install curl (needed to fetch the modern repository)
RUN apt-get update && apt-get install -y curl

# 2. Fetch the setup script for modern Node.js (v20)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

# 3. Install the modern version of nodejs (npm is automatically included)
RUN apt-get install -y nodejs

# 4. NOW install opencode permanently
RUN npm install -g opencode-ai

CMD ["/bin/bash"]
