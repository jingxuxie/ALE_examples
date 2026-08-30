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

using Clock = std::chrono::steady_clock;
constexpr int count = 512;
alignas(64) uint64_t original[3][count];
int observable[count];
int best_exact = 513;
int best_even = 513;
double best_score = 0;
bool finished = false;
Clock::time_point start_time;

double score(int weight, int syndrome_weight) {
    if (weight <= 36 && syndrome_weight == 0) return 1;
    return 0.65 + 0.15 * std::min(1.0, 36.0 / weight) - 0.45 * syndrome_weight / 192;
}

void write_support(const std::vector<int>& support, const std::string& path) {
    std::ofstream output(path);
    output << "{\"faults\": [";
    for (size_t position = 0; position < support.size(); ++position) {
        if (position) output << ", ";
        output << support[position];
    }
    output << "]}\n";
}

void save_candidate(std::vector<int> support) {
    std::sort(support.begin(), support.end());
    if (support.empty() || std::adjacent_find(support.begin(), support.end()) != support.end()) return;
    uint64_t syndrome[3] = {};
    int logical = 0;
    for (int fault : support) {
        for (int word = 0; word < 3; ++word) syndrome[word] ^= original[word][fault];
        logical ^= observable[fault];
    }
    int syndrome_weight = 0;
    for (uint64_t word : syndrome) syndrome_weight += __builtin_popcountll(word);
    int weight = support.size();
    if (!logical) {
        if (syndrome_weight == 0 && weight < best_even) {
            best_even = weight;
            write_support(support, "even.json");
            std::cerr << "even weight=" << weight << '\n';
        }
        return;
    }
    double candidate_score = score(weight, syndrome_weight);
    double elapsed = std::chrono::duration<double>(Clock::now() - start_time).count();
    if (syndrome_weight == 0 && weight < best_exact) {
        best_exact = weight;
        write_support(support, "exact.json");
        write_support(support, "candidate_" + std::to_string(weight) + "_0.json");
        std::cerr << "exact weight=" << weight << " seconds=" << elapsed << '\n';
    }
    if (candidate_score > best_score + 1e-12) {
        best_score = candidate_score;
        write_support(support, "witness.json");
        write_support(support, "candidate_" + std::to_string(weight) + "_" + std::to_string(syndrome_weight) + ".json");
        std::cerr << "best score=" << best_score << " weight=" << weight << " syndrome=" << syndrome_weight << " seconds=" << elapsed << '\n';
    }
    if (weight <= 36 && syndrome_weight == 0) {
        write_support(support, "success.json");
        finished = true;
    }
}

void load_candidate(const std::string& path) {
    std::ifstream input(path);
    if (!input) return;
    std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    std::vector<int> support;
    for (size_t position = 0; position < text.size();) {
        if (text[position] < '0' || text[position] > '9') {
            ++position;
            continue;
        }
        int value = 0;
        while (position < text.size() && text[position] >= '0' && text[position] <= '9') value = value * 10 + text[position++] - '0';
        if (value >= count) return;
        support.push_back(value);
    }
    save_candidate(std::move(support));
}

int main(int argc, char** argv) {
    int seconds = argc > 1 ? std::atoi(argv[1]) : 600;
    int constraints = argc > 2 ? std::atoi(argv[2]) : 192;
    int residual = argc > 3 ? std::atoi(argv[3]) : 16;
    int swaps = argc > 4 ? std::atoi(argv[4]) : 12;
    uint64_t seed = argc > 5 ? std::strtoull(argv[5], nullptr, 10) : 48279481;
    int filter_row = argc > 6 ? std::atoi(argv[6]) : -1;
    int filter_value = argc > 7 ? std::atoi(argv[7]) : 1;
    bool basis_filter = argc > 8 && std::atoi(argv[8]);
    if (constraints < 128 || constraints > 192 || residual > 22 || residual < 4) return 2;
    const int pivots = constraints - residual;
    const uint64_t key_mask = (uint64_t(1) << residual) - 1;
    uint64_t pivot_masks[3];
    for (int word = 0; word < 3; ++word) {
        int bits = std::clamp(pivots - 64 * word, 0, 64);
        pivot_masks[word] = bits == 64 ? ~uint64_t(0) : (uint64_t(1) << bits) - 1;
    }
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < count; ++fault) input >> std::hex >> original[0][fault] >> original[1][fault] >> original[2][fault] >> observable[fault];
    if (!input) return 2;
    bool filter_observable = filter_row == 192;
    if (filter_row >= 0 && filter_row < 191) {
        for (int fault = 0; fault < count; ++fault) {
            uint64_t difference = ((original[filter_row >> 6][fault] >> (filter_row & 63)) ^ (original[2][fault] >> 63)) & 1;
            original[filter_row >> 6][fault] ^= difference << (filter_row & 63);
            original[2][fault] ^= difference << 63;
        }
        filter_row = 191;
    }
    auto matches_filter = [&](int fault) {
        int value = filter_observable ? observable[fault] : int((original[filter_row >> 6][fault] >> (filter_row & 63)) & 1);
        return value == filter_value;
    };
    int active_count = count;
    int preferred_count = count;
    if (filter_row >= 0) {
        preferred_count = 0;
        for (int fault = 0; fault < count; ++fault) preferred_count += matches_filter(fault);
        if (!basis_filter) active_count = preferred_count;
        if (active_count <= pivots + 4) return 4;
    }
    const int split = pivots + (active_count - pivots) / 2;
    std::cerr << "active_count=" << active_count << " filter_row=" << filter_row << '\n';
    start_time = Clock::now();
    load_candidate("witness.json");
    load_candidate("exact.json");
    load_candidate("baseline_long.json");
    std::mt19937_64 random(seed);
    alignas(64) uint64_t columns[3][count];
    alignas(64) uint64_t logical_columns[count];
    std::array<int, count> permutation;
    const int bucket_count = 1 << (residual + 1);
    std::vector<int> bucket_sizes(bucket_count), offsets(bucket_count), cursor(bucket_count);
    std::vector<uint32_t> raw_pairs(65536), raw_keys(65536), pairs(524288);
    std::vector<uint64_t> raw_zero(65536), raw_one(65536), raw_two(65536);
    std::vector<uint64_t> left_zero(524288), left_one(524288), left_two(524288);
    uint64_t iterations = 0;
    double next_report = 10;
    auto pivot_column = [&](int pivot, int position) {
        const int word = pivot >> 6;
        const int bit = pivot & 63;
        std::swap(permutation[pivot], permutation[position]);
        uint64_t change[3] = {columns[0][permutation[pivot]], columns[1][permutation[pivot]], columns[2][permutation[pivot]]};
        uint64_t logical_change = logical_columns[permutation[pivot]];
        change[word] ^= uint64_t(1) << bit;
        #pragma GCC ivdep
        for (int column = 0; column < count; ++column) {
            uint64_t mask = uint64_t(0) - ((columns[word][column] >> bit) & 1);
            columns[0][column] ^= change[0] & mask;
            columns[1][column] ^= change[1] & mask;
            columns[2][column] ^= change[2] & mask;
            logical_columns[column] ^= logical_change & mask;
        }
    };
    auto get_key = [&](uint64_t first, uint64_t second, uint64_t third) {
        uint64_t words[3] = {first, second, third};
        int word = pivots >> 6;
        int bit = pivots & 63;
        uint64_t value = words[word] >> bit;
        if (bit + residual > 64) value |= words[word + 1] << (64 - bit);
        return value & key_mask;
    };
    while (!finished) {
        if ((iterations & 255) == 0) {
            double elapsed = std::chrono::duration<double>(Clock::now() - start_time).count();
            if (elapsed >= seconds) break;
            if (elapsed >= next_report) {
                std::cerr << "progress seconds=" << elapsed << " iterations=" << iterations << " score=" << best_score << " exact=" << best_exact << '\n';
                next_report += 10;
            }
        }
        if (iterations % 4096 == 0 || swaps == 0) {
            std::copy(&original[0][0], &original[0][0] + 3 * count, &columns[0][0]);
            for (int fault = 0; fault < count; ++fault) logical_columns[fault] = observable[fault];
            std::iota(permutation.begin(), permutation.end(), 0);
            if (filter_row >= 0) std::stable_partition(permutation.begin(), permutation.end(), matches_filter);
            if (basis_filter) {
                std::shuffle(permutation.begin(), permutation.begin() + preferred_count, random);
                std::shuffle(permutation.begin() + preferred_count, permutation.end(), random);
            } else {
                std::shuffle(permutation.begin(), permutation.begin() + active_count, random);
            }
            for (int pivot = 0; pivot < pivots; ++pivot) {
                int position = pivot;
                while (position < active_count && ((columns[pivot >> 6][permutation[position]] >> (pivot & 63)) & 1) == 0) ++position;
                if (position == active_count) return 3;
                pivot_column(pivot, position);
            }
            if (basis_filter) std::shuffle(permutation.begin() + pivots, permutation.begin() + active_count, random);
        } else {
            for (int change = 0; change < swaps; ++change) {
                int pivot = random() % pivots;
                int position;
                do {
                    position = pivots + random() % (active_count - pivots);
                } while (((columns[pivot >> 6][permutation[position]] >> (pivot & 63)) & 1) == 0 || (basis_filter && !matches_filter(permutation[position])));
                pivot_column(pivot, position);
            }
        }
        std::fill(bucket_sizes.begin(), bucket_sizes.end(), 0);
        int pair_count = 0;
        for (int first = pivots; first < split; ++first) {
            int first_id = permutation[first];
            for (int second = first + 1; second < split; ++second) {
                int second_id = permutation[second];
                uint64_t value_zero = columns[0][first_id] ^ columns[0][second_id];
                uint64_t value_one = columns[1][first_id] ^ columns[1][second_id];
                uint64_t value_two = columns[2][first_id] ^ columns[2][second_id];
                uint64_t key = get_key(value_zero, value_one, value_two) | ((logical_columns[first_id] ^ logical_columns[second_id]) << residual);
                raw_keys[pair_count] = key;
                raw_pairs[pair_count] = first_id | (second_id << 9);
                raw_zero[pair_count] = value_zero;
                raw_one[pair_count] = value_one;
                raw_two[pair_count] = value_two;
                ++bucket_sizes[key];
                ++pair_count;
            }
        }
        int storage_size = 0;
        for (int key = 0; key < bucket_count; ++key) {
            offsets[key] = storage_size;
            cursor[key] = storage_size;
            storage_size += (bucket_sizes[key] + 7) & ~7;
        }
        if (storage_size > 524288) return 5;
        for (int entry = 0; entry < pair_count; ++entry) {
            int position = cursor[raw_keys[entry]]++;
            pairs[position] = raw_pairs[entry];
            left_zero[position] = raw_zero[entry];
            left_one[position] = raw_one[entry];
            left_two[position] = raw_two[entry];
        }
        int threshold = std::min(192, std::max(best_exact - 1, int(5.4 / std::max(0.00001, best_score - 0.65))));
        for (int first = split; first < active_count; ++first) {
            int first_id = permutation[first];
            for (int second = first + 1; second < active_count; ++second) {
                int second_id = permutation[second];
                uint64_t right_zero = columns[0][first_id] ^ columns[0][second_id];
                uint64_t right_one = columns[1][first_id] ^ columns[1][second_id];
                uint64_t right_two = columns[2][first_id] ^ columns[2][second_id];
                uint64_t key = get_key(right_zero, right_one, right_two) | ((logical_columns[first_id] ^ logical_columns[second_id] ^ 1) << residual);
                auto consider_entry = [&](int entry) {
                    uint64_t result_zero = right_zero ^ left_zero[entry];
                    uint64_t result_one = right_one ^ left_one[entry];
                    uint64_t result_two = right_two ^ left_two[entry];
                    int weight = 4 + __builtin_popcountll(result_zero & pivot_masks[0]) + __builtin_popcountll(result_one & pivot_masks[1]) + __builtin_popcountll(result_two & pivot_masks[2]);
                    if (weight > threshold) return;
                    int syndrome_weight = __builtin_popcountll(result_zero & ~pivot_masks[0]) + __builtin_popcountll(result_one & ~pivot_masks[1]) + __builtin_popcountll(result_two & ~pivot_masks[2]);
                    if (!(syndrome_weight == 0 && weight < best_exact) && score(weight, syndrome_weight) <= best_score + 1e-12) return;
                    int left_first = pairs[entry] & 511;
                    int left_second = pairs[entry] >> 9;
                    std::vector<int> support = {first_id, second_id, left_first, left_second};
                    uint64_t results[3] = {result_zero & pivot_masks[0], result_one & pivot_masks[1], result_two & pivot_masks[2]};
                    for (int word = 0; word < 3; ++word) {
                        while (results[word]) {
                            int bit = __builtin_ctzll(results[word]);
                            support.push_back(permutation[64 * word + bit]);
                            results[word] &= results[word] - 1;
                        }
                    }
                    save_candidate(std::move(support));
                };
                int begin = offsets[key];
                int end = begin + bucket_sizes[key];
                #ifdef __AVX512VPOPCNTDQ__
                for (int base = begin; base < end; base += 8) {
                    __m512i result_zero = _mm512_xor_si512(_mm512_loadu_si512(left_zero.data() + base), _mm512_set1_epi64(right_zero));
                    __m512i result_one = _mm512_xor_si512(_mm512_loadu_si512(left_one.data() + base), _mm512_set1_epi64(right_one));
                    __m512i result_two = _mm512_xor_si512(_mm512_loadu_si512(left_two.data() + base), _mm512_set1_epi64(right_two));
                    __m512i weight_zero = _mm512_popcnt_epi64(_mm512_and_si512(result_zero, _mm512_set1_epi64(pivot_masks[0])));
                    __m512i weight_one = _mm512_popcnt_epi64(_mm512_and_si512(result_one, _mm512_set1_epi64(pivot_masks[1])));
                    __m512i weight_two = _mm512_popcnt_epi64(_mm512_and_si512(result_two, _mm512_set1_epi64(pivot_masks[2])));
                    __m512i weights = _mm512_add_epi64(_mm512_add_epi64(weight_zero, weight_one), _mm512_add_epi64(weight_two, _mm512_set1_epi64(4)));
                    unsigned matches = _mm512_cmple_epu64_mask(weights, _mm512_set1_epi64(threshold));
                    matches &= (1U << std::min(8, end - base)) - 1;
                    while (matches) {
                        int position = __builtin_ctz(matches);
                        consider_entry(base + position);
                        matches &= matches - 1;
                    }
                }
                #else
                for (int entry = begin; entry < end; ++entry) consider_entry(entry);
                #endif
            }
        }
        ++iterations;
    }
    std::cerr << "final iterations=" << iterations << " exact=" << best_exact << " score=" << best_score << '\n';
    return finished ? 0 : 1;
}
