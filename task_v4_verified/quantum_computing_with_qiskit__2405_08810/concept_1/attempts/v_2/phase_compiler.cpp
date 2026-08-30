#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <queue>
#include <random>
#include <unordered_map>
#include <utility>
#include <vector>

using Mask = uint32_t;
using Clock = std::chrono::steady_clock;

struct Edge {
    int control;
    int target;
    int weight;
    int duration;
    double price;
};

struct Operation {
    int kind;
    int first;
    int second;
};

struct Settings {
    double factor = 1.0;
    double weighted = 0.0;
    double exponent = 0.5;
    double bonus = 1.0;
    double noise = 0.1;
    double dynamic_noise = 0.0;
    double fallback_gain = 0.18;
    int term_candidates = 8;
    int rollback = 0;
    int lookahead = 0;
    double potential_power = 1.0;
    double prior_power = 0.0;
    double steiner = 0.0;
};

struct Engine {
    int size;
    int count;
    std::vector<Edge> edges;
    std::vector<Mask> terms;
    std::array<std::vector<int>, 28> incoming;
    std::array<std::array<int, 28>, 28> edge_index;
    std::array<std::array<double, 28>, 28> distances;
    std::array<std::array<double, 28>, 28> weighted_distances;
    std::array<std::array<Mask, 28>, 28> path_vertices;
    std::vector<Mask> metric_keys;
    std::vector<std::array<double, 3>> metric_values;
    size_t metric_size = 0;
    std::mt19937 randomizer;
    Clock::time_point deadline;
    std::array<int, 3> stats{};
    std::vector<int> last_history;

    Engine(int qubits, int edge_count, const int* edge_data,
           int term_count, const uint32_t* term_data)
        : size(qubits), count(term_count), terms(term_data, term_data + term_count), randomizer(12345) {
        for (int vertex = 0; vertex < size; ++vertex) {
            edge_index[vertex].fill(-1);
            for (int other = 0; other < size; ++other) {
                distances[vertex][other] = vertex == other ? 0 : 1e9;
                weighted_distances[vertex][other] = vertex == other ? 0 : 1e9;
            }
        }
        for (int index = 0; index < edge_count; ++index) {
            const int* data = edge_data + 4 * index;
            edges.push_back({data[0], data[1], data[2], data[3], data[2] + 0.15 * data[3]});
            incoming[data[1]].push_back(index);
            edge_index[data[0]][data[1]] = index;
            distances[data[0]][data[1]] = 1;
            double price = data[2] + 0.15 * data[3];
            weighted_distances[data[0]][data[1]] = std::min(weighted_distances[data[0]][data[1]], price);
            weighted_distances[data[1]][data[0]] = std::min(weighted_distances[data[1]][data[0]], price);
        }
        double average = 0;
        int links = 0;
        for (int first = 0; first < size; ++first) {
            for (int second = 0; second < first; ++second) {
                if (edge_index[first][second] >= 0) {
                    average += weighted_distances[first][second];
                    ++links;
                }
            }
        }
        average /= links;
        for (int first = 0; first < size; ++first) {
            for (int second = 0; second < size; ++second) {
                weighted_distances[first][second] /= average;
            }
        }
        for (int middle = 0; middle < size; ++middle) {
            for (int first = 0; first < size; ++first) {
                for (int second = 0; second < size; ++second) {
                    distances[first][second] = std::min(distances[first][second], distances[first][middle] + distances[middle][second]);
                    weighted_distances[first][second] = std::min(weighted_distances[first][second], weighted_distances[first][middle] + weighted_distances[middle][second]);
                }
            }
        }
        for (int source = 0; source < size; ++source) {
            path_vertices[source].fill(0);
            path_vertices[source][source] = Mask(1) << source;
            std::vector<int> queue{source};
            for (size_t offset = 0; offset < queue.size(); ++offset) {
                int vertex = queue[offset];
                for (int index : incoming[vertex]) {
                    int neighbor = edges[index].control;
                    if (!path_vertices[source][neighbor]) {
                        path_vertices[source][neighbor] = path_vertices[source][vertex] | (Mask(1) << neighbor);
                        queue.push_back(neighbor);
                    }
                }
            }
        }
        metric_keys.resize(1 << 21);
        metric_values.resize(1 << 21);
    }

    double random_unit() {
        return double(randomizer()) / double(std::mt19937::max());
    }

    double mst(Mask mask, const std::array<std::array<double, 28>, 28>& distance, Mask* nodes = nullptr) const {
        int root = __builtin_ctz(mask);
        std::array<int, 28> parent;
        if (nodes) {
            parent.fill(root);
            *nodes = Mask(1) << root;
        }
        mask &= mask - 1;
        std::array<double, 28> nearest = distance[root];
        double total = 0;
        while (mask) {
            int closest = -1;
            double price = 1e12;
            Mask rest = mask;
            while (rest) {
                int vertex = __builtin_ctz(rest);
                rest &= rest - 1;
                if (nearest[vertex] < price) {
                    price = nearest[vertex];
                    closest = vertex;
                }
            }
            total += price;
            if (nodes) {
                *nodes |= path_vertices[parent[closest]][closest];
            }
            mask ^= Mask(1) << closest;
            rest = mask;
            while (rest) {
                int vertex = __builtin_ctz(rest);
                rest &= rest - 1;
                if (distance[closest][vertex] < nearest[vertex]) {
                    nearest[vertex] = distance[closest][vertex];
                    if (nodes) {
                        parent[vertex] = closest;
                    }
                }
            }
        }
        return total;
    }

    double metric(Mask mask, const Settings& settings) {
        int cardinality = __builtin_popcount(mask) - 1;
        if (cardinality == 0) {
            return 0;
        }
        double value = cardinality;
        if (settings.factor != 0) {
            if (metric_size >= 1600000) {
                std::fill(metric_keys.begin(), metric_keys.end(), 0);
                metric_size = 0;
            }
            uint32_t hashed = mask;
            hashed ^= hashed >> 16;
            hashed *= 0x7feb352du;
            hashed ^= hashed >> 15;
            hashed *= 0x846ca68bu;
            hashed ^= hashed >> 16;
            size_t slot = hashed & ((1 << 21) - 1);
            while (metric_keys[slot] && metric_keys[slot] != mask) {
                slot = (slot + 1) & ((1 << 21) - 1);
            }
            if (!metric_keys[slot]) {
                metric_keys[slot] = mask;
                metric_values[slot] = {mst(mask, distances), mst(mask, weighted_distances), -1};
                ++metric_size;
            }
            if (settings.steiner && metric_values[slot][2] < 0) {
                Mask tree_nodes = 0;
                mst(mask, distances, &tree_nodes);
                double steiner_cost = 2 * __builtin_popcount(tree_nodes) - __builtin_popcount(mask) - 1;
                metric_values[slot][2] = steiner_cost;
            }
            double unweighted = (1 - settings.steiner) * metric_values[slot][0] + settings.steiner * metric_values[slot][2];
            double tree = (1 - settings.weighted) * unweighted + settings.weighted * metric_values[slot][1];
            value = (1 - settings.factor) * cardinality + settings.factor * tree;
        }
        if (settings.potential_power == 1.0) {
            return value;
        }
        if (settings.potential_power == 0.0) {
            return std::log1p(value);
        }
        if (settings.potential_power == 0.5) {
            return std::sqrt(1 + value) - 1;
        }
        if (settings.potential_power < 0) {
            return (std::pow(1 + value, settings.potential_power) - 1) / settings.potential_power;
        }
        return std::pow(1 + value, settings.potential_power) - 1;
    }

    std::vector<int> tree_sequence(Mask mask, int root, const std::vector<double>& noise) const {
        Mask connected = Mask(1) << root;
        std::array<int, 28> parent;
        parent.fill(-1);
        std::vector<int> order{root};
        while (mask & ~connected) {
            std::array<double, 28> distance;
            std::array<int, 28> next_edge;
            distance.fill(1e12);
            next_edge.fill(-1);
            std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>, std::greater<std::pair<double, int>>> queue;
            for (int vertex : order) {
                distance[vertex] = 0;
                queue.emplace(0, vertex);
            }
            int endpoint = -1;
            while (!queue.empty()) {
                auto [price, vertex] = queue.top();
                queue.pop();
                if (price != distance[vertex]) {
                    continue;
                }
                if ((mask & (Mask(1) << vertex)) && !(connected & (Mask(1) << vertex))) {
                    endpoint = vertex;
                    break;
                }
                for (int index : incoming[vertex]) {
                    const Edge& edge = edges[index];
                    double factor = mask & (Mask(1) << edge.control) ? 1 : 2;
                    double candidate = price + factor * edge.price * noise[index];
                    if (candidate < distance[edge.control]) {
                        distance[edge.control] = candidate;
                        next_edge[edge.control] = index;
                        queue.emplace(candidate, edge.control);
                    }
                }
            }
            std::vector<int> path;
            while (!(connected & (Mask(1) << endpoint))) {
                int index = next_edge[endpoint];
                parent[endpoint] = index;
                path.push_back(endpoint);
                endpoint = edges[index].target;
            }
            for (auto vertex = path.rbegin(); vertex != path.rend(); ++vertex) {
                connected |= Mask(1) << *vertex;
                order.push_back(*vertex);
            }
        }
        std::vector<int> sequence;
        for (size_t index = 1; index < order.size(); ++index) {
            if (!(mask & (Mask(1) << order[index]))) {
                sequence.push_back(parent[order[index]]);
            }
        }
        for (int index = int(order.size()) - 1; index >= 1; --index) {
            sequence.push_back(parent[order[index]]);
        }
        return sequence;
    }

    std::vector<Operation> simplify(const std::vector<Operation>& operations) const {
        std::vector<Operation> result;
        for (const Operation& operation : operations) {
            bool canceled = false;
            if (operation.kind == 0) {
                for (int index = int(result.size()) - 1; index >= 0; --index) {
                    const Operation& previous = result[index];
                    if (previous.kind == 1) {
                        if (previous.first == operation.second) {
                            break;
                        }
                    } else if (previous.first == operation.first && previous.second == operation.second) {
                        result.erase(result.begin() + index);
                        canceled = true;
                        break;
                    } else if (previous.first == operation.second || previous.second == operation.first) {
                        break;
                    }
                }
            }
            if (!canceled) {
                result.push_back(operation);
            }
        }
        return result;
    }

    double cost(const std::vector<Operation>& operations) const {
        std::array<int, 28> ready{};
        double price = 0;
        for (const Operation& operation : operations) {
            if (operation.kind == 0) {
                const Edge& edge = edges[edge_index[operation.first][operation.second]];
                price += edge.weight;
                int finish = std::max(ready[edge.control], ready[edge.target]) + edge.duration;
                ready[edge.control] = finish;
                ready[edge.target] = finish;
            }
        }
        return price + 0.2 * *std::max_element(ready.begin(), ready.begin() + size);
    }

    bool connected(Mask allowed) const {
        if (!allowed) {
            return true;
        }
        Mask seen = allowed & -allowed;
        Mask fringe = seen;
        while (fringe) {
            int vertex = __builtin_ctz(fringe);
            fringe &= fringe - 1;
            for (int index : incoming[vertex]) {
                Mask bit = Mask(1) << edges[index].control;
                if ((bit & allowed) && !(bit & seen)) {
                    seen |= bit;
                    fringe |= bit;
                }
            }
        }
        return seen == allowed;
    }

    std::vector<int> reduce_vector(Mask mask, int root, Mask allowed, bool transpose,
                                   const std::vector<double>& noise) const {
        std::vector<int> sequence;
        auto source = [&](int index) { return transpose ? edges[index].target : edges[index].control; };
        auto destination = [&](int index) { return transpose ? edges[index].control : edges[index].target; };
        auto apply_vector = [&](int index) {
            if (mask & (Mask(1) << source(index))) {
                mask ^= Mask(1) << destination(index);
            }
            sequence.push_back(index);
        };
        if (!(mask & (Mask(1) << root))) {
            std::array<double, 28> distance;
            std::array<int, 28> previous;
            distance.fill(1e12);
            previous.fill(-1);
            Mask rest = mask;
            while (rest) {
                int vertex = __builtin_ctz(rest);
                rest &= rest - 1;
                distance[vertex] = 0;
            }
            Mask visited = 0;
            for (int step = 0; step < size; ++step) {
                int vertex = -1;
                double price = 1e12;
                for (int candidate = 0; candidate < size; ++candidate) {
                    if ((allowed & (Mask(1) << candidate)) && !(visited & (Mask(1) << candidate)) && distance[candidate] < price) {
                        vertex = candidate;
                        price = distance[candidate];
                    }
                }
                if (vertex == root) {
                    break;
                }
                visited |= Mask(1) << vertex;
                for (int index = 0; index < int(edges.size()); ++index) {
                    int target = destination(index);
                    if (source(index) == vertex && (allowed & (Mask(1) << target))) {
                        double candidate = price + edges[index].price * noise[index];
                        if (candidate < distance[target]) {
                            distance[target] = candidate;
                            previous[target] = index;
                        }
                    }
                }
            }
            std::vector<int> path;
            int vertex = root;
            while (!(mask & (Mask(1) << vertex))) {
                int index = previous[vertex];
                path.push_back(index);
                vertex = source(index);
            }
            for (auto index = path.rbegin(); index != path.rend(); ++index) {
                apply_vector(*index);
            }
        }
        Mask included = Mask(1) << root;
        std::vector<int> order{root};
        std::array<int, 28> parent;
        parent.fill(-1);
        while (mask & ~included) {
            std::array<double, 28> distance;
            std::array<int, 28> previous;
            distance.fill(1e12);
            previous.fill(-1);
            for (int vertex : order) {
                distance[vertex] = 0;
            }
            Mask visited = 0;
            int endpoint = -1;
            for (int step = 0; step < size; ++step) {
                int vertex = -1;
                double price = 1e12;
                for (int candidate = 0; candidate < size; ++candidate) {
                    if ((allowed & (Mask(1) << candidate)) && !(visited & (Mask(1) << candidate)) && distance[candidate] < price) {
                        vertex = candidate;
                        price = distance[candidate];
                    }
                }
                if ((mask & (Mask(1) << vertex)) && !(included & (Mask(1) << vertex))) {
                    endpoint = vertex;
                    break;
                }
                visited |= Mask(1) << vertex;
                for (int index = 0; index < int(edges.size()); ++index) {
                    int target = destination(index);
                    if (source(index) == vertex && (allowed & (Mask(1) << target))) {
                        double factor = mask & (Mask(1) << target) ? 1 : 2;
                        double candidate = price + factor * edges[index].price * noise[index];
                        if (candidate < distance[target]) {
                            distance[target] = candidate;
                            previous[target] = index;
                        }
                    }
                }
            }
            std::vector<int> path;
            while (!(included & (Mask(1) << endpoint))) {
                parent[endpoint] = previous[endpoint];
                path.push_back(endpoint);
                endpoint = source(previous[endpoint]);
            }
            for (auto vertex = path.rbegin(); vertex != path.rend(); ++vertex) {
                included |= Mask(1) << *vertex;
                order.push_back(*vertex);
            }
        }
        for (size_t index = 1; index < order.size(); ++index) {
            if (!(mask & (Mask(1) << order[index]))) {
                apply_vector(parent[order[index]]);
            }
        }
        for (int index = int(order.size()) - 1; index > 0; --index) {
            apply_vector(parent[order[index]]);
        }
        return sequence;
    }

    std::vector<Operation> linear_cleanup(const std::vector<Operation>& original, unsigned seed, bool greedy) {
        randomizer.seed(seed);
        int last_phase = -1;
        for (int index = 0; index < int(original.size()); ++index) {
            if (original[index].kind == 1) {
                last_phase = index;
            }
        }
        std::vector<Operation> result(original.begin(), original.begin() + last_phase + 1);
        std::vector<Mask> rows(size);
        for (int vertex = 0; vertex < size; ++vertex) {
            rows[vertex] = Mask(1) << vertex;
        }
        for (const Operation& operation : result) {
            if (operation.kind == 0) {
                rows[operation.second] ^= rows[operation.first];
            }
        }
        std::vector<int> left;
        std::vector<int> right;
        std::vector<double> noise;
        for (const Edge& edge : edges) {
            noise.push_back(0.8 + 0.4 * random_unit());
        }
        auto apply_left = [&](std::vector<Mask>& matrix, int index) {
            const Edge& edge = edges[index];
            matrix[edge.target] ^= matrix[edge.control];
        };
        auto apply_right = [&](std::vector<Mask>& matrix, int index) {
            const Edge& edge = edges[index];
            for (Mask& row : matrix) {
                if (row & (Mask(1) << edge.target)) {
                    row ^= Mask(1) << edge.control;
                }
            }
        };
        if (greedy) {
            while (true) {
                std::vector<Mask> columns(size, 0);
                for (int vertex = 0; vertex < size; ++vertex) {
                    for (int bit = 0; bit < size; ++bit) {
                        if (rows[vertex] & (Mask(1) << bit)) {
                            columns[bit] |= Mask(1) << vertex;
                        }
                    }
                }
                double best_score = 1e-8;
                int best_edge = -1;
                bool best_transpose = false;
                for (int index = 0; index < int(edges.size()); ++index) {
                    const Edge& edge = edges[index];
                    int gain_left = __builtin_popcount(rows[edge.target]) - __builtin_popcount(rows[edge.target] ^ rows[edge.control]);
                    int gain_right = __builtin_popcount(columns[edge.control]) - __builtin_popcount(columns[edge.control] ^ columns[edge.target]);
                    for (int transpose = 0; transpose < 2; ++transpose) {
                        double score = (transpose ? gain_right : gain_left) / (std::sqrt(edge.price) * noise[index]);
                        if (score > best_score) {
                            best_score = score;
                            best_edge = index;
                            best_transpose = transpose;
                        }
                    }
                }
                if (best_edge < 0) {
                    break;
                }
                if (best_transpose) {
                    apply_right(rows, best_edge);
                    right.push_back(best_edge);
                } else {
                    apply_left(rows, best_edge);
                    left.push_back(best_edge);
                }
            }
        }
        Mask allowed = (Mask(1) << size) - 1;
        while (allowed) {
            if (Clock::now() > deadline) {
                return {};
            }
            double best_price = 1e30;
            int best_root = -1;
            std::vector<Mask> best_rows;
            std::vector<int> best_left;
            std::vector<int> best_right;
            Mask roots = allowed;
            while (roots) {
                int root = __builtin_ctz(roots);
                roots &= roots - 1;
                if (!connected(allowed ^ (Mask(1) << root))) {
                    continue;
                }
                Mask column = 0;
                for (int vertex = 0; vertex < size; ++vertex) {
                    if (rows[vertex] & (Mask(1) << root)) {
                        column |= Mask(1) << vertex;
                    }
                }
                std::vector<Mask> trial_rows = rows;
                std::vector<int> trial_left = reduce_vector(column, root, allowed, false, noise);
                for (int index : trial_left) {
                    apply_left(trial_rows, index);
                }
                std::vector<int> trial_right = reduce_vector(trial_rows[root], root, allowed, true, noise);
                for (int index : trial_right) {
                    apply_right(trial_rows, index);
                }
                double price = 0;
                for (int index : trial_left) {
                    price += edges[index].price * noise[index];
                }
                for (int index : trial_right) {
                    price += edges[index].price * noise[index];
                }
                for (Mask row : trial_rows) {
                    price += 0.3 * __builtin_popcount(row);
                }
                if (price < best_price) {
                    best_price = price;
                    best_root = root;
                    best_rows = std::move(trial_rows);
                    best_left = std::move(trial_left);
                    best_right = std::move(trial_right);
                }
            }
            rows = std::move(best_rows);
            left.insert(left.end(), best_left.begin(), best_left.end());
            right.insert(right.end(), best_right.begin(), best_right.end());
            allowed ^= Mask(1) << best_root;
        }
        for (int index : left) {
            result.push_back({0, edges[index].control, edges[index].target});
        }
        for (auto index = right.rbegin(); index != right.rend(); ++index) {
            result.push_back({0, edges[*index].control, edges[*index].target});
        }
        return simplify(result);
    }

    std::vector<Operation> optimize_region(const std::vector<Operation>& original,
                                           const std::vector<int>& vertices) {
        int width = vertices.size();
        Mask region = 0;
        std::array<int, 28> local;
        local.fill(-1);
        for (int index = 0; index < width; ++index) {
            region |= Mask(1) << vertices[index];
            local[vertices[index]] = index;
        }
        std::vector<int> native;
        for (int index = 0; index < int(edges.size()); ++index) {
            if (local[edges[index].control] >= 0 && local[edges[index].target] >= 0) {
                native.push_back(index);
            }
        }
        std::unordered_map<unsigned, std::vector<int>> cache;
        std::vector<Operation> result;
        std::vector<Operation> block;
        auto flush = [&]() {
            int gates = 0;
            int old_price = 0;
            for (const Operation& operation : block) {
                if (operation.kind == 0) {
                    ++gates;
                    const Edge& edge = edges[edge_index[operation.first][operation.second]];
                    old_price += 5 * edge.weight + edge.duration;
                }
            }
            if (gates < (width == 4 ? 4 : 3) || Clock::now() > deadline) {
                result.insert(result.end(), block.begin(), block.end());
                block.clear();
                return;
            }
            std::array<int, 4> rows{};
            std::array<std::vector<int>, 16> phases;
            for (int vertex = 0; vertex < width; ++vertex) {
                rows[vertex] = 1 << vertex;
            }
            unsigned required = 0;
            for (const Operation& operation : block) {
                if (operation.kind == 0) {
                    rows[local[operation.second]] ^= rows[local[operation.first]];
                } else {
                    int mask = rows[local[operation.first]];
                    phases[mask].push_back(operation.second);
                    required |= 1u << mask;
                }
            }
            int goal_code = 0;
            int start_code = 0;
            for (int vertex = 0; vertex < width; ++vertex) {
                goal_code |= rows[vertex] << (width * vertex);
                start_code |= (1 << vertex) << (width * vertex);
            }
            unsigned cache_key = (required << (width * width)) | goal_code;
            std::vector<int> path;
            bool found_path = false;
            auto cached = cache.find(cache_key);
            if (cached != cache.end()) {
                path = cached->second;
                found_path = true;
            } else {
                int phase_count = 0;
                std::array<int, 16> phase_bits{};
                for (int mask = 1; mask < (1 << width); ++mask) {
                    if ((required & (1u << mask)) && __builtin_popcount(unsigned(mask)) != 1) {
                        phase_bits[mask] = 1 << phase_count;
                        ++phase_count;
                    }
                }
                if (width == 4 && phase_count > 3) {
                    result.insert(result.end(), block.begin(), block.end());
                    block.clear();
                    return;
                }
                int matrix_bits = width * width;
                int matrix_count = 1 << matrix_bits;
                int state_count = matrix_count << phase_count;
                int final_state = goal_code | (((1 << phase_count) - 1) << matrix_bits);
                std::vector<int> distance(state_count, std::numeric_limits<int>::max());
                std::vector<int> previous(state_count, -1);
                std::vector<int> previous_edge(state_count, -1);
                std::priority_queue<std::pair<int, int>, std::vector<std::pair<int, int>>, std::greater<std::pair<int, int>>> queue;
                distance[start_code] = 0;
                queue.emplace(0, start_code);
                int visited_count = 0;
                while (!queue.empty()) {
                    if ((++visited_count & 255) == 0 && Clock::now() > deadline) {
                        break;
                    }
                    auto [price, state] = queue.top();
                    queue.pop();
                    if (price != distance[state]) {
                        continue;
                    }
                    if (state == final_state) {
                        found_path = true;
                        int current = state;
                        while (current != start_code) {
                            path.push_back(previous_edge[current]);
                            current = previous[current];
                        }
                        std::reverse(path.begin(), path.end());
                        cache[cache_key] = path;
                        break;
                    }
                    if (price >= old_price) {
                        break;
                    }
                    int code = state & (matrix_count - 1);
                    int seen = state >> matrix_bits;
                    for (int index : native) {
                        const Edge& edge = edges[index];
                        int control = local[edge.control];
                        int target = local[edge.target];
                        int control_row = (code >> (control * width)) & ((1 << width) - 1);
                        int target_row = (code >> (target * width)) & ((1 << width) - 1);
                        int next_code = code ^ (control_row << (target * width));
                        int next_seen = seen | phase_bits[control_row ^ target_row];
                        int next_state = next_code | (next_seen << matrix_bits);
                        int next_price = price + 5 * edge.weight + edge.duration;
                        if (next_price < distance[next_state] && next_price <= old_price) {
                            distance[next_state] = next_price;
                            previous[next_state] = state;
                            previous_edge[next_state] = index;
                            queue.emplace(next_price, next_state);
                        }
                    }
                }
            }
            int new_price = 0;
            for (int index : path) {
                new_price += 5 * edges[index].weight + edges[index].duration;
            }
            if (!found_path || new_price >= old_price) {
                result.insert(result.end(), block.begin(), block.end());
                block.clear();
                return;
            }
            for (int vertex = 0; vertex < width; ++vertex) {
                rows[vertex] = 1 << vertex;
            }
            unsigned emitted = 0;
            auto emit_phases = [&]() {
                for (int vertex = 0; vertex < width; ++vertex) {
                    int mask = rows[vertex];
                    if (!(emitted & (1u << mask))) {
                        for (int term : phases[mask]) {
                            result.push_back({1, vertices[vertex], term});
                        }
                        emitted |= 1u << mask;
                    }
                }
            };
            emit_phases();
            for (int index : path) {
                const Edge& edge = edges[index];
                result.push_back({0, edge.control, edge.target});
                rows[local[edge.target]] ^= rows[local[edge.control]];
                emit_phases();
            }
            block.clear();
        };
        for (const Operation& operation : original) {
            bool first_inside = region & (Mask(1) << operation.first);
            if (operation.kind == 1) {
                if (first_inside) {
                    block.push_back(operation);
                } else {
                    result.push_back(operation);
                }
            } else {
                bool second_inside = region & (Mask(1) << operation.second);
                if (first_inside && second_inside) {
                    block.push_back(operation);
                } else if (first_inside || second_inside) {
                    flush();
                    result.push_back(operation);
                } else {
                    result.push_back(operation);
                }
            }
        }
        flush();
        return simplify(result);
    }

    std::vector<Operation> schedule_operations(const std::vector<Operation>& original) {
        int length = original.size();
        if (length > 2500 || Clock::now() > deadline) {
            return original;
        }
        std::vector<std::vector<int>> successors(length);
        std::vector<int> indegree(length, 0);
        std::vector<int> duration(length, 0);
        for (int first = 0; first < length; ++first) {
            const Operation& earlier = original[first];
            if (earlier.kind == 0) {
                duration[first] = edges[edge_index[earlier.first][earlier.second]].duration;
            }
            for (int second = first + 1; second < length; ++second) {
                const Operation& later = original[second];
                bool conflict = false;
                if (earlier.kind == 0 && later.kind == 0) {
                    conflict = earlier.first == later.second || earlier.second == later.first;
                } else if (earlier.kind == 0 && later.kind == 1) {
                    conflict = earlier.second == later.first;
                } else if (earlier.kind == 1 && later.kind == 0) {
                    conflict = earlier.first == later.second;
                }
                if (conflict) {
                    successors[first].push_back(second);
                    ++indegree[second];
                }
            }
        }
        std::vector<int> tails(length, 0);
        for (int index = length - 1; index >= 0; --index) {
            for (int child : successors[index]) {
                tails[index] = std::max(tails[index], tails[child]);
            }
            tails[index] += duration[index];
        }
        std::vector<Operation> best = original;
        double best_cost = cost(best);
        const double priorities[] = {1000000, 0, 0.5, 1, 2, 4, 8};
        for (int trial = 0; trial < 28 && Clock::now() < deadline; ++trial) {
            std::vector<int> pending = indegree;
            std::vector<int> available;
            std::array<int, 28> ready{};
            std::array<int, 28> loads{};
            std::vector<double> jitter(length, 1);
            for (int index = 0; index < length; ++index) {
                if (!pending[index]) {
                    available.push_back(index);
                }
                if (original[index].kind == 0) {
                    loads[original[index].first] += duration[index];
                    loads[original[index].second] += duration[index];
                }
                if (trial >= 7) {
                    jitter[index] = 0.9 + 0.2 * random_unit();
                }
            }
            std::vector<Operation> candidate;
            while (!available.empty()) {
                int chosen = 0;
                double best_priority = -1e30;
                for (int offset = 0; offset < int(available.size()); ++offset) {
                    int index = available[offset];
                    const Operation& operation = original[index];
                    double priority = 1e20 + tails[index];
                    if (operation.kind == 0) {
                        int earliest = std::max(ready[operation.first], ready[operation.second]);
                        priority = tails[index] * jitter[index] - priorities[trial % 7] * earliest;
                        if (trial >= 14) {
                            priority += 0.5 * std::max(loads[operation.first], loads[operation.second]);
                        }
                    }
                    if (priority > best_priority) {
                        best_priority = priority;
                        chosen = offset;
                    }
                }
                int index = available[chosen];
                available[chosen] = available.back();
                available.pop_back();
                const Operation& operation = original[index];
                candidate.push_back(operation);
                if (operation.kind == 0) {
                    int finish = std::max(ready[operation.first], ready[operation.second]) + duration[index];
                    ready[operation.first] = finish;
                    ready[operation.second] = finish;
                    loads[operation.first] -= duration[index];
                    loads[operation.second] -= duration[index];
                }
                for (int child : successors[index]) {
                    if (--pending[child] == 0) {
                        available.push_back(child);
                    }
                }
            }
            double price = cost(candidate);
            if (price < best_cost) {
                best_cost = price;
                best = std::move(candidate);
            }
        }
        return best;
    }

    std::vector<Operation> peephole(const std::vector<Operation>& original, int max_width = 4) {
        std::vector<std::vector<int>> regions;
        for (int first = 0; first < size; ++first) {
            for (int second = first + 1; second < size; ++second) {
                if (edge_index[first][second] >= 0) {
                    regions.push_back({first, second});
                }
                for (int third = second + 1; third < size; ++third) {
                    int links = (edge_index[first][second] >= 0) + (edge_index[first][third] >= 0) + (edge_index[second][third] >= 0);
                    if (links >= 2) {
                        regions.push_back({first, second, third});
                    }
                    for (int fourth = third + 1; max_width >= 4 && fourth < size; ++fourth) {
                        Mask subset = (Mask(1) << first) | (Mask(1) << second) | (Mask(1) << third) | (Mask(1) << fourth);
                        if (connected(subset)) {
                            regions.push_back({first, second, third, fourth});
                        }
                    }
                }
            }
        }
        std::vector<Operation> best = original;
        double best_cost = cost(best);
        for (int pass = 0; pass < 8 && Clock::now() < deadline; ++pass) {
            bool improved = false;
            std::shuffle(regions.begin(), regions.end(), randomizer);
            for (const std::vector<int>& region : regions) {
                if (Clock::now() > deadline) {
                    break;
                }
                std::vector<Operation> candidate = optimize_region(best, region);
                double price = cost(candidate);
                if (price + 1e-8 < best_cost) {
                    best_cost = price;
                    best = std::move(candidate);
                    improved = true;
                }
            }
            if (!improved) {
                break;
            }
        }
        return schedule_operations(best);
    }

    std::vector<Operation> run(const Settings& settings, unsigned seed,
                               const std::vector<int>& prefix = {}, int forbidden = -1) {
        randomizer.seed(seed);
        std::vector<Mask> masks = terms;
        std::vector<bool> active(count, true);
        int remaining = count;
        std::vector<Operation> operations;
        std::vector<int> history;
        std::vector<double> noise;
        std::vector<double> prices;
        std::vector<double> term_weights;
        for (Mask mask : terms) {
            term_weights.push_back(std::pow(__builtin_popcount(mask), -settings.prior_power));
        }
        for (const Edge& edge : edges) {
            noise.push_back(1 + settings.noise * (2 * random_unit() - 1));
            prices.push_back(std::pow(edge.price, settings.exponent) * noise.back());
        }
        stats.fill(0);
        auto emit = [&]() {
            for (int term = 0; term < count; ++term) {
                if (active[term] && __builtin_popcount(masks[term]) == 1) {
                    operations.push_back({1, __builtin_ctz(masks[term]), term});
                    active[term] = false;
                    --remaining;
                }
            }
        };
        auto apply = [&](int index) {
            const Edge& edge = edges[index];
            for (int term = 0; term < count; ++term) {
                if (active[term] && (masks[term] & (Mask(1) << edge.target))) {
                    masks[term] ^= Mask(1) << edge.control;
                }
            }
            operations.push_back({0, edge.control, edge.target});
            history.push_back(index);
            emit();
        };
        emit();
        for (int index : prefix) {
            if (!remaining) {
                break;
            }
            apply(index);
        }
        while (remaining) {
            if (Clock::now() > deadline || history.size() > 20000) {
                return {};
            }
            std::vector<double> old_metrics(count);
            double old_total = 0;
            for (int term = 0; term < count; ++term) {
                if (active[term]) {
                    old_metrics[term] = metric(masks[term], settings) * term_weights[term];
                    old_total += old_metrics[term];
                }
            }
            double best_score = 1e-8;
            int best_edge = -1;
            for (int index = 0; index < int(edges.size()); ++index) {
                const Edge& edge = edges[index];
                double gain = 0;
                for (int term = 0; term < count; ++term) {
                    if (active[term] && (masks[term] & (Mask(1) << edge.target))) {
                        Mask transformed = masks[term] ^ (Mask(1) << edge.control);
                        gain += old_metrics[term] - metric(transformed, settings) * term_weights[term];
                        if (__builtin_popcount(transformed) == 1) {
                            gain += settings.bonus;
                        }
                    }
                }
                double score = gain / prices[index];
                if (index == forbidden) {
                    score *= 0.001;
                }
                if (settings.dynamic_noise) {
                    score *= 1 + settings.dynamic_noise * (2 * random_unit() - 1);
                }
                if (score > best_score) {
                    best_score = score;
                    best_edge = index;
                }
            }
            if (best_edge >= 0) {
                forbidden = -1;
                ++stats[0];
                apply(best_edge);
                continue;
            }
            std::vector<int> best_sequence;
            forbidden = -1;
            if (settings.lookahead) {
                for (int first_index = 0; first_index < int(edges.size()); ++first_index) {
                    const Edge& first = edges[first_index];
                    for (int second_index = 0; second_index < int(edges.size()); ++second_index) {
                        const Edge& second = edges[second_index];
                        if (first_index == second_index || (first.control != second.target && first.control != second.control)) {
                            continue;
                        }
                        double gain = 0;
                        for (int term = 0; term < count; ++term) {
                            if (active[term]) {
                                Mask mask = masks[term];
                                if (mask & (Mask(1) << first.target)) {
                                    mask ^= Mask(1) << first.control;
                                }
                                if (mask & (Mask(1) << second.target)) {
                                    mask ^= Mask(1) << second.control;
                                }
                                gain += old_metrics[term] - metric(mask, settings) * term_weights[term];
                                if (__builtin_popcount(mask) == 1) {
                                    gain += settings.bonus;
                                }
                            }
                        }
                        double score = gain / (prices[first_index] + prices[second_index]);
                        if (score > best_score) {
                            best_score = score;
                            best_sequence = {first_index, second_index};
                        }
                    }
                }
                if (!best_sequence.empty()) {
                    stats[1] += best_sequence.size();
                    for (int index : best_sequence) {
                        apply(index);
                    }
                    continue;
                }
            }
            std::vector<std::pair<double, int>> candidates;
            for (int term = 0; term < count; ++term) {
                if (active[term]) {
                    candidates.emplace_back(old_metrics[term], term);
                }
            }
            std::sort(candidates.begin(), candidates.end());
            double best_value = 1e30;
            for (int candidate = 0; candidate < std::min(settings.term_candidates, int(candidates.size())); ++candidate) {
                int term = candidates[candidate].second;
                Mask support = masks[term];
                while (support) {
                    int root = __builtin_ctz(support);
                    support &= support - 1;
                    std::vector<int> sequence = tree_sequence(masks[term], root, noise);
                    double price = 0;
                    std::vector<Mask> trial_masks = masks;
                    for (int index : sequence) {
                        const Edge& edge = edges[index];
                        price += edge.price * noise[index];
                        for (int other = 0; other < count; ++other) {
                            if (active[other] && (trial_masks[other] & (Mask(1) << edge.target))) {
                                trial_masks[other] ^= Mask(1) << edge.control;
                            }
                        }
                    }
                    double gain = old_total;
                    for (int other = 0; other < count; ++other) {
                        if (active[other]) {
                            gain -= metric(trial_masks[other], settings) * term_weights[other];
                        }
                    }
                    double value = price / (1 + std::max(0.0, gain) * settings.fallback_gain);
                    if (value < best_value) {
                        best_value = value;
                        best_sequence = std::move(sequence);
                    }
                }
            }
            stats[2] += best_sequence.size();
            for (int index : best_sequence) {
                apply(index);
            }
            if (settings.rollback) {
                std::vector<Mask> trial_masks = masks;
                double best_metric = 0;
                for (int term = 0; term < count; ++term) {
                    if (active[term]) {
                        best_metric += metric(masks[term], settings) * term_weights[term];
                    }
                }
                int rollback_count = 0;
                double rollback_price = 0;
                for (int offset = 1; offset <= int(best_sequence.size()); ++offset) {
                    const Edge& edge = edges[best_sequence[best_sequence.size() - offset]];
                    rollback_price += edge.price;
                    double total = settings.rollback == 2 ? 0.15 * rollback_price : 0;
                    for (int term = 0; term < count; ++term) {
                        if (active[term]) {
                            if (trial_masks[term] & (Mask(1) << edge.target)) {
                                trial_masks[term] ^= Mask(1) << edge.control;
                            }
                            total += metric(trial_masks[term], settings) * term_weights[term];
                        }
                    }
                    if (total + 1e-8 < best_metric) {
                        best_metric = total;
                        rollback_count = offset;
                    }
                }
                for (int offset = 1; offset <= rollback_count; ++offset) {
                    apply(best_sequence[best_sequence.size() - offset]);
                }
            }
        }
        for (auto index = history.rbegin(); index != history.rend(); ++index) {
            const Edge& edge = edges[*index];
            operations.push_back({0, edge.control, edge.target});
        }
        last_history = history;
        return simplify(operations);
    }
};

extern "C" int compile_phase(int size, int edge_count, const int* edge_data,
                             int term_count, const uint32_t* terms, double seconds,
                             int* output, int capacity, const double* options, double* report) {
    Engine engine(size, edge_count, edge_data, term_count, terms);
    engine.deadline = Clock::now() + std::chrono::milliseconds(int(seconds * 1000));
    std::vector<Operation> best;
    std::vector<int> best_history;
    Settings best_settings;
    std::array<std::vector<int>, 4> histories;
    std::array<std::vector<Operation>, 4> island_circuits;
    std::array<Settings, 4> island_settings;
    std::array<double, 4> island_costs;
    island_costs.fill(1e30);
    double best_cost = 1e30;
    int trials = 0;
    std::mt19937 randomizer(62493);
    while (Clock::now() < engine.deadline) {
        Settings settings;
        unsigned seed = randomizer();
        if (options) {
            settings.factor = options[0];
            settings.weighted = options[1];
            settings.exponent = options[2];
            settings.bonus = options[3];
            settings.noise = options[4];
            settings.dynamic_noise = options[5];
            settings.fallback_gain = options[6];
            settings.term_candidates = int(options[7]);
            settings.rollback = int(options[8]);
            settings.lookahead = int(options[9]);
            settings.potential_power = options[12];
            settings.prior_power = options[13];
            settings.steiner = options[14];
            seed = unsigned(options[10]) + trials * 3187;
        } else {
            settings.factor = (randomizer() % 4 == 0) ? 0.8 : 1.0;
            settings.weighted = (randomizer() % 4 == 0) ? 0.7 : 0.0;
            settings.exponent = 0.2 + (randomizer() % 5) * 0.2;
            const double bonuses[] = {0, 0.5, 1, 2, 5, 10};
            settings.bonus = bonuses[randomizer() % 6];
            settings.noise = 0.05 + (randomizer() % 6) * 0.05;
            settings.dynamic_noise = (randomizer() % 4 == 0) ? 0.2 : 0.0;
            settings.rollback = randomizer() % 3;
            settings.potential_power = (randomizer() % 3) * 0.5;
            settings.prior_power = (randomizer() % 5 == 0) ? 0.5 : 0.0;
            settings.fallback_gain = (randomizer() % 3) * 0.2;
        }
        std::vector<int> prefix;
        int forbidden = -1;
        int island = trials % 4;
        if (!options && trials % 3 != 0 && !histories[island].empty()) {
            int cut = randomizer() % histories[island].size();
            prefix.assign(histories[island].begin(), histories[island].begin() + cut);
            int mutation = randomizer() % 8;
            if (island % 2 == 0) {
                mutation = mutation < 2 ? 2 : 3;
            }
            if (mutation == 0) {
                int end = std::min(int(histories[island].size()), cut + 1 + int(randomizer() % 6));
                prefix.insert(prefix.end(), histories[island].begin() + end, histories[island].end());
            } else if (mutation == 1) {
                int other = cut + 1;
                while (other < int(histories[island].size()) && histories[island][other] != histories[island][cut]) {
                    ++other;
                }
                for (int index = cut + 1; index < int(histories[island].size()); ++index) {
                    if (index != other) {
                        prefix.push_back(histories[island][index]);
                    }
                }
            } else if (mutation == 2) {
                forbidden = histories[island][cut];
            }
            if (randomizer() % (island % 2 == 0 ? 2 : 5) != 0) {
                settings = island_settings[island];
                settings.noise = 0.05 + (randomizer() % 8) * 0.05;
            }
        }
        std::vector<Operation> candidate = engine.run(settings, seed, prefix, forbidden);
        ++trials;
        if (!candidate.empty()) {
            double price = engine.cost(candidate);
            if (price < island_costs[island]) {
                island_costs[island] = price;
                histories[island] = engine.last_history;
                island_settings[island] = settings;
                island_circuits[island] = candidate;
            }
            if (price < best_cost) {
                best_cost = price;
                best = std::move(candidate);
                best_history.clear();
                int last_phase = -1;
                for (int index = 0; index < int(best.size()); ++index) {
                    if (best[index].kind == 1) {
                        last_phase = index;
                    }
                }
                for (int index = 0; index <= last_phase; ++index) {
                    if (best[index].kind == 0) {
                        best_history.push_back(engine.edge_index[best[index].first][best[index].second]);
                    }
                }
                best_settings = settings;
                report[2] = engine.stats[0];
                report[3] = engine.stats[1];
                report[4] = engine.stats[2];
                report[5] = settings.factor;
                report[6] = settings.weighted;
                report[7] = settings.exponent;
                report[8] = settings.bonus;
                report[9] = settings.noise;
                report[10] = settings.dynamic_noise;
                report[11] = settings.fallback_gain;
                report[12] = settings.term_candidates;
                report[13] = settings.rollback;
                report[14] = settings.lookahead;
                report[15] = seed;
                report[16] = settings.potential_power;
                report[17] = settings.prior_power;
                report[18] = settings.steiner;
            }
        }
        if (options && options[11] > 0 && trials >= options[11]) {
            break;
        }
        if (engine.metric_size > 1200000) {
            std::fill(engine.metric_keys.begin(), engine.metric_keys.end(), 0);
            engine.metric_size = 0;
        }
    }
    if (!options && !best.empty()) {
        std::vector<int> ranking{0, 1, 2, 3};
        std::sort(ranking.begin(), ranking.end(), [&](int first, int second) {
            return island_costs[first] < island_costs[second];
        });
        auto polishing_deadline = Clock::now() + std::chrono::milliseconds(650);
        for (int island : ranking) {
            if (island_circuits[island].empty() || Clock::now() > polishing_deadline) {
                continue;
            }
            engine.deadline = std::min(polishing_deadline, Clock::now() + std::chrono::milliseconds(300));
            engine.randomizer.seed(12345);
            std::vector<Operation> candidate = engine.peephole(island_circuits[island]);
            double price = engine.cost(candidate);
            if (price < best_cost) {
                best_cost = price;
                best = std::move(candidate);
            }
        }
    }
    report[0] = best_cost;
    report[1] = trials;
    if (best.size() > size_t(capacity)) {
        return -1;
    }
    for (int index = 0; index < int(best.size()); ++index) {
        output[3 * index] = best[index].kind;
        output[3 * index + 1] = best[index].first;
        output[3 * index + 2] = best[index].second;
    }
    return int(best.size());
}

extern "C" int improve_phase(int size, int edge_count, const int* edge_data,
                             int term_count, const uint32_t* terms, int operation_count,
                             const int* input, double seconds, int* output, double* report) {
    Engine engine(size, edge_count, edge_data, term_count, terms);
    engine.deadline = Clock::now() + std::chrono::milliseconds(int(seconds * 1000));
    std::vector<Operation> original;
    for (int index = 0; index < operation_count; ++index) {
        original.push_back({input[3 * index], input[3 * index + 1], input[3 * index + 2]});
    }
    std::vector<Operation> best = original;
    double best_cost = engine.cost(best);
    int trials = 0;
    while (Clock::now() < engine.deadline) {
        std::vector<Operation> candidate = engine.linear_cleanup(original, 7293 + trials * 3171, trials % 2);
        ++trials;
        if (!candidate.empty()) {
            double price = engine.cost(candidate);
            if (price < best_cost) {
                best_cost = price;
                best = std::move(candidate);
            }
        }
    }
    report[0] = best_cost;
    report[1] = trials;
    if (best.size() > 100000) {
        return -1;
    }
    for (int index = 0; index < int(best.size()); ++index) {
        output[3 * index] = best[index].kind;
        output[3 * index + 1] = best[index].first;
        output[3 * index + 2] = best[index].second;
    }
    return int(best.size());
}

extern "C" int optimize_phase(int size, int edge_count, const int* edge_data,
                              int term_count, const uint32_t* terms, int operation_count,
                              const int* input, double seconds, int* output, double* report) {
    Engine engine(size, edge_count, edge_data, term_count, terms);
    engine.deadline = Clock::now() + std::chrono::milliseconds(int(seconds * 1000));
    std::vector<Operation> original;
    for (int index = 0; index < operation_count; ++index) {
        original.push_back({input[3 * index], input[3 * index + 1], input[3 * index + 2]});
    }
    std::vector<Operation> best = engine.peephole(original);
    report[0] = engine.cost(best);
    if (best.size() > 100000) {
        return -1;
    }
    for (int index = 0; index < int(best.size()); ++index) {
        output[3 * index] = best[index].kind;
        output[3 * index + 1] = best[index].first;
        output[3 * index + 2] = best[index].second;
    }
    return int(best.size());
}
