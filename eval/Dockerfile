# Sandbox for executing model-generated commands during the hai eval.
# Runs with --network none, a read-only root, and only a copy of the fixture
# mounted read-write.
FROM debian:stable-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git findutils coreutils grep sed gawk tar gzip zip unzip procps file bc \
 && rm -rf /var/lib/apt/lists/*
