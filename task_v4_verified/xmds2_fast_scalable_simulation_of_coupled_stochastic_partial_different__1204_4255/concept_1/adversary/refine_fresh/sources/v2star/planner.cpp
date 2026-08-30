#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;
using Cost = long long;
const Cost INF = (1LL << 55);
const auto PROCESS_START = chrono::steady_clock::now();
double elapsed() { return chrono::duration<double>(chrono::steady_clock::now() - PROCESS_START).count(); }

struct Edge { int dest, coordinate, kind; Cost cost; };
struct Request { int field, target, updates; };
struct Rep {
    int field, state;
    bool operator==(const Rep& other) const { return field == other.field && state == other.state; }
};
struct Action { int kind, field, state, coordinate; bool keep; };
struct Plan { Cost cost = 0; vector<Action> actions; };
struct Parameters { double horizon, exponent; int future_mode, route; };
struct BeamNode {
    vector<int> cache, kept, path;
    Cost cost = 0;
    double score = 0;
    int parent = -1;
};
struct CacheHash {
    size_t operator()(const vector<int>& cache) const {
        size_t value = 1234567;
        for (int rep : cache) value = (value ^ (rep + 891)) * 1099511628211ULL;
        return value;
    }
};
struct Forecast { int field, target; Cost base; double weight; };
struct SearchNode {
    vector<int> cache;
    vector<Action> actions;
    Cost cost;
    double score;
    int parent, origin;
};
struct SearchResult { vector<int> cache; vector<Action> actions; Cost cost; int parent; };

struct Planner {
    int dimensions, fields, capacity, count, states;
    vector<int> sizes;
    vector<Request> requests;
    vector<vector<Edge>> edges, reverse_edges;
    vector<vector<Cost>> distance;
    vector<vector<int>> successor;
    vector<vector<Cost>> class_distance;
    vector<vector<vector<pair<int, double>>>> future;
    vector<vector<BeamNode>> forward_layers;
    vector<vector<SearchResult>> backward_layers;
    double deadline = 1e100;

    bool expired() const { return elapsed() >= deadline; }

    bool input() {
        if (!(cin >> dimensions >> fields >> capacity >> count)) return false;
        states = (1 << dimensions) * dimensions;
        sizes.resize(fields);
        for (auto& size : sizes) cin >> size;
        Cost axis[6][6][2], transpose[6][6];
        for (int layout = 0; layout < dimensions; ++layout)
            for (int coordinate = 0; coordinate < dimensions; ++coordinate)
                cin >> axis[layout][coordinate][0] >> axis[layout][coordinate][1];
        for (int source = 0; source < dimensions; ++source)
            for (int dest = 0; dest < dimensions; ++dest) cin >> transpose[source][dest];
        class_distance.assign(2 * dimensions, vector<Cost>(2 * dimensions, INF));
        for (int source = 0; source < 2 * dimensions; ++source) {
            class_distance[source][source] = 0;
            for (int dest = 0; dest < 2 * dimensions; ++dest)
                if (source / 2 != dest / 2) class_distance[source][dest] = transpose[source / 2][dest / 2];
        }
        for (int via = 0; via < 2 * dimensions; ++via)
            for (int source = 0; source < 2 * dimensions; ++source)
                for (int dest = 0; dest < 2 * dimensions; ++dest)
                    class_distance[source][dest] = min(class_distance[source][dest], class_distance[source][via] + class_distance[via][dest]);
        requests.resize(count);
        for (auto& request : requests) {
            int mask, layout, updates;
            cin >> request.field >> mask >> layout >> updates;
            request.target = mask * dimensions + layout;
            request.updates = 0;
            for (int index = 0; index < updates; ++index) {
                int field;
                cin >> field;
                request.updates |= 1 << field;
            }
        }
        edges.resize(states);
        reverse_edges.resize(states);
        for (int source = 0; source < states; ++source) {
            int mask = source / dimensions, layout = source % dimensions;
            for (int coordinate = 0; coordinate < dimensions; ++coordinate) {
                if (coordinate == layout) continue;
                int dest = (mask ^ (1 << coordinate)) * dimensions + layout;
                if (dest) {
                    Cost weight = axis[layout][coordinate][(mask >> coordinate) & 1];
                    edges[source].push_back({dest, coordinate, 0, weight});
                    reverse_edges[dest].push_back({source, coordinate, 0, weight});
                }
                dest = mask * dimensions + coordinate;
                if (dest) {
                    Cost weight = transpose[layout][coordinate];
                    edges[source].push_back({dest, coordinate, 1, weight});
                    reverse_edges[dest].push_back({source, layout, 1, weight});
                }
            }
        }
        distance.resize(states);
        successor.resize(states);
        for (int target = 0; target < states; ++target) make_distances(target);
        return true;
    }

    void make_distances(int target) {
        if (!distance[target].empty()) return;
        auto& dist = distance[target];
        auto& next = successor[target];
        dist.assign(states, INF);
        next.assign(states, -1);
        dist[target] = 0;
        priority_queue<pair<Cost,int>, vector<pair<Cost,int>>, greater<pair<Cost,int>>> queue;
        queue.push({0, target});
        while (!queue.empty()) {
            auto [cost, current] = queue.top();
            queue.pop();
            if (cost != dist[current]) continue;
            for (auto& edge : reverse_edges[current]) {
                Cost alternative = cost + edge.cost;
                if (alternative < dist[edge.dest]) {
                    dist[edge.dest] = alternative;
                    next[edge.dest] = current;
                    if (edge.dest) queue.push({alternative, edge.dest});
                }
            }
        }
    }

    void prepare_future(Parameters param) {
        future.assign(count, vector<vector<pair<int,double>>>(fields));
        for (int position = 0; position < count; ++position) {
            int stopped = requests[position].updates;
            for (int index = position + 1; index < count; ++index) {
                auto& request = requests[index];
                if (!(stopped & (1 << request.field)) && request.target) {
                    double weight = exp(-(index - position - 1) / param.horizon);
                    if (weight > 0.001) future[position][request.field].push_back({request.target, weight});
                }
                stopped |= request.updates;
                if (stopped == (1 << fields) - 1) break;
            }
        }
    }

    double potential(const vector<Rep>& cache, int removed, int position, Rep wanted, Parameters param) {
        double value = 0;
        for (int field = 0; field < fields; ++field) {
            vector<int> sources{0};
            for (int index = 0; index < int(cache.size()); ++index)
                if (!(removed & (1 << index)) && cache[index].field == field) sources.push_back(cache[index].state);
            if (wanted.field == field) sources.push_back(wanted.state);
            double scaling = pow(double(sizes[field]), param.exponent);
            for (auto [target, weight] : future[position][field]) {
                Cost best = INF;
                for (int source : sources) best = min(best, distance[target][source]);
                value += best * weight * scaling;
                if (param.future_mode) sources.push_back(target);
            }
        }
        return value;
    }

    int evict(const vector<Rep>& cache, int required, int position, Rep wanted, Parameters param) {
        int available = int(cache.size()) - 1;
        int best_mask = 0;
        double best_score = 1e100;
        if (available <= 13) {
            int limit = 1 << available;
            vector<int> freed(limit);
            for (int mask = 1; mask < limit; ++mask) {
                int bit = __builtin_ctz(unsigned(mask));
                freed[mask] = freed[mask & (mask - 1)] + sizes[cache[bit].field];
                if (freed[mask] < required) continue;
                bool minimal = true;
                for (int index = 0; index < available; ++index)
                    if ((mask & (1 << index)) && freed[mask] - sizes[cache[index].field] >= required) { minimal = false; break; }
                if (!minimal) continue;
                double score = potential(cache, mask, position, wanted, param) + 1e-8 * freed[mask];
                if (score < best_score) { best_score = score; best_mask = mask; }
            }
        } else {
            int freed = 0;
            while (freed < required) {
                double current = potential(cache, best_mask, position, wanted, param);
                double least = 1e100;
                int victim = -1;
                for (int index = 0; index < available; ++index) {
                    if (best_mask & (1 << index)) continue;
                    double score = (potential(cache, best_mask | (1 << index), position, wanted, param) - current) / sizes[cache[index].field];
                    if (score < least) { least = score; victim = index; }
                }
                best_mask |= 1 << victim;
                freed += sizes[cache[victim].field];
            }
        }
        return best_mask;
    }

    Plan greedy(Parameters param) {
        prepare_future(param);
        Plan result;
        vector<Rep> cache;
        int memory = 0;
        for (int position = 0; position < count; ++position) {
            if (expired()) return Plan{INF, {}};
            auto& request = requests[position];
            Rep wanted{request.field, request.target};
            int source = 0;
            Cost best = distance[wanted.state][0];
            for (auto rep : cache) {
                if (rep.field == wanted.field && distance[wanted.state][rep.state] < best) {
                    best = distance[wanted.state][rep.state];
                    source = rep.state;
                }
            }
            while (source != wanted.state) {
                int dest = successor[wanted.state][source];
                Rep source_rep{wanted.field, source};
                cache.push_back({wanted.field, dest});
                memory += sizes[wanted.field];
                int removed = 0;
                if (memory > capacity || cache.size() > 13) removed = evict(cache, max(1, memory - capacity), position, wanted, param);
                bool keep = true;
                vector<Rep> remaining;
                for (int index = 0; index < int(cache.size()); ++index) {
                    auto rep = cache[index];
                    if (removed & (1 << index)) {
                        memory -= sizes[rep.field];
                        if (rep == source_rep) keep = false;
                        else result.actions.push_back({2, rep.field, rep.state, 0, false});
                    } else remaining.push_back(rep);
                }
                cache.swap(remaining);
                for (auto& edge : edges[source]) if (edge.dest == dest) {
                    result.actions.push_back({edge.kind, wanted.field, source, edge.coordinate, keep});
                    result.cost += edge.cost * sizes[wanted.field];
                    break;
                }
                source = dest;
            }
            result.actions.push_back({3, 0, 0, 0, false});
            vector<Rep> remaining;
            for (auto rep : cache) {
                if (request.updates & (1 << rep.field)) memory -= sizes[rep.field];
                else remaining.push_back(rep);
            }
            cache.swap(remaining);
        }
        return result;
    }

    Plan beam(int width, double horizon, double scale, int future_mode, int route_count = 0) {
        if (getenv("PLANNER_WIDTH")) width = atoi(getenv("PLANNER_WIDTH"));
        if (getenv("REFINE_FORWARD_WIDTH")) width = atoi(getenv("REFINE_FORWARD_WIDTH"));
        if (getenv("PLANNER_ROUTES")) route_count = atoi(getenv("PLANNER_ROUTES"));
        if (getenv("PLANNER_HORIZON")) horizon = atof(getenv("PLANNER_HORIZON"));
        if (getenv("REFINE_FORWARD_HORIZON")) horizon = atof(getenv("REFINE_FORWARD_HORIZON"));
        if (getenv("REFINE_SCALE")) scale = atof(getenv("REFINE_SCALE"));
        if (getenv("PLANNER_FUTURE")) future_mode = atoi(getenv("PLANNER_FUTURE"));
        prepare_future({horizon, 1.0, future_mode, 0});
        vector<vector<Forecast>> forecasts(count);
        for (int position = 0; position < count; ++position) {
            for (int field = 0; field < fields; ++field) {
                vector<int> earlier{0};
                for (auto [target, weight] : future[position][field]) {
                    Cost base = INF;
                    for (int source : earlier) base = min(base, distance[target][source]);
                    forecasts[position].push_back({field, target, base, weight * sizes[field]});
                    if (future_mode) {
                        earlier.push_back(target);
                        if (future_mode >= 2 && int(earlier.size()) > future_mode) earlier.erase(earlier.begin() + 1);
                    }
                }
            }
        }
        int class_count = 2 * dimensions;
        vector<uint64_t> alive(count + 1), update_mask(count);
        vector<int> requested_class(count);
        for (int position = 0; position < count; ++position) {
            auto request = requests[position];
            int layout = request.target % dimensions, mask = request.target / dimensions;
            requested_class[position] = request.field * class_count + 2 * layout + ((mask >> layout) & 1);
            for (int field = 0; field < fields; ++field)
                if (request.updates & (1 << field)) update_mask[position] |= ((1ULL << class_count) - 1) << (field * class_count);
        }
        for (int position = count - 1; position >= 0; --position) {
            alive[position] = alive[position + 1] & ~update_mask[position];
            alive[position] |= ((1ULL << class_count) - 1) << (requests[position].field * class_count);
        }
        vector<unordered_map<uint64_t, Cost>> abstract_memo(count);
        int abstract_expanded = 0;
        auto abstract_cache = [&](const vector<int>& cache) {
            uint64_t result = 0;
            for (int rep : cache) {
                int state = rep % states, layout = state % dimensions, mask = state / dimensions;
                int group = 2 * layout + ((mask >> layout) & 1);
                if (group) result |= 1ULL << (rep / states * class_count + group);
            }
            return result;
        };
        function<Cost(int,uint64_t)> abstract_value = [&](int position, uint64_t cache) -> Cost {
            if (position == count) return 0;
            cache &= alive[position];
            auto found = abstract_memo[position].find(cache);
            if (found != abstract_memo[position].end()) return found->second;
            if (abstract_expanded >= 1000000) {
                Cost cost = 0;
                for (int index = position; index < count; ++index) {
                    int target = requested_class[index], field = requests[index].field;
                    int local_target = target % class_count;
                    Cost best = class_distance[0][local_target];
                    uint64_t sources = cache & (((1ULL << class_count) - 1) << (field * class_count));
                    while (sources) {
                        int source = __builtin_ctzll(sources);
                        sources &= sources - 1;
                        best = min(best, class_distance[source % class_count][local_target]);
                    }
                    cost += best * sizes[field];
                    if (local_target) cache |= 1ULL << target;
                    cache &= ~update_mask[index];
                }
                return cost;
            }
            ++abstract_expanded;
            auto request = requests[position];
            int target = requested_class[position], local_target = target % class_count;
            Cost result;
            if (local_target == 0 || (cache & (1ULL << target))) {
                result = abstract_value(position + 1, cache & ~update_mask[position]);
            } else {
                Cost creation = class_distance[0][local_target];
                int memory = sizes[request.field];
                vector<int> entries;
                uint64_t rest = cache;
                while (rest) {
                    int entry = __builtin_ctzll(rest);
                    rest &= rest - 1;
                    entries.push_back(entry);
                    int field = entry / class_count;
                    memory += sizes[field];
                    if (field == request.field) creation = min(creation, class_distance[entry % class_count][local_target]);
                }
                uint64_t added = cache | (1ULL << target);
                if (memory <= capacity) result = abstract_value(position + 1, added & ~update_mask[position]);
                else {
                    result = INF;
                    int required = memory - capacity;
                    auto choose = [&](auto&& self, int index, int freed, uint64_t removed, int smallest) -> void {
                        if (freed >= required) {
                            if (freed - smallest >= required) return;
                            result = min(result, abstract_value(position + 1, added & ~removed & ~update_mask[position]));
                            return;
                        }
                        if (index == int(entries.size())) return;
                        self(self, index + 1, freed, removed, smallest);
                        int size = sizes[entries[index] / class_count];
                        self(self, index + 1, freed + size, removed | (1ULL << entries[index]), min(smallest, size));
                    };
                    choose(choose, 0, 0, 0, 1000000000);
                }
                result += creation * sizes[request.field];
            }
            abstract_memo[position].emplace(cache, result);
            return result;
        };
        vector<unordered_map<vector<int>,Cost,CacheHash>> rollout_memo(count);
        function<Cost(int,const vector<int>&)> rollout = [&](int position, const vector<int>& initial) -> Cost {
            if (position == count) return 0;
            auto found = rollout_memo[position].find(initial);
            if (found != rollout_memo[position].end()) return found->second;
            auto request = requests[position];
            vector<int> cache = initial;
            int memory = 0;
            for (int rep : cache) memory += sizes[rep / states];
            int source = 0;
            for (int rep : cache) if (rep / states == request.field && distance[request.target][rep % states] < distance[request.target][source]) source = rep % states;
            Cost cost = distance[request.target][source] * sizes[request.field];
            while (source != request.target) {
                int dest = successor[request.target][source];
                cache.push_back(request.field * states + dest);
                memory += sizes[request.field];
                while (memory > capacity || cache.size() > 13) {
                    vector<double> losses(cache.size());
                    for (auto forecast : forecasts[position]) {
                        Cost best = forecast.base, second = INF;
                        if (forecast.field == request.field) best = min(best, distance[forecast.target][request.target]);
                        int best_index = -1;
                        for (int index = 0; index < int(cache.size()); ++index) {
                            int rep = cache[index];
                            if (rep / states != forecast.field) continue;
                            Cost candidate = distance[forecast.target][rep % states];
                            if (candidate < best) {
                                second = best;
                                best = candidate;
                                best_index = index;
                            } else second = min(second, candidate);
                        }
                        if (best_index >= 0) losses[best_index] += (second - best) * forecast.weight;
                    }
                    int victim = 0;
                    double best_loss = 1e100;
                    for (int index = 0; index + 1 < int(cache.size()); ++index) {
                        double loss = losses[index] / sizes[cache[index] / states];
                        if (loss < best_loss) { best_loss = loss; victim = index; }
                    }
                    memory -= sizes[cache[victim] / states];
                    cache.erase(cache.begin() + victim);
                }
                source = dest;
            }
            vector<int> after;
            for (int rep : cache) if (!(request.updates & (1 << (rep / states)))) after.push_back(rep);
            sort(after.begin(), after.end());
            cost += rollout(position + 1, after);
            if (rollout_memo[position].size() < 100000) rollout_memo[position].emplace(initial, cost);
            return cost;
        };
        vector<vector<BeamNode>> layers(count + 1);
        layers[0].push_back({});
        double previous_time = elapsed(), average_time = 0;
        for (int position = 0; position < count; ++position) {
            double now = elapsed();
            if (position > 0) {
                average_time = position == 1 ? now - previous_time : 0.65 * average_time + 0.35 * (now - previous_time);
                double remaining = max(0.0, deadline - now);
                if (average_time * (count - position) > remaining * 0.9 && width > 8) {
                    int reduced = max(8, int(width * remaining * 0.75 / max(1e-9, average_time * (count - position))));
                    average_time *= double(reduced) / width;
                    width = min(width, reduced);
                    if (width <= 16) route_count = min(route_count, 2);
                }
            }
            previous_time = now;
            auto request = requests[position];
            int wanted = request.field * states + request.target;
            if (expired()) return Plan{INF, {}};
            vector<double> benefit(states);
            vector<vector<double>> gains(states);
            if (route_count && request.target && capacity >= 2 * sizes[request.field]) {
                if (getenv("PLANNER_RAW_ROUTES")) {
                    for (auto [target, weight] : future[position][request.field]) {
                        Cost base = min(distance[target][0], distance[target][request.target]);
                        for (int via = 1; via < states; ++via)
                            benefit[via] += max(Cost(0), base - distance[target][via]) * weight * sizes[request.field];
                    }
                } else {
                    for (auto forecast : forecasts[position]) if (forecast.field == request.field) {
                        Cost base = min(forecast.base, distance[forecast.target][request.target]);
                        for (int via = 1; via < states; ++via) {
                            double gain = max(Cost(0), base - distance[forecast.target][via]) * forecast.weight;
                            benefit[via] += gain;
                            gains[via].push_back(gain);
                        }
                    }
                }
            }
            vector<vector<vector<int>>> routes(states);
            auto get_routes = [&](int source) -> const vector<vector<int>>& {
                if (!routes[source].empty()) return routes[source];
                vector<pair<double,int>> waypoints;
                waypoints.push_back({-1e100, request.target});
                if (route_count) {
                    for (int via = 1; via < states; ++via) {
                        if (via == request.target || benefit[via] == 0) continue;
                        Cost extra = distance[via][source] + distance[request.target][via] - distance[request.target][source];
                        double score = extra * sizes[request.field] - benefit[via];
                        if (score < 1) waypoints.push_back({score, via});
                    }
                    sort(waypoints.begin(), waypoints.end());
                }
                for (auto [score, via] : waypoints) {
                    vector<int> path{source};
                    for (int target : {via, request.target}) {
                        while (path.back() != target) {
                            int next = successor[target][path.back()];
                            auto found = find(path.begin(), path.end(), next);
                            if (found != path.end()) path.resize(found - path.begin() + 1);
                            else path.push_back(next);
                        }
                    }
                    if (find(routes[source].begin(), routes[source].end(), path) == routes[source].end()) routes[source].push_back(move(path));
                    if (int(routes[source].size()) >= route_count + 1) break;
                }
                if (getenv("PLANNER_PAIRS") && capacity >= 3 * sizes[request.field] && !getenv("PLANNER_RAW_ROUTES")) {
                    vector<tuple<double,int,int>> pairs;
                    int limit = min(int(waypoints.size()), 18);
                    for (int first = 1; first < limit; ++first) {
                        int first_via = waypoints[first].second;
                        for (int second = 1; second < limit; ++second) {
                            if (first == second) continue;
                            int second_via = waypoints[second].second;
                            double benefit_pair = 0;
                            for (int index = 0; index < int(gains[first_via].size()); ++index)
                                benefit_pair += max(gains[first_via][index], gains[second_via][index]);
                            Cost extra = distance[first_via][source] + distance[second_via][first_via] + distance[request.target][second_via] - distance[request.target][source];
                            double score = extra * sizes[request.field] - benefit_pair;
                            if (score < 1) pairs.push_back({score, first_via, second_via});
                        }
                    }
                    sort(pairs.begin(), pairs.end());
                    int added = 0;
                    for (auto [score, first_via, second_via] : pairs) {
                        vector<int> path{source};
                        for (int target : {first_via, second_via, request.target}) {
                            while (path.back() != target) {
                                int next = successor[target][path.back()];
                                auto found = find(path.begin(), path.end(), next);
                                if (found != path.end()) path.resize(found - path.begin() + 1);
                                else path.push_back(next);
                            }
                        }
                        if (find(routes[source].begin(), routes[source].end(), path) == routes[source].end()) {
                            routes[source].push_back(move(path));
                            if (++added >= route_count) break;
                        }
                    }
                }
                if (getenv("PLANNER_ALL_SHORTEST")) {
                    vector<int> path{source};
                    int generated = 0;
                    auto generate = [&](auto&& self) -> void {
                        if (generated >= 256) return;
                        int current = path.back();
                        if (current == request.target) {
                            ++generated;
                            if (find(routes[source].begin(), routes[source].end(), path) == routes[source].end()) routes[source].push_back(path);
                            return;
                        }
                        for (auto edge : edges[current]) {
                            if (distance[request.target][current] != edge.cost + distance[request.target][edge.dest]) continue;
                            path.push_back(edge.dest);
                            self(self);
                            path.pop_back();
                        }
                    };
                    generate(generate);
                }
                return routes[source];
            };
            vector<BeamNode> candidates;
            unordered_map<vector<int>, int, CacheHash> dedup;
            auto insert = [&](vector<int> kept, const vector<int>& path, Cost cost, int parent) {
                sort(kept.begin(), kept.end());
                vector<int> after;
                for (int rep : kept) if (!(request.updates & (1 << (rep / states)))) after.push_back(rep);
                auto found = dedup.find(after);
                if (found != dedup.end()) {
                    if (cost < candidates[found->second].cost) {
                        auto& node = candidates[found->second];
                        node.cost = cost;
                        node.kept = move(kept);
                        node.path = path;
                        node.parent = parent;
                    }
                } else {
                    dedup.emplace(after, int(candidates.size()));
                    candidates.push_back({move(after), move(kept), path, cost, 0.0, parent});
                }
            };
            for (int parent = 0; parent < min(width, int(layers[position].size())); ++parent) {
                if (expired()) return Plan{INF, {}};
                const auto& node = layers[position][parent];
                if (request.target == 0 || binary_search(node.cache.begin(), node.cache.end(), wanted)) {
                    insert(node.cache, {request.target}, node.cost, parent);
                    continue;
                }
                vector<int> sources{0};
                for (int rep : node.cache) if (rep / states == request.field) sources.push_back(rep % states);
                Cost shortest = INF;
                for (int source : sources) shortest = min(shortest, distance[request.target][source]);
                for (int source : sources) {
                    if (!getenv("PLANNER_ALL_SOURCES") && distance[request.target][source] > shortest * 2 + 100) continue;
                    for (auto path : get_routes(source)) {
                    int last_cached = 0;
                    for (int index = 1; index < int(path.size()); ++index)
                        if (binary_search(node.cache.begin(), node.cache.end(), request.field * states + path[index])) last_cached = index;
                    path.erase(path.begin(), path.begin() + last_cached);
                    Cost route_cost = 0;
                    for (int index = 1; index < int(path.size()); ++index)
                        for (auto edge : edges[path[index - 1]]) if (edge.dest == path[index]) route_cost += edge.cost;
                    vector<int> pool;
                    for (int rep : node.cache) {
                        int field = rep / states;
                        if (!(request.updates & (1 << field)) && !future[position][field].empty()) pool.push_back(rep);
                    }
                    if (!(request.updates & (1 << request.field))) {
                        for (int index = 1; index + 1 < int(path.size()); ++index) pool.push_back(request.field * states + path[index]);
                    }
                    sort(pool.begin(), pool.end());
                    pool.erase(unique(pool.begin(), pool.end()), pool.end());
                    Cost cost = node.cost + route_cost * sizes[request.field];
                    int remaining = capacity - sizes[request.field];
                    vector<int> kept{wanted};
                    if (pool.size() > 17) pool.resize(17);
                    auto enumerate = [&](auto&& self, int index, int free_space, int smallest_omitted) -> void {
                        if (index == int(pool.size())) {
                            if (free_space >= smallest_omitted) return;
                            insert(kept, path, cost, parent);
                            return;
                        }
                        int size = sizes[pool[index] / states];
                        if (size <= free_space) {
                            kept.push_back(pool[index]);
                            self(self, index + 1, free_space - size, smallest_omitted);
                            kept.pop_back();
                        }
                        self(self, index + 1, free_space, min(smallest_omitted, size));
                    };
                    enumerate(enumerate, 0, remaining, 1000000000);
                    }
                }
            }
            for (auto& node : candidates) {
                double prediction = 0;
                for (auto forecast : forecasts[position]) {
                    Cost best = forecast.base;
                    for (int rep : node.cache) if (rep / states == forecast.field)
                        best = min(best, distance[forecast.target][rep % states]);
                    prediction += best * forecast.weight;
                }
                node.score = node.cost + scale * prediction;
            }
            auto compare = [](const BeamNode& left, const BeamNode& right) {
                if (left.score != right.score) return left.score < right.score;
                if (left.cost != right.cost) return left.cost < right.cost;
                return left.cache < right.cache;
            };
            if (getenv("PLANNER_ABSTRACT")) {
                int shortlist = max(256, width * 8);
                if (int(candidates.size()) > shortlist) {
                    nth_element(candidates.begin(), candidates.begin() + shortlist, candidates.end(), compare);
                    candidates.resize(shortlist);
                }
                for (auto& node : candidates) {
                    double residual = (node.score - node.cost) * 0.2;
                    node.score = node.cost + abstract_value(position + 1, abstract_cache(node.cache)) + residual;
                }
            }
            if (getenv("PLANNER_ROLLOUT")) {
                int shortlist = max(128, width * 4);
                if (int(candidates.size()) > shortlist) {
                    nth_element(candidates.begin(), candidates.begin() + shortlist, candidates.end(), compare);
                    candidates.resize(shortlist);
                }
                for (auto& node : candidates) {
                    double old_score = node.score;
                    node.score = node.cost + rollout(position + 1, node.cache) + old_score * 1e-9;
                }
            }
            if (int(candidates.size()) > width) {
                nth_element(candidates.begin(), candidates.begin() + width, candidates.end(), compare);
                candidates.resize(width);
            }
            sort(candidates.begin(), candidates.end(), compare);
            layers[position + 1] = move(candidates);
        }
        int selected = 0;
        vector<int> choices(count + 1);
        for (int position = count; position > 0; --position) {
            choices[position] = selected;
            selected = layers[position][selected].parent;
        }
        Plan result;
        result.cost = layers[count][choices[count]].cost;
        for (int position = 0; position < count; ++position) {
            const auto& before = layers[position][choices[position]].cache;
            const auto& node = layers[position + 1][choices[position + 1]];
            int field = requests[position].field;
            int source = node.path.front();
            for (int rep : before) {
                if (!binary_search(node.kept.begin(), node.kept.end(), rep) && !(rep == field * states + source && node.path.size() > 1))
                    result.actions.push_back({2, rep / states, rep % states, 0, false});
            }
            for (int index = 1; index < int(node.path.size()); ++index) {
                int dest = node.path[index];
                bool keep = source == 0 || binary_search(node.kept.begin(), node.kept.end(), field * states + source);
                for (auto edge : edges[source]) if (edge.dest == dest) {
                    result.actions.push_back({edge.kind, field, source, edge.coordinate, keep});
                    break;
                }
                source = dest;
            }
            result.actions.push_back({3, 0, 0, 0, false});
        }
        forward_layers = move(layers);
        return result;
    }

    Plan graph_beam(int width, int expansion_limit, double horizon) {
        if (getenv("PLANNER_WIDTH")) width = atoi(getenv("PLANNER_WIDTH"));
        if (getenv("PLANNER_EXPAND")) expansion_limit = atoi(getenv("PLANNER_EXPAND"));
        prepare_future({horizon, 1.0, 1, 0});
        vector<vector<SearchResult>> layers(count + 1);
        layers[0].push_back({{}, {}, 0, -1});
        for (int position = 0; position < count; ++position) {
            auto request = requests[position];
            int wanted = request.field * states + request.target;
            vector<Forecast> forecast;
            for (int field = 0; field < fields; ++field) {
                vector<int> earlier{0};
                if (field == request.field) earlier.push_back(request.target);
                for (auto [target, weight] : future[position][field]) {
                    Cost base = INF;
                    for (int source : earlier) base = min(base, distance[target][source]);
                    forecast.push_back({field, target, base, weight * sizes[field]});
                    earlier.push_back(target);
                }
            }
            auto estimate = [&](const vector<int>& cache, Cost cost) {
                Cost nearest = distance[request.target][0];
                for (int rep : cache) if (rep / states == request.field) nearest = min(nearest, distance[request.target][rep % states]);
                double score = cost + nearest * sizes[request.field];
                for (auto item : forecast) {
                    Cost best = item.base;
                    for (int rep : cache) if (rep / states == item.field) best = min(best, distance[item.target][rep % states]);
                    score += best * item.weight;
                }
                return score;
            };
            vector<SearchNode> nodes;
            unordered_map<vector<int>, int, CacheHash> visited;
            priority_queue<pair<double,int>, vector<pair<double,int>>, greater<pair<double,int>>> queue;
            unordered_map<vector<int>, int, CacheHash> goals;
            auto add = [&](vector<int> cache, vector<Action> actions, Cost cost, int parent, int origin) {
                sort(cache.begin(), cache.end());
                auto found = visited.find(cache);
                if (found != visited.end() && nodes[found->second].cost <= cost) return;
                int index = int(nodes.size());
                visited[cache] = index;
                double score = estimate(cache, cost);
                nodes.push_back({cache, move(actions), cost, score, parent, origin});
                if (request.target == 0 || binary_search(cache.begin(), cache.end(), wanted)) {
                    vector<int> after;
                    for (int rep : cache) if (!(request.updates & (1 << (rep / states)))) after.push_back(rep);
                    auto old = goals.find(after);
                    if (old == goals.end() || nodes[old->second].cost > cost) goals[move(after)] = index;
                } else queue.push({score, index});
            };
            for (int origin = 0; origin < int(layers[position].size()); ++origin) {
                const auto& previous = layers[position][origin];
                add(previous.cache, {}, previous.cost, -1, origin);
            }
            auto expand_edge = [&](const SearchNode& node, int parent, int source, Edge edge, bool only_best) {
                int destination = request.field * states + edge.dest;
                if (binary_search(node.cache.begin(), node.cache.end(), destination)) return;
                int memory = sizes[request.field];
                for (int rep : node.cache) memory += sizes[rep / states];
                int required = max(0, memory - capacity);
                vector<int> masks;
                if (required == 0 && node.cache.size() < 13) masks.push_back(0);
                else {
                    required = max(required, 1);
                    int limit = 1 << node.cache.size();
                    vector<int> freed(limit);
                    for (int mask = 1; mask < limit; ++mask) {
                        int bit = __builtin_ctz(unsigned(mask));
                        freed[mask] = freed[mask & (mask - 1)] + sizes[node.cache[bit] / states];
                        if (freed[mask] < required) continue;
                        bool minimal = true;
                        for (int index = 0; index < int(node.cache.size()); ++index)
                            if ((mask & (1 << index)) && freed[mask] - sizes[node.cache[index] / states] >= required) { minimal = false; break; }
                        if (minimal) masks.push_back(mask);
                    }
                }
                double best_score = 1e100;
                vector<int> best_cache;
                vector<Action> best_actions;
                for (int mask : masks) {
                    vector<int> cache;
                    vector<Action> actions;
                    bool keep = true;
                    for (int index = 0; index < int(node.cache.size()); ++index) {
                        int rep = node.cache[index];
                        if (mask & (1 << index)) {
                            if (rep == request.field * states + source) keep = false;
                            else actions.push_back({2, rep / states, rep % states, 0, false});
                        } else cache.push_back(rep);
                    }
                    cache.push_back(destination);
                    actions.push_back({edge.kind, request.field, source, edge.coordinate, keep});
                    Cost cost = node.cost + edge.cost * sizes[request.field];
                    if (only_best) {
                        double score = estimate(cache, cost);
                        if (score < best_score) { best_score = score; best_cache = move(cache); best_actions = move(actions); }
                    } else add(move(cache), move(actions), cost, parent, node.origin);
                }
                if (only_best && !best_cache.empty()) add(move(best_cache), move(best_actions), node.cost + edge.cost * sizes[request.field], parent, node.origin);
            };
            int expanded = 0;
            while (!queue.empty() && (expanded < expansion_limit || goals.empty())) {
                int index = queue.top().second;
                queue.pop();
                SearchNode node = nodes[index];
                if (visited[node.cache] != index) continue;
                ++expanded;
                vector<int> sources{0};
                for (int rep : node.cache) if (rep / states == request.field) sources.push_back(rep % states);
                bool forced = expanded >= expansion_limit;
                for (int source : sources) {
                    for (auto edge : edges[source]) {
                        if (forced && successor[request.target][source] != edge.dest) continue;
                        expand_edge(node, index, source, edge, forced);
                    }
                }
            }
            vector<pair<double,int>> ordered;
            for (auto& item : goals) ordered.push_back({nodes[item.second].score, item.second});
            sort(ordered.begin(), ordered.end());
            if (int(ordered.size()) > width) ordered.resize(width);
            for (auto [score, index] : ordered) {
                SearchResult result;
                result.cost = nodes[index].cost;
                result.parent = nodes[index].origin;
                for (int rep : nodes[index].cache) if (!(request.updates & (1 << (rep / states)))) result.cache.push_back(rep);
                vector<int> chain;
                while (index >= 0) { chain.push_back(index); index = nodes[index].parent; }
                reverse(chain.begin(), chain.end());
                for (int link : chain) for (auto action : nodes[link].actions) result.actions.push_back(action);
                result.actions.push_back({3, 0, 0, 0, false});
                layers[position + 1].push_back(move(result));
            }
        }
        Plan result;
        result.cost = layers[count][0].cost;
        int selected = 0;
        vector<int> choices(count + 1);
        for (int position = count; position > 0; --position) {
            choices[position] = selected;
            selected = layers[position][selected].parent;
        }
        for (int position = 1; position <= count; ++position)
            for (auto action : layers[position][choices[position]].actions) result.actions.push_back(action);
        return result;
    }

    Plan reverse_beam(int width, double horizon, int pair_count) {
        if (getenv("PLANNER_WIDTH")) width = atoi(getenv("PLANNER_WIDTH"));
        if (getenv("REFINE_REVERSE_WIDTH")) width = atoi(getenv("REFINE_REVERSE_WIDTH"));
        if (getenv("PLANNER_HORIZON")) horizon = atof(getenv("PLANNER_HORIZON"));
        if (getenv("REFINE_REVERSE_HORIZON")) horizon = atof(getenv("REFINE_REVERSE_HORIZON"));
        if (getenv("PLANNER_PAIR_COUNT")) pair_count = atoi(getenv("PLANNER_PAIR_COUNT"));
        vector<vector<vector<double>>> anchors(count + 1, vector<vector<double>>(fields, vector<double>(states)));
        for (int cut = -1; cut < count; ++cut) {
            for (int field = 0; field < fields; ++field) {
                auto& values = anchors[cut + 1][field];
                for (int state = 0; state < states; ++state) values[state] = distance[state][0];
                for (int previous = cut; previous >= 0; --previous) {
                    if (requests[previous].updates & (1 << field)) break;
                    if (requests[previous].field != field) continue;
                    double discount = 1 - exp(-(cut - previous) / horizon);
                    int target = requests[previous].target;
                    for (int state = 1; state < states; ++state)
                        values[state] = min(values[state], distance[state][target] + discount * distance[state][0]);
                }
            }
        }
        struct PrefixHint { Cost premium; vector<Cost> nearest; };
        vector<vector<PrefixHint>> hints(count + 1);
        double guide_weight = getenv("REFINE_GUIDE") ? atof(getenv("REFINE_GUIDE")) : 0.0;
        int hint_count = getenv("REFINE_GUIDE_HINTS") ? atoi(getenv("REFINE_GUIDE_HINTS")) : 8;
        if (guide_weight && !forward_layers.empty()) {
            for (int layer = 0; layer <= count; ++layer) {
                vector<pair<Cost,int>> order;
                for (int index = 0; index < int(forward_layers[layer].size()); ++index)
                    order.push_back({forward_layers[layer][index].cost, index});
                sort(order.begin(), order.end());
                int limit = min(hint_count, int(order.size()));
                for (int sample = 0; sample < limit; ++sample) {
                    int selected = sample * int(order.size()) / limit;
                    const auto& prefix = forward_layers[layer][order[selected].second];
                    PrefixHint hint{prefix.cost - order.front().first, vector<Cost>(fields * states)};
                    for (int field = 0; field < fields; ++field) {
                        for (int target = 0; target < states; ++target) {
                            Cost nearest = distance[target][0];
                            for (int rep : prefix.cache) if (rep / states == field)
                                nearest = min(nearest, distance[target][rep % states]);
                            hint.nearest[field * states + target] = nearest * sizes[field];
                        }
                    }
                    hints[layer].push_back(move(hint));
                }
            }
        }
        auto estimate = [&](const vector<int>& cache, int cut, Cost cost) {
            double score = cost;
            vector<double> best;
            vector<bool> used(cache.size());
            for (int rep : cache) best.push_back(anchors[cut + 1][rep / states][rep % states] * sizes[rep / states]);
            for (int step = 0; step < int(cache.size()); ++step) {
                int selected = -1;
                for (int index = 0; index < int(cache.size()); ++index)
                    if (!used[index] && (selected < 0 || best[index] < best[selected])) selected = index;
                score += best[selected];
                used[selected] = true;
                int source = cache[selected], field = source / states;
                for (int index = 0; index < int(cache.size()); ++index)
                    if (!used[index] && cache[index] / states == field)
                        best[index] = min(best[index], double(distance[cache[index] % states][source % states] * sizes[field]));
            }
            double reverse_scale = getenv("REFINE_REVERSE_SCALE") ? atof(getenv("REFINE_REVERSE_SCALE")) : 1.0;
            score = cost + reverse_scale * (score - cost);
            if (guide_weight && !hints[cut + 1].empty()) {
                Cost guided = INF;
                for (const auto& hint : hints[cut + 1]) {
                    array<Cost,4> field_cost{};
                    for (int rep : cache) field_cost[rep / states] = max(field_cost[rep / states], hint.nearest[rep]);
                    Cost candidate = hint.premium;
                    for (int field = 0; field < fields; ++field) candidate += field_cost[field];
                    guided = min(guided, candidate);
                }
                score = cost + (1.0 - guide_weight) * (score - cost) + guide_weight * guided;
            }
            return score;
        };
        auto inverse_path = [&](SearchResult& node, int field, int root, int target) {
            if (root == target || !binary_search(node.cache.begin(), node.cache.end(), field * states + target)) return;
            vector<int> path{root};
            while (path.back() != target) path.push_back(successor[target][path.back()]);
            for (int index = int(path.size()) - 1; index > 0; --index) {
                int source = path[index - 1], dest = path[index];
                bool keep = source == 0 || binary_search(node.cache.begin(), node.cache.end(), field * states + source);
                auto found = lower_bound(node.cache.begin(), node.cache.end(), field * states + dest);
                node.cache.erase(found);
                if (!keep) node.cache.insert(lower_bound(node.cache.begin(), node.cache.end(), field * states + source), field * states + source);
                for (auto edge : edges[source]) if (edge.dest == dest) {
                    node.actions.push_back({edge.kind, field, source, edge.coordinate, keep});
                    node.cost += edge.cost * sizes[field];
                    break;
                }
            }
        };
        vector<vector<SearchResult>> layers(count + 2);
        layers[0].push_back({{}, {}, 0, -1});
        double previous_time = elapsed(), average_time = 0;
        for (int stage = 0; stage <= count; ++stage) {
            double now = elapsed();
            if (stage > 0) {
                average_time = stage == 1 ? now - previous_time : 0.65 * average_time + 0.35 * (now - previous_time);
                double remaining = max(0.0, deadline - now);
                if (average_time * (count - stage + 1) > remaining * 0.9 && width > 8) {
                    int reduced = max(8, int(width * remaining * 0.75 / max(1e-9, average_time * (count - stage + 1))));
                    average_time *= double(reduced) / width;
                    width = min(width, reduced);
                    if (width <= 32) pair_count = min(pair_count, 4);
                }
            }
            previous_time = now;
            if (expired()) return Plan{INF, {}};
            int position = count - stage - 1;
            Request request = position >= 0 ? requests[position] : Request{0, 0, (1 << fields) - 1};
            int wanted = request.field * states + request.target;
            vector<SearchResult> pool;
            for (int parent = 0; parent < min(width, int(layers[stage].size())); ++parent) {
                const auto& before = layers[stage][parent];
                pool.push_back({before.cache, {}, before.cost, parent});
            }
            vector<SearchResult> completed;
            unordered_map<uint64_t, vector<int>> pair_roots;
            unordered_map<uint64_t, vector<int>> triple_roots;
            unordered_map<vector<int>, int, CacheHash> completed_map;
            auto append = [&](vector<SearchResult>& output, unordered_map<vector<int>, int, CacheHash>& lookup, SearchResult node) {
                auto found = lookup.find(node.cache);
                if (found == lookup.end()) {
                    lookup.emplace(node.cache, int(output.size()));
                    output.push_back(move(node));
                } else if (node.cost < output[found->second].cost) output[found->second] = move(node);
            };
            while (!pool.empty()) {
                vector<SearchResult> next_pool;
                unordered_map<vector<int>, int, CacheHash> next_map;
                for (const auto& node : pool) {
                    if (expired()) return Plan{INF, {}};
                    int memory = 0, forced_fields = 0;
                    for (int rep : node.cache) {
                        memory += sizes[rep / states];
                        if (request.updates & (1 << (rep / states))) forced_fields |= 1 << (rep / states);
                    }
                    bool present = request.target == 0 || binary_search(node.cache.begin(), node.cache.end(), wanted);
                    if (!forced_fields && (present || memory + sizes[request.field] <= capacity)) {
                        SearchResult finished = node;
                        if (!present) {
                            finished.cache.insert(lower_bound(finished.cache.begin(), finished.cache.end(), wanted), wanted);
                            if (!(request.updates & (1 << request.field))) finished.actions.push_back({2, request.field, request.target, 0, false});
                        }
                        if (position >= 0) finished.actions.push_back({3, 0, 0, 0, false});
                        append(completed, completed_map, move(finished));
                        if (!getenv("REFINE_COLLAPSE")) continue;
                        if (atoi(getenv("REFINE_COLLAPSE")) == 1 && !node.actions.empty()) continue;
                    }
                    for (int rep : node.cache) {
                        int field = rep / states, target = rep % states;
                        if (forced_fields && !(forced_fields & (1 << field))) continue;
                        vector<int> roots{0};
                        for (int other : node.cache) if (other / states == field && other != rep) roots.push_back(other % states);
                        if (!forced_fields && request.field == field && request.target) roots.push_back(request.target);
                        for (int root : roots) {
                            if (root == target) continue;
                            SearchResult changed = node;
                            inverse_path(changed, field, root, target);
                            append(next_pool, next_map, move(changed));
                        }
                    }
                    if (pair_count) {
                        for (int first = 0; first < int(node.cache.size()); ++first) {
                            int field = node.cache[first] / states;
                            if (forced_fields && !(forced_fields & (1 << field))) continue;
                            int target_first = node.cache[first] % states;
                            for (int second = first + 1; second < int(node.cache.size()); ++second) {
                                if (node.cache[second] / states != field) continue;
                                int target_second = node.cache[second] % states;
                                uint64_t pair_key = (uint64_t(field) * states + target_first) * states + target_second;
                                auto found_roots = pair_roots.find(pair_key);
                                if (found_roots == pair_roots.end()) {
                                    vector<pair<double,int>> choices;
                                    for (int root = 1; root < states; ++root) {
                                        if (root == target_first || root == target_second) continue;
                                        double score = distance[target_first][root] + distance[target_second][root] + anchors[position + 1][field][root];
                                        choices.push_back({score, root});
                                    }
                                    int limit = min(pair_count, int(choices.size()));
                                    partial_sort(choices.begin(), choices.begin() + limit, choices.end());
                                    vector<int> roots;
                                    for (int choice = 0; choice < limit; ++choice) roots.push_back(choices[choice].second);
                                    found_roots = pair_roots.emplace(pair_key, move(roots)).first;
                                }
                                for (int root : found_roots->second) {
                                    SearchResult changed = node;
                                    inverse_path(changed, field, root, target_first);
                                    inverse_path(changed, field, root, target_second);
                                    append(next_pool, next_map, move(changed));
                                }
                                if (getenv("REFINE_TRIPLES")) {
                                    int triple_count = atoi(getenv("REFINE_TRIPLES"));
                                    for (int third = second + 1; third < int(node.cache.size()); ++third) {
                                        if (node.cache[third] / states != field) continue;
                                        int target_third = node.cache[third] % states;
                                        uint64_t triple_key = pair_key * states + target_third;
                                        auto found_triples = triple_roots.find(triple_key);
                                        if (found_triples == triple_roots.end()) {
                                            vector<pair<double,int>> choices;
                                            for (int root = 1; root < states; ++root) {
                                                if (root == target_first || root == target_second || root == target_third) continue;
                                                double score = distance[target_first][root] + distance[target_second][root] + distance[target_third][root] + anchors[position + 1][field][root];
                                                choices.push_back({score, root});
                                            }
                                            int limit = min(triple_count, int(choices.size()));
                                            partial_sort(choices.begin(), choices.begin() + limit, choices.end());
                                            vector<int> roots;
                                            for (int choice = 0; choice < limit; ++choice) roots.push_back(choices[choice].second);
                                            found_triples = triple_roots.emplace(triple_key, move(roots)).first;
                                        }
                                        for (int root : found_triples->second) {
                                            SearchResult changed = node;
                                            inverse_path(changed, field, root, target_first);
                                            inverse_path(changed, field, root, target_second);
                                            inverse_path(changed, field, root, target_third);
                                            append(next_pool, next_map, move(changed));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                vector<pair<double,int>> order;
                for (int index = 0; index < int(next_pool.size()); ++index) order.push_back({estimate(next_pool[index].cache, position, next_pool[index].cost), index});
                int keep = min(width, int(order.size()));
                partial_sort(order.begin(), order.begin() + keep, order.end());
                pool.clear();
                for (int index = 0; index < keep; ++index) pool.push_back(move(next_pool[order[index].second]));
            }
            vector<pair<double,int>> order;
            for (int index = 0; index < int(completed.size()); ++index) order.push_back({estimate(completed[index].cache, max(-1, position - 1), completed[index].cost), index});
            int keep = min(width, int(order.size()));
            partial_sort(order.begin(), order.begin() + keep, order.end());
            for (int index = 0; index < keep; ++index) layers[stage + 1].push_back(move(completed[order[index].second]));
        }
        Plan result;
        result.cost = layers[count + 1][0].cost;
        vector<int> selected(count + 2);
        int choice = 0;
        for (int stage = count + 1; stage > 0; --stage) {
            selected[stage] = choice;
            choice = layers[stage][choice].parent;
        }
        for (int stage = 1; stage <= count + 1; ++stage)
            for (auto action : layers[stage][selected[stage]].actions) result.actions.push_back(action);
        reverse(result.actions.begin(), result.actions.end());
        backward_layers = move(layers);
        return result;
    }

    Plan join(Plan best) {
        if (forward_layers.empty() || backward_layers.empty()) return best;
        auto bridge = [&](vector<int> cache, const vector<int>& required, Cost bound) {
            Plan result;
            int memory = 0;
            for (int rep : cache) memory += sizes[rep / states];
            while (true) {
                int wanted = -1, source = -1;
                Cost cheapest = INF;
                for (int target : required) {
                    if (binary_search(cache.begin(), cache.end(), target)) continue;
                    int field = target / states, state = target % states;
                    Cost cost = distance[state][0];
                    int candidate_source = field * states;
                    for (int rep : cache) if (rep / states == field && distance[state][rep % states] < cost) {
                        cost = distance[state][rep % states];
                        candidate_source = rep;
                    }
                    cost *= sizes[field];
                    if (cost < cheapest) { cheapest = cost; wanted = target; source = candidate_source; }
                }
                if (wanted < 0) break;
                int field = wanted / states;
                if (result.cost + cheapest >= bound) { result.cost = INF; return result; }
                while (source != wanted) {
                    int dest = field * states + successor[wanted % states][source % states];
                    bool keep = true;
                    while (memory + sizes[field] > capacity) {
                        int victim = -1;
                        double best_loss = 1e100;
                        for (int index = 0; index < int(cache.size()); ++index) {
                            int rep = cache[index];
                            if (binary_search(required.begin(), required.end(), rep)) continue;
                            double loss = 0;
                            for (int target : required) {
                                if (target / states != rep / states || binary_search(cache.begin(), cache.end(), target)) continue;
                                int state = target % states;
                                Cost alternative = distance[state][0];
                                if (target / states == field) alternative = min({alternative, distance[state][dest % states], distance[state][wanted % states]});
                                for (int other : cache) if (other != rep && other / states == rep / states) alternative = min(alternative, distance[state][other % states]);
                                loss += max(Cost(0), alternative - distance[state][rep % states]);
                            }
                            if (loss < best_loss) { best_loss = loss; victim = index; }
                        }
                        if (victim < 0) { result.cost = INF; return result; }
                        int rep = cache[victim];
                        memory -= sizes[rep / states];
                        if (rep == source) keep = false;
                        else result.actions.push_back({2, rep / states, rep % states, 0, false});
                        cache.erase(cache.begin() + victim);
                    }
                    for (auto edge : edges[source % states]) if (edge.dest == dest % states) {
                        result.actions.push_back({edge.kind, field, source % states, edge.coordinate, keep});
                        result.cost += edge.cost * sizes[field];
                        break;
                    }
                    cache.insert(lower_bound(cache.begin(), cache.end(), dest), dest);
                    memory += sizes[field];
                    source = dest;
                }
            }
            for (int rep : cache) if (!binary_search(required.begin(), required.end(), rep)) result.actions.push_back({2, rep / states, rep % states, 0, false});
            return result;
        };
        int best_position = -1, best_forward = -1, best_reverse = -1;
        vector<Action> best_bridge;
        for (int position = 0; position < count; ++position) {
            auto& forwards = forward_layers[position + 1];
            if (expired()) break;
            auto& backwards = backward_layers[count - position];
            vector<tuple<Cost,int,int>> pairs;
            for (int prefix = 0; prefix < int(forwards.size()); ++prefix) {
                const auto& earlier = forwards[prefix];
                for (int suffix = 0; suffix < int(backwards.size()); ++suffix) {
                    const auto& later = backwards[suffix];
                    Cost cost = earlier.cost + later.cost;
                    if (cost >= best.cost) continue;
                    Cost lower = 0;
                    for (int target : later.cache) {
                        int field = target / states, state = target % states;
                        Cost nearest = distance[state][0];
                        for (int rep : earlier.kept) if (rep / states == field) nearest = min(nearest, distance[state][rep % states]);
                        lower = max(lower, nearest * sizes[field]);
                    }
                    if (cost + lower < best.cost) pairs.push_back({cost + lower, prefix, suffix});
                }
            }
            int join_limit = getenv("REFINE_JOIN_LIMIT") ? atoi(getenv("REFINE_JOIN_LIMIT")) : 128;
            int limit = min(join_limit, int(pairs.size()));
            partial_sort(pairs.begin(), pairs.begin() + limit, pairs.end());
            for (int index = 0; index < limit; ++index) {
                auto [lower, prefix, suffix] = pairs[index];
                if (lower >= best.cost) continue;
                const auto& earlier = forwards[prefix];
                const auto& later = backwards[suffix];
                Cost base = earlier.cost + later.cost;
                Plan connection = bridge(earlier.kept, later.cache, best.cost - base);
                if (base + connection.cost < best.cost) {
                    best.cost = base + connection.cost;
                    best_position = position;
                    best_forward = prefix;
                    best_reverse = suffix;
                    best_bridge = move(connection.actions);
                }
            }
        }
        if (best_position < 0) return best;
        best.actions.clear();
        vector<int> choices(best_position + 2);
        int selected = best_forward;
        for (int position = best_position + 1; position > 0; --position) {
            choices[position] = selected;
            selected = forward_layers[position][selected].parent;
        }
        for (int position = 0; position <= best_position; ++position) {
            const auto& before = forward_layers[position][choices[position]].cache;
            const auto& node = forward_layers[position + 1][choices[position + 1]];
            int field = requests[position].field, source = node.path.front();
            for (int rep : before)
                if (!binary_search(node.kept.begin(), node.kept.end(), rep) && !(rep == field * states + source && node.path.size() > 1))
                    best.actions.push_back({2, rep / states, rep % states, 0, false});
            for (int index = 1; index < int(node.path.size()); ++index) {
                int dest = node.path[index];
                bool keep = source == 0 || binary_search(node.kept.begin(), node.kept.end(), field * states + source);
                for (auto edge : edges[source]) if (edge.dest == dest) {
                    best.actions.push_back({edge.kind, field, source, edge.coordinate, keep});
                    break;
                }
                source = dest;
            }
            if (position < best_position) best.actions.push_back({3, 0, 0, 0, false});
        }
        for (auto action : best_bridge) best.actions.push_back(action);
        vector<int> reverse_choices(count - best_position + 1);
        selected = best_reverse;
        for (int stage = count - best_position; stage > 0; --stage) {
            reverse_choices[stage] = selected;
            selected = backward_layers[stage][selected].parent;
        }
        vector<Action> suffix_actions;
        for (int stage = 1; stage <= count - best_position; ++stage)
            for (auto action : backward_layers[stage][reverse_choices[stage]].actions) suffix_actions.push_back(action);
        reverse(suffix_actions.begin(), suffix_actions.end());
        for (auto action : suffix_actions) best.actions.push_back(action);
        return best;
    }

    Plan baseline() {
        Plan result;
        vector<int> cache;
        int memory = 0;
        for (int position = 0; position < count; ++position) {
            auto request = requests[position];
            int source = 0;
            for (int rep : cache) if (rep / states == request.field) {
                int state = rep % states;
                if (make_pair(distance[request.target][state], state) < make_pair(distance[request.target][source], source)) source = state;
            }
            while (source != request.target) {
                int dest = successor[request.target][source];
                bool keep = true;
                while (memory + sizes[request.field] > capacity) {
                    tuple<int,int,int> priority{-1,-1,-1};
                    int victim = -1;
                    for (int index = 0; index < int(cache.size()); ++index) {
                        int rep = cache[index], next = count + 1;
                        for (int future = position + 1; future < count; ++future) {
                            auto later = requests[future];
                            if (later.field * states + later.target == rep) { next = future - position - 1; break; }
                            if (later.updates & (1 << (rep / states))) break;
                        }
                        auto value = make_tuple(next, sizes[rep / states], rep);
                        if (value > priority) { priority = value; victim = index; }
                    }
                    int rep = cache[victim];
                    memory -= sizes[rep / states];
                    if (rep == request.field * states + source) keep = false;
                    else result.actions.push_back({2, rep / states, rep % states, 0, false});
                    cache.erase(cache.begin() + victim);
                }
                for (auto edge : edges[source]) if (edge.dest == dest) {
                    result.actions.push_back({edge.kind, request.field, source, edge.coordinate, keep});
                    result.cost += edge.cost * sizes[request.field];
                    break;
                }
                cache.push_back(request.field * states + dest);
                memory += sizes[request.field];
                source = dest;
            }
            result.actions.push_back({3, 0, 0, 0, false});
            vector<int> remaining;
            for (int rep : cache) {
                if (request.updates & (1 << (rep / states))) memory -= sizes[rep / states];
                else remaining.push_back(rep);
            }
            cache.swap(remaining);
        }
        return result;
    }

    bool valid(const Plan& plan) const {
        if (plan.actions.size() > 100000) return false;
        vector<bool> exists(fields * states);
        for (int field = 0; field < fields; ++field) exists[field * states] = true;
        Cost cost = 0;
        int memory = 0, position = 0;
        for (auto action : plan.actions) {
            if (action.kind == 3) {
                if (position == count) return false;
                auto request = requests[position++];
                if (!exists[request.field * states + request.target]) return false;
                for (int field = 0; field < fields; ++field) if (request.updates & (1 << field))
                    for (int state = 1; state < states; ++state) if (exists[field * states + state]) {
                        exists[field * states + state] = false;
                        memory -= sizes[field];
                    }
                continue;
            }
            int field = action.field, source = action.state;
            if (field < 0 || field >= fields || source < 0 || source >= states || !exists[field * states + source]) return false;
            if (action.kind == 2) {
                if (source == 0) return false;
                exists[field * states + source] = false;
                memory -= sizes[field];
                continue;
            }
            int dest = -1;
            Cost weight = 0;
            for (auto edge : edges[source]) if (edge.kind == action.kind && edge.coordinate == action.coordinate) {
                dest = edge.dest;
                weight = edge.cost;
                break;
            }
            if (dest <= 0 || exists[field * states + dest]) return false;
            if (!action.keep) {
                if (source == 0) return false;
                exists[field * states + source] = false;
                memory -= sizes[field];
            }
            exists[field * states + dest] = true;
            memory += sizes[field];
            cost += weight * sizes[field];
            if (memory > capacity) return false;
        }
        return position == count && cost == plan.cost;
    }

    Plan solve() {
        Plan best;
        best.cost = INF;
        const char* setting = getenv("PLANNER_MODE");
        int mode = setting ? atoi(setting) : -1;
        if (mode == 26) {
            double budget = getenv("REFINE_BUDGET") ? atof(getenv("REFINE_BUDGET")) : 3.6;
            double finish = min(110.0, elapsed() + budget);
            deadline = finish;
            Plan selected = baseline();
            auto consider = [&](Plan candidate) {
                if (candidate.cost < selected.cost && valid(candidate)) selected = move(candidate);
            };
            for (auto param : vector<Parameters>{{2,1,0,0}, {5,1,1,0}, {12,0,1,0}, {12,1,1,0}, {30,1,0,0}}) {
                if (expired()) break;
                consider(greedy(param));
            }
            double fraction = getenv("REFINE_REVERSE_FRACTION") ? atof(getenv("REFINE_REVERSE_FRACTION")) : 0.65;
            deadline = min(finish, elapsed() + budget * fraction);
            if (!expired()) consider(reverse_beam(512, 40.0, 8));
            deadline = finish;
            if (!expired()) consider(beam(128, 8.0, 1.0, 1, 5));
            if (!expired()) consider(join(selected));
            return selected;
        }
        if (mode == 27) {
            double budget = getenv("REFINE_BUDGET") ? atof(getenv("REFINE_BUDGET")) : 3.4;
            double finish = min(110.0, elapsed() + budget);
            Plan selected = baseline();
            auto consider = [&](Plan candidate) {
                if (candidate.cost < selected.cost && valid(candidate)) selected = move(candidate);
            };
            deadline = min(finish, elapsed() + 0.30 * budget);
            if (!expired()) consider(beam(48, 8.0, 1.0, 1, 5));
            deadline = finish;
            if (!expired()) consider(reverse_beam(256, 40.0, 8));
            if (!expired()) consider(join(selected));
            return selected;
        }
        if (mode < 0) {
            double start = elapsed();
            double budget = min(1.5, max(0.0, 100.0 - start) / 50.0);
            double finish = start + budget;
            deadline = finish;
            Plan best = baseline();
            auto consider = [&](Plan candidate) {
                if (candidate.cost < best.cost && valid(candidate)) best = move(candidate);
            };
            for (auto param : vector<Parameters>{{2,1,0,0}, {5,1,1,0}, {12,0,1,0}, {12,1,1,0}, {30,1,0,0}}) {
                if (elapsed() >= finish) break;
                consider(greedy(param));
            }
            if (capacity <= 12 * *min_element(sizes.begin(), sizes.end())) {
                deadline = min(finish, elapsed() + budget * 0.55);
                if (!expired()) consider(reverse_beam(192, 40.0, 8));
                deadline = finish;
                if (!expired()) consider(beam(48, 8.0, 1.0, 1, 5));
                if (!expired()) consider(join(best));
            }
            return best;
        }
        if (mode == 23) return graph_beam(32, 2000, 8.0);
        if (mode == 24) return reverse_beam(128, 8.0, 4);
        if (mode == 25) {
            Plan forward = beam(64, 8.0, 1.0, 1, 5);
            Plan backward = reverse_beam(256, 40.0, 8);
            Plan best = forward.cost < backward.cost ? move(forward) : move(backward);
            if (getenv("PLANNER_STATS")) cerr << "before join " << best.cost << '\n';
            return join(move(best));
        }
        vector<Parameters> params;
        for (int future_mode : {0, 1})
            for (double horizon : {2.0, 5.0, 12.0, 30.0})
                for (double exponent : {0.0, 1.0}) params.push_back({horizon, exponent, future_mode, 0});
        for (int index = 0; index < int(params.size()); ++index) {
            if (mode >= 0 && mode != index) continue;
            Plan candidate = greedy(params[index]);
            if (getenv("PLANNER_STATS")) cerr << index << ':' << candidate.cost << ' ';
            if (candidate.cost < best.cost) best = move(candidate);
        }
        if (mode < 0 || mode >= 16) {
            int index = 16;
            for (auto config : vector<array<double,5>>{{64, 8, 1, 1, 0}, {64, 15, 1, 0, 0}, {128, 8, 2, 1, 0}, {128, 4, 0, 1, 0}, {64, 8, 1, 1, 5}, {64, 15, 1, 0, 5}, {64, 8, 2, 1, 5}}) {
                if (mode < 0 || mode == index) {
                    Plan candidate = beam(int(config[0]), config[1], config[2], int(config[3]), int(config[4]));
                    if (getenv("PLANNER_STATS")) cerr << index << ':' << candidate.cost << ' ';
                    if (candidate.cost < best.cost) best = move(candidate);
                }
                ++index;
            }
        }
        if (getenv("PLANNER_STATS")) cerr << '\n';
        return best;
    }

    void output(const Plan& plan) {
        cout << "{\"actions\":[";
        bool first = true;
        for (auto& action : plan.actions) {
            if (!first) cout << ',';
            first = false;
            if (action.kind == 3) { cout << "[\"read\"]"; continue; }
            string kind = action.kind == 0 ? "axis" : action.kind == 1 ? "transpose" : "drop";
            cout << "[\"" << kind << "\"," << action.field << ',' << action.state / dimensions << ',' << action.state % dimensions;
            if (action.kind != 2) cout << ',' << action.coordinate << ',' << (action.keep ? "true" : "false");
            cout << ']';
        }
        cout << "]}" << endl;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    while (true) {
        Planner planner;
        if (!planner.input()) break;
        planner.output(planner.solve());
    }
}
