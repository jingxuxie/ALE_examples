#include <algorithm>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr double pi = 3.14159265358979323846;

struct Particle {
    double pt;
    double rapidity;
    double phi;
};

struct Direction {
    double radius;
    double rapidity_component;
    double phi_component;
    double weight;
};

std::size_t checked_product(std::size_t left, std::size_t right) {
    if (right != 0 && left > std::numeric_limits<std::size_t>::max() / right) {
        throw std::invalid_argument("Histogram dimensions overflow size_t.");
    }
    return left * right;
}

std::size_t positive_integer(const char* text) {
    const std::string value(text);
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos) {
        throw std::invalid_argument("Expected a positive integer: " + value);
    }
    const unsigned long long parsed = std::stoull(value);
    if (parsed == 0 || parsed > std::numeric_limits<std::size_t>::max()) {
        throw std::invalid_argument("Integer is outside the supported range: " + value);
    }
    return static_cast<std::size_t>(parsed);
}

double wrap_phi(double angle) {
    angle = std::fmod(angle, 2.0 * pi);
    if (angle > pi) {
        angle -= 2.0 * pi;
    }
    if (angle <= -pi) {
        angle += 2.0 * pi;
    }
    return angle;
}

double oriented_angle(const Direction& reference, const Direction& target) {
    if (reference.radius == 0.0 || target.radius == 0.0) {
        return 0.0;
    }
    const double dot = reference.rapidity_component * target.rapidity_component
                     + reference.phi_component * target.phi_component;
    const double determinant = reference.rapidity_component * target.phi_component
                             - reference.phi_component * target.rapidity_component;
    return wrap_phi(std::atan2(determinant, dot));
}

double power_difference(double prefix, double weight, double exponent) {
    if (weight == 0.0) {
        return 0.0;
    }
    if (exponent == 1.0) {
        return weight;
    }
    if (prefix == 0.0) {
        return std::pow(weight, exponent);
    }
    return std::pow(prefix + weight, exponent)
         * (-std::expm1(-exponent * std::log1p(weight / prefix)));
}

class Histogram {
public:
    Histogram(std::size_t order, double log_min, std::size_t bins,
              std::size_t ratio_bins, std::size_t phi_bins,
              const std::vector<double>& exponents)
        : order_(order), log_min_(log_min), min_radius_(std::pow(10.0, log_min)),
          bins_(bins), ratio_bins_(ratio_bins), phi_bins_(phi_bins),
          angular_size_(checked_product(ratio_bins, phi_bins)), exponents_(exponents),
          unit_exponents_(std::all_of(exponents.begin(), exponents.end(),
                                     [](double exponent) { return exponent == 1.0; })) {
        if ((order != 3 && order != 4) || bins < 3 || !std::isfinite(log_min)
                || log_min >= 0.0 || min_radius_ == 0.0) {
            throw std::invalid_argument("Require order 3 or 4, bins >= 3, and finite representable log_min < 0.");
        }
        if (exponents_.size() != order_ - 1) {
            throw std::invalid_argument("Require order-1 exponents.");
        }
        double exponent_sum = 1.0;
        for (const double exponent : exponents_) {
            if (!(exponent > 0.0) || !std::isfinite(exponent)) {
                throw std::invalid_argument("Exponents must be finite and strictly positive.");
            }
            exponent_sum += exponent;
        }
        if (!std::isfinite(exponent_sum)) {
            throw std::invalid_argument("The sum of exponents is not representable.");
        }
        const std::size_t first_size = checked_product(bins_, angular_size_);
        values_.assign(order_ == 3 ? first_size : checked_product(first_size, angular_size_), 0.0);
    }

    void add_jet(const std::vector<Particle>& particles) {
        long double total_pt = 0.0L;
        for (const auto& particle : particles) {
            total_pt += particle.pt;
        }
        if (particles.empty() || !(total_pt > 0.0L) || !std::isfinite(total_pt)) {
            throw std::invalid_argument("Every jet must have finite positive total transverse momentum.");
        }

        std::vector<double> weights;
        weights.reserve(particles.size());
        for (const auto& particle : particles) {
            weights.push_back(static_cast<double>(particle.pt / total_pt));
        }

        std::vector<Direction> directions;
        directions.reserve(particles.size() - 1);
        for (std::size_t special = 0; special < particles.size(); ++special) {
            if (weights[special] == 0.0) {
                continue;
            }
            directions.clear();
            for (std::size_t index = 0; index < particles.size(); ++index) {
                if (index == special) {
                    continue;
                }
                double rapidity_component = particles[index].rapidity - particles[special].rapidity;
                double phi_component = wrap_phi(particles[index].phi - particles[special].phi);
                const double radius = std::sqrt(rapidity_component * rapidity_component
                                              + phi_component * phi_component);
                if (!std::isfinite(radius)) {
                    throw std::invalid_argument("Particle separations must be finite.");
                }
                if (radius != 0.0) {
                    rapidity_component /= radius;
                    phi_component /= radius;
                }
                directions.push_back({radius, rapidity_component, phi_component, weights[index]});
            }
            std::stable_sort(directions.begin(), directions.end(),
                             [](const Direction& left, const Direction& right) {
                                 return left.radius < right.radius;
                             });
            if (order_ == 3 && unit_exponents_) {
                add_three(weights[special], directions);
            } else if (order_ == 4 && unit_exponents_) {
                add_four(weights[special], directions);
            } else if (order_ == 3) {
                add_three_weighted(weights[special], directions);
            } else {
                add_four_weighted(weights[special], directions);
            }
        }
    }

    void write(const std::string& filename, std::size_t jets) const {
        std::ofstream output(filename);
        if (!output) {
            throw std::runtime_error("Cannot open output file: " + filename);
        }
        output << std::scientific << std::setprecision(17);
        for (const double value : values_) {
            if (!std::isfinite(value)) {
                throw std::runtime_error("Nonfinite histogram weight; exponent/input range is unsupported.");
            }
            output << value / static_cast<double>(jets) << '\n';
        }
        output.close();
        if (!output) {
            throw std::runtime_error("Failed to write complete histogram: " + filename);
        }
    }

private:
    std::size_t radial_bin(double radius) const {
        if (radius < min_radius_) {
            return 0;
        }
        if (radius >= 1.0) {
            return bins_ - 1;
        }
        const double position = 1.0 + static_cast<double>(bins_ - 2)
                              * (std::log10(radius) - log_min_) / (-log_min_);
        return std::min(bins_ - 1, static_cast<std::size_t>(position));
    }

    std::size_t ratio_bin(double inner_radius, double outer_radius) const {
        const double ratio = outer_radius == 0.0 ? 0.0 : inner_radius / outer_radius;
        return std::min(ratio_bins_ - 1,
                        static_cast<std::size_t>(ratio * static_cast<double>(ratio_bins_)));
    }

    std::size_t phi_bin(double angle) const {
        const double position = static_cast<double>(phi_bins_) * (angle + pi) / (2.0 * pi);
        return std::min(phi_bins_ - 1, static_cast<std::size_t>(position));
    }

    std::size_t relative_bin(const Direction& reference, const Direction& target) const {
        return ratio_bin(target.radius, reference.radius) * phi_bins_
             + phi_bin(oriented_angle(reference, target));
    }

    void add_three(double special_weight, const std::vector<Direction>& directions) {
        const std::size_t zero_phi = phi_bin(0.0);
        values_[zero_phi] += special_weight * special_weight * special_weight;
        for (std::size_t outer = 0; outer < directions.size(); ++outer) {
            const Direction& first = directions[outer];
            const std::size_t base = radial_bin(first.radius) * angular_size_;
            values_[base + zero_phi] += 2.0 * special_weight * special_weight * first.weight;
            values_[base + (ratio_bins_ - 1) * phi_bins_ + zero_phi]
                += special_weight * first.weight * first.weight;
            const double outer_weight = 2.0 * special_weight * first.weight;
            for (std::size_t inner = 0; inner < outer; ++inner) {
                const Direction& second = directions[inner];
                values_[base + relative_bin(first, second)] += outer_weight * second.weight;
            }
        }
    }

    void add_four(double special_weight, const std::vector<Direction>& directions) {
        if (directions.size() < 3) {
            return;
        }
        std::vector<double> inner_weights(angular_size_, 0.0);
        std::vector<std::size_t> occupied_bins;
        occupied_bins.reserve(std::min(angular_size_, directions.size()));
        for (std::size_t middle = 1; middle + 1 < directions.size(); ++middle) {
            const Direction& second = directions[middle];
            if (second.weight == 0.0) {
                continue;
            }
            for (std::size_t inner = 0; inner < middle; ++inner) {
                const Direction& third = directions[inner];
                if (third.weight == 0.0) {
                    continue;
                }
                const std::size_t cell = relative_bin(second, third);
                if (inner_weights[cell] == 0.0) {
                    occupied_bins.push_back(cell);
                }
                inner_weights[cell] += third.weight;
            }
            const double middle_weight = 6.0 * special_weight * second.weight;
            for (std::size_t outer = middle + 1; outer < directions.size(); ++outer) {
                const Direction& first = directions[outer];
                if (first.weight == 0.0) {
                    continue;
                }
                const std::size_t prefix = radial_bin(first.radius) * angular_size_
                                         + relative_bin(first, second);
                const std::size_t base = prefix * angular_size_;
                const double outer_weight = middle_weight * first.weight;
                for (const std::size_t cell : occupied_bins) {
                    values_[base + cell] += outer_weight * inner_weights[cell];
                }
            }
            for (const std::size_t cell : occupied_bins) {
                inner_weights[cell] = 0.0;
            }
            occupied_bins.clear();
        }
    }

    void add_three_weighted(double special_weight, const std::vector<Direction>& directions) {
        const double first_exponent = exponents_[0];
        const double second_exponent = exponents_[1];
        const std::size_t zero_phi = phi_bin(0.0);
        values_[zero_phi] += std::pow(special_weight, 1.0 + first_exponent + second_exponent);
        double first_prefix = special_weight;
        std::vector<double> second_prefix(phi_bins_, 0.0);
        for (std::size_t outer = 0; outer < directions.size(); ++outer) {
            const Direction& first = directions[outer];
            const std::size_t base = radial_bin(first.radius) * angular_size_;
            const double first_delta = power_difference(first_prefix, first.weight, first_exponent);
            values_[base + zero_phi] += 2.0 * std::pow(special_weight, 1.0 + second_exponent)
                                          * std::pow(first.weight, first_exponent);
            values_[base + (ratio_bins_ - 1) * phi_bins_ + zero_phi]
                += special_weight * std::pow(first.weight, first_exponent + second_exponent);
            std::fill(second_prefix.begin(), second_prefix.end(), 0.0);
            second_prefix[zero_phi] = special_weight;
            for (std::size_t inner = 0; inner < outer; ++inner) {
                const Direction& second = directions[inner];
                const std::size_t cell = relative_bin(first, second);
                const std::size_t phase = cell % phi_bins_;
                const double second_delta = power_difference(second_prefix[phase], second.weight,
                                                              second_exponent);
                values_[base + cell] += 2.0 * special_weight * first_delta * second_delta;
                second_prefix[phase] += second.weight;
            }
            first_prefix += first.weight;
        }
    }

    void add_four_weighted(double special_weight, const std::vector<Direction>& directions) {
        if (directions.size() < 3) {
            return;
        }
        const std::size_t zero_phi = phi_bin(0.0);
        std::vector<std::vector<std::pair<std::size_t, double>>> inner_histograms(directions.size());
        std::vector<double> inner_weights(angular_size_, 0.0);
        std::vector<double> third_prefix(phi_bins_, 0.0);
        std::vector<std::size_t> occupied_bins;
        occupied_bins.reserve(std::min(angular_size_, directions.size()));
        for (std::size_t middle = 1; middle + 1 < directions.size(); ++middle) {
            const Direction& second = directions[middle];
            std::fill(third_prefix.begin(), third_prefix.end(), 0.0);
            third_prefix[zero_phi] = special_weight;
            for (std::size_t inner = 0; inner < middle; ++inner) {
                const Direction& third = directions[inner];
                const std::size_t cell = relative_bin(second, third);
                const std::size_t phase = cell % phi_bins_;
                const double delta = power_difference(third_prefix[phase], third.weight, exponents_[2]);
                if (delta != 0.0) {
                    if (inner_weights[cell] == 0.0) {
                        occupied_bins.push_back(cell);
                    }
                    inner_weights[cell] += delta;
                }
                third_prefix[phase] += third.weight;
            }
            auto& inner_histogram = inner_histograms[middle];
            inner_histogram.reserve(occupied_bins.size());
            for (const std::size_t cell : occupied_bins) {
                inner_histogram.emplace_back(cell, inner_weights[cell]);
                inner_weights[cell] = 0.0;
            }
            occupied_bins.clear();
        }

        double first_prefix = special_weight;
        std::vector<double> second_prefix(phi_bins_, 0.0);
        for (std::size_t outer = 0; outer < directions.size(); ++outer) {
            const Direction& first = directions[outer];
            const double first_delta = power_difference(first_prefix, first.weight, exponents_[0]);
            std::fill(second_prefix.begin(), second_prefix.end(), 0.0);
            second_prefix[zero_phi] = special_weight;
            for (std::size_t middle = 0; middle < outer; ++middle) {
                const Direction& second = directions[middle];
                const std::size_t cell = relative_bin(first, second);
                const std::size_t phase = cell % phi_bins_;
                const double second_delta = power_difference(second_prefix[phase], second.weight,
                                                              exponents_[1]);
                const std::size_t base = (radial_bin(first.radius) * angular_size_ + cell) * angular_size_;
                const double outer_weight = 6.0 * special_weight * first_delta * second_delta;
                for (const auto& entry : inner_histograms[middle]) {
                    values_[base + entry.first] += outer_weight * entry.second;
                }
                second_prefix[phase] += second.weight;
            }
            first_prefix += first.weight;
        }
    }

    std::size_t order_;
    double log_min_;
    double min_radius_;
    std::size_t bins_;
    std::size_t ratio_bins_;
    std::size_t phi_bins_;
    std::size_t angular_size_;
    std::vector<double> exponents_;
    bool unit_exponents_;
    std::vector<double> values_;
};

void process_events(const std::string& filename, std::size_t requested, Histogram& histogram) {
    std::ifstream input(filename);
    if (!input) {
        throw std::runtime_error("Cannot open events file: " + filename);
    }
    std::vector<Particle> particles;
    std::string line;
    long long previous_id = -1;
    std::size_t processed = 0;
    std::size_t line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        if (line.find_first_not_of(" \t\r") == std::string::npos) {
            continue;
        }
        std::istringstream row(line);
        long long event_id;
        Particle particle;
        std::string extra;
        if (!(row >> event_id >> particle.pt >> particle.rapidity >> particle.phi)
                || (row >> extra) || event_id < 0 || !std::isfinite(particle.pt)
                || particle.pt < 0.0 || !std::isfinite(particle.rapidity)
                || !std::isfinite(particle.phi)) {
            throw std::invalid_argument("Invalid particle row at line " + std::to_string(line_number));
        }
        if (!particles.empty() && event_id != previous_id) {
            histogram.add_jet(particles);
            if (++processed == requested) {
                return;
            }
            particles.clear();
            if (event_id < previous_id) {
                throw std::invalid_argument("Event IDs must be grouped in strictly increasing order.");
            }
        }
        particle.phi = wrap_phi(particle.phi);
        particles.push_back(particle);
        previous_id = event_id;
    }
    if (input.bad()) {
        throw std::runtime_error("Failed while reading events file: " + filename);
    }
    if (!particles.empty()) {
        histogram.add_jet(particles);
        ++processed;
    }
    if (processed != requested) {
        throw std::invalid_argument("Events file contains fewer jets than nevents.");
    }
}

}

int main(int argc, char* argv[]) {
    try {
        if (argc < 9) {
            throw std::invalid_argument(
                "Usage: executable events_file nevents order log_min bins ratio_bins phi_bins output_file [nu1 nu2 [nu3]]");
        }
        const std::size_t jets = positive_integer(argv[2]);
        const std::size_t order = positive_integer(argv[3]);
        if (order != 3 && order != 4) {
            throw std::invalid_argument("Order must be 3 or 4.");
        }
        if (argc != 9 && argc != 9 + static_cast<int>(order - 1)) {
            throw std::invalid_argument("Supply either no exponents or exactly order-1 trailing exponents.");
        }
        std::vector<double> exponents(order - 1, 1.0);
        if (argc != 9) {
            for (std::size_t index = 0; index < exponents.size(); ++index) {
                std::size_t consumed = 0;
                const std::string exponent_text(argv[9 + index]);
                exponents[index] = std::stod(exponent_text, &consumed);
                if (consumed != exponent_text.size()) {
                    throw std::invalid_argument("Invalid trailing exponent.");
                }
            }
        }
        std::size_t parsed = 0;
        const std::string log_text(argv[4]);
        const double log_min = std::stod(log_text, &parsed);
        if (parsed != log_text.size()) {
            throw std::invalid_argument("Invalid log_min.");
        }
        Histogram histogram(order, log_min, positive_integer(argv[5]),
                            positive_integer(argv[6]), positive_integer(argv[7]), exponents);
        process_events(argv[1], jets, histogram);
        histogram.write(argv[8], jets);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "resolved_reference: " << error.what() << '\n';
        return 1;
    }
}
