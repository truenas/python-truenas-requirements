#!/bin/sh
docker pull debian:trixie
docker run --rm -v $(pwd):/work -w /work debian:trixie sh -c 'apt-get update && apt-get install -y curl git libffi-dev python3-virtualenv python3.13 python3.13-dev && curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && PATH="$PATH:$HOME/.cargo/bin" python3.13 generate.py'
