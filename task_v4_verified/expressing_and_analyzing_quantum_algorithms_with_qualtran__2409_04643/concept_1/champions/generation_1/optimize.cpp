#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <numeric>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace std;

struct Measurement {
    int peak = 0;
    long long area = 0;
    double score = 0;
};

struct Graph {
    string name;
    int count, edge_count, baseline_peak;
    long long baseline_area;
    vector<int> duration, workspace, incoming, outgoing, delta, extra;
    vector<vector<int>> predecessors, successors, seeds;

    Measurement measure(const vector<int>& order) const {
        Measurement result;
        int live = 0;
        for (int node : order) {
            int footprint = live + extra[node];
            result.peak = max(result.peak, footprint);
            result.area += static_cast<long long>(duration[node]) * footprint;
            live += delta[node];
        }
        result.score = 0.7 * log(result.peak) + 0.3 * log(result.area);
        return result;
    }
};

mutex output_mutex;

void write_order(const Graph& graph, const vector<int>& order, const string& directory) {
    ofstream output(directory + "/" + graph.name + ".txt");
    for (int node : order) output << node << ' ';
    output << '\n';
}

vector<int> random_dfs(const Graph& graph, mt19937_64& rng) {
    vector<double> priorities(graph.count);
    for (double& priority : priorities) priority = generate_canonical<double, 53>(rng);
    vector<int> order;
    vector<bool> seen(graph.count, false);
    function<void(int)> visit = [&](int node) {
        if (seen[node]) return;
        seen[node] = true;
        vector<int> parents = graph.predecessors[node];
        sort(parents.begin(), parents.end(), [&](int first, int second) {return priorities[first] < priorities[second];});
        for (int parent : parents) visit(parent);
        order.push_back(node);
    };
    vector<int> sinks;
    for (int node = 0; node < graph.count; ++node) {
        if (graph.successors[node].empty()) sinks.push_back(node);
    }
    shuffle(sinks.begin(), sinks.end(), rng);
    for (int node : sinks) visit(node);
    return order;
}

void solve(const Graph& graph, double seconds, int seed, const string& directory) {
    mt19937_64 rng(seed);
    auto start_time = chrono::steady_clock::now();
    vector<int> best_order = graph.seeds[0];
    Measurement best = graph.measure(best_order);
    for (const auto& candidate : graph.seeds) {
        Measurement current = graph.measure(candidate);
        if (current.score < best.score && current.peak * 20 <= graph.baseline_peak * 21) {
            best = current;
            best_order = candidate;
        }
    }
    ifstream existing(directory + "/" + graph.name + ".txt");
    if (existing) {
        vector<int> candidate(graph.count);
        for (int& node : candidate) existing >> node;
        if (existing) {
            Measurement current = graph.measure(candidate);
            if (current.score < best.score && current.peak * 20 <= graph.baseline_peak * 21) {
                best = current;
                best_order = candidate;
            }
        }
    }
    write_order(graph, best_order, directory);
    vector<int> positions(graph.count);
    long long iterations = 0;
    int cycle = 0;
    while (chrono::duration<double>(chrono::steady_clock::now() - start_time).count() < seconds) {
        vector<int> order;
        if (cycle % 7 == 5) order = graph.seeds[rng() % graph.seeds.size()];
        else if (cycle % 7 == 6) order = random_dfs(graph, rng);
        else order = best_order;
        Measurement current = graph.measure(order);
        for (int index = 0; index < graph.count; ++index) positions[order[index]] = index;
        int cycle_length = 150000;
        double initial_temperature = cycle % 3 == 0 ? 0.008 : cycle % 3 == 1 ? 0.025 : 0.0025;
        for (int iteration = 0; iteration < cycle_length; ++iteration) {
            if (iteration % 4096 == 0 && chrono::duration<double>(chrono::steady_clock::now() - start_time).count() >= seconds) break;
            ++iterations;
            int length = 1;
            if (rng() % 5 == 0) length = 2 + rng() % 7;
            else if (rng() % 12 == 0) length = 8 + rng() % min(80, graph.count / 3);
            int first = rng() % (graph.count - length + 1);
            int end = first + length;
            bool right = rng() % 2;
            int target;
            if (right) {
                int upper = graph.count;
                for (int index = first; index < end; ++index) {
                    for (int successor : graph.successors[order[index]]) {
                        if (positions[successor] >= end) upper = min(upper, positions[successor]);
                    }
                }
                upper -= length;
                if (upper <= first) continue;
                int distance = 1 + rng() % (upper - first);
                if (rng() % 3 == 0) distance = min(distance, 1 + int(rng() % 6));
                target = first + distance;
                rotate(order.begin() + first, order.begin() + end, order.begin() + target + length);
            } else {
                int lower = 0;
                for (int index = first; index < end; ++index) {
                    for (int predecessor : graph.predecessors[order[index]]) {
                        if (positions[predecessor] < first) lower = max(lower, positions[predecessor] + 1);
                    }
                }
                if (lower >= first) continue;
                int distance = 1 + rng() % (first - lower);
                if (rng() % 3 == 0) distance = min(distance, 1 + int(rng() % 6));
                target = first - distance;
                rotate(order.begin() + target, order.begin() + first, order.begin() + end);
            }
            Measurement proposed = graph.measure(order);
            double temperature = initial_temperature * exp(-7.0 * iteration / cycle_length);
            double difference = proposed.score - current.score;
            bool accept = difference <= 0 || generate_canonical<double, 53>(rng) < exp(-difference / temperature);
            if (accept) {
                current = proposed;
                for (int index = min(first, target); index < max(first, target) + length; ++index) positions[order[index]] = index;
                if (current.score + 1e-12 < best.score && current.peak * 20 <= graph.baseline_peak * 21) {
                    best = current;
                    best_order = order;
                    write_order(graph, best_order, directory);
                }
            } else {
                if (right) rotate(order.begin() + first, order.begin() + target, order.begin() + target + length);
                else rotate(order.begin() + target, order.begin() + target + length, order.begin() + end);
            }
        }
        ++cycle;
    }
    lock_guard<mutex> lock(output_mutex);
    double ratio = exp(0.7 * log(double(graph.baseline_peak) / best.peak) + 0.3 * log(double(graph.baseline_area) / best.area));
    cout << graph.name << " peak " << best.peak << " area " << best.area << " ratio " << ratio << " iterations " << iterations << " cycles " << cycle << endl;
}

int main(int argc, char** argv) {
    double seconds = argc > 1 ? stod(argv[1]) : 20.0;
    int seed = argc > 2 ? stoi(argv[2]) : 12873;
    string directory = argc > 3 ? argv[3] : "results";
    ifstream input("graphs.txt");
    int total;
    input >> total;
    vector<Graph> graphs(total);
    for (Graph& graph : graphs) {
        input >> graph.name >> graph.count >> graph.edge_count >> graph.baseline_peak >> graph.baseline_area;
        graph.duration.resize(graph.count);
        graph.workspace.resize(graph.count);
        graph.incoming.resize(graph.count);
        graph.outgoing.resize(graph.count);
        graph.delta.resize(graph.count);
        graph.extra.resize(graph.count);
        graph.predecessors.resize(graph.count);
        graph.successors.resize(graph.count);
        for (int node = 0; node < graph.count; ++node) input >> graph.duration[node] >> graph.workspace[node];
        for (int edge = 0; edge < graph.edge_count; ++edge) {
            int source, destination, width;
            input >> source >> destination >> width;
            graph.predecessors[destination].push_back(source);
            graph.successors[source].push_back(destination);
            graph.incoming[destination] += width;
            graph.outgoing[source] += width;
        }
        for (int node = 0; node < graph.count; ++node) {
            graph.delta[node] = graph.outgoing[node] - graph.incoming[node];
            graph.extra[node] = max(0, graph.delta[node]) + graph.workspace[node];
        }
        int seed_count;
        input >> seed_count;
        graph.seeds.resize(seed_count, vector<int>(graph.count));
        for (auto& order : graph.seeds) for (int& node : order) input >> node;
    }
    atomic<int> next(0);
    vector<thread> workers;
    for (int worker = 0; worker < 4; ++worker) {
        workers.emplace_back([&]() {
            while (true) {
                int index = next++;
                if (index >= total) return;
                solve(graphs[index], seconds, seed + index * 7171, directory);
            }
        });
    }
    for (auto& worker : workers) worker.join();
}
