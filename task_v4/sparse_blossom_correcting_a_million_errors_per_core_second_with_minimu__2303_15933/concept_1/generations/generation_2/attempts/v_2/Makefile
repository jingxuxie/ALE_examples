.RECIPEPREFIX := >
CXX = /usr/bin/g++
CXXFLAGS = -O3 -march=native -ffast-math -std=c++17 -fPIC

final.so: final.cpp
>$(CXX) $(CXXFLAGS) -shared final.cpp -o final.so
