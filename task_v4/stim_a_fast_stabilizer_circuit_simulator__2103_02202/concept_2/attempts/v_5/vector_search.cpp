#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <immintrin.h>
#include <numeric>
#include <random>
#include <string>
#include <vector>

constexpr int fault_count = 512;
#ifndef COLUMN_COUNT
#define COLUMN_COUNT 704
#endif
constexpr int column_count = COLUMN_COUNT;
constexpr int detector_count = 192;
alignas(64) uint64_t original[3][column_count];
int observable[column_count];
double best_score = 0.65 + 5.4 / 51;
int detector_budget[513];
int total_budget = 0;
std::string output_name;

void update_budgets() {
    total_budget = 0;
    for (int weight = 1; weight <= 512; ++weight) {
        double perfect_score = 0.65 + 0.15 * std::min(1.0, 36.0 / weight);
        detector_budget[weight] = static_cast<int>(std::ceil((perfect_score - best_score) * 192 / 0.45 - 1e-9)) - 1;
        if (detector_budget[weight] >= 0) total_budget = std::max(total_budget, weight + detector_budget[weight]);
    }
    detector_budget[0] = -1;
    if (column_count == fault_count) total_budget = static_cast<int>(std::ceil(5.4 / (best_score - 0.65) - 1e-9)) - 1;
}

bool save_candidate(const std::vector<int>& support, double elapsed) {
    std::vector<int> faults;
    uint64_t syndrome[3] = {};
    uint64_t augmented[3] = {};
    int logical = 0;
    for (int position : support) {
        for (int word = 0; word < 3; ++word) augmented[word] ^= original[word][position];
        if (position >= fault_count) continue;
        faults.push_back(position);
        logical ^= observable[position];
        for (int word = 0; word < 3; ++word) syndrome[word] ^= original[word][position];
    }
    if (augmented[0] || augmented[1] || augmented[2] || !logical) std::abort();
    int detector_weight = __builtin_popcountll(syndrome[0]) + __builtin_popcountll(syndrome[1]) + __builtin_popcountll(syndrome[2]);
    if (faults.empty()) return false;
    double score = 0.65 + 0.15 * std::min(1.0, 36.0 / faults.size()) - 0.45 * detector_weight / 192;
    bool valid = faults.size() <= 36 && !detector_weight;
    if (valid) score = 1;
    if (score <= best_score + 1e-12) return false;
    best_score = score;
    update_budgets();
    std::sort(faults.begin(), faults.end());
    std::ofstream output(output_name);
    output << "{\"faults\": [";
    for (size_t index = 0; index < faults.size(); ++index) {
        if (index) output << ", ";
        output << faults[index];
    }
    output << "]}\n";
    std::cerr << "best score=" << score << " faults=" << faults.size() << " detectors=" << detector_weight << " seconds=" << elapsed << '\n';
    return valid;
}

int main(int argc, char** argv) {
    int seconds = argc > 1 ? std::atoi(argv[1]) : 1200;
    uint64_t seed = argc > 2 ? std::strtoull(argv[2], nullptr, 10) : 451965;
    int residual = argc > 3 ? std::atoi(argv[3]) : 17;
    int forced_faults = argc > 4 ? std::atoi(argv[4]) : -1;
    output_name = argc > 5 ? argv[5] : "augmented_best.json";
    if (argc > 6) best_score = std::atof(argv[6]);
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < fault_count; ++fault) {
        input >> std::hex >> original[0][fault] >> original[1][fault] >> original[2][fault] >> observable[fault];
    }
    if (!input) return 2;
    for (int detector = 0; detector < column_count - fault_count; ++detector) original[detector >> 6][fault_count + detector] = uint64_t(1) << (detector & 63);
    int pivots = detector_count - residual;
    int split = pivots + (column_count - pivots) / 2;
    int shift = 64 - residual;
    std::mt19937_64 generator(seed);
    alignas(64) uint64_t columns[3][column_count];
    std::array<int, column_count> permutation;
    int transformed_observable[column_count];
    std::vector<int> offsets((1 << (residual + 1)) + 1);
    std::vector<int> cursors(offsets.size());
    std::vector<uint32_t> pairs(40000);
    std::vector<uint64_t> left_zero(40000), left_one(40000);
#if defined(__AVX512VPOPCNTDQ__) && defined(__AVX512VL__)
    std::cerr << "vector popcount enabled\n";
#endif
    auto started = std::chrono::steady_clock::now();
    uint64_t iterations = 0;
    update_budgets();
    while (true) {
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        if (elapsed >= seconds) break;
        if ((iterations & 32767) == 0) std::cerr << "progress " << elapsed << " iterations=" << iterations << " score=" << best_score << '\n';
        std::copy(&original[0][0], &original[0][0] + 3 * column_count, &columns[0][0]);
        std::iota(permutation.begin(), permutation.end(), 0);
        if (forced_faults < 0) {
            std::shuffle(permutation.begin(), permutation.end(), generator);
        } else {
            std::shuffle(permutation.begin(), permutation.begin() + fault_count, generator);
            std::shuffle(permutation.begin() + fault_count, permutation.end(), generator);
            std::rotate(permutation.begin() + forced_faults, permutation.begin() + fault_count, permutation.begin() + fault_count + pivots - forced_faults);
            std::shuffle(permutation.begin(), permutation.begin() + pivots, generator);
            std::shuffle(permutation.begin() + pivots, permutation.end(), generator);
        }
        for (int pivot = 0; pivot < pivots; ++pivot) {
            int word = pivot >> 6;
            int bit = pivot & 63;
            int position = pivot;
            while (position < column_count && ((columns[word][permutation[position]] >> bit) & 1) == 0) ++position;
            if (position == column_count) std::abort();
            std::swap(permutation[pivot], permutation[position]);
            uint64_t change[3] = {columns[0][permutation[pivot]], columns[1][permutation[pivot]], columns[2][permutation[pivot]]};
            change[word] ^= uint64_t(1) << bit;
            #pragma GCC ivdep
            for (int column = 0; column < column_count; ++column) {
                uint64_t mask = uint64_t(0) - ((columns[word][column] >> bit) & 1);
                columns[0][column] ^= change[0] & mask;
                columns[1][column] ^= change[1] & mask;
                columns[2][column] ^= change[2] & mask;
            }
        }
        uint64_t logical_mask[3] = {};
        uint64_t fault_mask[3] = {};
        for (int pivot = 0; pivot < pivots; ++pivot) {
            if (observable[permutation[pivot]]) logical_mask[pivot >> 6] |= uint64_t(1) << (pivot & 63);
            if (permutation[pivot] < fault_count) fault_mask[pivot >> 6] |= uint64_t(1) << (pivot & 63);
        }
        for (int position = pivots; position < column_count; ++position) {
            int column = permutation[position];
            transformed_observable[column] = observable[column] ^ ((__builtin_popcountll(columns[0][column] & logical_mask[0]) + __builtin_popcountll(columns[1][column] & logical_mask[1]) + __builtin_popcountll(columns[2][column] & logical_mask[2])) & 1);
        }
        std::fill(offsets.begin(), offsets.end(), 0);
        for (int first = pivots; first < split; ++first) {
            int first_id = permutation[first];
            for (int second = first + 1; second < split; ++second) {
                int second_id = permutation[second];
                uint64_t key = (((columns[2][first_id] ^ columns[2][second_id]) >> shift) << 1) | (transformed_observable[first_id] ^ transformed_observable[second_id]);
                ++offsets[key + 1];
            }
        }
        for (size_t key = 1; key < offsets.size(); ++key) offsets[key] += offsets[key - 1];
        cursors = offsets;
        for (int first = pivots; first < split; ++first) {
            int first_id = permutation[first];
            for (int second = first + 1; second < split; ++second) {
                int second_id = permutation[second];
                uint64_t key = (((columns[2][first_id] ^ columns[2][second_id]) >> shift) << 1) | (transformed_observable[first_id] ^ transformed_observable[second_id]);
                int entry = cursors[key]++;
                pairs[entry] = first_id | (second_id << 10);
                left_zero[entry] = columns[0][first_id] ^ columns[0][second_id];
                left_one[entry] = columns[1][first_id] ^ columns[1][second_id];
            }
        }
        for (int first = split; first < column_count; ++first) {
            int first_id = permutation[first];
            for (int second = first + 1; second < column_count; ++second) {
                int second_id = permutation[second];
                uint64_t right_zero = columns[0][first_id] ^ columns[0][second_id];
                uint64_t right_one = columns[1][first_id] ^ columns[1][second_id];
                uint64_t right_two = columns[2][first_id] ^ columns[2][second_id];
                uint64_t key = ((right_two >> shift) << 1) | (transformed_observable[first_id] ^ transformed_observable[second_id] ^ 1);
                auto check_entry = [&](int entry) {
                    int left_first = pairs[entry] & 1023;
                    int left_second = pairs[entry] >> 10;
                    uint64_t result_zero = right_zero ^ left_zero[entry];
                    int weight = __builtin_popcountll(result_zero);
                    if (weight + 4 > total_budget) return false;
                    uint64_t result_one = right_one ^ left_one[entry];
                    weight += __builtin_popcountll(result_one);
                    if (weight + 4 > total_budget) return false;
                    uint64_t result_two = right_two ^ columns[2][left_first] ^ columns[2][left_second];
                    weight += __builtin_popcountll(result_two);
                    if (weight + 4 > total_budget) return false;
                    int fault_weight = (first_id < fault_count) + (second_id < fault_count) + (left_first < fault_count) + (left_second < fault_count);
                    fault_weight += __builtin_popcountll(result_zero & fault_mask[0]) + __builtin_popcountll(result_one & fault_mask[1]) + __builtin_popcountll(result_two & fault_mask[2]);
                    if (weight + 4 - fault_weight > detector_budget[fault_weight]) return false;
                    std::vector<int> support = {first_id, second_id, left_first, left_second};
                    uint64_t results[3] = {result_zero, result_one, result_two};
                    for (int word = 0; word < 3; ++word) {
                        while (results[word]) {
                            int bit = __builtin_ctzll(results[word]);
                            support.push_back(permutation[64 * word + bit]);
                            results[word] &= results[word] - 1;
                        }
                    }
                    return save_candidate(support, elapsed);
                };
                int entry = offsets[key];
                int end = offsets[key + 1];
#if defined(__AVX512VPOPCNTDQ__) && defined(__AVX512VL__)
                __m256i broadcast_zero = _mm256_set1_epi64x(right_zero);
                __m256i broadcast_one = _mm256_set1_epi64x(right_one);
                while (entry + 4 <= end) {
                    __m256i weights_zero = _mm256_popcnt_epi64(_mm256_xor_si256(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(left_zero.data() + entry)), broadcast_zero));
                    __m256i weights_one = _mm256_popcnt_epi64(_mm256_xor_si256(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(left_one.data() + entry)), broadcast_one));
                    __m256i weights = _mm256_add_epi64(weights_zero, weights_one);
                    unsigned matches = _mm256_cmp_epi64_mask(weights, _mm256_set1_epi64x(total_budget - 4), _MM_CMPINT_LE);
                    while (matches) {
                        int offset = __builtin_ctz(matches);
                        if (check_entry(entry + offset)) return 0;
                        matches &= matches - 1;
                    }
                    entry += 4;
                }
#endif
                for (; entry < end; ++entry) if (check_entry(entry)) return 0;
            }
        }
        ++iterations;
    }
    std::cerr << "finished iterations=" << iterations << " score=" << best_score << '\n';
    return 1;
}
