#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using namespace std;

struct Graph {
    int count;
    vector<int> duration, workspace, delta, height, baseline;
    vector<vector<int>> pred, succ;
    explicit Graph(const string& path) {
        ifstream input(path);
        int edges;
        input >> count >> edges;
        duration.resize(count); workspace.resize(count); delta.assign(count, 0);
        height.resize(count); pred.resize(count); succ.resize(count); baseline.resize(count);
        for (int node = 0; node < count; ++node) input >> duration[node] >> workspace[node];
        for (int edge = 0; edge < edges; ++edge) {
            int source, dest, width;
            input >> source >> dest >> width;
            succ[source].push_back(dest); pred[dest].push_back(source);
            delta[source] += width; delta[dest] -= width;
        }
        for (int node = 0; node < count; ++node) height[node] = max(0, delta[node]) + workspace[node];
        for (int& node : baseline) input >> node;
    }
};

struct State {
    const Graph& graph;
    vector<int> order, position, live, footprint, histogram;
    long long area = 0;
    int peak = 0;
    double smooth = 0;
    explicit State(const Graph& input): graph(input), histogram(200000, 0) {}
    void reset(const vector<int>& schedule, const vector<double>& potential) {
        order = schedule; position.resize(graph.count); live.resize(graph.count); footprint.resize(graph.count);
        fill(histogram.begin(), histogram.end(), 0);
        area = 0; peak = 0; smooth = 0;
        int width = 0;
        for (int index = 0; index < graph.count; ++index) {
            int node = order[index]; position[node] = index; live[index] = width;
            int value = width + graph.height[node];
            footprint[index] = value; ++histogram[value];
            peak = max(peak, value); area += (long long)graph.duration[node] * value;
            if (!potential.empty()) smooth += potential[value];
            width += graph.delta[node];
        }
    }
};

#ifndef NO_MAIN
int main(int argc, char** argv) {
    if (argc < 5) return 1;
    Graph graph(argv[1]);
    string output = argv[2];
    double seconds = stod(argv[3]);
    mt19937_64 random(stoull(argv[4]));
    double power = argc > 5 ? stod(argv[5]) : 24;
    double highTemp = argc > 6 ? stod(argv[6]) : 0.0001;
    double cycleTime = argc > 7 ? stod(argv[7]) : 20;
    vector<double> potential(200000);
    State current(graph);
    current.reset(graph.baseline, {});
    int baselinePeak = current.peak;
    long long baselineArea = current.area;
    for (int width = 0; width < (int)potential.size(); ++width) potential[width] = pow((double)width / baselinePeak, power);
    vector<int> best = graph.baseline;
    if (argc > 8) {
        ifstream input(argv[8]);
        for (int& node : best) input >> node;
    }
    current.reset(best, potential);
    auto trueScore = [&](int peak, long long area) {
        return 0.7 * log((double)peak / baselinePeak) + 0.3 * log((double)area / baselineArea);
    };
    auto energy = [&](double smooth, long long area) {
        return 0.7 / power * log(max(smooth, 1e-100) / graph.count) + 0.3 * log((double)area / baselineArea);
    };
    double bestScore = trueScore(current.peak, current.area);
    double currentEnergy = energy(current.smooth, current.area);
    int bestPeak = current.peak;
    long long bestArea = current.area;
    auto save = [&]() {
        ofstream result(output);
        for (int node : best) result << node << ' ';
        result << '\n';
    };
    save();
    auto started = chrono::steady_clock::now();
    long long iterations = 0, accepted = 0;
    int cycle = -1;
    double elapsed = 0, temperature = highTemp;
    while (true) {
        if (iterations % 8192 == 0) {
            elapsed = chrono::duration<double>(chrono::steady_clock::now() - started).count();
            if (elapsed >= seconds) break;
            int newCycle = (int)(elapsed / cycleTime);
            if (newCycle != cycle) {
                cycle = newCycle;
                if (cycle > 0 && cycle % 3 != 2) current.reset(best, potential);
                currentEnergy = energy(current.smooth, current.area);
                cerr << "cycle " << cycle << " time " << elapsed << " iterations " << iterations
                     << " accepted " << accepted << " best " << bestPeak << ' ' << bestArea
                     << " ratio " << exp(-bestScore) << '\n';
            }
            double phase = elapsed / cycleTime - cycle;
            temperature = highTemp * pow(0.0005, phase);
        }
        ++iterations;
        int source = random() % graph.count;
        int node = current.order[source];
        int lower = 0, upper = graph.count - 1;
        for (int parent : graph.pred[node]) lower = max(lower, current.position[parent] + 1);
        for (int child : graph.succ[node]) upper = min(upper, current.position[child] - 1);
        if (upper <= lower) continue;
        int dest;
        uint64_t kind = random() % 8;
        if (kind == 0) dest = source + (random() % 2 ? 1 : -1);
        else if (kind == 1) dest = random() % 2 ? lower : upper;
        else dest = lower + random() % (upper - lower + 1);
        if (dest == source || dest < lower || dest > upper) continue;
        int begin = min(source, dest), end = max(source, dest);
        int width = current.live[begin];
        long long areaChange = 0;
        double smoothChange = 0;
        for (int index = begin; index <= end; ++index) {
            int moved;
            if (source < dest) moved = index == end ? node : current.order[index + 1];
            else moved = index == begin ? node : current.order[index - 1];
            int value = width + graph.height[moved];
            smoothChange += potential[value] - potential[current.footprint[index]];
            areaChange += (long long)graph.duration[moved] * value - (long long)graph.duration[current.order[index]] * current.footprint[index];
            width += graph.delta[moved];
        }
        double proposedEnergy = energy(current.smooth + smoothChange, current.area + areaChange);
        if (proposedEnergy <= currentEnergy || (double)(random() >> 11) * 0x1.0p-53 < exp((currentEnergy - proposedEnergy) / temperature)) {
            ++accepted;
            currentEnergy = proposedEnergy;
            current.smooth += smoothChange; current.area += areaChange;
            for (int index = begin; index <= end; ++index) --current.histogram[current.footprint[index]];
            if (source < dest) rotate(current.order.begin() + source, current.order.begin() + source + 1, current.order.begin() + dest + 1);
            else rotate(current.order.begin() + dest, current.order.begin() + source, current.order.begin() + source + 1);
            width = current.live[begin];
            for (int index = begin; index <= end; ++index) {
                int moved = current.order[index]; current.position[moved] = index; current.live[index] = width;
                int value = width + graph.height[moved]; current.footprint[index] = value;
                ++current.histogram[value]; current.peak = max(current.peak, value);
                width += graph.delta[moved];
            }
            while (!current.histogram[current.peak]) --current.peak;
            double score = trueScore(current.peak, current.area);
            if (score < bestScore && current.peak * 20 <= baselinePeak * 21) {
                bestScore = score; bestPeak = current.peak; bestArea = current.area; best = current.order;
                save();
            }
        }
    }
    save();
    cerr << "FINAL " << bestPeak << ' ' << bestArea << " ratio " << exp(-bestScore) << " iterations " << iterations << '\n';
}
#endif
