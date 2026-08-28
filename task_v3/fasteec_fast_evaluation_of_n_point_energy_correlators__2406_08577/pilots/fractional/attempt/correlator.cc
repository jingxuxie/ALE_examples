#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "fastjet/ClusterSequence.hh"

using Mask = std::uint32_t;
constexpr unsigned MAX_MASKS = 1u << 16;
constexpr double TWO_PI = 6.283185307179586476925286766559;

struct Particle {
    double pt;
    double rapidity;
    double phi;
};

struct Query {
    double nu;
    int cap;
    double log_min;
    int bins;
    std::vector<long double> histogram;
    std::vector<long double> values;
    std::vector<std::uint64_t> stamps;
    std::array<double, 256> left_powers{};
    std::array<double, 256> right_powers{};
    std::array<std::uint64_t, 256> left_stamps{};
    std::array<std::uint64_t, 256> right_stamps{};
};

struct AxisGroup {
    double log_min;
    int bins;
    std::vector<int> queries;
};

struct ResolutionGroup {
    int cap;
    std::vector<AxisGroup> axes;
};

struct Edge {
    int first;
    int second;
    int bin;
};

class Evaluator {
public:
    explicit Evaluator(std::vector<Query> input_queries, bool use_mobius)
        : queries(std::move(input_queries)), mobius(use_mobius),
          coefficients(MAX_MASKS), coefficient_stamps(MAX_MASKS) {
        for (int query_index = 0; query_index < static_cast<int>(queries.size()); ++query_index) {
            Query &query = queries[query_index];
            query.histogram.assign(query.bins, 0);
            if (query.nu == 1.0) continue;
            query.values.resize(MAX_MASKS);
            query.stamps.resize(MAX_MASKS);
            for (int limit = 1; limit <= 8; ++limit) {
                const int cap = std::min(query.cap, limit);
                auto &local_groups = groups[limit];
                auto resolution = std::find_if(local_groups.begin(), local_groups.end(),
                    [&](const ResolutionGroup &group) { return group.cap == cap; });
                if (resolution == local_groups.end()) {
                    local_groups.push_back({cap, {}});
                    resolution = local_groups.end() - 1;
                }
                auto axis = std::find_if(resolution->axes.begin(), resolution->axes.end(),
                    [&](const AxisGroup &group) {
                        return group.bins == query.bins && group.log_min == query.log_min;
                    });
                if (axis == resolution->axes.end()) {
                    resolution->axes.push_back({query.log_min, query.bins, {}});
                    axis = resolution->axes.end() - 1;
                }
                axis->queries.push_back(query_index);
            }
        }
        active.reserve(512);
        pending.reserve(512);
        cliques.reserve(128);
        edges.reserve(120);
        previous.resize(queries.size());
    }

    void event(const std::vector<Particle> &particles) {
        double total_pt = 0;
        for (const Particle &particle : particles) total_pt += particle.pt;
        if (!(total_pt > 0) || !std::isfinite(total_pt)) {
            throw std::runtime_error("An event has invalid scalar pt");
        }
        for (Query &query : queries) {
            if (query.nu == 1.0) {
                query.histogram[0] += 1;
            } else {
                for (const Particle &particle : particles) {
                    query.histogram[0] += std::pow(particle.pt / total_pt, query.nu);
                }
            }
        }
        if (groups[8].empty() || particles.size() == 1) return;
        std::vector<fastjet::PseudoJet> inputs;
        inputs.reserve(particles.size());
        for (const Particle &particle : particles) {
            double phi = std::fmod(particle.phi, TWO_PI);
            if (phi < 0) phi += TWO_PI;
            fastjet::PseudoJet input;
            input.reset_PtYPhiM(particle.pt, particle.rapidity, phi, 0.0);
            input.set_user_index(static_cast<int>(inputs.size()));
            inputs.push_back(input);
        }
        const fastjet::JetDefinition definition(fastjet::genkt_algorithm, 1.5, 0.0, fastjet::pt_scheme);
        fastjet::ClusterSequence sequence(inputs, definition);
        std::vector<fastjet::PseudoJet> roots = sequence.inclusive_jets(0);
        if (roots.size() != 1) throw std::runtime_error("Input event does not form one R=1.5 jet");
        visit(roots[0], total_pt);
    }

    void output(int nevents) const {
        std::cout << std::setprecision(17) << '[';
        for (std::size_t query_index = 0; query_index < queries.size(); ++query_index) {
            if (query_index) std::cout << ',';
            std::cout << '[';
            const Query &query = queries[query_index];
            for (int bin_index = 0; bin_index < query.bins; ++bin_index) {
                if (bin_index) std::cout << ',';
                const double value = static_cast<double>(query.histogram[bin_index] / nevents);
                if (!std::isfinite(value)) throw std::runtime_error("Nonfinite result");
                std::cout << value;
            }
            std::cout << ']';
        }
        std::cout << "]\n";
    }

private:
    std::vector<Query> queries;
    std::array<std::vector<ResolutionGroup>, 9> groups;
    bool mobius;
    std::uint64_t node_stamp = 0;
    std::uint64_t coefficient_stamp = 0;
    int left_count = 0;
    int count = 0;
    Mask left_mask = 0;
    Mask right_mask = 0;
    Mask full_mask = 0;
    std::array<double, 256> left_sums{};
    std::array<double, 256> right_sums{};
    std::array<double, 16> fractions{};
    std::array<Mask, 16> adjacency{};
    std::array<std::array<double, 16>, 16> log_distances{};
    std::vector<int> coefficients;
    std::vector<std::uint64_t> coefficient_stamps;
    std::vector<Mask> active;
    std::vector<std::pair<Mask, int>> pending;
    std::vector<Mask> cliques;
    std::vector<Edge> edges;
    std::vector<long double> previous;

    bool crosses(Mask mask) const {
        return (mask & left_mask) && (mask & right_mask);
    }

    long double cross_power(Query &query, Mask mask) {
        if (!crosses(mask)) return 0;
        if (query.stamps[mask] == node_stamp) return query.values[mask];
        const Mask left = mask & left_mask;
        const Mask right = mask >> left_count;
        const double left_sum = left_sums[left];
        const double right_sum = right_sums[right];
        long double value;
        if (query.nu == 2.0) {
            value = 2.0L * left_sum * right_sum;
        } else if (query.nu == 3.0) {
            value = 3.0L * left_sum * right_sum * (left_sum + right_sum);
        } else {
            if (query.left_stamps[left] != node_stamp) {
                query.left_powers[left] = std::pow(left_sum, query.nu);
                query.left_stamps[left] = node_stamp;
            }
            if (query.right_stamps[right] != node_stamp) {
                query.right_powers[right] = std::pow(right_sum, query.nu);
                query.right_stamps[right] = node_stamp;
            }
            value = static_cast<long double>(std::pow(left_sum + right_sum, query.nu))
                - query.left_powers[left] - query.right_powers[right];
        }
        query.stamps[mask] = node_stamp;
        query.values[mask] = value;
        return value;
    }

    void maximal_cliques(Mask selected, Mask candidates, Mask excluded) {
        if (!crosses(selected | candidates)) return;
        if (!(candidates | excluded)) {
            cliques.push_back(selected);
            return;
        }
        int pivot = -1;
        int best_degree = -1;
        for (Mask choices = candidates | excluded; choices; choices &= choices - 1) {
            const int vertex = __builtin_ctz(choices);
            const int degree = __builtin_popcount(candidates & adjacency[vertex]);
            if (degree > best_degree) {
                best_degree = degree;
                pivot = vertex;
            }
        }
        Mask choices = candidates & ~adjacency[pivot];
        while (choices) {
            const Mask bit = choices & -choices;
            const int vertex = __builtin_ctz(bit);
            maximal_cliques(selected | bit, candidates & adjacency[vertex], excluded & adjacency[vertex]);
            candidates &= ~bit;
            excluded |= bit;
            choices &= ~bit;
        }
    }

    void clique_coefficients(Mask vertices) {
        cliques.clear();
        maximal_cliques(0, vertices, 0);
        ++coefficient_stamp;
        active.clear();
        for (Mask clique : cliques) {
            pending.clear();
            for (Mask mask : active) {
                if (!coefficients[mask]) continue;
                const Mask intersection = mask & clique;
                if (crosses(intersection)) pending.emplace_back(intersection, -coefficients[mask]);
            }
            pending.emplace_back(clique, 1);
            for (const auto &term : pending) {
                if (coefficient_stamps[term.first] != coefficient_stamp) {
                    coefficient_stamps[term.first] = coefficient_stamp;
                    coefficients[term.first] = term.second;
                    active.push_back(term.first);
                } else {
                    coefficients[term.first] += term.second;
                }
            }
        }
    }

    void brute_axis(const AxisGroup &axis, const std::vector<Edge> &edges) {
        std::array<std::array<int, 16>, 16> pair_bins{};
        for (const Edge &edge : edges) {
            pair_bins[edge.first][edge.second] = pair_bins[edge.second][edge.first] = edge.bin;
        }
        std::vector<int> diameters(full_mask + 1);
        std::vector<long double> sums(full_mask + 1);
        for (Mask mask = 1; mask <= full_mask; ++mask) {
            const int vertex = __builtin_ctz(mask);
            const Mask rest = mask & (mask - 1);
            sums[mask] = sums[rest] + fractions[vertex];
            int diameter = diameters[rest];
            for (Mask remaining = rest; remaining; remaining &= remaining - 1) {
                diameter = std::max(diameter, pair_bins[vertex][__builtin_ctz(remaining)]);
            }
            diameters[mask] = diameter;
        }
        std::vector<long double> weights(full_mask + 1);
        for (int query_index : axis.queries) {
            Query &query = queries[query_index];
            weights[0] = 0;
            for (Mask mask = 1; mask <= full_mask; ++mask) {
                weights[mask] = std::pow(sums[mask], static_cast<long double>(query.nu));
            }
            for (Mask bit = 1; bit <= full_mask; bit <<= 1) {
                for (Mask start = 0; start <= full_mask; start += 2 * bit) {
                    for (Mask offset = 0; offset < bit; ++offset) {
                        weights[start + bit + offset] -= weights[start + offset];
                    }
                }
            }
            for (Mask mask = 1; mask <= full_mask; ++mask) {
                if (crosses(mask)) query.histogram[diameters[mask]] += weights[mask];
            }
        }
    }

    void evaluate_axis(const AxisGroup &axis) {
        edges.clear();
        for (int first = 0; first < count; ++first) {
            for (int second = first + 1; second < count; ++second) {
                const double logarithm = log_distances[first][second];
                int bin = 0;
                if (logarithm > axis.log_min) {
                    const double position = (logarithm - axis.log_min) * axis.bins / (-axis.log_min);
                    bin = position >= axis.bins ? axis.bins - 1 : static_cast<int>(position);
                }
                edges.push_back({first, second, bin});
            }
        }
        if (mobius) {
            brute_axis(axis, edges);
            return;
        }
        if (edges.size() > 24 && axis.bins <= 128) {
            std::array<int, 128> offsets;
            std::fill_n(offsets.begin(), axis.bins, 0);
            for (const Edge &edge : edges) ++offsets[edge.bin];
            int start = 0;
            for (int bin = 0; bin < axis.bins; ++bin) {
                const int size = offsets[bin];
                offsets[bin] = start;
                start += size;
            }
            std::array<Edge, 120> ordered;
            for (const Edge &edge : edges) ordered[offsets[edge.bin]++] = edge;
            std::copy_n(ordered.begin(), edges.size(), edges.begin());
        } else {
            std::sort(edges.begin(), edges.end(), [](const Edge &first, const Edge &second) {
                return first.bin < second.bin;
            });
        }
        adjacency.fill(0);
        std::fill_n(previous.begin(), axis.queries.size(), 0);
        std::size_t edge_index = 0;
        Mask cross_vertices = 0;
        while (edge_index < edges.size()) {
            const int bin = edges[edge_index].bin;
            do {
                const Edge &edge = edges[edge_index++];
                adjacency[edge.first] |= 1u << edge.second;
                adjacency[edge.second] |= 1u << edge.first;
                if (edge.first < left_count && edge.second >= left_count) {
                    cross_vertices |= (1u << edge.first) | (1u << edge.second);
                }
            } while (edge_index < edges.size() && edges[edge_index].bin == bin);
            if (!cross_vertices) continue;
            bool complete = true;
            if (edge_index < edges.size()) {
                for (Mask remaining = cross_vertices; remaining; remaining &= remaining - 1) {
                    const Mask bit = remaining & -remaining;
                    if ((adjacency[__builtin_ctz(bit)] & cross_vertices) != (cross_vertices ^ bit)) {
                        complete = false;
                        break;
                    }
                }
            }
            if (!complete) clique_coefficients(cross_vertices);
            for (std::size_t local_query = 0; local_query < axis.queries.size(); ++local_query) {
                Query &query = queries[axis.queries[local_query]];
                long double cumulative = 0;
                if (complete) {
                    cumulative = cross_power(query, cross_vertices);
                } else {
                    for (Mask mask : active) {
                        if (coefficients[mask]) cumulative += coefficients[mask] * cross_power(query, mask);
                    }
                }
                query.histogram[bin] += cumulative - previous[local_query];
                previous[local_query] = cumulative;
            }
        }
    }

    void split(const fastjet::PseudoJet &first, const fastjet::PseudoJet &second,
               int first_size, int second_size, double total_pt, const ResolutionGroup &group) {
        std::vector<fastjet::PseudoJet> subjets = group.cap == 1
            ? std::vector<fastjet::PseudoJet>{first}
            : (first_size <= group.cap ? first.constituents() : first.exclusive_subjets_up_to(group.cap));
        const std::vector<fastjet::PseudoJet> other = group.cap == 1
            ? std::vector<fastjet::PseudoJet>{second}
            : (second_size <= group.cap ? second.constituents() : second.exclusive_subjets_up_to(group.cap));
        left_count = static_cast<int>(subjets.size());
        subjets.insert(subjets.end(), other.begin(), other.end());
        count = static_cast<int>(subjets.size());
        full_mask = (1u << count) - 1;
        left_mask = (1u << left_count) - 1;
        right_mask = full_mask ^ left_mask;
        ++node_stamp;
        std::array<double, 16> rapidities;
        std::array<double, 16> azimuths;
        for (int index = 0; index < count; ++index) {
            fractions[index] = subjets[index].pt() / total_pt;
            rapidities[index] = subjets[index].rap();
            azimuths[index] = subjets[index].phi();
        }
        left_sums[0] = right_sums[0] = 0;
        for (Mask mask = 1; mask <= left_mask; ++mask) {
            left_sums[mask] = left_sums[mask & (mask - 1)] + fractions[__builtin_ctz(mask)];
        }
        for (Mask mask = 1; mask < (1u << (count - left_count)); ++mask) {
            right_sums[mask] = right_sums[mask & (mask - 1)] + fractions[left_count + __builtin_ctz(mask)];
        }
        for (int first_index = 0; first_index < count; ++first_index) {
            for (int second_index = first_index + 1; second_index < count; ++second_index) {
                const double delta_y = rapidities[first_index] - rapidities[second_index];
                double delta_phi = std::abs(azimuths[first_index] - azimuths[second_index]);
                if (delta_phi > TWO_PI / 2) delta_phi = TWO_PI - delta_phi;
                const double distance = std::sqrt(delta_y * delta_y + delta_phi * delta_phi);
                log_distances[first_index][second_index] = distance > 0
                    ? std::log10(distance) : -std::numeric_limits<double>::infinity();
            }
        }
        for (const AxisGroup &axis : group.axes) evaluate_axis(axis);
    }

    int visit(const fastjet::PseudoJet &node, double total_pt) {
        fastjet::PseudoJet first, second;
        if (!node.has_parents(first, second)) return 1;
        const int first_size = visit(first, total_pt);
        const int second_size = visit(second, total_pt);
        const int limit = std::min(8, std::max(first_size, second_size));
        for (const ResolutionGroup &group : groups[limit]) {
            split(first, second, first_size, second_size, total_pt, group);
        }
        return first_size + second_size;
    }
};

std::vector<std::vector<Particle>> read_events(const std::string &path, int nevents) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Cannot open events file");
    std::vector<std::vector<Particle>> events(nevents);
    std::string line;
    while (std::getline(input, line)) {
        const char *cursor = line.c_str();
        while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r') ++cursor;
        if (!*cursor || *cursor == '#') continue;
        char *end = nullptr;
        const long event_id = std::strtol(cursor, &end, 10);
        if (end == cursor || event_id < 0 || event_id >= nevents) {
            throw std::runtime_error("Invalid event id");
        }
        cursor = end;
        Particle particle;
        particle.pt = std::strtod(cursor, &end);
        if (end == cursor) throw std::runtime_error("Missing pt");
        cursor = end;
        particle.rapidity = std::strtod(cursor, &end);
        if (end == cursor) throw std::runtime_error("Missing rapidity");
        cursor = end;
        particle.phi = std::strtod(cursor, &end);
        if (end == cursor) throw std::runtime_error("Missing azimuth");
        if (!(particle.pt > 0) || !std::isfinite(particle.pt)
            || !std::isfinite(particle.rapidity) || !std::isfinite(particle.phi)) {
            throw std::runtime_error("Invalid constituent");
        }
        events[event_id].push_back(particle);
    }
    for (const auto &event : events) {
        if (event.empty()) throw std::runtime_error("Missing event");
    }
    return events;
}

int main(int argc, char **argv) {
    try {
        if (argc != 4) throw std::runtime_error("Expected events_file nevents algorithm");
        const int nevents = std::stoi(argv[2]);
        if (nevents <= 0) throw std::runtime_error("Invalid event count");
        int query_count;
        if (!(std::cin >> query_count) || query_count < 0) throw std::runtime_error("Invalid query count");
        std::vector<Query> queries(query_count);
        for (Query &query : queries) {
            int nsub;
            if (!(std::cin >> query.nu >> nsub >> query.log_min >> query.bins)) {
                throw std::runtime_error("Invalid query");
            }
            query.cap = nsub / 2;
        }
        fastjet::ClusterSequence::set_fastjet_banner_stream(nullptr);
        Evaluator evaluator(std::move(queries), std::string(argv[3]) == "mobius");
        const auto events = read_events(argv[1], nevents);
        for (const auto &event : events) evaluator.event(event);
        evaluator.output(nevents);
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
