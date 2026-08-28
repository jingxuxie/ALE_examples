#include <fastjet/ClusterSequence.hh>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

constexpr double PI = 3.141592653589793238462643383279502884;

struct Particle {
    double pt;
    double rapidity;
    double phi;
};

struct Query {
    double kappa;
    std::vector<double> histogram;
    std::vector<double> weights;
};

struct Axis {
    int observable;
    int bins;
    double log_min;
    std::vector<double> squared_edges;
    std::vector<std::size_t> query_indices;

    Axis(int observable_in, int bins_in, double log_min_in)
        : observable(observable_in), bins(bins_in), log_min(log_min_in) {
        double upper = observable == 0 ? 10000.0 : PI;
        double log_upper = std::log10(upper);
        int finite_bins = bins - 2;
        squared_edges.reserve(bins - 1);
        for (int edge_index = 0; edge_index <= finite_bins; ++edge_index) {
            double edge = edge_index == finite_bins ? upper : std::pow(
                10.0, log_min + (log_upper - log_min) * edge_index / finite_bins
            );
            squared_edges.push_back(edge * edge);
        }
    }

    std::size_t bin(double coordinate_squared) const {
        if (!(coordinate_squared > 0.0)) {
            return 0;
        }
        return std::upper_bound(
            squared_edges.begin(), squared_edges.end(), coordinate_squared
        ) - squared_edges.begin();
    }
};

fastjet::JetDefinition definition(int geometry, int algorithm, double radius) {
    if (geometry == 1) {
        return fastjet::JetDefinition(
            fastjet::ee_genkt_algorithm, radius, static_cast<double>(algorithm),
            fastjet::E_scheme, fastjet::Best
        );
    }
    auto jet_algorithm = fastjet::cambridge_algorithm;
    if (algorithm == 1) {
        jet_algorithm = fastjet::kt_algorithm;
    } else if (algorithm == -1) {
        jet_algorithm = fastjet::antikt_algorithm;
    }
    return fastjet::JetDefinition(
        jet_algorithm, radius, fastjet::E_scheme, fastjet::Best
    );
}

struct ClusterGroup {
    int geometry;
    int algorithm;
    double radius;
    fastjet::JetDefinition jet_definition;
    std::vector<Axis> axes;
    std::vector<std::size_t> query_indices;
    bool need_mass = false;
    bool need_angular = false;

    ClusterGroup(int geometry_in, int algorithm_in, double radius_in)
        : geometry(geometry_in), algorithm(algorithm_in), radius(radius_in),
          jet_definition(definition(geometry, algorithm, radius)) {}
};

std::vector<std::vector<Particle>> read_events(const char* path, int nevents) {
    std::ifstream stream(path);
    if (!stream) {
        throw std::runtime_error("Cannot open events file");
    }
    std::vector<std::vector<Particle>> events(nevents);
    std::string line;
    while (std::getline(stream, line)) {
        const char* cursor = line.c_str();
        while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r') {
            ++cursor;
        }
        if (*cursor == '\0' || *cursor == '#') {
            continue;
        }
        char* after;
        long event_id = std::strtol(cursor, &after, 10);
        if (after == cursor || event_id < 0 || event_id >= nevents) {
            throw std::runtime_error("Invalid event ID");
        }
        cursor = after;
        double values[3];
        for (int field = 0; field < 3; ++field) {
            values[field] = std::strtod(cursor, &after);
            if (after == cursor || !std::isfinite(values[field])) {
                throw std::runtime_error("Invalid constituent record");
            }
            cursor = after;
        }
        if (values[0] <= 0.0) {
            throw std::runtime_error("Constituent pt must be positive");
        }
        auto& event = events[event_id];
        if (event.empty()) {
            event.reserve(32);
        }
        event.push_back({values[0], values[1], values[2]});
    }
    return events;
}

struct SubjetData {
    double px;
    double py;
    double pz;
    double energy;
    double mass_squared;
    double rapidity;
    double phi;
};

double angular_squared(const SubjetData& first, const SubjetData& second, int geometry) {
    if (geometry == 0) {
        double rapidity_delta = first.rapidity - second.rapidity;
        double phi_delta = std::abs(first.phi - second.phi);
        if (phi_delta > PI) {
            phi_delta = 2.0 * PI - phi_delta;
        }
        return rapidity_delta * rapidity_delta + phi_delta * phi_delta;
    }
    double dot_product = first.px * second.px + first.py * second.py + first.pz * second.pz;
    double cross_x = first.py * second.pz - first.pz * second.py;
    double cross_y = first.pz * second.px - first.px * second.pz;
    double cross_z = first.px * second.py - first.py * second.px;
    double angle = std::atan2(std::hypot(cross_x, cross_y, cross_z), dot_product);
    return angle * angle;
}

void accumulate_group(
    const ClusterGroup& group, const std::vector<fastjet::PseudoJet>& particles,
    double total_pt, double total_energy, std::vector<Query>& queries,
    std::vector<SubjetData>& subjet_data
) {
    fastjet::ClusterSequence sequence(particles, group.jet_definition);
    auto subjets = sequence.inclusive_jets(0.0);
    std::size_t count = subjets.size();
    double denominator = group.geometry == 0 ? total_pt : total_energy;
    subjet_data.resize(count);
    for (std::size_t subjet_index = 0; subjet_index < count; ++subjet_index) {
        const auto& subjet = subjets[subjet_index];
        subjet_data[subjet_index] = {
            subjet.px(), subjet.py(), subjet.pz(), subjet.E(),
            subjet.cluster_hist_index() < static_cast<int>(particles.size())
                ? 0.0 : std::max(0.0, subjet.m2()),
            group.need_angular && group.geometry == 0 ? subjet.rap() : 0.0,
            group.need_angular && group.geometry == 0 ? subjet.phi() : 0.0,
        };
    }
    for (std::size_t query_index : group.query_indices) {
        auto& query = queries[query_index];
        query.weights.resize(count);
        for (std::size_t subjet_index = 0; subjet_index < count; ++subjet_index) {
            const auto& subjet = subjets[subjet_index];
            double fraction = (group.geometry == 0 ? subjet.pt() : subjet.E()) / denominator;
            double weight;
            if (query.kappa == 1.0) {
                weight = fraction;
            } else if (query.kappa == 2.0) {
                weight = fraction * fraction;
            } else if (query.kappa == 0.5) {
                weight = std::sqrt(fraction);
            } else {
                weight = std::pow(fraction, query.kappa);
            }
            query.weights[subjet_index] = weight;
        }
    }
    for (std::size_t first_index = 0; first_index < count; ++first_index) {
        const auto& first = subjet_data[first_index];
        for (const auto& axis : group.axes) {
            std::size_t bin = axis.observable == 0 ? axis.bin(first.mass_squared) : 0;
            for (std::size_t query_index : axis.query_indices) {
                auto& query = queries[query_index];
                double weight = query.weights[first_index];
                query.histogram[bin] += weight * weight;
            }
        }
        for (std::size_t second_index = first_index + 1; second_index < count; ++second_index) {
            const auto& second = subjet_data[second_index];
            double mass_squared = 0.0;
            double distance_squared = 0.0;
            if (group.need_mass) {
                double energy = first.energy + second.energy;
                double longitudinal = first.pz + second.pz;
                double transverse_x = first.px + second.px;
                double transverse_y = first.py + second.py;
                mass_squared = std::max(0.0, (energy + longitudinal) * (energy - longitudinal)
                    - transverse_x * transverse_x - transverse_y * transverse_y);
            }
            if (group.need_angular) {
                distance_squared = angular_squared(first, second, group.geometry);
            }
            for (const auto& axis : group.axes) {
                std::size_t bin = axis.bin(axis.observable == 0 ? mass_squared : distance_squared);
                for (std::size_t query_index : axis.query_indices) {
                    auto& query = queries[query_index];
                    query.histogram[bin] += 2.0 * query.weights[first_index] * query.weights[second_index];
                }
            }
        }
    }
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error("Usage: engine EVENTS_FILE < QUERY_CONFIG");
        }
        std::ios::sync_with_stdio(false);
        std::cin.tie(nullptr);
        fastjet::ClusterSequence::set_fastjet_banner_stream(nullptr);
        int nevents;
        int query_count;
        if (!(std::cin >> nevents >> query_count) || nevents < 0 || query_count < 0) {
            throw std::runtime_error("Invalid query header");
        }
        std::vector<Query> queries;
        std::vector<ClusterGroup> groups;
        queries.reserve(query_count);
        for (int query_index = 0; query_index < query_count; ++query_index) {
            int geometry, algorithm, observable, bins;
            double radius, kappa, log_min;
            if (!(std::cin >> geometry >> algorithm >> radius >> observable >> kappa >> log_min >> bins)) {
                throw std::runtime_error("Invalid query");
            }
            queries.push_back({kappa, std::vector<double>(bins, 0.0), {}});
            auto group = std::find_if(groups.begin(), groups.end(), [&](const ClusterGroup& candidate) {
                return candidate.geometry == geometry && candidate.algorithm == algorithm && candidate.radius == radius;
            });
            if (group == groups.end()) {
                groups.emplace_back(geometry, algorithm, radius);
                group = groups.end() - 1;
            }
            group->query_indices.push_back(query_index);
            group->need_mass = group->need_mass || observable == 0;
            group->need_angular = group->need_angular || observable == 1;
            auto axis = std::find_if(group->axes.begin(), group->axes.end(), [&](const Axis& candidate) {
                return candidate.observable == observable && candidate.bins == bins && candidate.log_min == log_min;
            });
            if (axis == group->axes.end()) {
                group->axes.emplace_back(observable, bins, log_min);
                axis = group->axes.end() - 1;
            }
            axis->query_indices.push_back(query_index);
        }
        auto events = read_events(argv[1], nevents);
        std::vector<fastjet::PseudoJet> particles;
        std::vector<SubjetData> subjet_data;
        for (const auto& event : events) {
            if (event.empty()) {
                continue;
            }
            particles.clear();
            particles.reserve(event.size());
            double total_pt = 0.0;
            double total_energy = 0.0;
            for (const auto& particle : event) {
                double phi = particle.phi;
                if (std::abs(phi) > 2.0 * PI) {
                    phi = std::remainder(phi, 2.0 * PI);
                }
                double energy = particle.pt * std::cosh(particle.rapidity);
                particles.emplace_back(
                    particle.pt * std::cos(phi), particle.pt * std::sin(phi),
                    particle.pt * std::sinh(particle.rapidity), energy
                );
                particles.back().set_user_index(static_cast<int>(particles.size() - 1));
                total_pt += particle.pt;
                total_energy += energy;
            }
            if (!(std::isfinite(total_energy) && std::isfinite(total_pt))) {
                throw std::runtime_error("Four-vector overflow in input");
            }
            for (const auto& group : groups) {
                accumulate_group(group, particles, total_pt, total_energy, queries, subjet_data);
            }
        }
        std::cout << std::setprecision(17) << "{\"histograms\":[";
        double normalization = nevents == 0 ? 1.0 : 1.0 / nevents;
        for (std::size_t query_index = 0; query_index < queries.size(); ++query_index) {
            if (query_index != 0) {
                std::cout << ',';
            }
            std::cout << '[';
            const auto& histogram = queries[query_index].histogram;
            for (std::size_t bin_index = 0; bin_index < histogram.size(); ++bin_index) {
                if (bin_index != 0) {
                    std::cout << ',';
                }
                double value = histogram[bin_index] * normalization;
                if (!std::isfinite(value)) {
                    throw std::runtime_error("Nonfinite histogram value");
                }
                std::cout << value;
            }
            std::cout << ']';
        }
        std::cout << "]}\n";
    } catch (const std::exception& error) {
        std::cerr << "ewoc: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
