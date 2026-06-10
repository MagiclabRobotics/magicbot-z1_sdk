# Build viz.py on Ubuntu 20.04 (glibc 2.31) for older deployment targets.
# Uses system Python 3.8 from apt (no third-party PPA).
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-tk \
    tk-dev \
    cmake \
    build-essential \
    gcc-10 \
    g++-10 \
    libeigen3-dev \
    pkg-config \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 100 \
    && python3 -m pip install --no-cache-dir -U pip \
    && python3 -m pip install --no-cache-dir pyinstaller \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

