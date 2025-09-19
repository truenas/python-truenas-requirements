#!/bin/sh -ex
virtualenv --python=python3.13 v

v/bin/pip install -r requirements.txt
