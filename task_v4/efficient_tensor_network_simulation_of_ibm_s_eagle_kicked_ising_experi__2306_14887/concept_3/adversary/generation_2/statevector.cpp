#include <algorithm>
#include <cmath>
#include <complex>
#include <vector>

using Complex = std::complex<double>;
constexpr int qubits = 12;
constexpr int dimension = 1 << qubits;
constexpr int depth = 24;
const int groups[qubits] = {0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0};

void kick(std::vector<Complex>& state, int site, double cosine, Complex sine) {
    const int stride = 1 << site;
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

void single(const double* controls, const double* scenario, bool gradient_requested,
            double* fidelity, double* gradient, double* error_gradient = nullptr) {
    std::vector<Complex> phases[2];
    std::vector<Complex> drift[2];
    for (int matching = 0; matching < 2; ++matching) {
        phases[matching].resize(dimension);
        for (int basis = 0; basis < dimension; ++basis) {
            double energy = 0.0;
            for (int edge = matching; edge < qubits; edge += 2) {
                const int neighbor = (edge + 1) % qubits;
                const int sign = 1 - 2 * (((basis >> edge) ^ (basis >> neighbor)) & 1);
                energy += sign * (1.0 + scenario[2] + scenario[3 + edge]);
            }
            phases[matching][basis] = std::exp(Complex(0.0, M_PI * 0.25 * energy));
        }
    }
    for (int matching = 0; matching < 2; ++matching) {
        drift[matching].resize(dimension);
        for (int basis = 0; basis < dimension; ++basis) {
            double phase = 0.0;
            for (int site = 0; site < qubits; ++site) {
                phase += scenario[15 + 12 * matching + site] * (1 - 2 * ((basis >> site) & 1));
            }
            drift[matching][basis] = std::exp(Complex(0.0, -0.5 * phase));
        }
    }
    double cosines[depth][2];
    Complex sines[depth][2];
    for (int layer = 0; layer < depth; ++layer) {
        for (int group = 0; group < 2; ++group) {
            const double half_angle = controls[2 * layer + group] * (1.0 + scenario[group]) * 0.5;
            cosines[layer][group] = std::cos(half_angle);
            sines[layer][group] = Complex(0.0, -std::sin(half_angle));
        }
    }
    std::vector<std::vector<Complex>> history;
    std::vector<std::vector<Complex>> bond_history;
    if (gradient_requested) {
        history.resize(depth, std::vector<Complex>(dimension));
    }
    if (error_gradient != nullptr) {
        bond_history.resize(depth, std::vector<Complex>(dimension));
        std::fill(error_gradient, error_gradient + 39, 0.0);
    }
    std::vector<Complex> state(dimension, 1.0 / std::sqrt(dimension));
    for (int layer = 0; layer < depth; ++layer) {
        for (int basis = 0; basis < dimension; ++basis) {
            state[basis] *= phases[layer % 2][basis];
        }
        if (error_gradient != nullptr) {
            bond_history[layer] = state;
        }
        for (int site = 0; site < qubits; ++site) {
            const int group = groups[site];
            kick(state, site, cosines[layer][group], sines[layer][group]);
        }
        if (gradient_requested) {
            history[layer] = state;
        }
        for (int basis = 0; basis < dimension; ++basis) {
            state[basis] *= drift[layer % 2][basis];
        }
    }
    const Complex overlap = (state[0] + state[dimension - 1]) / std::sqrt(2.0);
    *fidelity = std::norm(overlap);
    if (!gradient_requested) {
        return;
    }
    std::vector<Complex> costate(dimension, 0.0);
    costate[0] = costate[dimension - 1] = overlap / std::sqrt(2.0);
    for (int layer = depth - 1; layer >= 0; --layer) {
        for (int basis = 0; basis < dimension; ++basis) {
            costate[basis] *= std::conj(drift[layer % 2][basis]);
        }
        if (error_gradient != nullptr) {
            for (int site = 0; site < qubits; ++site) {
                Complex inner = 0.0;
                for (int basis = 0; basis < dimension; ++basis) {
                    inner += std::conj(costate[basis]) * history[layer][basis]
                        * static_cast<double>(1 - 2 * ((basis >> site) & 1));
                }
                error_gradient[15 + 12 * (layer % 2) + site] += inner.imag();
            }
        }
        gradient[2 * layer] = gradient[2 * layer + 1] = 0.0;
        for (int site = 0; site < qubits; ++site) {
            const int group = groups[site];
            Complex inner = 0.0;
            for (int basis = 0; basis < dimension; ++basis) {
                inner += std::conj(costate[basis]) * history[layer][basis ^ (1 << site)];
            }
            gradient[2 * layer + group] += (1.0 + scenario[group]) * inner.imag();
        }
        if (error_gradient != nullptr) {
            for (int group = 0; group < 2; ++group) {
                error_gradient[group] += controls[2 * layer + group] * gradient[2 * layer + group]
                    / (1.0 + scenario[group]);
            }
        }
        for (int site = 0; site < qubits; ++site) {
            const int group = groups[site];
            kick(costate, site, cosines[layer][group], std::conj(sines[layer][group]));
        }
        if (error_gradient != nullptr) {
            for (int edge = layer % 2; edge < qubits; edge += 2) {
                Complex inner = 0.0;
                const int neighbor = (edge + 1) % qubits;
                for (int basis = 0; basis < dimension; ++basis) {
                    const int sign = 1 - 2 * (((basis >> edge) ^ (basis >> neighbor)) & 1);
                    inner += std::conj(costate[basis]) * bond_history[layer][basis] * static_cast<double>(sign);
                }
                const double derivative = -M_PI * 0.5 * inner.imag();
                error_gradient[2] += derivative;
                error_gradient[3 + edge] += derivative;
            }
        }
        for (int basis = 0; basis < dimension; ++basis) {
            costate[basis] *= std::conj(phases[layer % 2][basis]);
        }
    }
}

extern "C" void evaluate(const double* controls, const double* scenarios, int count,
                          int gradient_requested, double* fidelities, double* gradients) {
    for (int scenario_index = 0; scenario_index < count; ++scenario_index) {
        single(controls, scenarios + 39 * scenario_index, gradient_requested != 0,
               fidelities + scenario_index, gradients + 48 * scenario_index);
    }
}

extern "C" void error_derivatives(const double* controls, const double* scenarios, int count,
                                   double* fidelities, double* gradients) {
    double pulse_gradient[48];
    for (int scenario_index = 0; scenario_index < count; ++scenario_index) {
        single(controls, scenarios + 39 * scenario_index, true, fidelities + scenario_index,
               pulse_gradient, gradients + 39 * scenario_index);
    }
}
