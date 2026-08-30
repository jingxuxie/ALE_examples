#!/bin/sh
set -eu
cd "$(dirname "$0")"
g++ -O3 -std=c++17 -ffp-contract=off -fPIC -shared kernel.cpp -o kernel.so
