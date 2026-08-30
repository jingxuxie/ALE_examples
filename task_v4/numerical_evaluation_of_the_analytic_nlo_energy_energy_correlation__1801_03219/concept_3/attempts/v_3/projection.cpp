#include <algorithm>
#include <cmath>
#include <vector>

extern "C" void sparse_project(const double* values, double* result, int size, int occupied_target, double upper) {
    std::vector<double> weights(size), amplitudes(size), dynamic(size + 2);
    for (int index = 0; index < size; ++index) amplitudes[index] = std::clamp(values[index], 0.0, upper);
    auto evaluate = [&](double penalty) {
        std::fill(result, result + size, 0.0);
        for (int index = 0; index < size; ++index)
            weights[index] = std::max(0.0, amplitudes[index] * (2 * values[index] - amplitudes[index]) - penalty);
        auto score = [&](int begin, int end) {
            dynamic[begin] = dynamic[begin + 1] = 0.0;
            for (int index = begin; index < end; ++index)
                dynamic[index + 2] = std::max(dynamic[index + 1], dynamic[index] + weights[index]);
            return dynamic[end + 1];
        };
        double first_absent = score(1, size);
        double first_present = weights[0] + score(2, size - 1);
        int begin, end, occupied = 0;
        if (first_present > first_absent) {
            result[0] = amplitudes[0];
            occupied = 1;
            begin = 2;
            end = size - 1;
        } else {
            begin = 1;
            end = size;
            score(begin, end);
        }
        for (int index = end - 1; index >= begin;) {
            if (dynamic[index] + weights[index] > dynamic[index + 1]) {
                result[index] = amplitudes[index];
                ++occupied;
                index -= 2;
            } else --index;
        }
        return occupied;
    };
    double lower = 0, higher = 8;
    for (int iteration = 0; iteration < 18; ++iteration) {
        double penalty = 0.5 * (lower + higher);
        int count = evaluate(penalty);
        if (count == occupied_target) break;
        if (count > occupied_target) lower = penalty;
        else higher = penalty;
    }
}

extern "C" void project(const double* values, double* result, int size, int mode, double shift) {
    std::vector<double> weights(size), dynamic(size + 2);
    std::vector<int> labels(size), ordering(size);
    std::fill(result, result + size, 0.0);
    for (int index = 0; index < size; ++index) {
        double value = values[index] - shift;
        labels[index] = value > 1.5 ? 2 : 1;
        weights[index] = std::max(0.0, labels[index] * (2.0 * value - labels[index]));
        ordering[index] = index;
    }
    if (mode == 3 || mode == 4) {
        auto evaluate = [&](double occupied_penalty, double double_penalty) {
            std::fill(result, result + size, 0.0);
            for (int index = 0; index < size; ++index) {
                double single = 2 * values[index] - 1 - occupied_penalty;
                double twice = 4 * values[index] - 4 - occupied_penalty - double_penalty;
                labels[index] = twice > single ? 2 : 1;
                weights[index] = std::max(0.0, std::max(single, twice));
            }
            auto score = [&](int begin, int end) {
                dynamic[begin] = dynamic[begin + 1] = 0.0;
                for (int index = begin; index < end; ++index)
                    dynamic[index + 2] = std::max(dynamic[index + 1], dynamic[index] + weights[index]);
                return dynamic[end + 1];
            };
            double first_absent = score(1, size);
            double first_present = weights[0] + score(2, size - 1);
            int begin, end, occupied = 0, doubles = 0;
            if (first_present > first_absent) {
                result[0] = labels[0];
                occupied = 1;
                doubles = labels[0] == 2;
                begin = 2;
                end = size - 1;
            } else {
                begin = 1;
                end = size;
                score(begin, end);
            }
            for (int index = end - 1; index >= begin;) {
                if (dynamic[index] + weights[index] > dynamic[index + 1]) {
                    result[index] = labels[index];
                    ++occupied;
                    doubles += labels[index] == 2;
                    index -= 2;
                } else --index;
            }
            return std::pair<int, int>(occupied, doubles);
        };
        static double penalty = 0.0, double_penalty = -0.5;
        double best_error = 1e20, best_penalty = penalty, best_double_penalty = double_penalty;
        for (int iteration = 0; iteration < 8; ++iteration) {
            auto count = evaluate(penalty, double_penalty);
            double occupied_error = count.first - 3 * size / 16;
            double double_error = count.second - size / 16;
            double error = occupied_error * occupied_error + double_error * double_error;
            if (error < best_error) {
                best_error = error;
                best_penalty = penalty;
                best_double_penalty = double_penalty;
            }
            if (error < 2) break;
            auto shifted_occupied = evaluate(penalty + 0.04, double_penalty);
            auto shifted_double = evaluate(penalty, double_penalty + 0.04);
            double jacobian00 = std::min(-10.0, (shifted_occupied.first - count.first) / 0.04);
            double jacobian10 = (shifted_occupied.second - count.second) / 0.04;
            double jacobian01 = (shifted_double.first - count.first) / 0.04;
            double jacobian11 = std::min(-10.0, (shifted_double.second - count.second) / 0.04);
            double determinant = jacobian00 * jacobian11 - jacobian01 * jacobian10;
            double delta_occupied = occupied_error / jacobian00;
            double delta_double = double_error / jacobian11;
            if (determinant > 100) {
                delta_occupied = (jacobian11 * occupied_error - jacobian01 * double_error) / determinant;
                delta_double = (jacobian00 * double_error - jacobian10 * occupied_error) / determinant;
            }
            penalty -= std::clamp(delta_occupied, -0.4, 0.4);
            double_penalty -= std::clamp(delta_double, -0.4, 0.4);
        }
        penalty = best_penalty;
        double_penalty = best_double_penalty;
        auto count = evaluate(penalty, double_penalty);
        if (mode == 4) return;
        std::sort(ordering.begin(), ordering.end(), [&](int left, int right) { return values[left] > values[right]; });
        int occupied = count.first;
        for (int rank = size - 1; rank >= 0 && occupied > 3 * size / 16; --rank) {
            int index = ordering[rank];
            if (result[index]) { result[index] = 0; --occupied; }
        }
        for (int index : ordering) {
            if (occupied >= 3 * size / 16) break;
            if (!result[index] && !result[(index + 1) % size] && !result[(index + size - 1) % size]) {
                result[index] = 1;
                ++occupied;
            }
        }
        int doubles = 0;
        for (int index : ordering) if (result[index]) result[index] = ++doubles <= size / 16 ? 2 : 1;
        return;
    }
    if (mode == 2) {
        auto compare = [&](int left, int right) { return values[left] > values[right]; };
        std::nth_element(ordering.begin(), ordering.begin() + 3 * size / 16, ordering.end(), compare);
        std::nth_element(ordering.begin(), ordering.begin() + size / 16, ordering.begin() + 3 * size / 16, compare);
        for (int rank = 0; rank < 3 * size / 16; ++rank) result[ordering[rank]] = rank < size / 16 ? 2 : 1;
        return;
    }
    if (mode == 1 || mode == 5 || mode == 6 || mode == 7) {
        std::sort(ordering.begin(), ordering.end(), [&](int left, int right) { return values[left] > values[right]; });
        int count = 0;
        for (int index : ordering) {
            if ((mode == 1 || mode == 5 || mode == 7) && (result[(index + 1) % size] || result[(index + size - 1) % size])) continue;
            result[index] = mode >= 5 ? std::max(0.0, values[index]) : (count < size / 16 ? 2.0 : 1.0);
            if (mode == 7) result[index] = std::min(2.0, result[index]);
            if (++count == 3 * size / 16) break;
        }
        return;
    }
    auto score = [&](int begin, int end) {
        dynamic[begin] = dynamic[begin + 1] = 0.0;
        for (int index = begin; index < end; ++index)
            dynamic[index + 2] = std::max(dynamic[index + 1], dynamic[index] + weights[index]);
        return dynamic[end + 1];
    };
    double first_absent = score(1, size);
    double first_present = weights[0] + score(2, size - 1);
    int begin, end;
    if (first_present > first_absent) {
        result[0] = labels[0];
        begin = 2;
        end = size - 1;
    } else {
        begin = 1;
        end = size;
        score(begin, end);
    }
    for (int index = end - 1; index >= begin;) {
        if (dynamic[index] + weights[index] > dynamic[index + 1]) {
            result[index] = labels[index];
            index -= 2;
        } else --index;
    }
}
