#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <deque>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>

using Bytes = std::vector<uint8_t>;
using Integers = std::vector<int>;

static double cpu_now() { return double(std::clock()) / CLOCKS_PER_SEC; }

struct PhiTable {
    std::array<float, 16386> table;
    PhiTable() {
        table[0] = 40;
        for (size_t index = 1; index < table.size(); ++index) table[index] = float(-std::log(std::tanh(double(index) / 1024.0)));
    }
    float operator()(float value) const {
        if (value >= 32) return 0;
        if (value < 1.0f / 512) return std::min(40.0f, float(std::log(2.0 / std::max(1e-18f, value))));
        float position = value * 512;
        int index = int(position);
        return table[index] + (position - index) * (table[index + 1] - table[index]);
    }
};

static void xor_sorted(Integers &target, const Integers &other, Integers &scratch) {
    scratch.clear();
    scratch.reserve(target.size() + other.size());
    std::set_symmetric_difference(target.begin(), target.end(), other.begin(), other.end(), std::back_inserter(scratch));
    target.swap(scratch);
}

struct Graph {
    int checks, original_variables, variables;
    std::vector<Integers> support;
    Integers representative, row_start, edge_column, col_start, col_edge;
    std::vector<float> prior;
    double expected_cost = 0, cost_variance = 0;
    Bytes baseline, offset;

    Graph(int check_count, int variable_count, int edges, const int *rows, const int *columns, const double *probability)
        : checks(check_count), original_variables(variable_count), baseline(variable_count), offset(check_count) {
        std::vector<Integers> original(variable_count);
        for (int edge = 0; edge < edges; ++edge) original[columns[edge]].push_back(rows[edge]);
        for (auto &column : original) std::sort(column.begin(), column.end());
        std::unordered_map<uint64_t, Integers> buckets;
        std::vector<double> product, largest;
        for (int column = 0; column < variable_count; ++column) {
            double chance = probability[column];
            if (chance > 0.5) {
                baseline[column] = 1;
                for (int row : original[column]) offset[row] ^= 1;
                chance = 1 - chance;
            }
            if (original[column].empty()) continue;
            uint64_t hash = 1469598103934665603ULL;
            for (int row : original[column]) { hash ^= uint64_t(row + 1); hash *= 1099511628211ULL; }
            auto &bucket = buckets[hash];
            int group = -1;
            for (int candidate : bucket) if (support[candidate] == original[column]) { group = candidate; break; }
            if (group < 0) {
                group = int(support.size());
                support.push_back(std::move(original[column]));
                representative.push_back(column);
                product.push_back(1.0);
                largest.push_back(-1.0);
                bucket.push_back(group);
            }
            product[group] *= 1 - 2 * chance;
            if (chance > largest[group]) { largest[group] = chance; representative[group] = column; }
        }
        variables = int(support.size());
        prior.resize(variables);
        row_start.assign(checks + 1, 0);
        col_start.assign(variables + 1, 0);
        for (int column = 0; column < variables; ++column) {
            double chance = (1 - product[column]) * 0.5;
            prior[column] = chance > 0 ? float(std::log((1 - chance) / chance)) : 1000000.0f;
            expected_cost += chance * prior[column];
            cost_variance += chance * (1 - chance) * prior[column] * prior[column];
            for (int row : support[column]) ++row_start[row + 1];
            col_start[column + 1] = col_start[column] + int(support[column].size());
        }
        std::partial_sum(row_start.begin(), row_start.end(), row_start.begin());
        edge_column.resize(row_start.back());
        col_edge.resize(row_start.back());
        Integers cursor = row_start;
        for (int column = 0; column < variables; ++column) {
            int local = col_start[column];
            for (int row : support[column]) {
                int edge = cursor[row]++;
                edge_column[edge] = column;
                col_edge[local++] = edge;
            }
        }
    }

    int mismatch(const Bytes &value, const Bytes &syndrome) const {
        int failures = 0;
        for (int row = 0; row < checks; ++row) {
            int parity = syndrome[row];
            for (int edge = row_start[row]; edge < row_start[row + 1]; ++edge) parity ^= value[edge_column[edge]];
            failures += parity;
        }
        return failures;
    }

    double cost(const Bytes &value) const {
        double total = 0;
        for (int column = 0; column < variables; ++column) if (value[column]) total += prior[column];
        return total;
    }
};

struct BP {
    const Graph &graph;
    std::vector<float> incoming, outgoing, posterior, average, best_score, best_posterior;
    Bytes hard;
    int iterations_used = 0;
    explicit BP(const Graph &matrix) : graph(matrix) {}

    bool run(const Bytes &syndrome, int iterations, bool layered, float alpha, int seed, double deadline, float damping = 0.0f) {
        int variables = graph.variables;
        int edges = int(graph.edge_column.size());
        incoming.resize(edges);
        outgoing.assign(edges, 0);
        static const PhiTable phi;
        std::vector<float> transformed(alpha < 0 ? edges : 0);
        posterior = graph.prior;
        average = graph.prior;
        best_score = graph.prior;
        best_posterior = graph.prior;
        hard.assign(variables, 0);
        std::vector<float> channel = graph.prior;
        std::mt19937 random(seed);
        if (seed > 1) for (float &value : channel) value *= 0.85f + float(random() % 3001) / 10000.0f;
        for (int edge = 0; edge < edges; ++edge) incoming[edge] = channel[graph.edge_column[edge]];
        posterior = channel;
        Integers order(graph.checks);
        std::iota(order.begin(), order.end(), 0);
        if (layered) std::shuffle(order.begin(), order.end(), random);
        int best_unsatisfied = graph.checks + 1;
        for (int iteration = 0; iteration < iterations; ++iteration) {
            if ((iteration & 7) == 0 && cpu_now() > deadline) break;
            for (int position = 0; position < graph.checks; ++position) {
                int row = layered ? order[position] : position;
                int start = graph.row_start[row], stop = graph.row_start[row + 1];
                if (start == stop) continue;
                float minimum = 40, second = 40;
                double phi_sum = 0;
                int smallest = -1;
                bool sign = syndrome[row];
                for (int edge = start; edge < stop; ++edge) {
                    float value = layered ? std::max(-40.0f, std::min(40.0f, posterior[graph.edge_column[edge]] - outgoing[edge])) : incoming[edge];
                    incoming[edge] = value;
                    sign ^= value < 0;
                    float magnitude = std::abs(value);
                    if (alpha < 0) { transformed[edge] = phi(magnitude); phi_sum += transformed[edge]; }
                    if (magnitude < minimum) { second = minimum; minimum = magnitude; smallest = edge; }
                    else if (magnitude < second) second = magnitude;
                }
                for (int edge = start; edge < stop; ++edge) {
                    float magnitude = alpha < 0 ? phi(float(std::max(0.0, phi_sum - transformed[edge]))) : (edge == smallest ? second : minimum);
                    float value = (sign ^ (incoming[edge] < 0) ? -1.0f : 1.0f) * magnitude * (stop - start == 1 || alpha < 0 ? 1.0f : alpha);
                    if (layered) {
                        value = 0.85f * value + 0.15f * outgoing[edge];
                        posterior[graph.edge_column[edge]] += value - outgoing[edge];
                    }
                    outgoing[edge] = value;
                }
            }
            if (!layered) {
                posterior = channel;
                for (int edge = 0; edge < edges; ++edge) posterior[graph.edge_column[edge]] += outgoing[edge];
            }
            for (int column = 0; column < variables; ++column) {
                hard[column] = posterior[column] < 0;
                average[column] = iteration == 0 ? posterior[column] : 0.7f * average[column] + 0.3f * posterior[column];
            }
            int unsatisfied = graph.mismatch(hard, syndrome);
            ++iterations_used;
            if (unsatisfied < best_unsatisfied) { best_unsatisfied = unsatisfied; best_score = average; best_posterior = posterior; }
            if (!unsatisfied) return true;
            if (!layered) for (int edge = 0; edge < edges; ++edge) {
                float value = std::max(-40.0f, std::min(40.0f, posterior[graph.edge_column[edge]] - outgoing[edge]));
                incoming[edge] = (1 - damping) * value + damping * incoming[edge];
            }
        }
        for (int column = 0; column < variables; ++column) average[column] = 0.75f * average[column] + 0.25f * best_score[column];
        return false;
    }
};

struct Elimination {
    const Graph &graph;
    std::vector<Integers> basis, expression;
    Bytes selected, residual, correction;
    Integers scratch, scratch_expression;
    size_t work = 0;

    Elimination(const Graph &matrix, const Bytes &syndrome)
        : graph(matrix), basis(matrix.checks), expression(matrix.checks), selected(matrix.variables), residual(syndrome), correction(matrix.variables) {}

    bool reduce(int column, Integers &value, Integers &combination) {
        value = graph.support[column];
        combination.assign(1, column);
        int position = int(value.size()) - 1;
        while (position >= 0) {
            int row = value[position];
            if (!basis[row].empty()) {
                work += value.size() + basis[row].size() + combination.size() + expression[row].size();
                xor_sorted(value, basis[row], scratch);
                xor_sorted(combination, expression[row], scratch_expression);
                position = int(std::lower_bound(value.begin(), value.end(), row) - value.begin()) - 1;
            } else --position;
        }
        return !value.empty();
    }

    bool add(int column, Integers &changed, Integers *cycle = nullptr) {
        selected[column] = 1;
        Integers value, combination;
        reduce(column, value, combination);
        changed.clear();
        if (value.empty()) {
            if (cycle) *cycle = std::move(combination);
            return false;
        }
        int pivot = value.back();
        if (residual[pivot]) {
            changed = value;
            for (int row : value) residual[row] ^= 1;
            for (int variable : combination) correction[variable] ^= 1;
        }
        basis[pivot] = std::move(value);
        expression[pivot] = std::move(combination);
        return true;
    }

    double cycle_delta(const Integers &cycle) const {
        double delta = 0;
        for (int column : cycle) delta += correction[column] ? -graph.prior[column] : graph.prior[column];
        return delta;
    }

    void improve(const Integers &cycle) {
        if (cycle_delta(cycle) < -1e-6) for (int column : cycle) correction[column] ^= 1;
    }
};

struct LocalDecoder {
    const Graph &graph;
    const std::vector<float> &score;
    Elimination elimination;
    Integers parent, sizes, invalid, roots, left, right, node_column;
    std::vector<Integers> known_cycles;
    int additions = 0;

    LocalDecoder(const Graph &matrix, const Bytes &syndrome, const std::vector<float> &reliability)
        : graph(matrix), score(reliability), elimination(matrix, syndrome), parent(matrix.checks), sizes(matrix.checks, 1),
          invalid(matrix.checks), roots(matrix.checks, -1), left(matrix.edge_column.size(), -1),
          right(matrix.edge_column.size(), -1), node_column(matrix.edge_column) {
        std::iota(parent.begin(), parent.end(), 0);
        for (int row = 0; row < graph.checks; ++row) {
            invalid[row] = syndrome[row];
            for (int edge = graph.row_start[row]; edge < graph.row_start[row + 1]; ++edge) roots[row] = meld(roots[row], edge);
        }
    }

    int find(int row) {
        int root = row;
        while (parent[root] != root) root = parent[root];
        while (parent[row] != row) { int next = parent[row]; parent[row] = root; row = next; }
        return root;
    }

    bool before(int first, int second) const {
        int column1 = node_column[first], column2 = node_column[second];
        return score[column1] < score[column2] || (score[column1] == score[column2] && column1 < column2);
    }

    int meld(int first, int second) {
        if (first < 0) return second;
        if (second < 0) return first;
        if (!before(first, second)) std::swap(first, second);
        right[first] = meld(right[first], second);
        std::swap(left[first], right[first]);
        return first;
    }

    int unite(int first, int second) {
        first = find(first); second = find(second);
        if (first == second) return first;
        if (sizes[first] < sizes[second]) std::swap(first, second);
        parent[second] = first;
        sizes[first] += sizes[second];
        invalid[first] += invalid[second];
        roots[first] = meld(roots[first], roots[second]);
        roots[second] = -1;
        return first;
    }

    bool solve() {
        std::deque<int> active;
        for (int row = 0; row < graph.checks; ++row) if (invalid[row]) active.push_back(row);
        Integers changed, cycle;
        while (!active.empty()) {
            int root = find(active.front()); active.pop_front();
            if (!invalid[root]) continue;
            int column = -1;
            while (roots[root] >= 0) {
                int node = roots[root];
                roots[root] = meld(left[node], right[node]);
                if (!elimination.selected[node_column[node]]) { column = node_column[node]; break; }
            }
            if (column < 0) continue;
            for (int row : graph.support[column]) root = unite(root, row);
            cycle.clear();
            elimination.add(column, changed, &cycle);
            if (!cycle.empty() && known_cycles.size() < 512) known_cycles.push_back(std::move(cycle));
            ++additions;
            for (int row : changed) invalid[root] += elimination.residual[row] ? 1 : -1;
            if (invalid[root]) active.push_back(root);
        }
        return std::none_of(elimination.residual.begin(), elimination.residual.end(), [](uint8_t value) { return value != 0; });
    }

    void improve(int per_component, double deadline) {
        Integers candidates;
        candidates.reserve(graph.variables);
        for (int column = 0; column < graph.variables; ++column) if (!elimination.selected[column]) {
            int root = find(graph.support[column][0]);
            if (sizes[root] <= 1) continue;
            bool inside = true;
            for (int row : graph.support[column]) if (find(row) != root) { inside = false; break; }
            if (inside) candidates.push_back(column);
        }
        std::sort(candidates.begin(), candidates.end(), [&](int first, int second) { return score[first] < score[second]; });
        Integers counts(graph.checks), changed, cycle;
        std::vector<Integers> cycles = known_cycles;
        for (int column : candidates) {
            int root = find(graph.support[column][0]);
            if (counts[root]++ >= per_component) continue;
            if ((cycles.size() & 31) == 0 && cpu_now() > deadline) break;
            cycle.clear();
            elimination.add(column, changed, &cycle);
            if (!cycle.empty()) { elimination.improve(cycle); cycles.push_back(std::move(cycle)); }
        }
        for (int pass = 0; pass < 2; ++pass) for (const auto &candidate : cycles) elimination.improve(candidate);
        std::vector<Integers> groups(graph.checks);
        for (int index = 0; index < int(cycles.size()); ++index) groups[find(graph.support[cycles[index][0]][0])].push_back(index);
        Integers combined;
        for (const auto &group : groups) if (group.size() > 1) {
            int limit = std::min(96, int(group.size()));
            for (int first = 0; first < limit; ++first) {
                if ((first & 15) == 0 && cpu_now() > deadline) return;
                for (int second = 0; second < first; ++second) {
                    combined.clear();
                    const auto &cycle1 = cycles[group[first]], &cycle2 = cycles[group[second]];
                    std::set_symmetric_difference(cycle1.begin(), cycle1.end(), cycle2.begin(), cycle2.end(), std::back_inserter(combined));
                    elimination.improve(combined);
                }
            }
        }
    }
};

static void packed_search(const Graph &graph, Bytes &correction, const std::vector<Integers> &cycles, double deadline) {
    if (cycles.empty() || graph.variables == 0) return;
    int words = (graph.variables + 63) / 64;
    std::vector<std::vector<uint64_t>> masks(cycles.size(), std::vector<uint64_t>(words));
    std::vector<uint64_t> current(words), candidate(words);
    for (int column = 0; column < graph.variables; ++column) if (correction[column]) current[column / 64] |= uint64_t(1) << (column % 64);
    for (size_t index = 0; index < cycles.size(); ++index) for (int column : cycles[index]) masks[index][column / 64] |= uint64_t(1) << (column % 64);
    float minimum = *std::min_element(graph.prior.begin(), graph.prior.end());
    float maximum = *std::max_element(graph.prior.begin(), graph.prior.end());
    bool uniform = maximum - minimum < 1e-6;
    double best = graph.cost(correction);
    auto consider = [&](int first, int second) {
        int weight = 0;
        for (int word = 0; word < words; ++word) {
            uint64_t value = current[word] ^ masks[first][word];
            if (second >= 0) value ^= masks[second][word];
            candidate[word] = value;
            weight += __builtin_popcountll(value);
        }
        if (double(weight) * minimum >= best - 1e-6) return;
        double cost = double(weight) * minimum;
        if (!uniform) {
            cost = 0;
            for (int word = 0; word < words; ++word) {
                uint64_t value = candidate[word];
                while (value) {
                    int bit = __builtin_ctzll(value);
                    cost += graph.prior[word * 64 + bit];
                    value &= value - 1;
                }
                if (cost >= best - 1e-6) return;
            }
        }
        if (cost < best - 1e-6) { best = cost; current.swap(candidate); }
    };
    for (int pass = 0; pass < 2; ++pass) {
        double previous = best;
        for (int first = 0; first < int(cycles.size()); ++first) {
            if ((first & 7) == 0 && cpu_now() > deadline) break;
            consider(first, -1);
            for (int second = 0; second < first; ++second) consider(first, second);
        }
        if (previous == best) break;
    }
    for (int column = 0; column < graph.variables; ++column) correction[column] = (current[column / 64] >> (column % 64)) & 1;
}

static Bytes global_osd(const Graph &graph, const Bytes &syndrome, const std::vector<float> &score, int order, double deadline) {
    Integers sorted(graph.variables);
    std::iota(sorted.begin(), sorted.end(), 0);
    std::sort(sorted.begin(), sorted.end(), [&](int first, int second) { return score[first] < score[second]; });
    Elimination elimination(graph, syndrome);
    int residual = std::accumulate(syndrome.begin(), syndrome.end(), 0);
    Integers changed, cycle;
    std::vector<Integers> cycles;
    int dependent = 0;
    for (int column : sorted) {
        cycle.clear();
        elimination.add(column, changed, &cycle);
        for (int row : changed) residual += elimination.residual[row] ? 1 : -1;
        if (!cycle.empty()) {
            if (!residual) elimination.improve(cycle);
            if (dependent++ < order) cycles.push_back(std::move(cycle));
        }
        if (!residual && (dependent >= order || cpu_now() > deadline)) break;
    }
    for (int pass = 0; pass < 3; ++pass) for (const auto &candidate : cycles) elimination.improve(candidate);
    packed_search(graph, elimination.correction, cycles, deadline);
    return elimination.correction;
}

extern "C" int decode(int checks, int variables, int edges, int shots, const int *rows, const int *columns,
                      const double *probability, const uint8_t *syndromes, uint8_t *output, double budget, double *statistics) {
    try {
        double started = cpu_now(), deadline = started + budget;
        Graph graph(checks, variables, edges, rows, columns, probability);
        statistics[0] = graph.variables;
        statistics[1] = graph.edge_column.size();
        BP bp(graph);
        for (int shot = 0; shot < shots; ++shot) {
            Bytes syndrome(checks), answer(graph.variables, 0);
            for (int row = 0; row < checks; ++row) syndrome[row] = syndromes[size_t(shot) * checks + row] ^ graph.offset[row];
            int weight = std::accumulate(syndrome.begin(), syndrome.end(), 0);
            double remaining = deadline - cpu_now();
            double allowance = std::max(0.0001, remaining / (shots - shot));
            double shot_deadline = cpu_now() + allowance;
            if (weight) {
                int iterations = 45;
                if (graph.edge_column.size() > 300000) iterations = 25;
                double primary_share = checks > 3000 ? 0.65 : 0.35;
                bool converged = bp.run(syndrome, iterations, false, 0.75f, 1, cpu_now() + allowance * primary_share, 0.25f);
                std::vector<float> reliability = bp.average;
                if (converged) { answer = bp.hard; ++statistics[2]; }
                else {
                    LocalDecoder local(graph, syndrome, reliability);
                    bool valid = local.solve();
                    local.improve(checks < 2000 ? 80 : 20, cpu_now() + std::max(0.0, shot_deadline - cpu_now()) * 0.3);
                    answer = local.elimination.correction;
                    statistics[3] += local.additions;
                    if (!valid) ++statistics[5];
                    double best_cost = valid ? graph.cost(answer) : 1e100;
                    if (valid && checks <= 1200 && graph.variables <= 5000 && cpu_now() < shot_deadline) {
                        Bytes candidate = global_osd(graph, syndrome, reliability, 70, shot_deadline);
                        if (!graph.mismatch(candidate, syndrome) && graph.cost(candidate) < best_cost) {
                            answer = std::move(candidate); best_cost = graph.cost(answer);
                        }
                    }
                    double difficult_cost = graph.expected_cost + 0.5 * std::sqrt(graph.cost_variance);
                    if (valid && best_cost > difficult_cost && checks <= 1200 && graph.variables <= 5000 && cpu_now() < shot_deadline) {
                        Bytes candidate = global_osd(graph, syndrome, bp.best_posterior, 70, shot_deadline);
                        if (!graph.mismatch(candidate, syndrome) && graph.cost(candidate) < best_cost) {
                            answer = std::move(candidate); best_cost = graph.cost(answer);
                        }
                    }
                    int retries = checks <= 3000 ? 2 : 1;
                    for (int retry = 0; valid && retry < retries && (checks <= 3000 || best_cost > difficult_cost) && cpu_now() < shot_deadline - allowance * 0.15; ++retry) {
                        bool alternate = bp.run(syndrome, 40, retry % 3 == 0, retry % 3 == 1 ? -1.0f : retry % 3 == 0 ? 0.75f : 0.625f, 17 + shot + retry * 997, shot_deadline - allowance * 0.1);
                        Bytes candidate;
                        if (alternate) candidate = bp.hard;
                        else if (cpu_now() < shot_deadline) {
                            LocalDecoder second(graph, syndrome, bp.average);
                            second.solve();
                            second.improve(30, shot_deadline);
                            candidate = std::move(second.elimination.correction);
                        }
                        if (!candidate.empty() && !graph.mismatch(candidate, syndrome) && graph.cost(candidate) < best_cost) {
                            answer = std::move(candidate); best_cost = graph.cost(answer);
                        }
                        if (!alternate && best_cost > difficult_cost && checks <= 1200 && graph.variables <= 5000 && cpu_now() < shot_deadline) {
                            candidate = global_osd(graph, syndrome, bp.average, 70, shot_deadline);
                            if (!graph.mismatch(candidate, syndrome) && graph.cost(candidate) < best_cost) {
                                answer = std::move(candidate); best_cost = graph.cost(answer);
                            }
                        }
                    }
                }
            }
            if (graph.mismatch(answer, syndrome)) ++statistics[6];
            uint8_t *destination = output + size_t(shot) * variables;
            std::copy(graph.baseline.begin(), graph.baseline.end(), destination);
            for (int column = 0; column < graph.variables; ++column) if (answer[column]) destination[graph.representative[column]] ^= 1;
        }
        statistics[4] = bp.iterations_used;
        statistics[7] = cpu_now() - started;
        return 0;
    } catch (...) { return 1; }
}
