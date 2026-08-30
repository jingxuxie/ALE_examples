#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec "${CXX:-g++}" -O3 -ffast-math -march=x86-64 -fPIC -shared kernel.cpp -o kernel.so
