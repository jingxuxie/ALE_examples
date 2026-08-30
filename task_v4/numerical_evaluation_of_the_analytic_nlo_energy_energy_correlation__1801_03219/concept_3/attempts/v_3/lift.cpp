#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using Complex = std::complex<double>;
using Sequence = std::vector<int>;
using Clock = std::chrono::steady_clock;

bool can_lift(const Sequence& lower, const Sequence& expected) {
    int half = lower.size();
    if (half == 4096) return true;
    Sequence folded(2 * half);
    for (int index = 0; index < 4096; ++index) folded[index % (2 * half)] += expected[index];
    int words = (half + 64) / 64;
    std::vector<std::vector<uint64_t>> rows(half / 2, std::vector<uint64_t>(words));
    for (int lag = 0; lag < half / 2; ++lag) {
        long actual = 0;
        for (int index = 0; index < half; ++index)
            actual += lower[index] * lower[(index + lag) % half] * (index + lag < half ? 1 : -1);
        long difference = folded[lag] - folded[lag + half] - actual;
        if (difference % 2) return false;
        for (int index = 0; index < half; ++index)
            if ((lower[(index + lag) % half] + lower[(index + half - lag) % half]) % 2)
                rows[lag][index / 64] |= uint64_t(1) << (index % 64);
        if ((difference / 2) % 2) rows[lag][half / 64] |= uint64_t(1) << (half % 64);
    }
    int pivot = 0;
    for (int column = 0; column < half && pivot < int(rows.size()); ++column) {
        int selected = pivot;
        while (selected < int(rows.size()) && !(rows[selected][column / 64] & (uint64_t(1) << (column % 64)))) ++selected;
        if (selected == int(rows.size())) continue;
        std::swap(rows[pivot], rows[selected]);
        for (int index = pivot + 1; index < int(rows.size()); ++index)
            if (rows[index][column / 64] & (uint64_t(1) << (column % 64)))
                for (int word = column / 64; word < words; ++word) rows[index][word] ^= rows[pivot][word];
        ++pivot;
    }
    for (int index = pivot; index < int(rows.size()); ++index)
        if (rows[index][half / 64] & (uint64_t(1) << (half % 64))) return false;
    return true;
}

struct Fourier {
    int size;
    std::vector<int> reverse;
    std::vector<Complex> roots;
    Fourier(int count) : size(count), reverse(count), roots(count) {
        int bits = 0;
        while ((1 << bits) < size) ++bits;
        for (int index = 0; index < size; ++index) {
            int source = index;
            for (int bit = 0; bit < bits; ++bit) { reverse[index] = 2 * reverse[index] + (source & 1); source >>= 1; }
            roots[index] = std::polar(1.0, -2.0 * std::acos(-1.0) * index / size);
        }
    }
    void transform(std::vector<Complex>& values, bool inverse = false) {
        for (int index = 0; index < size; ++index) if (index < reverse[index]) std::swap(values[index], values[reverse[index]]);
        for (int width = 2; width <= size; width *= 2) {
            int half = width / 2, stride = size / width;
            for (int begin = 0; begin < size; begin += width) {
                for (int offset = 0; offset < half; ++offset) {
                    Complex root = roots[offset * stride];
                    if (inverse) root = std::conj(root);
                    Complex left = values[begin + offset];
                    Complex right = values[begin + offset + half] * root;
                    values[begin + offset] = left + right;
                    values[begin + offset + half] = left - right;
                }
            }
        }
        if (inverse) for (auto& value : values) value /= size;
    }
};

struct ParityProjection {
    int half, upper, left_bits, right_bits, checks;
    uint32_t target = 0;
    std::vector<uint32_t> columns, left_syndrome, right_syndrome;
    std::vector<double> left_cost, right_cost, best_cost;
    std::vector<uint32_t> best_mask;
    ParityProjection(const Sequence& lower, const Sequence& expected) : half(lower.size()), upper(4096 / half) {
        if (half > 32) return;
        Sequence folded(2 * half);
        for (int index = 0; index < 4096; ++index) folded[index % (2 * half)] += expected[index];
        std::vector<uint64_t> rows;
        for (int lag = 0; lag < half / 2; ++lag) {
            long actual = 0;
            uint64_t mask = 0;
            for (int index = 0; index < half; ++index) {
                actual += lower[index] * lower[(index + lag) % half] * (index + lag < half ? 1 : -1);
                if ((lower[(index + lag) % half] + lower[(index + half - lag) % half]) % 2) mask |= uint64_t(1) << index;
            }
            long difference = folded[lag] - folded[lag + half] - actual;
            if ((difference / 2) % 2) mask |= uint64_t(1) << half;
            rows.push_back(mask);
        }
        checks = 0;
        for (int column = 0; column < half && checks < int(rows.size()); ++column) {
            int selected = checks;
            while (selected < int(rows.size()) && !(rows[selected] & (uint64_t(1) << column))) ++selected;
            if (selected == int(rows.size())) continue;
            std::swap(rows[selected], rows[checks]);
            for (int index = checks + 1; index < int(rows.size()); ++index) if (rows[index] & (uint64_t(1) << column)) rows[index] ^= rows[checks];
            ++checks;
        }
        columns.resize(half);
        for (int row = 0; row < checks; ++row) {
            if (rows[row] & (uint64_t(1) << half)) target |= uint32_t(1) << row;
            for (int column = 0; column < half; ++column) if (rows[row] & (uint64_t(1) << column)) columns[column] |= uint32_t(1) << row;
        }
        left_bits = half / 2;
        right_bits = half - left_bits;
        left_syndrome.resize(1 << left_bits);
        right_syndrome.resize(1 << right_bits);
        left_cost.resize(1 << left_bits);
        right_cost.resize(1 << right_bits);
        best_cost.resize(1 << checks);
        best_mask.resize(1 << checks);
        for (int mask = 1; mask < (1 << left_bits); ++mask) left_syndrome[mask] = left_syndrome[mask & (mask - 1)] ^ columns[__builtin_ctz(unsigned(mask))];
        for (int mask = 1; mask < (1 << right_bits); ++mask) right_syndrome[mask] = right_syndrome[mask & (mask - 1)] ^ columns[left_bits + __builtin_ctz(unsigned(mask))];
    }
    void project(const std::vector<double>& values, std::vector<double>& discrete, const Sequence& lower) {
        if (half > 32) {
            for (int index = 0; index < half; ++index) {
                double value = std::nearbyint((values[index] - values[index + half] + lower[index]) / 2);
                value = std::clamp(value, double(std::max(0, lower[index] - upper)), double(std::min(upper, lower[index])));
                discrete[index] = value;
                discrete[index + half] = lower[index] - value;
            }
            return;
        }
        double choices[32][2], penalties[32];
        uint32_t preferred = 0, syndrome = target;
        for (int index = 0; index < half; ++index) {
            double desired = (values[index] - values[index + half] + lower[index]) / 2;
            double costs[2];
            for (int parity = 0; parity < 2; ++parity) {
                int minimum = std::max(0, lower[index] - upper);
                int maximum = std::min(upper, lower[index]);
                if ((minimum & 1) != parity) ++minimum;
                if ((maximum & 1) != parity) --maximum;
                double choice = 2 * std::nearbyint((desired - parity) / 2) + parity;
                if (minimum > maximum) { choices[index][parity] = 0; costs[parity] = 1e100; }
                else { choice = std::clamp(choice, double(minimum), double(maximum)); choices[index][parity] = choice; costs[parity] = (choice - desired) * (choice - desired); }
            }
            if (costs[1] < costs[0]) { preferred |= uint32_t(1) << index; syndrome ^= columns[index]; }
            penalties[index] = std::abs(costs[1] - costs[0]);
        }
        std::fill(best_cost.begin(), best_cost.end(), 1e200);
        left_cost[0] = right_cost[0] = 0;
        for (int mask = 0; mask < int(left_cost.size()); ++mask) {
            if (mask) left_cost[mask] = left_cost[mask & (mask - 1)] + penalties[__builtin_ctz(unsigned(mask))];
            uint32_t code = left_syndrome[mask];
            if (left_cost[mask] < best_cost[code]) { best_cost[code] = left_cost[mask]; best_mask[code] = mask; }
        }
        double best = 1e200;
        uint32_t selected = 0;
        for (int mask = 0; mask < int(right_cost.size()); ++mask) {
            if (mask) right_cost[mask] = right_cost[mask & (mask - 1)] + penalties[left_bits + __builtin_ctz(unsigned(mask))];
            uint32_t code = right_syndrome[mask] ^ syndrome;
            double cost = right_cost[mask] + best_cost[code];
            if (cost < best) { best = cost; selected = best_mask[code] | (uint32_t(mask) << left_bits); }
        }
        selected ^= preferred;
        for (int index = 0; index < half; ++index) {
            discrete[index] = choices[index][(selected >> index) & 1];
            discrete[index + half] = lower[index] - discrete[index];
        }
    }
};

Sequence canonical(Sequence values) {
    Sequence best = values;
    for (int reflected = 0; reflected < 2; ++reflected) {
        for (int offset = 0; offset < int(values.size()); ++offset) {
            if (values[offset] > best[0]) continue;
            Sequence shifted(values.size());
            for (int index = 0; index < int(values.size()); ++index) shifted[index] = values[(index + offset) % values.size()];
            if (shifted < best) best = shifted;
        }
        std::reverse(values.begin(), values.end());
    }
    return best;
}

Sequence lift(const Sequence& lower, const Sequence& expected, double seconds, double beta, int restarts, std::mt19937_64& generator) {
    int half = lower.size(), size = 2 * half, upper = 8192 / size;
    Fourier fourier(size), small(half);
    ParityProjection parity(lower, expected);
    std::vector<Complex> target(size), lower_spectrum(half), spectrum(size);
    Sequence wanted(size);
    for (int index = 0; index < 4096; ++index) wanted[index % size] += expected[index];
    for (int index = 0; index < size; ++index) target[index] = wanted[index];
    fourier.transform(target);
    std::vector<double> magnitudes(size), values(size), discrete(size);
    for (int index = 0; index < size; ++index) magnitudes[index] = std::sqrt(std::max(0.0, target[index].real()));
    for (int index = 0; index < half; ++index) lower_spectrum[index] = lower[index];
    small.transform(lower_spectrum);
    std::normal_distribution<double> normal(0, std::sqrt(1280.0 / size));
    auto initialize = [&]() {
        for (int index = 0; index < half; ++index) {
            values[index] = lower[index] / 2.0 + normal(generator);
            values[index + half] = lower[index] - values[index];
        }
    };
    initialize();
    auto started = Clock::now();
    double best = 1e100;
    long iterations = 0;
    while (true) {
        parity.project(values, discrete, lower);
        for (int index = 0; index < size; ++index) spectrum[index] = 2 * discrete[index] - values[index];
        fourier.transform(spectrum);
        for (int index = 0; index < size; ++index) {
            if (index % 2 == 0) spectrum[index] = lower_spectrum[index / 2];
            else spectrum[index] *= magnitudes[index] / std::max(1e-20, std::abs(spectrum[index]));
        }
        fourier.transform(spectrum, true);
        double residual = 0;
        for (int index = 0; index < size; ++index) {
            double difference = spectrum[index].real() - discrete[index];
            residual += difference * difference;
            values[index] += beta * difference;
        }
        best = std::min(best, residual);
        ++iterations;
        if (residual < 1e-9) {
            Sequence candidate(size);
            for (int index = 0; index < size; ++index) candidate[index] = std::lround(discrete[index]);
            bool exact = true;
            for (int lag = 0; lag < size && exact; ++lag) {
                int actual = 0;
                for (int index = 0; index < size; ++index) actual += candidate[index] * candidate[(index + lag) % size];
                exact = actual == wanted[lag];
            }
            if (exact) {
                std::cout << "EXACT FOLD " << size << " ITERATIONS " << iterations << " SECONDS " << std::chrono::duration<double>(Clock::now() - started).count() << std::endl;
                return canonical(candidate);
            }
        }
        if (restarts && iterations % restarts == 0) initialize();
        if (iterations % 1024 == 0 && std::chrono::duration<double>(Clock::now() - started).count() > seconds) break;
    }
    std::cout << "FAILED FOLD " << size << " ITERATIONS " << iterations << " BEST " << best << " BETA " << beta << std::endl;
    return {};
}

int main(int argc, char** argv) {
    double seconds = argc > 1 ? std::stod(argv[1]) : 1500;
    double trial_seconds = argc > 2 ? std::stod(argv[2]) : 10;
    int seed = argc > 3 ? std::stoi(argv[3]) : 120;
    std::mt19937_64 generator(seed);
    std::ifstream source("../../participant/input/target.json");
    std::string text((std::istreambuf_iterator<char>(source)), std::istreambuf_iterator<char>());
    auto position = text.find('[', text.find("cyclic_autocorrelation"));
    auto ending = text.find(']', position);
    std::string body = text.substr(position + 1, ending - position - 1);
    std::replace(body.begin(), body.end(), ',', ' ');
    std::istringstream numbers(body);
    Sequence expected(4096);
    for (int& value : expected) numbers >> value;
    std::vector<std::vector<Sequence>> pools(13);
    std::ifstream initial("levels.txt");
    int size, deepest = 0;
    while (initial >> size) {
        Sequence candidate(size);
        for (int& value : candidate) initial >> value;
        int level = 0;
        while ((1 << level) < size) ++level;
        if (can_lift(candidate, expected)) {
            pools[level].push_back(canonical(candidate));
            deepest = std::max(deepest, level);
        }
    }
    auto started = Clock::now();
    int trial = 0;
    while (std::chrono::duration<double>(Clock::now() - started).count() < seconds) {
        ++trial;
        int level = deepest;
        if (deepest > 3 && generator() % 2 == 0) --level;
        auto& pool = pools[level];
        if (pool.empty()) continue;
        const auto lower = pool[generator() % pool.size()];
        double betas[] = {0.5, 1.0, 1.5, 0.8};
        double beta = betas[generator() % 4];
        int restart_choices[] = {1000, 10000, 100000};
        int restarts = restart_choices[generator() % 3];
        std::cout << "TRIAL " << trial << " FROM " << (1 << level) << " POOL " << pool.size() << " ELAPSED " << std::chrono::duration<double>(Clock::now() - started).count() << std::endl;
        auto candidate = lift(lower, expected, trial_seconds, beta, restarts, generator);
        if (candidate.empty()) continue;
        if (!can_lift(candidate, expected)) {
            std::cout << "REJECTED MODULAR " << candidate.size() << std::endl;
            continue;
        }
        if (candidate.size() == 4096) {
            bool spacing = true;
            for (int index = 0; index < 4096; ++index) if (candidate[index] && candidate[(index + 1) % 4096]) spacing = false;
            if (spacing) {
                std::ofstream output("design.json");
                output << "{\"schema_version\":1,\"a\":[";
                for (int index = 0; index < 4096; ++index) output << (index ? "," : "") << candidate[index];
                output << "]}\n";
                std::cout << "EXACT DESIGN" << std::endl;
                return 0;
            }
        }
        auto& destination = pools[level + 1];
        if (std::find(destination.begin(), destination.end(), candidate) == destination.end()) {
            destination.push_back(candidate);
            std::ofstream output("levels_" + std::to_string(seed) + ".txt", std::ios::app);
            output << candidate.size();
            for (int value : candidate) output << " " << value;
            output << "\n";
            std::cout << "NEW FOLD " << candidate.size() << " POOL " << destination.size() << std::endl;
        }
        deepest = std::max(deepest, level + 1);
    }
}
