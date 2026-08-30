#include <algorithm>
#include <cmath>
#include <complex>
#include <vector>

using Complex = std::complex<double>;

#ifndef REGISTER_COLUMNS
#define REGISTER_COLUMNS 6
#endif

void small_multiply(const Complex* left, const Complex* right, Complex* output) {
    std::fill(output, output + 36, Complex(0));
    for (int row = 0; row < 6; ++row)
        for (int inner = 0; inner < 6; ++inner)
            for (int column = 0; column < 6; ++column)
                output[row * 6 + column] += left[row * 6 + inner] * right[inner * 6 + column];
}

struct Model {
    static constexpr int dimension = 70;
    static constexpr int columns = REGISTER_COLUMNS;
    static constexpr int size = dimension * columns;
    int degree;
    double radius;
    std::vector<int> row_offsets, indices;
    std::vector<Complex> drift[4], control[3], initial, target[4], coefficients;

    Model(const Complex* drifts, const Complex* controls, const Complex* initials,
          const Complex* targets, const Complex* factors, int order, double bound)
        : degree(order), radius(bound), initial(initials, initials + size), coefficients(factors, factors + order + 1) {
        for (int member = 0; member < 4; ++member)
            target[member].assign(targets + member * size, targets + (member + 1) * size);
        for (int row = 0; row < dimension; ++row) {
            row_offsets.push_back(indices.size());
            for (int column = 0; column < dimension; ++column) {
                int offset = row * dimension + column;
                bool nonzero = false;
                for (int member = 0; member < 4; ++member)
                    nonzero = nonzero || std::abs(drifts[member * dimension * dimension + offset]) > 1e-15;
                for (int channel = 0; channel < 3; ++channel)
                    nonzero = nonzero || std::abs(controls[channel * dimension * dimension + offset]) > 1e-15;
                if (!nonzero) continue;
                indices.push_back(column);
                for (int member = 0; member < 4; ++member)
                    drift[member].push_back(drifts[member * dimension * dimension + offset]);
                for (int channel = 0; channel < 3; ++channel)
                    control[channel].push_back(controls[channel * dimension * dimension + offset]);
            }
        }
        row_offsets.push_back(indices.size());
    }

    void multiply(const Complex* values, const Complex* states, Complex* output, double factor, bool add) const {
        if (!add) std::fill(output, output + size, Complex(0));
        for (int row = 0; row < dimension; ++row) {
            for (int edge = row_offsets[row]; edge < row_offsets[row + 1]; ++edge) {
                Complex value = values[edge] * factor;
                const Complex* source = states + indices[edge] * columns;
                Complex* destination = output + row * columns;
                for (int column = 0; column < columns; ++column)
                    destination[column] += value * source[column];
            }
        }
    }

    void derivative(const Complex* adjoint, const Complex* states, double factor, double* gradient, bool complex_parameters) const {
        for (int row = 0; row < dimension; ++row) {
            for (int edge = row_offsets[row]; edge < row_offsets[row + 1]; ++edge) {
                if (control[0][edge] == Complex(0) && control[1][edge] == Complex(0) && control[2][edge] == Complex(0)) continue;
                Complex contraction = 0;
                for (int column = 0; column < columns; ++column)
                    contraction += std::conj(adjoint[row * columns + column]) * states[indices[edge] * columns + column];
                for (int channel = 0; channel < 3; ++channel) {
                    gradient[channel] += factor * std::real(control[channel][edge] * contraction);
                    if (complex_parameters) gradient[channel + 72] -= factor * std::imag(control[channel][edge] * contraction);
                }
            }
        }
    }

    double evaluate(const double* amplitudes, int member_mask, int mode, double* gradient) const {
        int edges = indices.size();
        int record_size = (degree + 1) * size;
        std::vector<Complex> records(24 * record_size), hamiltonians(24 * edges), states(size), adjoint(size), reverse(record_size);
        bool complex_parameters = mode == 4;
        std::vector<Complex> conjugate_values(edges);
        std::fill(gradient, gradient + (complex_parameters ? 144 : 72), 0.);
        double loss = 0.;
        int members = 0;
        for (int member = 0; member < 4; ++member) {
            if (!(member_mask & (1 << member))) continue;
            ++members;
            states = initial;
            for (int step = 0; step < 24; ++step) {
                Complex* values = hamiltonians.data() + step * edges;
                for (int edge = 0; edge < edges; ++edge) {
                    values[edge] = drift[member][edge];
                    for (int channel = 0; channel < 3; ++channel) {
                        Complex amplitude(amplitudes[step * 3 + channel], complex_parameters ? amplitudes[72 + step * 3 + channel] : 0.);
                        values[edge] += amplitude * control[channel][edge];
                    }
                    values[edge] /= radius;
                }
                Complex* record = records.data() + step * record_size;
                std::copy(states.begin(), states.end(), record);
                multiply(values, record, record + size, 1., false);
                for (int order = 2; order <= degree; ++order) {
                    multiply(values, record + (order - 1) * size, record + order * size, 2., false);
                    for (int entry = 0; entry < size; ++entry)
                        record[order * size + entry] -= record[(order - 2) * size + entry];
                }
                std::fill(states.begin(), states.end(), Complex(0));
                for (int order = 0; order <= degree; ++order)
                    for (int entry = 0; entry < size; ++entry)
                        states[entry] += coefficients[order] * record[order * size + entry];
            }
            Complex trace = 0;
            for (int entry = 0; entry < size; ++entry)
                trace += std::conj(target[member][entry]) * states[entry];
            Complex factor;
            if (mode == 0) {
                loss += 1. - trace.real() / columns;
                factor = -1. / columns;
            } else if (mode == 1) {
                loss += 1. - std::abs(trace) / columns;
                factor = -trace / (std::max(std::abs(trace), 1e-30) * columns);
            } else if (mode == 2) {
                loss += 1. - std::norm(trace) / (columns * columns);
                factor = -2. * trace / double(columns * columns);
            } else if (mode == 4) {
                double norm = 0.;
                for (int entry = 0; entry < size; ++entry) norm += std::norm(states[entry]);
                loss += (norm + columns - 2. * std::abs(trace)) / (2. * columns);
                Complex phase = trace / std::max(std::abs(trace), 1e-30);
                for (int entry = 0; entry < size; ++entry)
                    adjoint[entry] = (states[entry] - phase * target[member][entry]) / double(columns);
            } else {
                constexpr double beta = 8.;
                Complex overlap[36] = {}, hermitian[36], exponential[36] = {}, term[36] = {}, temporary[36], weight[36];
                Complex phase = trace / std::max(std::abs(trace), 1e-30);
                for (int row = 0; row < 6; ++row) {
                    exponential[row * 6 + row] = 1.;
                    term[row * 6 + row] = 1.;
                    for (int column = 0; column < 6; ++column)
                        for (int entry = 0; entry < dimension; ++entry)
                            overlap[row * 6 + column] += std::conj(target[member][entry * 6 + row]) * states[entry * 6 + column];
                }
                for (int row = 0; row < 6; ++row)
                    for (int column = 0; column < 6; ++column)
                        hermitian[row * 6 + column] = -beta / 32. * (std::conj(phase) * overlap[row * 6 + column] + phase * std::conj(overlap[column * 6 + row]));
                for (int order = 1; order <= 18; ++order) {
                    small_multiply(term, hermitian, temporary);
                    for (int entry = 0; entry < 36; ++entry) {
                        term[entry] = temporary[entry] / double(order);
                        exponential[entry] += term[entry];
                    }
                }
                for (int power = 0; power < 4; ++power) {
                    small_multiply(exponential, exponential, temporary);
                    std::copy(temporary, temporary + 36, exponential);
                }
                double normalization = 0.;
                for (int row = 0; row < 6; ++row) normalization += exponential[row * 6 + row].real();
                loss += 1. + std::log(normalization / 6.) / beta;
                for (int entry = 0; entry < 36; ++entry) weight[entry] = exponential[entry] / normalization;
                Complex weighted_overlap = 0.;
                for (int row = 0; row < 6; ++row)
                    for (int column = 0; column < 6; ++column)
                        weighted_overlap += weight[column * 6 + row] * std::conj(phase) * overlap[row * 6 + column];
                Complex phase_derivative = Complex(0., -weighted_overlap.imag()) / std::conj(trace);
                for (int entry = 0; entry < dimension; ++entry)
                    for (int column = 0; column < 6; ++column) {
                        adjoint[entry * 6 + column] = phase_derivative * target[member][entry * 6 + column];
                        for (int inner = 0; inner < 6; ++inner)
                            adjoint[entry * 6 + column] -= phase * target[member][entry * 6 + inner] * weight[inner * 6 + column];
                    }
            }
            if (mode != 3 && mode != 4)
                for (int entry = 0; entry < size; ++entry)
                    adjoint[entry] = factor * target[member][entry];
            for (int step = 23; step >= 0; --step) {
                const Complex* record = records.data() + step * record_size;
                const Complex* values = hamiltonians.data() + step * edges;
                if (complex_parameters) {
                    for (int edge = 0; edge < edges; ++edge) {
                        conjugate_values[edge] = drift[member][edge];
                        for (int channel = 0; channel < 3; ++channel)
                            conjugate_values[edge] += Complex(amplitudes[step * 3 + channel], -amplitudes[72 + step * 3 + channel]) * control[channel][edge];
                        conjugate_values[edge] /= radius;
                    }
                    values = conjugate_values.data();
                }
                for (int order = 0; order <= degree; ++order)
                    for (int entry = 0; entry < size; ++entry)
                        reverse[order * size + entry] = std::conj(coefficients[order]) * adjoint[entry];
                for (int order = degree; order >= 2; --order) {
                    derivative(reverse.data() + order * size, record + (order - 1) * size, 2. / radius, gradient + step * 3, complex_parameters);
                    multiply(values, reverse.data() + order * size, reverse.data() + (order - 1) * size, 2., true);
                    for (int entry = 0; entry < size; ++entry)
                        reverse[(order - 2) * size + entry] -= reverse[order * size + entry];
                }
                derivative(reverse.data() + size, record, 1. / radius, gradient + step * 3, complex_parameters);
                multiply(values, reverse.data() + size, reverse.data(), 1., true);
                std::copy(reverse.begin(), reverse.begin() + size, adjoint.begin());
            }
        }
        for (int entry = 0; entry < (complex_parameters ? 144 : 72); ++entry) gradient[entry] /= members;
        return loss / members;
    }
};

extern "C" {
void* create_model(const Complex* drifts, const Complex* controls, const Complex* initial,
                   const Complex* targets, const Complex* coefficients, int degree, double radius) {
    return new Model(drifts, controls, initial, targets, coefficients, degree, radius);
}
double evaluate_model(void* model, const double* amplitudes, int members, int mode, double* gradient) {
    return static_cast<Model*>(model)->evaluate(amplitudes, members, mode, gradient);
}
void destroy_model(void* model) { delete static_cast<Model*>(model); }
}
