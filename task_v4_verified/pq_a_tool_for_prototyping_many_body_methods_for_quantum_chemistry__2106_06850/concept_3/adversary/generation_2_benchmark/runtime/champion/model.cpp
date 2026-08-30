#include <array>
#include <cmath>
#include <fstream>
#include <vector>

struct Pair { int source, destination; double sign; };
static int dimension, reference;
static std::vector<std::vector<Pair>> operators;

extern "C" int initialize(const char* path) {
    std::ifstream input(path);
    int gate_count, budget, ignored;
    input >> dimension >> gate_count >> budget >> reference;
    double amplitude;
    for (int index = 0; index < dimension; ++index) input >> amplitude;
    for (int index = 0; index < dimension; ++index) input >> ignored;
    operators.resize(gate_count);
    for (auto& pairs : operators) {
        int rank, count;
        input >> rank;
        for (int index = 0; index < 2*rank; ++index) input >> ignored;
        input >> count;
        pairs.resize(count);
        for (auto& pair : pairs) input >> pair.source >> pair.destination >> pair.sign;
    }
    return dimension;
}

extern "C" void evaluate(int count, const int* labels, const double* angles, double* state, double* jacobian) {
    for (int index = 0; index < dimension; ++index) state[index] = index == reference;
    for (int index = 0; index < dimension*count; ++index) jacobian[index] = 0;
    for (int position = 0; position < count; ++position) {
        double cosine = std::cos(angles[position]), sine = std::sin(angles[position]);
        for (const auto& pair : operators[labels[position]]) {
            double source = state[pair.source], destination = state[pair.destination];
            state[pair.source] = cosine*source-pair.sign*sine*destination;
            state[pair.destination] = pair.sign*sine*source+cosine*destination;
            for (int parameter = 0; parameter < position; ++parameter) {
                double source_derivative = jacobian[pair.source*count+parameter];
                double destination_derivative = jacobian[pair.destination*count+parameter];
                jacobian[pair.source*count+parameter] = cosine*source_derivative-pair.sign*sine*destination_derivative;
                jacobian[pair.destination*count+parameter] = pair.sign*sine*source_derivative+cosine*destination_derivative;
            }
            jacobian[pair.source*count+position] = -pair.sign*state[pair.destination];
            jacobian[pair.destination*count+position] = pair.sign*state[pair.source];
        }
    }
}
