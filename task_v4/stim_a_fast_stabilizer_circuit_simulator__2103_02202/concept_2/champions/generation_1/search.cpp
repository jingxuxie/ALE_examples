#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <random>
#include <thread>
#include <vector>

using Clock = std::chrono::steady_clock;
constexpr int count = 512;
alignas(64) uint64_t original[3][count];
int observable[count];
std::atomic<int> best_weight{513};
std::atomic<bool> finished{false};
std::atomic<uint64_t> iterations{0};
std::mutex output_mutex;
Clock::time_point start_time;
int time_limit = 2400;

void save_candidate(std::vector<int> support, int worker) {
    std::sort(support.begin(), support.end());
    if (std::adjacent_find(support.begin(), support.end()) != support.end()) {
        std::cerr << "Duplicate support\n";
        std::abort();
    }
    uint64_t syndrome[3] = {};
    int logical = 0;
    for (int fault : support) {
        for (int word = 0; word < 3; ++word) syndrome[word] ^= original[word][fault];
        logical ^= observable[fault];
    }
    if (syndrome[0] || syndrome[1] || syndrome[2]) {
        std::cerr << "Invalid reconstructed support\n";
        std::abort();
    }
    if (!logical) return;
    std::lock_guard<std::mutex> lock(output_mutex);
    if (static_cast<int>(support.size()) >= best_weight.load()) return;
    std::ofstream output("witness.json");
    output << "{\"faults\": [";
    for (size_t index = 0; index < support.size(); ++index) {
        if (index) output << ", ";
        output << support[index];
    }
    output << "]}\n";
    output.close();
    best_weight.store(support.size());
    double elapsed = std::chrono::duration<double>(Clock::now() - start_time).count();
    std::cerr << "best " << support.size() << " worker " << worker << " elapsed " << elapsed << " support";
    for (int fault : support) std::cerr << ' ' << fault;
    std::cerr << '\n';
    if (support.size() <= 20) finished.store(true);
}

void search_worker(int worker, uint64_t seed, int residual) {
    const int pivots = 192 - residual;
    const int split = pivots + (count - pivots) / 2;
    const int shift = 64 - residual;
    std::mt19937_64 random(seed);
    alignas(64) uint64_t columns[3][count];
    std::array<int, count> permutation;
    std::vector<int> heads(1 << residual, -1);
    std::vector<int> next(16000);
    std::vector<uint32_t> pairs(16000);
    uint64_t local_iterations = 0;
    while (!finished.load(std::memory_order_relaxed)) {
        if ((local_iterations & 127) == 0 &&
            std::chrono::duration<double>(Clock::now() - start_time).count() >= time_limit) break;
        std::copy(&original[0][0], &original[0][0] + 3 * count, &columns[0][0]);
        std::iota(permutation.begin(), permutation.end(), 0);
        std::shuffle(permutation.begin(), permutation.end(), random);
        for (int pivot = 0; pivot < pivots; ++pivot) {
            const int word = pivot >> 6;
            const int bit = pivot & 63;
            int position = pivot;
            while (position < count && ((columns[word][permutation[position]] >> bit) & 1) == 0) ++position;
            if (position == count) std::abort();
            std::swap(permutation[pivot], permutation[position]);
            uint64_t change[3] = {columns[0][permutation[pivot]], columns[1][permutation[pivot]], columns[2][permutation[pivot]]};
            change[word] ^= uint64_t(1) << bit;
            #pragma GCC ivdep
            for (int column = 0; column < count; ++column) {
                uint64_t mask = uint64_t(0) - ((columns[word][column] >> bit) & 1);
                columns[0][column] ^= change[0] & mask;
                columns[1][column] ^= change[1] & mask;
                columns[2][column] ^= change[2] & mask;
            }
        }
        std::fill(heads.begin(), heads.end(), -1);
        int pair_count = 0;
        for (int first = pivots; first < split; ++first) {
            const int first_id = permutation[first];
            for (int second = first + 1; second < split; ++second) {
                const int second_id = permutation[second];
                const uint64_t key = (columns[2][first_id] ^ columns[2][second_id]) >> shift;
                next[pair_count] = heads[key];
                pairs[pair_count] = first_id | (second_id << 9);
                heads[key] = pair_count++;
            }
        }
        int threshold = best_weight.load(std::memory_order_relaxed) - 4;
        for (int first = split; first < count; ++first) {
            const int first_id = permutation[first];
            for (int second = first + 1; second < count; ++second) {
                const int second_id = permutation[second];
                const uint64_t right_zero = columns[0][first_id] ^ columns[0][second_id];
                const uint64_t right_one = columns[1][first_id] ^ columns[1][second_id];
                const uint64_t right_two = columns[2][first_id] ^ columns[2][second_id];
                const uint64_t key = right_two >> shift;
                for (int entry = heads[key]; entry != -1; entry = next[entry]) {
                    const int left_first = pairs[entry] & 511;
                    const int left_second = pairs[entry] >> 9;
                    const uint64_t result_zero = right_zero ^ columns[0][left_first] ^ columns[0][left_second];
                    int weight = __builtin_popcountll(result_zero);
                    if (weight >= threshold) continue;
                    const uint64_t result_one = right_one ^ columns[1][left_first] ^ columns[1][left_second];
                    weight += __builtin_popcountll(result_one);
                    if (weight >= threshold) continue;
                    const uint64_t result_two = right_two ^ columns[2][left_first] ^ columns[2][left_second];
                    weight += __builtin_popcountll(result_two);
                    if (weight >= threshold) continue;
                    std::vector<int> support = {first_id, second_id, left_first, left_second};
                    uint64_t results[3] = {result_zero, result_one, result_two};
                    for (int word = 0; word < 3; ++word) {
                        while (results[word]) {
                            int bit = __builtin_ctzll(results[word]);
                            support.push_back(permutation[64 * word + bit]);
                            results[word] &= results[word] - 1;
                        }
                    }
                    save_candidate(std::move(support), worker);
                    threshold = best_weight.load(std::memory_order_relaxed) - 4;
                }
            }
        }
        ++local_iterations;
        iterations.fetch_add(1, std::memory_order_relaxed);
    }
}

int main(int argc, char **argv) {
    int threads = argc > 1 ? std::atoi(argv[1]) : 8;
    time_limit = argc > 2 ? std::atoi(argv[2]) : 2400;
    uint64_t seed = argc > 3 ? std::strtoull(argv[3], nullptr, 10) : 730001;
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < count; ++fault) {
        input >> std::hex >> original[0][fault] >> original[1][fault] >> original[2][fault] >> observable[fault];
    }
    if (!input) return 2;
    start_time = Clock::now();
    std::vector<std::thread> workers;
    for (int worker = 0; worker < threads; ++worker) workers.emplace_back(search_worker, worker, seed + 1000003 * worker, 16 + 2 * (worker % 2));
    while (!finished.load()) {
        std::this_thread::sleep_for(std::chrono::seconds(10));
        double elapsed = std::chrono::duration<double>(Clock::now() - start_time).count();
        std::cerr << "progress seconds=" << elapsed << " iterations=" << iterations.load() << " best=" << best_weight.load() << '\n';
        if (elapsed >= time_limit) break;
    }
    for (auto &worker : workers) worker.join();
    return best_weight.load() <= 20 ? 0 : 1;
}
