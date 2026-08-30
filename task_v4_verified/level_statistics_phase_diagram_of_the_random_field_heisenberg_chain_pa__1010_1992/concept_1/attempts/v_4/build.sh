#!/bin/sh
set -eu
cd "$(dirname "$0")"
gcc -O3 -fPIC -shared fast_transform.c -o fast_transform.so
g++ -O3 -std=c++17 -fPIC -shared native_features.cpp -llapack -lblas -o libnative_features.so
