#define NO_MAIN
#include "search.cpp"

using Wide = unsigned __int128;

struct Candidate {
    Wide key;
    long long area;
    double score;
    int peak, live, time, parent, node;
};

struct Trace {
    int parent;
    int node;
};

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
    double liveWeight = argc > 5 ? stod(argv[5]) : 0.5;
    double areaWeight = argc > 6 ? stod(argv[6]) : 0.000025;
    int cap = argc > 7 ? stoi(argv[7]) : 100000;
    State baseline(graph); baseline.reset(graph.baseline, {});
    vector<double> futureAverage(graph.count + 1, 0);
    long long tailArea = 0, tailTime = 0;
    for (int index = graph.count - 1; index >= 0; --index) {
        int node = graph.baseline[index];
        tailArea += (long long)baseline.footprint[index] * graph.duration[node];
        tailTime += graph.duration[node]; futureAverage[index] = (double)tailArea / tailTime;
    }
    int tableSize = 1;
    while (tableSize < beamWidth * 64) tableSize *= 2;
    vector<int> table(tableSize, -1);
    vector<Candidate> states, candidates;
    states.push_back({((Wide)1 << 40) - 1, 0, 0, 0, 0, 0, -1, -1});
    vector<vector<Trace>> traces;
    traces.reserve(graph.count);
    candidates.reserve(beamWidth * 24);
    auto started = chrono::steady_clock::now();
    for (int step = 0; step < graph.count; ++step) {
        fill(table.begin(), table.end(), -1); candidates.clear();
        for (int parent = 0; parent < (int)states.size(); ++parent) {
            const Candidate& state = states[parent];
            Wide ready = state.key & ~(state.key >> 1) & (((Wide)1 << 79) - 1);
            while (ready) {
                uint64_t bottom = (uint64_t)ready;
                int bit = bottom ? __builtin_ctzll(bottom) : 64 + __builtin_ctzll((uint64_t)(ready >> 64));
                Wide mask = (Wide)1 << bit;
                ready ^= mask;
                Wide below = state.key & (mask - 1);
                int rank = __builtin_popcountll((uint64_t)below) + __builtin_popcountll((uint64_t)(below >> 64));
                int node = grid[39 - rank][bit - rank];
                int footprint = state.live + graph.height[node];
                int peak = max(state.peak, footprint);
                if (peak > cap) continue;
                long long area = state.area + (long long)graph.duration[node] * footprint;
                Wide key = state.key ^ (mask * 3);
                int live = state.live + graph.delta[node];
                int time = state.time + graph.duration[node];
                double score = peak + liveWeight * live + areaWeight * (area - time * futureAverage[step + 1]);
                uint64_t hashed = mix((uint64_t)key ^ mix((uint64_t)(key >> 64)));
                int slot = hashed & (tableSize - 1);
                while (table[slot] >= 0 && candidates[table[slot]].key != key) slot = (slot + 1) & (tableSize - 1);
                if (table[slot] < 0) {
                    table[slot] = candidates.size();
                    candidates.push_back({key, area, score, peak, live, time, parent, node});
                } else {
                    Candidate& previous = candidates[table[slot]];
                    if (score < previous.score) previous = {key, area, score, peak, live, time, parent, node};
                }
            }
        }
        if (candidates.empty()) { cerr << "FAILED at " << step << '\n'; return 2; }
        auto compare = [](const Candidate& first, const Candidate& second) { return first.score < second.score; };
        if ((int)candidates.size() > beamWidth) {
            nth_element(candidates.begin(), candidates.begin() + beamWidth, candidates.end(), compare);
            candidates.resize(beamWidth);
        }
        states.swap(candidates);
        traces.emplace_back(); traces.back().reserve(states.size());
        for (const Candidate& state : states) traces.back().push_back({state.parent, state.node});
        if (step % 100 == 99) {
            const Candidate& state = *min_element(states.begin(), states.end(), compare);
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - started).count();
            cerr << step + 1 << " states " << states.size() << " peak " << state.peak << " area " << state.area << " live " << state.live << " time " << elapsed << '\n';
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
