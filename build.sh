#!/bin/sh -ex
virtualenv --python=python3.8 v
v/bin/pip install -r requirements.txt
