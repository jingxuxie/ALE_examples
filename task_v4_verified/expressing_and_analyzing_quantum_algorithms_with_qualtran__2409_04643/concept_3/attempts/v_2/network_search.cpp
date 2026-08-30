#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <vector>

struct CircuitModel {
    std::vector<uint64_t> left, right, outputs;
    int loss = 1000000;
};

struct NetworkSearch {
    int width, output_width, rows, active_count;
    std::vector<int> table, previous;
    std::vector<bool> active;
    std::vector<uint64_t> values;
    std::vector<int> spectrum;
    CircuitModel current, best;
    std::mt19937 random;
    std::string save_path;

    int parity(uint64_t value) { return __builtin_parityll(value); }

    void transform(int size) {
        for (int stride = 1; stride < size; stride *= 2) for (int start = 0; start < size; start += 2 * stride) {
            for (int offset = 0; offset < stride; ++offset) {
                int first = spectrum[start + offset], second = spectrum[start + stride + offset];
                spectrum[start + offset] = first + second;
                spectrum[start + stride + offset] = first - second;
            }
        }
    }

    int output(uint64_t state) {
        int result = 0;
        for (int bit = 0; bit < output_width; ++bit) result |= parity(state & current.outputs[bit]) << bit;
        return result;
    }

    int evaluate(bool training) {
        int loss = 0;
        for (int address = 0; address < rows; ++address) {
            uint64_t state = (uint64_t(address) << 1) | 1;
            for (int gate = 0; gate < int(previous.size()); ++gate) state |= uint64_t(parity(current.left[gate] & state) & parity(current.right[gate] & state)) << (width + 1 + gate);
            values[address] = state;
            if (!training || active[address]) loss += __builtin_popcount(unsigned(table[address] ^ output(state)));
        }
        if (training) current.loss = loss;
        return loss;
    }

    void optimize_outputs() {
        uint64_t input_mask = (1ULL << (width + 1)) - 1;
        for (int bit = 0; bit < output_width; ++bit) {
            uint64_t best_mask = current.outputs[bit];
            int best_score = -1;
            for (int attempt = -1; attempt < int(previous.size()); ++attempt) {
                uint64_t gate_mask = best_mask & ~input_mask;
                if (attempt >= 0) gate_mask ^= 1ULL << (width + 1 + attempt);
                for (int address = 0; address < rows; ++address) spectrum[address] = active[address] ? 1 - 2 * (((table[address] >> bit) & 1) ^ parity(values[address] & gate_mask)) : 0;
                transform(rows);
                int index = 0, ties = 1;
                for (int candidate = 1; candidate < rows; ++candidate) {
                    if (std::abs(spectrum[candidate]) > std::abs(spectrum[index])) { index = candidate; ties = 1; }
                    else if (std::abs(spectrum[candidate]) == std::abs(spectrum[index]) && random() % (++ties) == 0) index = candidate;
                }
                if (std::abs(spectrum[index]) >= best_score) {
                    best_score = std::abs(spectrum[index]);
                    best_mask = gate_mask | (uint64_t(index) << 1) | uint64_t(spectrum[index] < 0);
                }
            }
            current.outputs[bit] = best_mask;
        }
        evaluate(true);
    }

    int with_product(int address, int gate, int product) {
        uint64_t state = values[address] & ((1ULL << (width + 1 + gate)) - 1);
        state |= uint64_t(product) << (width + 1 + gate);
        for (int later = gate + 1; later < int(previous.size()); ++later) state |= uint64_t(parity(current.left[later] & state) & parity(current.right[later] & state)) << (width + 1 + later);
        return output(state);
    }

    void optimize_gate(int gate, bool noisy) {
        int size = 1 << (width + previous[gate]);
        std::fill(spectrum.begin(), spectrum.begin() + size, 0);
        for (int address = 0; address < rows; ++address) if (active[address]) {
            int zero = with_product(address, gate, 0), one = with_product(address, gate, 1);
            int weight = __builtin_popcount(unsigned(table[address] ^ one)) - __builtin_popcount(unsigned(table[address] ^ zero));
            if (noisy && random() % 5 == 0) weight = 0;
            spectrum[(values[address] >> 1) & (size - 1)] = weight;
        }
        transform(size);
        using Peak = std::pair<int, int>;
        std::priority_queue<Peak, std::vector<Peak>, std::greater<Peak>> heap;
        for (int index = 0; index < size; ++index) {
            int score = std::abs(spectrum[index]);
            if (heap.size() < 256) heap.push({score, index});
            else if (score > heap.top().first) { heap.pop(); heap.push({score, index}); }
        }
        std::vector<int> peaks;
        while (!heap.empty()) { peaks.push_back(heap.top().second); heap.pop(); }
        std::reverse(peaks.begin(), peaks.end());
        uint64_t new_left = 0, new_right = 0;
        uint64_t correction = (uint64_t(peaks[0]) << 1) | uint64_t(spectrum[peaks[0]] < 0);
        int best_score = 2 * std::abs(spectrum[peaks[0]]), ties = 1;
        if (best_score == 0) {
            current.outputs[random() % output_width] ^= 1ULL << (width + 1 + gate);
            evaluate(true);
            return;
        }
        for (int first = 0; first < std::min(24, int(peaks.size())); ++first) {
            for (int second = first + 1; second < int(peaks.size()); ++second) {
                for (int third = second + 1; third < int(peaks.size()); ++third) {
                    int indices[4] = {peaks[first], peaks[second], peaks[third], peaks[first] ^ peaks[second] ^ peaks[third]};
                    int signs[4], score = 0, smallest = 0, product_sign = 1;
                    for (int index = 0; index < 4; ++index) {
                        signs[index] = spectrum[indices[index]] < 0 ? -1 : 1;
                        product_sign *= signs[index];
                        score += std::abs(spectrum[indices[index]]);
                        if (std::abs(spectrum[indices[index]]) < std::abs(spectrum[indices[smallest]])) smallest = index;
                    }
                    if (product_sign > 0) { score -= 2 * std::abs(spectrum[indices[smallest]]); signs[smallest] *= -1; }
                    if (score < best_score) continue;
                    if (score == best_score && random() % (++ties)) continue;
                    if (score > best_score) { best_score = score; ties = 1; }
                    new_left = (uint64_t(indices[0] ^ indices[1]) << 1) | uint64_t(signs[0] != signs[1]);
                    new_right = (uint64_t(indices[0] ^ indices[2]) << 1) | uint64_t(signs[0] != signs[2]);
                    correction = (uint64_t(indices[0]) << 1) | uint64_t(signs[0] < 0);
                }
            }
        }
        current.left[gate] = new_left;
        current.right[gate] = new_right;
        uint64_t gate_bit = 1ULL << (width + 1 + gate);
        for (int later = gate + 1; later < int(previous.size()); ++later) {
            if (current.left[later] & gate_bit) current.left[later] ^= correction;
            if (current.right[later] & gate_bit) current.right[later] ^= correction;
        }
        for (auto& output_mask : current.outputs) if (output_mask & gate_bit) output_mask ^= correction;
        evaluate(true);
    }

    void fresh() {
        for (int gate = 0; gate < int(previous.size()); ++gate) {
            uint64_t mask = (1ULL << (width + 1 + previous[gate])) - 1;
            current.left[gate] = ((uint64_t(random()) << 32) | random()) & mask;
            current.right[gate] = ((uint64_t(random()) << 32) | random()) & mask;
        }
        for (int bit = 0; bit < output_width; ++bit) current.outputs[bit] = 1ULL << (width + 1 + previous.size() - 1 - bit);
        evaluate(true);
        optimize_outputs();
    }

    void save() {
        std::ofstream stream(save_path);
        stream << "{\"loss\":" << best.loss << ",\"left\":[";
        for (int gate = 0; gate < int(previous.size()); ++gate) stream << (gate ? "," : "") << best.left[gate];
        stream << "],\"right\":[";
        for (int gate = 0; gate < int(previous.size()); ++gate) stream << (gate ? "," : "") << best.right[gate];
        stream << "],\"outputs\":[";
        for (int bit = 0; bit < output_width; ++bit) stream << (bit ? "," : "") << best.outputs[bit];
        stream << "]}" << std::endl;
    }
};

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    NetworkSearch search;
    input >> search.width >> search.output_width;
    search.rows = 1 << search.width;
    search.table.resize(search.rows);
    for (auto& value : search.table) input >> value;
    int base = argc > 2 ? std::stoi(argv[2]) : 4;
    search.random.seed(argc > 3 ? std::stoi(argv[3]) : 1);
    int seconds = argc > 4 ? std::stoi(argv[4]) : 600;
    search.save_path = argc > 5 ? argv[5] : "network_best.json";
    search.active_count = argc > 6 ? std::stoi(argv[6]) : 32;
    search.previous.resize(base, 0);
    for (int gate = 0; gate < search.output_width; ++gate) search.previous.push_back(base);
    for (int gate = 0; gate < search.output_width; ++gate) search.previous.push_back(base + search.output_width);
    for (int gate = 0; gate < 2 * search.output_width; ++gate) search.previous.push_back(base + 2 * search.output_width);
    search.current.left.resize(search.previous.size());
    search.current.right.resize(search.previous.size());
    search.current.outputs.resize(search.output_width);
    search.spectrum.resize(1 << (search.width + search.previous.back()));
    search.values.resize(search.rows);
    search.active.resize(search.rows);
    std::vector<int> addresses(search.rows);
    std::iota(addresses.begin(), addresses.end(), 0);
    std::shuffle(addresses.begin(), addresses.end(), search.random);
    for (int index = 0; index < search.active_count; ++index) search.active[addresses[index]] = true;
    search.fresh();
    auto started = std::chrono::steady_clock::now();
    int iteration = 0, stagnation = 0;
    std::vector<CircuitModel> population;
    std::vector<int> gates(search.previous.size());
    std::iota(gates.begin(), gates.end(), 0);
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds) {
        int before = search.current.loss;
        std::shuffle(gates.begin(), gates.end(), search.random);
        for (int gate : gates) search.optimize_gate(gate, stagnation > 3);
        search.optimize_outputs();
        int full_loss = search.evaluate(false);
        std::cerr << "iteration " << iteration << " active " << search.active_count << " train " << search.current.loss << " full " << full_loss << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        if (full_loss < search.best.loss) { search.best = search.current; search.best.loss = full_loss; search.save(); if (full_loss == 0) return 0; }
        if (search.current.loss == 0) {
            int added = 0;
            for (int address : addresses) if (!search.active[address] && search.output(search.values[address]) != search.table[address]) {
                search.active[address] = true;
                ++search.active_count;
                if (++added == 16) break;
            }
            search.optimize_outputs();
            population.clear();
            stagnation = 0;
        } else if (search.current.loss < before) stagnation = 0;
        else ++stagnation;
        population.push_back(search.current);
        std::sort(population.begin(), population.end(), [](const CircuitModel& left, const CircuitModel& right) { return left.loss < right.loss; });
        if (population.size() > 8) population.resize(8);
        if (stagnation > 10) {
            if (search.random() % 3 == 0) search.fresh();
            else {
                search.current = population[search.random() % population.size()];
                int gate = search.random() % search.previous.size();
                search.current.left[gate] = ((uint64_t(search.random()) << 32) | search.random()) & ((1ULL << (search.width + 1 + search.previous[gate])) - 1);
                search.evaluate(true);
                search.optimize_outputs();
            }
            stagnation = 0;
        }
        ++iteration;
    }
}
