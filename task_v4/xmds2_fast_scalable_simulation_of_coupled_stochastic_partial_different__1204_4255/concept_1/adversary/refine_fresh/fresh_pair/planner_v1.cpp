#include <algorithm>
#include <array>
#include <cmath>
#include <ctime>
#include <iostream>
#include <limits>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;
using Cost = long long;
constexpr int INF = 1000000000;
struct Timeout {};
struct Request { int field, node, updates; };
struct Action { int kind, field, node, coordinate; bool keep; };
struct History { int parent; vector<Action> actions; };
struct State { vector<int> cache; Cost cost; int history; double rank; };
struct Candidate { vector<int> cache; Cost cost; int parent; vector<int> route, retained; double rank; };
struct Forecast { int target, base; double weight; };
struct VectorHash {
    size_t operator()(const vector<int>& values) const {
        size_t result = 1469598103934665603ULL;
        for (int value : values) result = (result ^ (value + 1)) * 1099511628211ULL;
        return result;
    }
};

struct Planner {
    int dimensions, fields, capacity, length, count;
    int width = 160, paths = 2, heuristic_mode = 0;
    double factor = 0.75, decay = 0.60;
    clock_t deadline;
    Cost best_cost = 0;
    unsigned long enumerations = 0;
    vector<int> sizes;
    vector<vector<array<int,2>>> axis;
    vector<vector<int>> transpose, distance, successor;
    vector<vector<pair<int,int>>> edges;
    vector<Request> requests;
    vector<History> history;
    vector<vector<pair<int,double>>> future;
    vector<vector<int>> future_base;
    vector<vector<Forecast>> forecast;
    vector<vector<double>> benefit;
    vector<vector<vector<int>>> routes;
    vector<State> beam;
    vector<Candidate> candidates;
    unordered_map<vector<int>, int, VectorHash> lookup;
    int position;
    double threshold;
    bool read() {
        if (!(cin >> dimensions >> fields >> capacity >> length)) return false;
        count = (1 << dimensions) * dimensions;
        sizes.resize(fields);
        for (int &value : sizes) cin >> value;
        axis.assign(dimensions, vector<array<int,2>>(dimensions));
        for (auto &row : axis) for (auto &pair : row) cin >> pair[0] >> pair[1];
        transpose.assign(dimensions, vector<int>(dimensions));
        for (auto &row : transpose) for (int &value : row) cin >> value;
        requests.resize(length);
        for (auto &request : requests) {
            int mask, layout;
            cin >> request.field >> mask >> layout >> request.updates;
            request.node = mask * dimensions + layout;
        }
        return true;
    }
    void graph() {
        distance.assign(count, vector<int>(count, INF));
        successor.assign(count, vector<int>(count, -1));
        edges.assign(count, {});
        for (int node = 0; node < count; ++node) {
            distance[node][node] = 0;
            int mask = node / dimensions, layout = node % dimensions;
            for (int coordinate = 0; coordinate < dimensions; ++coordinate) {
                if (coordinate == layout) continue;
                int destination = (mask ^ (1 << coordinate)) * dimensions + layout;
                if (destination) {
                    distance[node][destination] = axis[layout][coordinate][(mask >> coordinate) & 1];
                    successor[node][destination] = destination;
                    edges[node].push_back({destination, axis[layout][coordinate][(mask >> coordinate) & 1]});
                }
                destination = mask * dimensions + coordinate;
                if (destination) {
                    distance[node][destination] = transpose[layout][coordinate];
                    successor[node][destination] = destination;
                    edges[node].push_back({destination, transpose[layout][coordinate]});
                }
            }
        }
        for (int middle = 1; middle < count; ++middle)
            for (int source = 0; source < count; ++source) {
                if (distance[source][middle] == INF) continue;
                for (int target = 1; target < count; ++target) {
                    int alternative = distance[source][middle] + distance[middle][target];
                    if (alternative < distance[source][target]) {
                        distance[source][target] = alternative;
                        successor[source][target] = successor[source][middle];
                    }
                }
            }
    }
    vector<int> path(int source, int target) {
        vector<int> result{source};
        while (source != target) {
            source = successor[source][target];
            if (source < 0 || result.size() > size_t(count)) return {};
            result.push_back(source);
        }
        return result;
    }
    int edge_cost(int source, int destination) {
        if (source % dimensions != destination % dimensions) return transpose[source%dimensions][destination%dimensions];
        int coordinate = __builtin_ctz((source/dimensions) ^ (destination/dimensions));
        return axis[source%dimensions][coordinate][((source/dimensions)>>coordinate)&1];
    }
    pair<Cost,vector<Action>> baseline_plan(int start = 0, const vector<int>& initial = {}) {
        vector<int> cached = initial;
        for (int field = 0; field < fields; ++field) cached.push_back(field*count);
        vector<vector<int>> distances(count), next(count);
        vector<Action> result;
        int memory = 0;
        for (int key : initial) memory += sizes[key/count];
        Cost cost = 0;
        for (int stage = start; stage < length; ++stage) {
            const auto &request = requests[stage];
            int wanted = request.field*count+request.node;
            if (find(cached.begin(),cached.end(),wanted) == cached.end()) {
                if (distances[request.node].empty()) {
                    auto &values = distances[request.node];
                    auto &successors = next[request.node];
                    values.assign(count,INF); successors.assign(count,-1);
                    values[request.node] = 0;
                    priority_queue<pair<int,int>,vector<pair<int,int>>,greater<pair<int,int>>> queue;
                    queue.push({0,request.node});
                    while (!queue.empty()) {
                        auto [value,node] = queue.top(); queue.pop();
                        if (values[node] != value) continue;
                        int mask = node/dimensions, layout = node%dimensions;
                        for (int coordinate = 0; coordinate < dimensions; ++coordinate) {
                            if (coordinate == layout) continue;
                            int previous_mask = mask^(1<<coordinate);
                            array<pair<int,int>,2> previous{{{previous_mask*dimensions+layout,axis[layout][coordinate][(previous_mask>>coordinate)&1]},
                                                          {mask*dimensions+coordinate,transpose[coordinate][layout]}}};
                            for (auto [source,weight] : previous) {
                                if (value+weight >= values[source]) continue;
                                values[source] = value+weight; successors[source] = node;
                                if (source) queue.push({value+weight,source});
                            }
                        }
                    }
                }
                int source = -1;
                for (int key : cached) if (key/count == request.field) {
                    if (source < 0 || make_pair(distances[request.node][key%count],key) < make_pair(distances[request.node][source%count],source)) source = key;
                }
                while (source != wanted) {
                    int destination = request.field*count+next[request.node][source%count];
                    bool keep = true;
                    while (memory+sizes[request.field] > capacity) {
                        int victim = -1, farthest = -1;
                        for (int key : cached) {
                            if (!(key%count)) continue;
                            int next_use = length+1;
                            for (int later = stage+1; later < length; ++later) {
                                if (requests[later].field*count+requests[later].node == key) { next_use = later-stage-1; break; }
                                if ((requests[later].updates >> (key/count)) & 1) break;
                            }
                            if (victim < 0 || make_tuple(next_use,sizes[key/count],key) > make_tuple(farthest,sizes[victim/count],victim)) {
                                victim = key; farthest = next_use;
                            }
                        }
                        cached.erase(find(cached.begin(),cached.end(),victim));
                        memory -= sizes[victim/count];
                        if (victim == source) keep = false;
                        else result.push_back({2,victim/count,victim%count,0,false});
                    }
                    int source_node = source%count, next_node = destination%count;
                    if (source_node%dimensions == next_node%dimensions)
                        result.push_back({0,request.field,source_node,__builtin_ctz((source_node/dimensions)^(next_node/dimensions)),keep});
                    else result.push_back({1,request.field,source_node,next_node%dimensions,keep});
                    cost += Cost(sizes[request.field])*edge_cost(source_node,next_node);
                    memory += sizes[request.field]; cached.push_back(destination); source = destination;
                }
            }
            result.push_back({3,0,0,0,false});
            cached.erase(remove_if(cached.begin(),cached.end(),[&](int key) {
                if (!(key%count) || !((request.updates >> (key/count)) & 1)) return false;
                memory -= sizes[key/count]; return true;
            }),cached.end());
        }
        return {cost,result};
    }
    void prepare() {
        future.assign(fields, {});
        future_base.assign(fields, {});
        forecast.assign(fields, {});
        benefit.assign(fields, vector<double>(count));
        int updates = requests[position].updates;
        for (int field = 0; field < fields; ++field) {
            if ((updates >> field) & 1) continue;
            double weight = 1.0;
            for (int later = position + 1; later < length; ++later) {
                const auto &request = requests[later];
                if (request.field == field && request.node) {
                    int base = distance[0][request.node];
                    if (heuristic_mode) {
                        for (auto [earlier, earlier_weight] : future[field]) base = min(base, distance[earlier][request.node]);
                    }
                    future[field].push_back({request.node, weight * pow(0.985, later-position-1)});
                    future_base[field].push_back(base);
                    weight *= decay;
                    if (weight < 0.025) break;
                }
                if ((request.updates >> field) & 1) break;
            }
            for (int node = 1; node < count; ++node)
                for (auto [target, weight] : future[field])
                    benefit[field][node] += weight * max(0, distance[0][target] - distance[node][target]);
        }
        for (int field = 0; field < fields; ++field) {
            vector<pair<int,double>> combined;
            vector<int> raw_index(count,-1), forecast_index(count,-1);
            for (int offset = 0; offset < int(future[field].size()); ++offset) {
                auto [target, weight] = future[field][offset];
                if (raw_index[target] < 0) { raw_index[target] = combined.size(); combined.push_back({target,weight}); }
                else combined[raw_index[target]].second += weight;
                int base = future_base[field][offset];
                if (!base) continue;
                if (forecast_index[target] < 0) { forecast_index[target] = forecast[field].size(); forecast[field].push_back({target,base,weight}); }
                else forecast[field][forecast_index[target]].weight += weight;
            }
            future[field] = move(combined);
        }
        routes.assign(count, {});
    }
    void build_routes(int source) {
        if (!routes[source].empty()) return;
        const auto &request = requests[position];
        routes[source].push_back(path(source, request.node));
        if (paths <= 1 || capacity < 2 * sizes[request.field]) return;
        vector<pair<double,int>> hubs;
        for (int node = 1; node < count; ++node) {
            if (node == source || node == request.node) continue;
            int detour = distance[source][node] + distance[node][request.node] - distance[source][request.node];
            double reward = 0;
            for (auto [target, weight] : future[request.field]) {
                int initial = min({distance[0][target], distance[source][target], distance[request.node][target]});
                reward += weight * max(0, initial - distance[node][target]);
            }
            double score = reward - 1.3 * detour;
            if (score > 0) hubs.push_back({-score, node});
        }
        sort(hubs.begin(), hubs.end());
        for (auto [score, hub] : hubs) {
            auto first = path(source, hub), second = path(hub, request.node);
            first.insert(first.end(), second.begin()+1, second.end());
            auto sorted = first;
            sort(sorted.begin(), sorted.end());
            if (adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) continue;
            if (find(routes[source].begin(), routes[source].end(), first) != routes[source].end()) continue;
            routes[source].push_back(move(first));
            if (int(routes[source].size()) >= paths) break;
        }
    }
    double heuristic(const vector<int>& cache) {
        double result = 0;
        int begin = 0, end = 0;
        for (int field = 0; field < fields; ++field) {
            begin = end;
            while (end < int(cache.size()) && cache[end] < (field+1)*count) ++end;
            for (const auto &look : forecast[field]) {
                int best = look.base;
                for (int index = begin; index < end; ++index)
                    best = min(best, distance[cache[index]-field*count][look.target]);
                result += best*sizes[field]*look.weight;
            }
        }
        return result;
    }
    void add(const vector<int>& retained, Cost cost, int parent, const vector<int>& route) {
        vector<int> cache;
        int updates = requests[position].updates;
        for (int key : retained) if (!((updates >> (key/count)) & 1)) cache.push_back(key);
        sort(cache.begin(), cache.end());
        auto found = lookup.find(cache);
        if (found != lookup.end() && candidates[found->second].cost <= cost) return;
        double rank = cost + factor * heuristic(cache);
        if (rank > threshold) return;
        Candidate candidate{cache,cost,parent,route,retained,rank};
        if (found != lookup.end()) candidates[found->second] = move(candidate);
        else {
            lookup.emplace(cache, candidates.size());
            candidates.push_back(move(candidate));
        }
    }
    void enumerate(const vector<int>& optional, int offset, int room, vector<int>& retained,
                   Cost cost, int parent, const vector<int>& route, int excluded_min) {
        if ((++enumerations & 2047) == 0 && clock() > deadline) throw Timeout{};
        int remaining = 0;
        for (int index = offset; index < int(optional.size()); ++index) remaining += sizes[optional[index]/count];
        if (remaining <= room) {
            if (excluded_min > room-remaining) {
                auto result = retained;
                result.insert(result.end(),optional.begin()+offset,optional.end());
                add(result,cost,parent,route);
            }
            return;
        }
        if (offset == int(optional.size())) {
            if (excluded_min > room) add(retained, cost, parent, route);
            return;
        }
        int key = optional[offset], size = sizes[key/count];
        if (size <= room) {
            retained.push_back(key);
            enumerate(optional,offset+1,room-size,retained,cost,parent,route,excluded_min);
            retained.pop_back();
        }
        enumerate(optional,offset+1,room,retained,cost,parent,route,min(excluded_min,size));
    }

    void retain_greedily(const vector<int>& optional, int room, vector<int> retained,
                         Cost cost, int parent, const vector<int>& route) {
        int wanted = retained[0];
        retained.insert(retained.end(),optional.begin(),optional.end());
        sort(retained.begin(),retained.end());
        for (int key : optional) room -= sizes[key/count];
        while (room < 0) {
            vector<double> loss(retained.size());
            for (int field = 0; field < fields; ++field) {
                for (const auto &look : forecast[field]) {
                    int best = look.base, second = best, chosen = -1;
                    for (int offset = 0; offset < int(retained.size()); ++offset) {
                        int key = retained[offset];
                        if (key/count != field) continue;
                        int value = distance[key%count][look.target];
                        if (value < best) { second = best; best = value; chosen = offset; }
                        else if (value < second) second = value;
                    }
                    if (chosen >= 0) loss[chosen] += (second-best)*sizes[field]*look.weight;
                }
            }
            int victim = -1;
            for (int offset = 0; offset < int(retained.size()); ++offset) {
                if (retained[offset] == wanted) continue;
                loss[offset] /= sizes[retained[offset]/count];
                if (victim < 0 || loss[offset] < loss[victim]) victim = offset;
            }
            room += sizes[retained[victim]/count];
            retained.erase(retained.begin()+victim);
        }
        for (int key : optional) {
            if (sizes[key/count] <= room && !binary_search(retained.begin(),retained.end(),key)) {
                retained.push_back(key); sort(retained.begin(),retained.end());
                room -= sizes[key/count];
            }
        }
        add(retained,cost,parent,route);
    }
    void expand(const State& state, int parent) {
        const auto &request = requests[position];
        int wanted = request.field * count + request.node;
        if (!request.node || binary_search(state.cache.begin(), state.cache.end(), wanted)) {
            add(state.cache, state.cost, parent, {});
            return;
        }
        vector<int> sources{0};
        for (int key : state.cache) if (key / count == request.field) sources.push_back(key % count);
        if (sources.size() > 8) {
            sort(sources.begin()+1,sources.end(),[&](int left,int right) {
                return make_pair(distance[left][request.node],left) < make_pair(distance[right][request.node],right);
            });
            sources.resize(8);
        }
        unordered_set<vector<int>,VectorHash> seen;
        for (int source : sources) {
          build_routes(source);
          for (const auto &full_route : routes[source]) {
            int start = 0;
            for (int offset = 1; offset < int(full_route.size()); ++offset)
                if (binary_search(state.cache.begin(),state.cache.end(),request.field*count+full_route[offset])) start = offset;
            vector<int> route(full_route.begin()+start,full_route.end());
            if (!seen.insert(route).second) continue;
            Cost cost = state.cost;
            for (int offset = 1; offset < int(route.size()); ++offset)
                cost += Cost(sizes[request.field]) * edge_cost(route[offset-1],route[offset]);
            vector<int> optional = state.cache;
            for (int node : route) if (node) optional.push_back(request.field*count+node);
            sort(optional.begin(),optional.end());
            optional.erase(unique(optional.begin(),optional.end()),optional.end());
            optional.erase(remove_if(optional.begin(),optional.end(),[&](int key) {
                return key == wanted || ((request.updates >> (key/count)) & 1) || benefit[key/count][key%count] == 0;
            }), optional.end());
            vector<int> retained{wanted};
            int required = 0;
            for (int key : optional) required += sizes[key/count];
            if (required <= capacity-sizes[request.field]) {
                retained.insert(retained.end(),optional.begin(),optional.end());
                add(retained,cost,parent,route);
            } else if (optional.size() > 13)
                retain_greedily(optional,capacity-sizes[request.field],retained,cost,parent,route);
            else enumerate(optional,0,capacity-sizes[request.field],retained,cost,parent,route,INF);
        }
      }
    }
    vector<Action> actions(const State& state, const Candidate& candidate) {
        vector<Action> result;
        unordered_set<int> retained(candidate.retained.begin(),candidate.retained.end());
        const auto &request = requests[position];
        int source = candidate.route.empty() ? -1 : request.field * count + candidate.route[0];
        for (int key : state.cache) if (!retained.count(key) && key != source)
            result.push_back({2,key/count,key%count,0,false});
        for (int offset = 1; offset < int(candidate.route.size()); ++offset) {
            int previous = candidate.route[offset-1], next = candidate.route[offset];
            bool keep = !previous || retained.count(request.field*count+previous);
            if (previous % dimensions == next % dimensions) {
                int coordinate = __builtin_ctz((previous/dimensions) ^ (next/dimensions));
                result.push_back({0,request.field,previous,coordinate,keep});
            } else result.push_back({1,request.field,previous,next%dimensions,keep});
        }
        result.push_back({3,0,0,0,false});
        return result;
    }
    vector<Action> solve() {
        if (distance.empty()) graph();
        history.clear(); beam.clear(); enumerations = 0;
        history.push_back({-1,{}});
        beam.push_back({{},0,0,0});
        if (capacity / *min_element(sizes.begin(),sizes.end()) > 12) width = min(width,12);
        try {
          for (position = 0; position < length; ++position) {
            if (clock() > deadline) throw Timeout{};
            if (clock() > deadline-clock_t(0.12*CLOCKS_PER_SEC)) { width = min(width,8); paths = 1; }
            if (beam.size() > size_t(width)) beam.resize(width);
            prepare();
            candidates.clear(); lookup.clear(); threshold = numeric_limits<double>::infinity();
            for (int parent = 0; parent < int(beam.size()); ++parent) {
                if (clock() > deadline) throw Timeout{};
                expand(beam[parent],parent);
                if (candidates.size() > size_t(width*20)) {
                    vector<double> ranks;
                    for (const auto &candidate : candidates) ranks.push_back(candidate.rank);
                    nth_element(ranks.begin(),ranks.begin()+width*4,ranks.end());
                    threshold = ranks[width*4];
                }
            }
            sort(candidates.begin(),candidates.end(),[](const Candidate& left,const Candidate& right) {
                if (left.rank != right.rank) return left.rank < right.rank;
                if (left.cost != right.cost) return left.cost < right.cost;
                return left.cache < right.cache;
            });
            if (candidates.size() > size_t(width)) candidates.resize(width);
            vector<State> next;
            for (const auto &candidate : candidates) {
                history.push_back({beam[candidate.parent].history,actions(beam[candidate.parent],candidate)});
                next.push_back({candidate.cache,candidate.cost,int(history.size())-1,candidate.rank});
            }
            beam = move(next);
          }
        } catch (const Timeout&) {
        }
        const auto &best = *min_element(beam.begin(),beam.end(),[&](const State& left,const State& right){
            return position == length ? left.cost < right.cost : left.rank < right.rank;
        });
        best_cost = best.cost;
        vector<int> chain;
        for (int index = best.history; index > 0; index = history[index].parent) chain.push_back(index);
        vector<Action> result;
        for (auto iterator = chain.rbegin(); iterator != chain.rend(); ++iterator)
            result.insert(result.end(),history[*iterator].actions.begin(),history[*iterator].actions.end());
        if (position < length) {
            auto tail = baseline_plan(position,best.cache);
            best_cost += tail.first;
            result.insert(result.end(),tail.second.begin(),tail.second.end());
        }
        return result;
    }
    void output(const vector<Action>& actions) {
        cout << "{\"actions\":[";
        bool comma = false;
        for (const auto &action : actions) {
            if (comma) cout << ',';
            comma = true;
            if (action.kind == 3) { cout << "[\"read\"]"; continue; }
            cout << "[\"" << (action.kind == 0 ? "axis" : action.kind == 1 ? "transpose" : "drop")
                 << "\"," << action.field << ',' << action.node/dimensions << ',' << action.node%dimensions;
            if (action.kind != 2) cout << ',' << action.coordinate << ',' << (action.keep ? "true" : "false");
            cout << ']';
        }
        cout << "]}\n" << flush;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    while (true) {
        Planner planner;
        if (!planner.read()) break;
        clock_t started = clock();
        auto best = planner.baseline_plan();
        planner.deadline = started+clock_t(1.05*CLOCKS_PER_SEC);
        int total_size = 0, cheapest = INF, most_expensive = 0;
        for (int size : planner.sizes) total_size += size;
        for (int layout = 0; layout < planner.dimensions; ++layout)
            for (int coordinate = 0; coordinate < planner.dimensions; ++coordinate)
                if (layout != coordinate) for (int cost : planner.axis[layout][coordinate]) {
                    cheapest = min(cheapest,cost); most_expensive = max(most_expensive,cost);
                }
        bool spacious = planner.capacity >= 2*total_size;
        bool anisotropic = most_expensive >= 5*cheapest;
        for (int pass = 0; pass < 4; ++pass) {
            double elapsed = double(clock()-started)/CLOCKS_PER_SEC;
            if (pass && elapsed > 0.88) break;
            planner.width = pass == 3 ? 160 : 80;
            planner.paths = pass == 0 || pass == 3 ? 2 : 3;
            planner.factor = pass == 3 ? 0.5 : 1.0;
            planner.decay = pass == 1 ? 0.8 : pass == 2 ? 0.9 : 0.6;
            planner.heuristic_mode = pass == 2 ? 1 : 0;
            if (spacious && pass < 2) {
                planner.width = pass == 0 ? 90 : 80;
                planner.paths = pass == 0 ? 3 : 2;
                planner.decay = pass == 0 ? 0.8 : 0.6;
            } else if (anisotropic && (pass == 1 || pass == 2)) {
                planner.decay = pass == 1 ? 0.9 : 0.8;
                planner.heuristic_mode = pass == 1 ? 1 : 0;
            }
            try {
                auto answer = planner.solve();
                if (planner.best_cost < best.first) best = {planner.best_cost,move(answer)};
            } catch (const Timeout&) { break; }
        }
        planner.output(best.second);
    }
}
