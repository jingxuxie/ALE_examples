#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <vector>

using namespace std;
using Bits = array<uint64_t, 8>;
struct Node {
    int left = -1, right = -1, parent = -1, rank = 0;
    Bits mask{};
    double cost = 0;
};
struct Tree {
    vector<Node> nodes;
    vector<int> slices;
    double work = 0;
};
int count_vertices, count_edges, blocks;
double memory_cap;
vector<array<int, 3>> edges;
Bits weight_four{}, weight_six{};
vector<double> powers;
chrono::steady_clock::time_point deadline;
bool expired() { return chrono::steady_clock::now() >= deadline; }
mt19937_64 generator(827419);
class PythonRandom {
    array<uint32_t, 624> state{};
    int position = 624;
    bool cached = false;
    double cached_gaussian = 0;
    uint32_t integer() {
        if (position >= 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t value = (state[index] & 0x80000000U) | (state[(index + 1) % 624] & 0x7fffffffU);
                state[index] = state[(index + 397) % 624] ^ (value >> 1) ^ ((value & 1) ? 0x9908b0dfU : 0);
            }
            position = 0;
        }
        uint32_t value = state[position++];
        value ^= value >> 11; value ^= (value << 7) & 0x9d2c5680U;
        value ^= (value << 15) & 0xefc60000U; value ^= value >> 18;
        return value;
    }
public:
    explicit PythonRandom(uint32_t seed) {
        state[0] = 19650218U;
        for (int index = 1; index < 624; ++index) state[index] = 1812433253U * (state[index - 1] ^ (state[index - 1] >> 30)) + index;
        int index = 1;
        for (int count = 0; count < 624; ++count) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1664525U)) + seed;
            if (++index >= 624) { state[0] = state[623]; index = 1; }
        }
        for (int count = 0; count < 623; ++count) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1566083941U)) - index;
            if (++index >= 624) { state[0] = state[623]; index = 1; }
        }
        state[0] = 0x80000000U;
    }
    double random() {
        uint32_t first = integer() >> 5, second = integer() >> 6;
        return (first * 67108864.0 + second) * (1.0 / 9007199254740992.0);
    }
    double gaussian() {
        if (cached) { cached = false; return cached_gaussian; }
        double angle = random() * 6.283185307179586;
        double radius = sqrt(-2.0 * log(1.0 - random()));
        cached_gaussian = sin(angle) * radius; cached = true;
        return cos(angle) * radius;
    }
};
double uniform_random() { return (generator() >> 11) * 0x1.0p-53; }
int weight(const Bits &mask) {
    int result = 0;
    for (int block = 0; block < blocks; ++block)
        result += 2 * (__builtin_popcountll(mask[block]) + __builtin_popcountll(mask[block] & weight_four[block]) + 2 * __builtin_popcountll(mask[block] & weight_six[block]));
    return result;
}
Bits combine(const Bits &first, const Bits &second) {
    Bits result{};
    for (int block = 0; block < blocks; ++block) result[block] = first[block] ^ second[block];
    return result;
}
bool intersect(const Bits &first, const Bits &second) {
    for (int block = 0; block < blocks; ++block) if (first[block] & second[block]) return true;
    return false;
}
void update_node(Tree &tree, int index) {
    Node &node = tree.nodes[index];
    const Node &left = tree.nodes[node.left], &right = tree.nodes[node.right];
    node.mask = combine(left.mask, right.mask);
    node.rank = weight(node.mask);
    node.cost = powers[(left.rank + right.rank + node.rank) / 2];
}
void rebuild_node(Tree &tree, int index) {
    if (index < count_vertices) return;
    rebuild_node(tree, tree.nodes[index].left);
    rebuild_node(tree, tree.nodes[index].right);
    update_node(tree, index);
}
void rebuild(Tree &tree) {
    vector<bool> sliced(count_edges, false);
    for (int edge : tree.slices) sliced[edge] = true;
    for (int vertex = 0; vertex < count_vertices; ++vertex) tree.nodes[vertex].mask = {};
    for (int edge = 0; edge < count_edges; ++edge) if (!sliced[edge]) {
        tree.nodes[edges[edge][0]].mask[edge / 64] |= uint64_t(1) << (edge % 64);
        tree.nodes[edges[edge][1]].mask[edge / 64] |= uint64_t(1) << (edge % 64);
    }
    for (int vertex = 0; vertex < count_vertices; ++vertex) tree.nodes[vertex].rank = weight(tree.nodes[vertex].mask);
    rebuild_node(tree, 2 * count_vertices - 2);
    tree.work = 0;
    for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) tree.work += tree.nodes[index].cost;
}
double schedule(const Tree &tree, vector<array<int, 2>> *merges = nullptr) {
    int total = tree.nodes.size();
    vector<int> waiting(total, 2), ids(total, -1);
    vector<int> ready;
    double resident = !tree.slices.empty();
    for (int vertex = 0; vertex < count_vertices; ++vertex) {
        ids[vertex] = vertex;
        resident += powers[tree.nodes[vertex].rank];
        int parent = tree.nodes[vertex].parent;
        if (parent >= 0 && --waiting[parent] == 0) ready.push_back(parent);
    }
    double peak = resident;
    int next = count_vertices;
    while (!ready.empty()) {
        int choice = 0;
        double best_score = 1e300;
        for (int offset = 0; offset < (int)ready.size(); ++offset) {
            const Node &node = tree.nodes[ready[offset]];
            double output = powers[node.rank];
            double change = output - powers[tree.nodes[node.left].rank] - powers[tree.nodes[node.right].rank];
            double score = change <= 0 ? change : output;
            if (resident + output > memory_cap) score += 1e100;
            if (score < best_score) { choice = offset; best_score = score; }
        }
        int index = ready[choice];
        ready[choice] = ready.back(); ready.pop_back();
        const Node &node = tree.nodes[index];
        double output = powers[node.rank];
        peak = max(peak, resident + output);
        resident += output - powers[tree.nodes[node.left].rank] - powers[tree.nodes[node.right].rank];
        if (merges) merges->push_back({ids[node.left], ids[node.right]});
        ids[index] = next++;
        if (node.parent >= 0 && --waiting[node.parent] == 0) ready.push_back(node.parent);
    }
    return peak;
}
double total_work(const Tree &tree) {
    int slice_rank = 0;
    for (int edge : tree.slices) slice_rank += edges[edge][2];
    return powers[slice_rank] * (tree.work + 1) - 1;
}
Tree greedy(const vector<int> &slices, double alpha, double temperature, PythonRandom *baseline_random = nullptr) {
    Tree tree;
    tree.nodes.resize(2 * count_vertices - 1);
    tree.slices = slices;
    vector<bool> sliced(count_edges, false), live(2 * count_vertices - 1, false);
    for (int edge : slices) sliced[edge] = true;
    for (int edge = 0; edge < count_edges; ++edge) if (!sliced[edge]) {
        tree.nodes[edges[edge][0]].mask[edge / 64] |= uint64_t(1) << (edge % 64);
        tree.nodes[edges[edge][1]].mask[edge / 64] |= uint64_t(1) << (edge % 64);
    }
    for (int vertex = 0; vertex < count_vertices; ++vertex) {
        live[vertex] = true;
        tree.nodes[vertex].rank = weight(tree.nodes[vertex].mask);
    }
    using Entry = pair<double, pair<int, int>>;
    priority_queue<Entry, vector<Entry>, greater<Entry>> heap;
    auto push_pair = [&](int left, int right) {
        if (!intersect(tree.nodes[left].mask, tree.nodes[right].mask)) return;
        int output = weight(combine(tree.nodes[left].mask, tree.nodes[right].mask));
        int arithmetic = (tree.nodes[left].rank + tree.nodes[right].rank + output) / 2;
        double noise = baseline_random ? baseline_random->gaussian() : -log(-log(max(1e-12, uniform_random())));
        double score = arithmetic + alpha * output + temperature * noise;
        heap.push({score, {left, right}});
    };
    for (int left = 0; left < count_vertices; ++left)
        for (int right = left + 1; right < count_vertices; ++right) push_pair(left, right);
    for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) {
        while (!heap.empty() && (!live[heap.top().second.first] || !live[heap.top().second.second])) heap.pop();
        int left = -1, right = -1;
        if (heap.empty()) {
            for (int other = 0; other < index; ++other) if (live[other]) {
                if (left < 0 || tree.nodes[other].rank < tree.nodes[left].rank) { right = left; left = other; }
                else if (right < 0 || tree.nodes[other].rank < tree.nodes[right].rank) right = other;
            }
        } else { left = heap.top().second.first; right = heap.top().second.second; heap.pop(); }
        tree.nodes[index].left = left; tree.nodes[index].right = right;
        tree.nodes[left].parent = index; tree.nodes[right].parent = index;
        update_node(tree, index);
        tree.work += tree.nodes[index].cost;
        live[left] = live[right] = false; live[index] = true;
        for (int other = 0; other < index; ++other) if (live[other]) push_pair(other, index);
    }
    return tree;
}
using ExactWork = array<uint64_t, 64>;
ExactWork exact_work(const Tree &tree) {
    ExactWork result{};
    int slice_rank = 0;
    for (int edge : tree.slices) slice_rank += edges[edge][2];
    auto add_power = [&](int rank) {
        int block = rank / 64;
        uint64_t amount = uint64_t(1) << (rank % 64);
        while (true) {
            uint64_t before = result[block];
            result[block] += amount;
            if (result[block] >= before) break;
            ++block; amount = 1;
        }
    };
    add_power(slice_rank);
    for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) {
        const Node &node = tree.nodes[index];
        add_power(slice_rank + (tree.nodes[node.left].rank + tree.nodes[node.right].rank + node.rank) / 2);
    }
    for (int block = 0; block < 64; ++block) if (result[block]-- != 0) break;
    return result;
}
bool smaller(const ExactWork &left, const ExactWork &right) {
    for (int block = 63; block >= 0; --block) if (left[block] != right[block]) return left[block] < right[block];
    return false;
}
double original_peak(const Tree &tree) {
    double resident = !tree.slices.empty();
    for (int vertex = 0; vertex < count_vertices; ++vertex) resident += powers[tree.nodes[vertex].rank];
    double peak = resident;
    for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) {
        const Node &node = tree.nodes[index];
        peak = max(peak, resident + powers[node.rank]);
        resident += powers[node.rank] - powers[tree.nodes[node.left].rank] - powers[tree.nodes[node.right].rank];
    }
    return peak;
}
Tree reference_baseline() {
    Tree best;
    ExactWork best_work{};
    for (int trial = 0; trial < 24; ++trial) {
        int seed = 1337 + trial * 7919;
        const double temperatures[] = {0, 0.4, 0.8, 1.2};
        PythonRandom slicing_random(seed + 761);
        vector<int> slices;
        Tree tree;
        while (true) {
            PythonRandom contraction_random(seed);
            tree = greedy(slices, 0.35, temperatures[trial % 4], &contraction_random);
            if (original_peak(tree) <= memory_cap) break;
            vector<int> frontiers(count_vertices - 1);
            iota(frontiers.begin(), frontiers.end(), count_vertices);
            sort(frontiers.begin(), frontiers.end(), [&](int left, int right) {
                if (tree.nodes[left].rank != tree.nodes[right].rank) return tree.nodes[left].rank > tree.nodes[right].rank;
                for (int block = blocks - 1; block >= 0; --block)
                    if (tree.nodes[left].mask[block] != tree.nodes[right].mask[block]) return tree.nodes[left].mask[block] > tree.nodes[right].mask[block];
                return false;
            });
            int highest = tree.nodes[frontiers[0]].rank;
            vector<double> frequencies(count_edges);
            vector<int> candidates;
            for (int index : frontiers) {
                const Node &node = tree.nodes[index];
                if (node.rank < highest - 5) break;
                for (int block = 0; block < blocks; ++block) {
                    uint64_t remaining = node.mask[block];
                    while (remaining) {
                        int edge = block * 64 + __builtin_ctzll(remaining);
                        remaining &= remaining - 1;
                        if (!frequencies[edge]) candidates.push_back(edge);
                        frequencies[edge] += exp2(node.rank - highest);
                    }
                }
            }
            if (candidates.empty()) for (int edge = 0; edge < count_edges; ++edge)
                if (find(slices.begin(), slices.end(), edge) == slices.end()) { candidates.push_back(edge); frequencies[edge] = 1; }
            int chosen = -1;
            double best_score = -1;
            for (int edge : candidates) {
                double score = frequencies[edge] * edges[edge][2] * (0.8 + (1.2 - 0.8) * slicing_random.random());
                if (score > best_score) { chosen = edge; best_score = score; }
            }
            slices.push_back(chosen);
        }
        ExactWork work = exact_work(tree);
        if (best.nodes.empty() || smaller(work, best_work)) { best = move(tree); best_work = work; }
    }
    return best;
}
void emit(const Tree &tree, bool original = false) {
    vector<array<int, 2>> merges;
    if (original || schedule(tree) > memory_cap) {
        for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) merges.push_back({tree.nodes[index].left, tree.nodes[index].right});
    } else schedule(tree, &merges);
    cout << "{\"slices\":[";
    for (int offset = 0; offset < (int)tree.slices.size(); ++offset) cout << (offset ? "," : "") << tree.slices[offset];
    cout << "],\"merges\":[";
    for (int offset = 0; offset < (int)merges.size(); ++offset) cout << (offset ? "," : "") << '[' << merges[offset][0] << ',' << merges[offset][1] << ']';
    cout << "]}" << endl;
}
void anneal(Tree &tree, int iterations, double initial_temperature, double memory_penalty) {
    Tree best = tree;
    double best_energy = 0;
    auto energy = [&](int rank, double cost) { return cost + memory_penalty * powers[rank]; };
    for (int index = count_vertices; index < 2 * count_vertices - 1; ++index)
        best_energy += energy(tree.nodes[index].rank, tree.nodes[index].cost);
    double current_energy = best_energy;
    for (int iteration = 0; iteration < iterations; ++iteration) {
        if (iteration % 4096 == 0 && expired()) break;
        int index = count_vertices + generator() % (count_vertices - 2);
        Node &node = tree.nodes[index];
        int parent_index = node.parent;
        if (parent_index < 0) continue;
        Node &parent = tree.nodes[parent_index];
        int sibling = parent.left == index ? parent.right : parent.left;
        bool side = generator() & 1;
        int exchange = side ? node.left : node.right;
        int stay = side ? node.right : node.left;
        Bits new_mask = combine(tree.nodes[stay].mask, tree.nodes[sibling].mask);
        int new_rank = weight(new_mask);
        double new_cost = powers[(tree.nodes[stay].rank + tree.nodes[sibling].rank + new_rank) / 2];
        double parent_cost = powers[(new_rank + tree.nodes[exchange].rank + parent.rank) / 2];
        double old_local = energy(node.rank, node.cost) + energy(parent.rank, parent.cost);
        double new_local = energy(new_rank, new_cost) + energy(parent.rank, parent_cost);
        double temperature = initial_temperature * pow(0.01, double(iteration) / iterations);
        bool accept = new_local <= old_local;
        if (!accept && temperature > 0) accept = uniform_random() < exp2(-log2(new_local / old_local) / temperature);
        if (!accept) continue;
        tree.work += new_cost + parent_cost - node.cost - parent.cost;
        current_energy += new_local - old_local;
        node.mask = new_mask; node.rank = new_rank; node.cost = new_cost; parent.cost = parent_cost;
        if (side) node.left = sibling; else node.right = sibling;
        if (parent.left == index) parent.right = exchange; else parent.left = exchange;
        tree.nodes[sibling].parent = index; tree.nodes[exchange].parent = parent_index;
        if (current_energy < best_energy * (1 - 1e-12)) { best_energy = current_energy; best = tree; }
    }
    if (current_energy > best_energy * (1 + 1e-12)) tree = best;
    rebuild(tree);
}
double memory_badness(const Tree &tree, double peak) {
    double badness = max(0.0, peak / memory_cap - 1);
    for (const Node &node : tree.nodes) badness += max(0.0, 4 * powers[node.rank] / memory_cap - 1);
    return badness;
}
Tree slice_to_fit(Tree tree) {
    while (schedule(tree) > memory_cap) {
        if (expired()) return tree;
        Tree best;
        double best_score = 1e300;
        double old_peak = schedule(tree);
        double old_badness = memory_badness(tree, old_peak);
        for (int edge = 0; edge < count_edges; ++edge) {
            if (expired()) return tree;
            if (find(tree.slices.begin(), tree.slices.end(), edge) != tree.slices.end()) continue;
            Tree candidate = tree;
            candidate.slices.push_back(edge);
            rebuild(candidate);
            double peak = schedule(candidate);
            double reduction = log2((old_badness + 1e-12) / (memory_badness(candidate, peak) + 1e-12));
            if (reduction < 1e-5) continue;
            double growth = log2(total_work(candidate) / total_work(tree));
            double score = peak <= memory_cap ? -1e6 + growth : growth / reduction + 0.001 * edges[edge][2];
            if (score < best_score) { best_score = score; best = move(candidate); }
        }
        if (best.nodes.empty()) {
            for (int edge = 0; edge < count_edges; ++edge)
                if (find(tree.slices.begin(), tree.slices.end(), edge) == tree.slices.end()) { tree.slices.push_back(edge); break; }
            rebuild(tree);
        } else tree = move(best);
    }
    return tree;
}
double subtree_work(const Tree &tree, int index) {
    if (index < count_vertices) return 0;
    return tree.nodes[index].cost + subtree_work(tree, tree.nodes[index].left) + subtree_work(tree, tree.nodes[index].right);
}
void reconfigure(Tree &tree, int rounds, int frontier_limit, double penalty) {
    for (int round = 0; round < rounds; ++round) {
        if (expired()) return;
        int root = 2 * count_vertices - 2;
        if (round % 3) {
            double target = uniform_random() * tree.work;
            for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) {
                target -= tree.nodes[index].cost;
                if (target <= 0) { root = index; break; }
            }
            if (tree.nodes[root].parent >= 0 && uniform_random() < 0.5) root = tree.nodes[root].parent;
        }
        vector<int> frontier{root}, available;
        while ((int)frontier.size() < frontier_limit) {
            int choice = -1;
            double best_priority = -1;
            for (int offset = 0; offset < (int)frontier.size(); ++offset) {
                int index = frontier[offset];
                if (index < count_vertices) continue;
                double priority = log2(1 + subtree_work(tree, index)) + (frontier_limit >= 16 ? 2 : 8) * uniform_random();
                if (priority > best_priority) { best_priority = priority; choice = offset; }
            }
            if (choice < 0) break;
            int index = frontier[choice];
            available.push_back(index);
            frontier[choice] = tree.nodes[index].left;
            frontier.push_back(tree.nodes[index].right);
        }
        int count = frontier.size(), states = 1 << count;
        if (count < 4) continue;
        double old_cost = 0;
        int rank_cap = max(0, int(log2(memory_cap)) - 1);
        for (int index : available) {
            old_cost += tree.nodes[index].cost + penalty * powers[tree.nodes[index].rank];
            rank_cap = max(rank_cap, tree.nodes[index].rank);
        }
        for (int index : frontier) rank_cap = max(rank_cap, tree.nodes[index].rank);
        vector<Bits> masks(states);
        vector<int> ranks(states), splits(states, 0);
        vector<double> costs(states, 1e300);
        vector<int> feasible;
        costs[0] = 0;
        for (int subset = 1; subset < states; ++subset) {
            if (subset % 64 == 0 && expired()) return;
            int bit = __builtin_ctz(subset), other = subset & (subset - 1);
            masks[subset] = combine(masks[other], tree.nodes[frontier[bit]].mask);
            ranks[subset] = weight(masks[subset]);
            if (!other) { costs[subset] = 0; feasible.push_back(subset); continue; }
            if (ranks[subset] > rank_cap) continue;
            auto evaluate = [&](int part) {
                int complement = subset ^ part;
                if (costs[part] > old_cost || costs[complement] > old_cost) return;
                double candidate = costs[part] + costs[complement] + powers[(ranks[part] + ranks[complement] + ranks[subset]) / 2] + penalty * powers[ranks[subset]];
                if (candidate < costs[subset]) { costs[subset] = candidate; splits[subset] = part; }
            };
            if ((1 << __builtin_popcount(other)) > (int)feasible.size()) {
                for (int part : feasible) if ((part & other) == part) evaluate(part);
            } else {
                for (int part = other; part; part = (part - 1) & other) evaluate(part);
            }
            if (costs[subset] <= old_cost) feasible.push_back(subset);
        }
        if (costs.back() > old_cost * (1 + 1e-12)) continue;
        int cursor = 1;
        auto install = [&](auto &&self, int subset, int index) -> int {
            if (!(subset & (subset - 1))) return frontier[__builtin_ctz(subset)];
            if (index < 0) index = available[cursor++];
            int left = self(self, splits[subset], -1);
            int right = self(self, subset ^ splits[subset], -1);
            tree.nodes[index].left = left; tree.nodes[index].right = right;
            tree.nodes[left].parent = index; tree.nodes[right].parent = index;
            update_node(tree, index);
            return index;
        };
        install(install, states - 1, root);
        tree.work = 0;
        for (int index = count_vertices; index < 2 * count_vertices - 1; ++index) tree.work += tree.nodes[index].cost;
    }
}
int edge_count(const Bits &mask) {
    int result = 0;
    for (int block = 0; block < blocks; ++block) result += __builtin_popcountll(mask[block]);
    return result;
}
array<int, 2> reduction_pair(const vector<Bits> &masks) {
    for (int left = 0; left < (int)masks.size(); ++left) {
        int degree = edge_count(masks[left]);
        if (degree > 2) continue;
        for (int right = 0; right < (int)masks.size(); ++right)
            if (left != right && (!degree || intersect(masks[left], masks[right]))) return {min(left, right), max(left, right)};
    }
    for (int left = 0; left < (int)masks.size(); ++left)
        for (int right = left + 1; right < (int)masks.size(); ++right) {
            int shared = 0;
            for (int block = 0; block < blocks; ++block) shared += __builtin_popcountll(masks[left][block] & masks[right][block]);
            if (shared >= 2) return {left, right};
        }
    return {-1, -1};
}
int reduced_count(vector<Bits> masks) {
    while (masks.size() > 1) {
        auto pair = reduction_pair(masks);
        if (pair[0] < 0) break;
        masks[pair[0]] = combine(masks[pair[0]], masks[pair[1]]);
        masks.erase(masks.begin() + pair[1]);
    }
    return masks.size();
}
Tree series_trial() {
    Tree tree;
    tree.nodes.resize(2 * count_vertices - 1);
    vector<Bits> masks(count_vertices);
    vector<int> active(count_vertices);
    iota(active.begin(), active.end(), 0);
    for (int edge = 0; edge < count_edges; ++edge) {
        masks[edges[edge][0]][edge / 64] |= uint64_t(1) << (edge % 64);
        masks[edges[edge][1]][edge / 64] |= uint64_t(1) << (edge % 64);
    }
    int next = count_vertices;
    double noise = 1.0 + 7.0 * uniform_random();
    while (active.size() > 1) {
        if (expired()) return {};
        auto pair = reduction_pair(masks);
        if (pair[0] >= 0) {
            int left = active[pair[0]], right = active[pair[1]];
            tree.nodes[next].left = left; tree.nodes[next].right = right;
            tree.nodes[left].parent = next; tree.nodes[right].parent = next;
            masks[pair[0]] = combine(masks[pair[0]], masks[pair[1]]);
            active[pair[0]] = next++;
            masks.erase(masks.begin() + pair[1]);
            active.erase(active.begin() + pair[1]);
            continue;
        }
        Bits present{};
        for (const Bits &mask : masks) for (int block = 0; block < blocks; ++block) present[block] |= mask[block];
        int chosen = -1;
        double best_score = 1e300;
        for (int block = 0; block < blocks; ++block) {
            uint64_t remaining = present[block];
            while (remaining) {
                if (expired()) return {};
                int bit = __builtin_ctzll(remaining), edge = 64 * block + bit;
                remaining &= remaining - 1;
                vector<Bits> candidate = masks;
                for (Bits &mask : candidate) mask[block] &= ~(uint64_t(1) << bit);
                double score = reduced_count(move(candidate)) + 2.0 * edges[edge][2] + noise * uniform_random();
                if (score < best_score) { best_score = score; chosen = edge; }
            }
        }
        tree.slices.push_back(chosen);
        for (Bits &mask : masks) mask[chosen / 64] &= ~(uint64_t(1) << (chosen % 64));
    }
    rebuild(tree);
    return tree;
}
int main(int argc, char **argv) {
    auto started = chrono::steady_clock::now();
    double seconds = argc > 1 ? atof(argv[1]) : 37;
    deadline = started + chrono::duration_cast<chrono::steady_clock::duration>(chrono::duration<double>(seconds));
    cin >> count_vertices >> count_edges >> memory_cap;
    blocks = (count_edges + 63) / 64;
    if (blocks > 8 || count_vertices < 3) return 1;
    powers.resize(4096);
    for (int rank = 0; rank < 4096; ++rank) powers[rank] = exp2(min(rank, 1000));
    edges.resize(count_edges);
    for (int edge = 0; edge < count_edges; ++edge) {
        cin >> edges[edge][0] >> edges[edge][1] >> edges[edge][2];
        if (edges[edge][2] == 4) weight_four[edge / 64] |= uint64_t(1) << (edge % 64);
        if (edges[edge][2] == 6) weight_six[edge / 64] |= uint64_t(1) << (edge % 64);
    }
    Tree best = reference_baseline();
    emit(best, true);
    double best_work = total_work(best);
    auto consider = [&](Tree tree) {
        if (tree.nodes.empty()) return;
        if (schedule(tree) > memory_cap) tree = slice_to_fit(move(tree));
        if (schedule(tree) > memory_cap) return;
        double work = total_work(tree);
        if (work < best_work || (work == best_work && uniform_random() < 0.1)) { best = move(tree); best_work = work; }
    };
    int initial_slice_rank = 0;
    for (int edge : best.slices) initial_slice_rank += edges[edge][2];
    if (initial_slice_rank >= 24) {
        for (int trial = 0; trial < 32 && !expired(); ++trial) consider(series_trial());
    }
    int trials = 0;
    while (!expired()) {
        Tree tree;
        if (trials % 4 == 0 || (trials % 4 == 2 && !best.slices.empty())) {
            tree = best;
            if (trials % 4 == 2) {
                tree.slices.erase(tree.slices.begin() + generator() % tree.slices.size());
                rebuild(tree);
            }
        }
        else tree = greedy(trials % 5 == 0 ? best.slices : vector<int>{}, uniform_random() * 1.5 - 0.25, uniform_random() * 3.0);
        const double penalties[] = {0, 16, 256, 4096, 65536};
        double penalty = penalties[trials % 5];
        anneal(tree, count_vertices * (trials % 4 == 0 ? 1000 : 200), 0.3 + uniform_random() * 2, penalty);
        reconfigure(tree, trials % 4 == 0 ? 60 : 15, trials % 4 == 0 ? 10 : 8, penalty);
        reconfigure(tree, 1, trials % 4 == 0 ? 20 : 16, penalty);
        consider(tree);
        if (initial_slice_rank >= 24 && trials % 8 == 7) consider(series_trial());
        ++trials;
    }
    emit(best);
    cerr << "trials=" << trials << " logwork=" << log2(best_work) << " peak=" << schedule(best) << '\n';
}
