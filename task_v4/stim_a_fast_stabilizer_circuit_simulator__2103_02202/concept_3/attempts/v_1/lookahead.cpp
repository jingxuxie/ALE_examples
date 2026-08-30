#define main previous_main
#include "search.cpp"
#undef main
#include <unordered_set>

int mode;

double fast_cost(const Pair &pair, int qubit) {
    if (mode != 0) return cost(pair, qubit);
    uint64_t xlo = static_cast<uint64_t>(pair[0]) & mask;
    uint64_t xhi = static_cast<uint64_t>(pair[0] >> 36);
    uint64_t zlo = static_cast<uint64_t>(pair[1]) & mask;
    uint64_t zhi = static_cast<uint64_t>(pair[1] >> 36);
    return rank_weight * __builtin_popcountll(xlo | xhi | zlo | zhi) + __builtin_popcountll((xlo & zhi) ^ (xhi & zlo));
}

uint64_t hash_state(const State &state) {
    uint64_t result = 123412341234ULL;
    for (auto pair : state) {
        for (auto bits : pair) {
            result ^= uint64_t(bits) + 0x9e3779b97f4a7c15ULL + (result << 6) + (result >> 2);
            result ^= uint64_t(bits >> 64) + 0x9e3779b97f4a7c15ULL + (result << 6) + (result >> 2);
        }
    }
    return result;
}

int main(int argc, char **argv) {
    int runs = argc > 1 ? std::stoi(argv[1]) : 32;
    int max_steps = argc > 2 ? std::stoi(argv[2]) : 400;
    int offset = argc > 3 ? std::stoi(argv[3]) : 0;
    double balance = argc > 4 ? std::stod(argv[4]) : 0;
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
            masks[first][distance] |= 1ULL << second;
            if (distance == 1 && first < second) edges.push_back({first, second});
        }
    }
    std::array<std::vector<int>, 60> overlapping;
    for (int index = 0; index < 60; index++) {
        for (int other = 0; other < 60; other++) {
            if (edges[index][0] == edges[other][0] || edges[index][0] == edges[other][1] || edges[index][1] == edges[other][0] || edges[index][1] == edges[other][1]) overlapping[index].push_back(other);
        }
    }
    int best_support = 100000;
    int best_solved = 100000;
    for (int run = offset; run < offset + runs; run++) {
        randomizer.seed(run);
        mode = run % 5;
        rank_weight = run % 10 < 5 ? 2 : 1;
        for (int distance = 0; distance <= 10; distance++) {
            distance_weights[distance] = mode == 0 ? 1 : mode == 1 ? distance + 1 : mode == 2 ? distance * distance + 1 : mode == 3 ? std::pow(2, distance) : std::pow(4, distance);
        }
        State state = initial;
        std::vector<Move> history;
        std::array<std::array<int, 36>, 2> depth{};
        std::unordered_set<uint64_t> visited;
        visited.insert(hash_state(state));
        int smallest = support_cost(state), stalled = 0;
        for (int step = 0; step < max_steps; step++) {
            State inverted = inverse(state);
            double best_delta = 1e100;
            std::vector<Move> best_moves;
            uint64_t ties = 0;
            auto candidate = [&](double delta, const State &updated, const std::vector<Move> &moves) {
                if (delta > best_delta + 1e-8) return;
                State check_state = moves[0].side == 0 ? updated : inverse(updated);
                if (visited.count(hash_state(check_state))) return;
                if (delta < best_delta - 1e-8) {
                    best_delta = delta;
                    best_moves.clear();
                    ties = 0;
                }
                ties++;
                if (randomizer() % ties == 0) best_moves = moves;
            };
            auto depth_penalty = [&](const std::vector<Move> &moves) {
                if (balance == 0) return 0.0;
                auto current = depth[moves[0].side];
                int before = *std::max_element(current.begin(), current.end());
                for (auto move : moves) current[move.first] = current[move.second] = std::max(current[move.first], current[move.second]) + 1;
                return balance * (*std::max_element(current.begin(), current.end()) - before);
            };
            for (int side = 0; side < 2; side++) {
                State current = side == 0 ? state : inverted;
                std::array<double, 36> weights;
                for (int qubit = 0; qubit < 36; qubit++) weights[qubit] = fast_cost(current[qubit], qubit);
                for (int edge_index = 0; edge_index < 60; edge_index++) {
                    int first = edges[edge_index][0], second = edges[edge_index][1];
                    Pair old_first = current[first], old_second = current[second];
                    for (int axis_first = 0; axis_first < 3; axis_first++) {
                        for (int axis_second = 0; axis_second < 3; axis_second++) {
                            Move move{side, first, second, axis_first, axis_second};
                            auto updated = entangle(old_first, old_second, axis_first, axis_second);
                            double new_cost_first = fast_cost(updated[0], first), new_cost_second = fast_cost(updated[1], second);
                            double delta_first = new_cost_first + new_cost_second - weights[first] - weights[second];
                            current[first] = updated[0];
                            current[second] = updated[1];
                            candidate(delta_first / (1 + depth_penalty({move})), current, {move});
                            for (int other_edge : overlapping[edge_index]) {
                                int other_first = edges[other_edge][0], other_second = edges[other_edge][1];
                                Pair before_first = current[other_first], before_second = current[other_second];
                                double before_cost_first = other_first == first ? new_cost_first : other_first == second ? new_cost_second : weights[other_first];
                                double before_cost_second = other_second == first ? new_cost_first : other_second == second ? new_cost_second : weights[other_second];
                                for (int other_axis_first = 0; other_axis_first < 3; other_axis_first++) {
                                    for (int other_axis_second = 0; other_axis_second < 3; other_axis_second++) {
                                        auto updated_other = entangle(before_first, before_second, other_axis_first, other_axis_second);
                                        double delta_second = fast_cost(updated_other[0], other_first) + fast_cost(updated_other[1], other_second) - before_cost_first - before_cost_second;
                                        std::vector<Move> proposed_moves{move, Move{side, other_first, other_second, other_axis_first, other_axis_second}};
                                        double delta = (delta_first + delta_second) / ((run % 3 == 0 ? 2.0 : run % 3 == 1 ? 1.8 : 1.5) + depth_penalty(proposed_moves));
                                        if (delta <= best_delta + 1e-8) {
                                            current[other_first] = updated_other[0];
                                            current[other_second] = updated_other[1];
                                            candidate(delta, current, proposed_moves);
                                            current[other_first] = before_first;
                                            current[other_second] = before_second;
                                        }
                                    }
                                }
                            }
                            current[first] = old_first;
                            current[second] = old_second;
                        }
                    }
                }
            }
            if (best_moves.empty()) break;
            for (auto move : best_moves) {
                history.push_back(move);
                depth[move.side][move.first] = depth[move.side][move.second] = std::max(depth[move.side][move.first], depth[move.side][move.second]) + 1;
                if (move.side == 0) apply_move(state, move);
                else {
                    auto current = inverse(state);
                    apply_move(current, move);
                    state = inverse(current);
                }
                visited.insert(hash_state(state));
            }
            int support = support_cost(state);
            if (support < smallest) {
                smallest = support;
                stalled = 0;
                if (support < 600) save("trial_" + std::to_string(run) + "_" + std::to_string(int(balance * 10)) + ".json", state, history);
            } else stalled++;
            if (support < best_support) {
                best_support = support;
                save("lookahead_best.json", state, history);
            }
            if (support == 108) {
                if (int(history.size()) < best_solved) {
                    best_solved = history.size();
                    save("lookahead_solved.json", state, history);
                }
                std::cout << "SOLVED " << run << " gates " << history.size() << std::endl;
                break;
            }
            if (stalled > 40) break;
        }
        std::cout << "run " << run << " mode " << mode << " gates " << history.size() << " min " << smallest << " final " << support_cost(state) << " best " << best_support << std::endl;
    }
}
