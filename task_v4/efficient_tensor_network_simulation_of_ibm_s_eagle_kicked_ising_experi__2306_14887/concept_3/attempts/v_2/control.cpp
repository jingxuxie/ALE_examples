#include <complex>
#include <vector>
#include <cmath>
#include <algorithm>
#include <omp.h>
#include <random>

using Complex = std::complex<double>;
constexpr int size = 4096;
constexpr int depth = 24;
const int groups[12] = {0,0,1,0,1,1,0,1,0,1,1,0};

struct Scenario {
    double gains[2];
    std::vector<Complex> diagonal[2];
    std::vector<Complex> drift;
};

struct Ensemble {
    std::vector<Scenario> scenarios;
};

void rotate(Complex* state, int site, double angle) {
    double cosine = std::cos(angle / 2);
    Complex sine(0, -std::sin(angle / 2));
    int stride = 1 << site;
    for (int base = 0; base < size; base += 2 * stride) {
        for (int offset = 0; offset < stride; ++offset) {
            int index = base + offset;
            Complex first = state[index];
            Complex second = state[index + stride];
            state[index] = cosine * first + sine * second;
            state[index + stride] = sine * first + cosine * second;
        }
    }
}

extern "C" void* create_ensemble(const double* parameters, int count) {
    Ensemble* ensemble = new Ensemble;
    ensemble->scenarios.resize(count);
    for (int scenario_index = 0; scenario_index < count; ++scenario_index) {
        const double* values = parameters + 27 * scenario_index;
        Scenario& scenario = ensemble->scenarios[scenario_index];
        scenario.gains[0] = 1 + values[0];
        scenario.gains[1] = 1 + values[1];
        scenario.diagonal[0].resize(size);
        scenario.diagonal[1].resize(size);
        scenario.drift.resize(size);
        for (int index = 0; index < size; ++index) {
            double phase[2] = {0,0};
            double drift_phase = 0;
            for (int site = 0; site < 12; ++site) {
                int sign = 1 - 2 * ((index >> site) & 1);
                int neighbor_sign = 1 - 2 * ((index >> ((site + 1) % 12)) & 1);
                phase[site % 2] += M_PI / 4 * (1 + values[2] + values[3 + site]) * sign * neighbor_sign;
                drift_phase -= values[15 + site] * sign / 2;
            }
            scenario.diagonal[0][index] = std::polar(1.0, phase[0]);
            scenario.diagonal[1][index] = std::polar(1.0, phase[1]);
            scenario.drift[index] = std::polar(1.0, drift_phase);
        }
    }
    return ensemble;
}

extern "C" void delete_ensemble(void* pointer) {
    delete static_cast<Ensemble*>(pointer);
}

extern "C" void evaluate_full(void* pointer, const double* angles, double* fidelities, double* gradients, double* error_gradients, int threads) {
    Ensemble& ensemble = *static_cast<Ensemble*>(pointer);
    int count = ensemble.scenarios.size();
    #pragma omp parallel for num_threads(threads) schedule(static)
    for (int scenario_index = 0; scenario_index < count; ++scenario_index) {
        const Scenario& scenario = ensemble.scenarios[scenario_index];
        std::vector<Complex> state(size, Complex(1.0/64, 0));
        std::vector<Complex> history(gradients ? depth * size : 0);
        for (int layer = 0; layer < depth; ++layer) {
            for (int index = 0; index < size; ++index) state[index] *= scenario.diagonal[layer % 2][index];
            for (int site = 0; site < 12; ++site) rotate(state.data(), site, angles[2 * layer + groups[site]] * scenario.gains[groups[site]]);
            if (gradients) std::copy(state.begin(), state.end(), history.begin() + layer * size);
            for (int index = 0; index < size; ++index) state[index] *= scenario.drift[index];
        }
        Complex amplitude = (state[0] + state[size - 1]) / std::sqrt(2.0);
        fidelities[scenario_index] = std::norm(amplitude);
        if (!gradients) continue;
        std::vector<Complex> adjoint(size, 0);
        adjoint[0] = adjoint[size - 1] = amplitude / std::sqrt(2.0);
        double* gradient = gradients + scenario_index * 48;
        std::fill(gradient, gradient + 48, 0);
        double* error_gradient = error_gradients ? error_gradients + scenario_index * 27 : nullptr;
        if (error_gradient) std::fill(error_gradient, error_gradient + 27, 0);
        for (int layer = depth - 1; layer >= 0; --layer) {
            for (int index = 0; index < size; ++index) adjoint[index] *= std::conj(scenario.drift[index]);
            const Complex* forward = history.data() + layer * size;
            if (error_gradient) {
                for (int index = 0; index < size; ++index) {
                    double contribution = std::imag(std::conj(adjoint[index]) * forward[index]);
                    for (int site = 0; site < 12; ++site) error_gradient[15 + site] += contribution * (1 - 2 * ((index >> site) & 1));
                }
            }
            for (int site = 0; site < 12; ++site) {
                int stride = 1 << site;
                double total = 0;
                for (int base = 0; base < size; base += 2 * stride) {
                    for (int offset = 0; offset < stride; ++offset) {
                        int index = base + offset;
                        total += std::imag(std::conj(adjoint[index]) * forward[index + stride]);
                        total += std::imag(std::conj(adjoint[index + stride]) * forward[index]);
                    }
                }
                gradient[2 * layer + groups[site]] += scenario.gains[groups[site]] * total;
                if (error_gradient) error_gradient[groups[site]] += angles[2 * layer + groups[site]] * total;
            }
            for (int site = 11; site >= 0; --site) rotate(adjoint.data(), site, -angles[2 * layer + groups[site]] * scenario.gains[groups[site]]);
            if (error_gradient) {
                for (int index = 0; index < size; ++index) {
                    Complex before = layer ? history[(layer - 1) * size + index] * scenario.drift[index] : Complex(1.0/64, 0);
                    Complex after = before * scenario.diagonal[layer % 2][index];
                    double contribution = -M_PI / 2 * std::imag(std::conj(adjoint[index]) * after);
                    for (int edge = layer % 2; edge < 12; edge += 2) {
                        double value = contribution * (1 - 2 * (((index >> edge) ^ (index >> ((edge + 1) % 12))) & 1));
                        error_gradient[3 + edge] += value;
                        error_gradient[2] += value;
                    }
                }
            }
            for (int index = 0; index < size; ++index) adjoint[index] *= std::conj(scenario.diagonal[layer % 2][index]);
        }
    }
}

extern "C" void evaluate(void* pointer, const double* angles, double* fidelities, double* gradients, int threads) {
    evaluate_full(pointer, angles, fidelities, gradients, nullptr, threads);
}

extern "C" void nominal_sources(const double* angles, const double* fields, int field_count, Complex* output, int threads) {
    double parameters[27] = {};
    Ensemble* ensemble = static_cast<Ensemble*>(create_ensemble(parameters,1));
    const Scenario& scenario = ensemble->scenarios[0];
    std::vector<Complex> history(depth * size), after_diagonal(depth * size);
    std::vector<Complex> state(size,Complex(1.0/64,0));
    for (int layer = 0; layer < depth; ++layer) {
        for (int index = 0; index < size; ++index) state[index] *= scenario.diagonal[layer%2][index];
        std::copy(state.begin(),state.end(),after_diagonal.begin()+layer*size);
        for (int site = 0; site < 12; ++site) rotate(state.data(),site,angles[2*layer+groups[site]]);
        std::copy(state.begin(),state.end(),history.begin()+layer*size);
    }
    int source_count = 49 + depth * field_count;
    std::copy(state.begin(),state.end(),output+source_count*size);
    #pragma omp parallel for num_threads(threads) schedule(dynamic)
    for (int source = 0; source < source_count; ++source) {
        std::vector<Complex> tangent(size,0);
        int insertion_layer = source < 48 ? source/2 : (source-49)%depth;
        if (source == 48) {
            for (int layer = 0; layer < depth; ++layer) {
                for (int index = 0; index < size; ++index) {
                    tangent[index] *= scenario.diagonal[layer%2][index];
                    int total_sign = 0;
                    for (int edge = layer%2; edge < 12; edge += 2) total_sign += 1-2*(((index>>edge)^(index>>((edge+1)%12)))&1);
                    tangent[index] += Complex(0,M_PI/4*total_sign)*after_diagonal[layer*size+index];
                }
                for (int site = 0; site < 12; ++site) rotate(tangent.data(),site,angles[2*layer+groups[site]]);
            }
        } else {
            const Complex* forward = history.data()+insertion_layer*size;
            for (int index = 0; index < size; ++index) {
                if (source < 48) {
                    Complex total = 0;
                    for (int site = 0; site < 12; ++site) if (groups[site] == source%2) total += forward[index^(1<<site)];
                    tangent[index] = Complex(0,-.5)*total;
                } else {
                    const double* field = fields+12*((source-49)/depth);
                    double total = 0;
                    for (int site = 0; site < 12; ++site) total += field[site]*(1-2*((index>>site)&1));
                    tangent[index] = Complex(0,-.5*total)*forward[index];
                }
            }
            for (int layer = insertion_layer+1; layer < depth; ++layer) {
                for (int index = 0; index < size; ++index) tangent[index] *= scenario.diagonal[layer%2][index];
                for (int site = 0; site < 12; ++site) rotate(tangent.data(),site,angles[2*layer+groups[site]]);
            }
        }
        std::copy(tangent.begin(),tangent.end(),output+source*size);
    }
    delete ensemble;
}

extern "C" void approximate_gauges(const double* constants, const double* linear, const double* quadratic, const double* drift_quadratic,
                                    int field_count, int restarts, int steps, unsigned seed, unsigned* masks, double* losses) {
    std::mt19937 generator(seed);
    std::uniform_real_distribution<double> uniform(0,1);
    auto loss = [&](unsigned mask) {
        double bits[24], signs[24];
        double sign = 1;
        for (int layer = 0; layer < 24; ++layer) {
            bits[layer] = (mask>>layer)&1;
            if (bits[layer]) sign = -sign;
            signs[layer] = sign;
        }
        double calibration_loss = -1e9;
        for (int corner = 0; corner < 8; ++corner) {
            double value = constants[corner];
            for (int row = 0; row < 24; ++row) {
                double subtotal = linear[corner*24+row];
                for (int column = 0; column < 24; ++column) subtotal += quadratic[corner*576+row*24+column]*bits[column];
                value += bits[row]*subtotal;
            }
            calibration_loss = std::max(calibration_loss,value);
        }
        double drift_loss = 0;
        for (int field = 0; field < field_count; ++field) {
            double value = 0;
            for (int row = 0; row < 24; ++row) {
                double subtotal = 0;
                for (int column = 0; column < 24; ++column) subtotal += drift_quadratic[field*576+row*24+column]*signs[column];
                value += signs[row]*subtotal;
            }
            drift_loss = std::max(drift_loss,value);
        }
        return calibration_loss+drift_loss;
    };
    unsigned overall_mask = 0;
    double overall_loss = loss(0);
    for (int restart = 0; restart < restarts; ++restart) {
        unsigned mask = restart%3 ? overall_mask : (generator()&0xffffff);
        double value = loss(mask);
        unsigned best_mask = mask;
        double best_loss = value;
        for (int step = 0; step < steps; ++step) {
            double temperature = .008*std::pow(.00002/.008,double(step)/(steps-1));
            unsigned candidate = mask ^ (1U << (generator()%24));
            if (generator()%4 == 0) candidate ^= (1U << (generator()%24));
            double candidate_loss = loss(candidate);
            if (candidate_loss < value || uniform(generator) < std::exp((value-candidate_loss)/temperature)) {
                mask = candidate;
                value = candidate_loss;
            }
            if (value < best_loss) { best_loss = value; best_mask = mask; }
        }
        masks[restart] = best_mask;
        losses[restart] = best_loss;
        if (best_loss < overall_loss) { overall_loss = best_loss; overall_mask = best_mask; }
    }
}
