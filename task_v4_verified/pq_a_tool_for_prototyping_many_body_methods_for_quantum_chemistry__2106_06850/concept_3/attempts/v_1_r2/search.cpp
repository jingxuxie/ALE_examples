#include <algorithm>
#include <cmath>
#include <vector>
#include <cstring>

extern "C" {

void canonical(int orbitals, int dimension, const int* masks, const double* state, double* output) {
    std::vector<double> occupations(orbitals, 0.0);
    for (int index = 0; index < dimension; ++index)
        for (int orbital = 0; orbital < orbitals; ++orbital)
            if ((masks[index] >> orbital) & 1) occupations[orbital] += state[index] * state[index];
    std::vector<int> mapping(orbitals);
    for (int spin = 0; spin < 2; ++spin) {
        std::vector<int> order;
        for (int orbital = spin; orbital < orbitals; orbital += 2) order.push_back(orbital);
        std::stable_sort(order.begin(), order.end(), [&](int left, int right) { return occupations[left] < occupations[right]; });
        for (int position = 0; position < int(order.size()); ++position) mapping[order[position]] = 2 * position + spin;
    }
    std::vector<int> inverse(1 << orbitals);
    for (int index = 0; index < dimension; ++index) inverse[masks[index]] = index;
    for (int index = 0; index < dimension; ++index) {
        int mask = 0, parity = 0;
        for (int orbital = 0; orbital < orbitals; ++orbital) {
            if (!((masks[index] >> orbital) & 1)) continue;
            mask |= 1 << mapping[orbital];
            for (int other = 0; other < orbital; ++other)
                if (((masks[index] >> other) & 1) && mapping[other] > mapping[orbital]) parity ^= 1;
        }
        output[inverse[mask]] = (parity ? -1.0 : 1.0) * state[index];
    }
    std::vector<int> order(dimension);
    for (int index = 0; index < dimension; ++index) order[index] = index;
    std::stable_sort(order.begin(), order.end(), [&](int left, int right) { return std::abs(output[left]) > std::abs(output[right]); });
    std::vector<int> pivots(orbitals + 1, 0), phases(orbitals + 1, 0);
    for (int index : order) {
        if (std::abs(output[index]) < 1e-9) { output[index] = 0.0; continue; }
        int mask = masks[index] | (1 << orbitals);
        int phase = output[index] < 0.0;
        for (int orbital = orbitals; orbital >= 0; --orbital) {
            if (!((mask >> orbital) & 1)) continue;
            if (!pivots[orbital]) {
                pivots[orbital] = mask;
                phases[orbital] = phase;
            }
            mask ^= pivots[orbital];
            phase ^= phases[orbital];
        }
        output[index] = (phase ? -1.0 : 1.0) * std::abs(output[index]);
    }
}

int cancellations(int dimension, int labels, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, const double* state, int minimum, double* output) {
    const double pi = std::acos(-1.0);
    int support = 0;
    double norm = 0.0;
    for (int index = 0; index < dimension; ++index) {
        support += std::abs(state[index]) > 1e-9;
        norm += std::abs(state[index]);
    }
    int total = 0;
    for (int label = 0; label < labels; ++label) {
        std::vector<double> angles;
        int singles = 0;
        for (int pair = 0; pair < counts[label]; ++pair) {
            int offset = label * stride + pair;
            double left = state[sources[offset]];
            double right = signs[offset] * state[destinations[offset]];
            bool first = std::abs(left) > 1e-9;
            bool second = std::abs(right) > 1e-9;
            if (first != second) ++singles;
            if (first && second) {
                double angle = std::atan2(right, left);
                angle = std::remainder(angle, pi / 2);
                if (std::abs(angle) > 1e-8) angles.push_back(angle);
            }
        }
        std::sort(angles.begin(), angles.end());
        for (size_t start = 0; start < angles.size();) {
            size_t end = start + 1;
            while (end < angles.size() && angles[end] - angles[start] < 2e-8) ++end;
            if (int(end - start) - singles >= minimum) {
                double angle = 0.0;
                for (size_t index = start; index < end; ++index) angle += angles[index];
                angle /= end - start;
                for (int quadrant = 0; quadrant < 4; ++quadrant) {
                    double theta = std::remainder(angle + quadrant * pi / 2, 2 * pi);
                    double cosine = std::cos(theta), sine = std::sin(theta);
                    int remaining = support;
                    double trial_norm = norm;
                    for (int pair = 0; pair < counts[label]; ++pair) {
                        int offset = label * stride + pair;
                        double left = state[sources[offset]];
                        double right = state[destinations[offset]];
                        double new_left = cosine * left + signs[offset] * sine * right;
                        double new_right = cosine * right - signs[offset] * sine * left;
                        remaining += (std::abs(new_left) > 1e-9) + (std::abs(new_right) > 1e-9) - (std::abs(left) > 1e-9) - (std::abs(right) > 1e-9);
                        trial_norm += std::abs(new_left) + std::abs(new_right) - std::abs(left) - std::abs(right);
                    }
                    if (support - remaining >= minimum) {
                        output[total * 4] = label;
                        output[total * 4 + 1] = theta;
                        output[total * 4 + 2] = remaining;
                        output[total * 4 + 3] = trial_norm;
                        ++total;
                    }
                }
            }
            start = end;
        }
    }
    return total;
}

void rotate(int dimension, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, double* state, int label, double theta) {
    double cosine = std::cos(theta), sine = std::sin(theta);
    for (int pair = 0; pair < counts[label]; ++pair) {
        int offset = label * stride + pair;
        int source = sources[offset], destination = destinations[offset];
        double left = state[source], right = state[destination];
        state[source] = cosine * left - signs[offset] * sine * right;
        state[destination] = cosine * right + signs[offset] * sine * left;
    }
}

double objective(int dimension, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, const double* reference, const double* target, int length, const int* labels, const double* angles, double* gradient, double* output) {
    std::vector<double> history((length + 1) * dimension);
    std::memcpy(history.data(), reference, dimension * sizeof(double));
    for (int position = 0; position < length; ++position) {
        double* next = history.data() + (position + 1) * dimension;
        std::memcpy(next, history.data() + position * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, next, labels[position], angles[position]);
    }
    double overlap = 0.0;
    for (int index = 0; index < dimension; ++index) overlap += target[index] * history[length * dimension + index];
    std::memcpy(output, history.data() + length * dimension, dimension * sizeof(double));
    std::vector<double> adjoint(target, target + dimension);
    for (int position = length - 1; position >= 0; --position) {
        int label = labels[position];
        const double* current = history.data() + (position + 1) * dimension;
        double derivative = 0.0;
        for (int pair = 0; pair < counts[label]; ++pair) {
            int offset = label * stride + pair;
            int source = sources[offset], destination = destinations[offset];
            derivative += signs[offset] * (adjoint[destination] * current[source] - adjoint[source] * current[destination]);
        }
        gradient[position] = -2.0 * overlap * derivative;
        rotate(dimension, stride, sources, destinations, signs, counts, adjoint.data(), label, -angles[position]);
    }
    return 1.0 - overlap * overlap;
}

void circuit_jacobian(int dimension, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, const double* reference, int length, const int* labels, const double* angles, double* output, double* jacobian) {
    std::vector<double> history((length + 1) * dimension);
    std::memcpy(history.data(), reference, dimension * sizeof(double));
    for (int position = 0; position < length; ++position) {
        double* next = history.data() + (position + 1) * dimension;
        std::memcpy(next, history.data() + position * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, next, labels[position], angles[position]);
    }
    std::memcpy(output, history.data() + length * dimension, dimension * sizeof(double));
    for (int position = 0; position < length; ++position) {
        std::vector<double> derivative(dimension, 0.0);
        int label = labels[position];
        const double* current = history.data() + (position + 1) * dimension;
        for (int pair = 0; pair < counts[label]; ++pair) {
            int offset = label * stride + pair;
            int source = sources[offset], destination = destinations[offset];
            derivative[source] = -signs[offset] * current[destination];
            derivative[destination] = signs[offset] * current[source];
        }
        for (int later = position + 1; later < length; ++later)
            rotate(dimension, stride, sources, destinations, signs, counts, derivative.data(), labels[later], angles[later]);
        for (int index = 0; index < dimension; ++index) jacobian[index * length + position] = derivative[index];
    }
}

void replacements(int dimension, int label_count, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, const double* reference, const double* target, int length, const int* labels, const double* angles, double* output) {
    std::vector<double> history((length + 1) * dimension), adjoints((length + 1) * dimension);
    std::memcpy(history.data(), reference, dimension * sizeof(double));
    std::memcpy(adjoints.data() + length * dimension, target, dimension * sizeof(double));
    for (int position = 0; position < length; ++position) {
        double* next = history.data() + (position + 1) * dimension;
        std::memcpy(next, history.data() + position * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, next, labels[position], angles[position]);
    }
    for (int position = length - 1; position >= 0; --position) {
        double* previous = adjoints.data() + position * dimension;
        std::memcpy(previous, adjoints.data() + (position + 1) * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, previous, labels[position], -angles[position]);
    }
    for (int position = 0; position < length; ++position) {
        const double* state = history.data() + position * dimension;
        const double* target_here = adjoints.data() + (position + 1) * dimension;
        double overlap = 0.0;
        for (int index = 0; index < dimension; ++index) overlap += state[index] * target_here[index];
        for (int label = 0; label < label_count; ++label) {
            double active = 0.0, tangent = 0.0;
            for (int pair = 0; pair < counts[label]; ++pair) {
                int offset = label * stride + pair;
                int source = sources[offset], destination = destinations[offset];
                active += state[source] * target_here[source] + state[destination] * target_here[destination];
                tangent += signs[offset] * (state[source] * target_here[destination] - state[destination] * target_here[source]);
            }
            double constant = overlap - active;
            double magnitude = std::abs(constant) + std::hypot(active, tangent);
            int offset = 2 * (position * label_count + label);
            output[offset] = 1.0 - magnitude * magnitude;
            output[offset + 1] = std::atan2(tangent, active) + (constant < 0.0 ? std::acos(-1.0) : 0.0);
        }
    }
}

void insertions(int dimension, int label_count, int stride, const int* sources, const int* destinations, const double* signs, const int* counts, const double* reference, const double* target, int length, const int* labels, const double* angles, double* output) {
    std::vector<double> history((length + 1) * dimension), adjoints((length + 1) * dimension);
    std::memcpy(history.data(), reference, dimension * sizeof(double));
    std::memcpy(adjoints.data() + length * dimension, target, dimension * sizeof(double));
    for (int position = 0; position < length; ++position) {
        double* next = history.data() + (position + 1) * dimension;
        std::memcpy(next, history.data() + position * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, next, labels[position], angles[position]);
    }
    for (int position = length - 1; position >= 0; --position) {
        double* previous = adjoints.data() + position * dimension;
        std::memcpy(previous, adjoints.data() + (position + 1) * dimension, dimension * sizeof(double));
        rotate(dimension, stride, sources, destinations, signs, counts, previous, labels[position], -angles[position]);
    }
    for (int position = 0; position <= length; ++position) {
        const double* state = history.data() + position * dimension;
        const double* target_here = adjoints.data() + position * dimension;
        double overlap = 0.0;
        for (int index = 0; index < dimension; ++index) overlap += state[index] * target_here[index];
        for (int label = 0; label < label_count; ++label) {
            double active = 0.0, tangent = 0.0;
            for (int pair = 0; pair < counts[label]; ++pair) {
                int offset = label * stride + pair;
                int source = sources[offset], destination = destinations[offset];
                active += state[source] * target_here[source] + state[destination] * target_here[destination];
                tangent += signs[offset] * (state[source] * target_here[destination] - state[destination] * target_here[source]);
            }
            double constant = overlap - active;
            double magnitude = std::abs(constant) + std::hypot(active, tangent);
            int offset = 2 * (position * label_count + label);
            output[offset] = 1.0 - magnitude * magnitude;
            output[offset + 1] = std::atan2(tangent, active) + (constant < 0.0 ? std::acos(-1.0) : 0.0);
        }
    }
}

}
