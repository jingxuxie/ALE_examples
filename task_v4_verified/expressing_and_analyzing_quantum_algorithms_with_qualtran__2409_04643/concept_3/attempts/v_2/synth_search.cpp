#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Network {
    std::vector<unsigned> left;
    std::vector<unsigned> right;
    int loss = 1000000;
    unsigned output = 0;
};

struct Search {
    int width, output_bit, affine_mask, rows;
    std::vector<int> target;
    std::vector<int> previous;
    std::vector<unsigned> features;
    std::vector<int> spectrum;
    std::mt19937 random;
    Network current;

    int parity(unsigned value) { return __builtin_parity(value); }

    int evaluate(Network& network, bool store) {
        int loss = 0;
        for (int address = 0; address < rows; ++address) {
            unsigned values = (unsigned(address) << 1) | 1;
            for (int gate = 0; gate < int(previous.size()); ++gate) {
                unsigned value = parity(network.left[gate] & values) & parity(network.right[gate] & values);
                values |= value << (width + 1 + gate);
            }
            int actual = parity(network.output & values);
            loss += actual != target[address];
            if (store) features[address] = values;
        }
        network.loss = loss;
        return loss;
    }

    void fresh() {
        for (int gate = 0; gate < int(previous.size()); ++gate) {
            current.left[gate] = random() & ((1U << (width + 1 + previous[gate])) - 1);
            current.right[gate] = random() & ((1U << (width + 1 + previous[gate])) - 1);
        }
        current.output = (1U << (width + previous.size() - 1)) ^ (1U << (width + previous.size()));
        evaluate(current, true);
        optimize_output();
    }

    int with_operand(int address, int gate, bool right, int operand) {
        unsigned values = features[address] & ((1U << (width + 1 + gate)) - 1);
        unsigned other = right ? current.left[gate] : current.right[gate];
        int product = operand & parity(other & values);
        values |= unsigned(product) << (width + 1 + gate);
        for (int later = gate + 1; later < int(previous.size()); ++later) {
            product = parity(current.left[later] & values) & parity(current.right[later] & values);
            values |= unsigned(product) << (width + 1 + later);
        }
        return parity(current.output & values);
    }

    void transform(int size) {
        for (int stride = 1; stride < size; stride *= 2) {
            for (int start = 0; start < size; start += 2 * stride) {
                for (int offset = 0; offset < stride; ++offset) {
                    int left = spectrum[start + offset];
                    int right_value = spectrum[start + stride + offset];
                    spectrum[start + offset] = left + right_value;
                    spectrum[start + stride + offset] = left - right_value;
                }
            }
        }
    }

    void optimize_output() {
        int size = 1 << (width + previous.size());
        std::fill(spectrum.begin(), spectrum.begin() + size, 0);
        for (int address = 0; address < rows; ++address) spectrum[features[address] >> 1] += target[address] ? -1 : 1;
        transform(size);
        int best = 0;
        int tied = 0;
        for (int index = 0; index < size; ++index) {
            if (std::abs(spectrum[index]) > std::abs(spectrum[best])) { best = index; tied = 1; }
            else if (std::abs(spectrum[index]) == std::abs(spectrum[best]) && random() % (++tied) == 0) best = index;
        }
        current.output = (unsigned(best) << 1) | unsigned(spectrum[best] < 0);
        evaluate(current, true);
    }

    int with_product(int address, int gate, int product) {
        unsigned values = features[address] & ((1U << (width + 1 + gate)) - 1);
        values |= unsigned(product) << (width + 1 + gate);
        for (int later = gate + 1; later < int(previous.size()); ++later) {
            product = parity(current.left[later] & values) & parity(current.right[later] & values);
            values |= unsigned(product) << (width + 1 + later);
        }
        return parity(current.output & values);
    }

    void optimize_gate(int gate, int peak_count, int sample_rows) {
        int size = 1 << (width + previous[gate]);
        std::fill(spectrum.begin(), spectrum.begin() + size, 0);
        for (int address = 0; address < rows; ++address) {
            if (sample_rows < rows && int(random() % rows) >= sample_rows) continue;
            int zero = with_product(address, gate, 0);
            int one = with_product(address, gate, 1);
            if (zero != one) spectrum[(features[address] >> 1) & (size - 1)] += zero == target[address] ? 1 : -1;
        }
        transform(size);
        std::vector<int> peaks(size);
        std::iota(peaks.begin(), peaks.end(), 0);
        std::shuffle(peaks.begin(), peaks.end(), random);
        int peak_limit = std::min(size, peak_count);
        std::partial_sort(peaks.begin(), peaks.begin() + peak_limit, peaks.end(), [&](int left, int right) { return std::abs(spectrum[left]) > std::abs(spectrum[right]); });
        peaks.resize(peak_limit);
        if (spectrum[peaks[0]] == 0) {
            current.output ^= 1U << (width + 1 + gate);
            optimize_gate(gate, peak_count, rows);
            return;
        }
        struct Pair { int score = -1; int first = -1; int second = -1; };
        struct Bucket { Pair plus[2]; Pair minus[2]; };
        std::vector<Bucket> buckets(size);
        auto insert = [](Pair* pair, Pair candidate) {
            if (candidate.score > pair[0].score) { pair[1] = pair[0]; pair[0] = candidate; }
            else if (candidate.score > pair[1].score) pair[1] = candidate;
        };
        for (int first = 0; first < peak_limit; ++first) {
            for (int second = first + 1; second < peak_limit; ++second) {
                int first_index = peaks[first], second_index = peaks[second];
                auto& bucket = buckets[first_index ^ second_index];
                insert(bucket.plus, {std::abs(spectrum[first_index] + spectrum[second_index]), first_index, second_index});
                insert(bucket.minus, {std::abs(spectrum[first_index] - spectrum[second_index]), first_index, second_index});
            }
        }
        int best_score = 2 * std::abs(spectrum[peaks[0]]);
        unsigned new_left = 0, new_right = 0;
        unsigned correction = (unsigned(peaks[0]) << 1) | unsigned(spectrum[peaks[0]] < 0);
        int tied = 1;
        for (int direction = 1; direction < size; ++direction) {
            auto& bucket = buckets[direction];
            for (int first = 0; first < 2; ++first) {
                for (int second = 0; second < 2; ++second) {
                    auto plus = bucket.plus[first], minus = bucket.minus[second];
                    if (plus.first < 0 || minus.first < 0) continue;
                    if (plus.first == minus.first || plus.first == minus.second) continue;
                    int score = plus.score + minus.score;
                    if (score < best_score) continue;
                    if (score == best_score && random() % (++tied)) continue;
                    if (score > best_score) { best_score = score; tied = 1; }
                    bool plus_negative = spectrum[plus.first] + spectrum[plus.second] < 0;
                    bool minus_negative = spectrum[minus.first] - spectrum[minus.second] < 0;
                    new_left = unsigned(direction) << 1;
                    new_right = (unsigned(plus.first ^ minus.first) << 1) | unsigned(plus_negative != minus_negative);
                    correction = (unsigned(plus.first) << 1) | unsigned(plus_negative);
                }
            }
        }
        current.left[gate] = new_left;
        current.right[gate] = new_right;
        unsigned gate_bit = 1U << (width + 1 + gate);
        for (int later = gate + 1; later < int(previous.size()); ++later) {
            if (current.left[later] & gate_bit) current.left[later] ^= correction;
            if (current.right[later] & gate_bit) current.right[later] ^= correction;
        }
        if (current.output & gate_bit) current.output ^= correction;
        evaluate(current, true);
        optimize_output();
    }

    void optimize(int gate, bool right, double temperature, int sample_rows) {
        int size = 1 << (width + previous[gate]);
        std::fill(spectrum.begin(), spectrum.begin() + size, 0);
        for (int address = 0; address < rows; ++address) {
            if (sample_rows < rows && int(random() % rows) >= sample_rows) continue;
            int zero = with_operand(address, gate, right, 0);
            int one = with_operand(address, gate, right, 1);
            if (zero != one) {
                int index = (features[address] >> 1) & (size - 1);
                spectrum[index] += (zero == target[address]) ? 1 : -1;
            }
        }
        for (int stride = 1; stride < size; stride *= 2) {
            for (int start = 0; start < size; start += 2 * stride) {
                for (int offset = 0; offset < stride; ++offset) {
                    int left = spectrum[start + offset];
                    int right_value = spectrum[start + stride + offset];
                    spectrum[start + offset] = left + right_value;
                    spectrum[start + stride + offset] = left - right_value;
                }
            }
        }
        int maximum = 0;
        for (int index = 0; index < size; ++index) maximum = std::max(maximum, std::abs(spectrum[index]));
        unsigned best_mask = 0;
        double accumulated = 0;
        for (int index = 0; index < size; ++index) {
            int score = std::abs(spectrum[index]);
            if (temperature == 0 && score != maximum) continue;
            if (temperature > 0 && score < maximum - 20 * temperature) continue;
            double weight = temperature == 0 ? 1 : std::exp((score - maximum) / temperature);
            accumulated += weight;
            if (std::generate_canonical<double, 32>(random) * accumulated < weight) {
                best_mask = (unsigned(index) << 1) | unsigned(spectrum[index] < 0);
            }
        }
        if (right) current.right[gate] = best_mask;
        else current.left[gate] = best_mask;
        evaluate(current, true);
    }

    void save(const std::string& path, const Network& network) {
        std::ofstream output(path);
        output << "{\"loss\":" << network.loss << ",\"output\":" << network.output << ",\"left\":[";
        for (int gate = 0; gate < int(previous.size()); ++gate) output << (gate ? "," : "") << network.left[gate];
        output << "],\"right\":[";
        for (int gate = 0; gate < int(previous.size()); ++gate) output << (gate ? "," : "") << network.right[gate];
        output << "]}" << std::endl;
    }
};

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    Search search;
    int outputs;
    input >> search.width >> outputs;
    search.rows = 1 << search.width;
    search.output_bit = std::stoi(argv[2]);
    search.affine_mask = std::stoi(argv[3]);
    search.random.seed(argc > 4 ? std::stoi(argv[4]) : 1);
    int seconds = argc > 5 ? std::stoi(argv[5]) : 600;
    std::string save_path = argc > 6 ? argv[6] : "search_best.json";
    search.previous = {0, 0, 0, 0, 4, 4, 6, 7};
    if (argc > 7) {
        search.previous.clear();
        int base = std::stoi(argv[7]);
        search.previous.resize(base, 0);
        search.previous.push_back(base);
        search.previous.push_back(base);
        search.previous.push_back(base + 2);
        search.previous.push_back(base + 3);
    }
    search.features.resize(search.rows);
    search.spectrum.resize(1 << (search.width + search.previous.size()));
    search.current.left.resize(search.previous.size());
    search.current.right.resize(search.previous.size());
    for (int address = 0; address < search.rows; ++address) {
        int value;
        input >> value;
        search.target.push_back(((value >> search.output_bit) & 1) ^ search.parity(address & search.affine_mask));
    }
    auto started = std::chrono::steady_clock::now();
    Network best;
    std::vector<Network> population;
    search.fresh();
    int iteration = 0;
    int stagnation = 0;
    std::vector<int> ordering(search.previous.size());
    std::iota(ordering.begin(), ordering.end(), 0);
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds) {
        int before = search.current.loss;
        double temperature = 0;
        int sample_rows = search.rows;
        if (stagnation > 3) {
            temperature = (iteration % 7 == 0) ? 5.0 : 1.0;
        }
        if (stagnation > 15) {
            if (search.random() % 3 == 0 || population.empty()) search.fresh();
            else {
                search.current = population[search.random() % population.size()];
                for (int count = 0; count < 1 + int(search.random() % 3); ++count) {
                    int gate = search.random() % search.previous.size();
                    unsigned mask = search.random() & ((1U << (search.width + 1 + search.previous[gate])) - 1);
                    if (search.random() & 1) search.current.left[gate] = mask;
                    else search.current.right[gate] = mask;
                }
                search.evaluate(search.current, true);
            }
            stagnation = 0;
        }
        std::shuffle(ordering.begin(), ordering.end(), search.random);
        if (stagnation > 5) sample_rows = search.rows * 9 / 10;
        for (int operand : ordering) {
            search.optimize_gate(operand, 256, sample_rows);
            if (search.current.loss < best.loss) {
                best = search.current;
                search.save(save_path, best);
                std::cerr << "iteration " << iteration << " loss " << best.loss << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
                if (best.loss == 0) return 0;
            }
        }
        if (search.current.loss >= before) ++stagnation;
        else stagnation = 0;
        if (iteration % 5 == 0) {
            population.push_back(search.current);
            std::sort(population.begin(), population.end(), [](const Network& left, const Network& right) { return left.loss < right.loss; });
            if (population.size() > 16) population.resize(16);
        }
        ++iteration;
    }
    std::cerr << "final iterations " << iteration << " loss " << best.loss << std::endl;
}
