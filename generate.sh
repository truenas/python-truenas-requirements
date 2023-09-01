#!/bin/sh
docker run --rm -v $(pwd):/work -w /work debian:bullseye sh -c 'apt-get update && apt-get install -y git libffi-dev python3-virtualenv && python3 generate.py'
