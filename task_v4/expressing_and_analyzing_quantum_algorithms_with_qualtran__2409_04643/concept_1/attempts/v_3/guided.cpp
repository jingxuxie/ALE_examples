#define NO_MAIN
#include "search.cpp"

using Wide = unsigned __int128;

struct TreeNode {
    int left = 0, right = 0, refs = 0, peak = -100000000;
    int lazy = 0, duration = 0;
    long long area = 0;
};

struct Trees {
    vector<TreeNode> nodes;
    vector<int> available;
    Trees() { nodes.emplace_back(); nodes.reserve(4000000); }
    int create(const TreeNode& node) {
        int index;
        if (available.empty()) { index = nodes.size(); nodes.push_back(node); }
        else { index = available.back(); available.pop_back(); nodes[index] = node; }
        nodes[index].refs = 1;
        if (node.left) ++nodes[node.left].refs;
        if (node.right) ++nodes[node.right].refs;
        return index;
    }
    void release(int index) {
        if (!index || --nodes[index].refs) return;
        release(nodes[index].left); release(nodes[index].right);
        available.push_back(index);
    }
    int retain(int index) { if (index) ++nodes[index].refs; return index; }
    int initialize(const State& state, int lower, int upper) {
        TreeNode node;
        if (upper - lower == 1) {
            node.peak = state.footprint[lower]; node.duration = state.graph.duration[state.order[lower]];
            node.area = (long long)node.peak * node.duration;
            return create(node);
        }
        int middle = (lower + upper) / 2;
        node.left = initialize(state, lower, middle); node.right = initialize(state, middle, upper);
        node.peak = max(nodes[node.left].peak, nodes[node.right].peak);
        node.duration = nodes[node.left].duration + nodes[node.right].duration;
        node.area = nodes[node.left].area + nodes[node.right].area;
        int result = create(node);
        release(node.left); release(node.right);
        return result;
    }
    int add(int index, int delta) {
        if (!index || !delta) return retain(index);
        TreeNode node = nodes[index];
        node.lazy += delta; node.peak += delta; node.area += (long long)delta * node.duration;
        return create(node);
    }
    int execute(int index, int lower, int upper, int position, int delta) {
        if (!index) return 0;
        if (upper - lower == 1) return 0;
        TreeNode node = nodes[index];
        int middle = (lower + upper) / 2;
        int left, right;
        if (position < middle) {
            left = execute(node.left, lower, middle, position, delta);
            right = retain(node.right);
        } else {
            left = add(node.left, delta);
            right = execute(node.right, middle, upper, position, delta);
        }
        node.left = left; node.right = right;
        node.duration = nodes[left].duration + nodes[right].duration;
        if (!node.duration) { release(left); release(right); return 0; }
        node.peak = max(nodes[left].peak, nodes[right].peak) + node.lazy;
        node.area = nodes[left].area + nodes[right].area + (long long)node.lazy * node.duration;
        int result = create(node);
        release(left); release(right);
        return result;
    }
};

struct Candidate {
    Wide key;
    long long area;
    double score;
    int peak, live, root, parent, node;
};

struct Trace { int parent, node; };

uint64_t mix(uint64_t value) {
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

int main(int argc, char** argv) {
    Graph graph(argv[1]);
    ifstream gridInput(argv[2]);
    int grid[40][40];
    for (auto& row : grid) for (int& node : row) gridInput >> node;
    string output = argv[3];
    int beamWidth = stoi(argv[4]);
    vector<int> reference = graph.baseline;
    if (argc > 5) { ifstream input(argv[5]); for (int& node : reference) input >> node; }
    double liveWeight = argc > 6 ? stod(argv[6]) : 0;
    State baseline(graph); baseline.reset(graph.baseline, {});
    State schedule(graph); schedule.reset(reference, {});
    Trees trees;
    int initialRoot = trees.initialize(schedule, 0, graph.count);
    int tableSize = 1;
    while (tableSize < beamWidth * 64) tableSize *= 2;
    vector<int> table(tableSize, -1);
    vector<Candidate> states, candidates;
    states.push_back({((Wide)1 << 40) - 1, 0, 0, 0, 0, initialRoot, -1, -1});
    vector<vector<Trace>> traces;
    traces.reserve(graph.count); candidates.reserve(beamWidth * 24);
    auto started = chrono::steady_clock::now();
    for (int step = 0; step < graph.count; ++step) {
        fill(table.begin(), table.end(), -1); candidates.clear();
        for (int parent = 0; parent < (int)states.size(); ++parent) {
            const Candidate& state = states[parent];
            Wide ready = state.key & ~(state.key >> 1) & (((Wide)1 << 79) - 1);
            while (ready) {
                uint64_t bottom = (uint64_t)ready;
                int bit = bottom ? __builtin_ctzll(bottom) : 64 + __builtin_ctzll((uint64_t)(ready >> 64));
                Wide mask = (Wide)1 << bit; ready ^= mask;
                Wide below = state.key & (mask - 1);
                int rank = __builtin_popcountll((uint64_t)below) + __builtin_popcountll((uint64_t)(below >> 64));
                int node = grid[39 - rank][bit - rank];
                int footprint = state.live + graph.height[node];
                int peak = max(state.peak, footprint);
                if (peak * 20 > baseline.peak * 21) continue;
                long long area = state.area + (long long)graph.duration[node] * footprint;
                Wide key = state.key ^ (mask * 3);
                int live = state.live + graph.delta[node];
                uint64_t hashed = mix((uint64_t)key ^ mix((uint64_t)(key >> 64)));
                int slot = hashed & (tableSize - 1);
                while (table[slot] >= 0 && candidates[table[slot]].key != key) slot = (slot + 1) & (tableSize - 1);
                int root;
                bool fresh = table[slot] < 0;
                if (fresh) root = trees.execute(state.root, 0, graph.count, schedule.position[node], graph.delta[node]);
                else root = candidates[table[slot]].root;
                const TreeNode& completion = trees.nodes[root];
                double score = 0.7 * log((double)max(peak, completion.peak) / baseline.peak) +
                               0.3 * log((double)(area + completion.area) / baseline.area) +
                               liveWeight * live / baseline.peak;
                if (fresh) {
                    table[slot] = candidates.size();
                    candidates.push_back({key, area, score, peak, live, root, parent, node});
                } else if (score < candidates[table[slot]].score) {
                    candidates[table[slot]] = {key, area, score, peak, live, root, parent, node};
                }
            }
        }
        for (const Candidate& state : states) trees.release(state.root);
        if (candidates.empty()) { cerr << "FAILED at " << step << '\n'; return 2; }
        auto compare = [](const Candidate& first, const Candidate& second) { return first.score < second.score; };
        if ((int)candidates.size() > beamWidth) {
            nth_element(candidates.begin(), candidates.begin() + beamWidth, candidates.end(), compare);
            for (int index = beamWidth; index < (int)candidates.size(); ++index) trees.release(candidates[index].root);
            candidates.resize(beamWidth);
        }
        states.swap(candidates);
        traces.emplace_back(); traces.back().reserve(states.size());
        for (const Candidate& state : states) traces.back().push_back({state.parent, state.node});
        if (step % 100 == 99) {
            const Candidate& state = *min_element(states.begin(), states.end(), compare);
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - started).count();
            cerr << step + 1 << " states " << states.size() << " peak " << state.peak << " area " << state.area
                 << " expectedRatio " << exp(-state.score) << " time " << elapsed << " pool " << trees.nodes.size() << '\n';
        }
    }
    int index = 0;
    vector<int> order(graph.count);
    for (int step = graph.count - 1; step >= 0; --step) {
        order[step] = traces[step][index].node; index = traces[step][index].parent;
    }
    State result(graph); result.reset(order, {});
    ofstream outputFile(output);
    for (int node : order) outputFile << node << ' ';
    outputFile << '\n';
    cerr << "FINAL " << result.peak << ' ' << result.area << " ratio " << exp(0.7*log((double)baseline.peak/result.peak)+0.3*log((double)baseline.area/result.area)) << '\n';
}
