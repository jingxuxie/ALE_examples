#include <algorithm>
#include <cmath>
#include <chrono>
#include <vector>

static constexpr double pi = 3.1415926535897932384626433832795;

static double total_cost(int dimension, int rank, const double* one_body, const double* factors) {
    double value = 0.0;
    int entries = dimension * dimension;
    for (int entry = 0; entry < entries; ++entry) value += std::abs(one_body[entry]);
    for (int factor = 0; factor < rank; ++factor) {
        double weight = 0.0;
        for (int entry = 0; entry < entries; ++entry) weight += std::abs(factors[factor * entries + entry]);
        value += 0.5 * weight * weight;
    }
    return value;
}

struct Event {
    double angle, first, second;
    int kind;
    bool operator<(const Event& other) const { return angle < other.angle; }
};

static double auxiliary_pair(int dimension, int rank, double* factors, double* auxiliary, int first, int second) {
    int entries = dimension * dimension;
    double* first_factor = factors + first * entries;
    double* second_factor = factors + second * entries;
    double lower = -pi / 4.0, upper = pi / 4.0;
    double cosine = std::cos(lower + 1e-13), sine = std::sin(lower + 1e-13);
    double first_cosine = 0.0, first_sine = 0.0, second_cosine = 0.0, second_sine = 0.0;
    double first_weight = 0.0, second_weight = 0.0;
    std::vector<Event> events;
    events.reserve(entries + 1);
    for (int row = 0; row < dimension; ++row) {
        for (int column = row; column < dimension; ++column) {
            double weight = row == column ? 1.0 : 2.0;
            double first_value = first_factor[row * dimension + column];
            double second_value = second_factor[row * dimension + column];
            first_weight += weight * std::abs(first_value);
            second_weight += weight * std::abs(second_value);
            double first_sign = std::copysign(weight, cosine * first_value + sine * second_value);
            double second_sign = std::copysign(weight, -sine * first_value + cosine * second_value);
            first_cosine += first_sign * first_value;
            first_sine += first_sign * second_value;
            second_cosine += second_sign * second_value;
            second_sine -= second_sign * first_value;
            if (std::abs(first_value) + std::abs(second_value) < 1e-25) continue;
            for (int kind = 0; kind < 2; ++kind) {
                double angle = kind == 0 ? std::atan2(-first_value, second_value) : std::atan2(second_value, first_value);
                while (angle < lower) angle += pi;
                while (angle >= lower + pi) angle -= pi;
                if (angle > lower + 1e-12 && angle < upper - 1e-12) {
                    double derivative = kind == 0 ? -first_value * std::sin(angle) + second_value * std::cos(angle)
                                                 : -first_value * std::cos(angle) - second_value * std::sin(angle);
                    double delta_sign = 2.0 * std::copysign(weight, derivative);
                    events.push_back({angle, delta_sign * first_value, delta_sign * second_value, kind});
                }
            }
        }
    }
    std::sort(events.begin(), events.end());
    events.push_back({upper, 0.0, 0.0, 0});
    double original = 0.5 * (first_weight * first_weight + second_weight * second_weight);
    double best = original, best_angle = 0.0, previous = lower;
    for (const Event& event : events) {
        double constant = 0.25 * (first_cosine * first_cosine + first_sine * first_sine + second_cosine * second_cosine + second_sine * second_sine);
        double cosine_term = 0.25 * (first_cosine * first_cosine - first_sine * first_sine + second_cosine * second_cosine - second_sine * second_sine);
        double sine_term = 0.5 * (first_cosine * first_sine + second_cosine * second_sine);
        auto consider = [&](double angle) {
            double value = constant + cosine_term * std::cos(2 * angle) + sine_term * std::sin(2 * angle);
            if (value < best) { best = value; best_angle = angle; }
        };
        consider(previous);
        consider(event.angle);
        double optimum = 0.5 * std::atan2(sine_term, cosine_term) + pi / 2;
        while (optimum > upper) optimum -= pi;
        while (optimum < lower) optimum += pi;
        if (optimum > previous && optimum < event.angle) consider(optimum);
        if (event.kind == 0) {
            first_cosine += event.first;
            first_sine += event.second;
        } else {
            second_cosine += event.second;
            second_sine -= event.first;
        }
        previous = event.angle;
    }
    if (best < original - 1e-12 * std::max(original, 1.0)) {
        cosine = std::cos(best_angle);
        sine = std::sin(best_angle);
        for (int entry = 0; entry < entries; ++entry) {
            double first_value = first_factor[entry], second_value = second_factor[entry];
            first_factor[entry] = cosine * first_value + sine * second_value;
            second_factor[entry] = -sine * first_value + cosine * second_value;
        }
        for (int entry = 0; entry < rank; ++entry) {
            double first_value = auxiliary[first * rank + entry], second_value = auxiliary[second * rank + entry];
            auxiliary[first * rank + entry] = cosine * first_value + sine * second_value;
            auxiliary[second * rank + entry] = -sine * first_value + cosine * second_value;
        }
        return original - best;
    }
    return 0.0;
}

struct Curve {
    double rest, first_diagonal, second_diagonal, off_diagonal;
    double first_row[16], second_row[16];
};

static void linear_knots(std::vector<double>& knots, double cosine_term, double sine_term) {
    if (std::abs(cosine_term) + std::abs(sine_term) < 1e-20) return;
    double angle = std::atan2(-cosine_term, sine_term);
    while (angle < -pi / 4) angle += pi;
    while (angle >= 3 * pi / 4) angle -= pi;
    if (angle > -pi / 4 && angle < pi / 4) knots.push_back(angle);
}

static void quadratic_knots(std::vector<double>& knots, double constant, double cosine_term, double sine_term) {
    double radius = std::hypot(cosine_term, sine_term);
    if (radius < 1e-20 || std::abs(constant) > radius) return;
    double phase = std::atan2(sine_term, cosine_term);
    double offset = std::acos(std::max(-1.0, std::min(1.0, -constant / radius)));
    for (int direction : {-1, 1}) {
        for (int period = -1; period <= 1; ++period) {
            double angle = 0.5 * (phase + direction * offset + 2 * pi * period);
            if (angle > -pi / 4 && angle < pi / 4) knots.push_back(angle);
        }
    }
}

static double orbital_pair(int dimension, int rank, double* one_body, double* factors, double* orbital, int first, int second) {
    std::vector<Curve> curves(rank + 1);
    std::vector<double> knots;
    knots.reserve((rank + 1) * (dimension + 6) + 40);
    for (int sample = 0; sample <= 16; ++sample) knots.push_back(-pi / 4 + pi * sample / 32);
    for (int factor = 0; factor <= rank; ++factor) {
        const double* matrix = factor == 0 ? one_body : factors + (factor - 1) * dimension * dimension;
        Curve& curve = curves[factor];
        curve.rest = 0.0;
        curve.first_diagonal = matrix[first * dimension + first];
        curve.second_diagonal = matrix[second * dimension + second];
        curve.off_diagonal = matrix[first * dimension + second];
        for (int row = 0; row < dimension; ++row) {
            curve.first_row[row] = matrix[first * dimension + row];
            curve.second_row[row] = matrix[second * dimension + row];
            if (row == first || row == second) continue;
            linear_knots(knots, curve.first_row[row], curve.second_row[row]);
            linear_knots(knots, curve.second_row[row], -curve.first_row[row]);
            for (int column = 0; column < dimension; ++column) {
                if (column != first && column != second) curve.rest += std::abs(matrix[row * dimension + column]);
            }
        }
        double average = 0.5 * (curve.first_diagonal + curve.second_diagonal);
        double difference = 0.5 * (curve.first_diagonal - curve.second_diagonal);
        quadratic_knots(knots, average, difference, curve.off_diagonal);
        quadratic_knots(knots, average, -difference, -curve.off_diagonal);
        quadratic_knots(knots, 0.0, curve.off_diagonal, -difference);
    }
    auto evaluate = [&](double angle) {
        double cosine = std::cos(angle), sine = std::sin(angle);
        double cosine_double = cosine * cosine - sine * sine, sine_double = 2 * sine * cosine;
        double value = 0.0;
        for (int factor = 0; factor <= rank; ++factor) {
            const Curve& curve = curves[factor];
            double average = 0.5 * (curve.first_diagonal + curve.second_diagonal);
            double difference = 0.5 * (curve.first_diagonal - curve.second_diagonal);
            double displacement = difference * cosine_double + curve.off_diagonal * sine_double;
            double weight = curve.rest + std::abs(average + displacement) + std::abs(average - displacement)
                            + 2 * std::abs(curve.off_diagonal * cosine_double - difference * sine_double);
            for (int row = 0; row < dimension; ++row) {
                if (row == first || row == second) continue;
                weight += 2 * (std::abs(cosine * curve.first_row[row] + sine * curve.second_row[row])
                             + std::abs(-sine * curve.first_row[row] + cosine * curve.second_row[row]));
            }
            value += factor == 0 ? weight : 0.5 * weight * weight;
        }
        return value;
    };
    std::sort(knots.begin(), knots.end());
    knots.erase(std::unique(knots.begin(), knots.end(), [](double first_angle, double second_angle) {
        return std::abs(first_angle - second_angle) < 1e-13;
    }), knots.end());
    double original = evaluate(0.0), best = original, best_angle = 0.0;
    int best_index = -1;
    for (int index = 0; index < static_cast<int>(knots.size()); ++index) {
        double value = evaluate(knots[index]);
        if (value < best) { best = value; best_angle = knots[index]; best_index = index; }
    }
    if (best_index >= 0) {
        double lower = knots[std::max(0, best_index - 1)];
        double upper = knots[std::min(static_cast<int>(knots.size()) - 1, best_index + 1)];
        double left = upper - 0.6180339887498949 * (upper - lower);
        double right = lower + 0.6180339887498949 * (upper - lower);
        double left_value = evaluate(left), right_value = evaluate(right);
        for (int iteration = 0; iteration < 35 && upper - lower > 1e-12; ++iteration) {
            if (left_value < best) { best = left_value; best_angle = left; }
            if (right_value < best) { best = right_value; best_angle = right; }
            if (left_value < right_value) {
                upper = right; right = left; right_value = left_value;
                left = upper - 0.6180339887498949 * (upper - lower); left_value = evaluate(left);
            } else {
                lower = left; left = right; left_value = right_value;
                right = lower + 0.6180339887498949 * (upper - lower); right_value = evaluate(right);
            }
        }
    }
    if (best >= original - 1e-12 * std::max(original, 1.0)) return 0.0;
    double cosine = std::cos(best_angle), sine = std::sin(best_angle);
    for (int factor = 0; factor <= rank; ++factor) {
        double* matrix = factor == 0 ? one_body : factors + (factor - 1) * dimension * dimension;
        const Curve& curve = curves[factor];
        for (int row = 0; row < dimension; ++row) {
            if (row == first || row == second) continue;
            matrix[first * dimension + row] = matrix[row * dimension + first] = cosine * curve.first_row[row] + sine * curve.second_row[row];
            matrix[second * dimension + row] = matrix[row * dimension + second] = -sine * curve.first_row[row] + cosine * curve.second_row[row];
        }
        matrix[first * dimension + first] = cosine * cosine * curve.first_diagonal + sine * sine * curve.second_diagonal + 2 * sine * cosine * curve.off_diagonal;
        matrix[second * dimension + second] = sine * sine * curve.first_diagonal + cosine * cosine * curve.second_diagonal - 2 * sine * cosine * curve.off_diagonal;
        matrix[first * dimension + second] = matrix[second * dimension + first] = (cosine * cosine - sine * sine) * curve.off_diagonal
                                                                                 + sine * cosine * (curve.second_diagonal - curve.first_diagonal);
    }
    for (int row = 0; row < dimension; ++row) {
        double first_value = orbital[row * dimension + first], second_value = orbital[row * dimension + second];
        orbital[row * dimension + first] = cosine * first_value + sine * second_value;
        orbital[row * dimension + second] = -sine * first_value + cosine * second_value;
    }
    return original - best;
}

extern "C" double polish(int dimension, int rank, double* one_body, double* factors, double* orbital, double* auxiliary, int sweeps, int orbital_enabled, double seconds) {
    auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(seconds);
    double previous = total_cost(dimension, rank, one_body, factors);
    for (int sweep = 0; sweep < sweeps; ++sweep) {
        for (int first = 0; first < rank; ++first) {
            if (std::chrono::steady_clock::now() >= deadline) return total_cost(dimension, rank, one_body, factors);
            for (int second = first + 1; second < rank; ++second) auxiliary_pair(dimension, rank, factors, auxiliary, first, second);
        }
        if (orbital_enabled) {
            for (int first = 0; first < dimension; ++first) {
                if (std::chrono::steady_clock::now() >= deadline) return total_cost(dimension, rank, one_body, factors);
                for (int second = first + 1; second < dimension; ++second) orbital_pair(dimension, rank, one_body, factors, orbital, first, second);
            }
        }
        double current = total_cost(dimension, rank, one_body, factors);
        if (previous - current < 1e-10 * std::max(previous, 1.0)) return current;
        previous = current;
    }
    return previous;
}
