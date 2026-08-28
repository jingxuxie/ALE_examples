#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>
#include "fastjet/ClusterSequence.hh"

constexpr int max_order = 8;
constexpr double pi = 3.1415926535897932384626433832795;
constexpr double radius = 1.5;
constexpr double factorial[9] = {1, 1, 2, 6, 24, 120, 720, 5040, 40320};
double choose_number[9][9];
uint64_t recursion_calls = 0;
uint64_t split_count = 0;
uint64_t subjet_count = 0;
int largest_split = 0;
bool oracle_mode = false;

struct Particle {
    double pt, rapidity, phi;
};

struct Query {
    int order, algorithm, bins, kappa_index;
    double kappa, resolution, log_min;
    std::vector<double> histogram;
};

struct AxisGroup {
    double log_min;
    int bins;
    std::vector<int> queries;
};

struct ResolutionGroup {
    int algorithm;
    double resolution;
    std::vector<AxisGroup> axes;
};

template<int Words>
struct Mask {
    std::array<uint64_t, Words> words{};
    void set(int position) { words[position >> 6] |= uint64_t(1) << (position & 63); }
    void clear(int position) { words[position >> 6] &= ~(uint64_t(1) << (position & 63)); }
    bool empty() const {
        uint64_t combined = 0;
        for (int index = 0; index < Words; ++index) combined |= words[index];
        return combined == 0;
    }
    int count() const {
        int result = 0;
        for (int index = 0; index < Words; ++index) result += __builtin_popcountll(words[index]);
        return result;
    }
    int first() const {
        for (int index = 0; index < Words; ++index)
            if (words[index]) return 64 * index + __builtin_ctzll(words[index]);
        return -1;
    }
    int pop() {
        int position = first();
        clear(position);
        return position;
    }
    Mask operator&(const Mask& other) const {
        Mask result;
        for (int index = 0; index < Words; ++index) result.words[index] = words[index] & other.words[index];
        return result;
    }
    Mask without(const Mask& other) const {
        Mask result;
        for (int index = 0; index < Words; ++index) result.words[index] = words[index] & ~other.words[index];
        return result;
    }
    bool operator==(const Mask& other) const { return words == other.words; }
};

template<int Kappas>
using Weights = std::array<double, Kappas>;

template<int Kappas>
using Polynomial = std::array<Weights<Kappas>, max_order + 1>;

template<int Words>
struct MaskHash {
    size_t operator()(const Mask<Words>& mask) const {
        uint64_t result = mask.words[0];
        for (int index = 1; index < Words; ++index)
            result ^= mask.words[index] + 0x9e3779b97f4a7c15ULL + (result << 6) + (result >> 2);
        result ^= result >> 30;
        result *= 0xbf58476d1ce4e5b9ULL;
        result ^= result >> 27;
        result *= 0x94d049bb133111ebULL;
        return result ^ (result >> 31);
    }
};

template<int Words, int Kappas>
class CliqueMoments {
public:
    std::vector<Mask<Words>> adjacent;
    std::vector<Weights<Kappas>> weights;

    void evaluate(Mask<Words> vertices, int degree, Polynomial<Kappas>& output) const {
        ++recursion_calls;
        ++local_calls;
        bool use_cache = weights.size() >= 24 && local_calls > 256 && degree >= 2;
        if (use_cache) {
            auto found = cache.find(vertices);
            if (found != cache.end() && found->second.degree >= degree) {
                for (int order = 0; order <= degree; ++order) output[order] = found->second.polynomial[order];
                return;
            }
        }
        evaluate_uncached(vertices, degree, output);
        if (use_cache && cache.size() < 200000) {
            auto& cached = cache[vertices];
            cached.degree = degree;
            for (int order = 0; order <= degree; ++order) cached.polynomial[order] = output[order];
        }
    }

private:
    struct CachedPolynomial {
        int degree = -1;
        Polynomial<Kappas> polynomial;
    };
    mutable uint64_t local_calls = 0;
    mutable std::unordered_map<Mask<Words>, CachedPolynomial, MaskHash<Words>> cache;

    void evaluate_uncached(Mask<Words> vertices, int degree, Polynomial<Kappas>& output) const {
        for (int order = 0; order <= degree; ++order) output[order].fill(0);
        output[0].fill(1);
        if (!degree || vertices.empty()) return;
        if (degree == 1) {
            while (!vertices.empty()) {
                int vertex = vertices.pop();
                for (int kappa = 0; kappa < Kappas; ++kappa) output[1][kappa] += weights[vertex][kappa];
            }
            return;
        }
        Mask<Words> remaining = vertices;
        Mask<Words> universal;
        Weights<Kappas> universal_weight{};
        int size = vertices.count();
        int pivot = -1;
        int minimum_degree = size + 1;
        while (!remaining.empty()) {
            int vertex = remaining.pop();
            int neighbors = (vertices & adjacent[vertex]).count();
            if (neighbors == size) {
                universal.set(vertex);
                for (int kappa = 0; kappa < Kappas; ++kappa) universal_weight[kappa] += weights[vertex][kappa];
            } else if (neighbors < minimum_degree) {
                minimum_degree = neighbors;
                pivot = vertex;
            }
        }
        if (pivot < 0) {
            for (int order = 1; order <= degree; ++order)
                for (int kappa = 0; kappa < Kappas; ++kappa)
                    output[order][kappa] = output[order - 1][kappa] * universal_weight[kappa];
            return;
        }
        remaining = vertices.without(universal);
        bool factored = false;
        if (remaining.count() >= 12 && minimum_degree >= size / 2) {
            Mask<Words> unvisited = remaining;
            std::vector<Mask<Words>> components;
            while (!unvisited.empty()) {
                Mask<Words> frontier;
                frontier.set(unvisited.pop());
                Mask<Words> component = frontier;
                while (!frontier.empty()) {
                    int vertex = frontier.pop();
                    Mask<Words> discovered = unvisited.without(adjacent[vertex]);
                    unvisited = unvisited.without(discovered);
                    for (int word = 0; word < Words; ++word) {
                        frontier.words[word] |= discovered.words[word];
                        component.words[word] |= discovered.words[word];
                    }
                }
                components.push_back(component);
            }
            if (components.size() > 1) {
                factored = true;
                evaluate(components[0], degree, output);
                for (size_t component = 1; component < components.size(); ++component) {
                    Polynomial<Kappas> factor;
                    evaluate(components[component], degree, factor);
                    for (int order = degree; order >= 1; --order) {
                        for (int kappa = 0; kappa < Kappas; ++kappa) {
                            double value = 0;
                            for (int factor_order = 0; factor_order <= order; ++factor_order)
                                value += choose_number[order][factor_order] * factor[factor_order][kappa] * output[order - factor_order][kappa];
                            output[order][kappa] = value;
                        }
                    }
                }
            }
        }
        Weights<Kappas> power;
        if (!factored) {
            remaining.clear(pivot);
            Polynomial<Kappas> include;
            evaluate(remaining, degree, output);
            evaluate(remaining & adjacent[pivot], degree - 1, include);
            power.fill(1);
            for (int multiplicity = 1; multiplicity <= degree; ++multiplicity) {
                for (int kappa = 0; kappa < Kappas; ++kappa) power[kappa] *= weights[pivot][kappa];
                for (int order = multiplicity; order <= degree; ++order)
                    for (int kappa = 0; kappa < Kappas; ++kappa)
                        output[order][kappa] += choose_number[order][multiplicity] * power[kappa] * include[order - multiplicity][kappa];
            }
        }
        if (!universal.empty()) {
            Polynomial<Kappas> base = output;
            power.fill(1);
            for (int multiplicity = 1; multiplicity <= degree; ++multiplicity) {
                for (int kappa = 0; kappa < Kappas; ++kappa) power[kappa] *= universal_weight[kappa];
                for (int order = multiplicity; order <= degree; ++order)
                    for (int kappa = 0; kappa < Kappas; ++kappa)
                        output[order][kappa] += choose_number[order][multiplicity] * power[kappa] * base[order - multiplicity][kappa];
            }
        }
    }
};

struct TreeData {
    const fastjet::ClusterSequence& sequence;
    const std::vector<double>& kappas;
    std::vector<double> weight;
    std::vector<double> log_distance;
    int jet_count;

    TreeData(const fastjet::ClusterSequence& cluster, const std::vector<Particle>& particles,
             const std::vector<double>& requested_kappas, double total)
        : sequence(cluster), kappas(requested_kappas), jet_count(cluster.jets().size()) {
        int kappa_count = kappas.size();
        weight.resize(jet_count * kappa_count);
        log_distance.assign(jet_count * jet_count, 999.0);
        const auto& history = sequence.history();
        const auto& jets = sequence.jets();
        for (const auto& entry : history) {
            int jet = entry.jetp_index;
            if (jet < 0) continue;
            for (int kappa = 0; kappa < kappa_count; ++kappa) {
                double value;
                if (kappas[kappa] == 1.0) {
                    value = jets[jet].pt() / total;
                } else if (entry.parent1 < 0) {
                    value = std::pow(particles[jet].pt / total, kappas[kappa]);
                } else {
                    int first = history[entry.parent1].jetp_index;
                    int second = history[entry.parent2].jetp_index;
                    value = weight[first * kappa_count + kappa] + weight[second * kappa_count + kappa];
                }
                weight[jet * kappa_count + kappa] = value;
            }
        }
    }

    double distance_log(int first, int second) {
        if (first > second) std::swap(first, second);
        double& cached = log_distance[first * jet_count + second];
        if (cached == 999.0) {
            double squared = sequence.jets()[first].squared_distance(sequence.jets()[second]);
            cached = squared > 0 ? 0.5 * std::log10(squared) : -std::numeric_limits<double>::infinity();
        }
        return cached;
    }
};

template<int Kappas>
void brute_support(const std::vector<Weights<Kappas>>& weights, const std::vector<int>& edge_bins,
                   int left_size, int degree, const std::vector<std::pair<int, int>>& requested,
                   std::vector<Query>& queries) {
    int size = weights.size();
    std::vector<Polynomial<Kappas>> vertex_polynomials(size);
    for (int vertex = 0; vertex < size; ++vertex) {
        vertex_polynomials[vertex][0].fill(1);
        for (int order = 1; order <= degree; ++order)
            for (int kappa = 0; kappa < Kappas; ++kappa)
                vertex_polynomials[vertex][order][kappa] = vertex_polynomials[vertex][order - 1][kappa] * weights[vertex][kappa] / order;
    }
    std::array<int, max_order> selected;
    auto descend = [&](auto&& self, int start, int depth, int bin, int colors, const Polynomial<Kappas>& previous) -> void {
        for (int vertex = start; vertex < size; ++vertex) {
            int next_bin = bin;
            for (int position = 0; position < depth; ++position)
                next_bin = std::max(next_bin, edge_bins[vertex * size + selected[position]]);
            int next_colors = colors | (vertex < left_size ? 1 : 2);
            Polynomial<Kappas> polynomial{};
            for (int order = depth + 1; order <= degree; ++order)
                for (int multiplicity = 1; multiplicity <= order - depth; ++multiplicity)
                    for (int kappa = 0; kappa < Kappas; ++kappa)
                        polynomial[order][kappa] += previous[order - multiplicity][kappa] * vertex_polynomials[vertex][multiplicity][kappa];
            if (next_colors == 3) {
                for (auto request : requested) {
                    Query& query = queries[request.first];
                    query.histogram[next_bin] += factorial[query.order] * polynomial[query.order][request.second];
                }
            }
            if (depth + 1 < degree) {
                selected[depth] = vertex;
                self(self, vertex + 1, depth + 1, next_bin, next_colors, polynomial);
            }
        }
    };
    Polynomial<Kappas> initial{};
    initial[0].fill(1);
    descend(descend, 0, 0, 0, 0, initial);
}

template<int Words, int Kappas>
void accumulate_block(const TreeData& tree, const std::vector<int>& points,
                      const std::vector<int>& edge_bins, int left_size, int minimum_cross,
                      int maximum_bin, const std::vector<int>& active_bins,
                      const std::vector<int>& kappa_indices,
                      const std::vector<std::pair<int, int>>& requested, std::vector<Query>& queries) {
    int size = points.size();
    int degree = 2;
    for (auto request : requested) degree = std::max(degree, queries[request.first].order);
    std::vector<Weights<Kappas>> original_weight(size);
    Weights<Kappas> left_weight{}, right_weight{};
    for (int vertex = 0; vertex < size; ++vertex) {
        for (int kappa = 0; kappa < Kappas; ++kappa) {
            double value = tree.weight[points[vertex] * tree.kappas.size() + kappa_indices[kappa]];
            original_weight[vertex][kappa] = value;
            (vertex < left_size ? left_weight : right_weight)[kappa] += value;
        }
    }
    if (oracle_mode) {
        brute_support<Kappas>(original_weight, edge_bins, left_size, degree, requested, queries);
        return;
    }
    if (degree == 2) {
        for (int first = 0; first < left_size; ++first)
            for (int second = left_size; second < size; ++second)
                for (auto request : requested)
                    queries[request.first].histogram[edge_bins[first * size + second]] +=
                        2 * original_weight[first][request.second] * original_weight[second][request.second];
        return;
    }
    Polynomial<Kappas> previous{};
    std::vector<Mask<Words>> original_adjacent(size);
    for (int vertex = 0; vertex < size; ++vertex) original_adjacent[vertex].set(vertex);
    int previous_bin = -1;
    for (int bin : active_bins) {
        if (bin < minimum_cross) continue;
        Polynomial<Kappas> cross{};
        if (bin == maximum_bin) {
            Weights<Kappas> full_power, left_power, right_power;
            full_power.fill(1);
            left_power.fill(1);
            right_power.fill(1);
            for (int order = 1; order <= degree; ++order) {
                for (int kappa = 0; kappa < Kappas; ++kappa) {
                    full_power[kappa] *= left_weight[kappa] + right_weight[kappa];
                    left_power[kappa] *= left_weight[kappa];
                    right_power[kappa] *= right_weight[kappa];
                    cross[order][kappa] = full_power[kappa] - left_power[kappa] - right_power[kappa];
                }
            }
        } else {
            for (int first = 0; first < size; ++first) {
                for (int second = first + 1; second < size; ++second) {
                    int edge = edge_bins[first * size + second];
                    if (edge <= bin && edge > previous_bin) {
                        original_adjacent[first].set(second);
                        original_adjacent[second].set(first);
                    }
                }
            }
            CliqueMoments<Words, Kappas> evaluator;
            std::vector<int> representatives;
            std::vector<int> classes(size);
            Mask<Words> all, left, right;
            for (int vertex = 0; vertex < size; ++vertex) {
                int match = -1;
                for (int candidate = 0; candidate < int(representatives.size()); ++candidate) {
                    int representative = representatives[candidate];
                    if ((vertex < left_size) == (representative < left_size) &&
                        original_adjacent[vertex] == original_adjacent[representative]) {
                        match = candidate;
                        break;
                    }
                }
                if (match < 0) {
                    match = representatives.size();
                    representatives.push_back(vertex);
                    evaluator.weights.push_back(original_weight[vertex]);
                    all.set(match);
                    (vertex < left_size ? left : right).set(match);
                } else {
                    for (int kappa = 0; kappa < Kappas; ++kappa)
                        evaluator.weights[match][kappa] += original_weight[vertex][kappa];
                }
                classes[vertex] = match;
            }
            int compressed_size = representatives.size();
            evaluator.adjacent.resize(compressed_size);
            for (int first = 0; first < compressed_size; ++first) {
                evaluator.adjacent[first].set(first);
                for (int second = first + 1; second < compressed_size; ++second) {
                    if (edge_bins[representatives[first] * size + representatives[second]] <= bin) {
                        evaluator.adjacent[first].set(second);
                        evaluator.adjacent[second].set(first);
                    }
                }
            }
            Polynomial<Kappas> full, pure_left, pure_right;
            evaluator.evaluate(all, degree, full);
            evaluator.evaluate(left, degree, pure_left);
            evaluator.evaluate(right, degree, pure_right);
            for (int order = 2; order <= degree; ++order)
                for (int kappa = 0; kappa < Kappas; ++kappa)
                    cross[order][kappa] = full[order][kappa] - pure_left[order][kappa] - pure_right[order][kappa];
        }
        for (auto request : requested) {
            Query& query = queries[request.first];
            double value = cross[query.order][request.second] - previous[query.order][request.second];
            query.histogram[bin] += value;
        }
        previous = cross;
        previous_bin = bin;
    }
}

template<int Words>
void dispatch_block(int kappa_count, const TreeData& tree, const std::vector<int>& points,
                    const std::vector<int>& edge_bins, int left_size, int minimum_cross,
                    int maximum_bin, const std::vector<int>& active_bins,
                    const std::vector<int>& kappas, const std::vector<std::pair<int, int>>& requested,
                    std::vector<Query>& queries) {
    switch (kappa_count) {
        case 1: accumulate_block<Words, 1>(tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, kappas, requested, queries); break;
        case 2: accumulate_block<Words, 2>(tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, kappas, requested, queries); break;
        case 3: accumulate_block<Words, 3>(tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, kappas, requested, queries); break;
        case 4: accumulate_block<Words, 4>(tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, kappas, requested, queries); break;
    }
}

void accumulate_axis(TreeData& tree, const std::vector<int>& points, int left_size,
                     const AxisGroup& axis, std::vector<Query>& queries) {
    int size = points.size();
    std::vector<int> edge_bins(size * size, 0);
    std::vector<bool> occupied(axis.bins, false);
    int minimum_cross = axis.bins - 1;
    int maximum_bin = 0;
    double scale = axis.bins / (-axis.log_min);
    for (int first = 0; first < size; ++first) {
        for (int second = first + 1; second < size; ++second) {
            double logarithm = tree.distance_log(points[first], points[second]);
            int bin = logarithm <= axis.log_min ? 0 :
                (logarithm >= 0.0 ? axis.bins - 1 : std::min(axis.bins - 1, int((logarithm - axis.log_min) * scale)));
            edge_bins[first * size + second] = edge_bins[second * size + first] = bin;
            occupied[bin] = true;
            maximum_bin = std::max(maximum_bin, bin);
            if (first < left_size && second >= left_size) minimum_cross = std::min(minimum_cross, bin);
        }
    }
    std::vector<int> active_bins;
    for (int bin = 0; bin < axis.bins; ++bin) if (occupied[bin]) active_bins.push_back(bin);
    std::vector<int> unique_kappas;
    for (int query : axis.queries) {
        int kappa = queries[query].kappa_index;
        if (std::find(unique_kappas.begin(), unique_kappas.end(), kappa) == unique_kappas.end()) unique_kappas.push_back(kappa);
    }
    for (int offset = 0; offset < int(unique_kappas.size()); offset += 4) {
        int count = std::min(4, int(unique_kappas.size()) - offset);
        std::vector<int> block_kappas(unique_kappas.begin() + offset, unique_kappas.begin() + offset + count);
        std::vector<std::pair<int, int>> requested;
        for (int query : axis.queries) {
            auto position = std::find(block_kappas.begin(), block_kappas.end(), queries[query].kappa_index);
            if (position != block_kappas.end()) requested.emplace_back(query, position - block_kappas.begin());
        }
        if (size <= 64) dispatch_block<1>(count, tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, block_kappas, requested, queries);
        else if (size <= 128) dispatch_block<2>(count, tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, block_kappas, requested, queries);
        else if (size <= 192) dispatch_block<3>(count, tree, points, edge_bins, left_size, minimum_cross, maximum_bin, active_bins, block_kappas, requested, queries);
        else throw std::runtime_error("More than 192 resolved subjets are outside the supplied multiplicity bound.");
    }
}

std::vector<std::vector<Particle>> read_events(const std::string& path, int nevents) {
    FILE* file = std::fopen(path.c_str(), "r");
    if (!file) throw std::runtime_error("Cannot open events file");
    std::vector<std::vector<Particle>> events(nevents);
    char* line = nullptr;
    size_t capacity = 0;
    while (getline(&line, &capacity, file) >= 0) {
        char* cursor = line;
        while (*cursor == ' ' || *cursor == '\t') ++cursor;
        if (*cursor == '#' || *cursor == '\n' || !*cursor) continue;
        int event = std::strtol(cursor, &cursor, 10);
        double pt = std::strtod(cursor, &cursor);
        double rapidity = std::strtod(cursor, &cursor);
        double phi = std::strtod(cursor, &cursor);
        if (event < 0 || event >= nevents || !(pt > 0)) throw std::runtime_error("Invalid event row");
        events[event].push_back({pt, rapidity, phi});
    }
    std::free(line);
    std::fclose(file);
    for (const auto& event : events) if (event.empty()) throw std::runtime_error("Missing event");
    return events;
}

int main() {
    try {
        auto started = std::chrono::steady_clock::now();
        fastjet::ClusterSequence::set_fastjet_banner_stream(nullptr);
        oracle_mode = std::getenv("EEC_ORACLE") != nullptr;
        for (int order = 0; order <= max_order; ++order)
            for (int count = 0; count <= order; ++count)
                choose_number[order][count] = factorial[order] / (factorial[count] * factorial[order - count]);
        std::string events_file;
        std::getline(std::cin, events_file);
        int nevents, query_count;
        std::cin >> nevents >> query_count;
        if (nevents <= 0 || query_count < 0) throw std::runtime_error("Invalid job size");
        std::vector<Query> queries(query_count);
        std::vector<double> kappas;
        std::vector<ResolutionGroup> groups;
        for (int index = 0; index < query_count; ++index) {
            Query& query = queries[index];
            std::string algorithm;
            std::cin >> query.order >> query.kappa >> algorithm >> query.resolution >> query.log_min >> query.bins;
            if (!std::cin || query.order < 2 || query.order > 8 || query.kappa < 1 || query.kappa > 2 ||
                (algorithm != "ca" && algorithm != "kt") || query.resolution <= 0 || query.log_min >= 0 || query.bins < 1)
                throw std::runtime_error("Invalid weighted query");
            query.algorithm = algorithm == "ca" ? 0 : 1;
            query.histogram.assign(query.bins, 0);
            auto kappa = std::find(kappas.begin(), kappas.end(), query.kappa);
            if (kappa == kappas.end()) {
                query.kappa_index = kappas.size();
                kappas.push_back(query.kappa);
            } else query.kappa_index = kappa - kappas.begin();
            auto group = std::find_if(groups.begin(), groups.end(), [&](const ResolutionGroup& value) {
                return value.algorithm == query.algorithm && value.resolution == query.resolution;
            });
            if (group == groups.end()) {
                groups.push_back({query.algorithm, query.resolution, {}});
                group = groups.end() - 1;
            }
            auto axis = std::find_if(group->axes.begin(), group->axes.end(), [&](const AxisGroup& value) {
                return value.bins == query.bins && value.log_min == query.log_min;
            });
            if (axis == group->axes.end()) {
                group->axes.push_back({query.log_min, query.bins, {}});
                axis = group->axes.end() - 1;
            }
            axis->queries.push_back(index);
        }
        auto events = read_events(events_file, nevents);
        for (const auto& event : events) {
            double total = 0;
            for (const auto& particle : event) total += particle.pt;
            std::vector<fastjet::PseudoJet> particles;
            particles.reserve(event.size());
            for (const auto& particle : event) {
                double phi = std::remainder(particle.phi, 2 * pi);
                fastjet::PseudoJet jet(particle.pt * std::cos(phi), particle.pt * std::sin(phi),
                                      particle.pt * std::sinh(particle.rapidity), particle.pt * std::cosh(particle.rapidity));
                jet.set_user_index(particles.size());
                particles.push_back(jet);
            }
            for (Query& query : queries) {
                double contact = 0;
                for (const auto& particle : event) contact += std::pow(particle.pt / total, query.kappa * query.order);
                query.histogram[0] += contact;
            }
            for (int algorithm = 0; algorithm <= 1; ++algorithm) {
                if (std::none_of(groups.begin(), groups.end(), [&](const ResolutionGroup& group) { return group.algorithm == algorithm; })) continue;
                fastjet::JetDefinition definition(algorithm == 0 ? fastjet::cambridge_algorithm : fastjet::kt_algorithm, radius, fastjet::pt_scheme);
                fastjet::ClusterSequence sequence(particles, definition);
                auto roots = sequence.inclusive_jets(0);
                if (roots.size() != 1) throw std::runtime_error("The event does not cluster into one R=1.5 jet");
                TreeData tree(sequence, event, kappas, total);
                const auto& history = sequence.history();
                const auto& jets = sequence.jets();
                for (const auto& entry : history) {
                    if (entry.parent1 < 0 || entry.parent2 < 0 || entry.jetp_index < 0) continue;
                    const auto& left = jets[history[entry.parent1].jetp_index];
                    const auto& right = jets[history[entry.parent2].jetp_index];
                    double angle_squared = left.squared_distance(right);
                    for (const auto& group : groups) {
                        if (group.algorithm != algorithm) continue;
                        double cutoff = angle_squared / (radius * radius * group.resolution);
                        auto left_subjets = left.exclusive_subjets(cutoff);
                        auto right_subjets = right.exclusive_subjets(cutoff);
                        std::vector<int> points;
                        points.reserve(left_subjets.size() + right_subjets.size());
                        for (const auto& subjet : left_subjets) points.push_back(history[subjet.cluster_hist_index()].jetp_index);
                        for (const auto& subjet : right_subjets) points.push_back(history[subjet.cluster_hist_index()].jetp_index);
                        ++split_count;
                        subjet_count += points.size();
                        largest_split = std::max(largest_split, int(points.size()));
                        for (const auto& axis : group.axes) accumulate_axis(tree, points, left_subjets.size(), axis, queries);
                    }
                }
            }
        }
        std::cout << std::setprecision(17) << "{\"histograms\":[";
        for (int query = 0; query < query_count; ++query) {
            if (query) std::cout << ',';
            std::cout << '[';
            for (int bin = 0; bin < queries[query].bins; ++bin) {
                if (bin) std::cout << ',';
                double value = std::max(0.0, queries[query].histogram[bin] / nevents);
                if (!std::isfinite(value)) throw std::runtime_error("Nonfinite histogram");
                std::cout << value;
            }
            std::cout << ']';
        }
        std::cout << "],\"claims\":{\"method\":\"Exact FastJet pt-scheme split resolution; batched weighted clique moments with replacement, true-twin compression, and analytic complete-graph sums.\",\"limitations\":\"Floating-point roundoff; exact graph recursion has data-dependent runtime.\"}}\n";
        if (std::getenv("EEC_STATS")) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
            std::cerr << "seconds=" << elapsed << " splits=" << split_count << " subjets=" << subjet_count
                      << " max_subjets=" << largest_split << " recursions=" << recursion_calls << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "weighted engine: " << error.what() << '\n';
        return 1;
    }
}
