CXX = /usr/bin/g++
CXXFLAGS = -Ofast -march=native -std=c++17 -shared -fPIC

all: solver.so pauli_solver.so

solver.so: solver.cpp
$(CXX) $(CXXFLAGS) $< -o $@

pauli_solver.so: pauli_solver.cpp
$(CXX) $(CXXFLAGS) $< -o $@
