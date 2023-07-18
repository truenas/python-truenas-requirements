#!/bin/sh -ex
virtualenv --python=python3.11 v
v/bin/pip install Cython==0.29.36
v/bin/pip install -r requirements.txt
