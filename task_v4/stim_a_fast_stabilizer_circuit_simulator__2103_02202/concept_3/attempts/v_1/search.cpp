#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using Bits = unsigned __int128;
using Pair = std::array<Bits, 2>;
using State = std::array<Pair, 36>;
constexpr uint64_t mask = (1ULL << 36) - 1;
std::array<std::array<uint64_t, 11>, 36> masks;
std::vector<std::array<int, 2>> edges;
std::array<double, 11> distance_weights;
double rank_weight = 2;
std::mt19937_64 randomizer;

struct Move {
    int side, first, second, axis_first, axis_second;
};

State inverse(const State &state) {
    State result{};
    for (int qubit = 0; qubit < 36; qubit++) {
        for (int other = 0; other < 36; other++) {
            result[qubit][0] |= ((state[other][1] >> (qubit + 36)) & 1) << other;
            result[qubit][0] |= ((state[other][0] >> (qubit + 36)) & 1) << (other + 36);
            result[qubit][1] |= ((state[other][1] >> qubit) & 1) << other;
            result[qubit][1] |= ((state[other][0] >> qubit) & 1) << (other + 36);
        }
    }
    return result;
}

double cost(const Pair &pair, int qubit) {
    uint64_t xlo = static_cast<uint64_t>(pair[0]) & mask;
    uint64_t xhi = static_cast<uint64_t>(pair[0] >> 36);
    uint64_t zlo = static_cast<uint64_t>(pair[1]) & mask;
    uint64_t zhi = static_cast<uint64_t>(pair[1] >> 36);
    uint64_t support = xlo | xhi | zlo | zhi;
    uint64_t determinant = (xlo & zhi) ^ (xhi & zlo);
    double result = 0;
    for (int distance = 0; distance <= 10; distance++) {
        result += distance_weights[distance] *
            (rank_weight * __builtin_popcountll(support & masks[qubit][distance]) +
             __builtin_popcountll(determinant & masks[qubit][distance]));
    }
    return result;
}

int support_cost(const State &state) {
    int result = 0;
    for (const auto &pair : state) {
        uint64_t xlo = static_cast<uint64_t>(pair[0]) & mask;
        uint64_t xhi = static_cast<uint64_t>(pair[0] >> 36);
        uint64_t zlo = static_cast<uint64_t>(pair[1]) & mask;
        uint64_t zhi = static_cast<uint64_t>(pair[1] >> 36);
        result += 2 * __builtin_popcountll(xlo | xhi | zlo | zhi) + __builtin_popcountll((xlo & zhi) ^ (xhi & zlo));
    }
    return result;
}

std::array<Pair, 2> entangle(const Pair &first, const Pair &second, int axis_first, int axis_second) {
    int first_x = axis_first != 1;
    int first_z = axis_first != 0;
    int second_x = axis_second != 1;
    int second_z = axis_second != 0;
    Bits anti_first = (first_x ? first[1] : 0) ^ (first_z ? first[0] : 0);
    Bits anti_second = (second_x ? second[1] : 0) ^ (second_z ? second[0] : 0);
    return {Pair{first[0] ^ (first_x ? anti_second : 0), first[1] ^ (first_z ? anti_second : 0)},
            Pair{second[0] ^ (second_x ? anti_first : 0), second[1] ^ (second_z ? anti_first : 0)}};
}

void apply_move(State &state, const Move &move) {
    auto updated = entangle(state[move.first], state[move.second], move.axis_first, move.axis_second);
    state[move.first] = updated[0];
    state[move.second] = updated[1];
}

void save(const std::string &filename, const State &state, const std::vector<Move> &history) {
    std::ofstream output(filename);
    output << "{\"history\":[";
    bool separator = false;
    for (auto move : history) {
        if (separator) output << ',';
        separator = true;
        output << '[' << move.side << ',' << move.first << ',' << move.second << ',' << move.axis_first << ',' << move.axis_second << ']';
    }
    output << "],\"rows\":[";
    for (int row = 0; row < 72; row++) {
        uint64_t xrow = 0, zrow = 0;
        for (int qubit = 0; qubit < 36; qubit++) {
            xrow |= static_cast<uint64_t>((state[qubit][0] >> row) & 1) << qubit;
            zrow |= static_cast<uint64_t>((state[qubit][1] >> row) & 1) << qubit;
        }
        if (row) output << ',';
        output << '[' << xrow << ',' << zrow << ']';
    }
    output << "],\"cost\":" << support_cost(state) << '}';
}

int main(int argc, char **argv) {
    int runs = argc > 1 ? std::stoi(argv[1]) : 100;
    int max_steps = argc > 2 ? std::stoi(argv[2]) : 450;
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
    int best_support = 100000;
    int best_solved = 100000;
    for (int run = 0; run < runs; run++) {
        randomizer.seed(run);
        int mode = run % 8;
        rank_weight = run % 16 < 8 ? 2 : 1;
        for (int distance = 0; distance <= 10; distance++) {
            distance_weights[distance] = mode == 0 ? 1 : mode == 1 ? distance + 1 : mode == 2 ? distance : mode == 3 ? distance * distance + 1 : mode == 4 ? std::pow(1.5, distance) : mode == 5 ? std::sqrt(distance + 1) : mode == 6 ? distance + 0.2 : std::pow(2.0, distance);
        }
        State state = initial;
        std::vector<Move> history;
        int stalled = 0;
        int smallest = support_cost(state);
        for (int step = 0; step < max_steps; step++) {
            State inverted = inverse(state);
            double best_delta = 1e100;
            std::vector<Move> choices;
            for (int side = 0; side < 2; side++) {
                const State &current = side == 0 ? state : inverted;
                std::array<double, 36> weights;
                for (int qubit = 0; qubit < 36; qubit++) weights[qubit] = cost(current[qubit], qubit);
                for (auto edge : edges) {
                    int first = edge[0], second = edge[1];
                    for (int axis_first = 0; axis_first < 3; axis_first++) {
                        for (int axis_second = 0; axis_second < 3; axis_second++) {
                            if (!history.empty()) {
                                const auto &previous = history.back();
                                if (previous.side == side && previous.first == first && previous.second == second && previous.axis_first == axis_first && previous.axis_second == axis_second) continue;
                            }
                            auto updated = entangle(current[first], current[second], axis_first, axis_second);
                            double delta = cost(updated[0], first) + cost(updated[1], second) - weights[first] - weights[second];
                            if (run >= 16) delta += std::uniform_real_distribution<double>(0, 0.3 * (run / 16))(randomizer);
                            if (delta < best_delta - 1e-8) {
                                best_delta = delta;
                                choices.clear();
                            }
                            if (std::abs(delta - best_delta) < 1e-8) choices.push_back({side, first, second, axis_first, axis_second});
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
                save("search_best.json", state, history);
            }
            if (support == 108) {
                if (int(history.size()) < best_solved) {
                    best_solved = history.size();
                    save("search_solved.json", state, history);
                    std::cout << "SOLVED " << run << " gates " << best_solved << std::endl;
                }
                break;
            }
            if (stalled > 60) break;
        }
        std::cout << "run " << run << " mode " << mode << " steps " << history.size() << " min " << smallest << " final " << support_cost(state) << " best " << best_support << std::endl;
    }
}
