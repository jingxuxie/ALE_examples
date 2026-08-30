#include <cmath>
#include <cstring>
#include <vector>
#include <algorithm>
#include <queue>

static int dimension, gates, stride;
static std::vector<int> lengths, sources, destinations;
static std::vector<double> signs, initial, target;

static void rotate(double* state, int label, double angle) {
    double cosine = std::cos(angle), sine = std::sin(angle);
    int offset = label * stride;
    for (int pair = 0; pair < lengths[label]; ++pair) {
        int source = sources[offset + pair], destination = destinations[offset + pair];
        double left = state[source], right = state[destination];
        double signed_sine = signs[offset + pair] * sine;
        state[source] = cosine * left - signed_sine * right;
        state[destination] = signed_sine * left + cosine * right;
    }
}

static void generator(const double* state, int label, double* result) {
    std::fill(result, result + dimension, 0.0);
    int offset = label * stride;
    for (int pair = 0; pair < lengths[label]; ++pair) {
        int source = sources[offset + pair], destination = destinations[offset + pair];
        result[source] = -signs[offset + pair] * state[destination];
        result[destination] = signs[offset + pair] * state[source];
    }
}

extern "C" {
void setup(int dim, int count, int width, const int* lens, const int* src,
           const int* dst, const double* sig, const double* ref, const double* tar) {
    dimension = dim; gates = count; stride = width;
    lengths.assign(lens, lens + count);
    sources.assign(src, src + count * width);
    destinations.assign(dst, dst + count * width);
    signs.assign(sig, sig + count * width);
    initial.assign(ref, ref + dim); target.assign(tar, tar + dim);
}

void apply(double* state, int label, double angle) { rotate(state, label, angle); }

void forward(int count, const int* labels, const double* angles, double* output) {
    std::copy(initial.begin(), initial.end(), output);
    for (int position = 0; position < count; ++position) rotate(output, labels[position], angles[position]);
}

double fungrad(int count, const int* labels, const double* angles, double* gradient) {
    std::vector<double> history((count + 1) * dimension), adjoint(dimension), tangent(dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    double value = 0.0;
    for (int entry = 0; entry < dimension; ++entry) {
        double difference = history[count * dimension + entry] - target[entry];
        value += 0.5 * difference * difference;
        adjoint[entry] = difference;
    }
    for (int position = count - 1; position >= 0; --position) {
        generator(history.data() + (position + 1) * dimension, labels[position], tangent.data());
        double derivative = 0.0;
        for (int entry = 0; entry < dimension; ++entry) derivative += adjoint[entry] * tangent[entry];
        gradient[position] = derivative;
        rotate(adjoint.data(), labels[position], -angles[position]);
    }
    return value;
}

void residual_jac(int count, const int* labels, const double* angles, double* residual, double* jacobian) {
    std::vector<double> history((count + 1) * dimension), tangent(dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    for (int entry = 0; entry < dimension; ++entry) residual[entry] = history[count * dimension + entry] - target[entry];
    for (int position = 0; position < count; ++position) {
        generator(history.data() + (position + 1) * dimension, labels[position], tangent.data());
        for (int later = position + 1; later < count; ++later) rotate(tangent.data(), labels[later], angles[later]);
        for (int entry = 0; entry < dimension; ++entry) jacobian[entry * count + position] = tangent[entry];
    }
}

void scan(int count, const int* labels, const double* angles, int replacement, double* values, double* best_angles) {
    std::vector<double> history((count + 1) * dimension), backward((count + 1) * dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    std::copy(target.begin(), target.end(), backward.begin() + count * dimension);
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    for (int position = count - 1; position >= 0; --position) {
        double* state = backward.data() + position * dimension;
        std::copy(state + dimension, state + 2 * dimension, state);
        rotate(state, labels[position], -angles[position]);
    }
    for (int position = 0; position < count + 1 - replacement; ++position) {
        const double* left = history.data() + position * dimension;
        const double* right = backward.data() + (position + replacement) * dimension;
        double base = 0.0;
        for (int entry = 0; entry < dimension; ++entry) base += left[entry] * right[entry];
        for (int label = 0; label < gates; ++label) {
            double active = 0.0, tangent = 0.0;
            int offset = label * stride;
            for (int pair = 0; pair < lengths[label]; ++pair) {
                int source = sources[offset + pair], destination = destinations[offset + pair];
                active += left[source] * right[source] + left[destination] * right[destination];
                tangent += signs[offset + pair] * (left[source] * right[destination] - left[destination] * right[source]);
            }
            values[position * gates + label] = 1.0 - base + active - std::hypot(active, tangent);
            best_angles[position * gates + label] = std::atan2(tangent, active);
        }
    }
}

void entropy_scan(const double* state, int power, double* values, double* angles) {
    for (int label = 0; label < gates; ++label) {
        int offset = label * stride;
        double best = 0.0, best_angle = 0.0;
        for (int candidate = -1; candidate < lengths[label]; ++candidate) {
            double angle = candidate < 0 ? 0.0 : std::atan2(signs[offset + candidate] * state[destinations[offset + candidate]], state[sources[offset + candidate]]);
            double cosine = std::cos(angle), sine = std::sin(angle), value = 0.0;
            for (int pair = 0; pair < lengths[label]; ++pair) {
                double left = state[sources[offset + pair]], right = signs[offset + pair] * state[destinations[offset + pair]];
                double new_left = cosine * left + sine * right, new_right = cosine * right - sine * left;
                value += std::abs(new_left) + std::abs(new_right) - std::abs(left) - std::abs(right);
            }
            if (value < best) {best = value; best_angle = -angle;}
        }
        values[label] = best; angles[label] = best_angle;
    }
}

void insertion_tangents(int count, const int* labels, const double* angles, double* output) {
    std::vector<double> history((count + 1) * dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    for (int position = 0; position <= count; ++position) {
        for (int label = 0; label < gates; ++label) {
            double* tangent = output + (position * gates + label) * dimension;
            generator(history.data() + position * dimension, label, tangent);
            for (int later = position; later < count; ++later) rotate(tangent, labels[later], angles[later]);
        }
    }
}

double entropy_fungrad(int count, const int* labels, const double* angles, double* gradient) {
    std::vector<double> history((count + 1) * dimension), adjoint(dimension), tangent(dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    double value = 0.5;
    for (int entry = 0; entry < dimension; ++entry) {
        double amplitude = history[count * dimension + entry];
        value -= 0.5 * amplitude * amplitude * amplitude * amplitude;
        adjoint[entry] = -2 * amplitude * amplitude * amplitude;
    }
    for (int position = count - 1; position >= 0; --position) {
        generator(history.data() + (position + 1) * dimension, labels[position], tangent.data());
        double derivative = 0.0;
        for (int entry = 0; entry < dimension; ++entry) derivative += adjoint[entry] * tangent[entry];
        gradient[position] = derivative;
        rotate(adjoint.data(), labels[position], -angles[position]);
    }
    return value;
}

void fourth_scan(const double* state, double* gains, double* angles) {
    for (int label = 0; label < gates; ++label) {
        int offset = label * stride;
        double cosine_term = 0.0, sine_term = 0.0;
        for (int pair = 0; pair < lengths[label]; ++pair) {
            double left = state[sources[offset + pair]], right = signs[offset + pair] * state[destinations[offset + pair]];
            cosine_term += left * left * left * left - 6 * left * left * right * right + right * right * right * right;
            sine_term += -4 * left * right * (left * left - right * right);
        }
        gains[label] = 0.25 * (std::hypot(cosine_term,sine_term) - cosine_term);
        angles[label] = 0.25 * std::atan2(sine_term,cosine_term);
    }
}

void pair_scan_spaced(int count, const int* labels, const double* angles, int first_position,
               int last_position, int gap, int keep, int* choices, double* parameters, double* values) {
    struct Candidate {
        double value, first_angle, second_angle;
        int first_label, second_label;
        bool operator<(const Candidate& other) const { return value < other.value; }
    };
    std::vector<double> history((count + 1) * dimension), backward((count + 1) * dimension);
    std::copy(initial.begin(), initial.end(), history.begin());
    std::copy(target.begin(), target.end(), backward.begin() + count * dimension);
    for (int position = 0; position < count; ++position) {
        double* state = history.data() + (position + 1) * dimension;
        std::copy(state - dimension, state, state);
        rotate(state, labels[position], angles[position]);
    }
    for (int position = count - 1; position >= 0; --position) {
        double* state = backward.data() + position * dimension;
        std::copy(state + dimension, state + 2 * dimension, state);
        rotate(state, labels[position], -angles[position]);
    }
    std::vector<double> active(gates), tangent(gates), second_active(gates), second_tangent(gates), projected(dimension), generated(dimension);
    for (int position = first_position; position < last_position; ++position) {
        const double* left = history.data() + position * dimension;
        const double* right = backward.data() + (position + gap + 1) * dimension;
        std::vector<double> middle_left(left,left+dimension), middle_right(right,right+dimension);
        for (int middle = position+1; middle < position+gap; ++middle) rotate(middle_left.data(),labels[middle],angles[middle]);
        for (int middle = position+gap-1; middle > position; --middle) rotate(middle_right.data(),labels[middle],-angles[middle]);
        double base = 0.0;
        for (int entry = 0; entry < dimension; ++entry) base += middle_left[entry] * right[entry];
        for (int label = 0; label < gates; ++label) {
            active[label] = 0.0; tangent[label] = 0.0;
            second_active[label] = 0.0; second_tangent[label] = 0.0;
            int offset = label * stride;
            for (int pair = 0; pair < lengths[label]; ++pair) {
                int source = sources[offset + pair], destination = destinations[offset + pair];
                active[label] += left[source] * middle_right[source] + left[destination] * middle_right[destination];
                tangent[label] += signs[offset + pair] * (left[source] * middle_right[destination] - left[destination] * middle_right[source]);
                second_active[label] += middle_left[source] * right[source] + middle_left[destination] * right[destination];
                second_tangent[label] += signs[offset + pair] * (middle_left[source] * right[destination] - middle_left[destination] * right[source]);
            }
        }
        std::priority_queue<Candidate> winners;
        for (int first = 0; first < gates; ++first) {
            std::fill(projected.begin(), projected.end(), 0.0);
            generator(left,first,generated.data());
            int offset = first * stride;
            for (int pair = 0; pair < lengths[first]; ++pair) {
                projected[sources[offset + pair]] = left[sources[offset + pair]];
                projected[destinations[offset + pair]] = left[destinations[offset + pair]];
            }
            for (int middle = position+1; middle < position+gap; ++middle) {
                rotate(projected.data(),labels[middle],angles[middle]);
                rotate(generated.data(),labels[middle],angles[middle]);
            }
            for (int second = 0; second < gates; ++second) {
                if (first == labels[position] && second == labels[position + gap]) continue;
                double projection_projection = 0.0, projection_generator = 0.0;
                double generator_projection = 0.0, generator_generator = 0.0;
                int second_offset = second * stride;
                for (int pair = 0; pair < lengths[second]; ++pair) {
                    int source = sources[second_offset + pair], destination = destinations[second_offset + pair];
                    double sign = signs[second_offset + pair];
                    projection_projection += right[source] * projected[source] + right[destination] * projected[destination];
                    projection_generator += right[source] * generated[source] + right[destination] * generated[destination];
                    generator_projection += sign * (right[destination] * projected[source] - right[source] * projected[destination]);
                    generator_generator += sign * (right[destination] * generated[source] - right[source] * generated[destination]);
                }
                double coefficients[9] = {
                    base-active[first]-second_active[second]+projection_projection,
                    active[first]-projection_projection,tangent[first]-projection_generator,
                    second_active[second]-projection_projection,projection_projection,projection_generator,
                    second_tangent[second]-generator_projection,generator_projection,generator_generator
                };
                double best_overlap = -2.0, best_first_cosine = 1.0, best_first_sine = 0.0, best_second_cosine = 1.0, best_second_sine = 0.0;
                for (int start = 0; start < 4; ++start) {
                    double second_cosine = start == 0 ? 1.0 : (start == 2 ? -1.0 : 0.0);
                    double second_sine = start == 1 ? 1.0 : (start == 3 ? -1.0 : 0.0);
                    double first_cosine = 1.0, first_sine = 0.0;
                    for (int iteration = 0; iteration < 10; ++iteration) {
                        double cosine_term = coefficients[1] + coefficients[4] * second_cosine + coefficients[7] * second_sine;
                        double sine_term = coefficients[2] + coefficients[5] * second_cosine + coefficients[8] * second_sine;
                        double length = std::sqrt(cosine_term*cosine_term+sine_term*sine_term);
                        first_cosine = length > 1e-16 ? cosine_term / length : 1.0;
                        first_sine = length > 1e-16 ? sine_term / length : 0.0;
                        cosine_term = coefficients[3] + coefficients[4] * first_cosine + coefficients[5] * first_sine;
                        sine_term = coefficients[6] + coefficients[7] * first_cosine + coefficients[8] * first_sine;
                        length = std::sqrt(cosine_term*cosine_term+sine_term*sine_term);
                        second_cosine = length > 1e-16 ? cosine_term / length : 1.0;
                        second_sine = length > 1e-16 ? sine_term / length : 0.0;
                    }
                    double overlap = coefficients[0] + coefficients[1] * first_cosine + coefficients[2] * first_sine
                        + second_cosine * (coefficients[3] + coefficients[4] * first_cosine + coefficients[5] * first_sine)
                        + second_sine * (coefficients[6] + coefficients[7] * first_cosine + coefficients[8] * first_sine);
                    if (overlap > best_overlap) {
                        best_overlap = overlap; best_first_cosine = first_cosine; best_first_sine = first_sine;
                        best_second_cosine = second_cosine; best_second_sine = second_sine;
                    }
                }
                double value = 1.0-best_overlap;
                if ((int)winners.size() < keep || value < winners.top().value) {
                    if ((int)winners.size() == keep) winners.pop();
                    winners.push(Candidate{value,std::atan2(best_first_sine,best_first_cosine),std::atan2(best_second_sine,best_second_cosine),first,second});
                }
            }
        }
        for (int index = keep-1; index >= 0; --index) {
            Candidate winner = winners.top(); winners.pop();
            int output = (position-first_position)*keep+index;
            values[output] = winner.value;
            choices[output*2] = winner.first_label; choices[output*2+1] = winner.second_label;
            parameters[output*2] = winner.first_angle; parameters[output*2+1] = winner.second_angle;
        }
    }
}

void pair_scan(int count, const int* labels, const double* angles, int first_position,
               int last_position, int keep, int* choices, double* parameters, double* values) {
    pair_scan_spaced(count,labels,angles,first_position,last_position,1,keep,choices,parameters,values);
}

int support_size(int count, const int* labels) {
    std::vector<int> support(dimension);
    for (int entry = 0; entry < dimension; ++entry) support[entry] = initial[entry] != 0.0;
    for (int position = 0; position < count; ++position) {
        int label = labels[position], offset = label * stride;
        for (int pair = 0; pair < lengths[label]; ++pair) {
            int source = sources[offset+pair], destination = destinations[offset+pair];
            if (support[source] || support[destination]) support[source] = support[destination] = 1;
        }
    }
    int size = 0;
    for (int entry = 0; entry < dimension; ++entry) size += support[entry];
    return size;
}

int support_choices(double* support, int mode, int* result) {
    int count = 0, maximum = -1;
    for (int label = 0; label < gates; ++label) {
        int offset = label * stride, active = 0, growth = 0;
        for (int pair = 0; pair < lengths[label]; ++pair) {
            bool left = support[sources[offset+pair]] != 0.0, right = support[destinations[offset+pair]] != 0.0;
            active += left || right; growth += left != right;
        }
        int score = mode == 0 ? active : growth;
        if (mode == 2 && score > maximum) { maximum = score; count = 0; }
        if ((mode == 2 && score == maximum) || (mode != 2 && score > 0)) result[count++] = label;
    }
    return count;
}

void support_advance(double* support, int label) {
    int offset = label * stride;
    for (int pair = 0; pair < lengths[label]; ++pair) {
        int source = sources[offset+pair], destination = destinations[offset+pair];
        if (support[source] || support[destination]) support[source] = support[destination] = 1.0;
    }
}
}
