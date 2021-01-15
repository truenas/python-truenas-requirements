#!/bin/sh -ex
virtualenv --python=python3.9 v
v/bin/pip install -r requirements.txt
