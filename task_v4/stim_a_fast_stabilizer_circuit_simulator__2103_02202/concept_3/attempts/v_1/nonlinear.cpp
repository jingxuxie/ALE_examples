#define main previous_main
#include "search.cpp"
#undef main

std::array<std::array<int, 36>, 36> metric;
std::vector<double> transformed;

std::array<uint64_t, 2> block_masks(const Pair &pair) {
    uint64_t xlo = static_cast<uint64_t>(pair[0]) & mask;
    uint64_t xhi = static_cast<uint64_t>(pair[0] >> 36);
    uint64_t zlo = static_cast<uint64_t>(pair[1]) & mask;
    uint64_t zhi = static_cast<uint64_t>(pair[1] >> 36);
    return {xlo | xhi | zlo | zhi, (xlo & zhi) ^ (xhi & zlo)};
}

void degrees(const State &state, std::array<int, 36> &rows, std::array<int, 36> &columns) {
    rows.fill(0);
    columns.fill(0);
    for (int qubit = 0; qubit < 36; qubit++) {
        auto masks = block_masks(state[qubit]);
        for (int other = 0; other < 36; other++) {
            int value = metric[qubit][other] * (2 * ((masks[0] >> other) & 1) + ((masks[1] >> other) & 1));
            rows[other] += value;
            columns[qubit] += value;
        }
    }
}

double nonlinear_delta(const std::array<uint64_t, 2> &old_first, const std::array<uint64_t, 2> &old_second,
                       const std::array<uint64_t, 2> &new_first, const std::array<uint64_t, 2> &new_second,
                       int first, int second, const std::array<int, 36> &rows, const std::array<int, 36> &columns) {
    uint64_t changed = (old_first[0] ^ new_first[0]) | (old_first[1] ^ new_first[1]) | (old_second[0] ^ new_second[0]) | (old_second[1] ^ new_second[1]);
    int difference_first = 0, difference_second = 0;
    double delta = 0;
    while (changed) {
        int other = __builtin_ctzll(changed);
        changed &= changed - 1;
        int old_value_first = 2 * ((old_first[0] >> other) & 1) + ((old_first[1] >> other) & 1);
        int new_value_first = 2 * ((new_first[0] >> other) & 1) + ((new_first[1] >> other) & 1);
        int old_value_second = 2 * ((old_second[0] >> other) & 1) + ((old_second[1] >> other) & 1);
        int new_value_second = 2 * ((new_second[0] >> other) & 1) + ((new_second[1] >> other) & 1);
        int change_first = metric[first][other] * (new_value_first - old_value_first);
        int change_second = metric[second][other] * (new_value_second - old_value_second);
        difference_first += change_first;
        difference_second += change_second;
        delta += transformed[rows[other] + change_first + change_second] - transformed[rows[other]];
    }
    delta += transformed[columns[first] + difference_first] - transformed[columns[first]];
    delta += transformed[columns[second] + difference_second] - transformed[columns[second]];
    return delta;
}

int main(int argc, char **argv) {
    int runs = argc > 1 ? std::stoi(argv[1]) : 128;
    int max_steps = argc > 2 ? std::stoi(argv[2]) : 500;
    int offset = argc > 3 ? std::stoi(argv[3]) : 0;
    State initial{};
    std::ifstream input("target_rows.txt");
    for (int row = 0; row < 72; row++) {
        uint64_t xrow, zrow;
        input >> xrow >> zrow;
        for (int qubit = 0; qubit < 36; qubit++) {
            initial[qubit][0] |= Bits((xrow >> qubit) & 1) << row;
            initial[qubit][1] |= Bits((zrow >> qubit) & 1) << row;
        }
    }
    for (int first = 0; first < 36; first++) {
        for (int second = 0; second < 36; second++) {
            int distance = std::abs(first / 6 - second / 6) + std::abs(first % 6 - second % 6);
            if (distance == 1 && first < second) edges.push_back({first, second});
        }
    }
    int best_support = 100000;
    for (int run = offset; run < offset + runs; run++) {
        randomizer.seed(run);
        int mode = run % 12;
        for (int first = 0; first < 36; first++) {
            for (int second = 0; second < 36; second++) {
                int distance = std::abs(first / 6 - second / 6) + std::abs(first % 6 - second % 6);
                metric[first][second] = mode / 4 == 0 ? 1 : mode / 4 == 1 ? distance + 1 : distance * distance + 1;
            }
        }
        transformed.resize(20000);
        for (int value = 0; value < int(transformed.size()); value++) {
            transformed[value] = mode % 4 == 0 ? std::log(value + 1.0) : mode % 4 == 1 ? std::sqrt(value) : mode % 4 == 2 ? std::pow(value, 0.25) : -1.0 / (value + 1.0);
        }
        State state = initial;
        std::vector<Move> history;
        int stalled = 0, smallest = support_cost(state);
        for (int step = 0; step < max_steps; step++) {
            State inverted = inverse(state);
            std::array<int, 36> rows, columns;
            degrees(state, rows, columns);
            double best_delta = 1e100;
            std::vector<Move> choices;
            for (int side = 0; side < 2; side++) {
                const State &current = side == 0 ? state : inverted;
                const auto &row_degrees = side == 0 ? rows : columns;
                const auto &col_degrees = side == 0 ? columns : rows;
                for (auto edge : edges) {
                    int first = edge[0], second = edge[1];
                    auto old_first = block_masks(current[first]);
                    auto old_second = block_masks(current[second]);
                    for (int axis_first = 0; axis_first < 3; axis_first++) {
                        for (int axis_second = 0; axis_second < 3; axis_second++) {
                            if (!history.empty()) {
                                const auto &previous = history.back();
                                if (previous.side == side && previous.first == first && previous.second == second && previous.axis_first == axis_first && previous.axis_second == axis_second) continue;
                            }
                            auto updated = entangle(current[first], current[second], axis_first, axis_second);
                            double delta = nonlinear_delta(old_first, old_second, block_masks(updated[0]), block_masks(updated[1]), first, second, row_degrees, col_degrees);
                            double noise = run / 12 == 0 ? 0 : std::pow(10.0, -(mode % 4 == 3 ? 5 : 2)) * (1 + run / 24);
                            delta += std::uniform_real_distribution<double>(0, noise)(randomizer);
                            if (delta < best_delta - 1e-12) {
                                best_delta = delta;
                                choices.clear();
                            }
                            if (std::abs(delta - best_delta) < 1e-12) choices.push_back({side, first, second, axis_first, axis_second});
                        }
                    }
                }
            }
            if (choices.empty()) break;
            Move move = choices[randomizer() % choices.size()];
            history.push_back(move);
            if (move.side == 0) apply_move(state, move);
            else {
                apply_move(inverted, move);
                state = inverse(inverted);
            }
            int support = support_cost(state);
            if (support < smallest) {
                smallest = support;
                stalled = 0;
            } else stalled++;
            if (support < best_support) {
                best_support = support;
                save("nonlinear_best.json", state, history);
            }
            if (support == 108) {
                save("nonlinear_solved.json", state, history);
                std::cout << "SOLVED " << run << " gates " << history.size() << std::endl;
                break;
            }
            if (stalled > 80) break;
        }
        std::cout << "run " << run << " mode " << mode << " steps " << history.size() << " min " << smallest << " final " << support_cost(state) << " best " << best_support << std::endl;
    }
}
