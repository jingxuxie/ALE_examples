#include <cmath>
#include <complex>
#include <vector>

using Complex = std::complex<double>;
constexpr int qubits = 12;
constexpr int dimension = 1 << qubits;
constexpr int depth = 24;

int control_group(int site) {
    const int groups[qubits] = {0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0};
    return groups[site];
}

void kick(std::vector<Complex>& state, int site, double angle) {
    const int stride = 1 << site;
    const double cosine = std::cos(angle * 0.5);
    const Complex sine(0.0, -std::sin(angle * 0.5));
    for (int block = 0; block < dimension; block += 2 * stride) {
        for (int offset = 0; offset < stride; ++offset) {
            const int lower = block + offset;
            const int upper = lower + stride;
            const Complex first = state[lower];
            const Complex second = state[upper];
            state[lower] = cosine * first + sine * second;
            state[upper] = sine * first + cosine * second;
        }
    }
}

extern "C" void fidelity_gradient(const double* controls, const double* scenarios,
                                    int scenario_count, double* fidelities,
                                    double* gradients) {
    for (int scenario_index = 0; scenario_index < scenario_count; ++scenario_index) {
        const double* scenario = scenarios + scenario_index * 14;
        std::vector<Complex> phases[2];
        for (int matching = 0; matching < 2; ++matching) {
            phases[matching].resize(dimension);
            for (int basis = 0; basis < dimension; ++basis) {
                double energy = 0.0;
                for (int edge = matching; edge < qubits; edge += 2) {
                    const int neighbor = (edge + 1) % qubits;
                    const int sign = 1 - 2 * (((basis >> edge) ^ (basis >> neighbor)) & 1);
                    energy += sign * (1.0 + scenario[2 + edge]);
                }
                phases[matching][basis] = std::exp(Complex(0.0, M_PI * 0.25 * energy));
            }
        }
        std::vector<std::vector<Complex>> history(depth + 1, std::vector<Complex>(dimension));
        std::fill(history[0].begin(), history[0].end(), Complex(1.0 / std::sqrt(dimension), 0.0));
        for (int layer = 0; layer < depth; ++layer) {
            history[layer + 1] = history[layer];
            auto& state = history[layer + 1];
            for (int basis = 0; basis < dimension; ++basis) {
                state[basis] *= phases[layer % 2][basis];
            }
            for (int site = 0; site < qubits; ++site) {
                const int group = control_group(site);
                kick(state, site, controls[2 * layer + group] * (1.0 + scenario[group]));
            }
        }
        const Complex overlap = (history[depth][0] + history[depth][dimension - 1]) / std::sqrt(2.0);
        fidelities[scenario_index] = std::norm(overlap);
        std::vector<Complex> costate(dimension, 0.0);
        costate[0] = costate[dimension - 1] = overlap / std::sqrt(2.0);
        for (int layer = depth - 1; layer >= 0; --layer) {
            double* gradient = gradients + scenario_index * 2 * depth + 2 * layer;
            gradient[0] = gradient[1] = 0.0;
            for (int site = 0; site < qubits; ++site) {
                const int group = control_group(site);
                Complex inner = 0.0;
                for (int basis = 0; basis < dimension; ++basis) {
                    inner += std::conj(costate[basis]) * history[layer + 1][basis ^ (1 << site)];
                }
                gradient[group] += (1.0 + scenario[group]) * inner.imag();
            }
            for (int site = 0; site < qubits; ++site) {
                const int group = control_group(site);
                kick(costate, site, -controls[2 * layer + group] * (1.0 + scenario[group]));
            }
            for (int basis = 0; basis < dimension; ++basis) {
                costate[basis] *= std::conj(phases[layer % 2][basis]);
            }
        }
    }
}
