#!/bin/sh
set -eu
cd "$(dirname "$0")"
g++ -std=c++11 -O2 -Ishim engine.cpp -o reference_engine
