#!/bin/sh
docker pull debian:bookworm
docker run --rm -v $(pwd):/work -w /work debian:bookworm sh -c 'apt-get update && apt-get install -y curl git libffi-dev python3-virtualenv && curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && PATH="$PATH:$HOME/.cargo/bin" python3 generate.py'
