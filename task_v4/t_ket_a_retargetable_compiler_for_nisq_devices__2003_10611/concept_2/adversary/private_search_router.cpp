#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

extern "C" int count_swaps(int gate_count, const int* gates, int edge_count,
                           const int* edges, const int* initial, int horizon,
                           double decay, int lexicographic, const int* ranks) {
    constexpr int qubits = 16;
    std::array<std::array<int, qubits>, qubits> distance;
    std::array<std::vector<int>, qubits> neighbors;
    for (int source = 0; source < qubits; ++source) {
        for (int target = 0; target < qubits; ++target) {
            distance[source][target] = source == target ? 0 : 17;
        }
    }
    for (int index = 0; index < edge_count; ++index) {
        int left = edges[2 * index];
        int right = edges[2 * index + 1];
        distance[left][right] = distance[right][left] = 1;
        neighbors[left].push_back(right);
        neighbors[right].push_back(left);
    }
    for (auto& adjacent : neighbors) {
        std::sort(adjacent.begin(), adjacent.end());
    }
    for (int middle = 0; middle < qubits; ++middle) {
        for (int source = 0; source < qubits; ++source) {
            for (int target = 0; target < qubits; ++target) {
                distance[source][target] = std::min(distance[source][target],
                    distance[source][middle] + distance[middle][target]);
            }
        }
    }
    std::array<int, qubits> position;
    std::array<int, qubits> occupants;
    std::array<int, qubits> previous;
    previous.fill(-1);
    for (int qubit = 0; qubit < qubits; ++qubit) {
        position[qubit] = initial[qubit];
        occupants[initial[qubit]] = qubit;
    }
    std::array<std::array<int, 2>, 200> parents;
    for (int index = 0; index < gate_count; ++index) {
        int left = gates[2 * index];
        int right = gates[2 * index + 1];
        parents[index] = {previous[left], previous[right]};
        previous[left] = previous[right] = index;
    }
    std::array<bool, 200> completed{};
    std::array<int, 200> depth{};
    std::vector<std::uint64_t> visited;
    auto encode = [&]() {
        std::uint64_t state = 0;
        for (int qubit = 0; qubit < qubits; ++qubit) {
            state |= std::uint64_t(position[qubit]) << (4 * qubit);
        }
        return state;
    };
    visited.push_back(encode());
    std::array<double, 32> weights;
    for (int level = 0; level < horizon; ++level) {
        weights[level] = std::pow(decay, level);
    }
    int swaps = 0;
    int remaining = gate_count;
    int stalled = 0;
    auto apply_swap = [&](int left, int right) {
        int first = occupants[left];
        int second = occupants[right];
        std::swap(occupants[left], occupants[right]);
        position[first] = right;
        position[second] = left;
        ++swaps;
    };
    while (remaining > 0) {
        std::vector<int> front;
        std::vector<int> executable;
        for (int index = 0; index < gate_count; ++index) {
            if (completed[index]) {
                continue;
            }
            bool ready = true;
            for (int parent : parents[index]) {
                if (parent >= 0 && !completed[parent]) {
                    ready = false;
                }
            }
            if (ready) {
                front.push_back(index);
                if (distance[position[gates[2 * index]]][position[gates[2 * index + 1]]] == 1) {
                    executable.push_back(index);
                }
            }
        }
        if (!executable.empty()) {
            for (int index : executable) {
                completed[index] = true;
                --remaining;
            }
            visited.assign(1, encode());
            stalled = 0;
            continue;
        }
        std::array<std::vector<int>, 32> layers;
        for (int index = 0; index < gate_count; ++index) {
            if (completed[index]) {
                continue;
            }
            int level = 0;
            for (int parent : parents[index]) {
                if (parent >= 0 && !completed[parent]) {
                    level = std::max(level, depth[parent] + 1);
                }
            }
            depth[index] = level;
            if (level < horizon) {
                layers[level].push_back(index);
            }
        }
        std::array<bool, qubits> active{};
        for (int index : front) {
            active[position[gates[2 * index]]] = true;
            active[position[gates[2 * index + 1]]] = true;
        }
        int best_edge = -1;
        double best_score = std::numeric_limits<double>::infinity();
        std::array<double, 32> best_values{};
        for (int edge = 0; edge < edge_count; ++edge) {
            int left = edges[2 * edge];
            int right = edges[2 * edge + 1];
            if (!active[left] && !active[right]) {
                continue;
            }
            int first = occupants[left];
            int second = occupants[right];
            position[first] = right;
            position[second] = left;
            std::uint64_t state = encode();
            if (std::find(visited.begin(), visited.end(), state) == visited.end()) {
                std::array<double, 32> values{};
                double score = 0;
                for (int level = 0; level < horizon; ++level) {
                    int total = 0;
                    for (int index : layers[level]) {
                        total += distance[position[gates[2 * index]]][position[gates[2 * index + 1]]] - 1;
                    }
                    values[level] = double(total) / std::max(std::size_t(1), layers[level].size());
                    score += values[level] * weights[level];
                }
                bool better = best_edge < 0;
                bool equal = true;
                if (lexicographic) {
                    for (int level = 0; level < horizon; ++level) {
                        if (values[level] < best_values[level]) {
                            better = true;
                            equal = false;
                            break;
                        }
                        if (values[level] > best_values[level]) {
                            equal = false;
                            break;
                        }
                    }
                } else {
                    better = better || score < best_score;
                    equal = score == best_score;
                }
                if (better || (equal && ranks[edge] < ranks[best_edge])) {
                    best_edge = edge;
                    best_score = score;
                    best_values = values;
                }
            }
            position[first] = left;
            position[second] = right;
        }
        if (best_edge >= 0 && stalled < 32) {
            apply_swap(edges[2 * best_edge], edges[2 * best_edge + 1]);
            visited.push_back(encode());
            ++stalled;
        } else {
            int chosen = front[0];
            int closest = 17;
            for (int index : front) {
                int separation = distance[position[gates[2 * index]]][position[gates[2 * index + 1]]];
                if (separation < closest) {
                    closest = separation;
                    chosen = index;
                }
            }
            int current = position[gates[2 * chosen]];
            int destination = position[gates[2 * chosen + 1]];
            while (distance[current][destination] > 1) {
                int next = -1;
                for (int neighbor : neighbors[current]) {
                    if (distance[neighbor][destination] == distance[current][destination] - 1) {
                        next = neighbor;
                        break;
                    }
                }
                apply_swap(current, next);
                current = next;
            }
            completed[chosen] = true;
            --remaining;
            visited.assign(1, encode());
            stalled = 0;
        }
    }
    return swaps;
}
