#include <cmath>
#include <vector>
#include <algorithm>
#include <cstring>

static int dimension;
static int count;
static std::vector<int> starts, sources, destinations;
static std::vector<double> signs;
static std::vector<int> matrix_indices;
static std::vector<double> matrix_signs;

extern "C" void initialize(int dim, int gates, int *offsets, int *source, int *destination, double *sign) {
    dimension = dim;
    count = gates;
    starts.assign(offsets, offsets + gates + 1);
    sources.assign(source, source + offsets[gates]);
    destinations.assign(destination, destination + offsets[gates]);
    signs.assign(sign, sign + offsets[gates]);
}

static void rotate(double *state, int label, double angle) {
    double cosine = std::cos(angle), sine = std::sin(angle);
    for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
        int source = sources[pair], destination = destinations[pair];
        double first = state[source], second = state[destination];
        state[source] = cosine * first - signs[pair] * sine * second;
        state[destination] = signs[pair] * sine * first + cosine * second;
    }
}

static double dot(const double *first, const double *second) {
    double result = 0;
    for (int index = 0; index < dimension; ++index) result += first[index] * second[index];
    return result;
}

extern "C" void sparse_options(double *state, double *gains, double *angles) {
    for (int label = 0; label < count; ++label) {
        double cosine_coefficient = 0, sine_coefficient = 0;
        for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
            double first = state[sources[pair]], second = signs[pair] * state[destinations[pair]];
            double first_squared = first * first, second_squared = second * second;
            cosine_coefficient += (first_squared * first_squared + second_squared * second_squared - 6 * first_squared * second_squared) * 0.25;
            sine_coefficient += first * second * (second_squared - first_squared);
        }
        gains[label] = std::hypot(cosine_coefficient, sine_coefficient) - cosine_coefficient;
        angles[label] = std::atan2(sine_coefficient, cosine_coefficient) * 0.25;
    }
}

extern "C" void state_jac(int length, int *labels, double *angles, double *initial, double *state, double *jacobian) {
    std::copy(initial, initial + dimension, state);
    std::fill(jacobian, jacobian + dimension * length, 0.0);
    for (int position = 0; position < length; ++position) {
        int label = labels[position];
        rotate(state, label, angles[position]);
        for (int previous = 0; previous < position; ++previous) rotate(jacobian + previous * dimension, label, angles[position]);
        double *derivative = jacobian + position * dimension;
        for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
            derivative[sources[pair]] = -signs[pair] * state[destinations[pair]];
            derivative[destinations[pair]] = signs[pair] * state[sources[pair]];
        }
    }
}

extern "C" double loss_grad(int length, int *labels, double *angles, double *initial, double *target, double *gradient) {
    std::vector<double> history((length + 1) * dimension), adjoint(target, target + dimension);
    std::copy(initial, initial + dimension, history.data());
    for (int position = 0; position < length; ++position) {
        std::copy(history.data() + position * dimension, history.data() + (position + 1) * dimension, history.data() + (position + 1) * dimension);
        rotate(history.data() + (position + 1) * dimension, labels[position], angles[position]);
    }
    double overlap = dot(target, history.data() + length * dimension);
    for (int position = length - 1; position >= 0; --position) {
        int label = labels[position];
        const double *state = history.data() + (position + 1) * dimension;
        double value = 0;
        for (int pair = starts[label]; pair < starts[label + 1]; ++pair) value += signs[pair] * (adjoint[destinations[pair]] * state[sources[pair]] - adjoint[sources[pair]] * state[destinations[pair]]);
        gradient[position] = -value;
        rotate(adjoint.data(), label, -angles[position]);
    }
    return 1.0 - overlap;
}

extern "C" void candidates(int length, int *labels, double *angles, double *initial, double *target, int replacement, double *values, double *optimal) {
    std::vector<double> history((length + 1) * dimension), adjoints((length + 1) * dimension);
    std::copy(initial, initial + dimension, history.data());
    std::copy(target, target + dimension, adjoints.data() + length * dimension);
    for (int position = 0; position < length; ++position) {
        std::copy(history.data() + position * dimension, history.data() + (position + 1) * dimension, history.data() + (position + 1) * dimension);
        rotate(history.data() + (position + 1) * dimension, labels[position], angles[position]);
    }
    for (int position = length - 1; position >= 0; --position) {
        std::copy(adjoints.data() + (position + 1) * dimension, adjoints.data() + (position + 2) * dimension, adjoints.data() + position * dimension);
        rotate(adjoints.data() + position * dimension, labels[position], -angles[position]);
    }
    for (int position = 0; position <= length - replacement; ++position) {
        const double *state = history.data() + position * dimension;
        const double *adjoint = adjoints.data() + (position + replacement) * dimension;
        double overlap = dot(state, adjoint);
        for (int label = 0; label < count; ++label) {
            double active = 0, tangent = 0;
            for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
                int source = sources[pair], destination = destinations[pair];
                active += state[source] * adjoint[source] + state[destination] * adjoint[destination];
                tangent += signs[pair] * (state[source] * adjoint[destination] - state[destination] * adjoint[source]);
            }
            values[position * count + label] = overlap - active + std::hypot(active, tangent);
            optimal[position * count + label] = std::atan2(tangent, active);
        }
    }
}

extern "C" void projected_options(int length, int *labels, double *angles, double *initial, double *residual, int rank, double *basis, double *values, double *optimal) {
    std::vector<double> history((length + 1) * dimension), adjoint(residual, residual + dimension), orthogonal(basis, basis + rank * dimension);
    std::copy(initial, initial + dimension, history.data());
    for (int position = 0; position < length; ++position) {
        std::copy(history.data() + position * dimension, history.data() + (position + 1) * dimension, history.data() + (position + 1) * dimension);
        rotate(history.data() + (position + 1) * dimension, labels[position], angles[position]);
    }
    for (int position = length; position >= 0; --position) {
        const double *state = history.data() + position * dimension;
        for (int label = 0; label < count; ++label) {
            double tangent = 0, norm = 0;
            for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
                int source = sources[pair], destination = destinations[pair];
                tangent += signs[pair] * (state[source] * adjoint[destination] - state[destination] * adjoint[source]);
                norm += state[source] * state[source] + state[destination] * state[destination];
            }
            for (int column = 0; column < rank; ++column) {
                const double *vector = orthogonal.data() + column * dimension;
                double overlap = 0;
                for (int pair = starts[label]; pair < starts[label + 1]; ++pair) overlap += signs[pair] * (state[sources[pair]] * vector[destinations[pair]] - state[destinations[pair]] * vector[sources[pair]]);
                norm -= overlap * overlap;
            }
            norm = std::max(norm, 1e-10);
            double angle = std::max(-0.8, std::min(0.8, tangent / norm));
            values[position * count + label] = 2 * angle * tangent - angle * angle * norm;
            optimal[position * count + label] = angle;
        }
        if (position > 0) {
            rotate(adjoint.data(), labels[position - 1], -angles[position - 1]);
            for (int column = 0; column < rank; ++column) rotate(orthogonal.data() + column * dimension, labels[position - 1], -angles[position - 1]);
        }
    }
}

extern "C" double mixture(int length, double *parameters, double *initial, double *target, double penalty, double *gradient, double *metrics) {
    int total = length * count;
    std::vector<double> history((length + 1) * dimension), probabilities(total), cosines(total), sines(total), adjoint(dimension), previous(dimension), deltas(count);
    std::copy(initial, initial + dimension, history.data());
    for (int position = 0; position < length; ++position) {
        double maximum = *std::max_element(parameters + position * count, parameters + (position + 1) * count), normalizer = 0;
        for (int label = 0; label < count; ++label) {
            int index = position * count + label;
            probabilities[index] = std::exp(parameters[index] - maximum);
            normalizer += probabilities[index];
            cosines[index] = std::cos(parameters[total + index]);
            sines[index] = std::sin(parameters[total + index]);
        }
        const double *state = history.data() + position * dimension;
        double *next = history.data() + (position + 1) * dimension;
        std::copy(state, state + dimension, next);
        for (int label = 0; label < count; ++label) {
            int index = position * count + label;
            probabilities[index] /= normalizer;
            double cosine = probabilities[index] * (cosines[index] - 1), sine = probabilities[index] * sines[index];
            for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
                int source = sources[pair], destination = destinations[pair];
                next[source] += cosine * state[source] - signs[pair] * sine * state[destination];
                next[destination] += signs[pair] * sine * state[source] + cosine * state[destination];
            }
        }
    }
    const double *final = history.data() + length * dimension;
    double norm = std::max(dot(final, final), 1e-300), root = std::sqrt(norm), overlap = dot(target, final);
    double loss = 1 - overlap / root - penalty * std::log(norm);
    metrics[0] = overlap / root;
    metrics[1] = norm;
    for (int index = 0; index < dimension; ++index) adjoint[index] = -target[index] / root + (overlap / (norm * root) - 2 * penalty / norm) * final[index];
    for (int position = length - 1; position >= 0; --position) {
        const double *state = history.data() + position * dimension;
        std::copy(adjoint.begin(), adjoint.end(), previous.begin());
        double average = 0;
        for (int label = 0; label < count; ++label) {
            int index = position * count + label;
            double active = 0, tangent = 0, cosine = cosines[index], sine = sines[index], probability = probabilities[index];
            for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
                int source = sources[pair], destination = destinations[pair];
                active += state[source] * adjoint[source] + state[destination] * adjoint[destination];
                tangent += signs[pair] * (state[source] * adjoint[destination] - state[destination] * adjoint[source]);
                previous[source] += probability * ((cosine - 1) * adjoint[source] + signs[pair] * sine * adjoint[destination]);
                previous[destination] += probability * (-signs[pair] * sine * adjoint[source] + (cosine - 1) * adjoint[destination]);
            }
            deltas[label] = (cosine - 1) * active + sine * tangent;
            average += probability * deltas[label];
            gradient[total + index] = probability * (-sine * active + cosine * tangent);
        }
        for (int label = 0; label < count; ++label) {
            int index = position * count + label;
            gradient[index] = probabilities[index] * (deltas[label] - average);
        }
        adjoint.swap(previous);
    }
    return loss;
}

extern "C" void support_batch(int batches, int length, int *labels, int reference, int *sizes) {
    std::vector<unsigned char> state(dimension);
    for (int batch = 0; batch < batches; ++batch) {
        std::fill(state.begin(), state.end(), 0);
        state[reference] = 1;
        for (int position = 0; position < length; ++position) {
            int label = labels[batch * length + position];
            for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
                unsigned char active = state[sources[pair]] | state[destinations[pair]];
                state[sources[pair]] = active;
                state[destinations[pair]] = active;
            }
        }
        sizes[batch] = 0;
        for (int index = 0; index < dimension; ++index) sizes[batch] += state[index];
    }
}

extern "C" void batch_states(int batches, int length, int *labels, double *angles, double *initial, double *output) {
    for (int batch = 0; batch < batches; ++batch) {
        double *state = output + batch * dimension;
        std::copy(initial, initial + dimension, state);
        for (int position = 0; position < length; ++position) rotate(state, labels[batch * length + position], angles[batch * length + position]);
    }
}

extern "C" void set_schmidt(int *indices, double *phases) {
    matrix_indices.assign(indices, indices + dimension);
    matrix_signs.assign(phases, phases + dimension);
}

static double purity(const double *state) {
    double matrix[100], result = 0;
    for (int index = 0; index < dimension; ++index) matrix[matrix_indices[index]] = matrix_signs[index] * state[index];
    for (int first = 0; first < 10; ++first) {
        for (int second = 0; second <= first; ++second) {
            double entry = 0;
            for (int column = 0; column < 10; ++column) entry += matrix[10 * first + column] * matrix[10 * second + column];
            result += entry * entry * (first == second ? 1 : 2);
        }
    }
    return result;
}

extern "C" void purity_options(double *state, double *values, double *angles) {
    std::vector<double> changed(dimension);
    double samples[9], cosine_coefficients[5], sine_coefficients[5];
    const double pi = std::acos(-1.0);
    for (int label = 0; label < count; ++label) {
        for (int sample = 0; sample < 9; ++sample) {
            std::copy(state, state + dimension, changed.begin());
            rotate(changed.data(), label, 2 * pi * sample / 9);
            samples[sample] = purity(changed.data());
        }
        for (int harmonic = 0; harmonic < 5; ++harmonic) {
            cosine_coefficients[harmonic] = 0;
            sine_coefficients[harmonic] = 0;
            for (int sample = 0; sample < 9; ++sample) {
                cosine_coefficients[harmonic] += samples[sample] * std::cos(2 * pi * harmonic * sample / 9) * (harmonic == 0 ? 1.0 : 2.0) / 9;
                sine_coefficients[harmonic] += samples[sample] * std::sin(2 * pi * harmonic * sample / 9) * 2.0 / 9;
            }
        }
        double best = -1, best_angle = 0;
        for (int sample = 0; sample < 64; ++sample) {
            double angle = 2 * pi * sample / 64, value = cosine_coefficients[0];
            for (int harmonic = 1; harmonic < 5; ++harmonic) value += cosine_coefficients[harmonic] * std::cos(harmonic * angle) + sine_coefficients[harmonic] * std::sin(harmonic * angle);
            if (value > best) { best = value; best_angle = angle; }
        }
        for (int iteration = 0; iteration < 8; ++iteration) {
            double derivative = 0, curvature = 0;
            for (int harmonic = 1; harmonic < 5; ++harmonic) {
                double cosine = std::cos(harmonic * best_angle), sine = std::sin(harmonic * best_angle);
                derivative += harmonic * (-cosine_coefficients[harmonic] * sine + sine_coefficients[harmonic] * cosine);
                curvature -= harmonic * harmonic * (cosine_coefficients[harmonic] * cosine + sine_coefficients[harmonic] * sine);
            }
            if (curvature >= -1e-15) break;
            best_angle -= std::max(-0.1, std::min(0.1, derivative / curvature));
        }
        std::copy(state, state + dimension, changed.begin());
        rotate(changed.data(), label, best_angle);
        values[label] = purity(changed.data());
        angles[label] = std::remainder(best_angle, 2 * pi);
    }
}

extern "C" void block_bases(int length, int *labels, double *angles, double *initial, double *target, int first, int second, double *left, double *right) {
    std::vector<double> state(initial, initial + dimension), adjoint(target, target + dimension);
    for (int position = 0; position < first; ++position) rotate(state.data(), labels[position], angles[position]);
    for (int position = length - 1; position > second; --position) rotate(adjoint.data(), labels[position], -angles[position]);
    std::fill(left, left + count * 3 * dimension, 0.0);
    std::fill(right, right + count * 3 * dimension, 0.0);
    for (int label = 0; label < count; ++label) {
        double *left_inactive = left + label * 3 * dimension, *left_active = left_inactive + dimension, *left_generator = left_active + dimension;
        double *right_inactive = right + label * 3 * dimension, *right_active = right_inactive + dimension, *right_generator = right_active + dimension;
        std::copy(state.begin(), state.end(), left_inactive);
        std::copy(adjoint.begin(), adjoint.end(), right_inactive);
        for (int pair = starts[label]; pair < starts[label + 1]; ++pair) {
            int source = sources[pair], destination = destinations[pair];
            left_inactive[source] = left_inactive[destination] = 0;
            right_inactive[source] = right_inactive[destination] = 0;
            left_active[source] = state[source]; left_active[destination] = state[destination];
            right_active[source] = adjoint[source]; right_active[destination] = adjoint[destination];
            left_generator[source] = -signs[pair] * state[destination]; left_generator[destination] = signs[pair] * state[source];
            right_generator[source] = signs[pair] * adjoint[destination]; right_generator[destination] = -signs[pair] * adjoint[source];
        }
        for (int position = first + 1; position < second; ++position) {
            rotate(left_inactive, labels[position], angles[position]);
            rotate(left_active, labels[position], angles[position]);
            rotate(left_generator, labels[position], angles[position]);
        }
    }
}

static void block_maxima_impl(double *matrix, double *values, double *first_angles, double *second_angles, int initializations, int iterations) {
    int stride = 3 * count;
    const double pi = std::acos(-1.0);
    for (int first = 0; first < count; ++first) {
        for (int second = 0; second < count; ++second) {
            const double *start = matrix + 3 * first * stride + 3 * second;
            double constant = start[0], first_cosine = start[stride], first_sine = start[2 * stride], second_cosine = start[1], second_sine = start[2];
            double cosine_cosine = start[stride + 1], cosine_sine = start[stride + 2], sine_cosine = start[2 * stride + 1], sine_sine = start[2 * stride + 2];
            double best = -1e100, best_first_cosine = 1, best_first_sine = 0, best_second_cosine = 1, best_second_sine = 0;
            for (int initial = 0; initial < initializations; ++initial) {
                double second_real = std::cos(2 * pi * initial / initializations), second_imaginary = std::sin(2 * pi * initial / initializations), first_real = 1, first_imaginary = 0;
                for (int iteration = 0; iteration < iterations; ++iteration) {
                    double real = first_cosine + cosine_cosine * second_real + cosine_sine * second_imaginary;
                    double imaginary = first_sine + sine_cosine * second_real + sine_sine * second_imaginary;
                    double norm = std::sqrt(real * real + imaginary * imaginary) + 1e-300;
                    first_real = real / norm; first_imaginary = imaginary / norm;
                    real = second_cosine + cosine_cosine * first_real + sine_cosine * first_imaginary;
                    imaginary = second_sine + cosine_sine * first_real + sine_sine * first_imaginary;
                    norm = std::sqrt(real * real + imaginary * imaginary) + 1e-300;
                    second_real = real / norm; second_imaginary = imaginary / norm;
                }
                double value = constant + first_cosine * first_real + first_sine * first_imaginary + second_cosine * second_real + second_sine * second_imaginary + cosine_cosine * first_real * second_real + cosine_sine * first_real * second_imaginary + sine_cosine * first_imaginary * second_real + sine_sine * first_imaginary * second_imaginary;
                if (value > best) {
                    best = value;
                    best_first_cosine = first_real; best_first_sine = first_imaginary;
                    best_second_cosine = second_real; best_second_sine = second_imaginary;
                }
            }
            values[first * count + second] = best;
            first_angles[first * count + second] = std::atan2(best_first_sine, best_first_cosine);
            second_angles[first * count + second] = std::atan2(best_second_sine, best_second_cosine);
        }
    }
}

extern "C" void block_maxima(double *matrix, double *values, double *first_angles, double *second_angles) {
    block_maxima_impl(matrix, values, first_angles, second_angles, 6, 18);
}

extern "C" void block_maxima_fast(double *matrix, double *values, double *first_angles, double *second_angles) {
    block_maxima_impl(matrix, values, first_angles, second_angles, 2, 6);
}
