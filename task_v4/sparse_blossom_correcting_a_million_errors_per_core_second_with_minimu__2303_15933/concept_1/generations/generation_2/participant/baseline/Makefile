.RECIPEPREFIX := >
CXX = g++
CXXFLAGS = -O3 -std=c++17 -fPIC -Wall -Wextra

decoder.so: decoder.cpp
>$(CXX) $(CXXFLAGS) -shared decoder.cpp -o decoder.so

.PHONY: all
all: decoder.so
