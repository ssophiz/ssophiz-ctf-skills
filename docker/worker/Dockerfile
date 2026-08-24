FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash binutils build-essential ca-certificates curl file gdb git jq libssl-dev \
    ffmpeg netcat-openbsd openssh-client p7zip-full patchelf python3 python3-pip python3-venv \
    radare2 strace unzip wget xxd && \
    python3 -m pip install --no-cache-dir \
      angr capstone cryptography flask-unsign itsdangerous PyJWT pwntools requests ropper z3-solver && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 worker && mkdir /workspace && chown worker:worker /workspace

USER worker
WORKDIR /workspace
CMD ["sleep", "infinity"]
