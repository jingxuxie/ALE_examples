#include <algorithm>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <time.h>
#include <vector>

using SteadyClock = std::chrono::steady_clock;

volatile std::sig_atomic_t stopping_signal = 0;

void request_stop(int signal_number) {
    stopping_signal = signal_number;
}

double cpu_seconds() {
    timespec timestamp{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &timestamp) != 0)
        throw std::runtime_error("cannot read process CPU clock");
    return timestamp.tv_sec + timestamp.tv_nsec * 1e-9;
}

double elapsed_seconds(SteadyClock::time_point start) {
    return std::chrono::duration<double>(SteadyClock::now() - start).count();
}

struct Particle {
    double transverse;
    double rapidity;
    double azimuth;
};

class DirectHistogram {
public:
    DirectHistogram(const std::vector<Particle> &particles, int requested_order,
                    double kappa, double log_min, int bins)
        : histogram(bins, 0.0), multiplicity(particles.size()), order(requested_order), indices(order),
          weights(multiplicity), pair_bins(multiplicity * multiplicity, 0),
          factorial(order + 1, 1) {
        double scalar_transverse = 0.0;
        for (const auto &particle : particles) scalar_transverse += particle.transverse;
        for (std::size_t index = 0; index < multiplicity; ++index)
            weights[index] = std::pow(particles[index].transverse / scalar_transverse, kappa);
        for (int index = 1; index <= order; ++index)
            factorial[index] = factorial[index - 1] * index;
        const double period = 2.0 * std::acos(-1.0);
        for (std::size_t first = 0; first < multiplicity; ++first) {
            for (std::size_t second = 0; second < first; ++second) {
                const double distance = std::hypot(
                    particles[first].rapidity - particles[second].rapidity,
                    std::remainder(particles[first].azimuth - particles[second].azimuth, period));
                int position = 0;
                if (distance > std::pow(10.0, log_min))
                    position = static_cast<int>(std::floor((std::log10(distance) - log_min)
                                                          * bins / -log_min));
                position = std::clamp(position, 0, bins - 1);
                pair_bins[first * multiplicity + second] = position;
                pair_bins[second * multiplicity + first] = position;
            }
        }
    }

    void enumerate(int depth = 0, std::size_t minimum_index = 0) {
        if (stopping_signal) return;
        if (depth == order) {
            accumulate();
            return;
        }
        for (std::size_t index = minimum_index; index < multiplicity; ++index) {
            if (stopping_signal) return;
            indices[depth] = index;
            enumerate(depth + 1, index);
        }
    }

    std::vector<double> histogram;
    std::uint64_t multisets_completed = 0;
    std::uint64_t ordered_tuples_accounted_for = 0;

private:
    const std::size_t multiplicity;
    const int order;
    std::vector<std::size_t> indices;
    std::vector<double> weights;
    std::vector<int> pair_bins;
    std::vector<std::uint64_t> factorial;

    void accumulate() {
        double contribution = 1.0;
        std::uint64_t denominator = 1;
        int repetitions = 1;
        int position = 0;
        for (int first = 0; first < order; ++first) {
            contribution *= weights[indices[first]];
            for (int second = 0; second < first; ++second)
                position = std::max(position,
                    pair_bins[indices[first] * multiplicity + indices[second]]);
            if (first > 0) {
                if (indices[first] == indices[first - 1]) {
                    ++repetitions;
                } else {
                    denominator *= factorial[repetitions];
                    repetitions = 1;
                }
            }
        }
        denominator *= factorial[repetitions];
        const std::uint64_t permutations = factorial[order] / denominator;
        if (std::numeric_limits<std::uint64_t>::max() - ordered_tuples_accounted_for < permutations
            || multisets_completed == std::numeric_limits<std::uint64_t>::max())
            throw std::overflow_error("diagnostic tuple counter overflow");
        histogram[position] += permutations * contribution;
        ++multisets_completed;
        ordered_tuples_accounted_for += permutations;
    }
};

int main(int argc, char **argv) {
    try {
        if (argc != 7)
            throw std::runtime_error("usage: direct_baseline INPUT ORDER KAPPA LOG_MIN BINS OUTPUT_JSON");
        std::signal(SIGTERM, request_stop);
        std::signal(SIGXCPU, request_stop);
        std::signal(SIGINT, request_stop);
        const int order = std::stoi(argv[2]);
        const double kappa = std::stod(argv[3]);
        const double log_min = std::stod(argv[4]);
        const int bins = std::stoi(argv[5]);
        if (order < 1 || order > 8 || !std::isfinite(kappa) || kappa <= 0
            || !std::isfinite(log_min) || log_min >= 0 || bins < 2 || bins > 1000)
            throw std::runtime_error("invalid histogram parameters");
        const auto parsing_start = SteadyClock::now();
        const double parsing_cpu_start = cpu_seconds();
        std::ifstream input(argv[1]);
        if (!input) throw std::runtime_error("cannot open input");
        std::vector<Particle> particles;
        int event_id;
        Particle particle{};
        while (input >> event_id) {
            if (!(input >> particle.transverse >> particle.rapidity >> particle.azimuth))
                throw std::runtime_error("incomplete input record");
            if (event_id != 0 || !std::isfinite(particle.transverse) || particle.transverse <= 0
                || !std::isfinite(particle.rapidity) || !std::isfinite(particle.azimuth))
                throw std::runtime_error("expected one complete jet with event ID zero");
            particles.push_back(particle);
        }
        if (!input.eof() || particles.empty()) throw std::runtime_error("invalid or empty input");
        const double parsing_wall = elapsed_seconds(parsing_start);
        const double parsing_cpu = cpu_seconds() - parsing_cpu_start;
        const auto preparation_start = SteadyClock::now();
        const double preparation_cpu_start = cpu_seconds();
        DirectHistogram direct(particles, order, kappa, log_min, bins);
        const double preparation_wall = elapsed_seconds(preparation_start);
        const double preparation_cpu = cpu_seconds() - preparation_cpu_start;
        std::cout << std::setprecision(17)
                  << "{\"phase\":\"loop_start\",\"constituents\":" << particles.size()
                  << ",\"order\":" << order << ",\"parsing_wall_seconds\":" << parsing_wall
                  << ",\"parsing_cpu_seconds\":" << parsing_cpu
                  << ",\"preparation_wall_seconds\":" << preparation_wall
                  << ",\"preparation_cpu_seconds\":" << preparation_cpu << "}\n" << std::flush;
        const auto loop_start = SteadyClock::now();
        const double loop_cpu_start = cpu_seconds();
        direct.enumerate();
        const double loop_cpu = cpu_seconds() - loop_cpu_start;
        const double loop_wall = elapsed_seconds(loop_start);
        const bool complete = stopping_signal == 0;
        std::ofstream output(argv[6]);
        if (!output) throw std::runtime_error("cannot open result file");
        output << std::setprecision(17)
               << "{\"status\":\"" << (complete ? "complete" : "interrupted_partial")
               << "\",\"exact_full_particle_result\":" << (complete ? "true" : "false")
               << ",\"constituents\":" << particles.size() << ",\"order\":" << order
               << ",\"kappa\":" << kappa << ",\"log_min\":" << log_min << ",\"bins\":" << bins
               << ",\"termination_signal\":" << stopping_signal
               << ",\"parsing_wall_seconds\":" << parsing_wall
               << ",\"parsing_cpu_seconds\":" << parsing_cpu
               << ",\"preparation_wall_seconds\":" << preparation_wall
               << ",\"preparation_cpu_seconds\":" << preparation_cpu
               << ",\"loop_wall_seconds\":" << loop_wall
               << ",\"loop_cpu_seconds\":" << loop_cpu
               << ",\"multisets_completed\":" << direct.multisets_completed
               << ",\"ordered_tuples_accounted_for\":" << direct.ordered_tuples_accounted_for
               << (complete ? ",\"histogram\":[" : ",\"partial_histogram_diagnostic_only\":[");
        for (std::size_t index = 0; index < direct.histogram.size(); ++index) {
            if (index) output << ',';
            output << direct.histogram[index];
        }
        output << "]}\n";
        output.close();
        if (!output) throw std::runtime_error("cannot write result file");
        std::cout << "{\"phase\":\"loop_end\",\"complete\":" << (complete ? "true" : "false")
                  << ",\"loop_wall_seconds\":" << loop_wall
                  << ",\"loop_cpu_seconds\":" << loop_cpu << "}\n";
        return complete ? 0 : 124;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
