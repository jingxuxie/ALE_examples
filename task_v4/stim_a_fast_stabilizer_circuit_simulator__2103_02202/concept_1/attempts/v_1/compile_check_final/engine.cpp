#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using Clock = std::chrono::steady_clock;

struct alignas(32) Values {
    double value[8];
};

struct Channel {
    int branches;
    uint32_t signature[3];
    int logical[3];
    double probabilities[3][8];
    Values factors[8];
};

struct State {
    double score;
    uint64_t mask;
    bool operator<(const State &other) const {
        if (score != other.score) return score < other.score;
        return mask < other.mask;
    }
};

struct Evaluation {
    double actual, optimistic;
};

struct Optimizer {
    int detectors, count, budget, regimes, channel_count;
    std::vector<uint32_t> taps;
    std::vector<Channel> channels;
    std::vector<uint32_t> keys;
    std::vector<Values> fourier;
    std::unordered_map<uint64_t, Evaluation> evaluated;
    std::priority_queue<State> archive;
    std::priority_queue<State> optimistic_archive;
    std::unordered_set<uint64_t> archived;
    std::mt19937_64 random{917413};
    int cache_bits;
    uint64_t evaluations = 0, misses = 0;
    Clock::time_point start, deadline;
    bool stopped = false;
    State best{1.0, 0};

    Optimizer(double seconds) {
        start = Clock::now();
        deadline = start + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
        std::cin >> detectors >> count >> budget >> regimes >> channel_count;
        taps.resize(count);
        for (auto &tap : taps) std::cin >> tap;
        channels.resize(channel_count);
        for (auto &channel : channels) {
            std::cin >> channel.branches;
            uint32_t full[3];
            for (int branch = 0; branch < channel.branches; ++branch) {
                std::cin >> full[branch];
                channel.signature[branch] = full[branch] & ((1u << detectors) - 1);
                channel.logical[branch] = full[branch] >> detectors;
            }
            double probabilities[8][3] = {};
            for (int regime = 0; regime < regimes; ++regime)
                for (int branch = 0; branch < channel.branches; ++branch) {
                    std::cin >> probabilities[regime][branch];
                    channel.probabilities[branch][regime] = probabilities[regime][branch];
                }
            for (int code = 0; code < (1 << channel.branches); ++code) {
                for (int regime = 0; regime < 8; ++regime) {
                    double factor = 1;
                    for (int branch = 0; branch < channel.branches; ++branch)
                        if (((code >> branch) & 1) ^ (full[branch] >> detectors))
                            factor -= 2 * probabilities[regime][branch];
                    channel.factors[code].value[regime] = factor;
                }
            }
        }
        cache_bits = std::min(detectors, 22);
        keys.assign(1u << cache_bits, UINT32_MAX);
        fourier.resize(1u << cache_bits);
        evaluated.reserve(500000);
    }

    const Values &get_fourier(uint32_t mask) {
        uint32_t slot = detectors <= cache_bits ? mask : (mask * 2654435761u) >> (32 - cache_bits);
        if (keys[slot] != mask) {
            ++misses;
            keys[slot] = mask;
            Values product;
            for (int regime = 0; regime < 8; ++regime) product.value[regime] = 1;
            for (const auto &channel : channels) {
                int code = 0;
                for (int branch = 0; branch < channel.branches; ++branch)
                    code |= __builtin_parity(mask & channel.signature[branch]) << branch;
                for (int regime = 0; regime < 8; ++regime)
                    product.value[regime] *= channel.factors[code].value[regime];
            }
            fourier[slot] = product;
        }
        return fourier[slot];
    }

    int distribution(uint64_t mask, Values *difference) {
        uint32_t combinations[128] = {};
        int size = 1;
        for (uint64_t remaining = mask; remaining; remaining &= remaining - 1) {
            int tap = __builtin_ctzll(remaining);
            for (int syndrome = 0; syndrome < size; ++syndrome)
                combinations[syndrome + size] = combinations[syndrome] ^ taps[tap];
            size *= 2;
        }
        for (int syndrome = 0; syndrome < size; ++syndrome)
            difference[syndrome] = get_fourier(combinations[syndrome]);
        for (int step = 1; step < size; step *= 2) {
            for (int block = 0; block < size; block += step * 2) {
                for (int offset = 0; offset < step; ++offset) {
                    Values first = difference[block + offset];
                    Values second = difference[block + offset + step];
                    for (int regime = 0; regime < 8; ++regime) {
                        difference[block + offset].value[regime] = first.value[regime] + second.value[regime];
                        difference[block + offset + step].value[regime] = first.value[regime] - second.value[regime];
                    }
                }
            }
        }
        double inverse = 1.0 / size;
        for (int syndrome = 0; syndrome < size; ++syndrome)
            for (int regime = 0; regime < 8; ++regime)
                difference[syndrome].value[regime] *= inverse;
        return size;
    }

    double fit(Values *difference, int size, int *answer = nullptr, bool thorough = false) {
        int signs[128], best_signs[128];
        double best_score = 1, best_mean = 1;
        double weights[8] = {};
        for (int regime = 0; regime < regimes; ++regime) weights[regime] = 1.0 / regimes;
        int trials = thorough ? 15 : 2;
        for (int trial = 0; trial < trials; ++trial) {
            double risks[8];
            for (int regime = 0; regime < regimes; ++regime) risks[regime] = 0.5;
            for (int syndrome = 0; syndrome < size; ++syndrome) {
                double average = 0;
                for (int regime = 0; regime < regimes; ++regime)
                    average += weights[regime] * difference[syndrome].value[regime];
                signs[syndrome] = average >= 0 ? 1 : -1;
                for (int regime = 0; regime < regimes; ++regime)
                    risks[regime] -= 0.5 * signs[syndrome] * difference[syndrome].value[regime];
            }
            double score = *std::max_element(risks, risks + regimes);
            double mean = 0;
            for (int regime = 0; regime < regimes; ++regime) mean += risks[regime];
            for (int sweep = 0; sweep < (thorough ? 8 : 3); ++sweep) {
                bool changed = false;
                for (int syndrome = 0; syndrome < size; ++syndrome) {
                    double candidate[8], maximum = -1, total = 0;
                    for (int regime = 0; regime < regimes; ++regime) {
                        candidate[regime] = risks[regime] + signs[syndrome] * difference[syndrome].value[regime];
                        maximum = std::max(maximum, candidate[regime]);
                        total += candidate[regime];
                    }
                    if (maximum < score - 1e-14 || (std::abs(maximum - score) < 1e-14 && total < mean - 1e-14)) {
                        for (int regime = 0; regime < regimes; ++regime) risks[regime] = candidate[regime];
                        score = maximum;
                        mean = total;
                        signs[syndrome] = -signs[syndrome];
                        changed = true;
                    }
                }
                if (!changed) break;
            }
            if (score < best_score || (score == best_score && mean < best_mean)) {
                best_score = score;
                best_mean = mean;
                std::copy(signs, signs + size, best_signs);
            }
            int worst = std::max_element(risks, risks + regimes) - risks;
            for (int regime = 0; regime < regimes; ++regime)
                weights[regime] = 0.65 * weights[regime] + (regime == worst ? 0.35 : 0);
        }
        if (answer)
            for (int syndrome = 0; syndrome < size; ++syndrome) answer[syndrome] = best_signs[syndrome] < 0;
        return best_score;
    }

    void remember(uint64_t mask, double score, double bound) {
        if (score < best.score) best = {score, mask};
        if (optimistic_archive.size() < 96 || bound < optimistic_archive.top().score) {
            optimistic_archive.push({bound, mask});
            if (optimistic_archive.size() > 96) optimistic_archive.pop();
        }
        if (archive.size() >= 96 && score >= archive.top().score) return;
        if (archived.count(mask)) return;
        archive.push({score, mask});
        archived.insert(mask);
        if (archive.size() > 96) {
            archived.erase(archive.top().mask);
            archive.pop();
        }
    }

    double evaluate(uint64_t mask, bool optimistic = false) {
        auto found = evaluated.find(mask);
        if (found != evaluated.end()) return optimistic ? found->second.optimistic : found->second.actual;
        if ((++evaluations & 255) == 0 && Clock::now() >= deadline) stopped = true;
        Values difference[128];
        int size = distribution(mask, difference);
        double score = fit(difference, size);
        Values norms{};
        for (int syndrome = 0; syndrome < size; ++syndrome)
            for (int regime = 0; regime < 8; ++regime)
                norms.value[regime] += std::abs(difference[syndrome].value[regime]);
        double bound = (1 - *std::min_element(norms.value, norms.value + regimes)) * 0.5;
        evaluated.emplace(mask, Evaluation{score, bound});
        if (__builtin_popcountll(mask) == budget) remember(mask, score, bound);
        return optimistic ? bound : score;
    }

    std::vector<State> beam_search() {
        std::vector<State> beam{{evaluate(0), 0}};
        for (int width = 1; width <= budget && !stopped; ++width) {
            std::vector<State> next;
            std::unordered_set<uint64_t> seen;
            for (const auto &state : beam) {
                for (int tap = 0; tap < count; ++tap) {
                    if ((state.mask >> tap) & 1) continue;
                    uint64_t proposal = state.mask | (1ull << tap);
                    if (seen.insert(proposal).second) next.push_back({evaluate(proposal), proposal});
                    if (stopped) break;
                }
                if (stopped) break;
            }
            int limit = width < 3 ? 1024 : 256;
            if (next.size() > static_cast<size_t>(limit)) {
                std::nth_element(next.begin(), next.begin() + limit, next.end());
                next.resize(limit);
            }
            std::sort(next.begin(), next.end());
            beam = std::move(next);
        }
        return beam;
    }

    std::vector<State> spectral_seeds() {
        double total_seconds = std::chrono::duration<double>(deadline - start).count();
        auto spectral_deadline = start + std::chrono::duration_cast<Clock::duration>(
            std::chrono::duration<double>(std::min(5.0, total_seconds * 0.22)));
        std::vector<int> permutation(count);
        for (int tap = 0; tap < count; ++tap) permutation[tap] = tap;
        std::shuffle(permutation.begin(), permutation.end(), random);
        std::vector<std::priority_queue<State>> pools(regimes + 2);
        uint64_t scans = 0;
        bool done = false;
        for (int width = 1; width <= budget && !done; ++width) {
            uint64_t mask = (1ull << width) - 1;
            uint32_t parity = 0;
            for (int position = 0; position < width; ++position) parity ^= taps[permutation[position]];
            while (mask < (1ull << count)) {
                const Values &values = get_fourier(parity);
                double minimum = 1, maximum = -1, average = 0;
                double objectives[8];
                for (int regime = 0; regime < regimes; ++regime) {
                    double value = values.value[regime];
                    minimum = std::min(minimum, value);
                    maximum = std::max(maximum, value);
                    average += value;
                    objectives[regime + 2] = -std::abs(value);
                }
                objectives[0] = -std::max(minimum, -maximum);
                objectives[1] = -std::abs(average) / regimes;
                uint64_t actual = 0;
                bool converted = false;
                for (int objective = 0; objective < regimes + 2; ++objective) {
                    auto &pool = pools[objective];
                    if (pool.size() >= 48 && objectives[objective] >= pool.top().score) continue;
                    if (!converted) {
                        for (uint64_t remaining = mask; remaining; remaining &= remaining - 1)
                            actual |= 1ull << permutation[__builtin_ctzll(remaining)];
                        converted = true;
                    }
                    pool.push({objectives[objective], actual});
                    if (pool.size() > 48) pool.pop();
                }
                uint64_t lowest = mask & -mask;
                uint64_t next = mask + lowest;
                next = (((next ^ mask) >> 2) / lowest) | next;
                uint64_t changed = next ^ mask;
                if (next >= (1ull << count)) break;
                for (; changed; changed &= changed - 1)
                    parity ^= taps[permutation[__builtin_ctzll(changed)]];
                mask = next;
                if ((++scans & 4095) == 0 && Clock::now() >= spectral_deadline) {
                    done = true;
                    break;
                }
            }
        }
        std::unordered_set<uint64_t> seen;
        std::vector<State> seeds;
        for (auto &pool : pools) while (!pool.empty() && !stopped) {
            uint64_t mask = pool.top().mask;
            pool.pop();
            if (!seen.insert(mask).second) continue;
            while (__builtin_popcountll(mask) < budget && !stopped) {
                State next{1, 0};
                for (int tap = 0; tap < count; ++tap) {
                    if ((mask >> tap) & 1) continue;
                    uint64_t proposal = mask | (1ull << tap);
                    double score = evaluate(proposal);
                    if (score < next.score) next = {score, proposal};
                }
                mask = next.mask;
            }
            if (__builtin_popcountll(mask) == budget) seeds.push_back({evaluate(mask), mask});
        }
        std::cerr << "spectral_scans=" << scans << " seeds=" << seeds.size() << " ";
        return seeds;
    }

    std::vector<State> informed_seeds() {
        if (detectors < 4) return {};
        double total_seconds = std::chrono::duration<double>(deadline - start).count();
        auto informed_deadline = start + std::chrono::duration_cast<Clock::duration>(
            std::chrono::duration<double>(std::min(4.7, total_seconds * 0.19)));
        if (Clock::now() >= informed_deadline) return {};
        std::vector<std::priority_queue<State>> pools(regimes + 2);
        int pool_limit = 128;
        auto consider = [&](uint32_t mask) {
            const Values &values = get_fourier(mask);
            double minimum = 1, maximum = -1, average = 0;
            double objectives[8];
            for (int regime = 0; regime < regimes; ++regime) {
                double value = values.value[regime];
                minimum = std::min(minimum, value);
                maximum = std::max(maximum, value);
                average += value;
                objectives[regime + 2] = -std::abs(value);
            }
            objectives[0] = -std::max(minimum, -maximum);
            objectives[1] = -std::abs(average) / regimes;
            for (int objective = 0; objective < regimes + 2; ++objective) {
                auto &pool = pools[objective];
                if (pool.size() >= static_cast<size_t>(pool_limit) && objectives[objective] >= pool.top().score) continue;
                pool.push({objectives[objective], mask});
                if (pool.size() > static_cast<size_t>(pool_limit)) pool.pop();
            }
        };
        if (detectors <= 21) {
            for (uint32_t mask = 0; mask < (1u << detectors); ++mask) {
                consider(mask);
                if ((mask & 16383) == 16383 && Clock::now() + std::chrono::milliseconds(500) >= informed_deadline) break;
            }
        } else {
            struct Constraint {
                uint32_t mask;
                int logical;
                double probabilities[8];
            };
            std::vector<Constraint> constraints;
            for (const auto &channel : channels) for (int branch = 0; branch < channel.branches; ++branch) {
                Constraint constraint;
                constraint.mask = channel.signature[branch];
                constraint.logical = channel.logical[branch];
                for (int regime = 0; regime < regimes; ++regime)
                    constraint.probabilities[regime] = channel.probabilities[branch][regime];
                constraints.push_back(constraint);
            }
            std::unordered_set<uint32_t> seen;
            seen.reserve(100000);
            std::uniform_real_distribution<double> uniform(0.00001, 0.99999);
            for (int trial = 0; trial < 384; ++trial) {
                double weights[8];
                for (int regime = 0; regime < regimes; ++regime) {
                    if (trial == 0) weights[regime] = 1.0 / regimes;
                    else if (trial <= regimes) weights[regime] = regime == trial - 1;
                    else weights[regime] = -std::log(uniform(random));
                }
                std::vector<std::pair<double, int>> order;
                for (size_t index = 0; index < constraints.size(); ++index) {
                    double importance = 0;
                    for (int regime = 0; regime < regimes; ++regime)
                        importance += weights[regime] * constraints[index].probabilities[regime];
                    if (trial > regimes) importance /= 0.1 - std::log(uniform(random));
                    order.push_back({-importance, static_cast<int>(index)});
                }
                std::sort(order.begin(), order.end());
                uint32_t rows[28] = {}, codes[28] = {}, solutions[28] = {};
                uint32_t logical = 0;
                int rank = 0;
                for (const auto &entry : order) {
                    const auto &constraint = constraints[entry.second];
                    uint32_t row = constraint.mask, code = 1u << rank;
                    while (row) {
                        int pivot = 31 - __builtin_clz(row);
                        if (rows[pivot]) {
                            row ^= rows[pivot];
                            code ^= codes[pivot];
                        } else {
                            rows[pivot] = row;
                            codes[pivot] = code;
                            logical |= static_cast<uint32_t>(constraint.logical) << rank;
                            ++rank;
                            break;
                        }
                    }
                    if (rank == detectors) break;
                }
                for (int pivot = 0; pivot < detectors; ++pivot) {
                    solutions[pivot] = codes[pivot];
                    uint32_t remaining = rows[pivot] & ~(1u << pivot);
                    for (; remaining; remaining &= remaining - 1)
                        solutions[pivot] ^= solutions[__builtin_ctz(remaining)];
                }
                uint32_t changes[28] = {}, base = 0;
                for (int pivot = 0; pivot < detectors; ++pivot) {
                    if (__builtin_parity(solutions[pivot] & logical)) base |= 1u << pivot;
                    for (int equation = 0; equation < rank; ++equation)
                        if ((solutions[pivot] >> equation) & 1) changes[equation] |= 1u << pivot;
                }
                if (seen.insert(base).second) consider(base);
                for (int first = 0; first < rank; ++first) {
                    uint32_t changed = base ^ changes[first];
                    if (seen.insert(changed).second) consider(changed);
                    for (int second = first + 1; second < rank; ++second) {
                        uint32_t proposal = changed ^ changes[second];
                        if (seen.insert(proposal).second) consider(proposal);
                    }
                }
                if (Clock::now() + std::chrono::milliseconds(700) >= informed_deadline) break;
            }
        }
        std::vector<uint32_t> targets;
        std::unordered_set<uint32_t> unique_targets;
        for (auto &pool : pools) {
            std::vector<State> ordered;
            while (!pool.empty()) {
                ordered.push_back(pool.top());
                pool.pop();
            }
            std::sort(ordered.begin(), ordered.end());
            for (const auto &state : ordered)
                if (unique_targets.insert(state.mask).second) targets.push_back(state.mask);
        }
        std::vector<std::pair<uint32_t, uint64_t>> left{{0, 0}}, right{{0, 0}};
        std::vector<int> permutation(count);
        for (int tap = 0; tap < count; ++tap) permutation[tap] = tap;
        std::shuffle(permutation.begin(), permutation.end(), random);
        for (int width = 1; width <= (budget + 1) / 2; ++width) {
            uint64_t mask = (1ull << width) - 1;
            while (mask < (1ull << count)) {
                uint32_t parity = 0;
                uint64_t actual = 0;
                for (uint64_t remaining = mask; remaining; remaining &= remaining - 1) {
                    int tap = permutation[__builtin_ctzll(remaining)];
                    parity ^= taps[tap];
                    actual |= 1ull << tap;
                }
                right.push_back({parity, actual});
                if (width <= budget / 2) left.push_back({parity, actual});
                uint64_t lowest = mask & -mask, next = mask + lowest;
                mask = (((next ^ mask) >> 2) / lowest) | next;
            }
        }
        std::unordered_multimap<uint32_t, uint64_t> lookup;
        lookup.reserve(left.size() * 2);
        for (const auto &entry : left) lookup.emplace(entry.first, entry.second);
        std::vector<int> representations(targets.size(), 0);
        std::unordered_set<uint64_t> seen_seeds;
        std::vector<State> seeds;
        auto add_seed = [&](uint64_t left_mask, uint64_t right_mask, int target) {
            if (representations[target] >= 32 || (left_mask & right_mask)) return;
            uint64_t mask = left_mask | right_mask;
            if (!seen_seeds.insert(mask).second) return;
            ++representations[target];
            while (__builtin_popcountll(mask) < budget && !stopped) {
                State next{1, 0};
                for (int tap = 0; tap < count; ++tap) {
                    if ((mask >> tap) & 1) continue;
                    uint64_t proposal = mask | (1ull << tap);
                    double score = evaluate(proposal);
                    if (score < next.score) next = {score, proposal};
                }
                mask = next.mask;
            }
            if (__builtin_popcountll(mask) == budget) seeds.push_back({evaluate(mask), mask});
        };
        if (right.size() > 2 * left.size()) {
            std::vector<uint64_t> joined;
            joined.reserve(left.size() * targets.size());
            for (size_t target = 0; target < targets.size(); ++target)
                for (size_t index = 0; index < left.size(); ++index)
                    joined.push_back((static_cast<uint64_t>(targets[target] ^ left[index].first) << 32) |
                                     (static_cast<uint64_t>(target) << 16) | index);
            std::vector<uint64_t> buffer(joined.size());
            std::vector<uint32_t> counts(65536), offsets(65536);
            for (int shift : {32, 48}) {
                std::fill(counts.begin(), counts.end(), 0);
                for (uint64_t entry : joined) ++counts[(entry >> shift) & 65535];
                uint32_t offset = 0;
                for (int bucket = 0; bucket < 65536; ++bucket) {
                    offsets[bucket] = offset;
                    offset += counts[bucket];
                }
                for (uint64_t entry : joined) buffer[offsets[(entry >> shift) & 65535]++] = entry;
                joined.swap(buffer);
            }
            for (size_t index = 0; index < right.size() && !stopped && best.score > 1e-14; ++index) {
                const auto &entry = right[index];
                auto match = std::lower_bound(joined.begin(), joined.end(), static_cast<uint64_t>(entry.first) << 32,
                                              [](uint64_t first, uint64_t second) { return (first >> 32) < (second >> 32); });
                int checked = 0;
                for (; match != joined.end() && (*match >> 32) == entry.first && checked < 4096; ++match, ++checked)
                    add_seed(left[*match & 65535].second, entry.second, (*match >> 16) & 65535);
                if ((index & 1023) == 1023 && Clock::now() >= informed_deadline) break;
            }
        } else {
            for (size_t index = 0; index < right.size() && !stopped && best.score > 1e-14; ++index) {
                const auto &entry = right[index];
                for (size_t target = 0; target < targets.size(); ++target) {
                    if (representations[target] >= 32) continue;
                    auto matches = lookup.equal_range(targets[target] ^ entry.first);
                    int checked = 0;
                    for (auto match = matches.first; match != matches.second && checked < 128; ++match, ++checked)
                        add_seed(match->second, entry.second, target);
                }
                if ((index & 1023) == 1023 && Clock::now() >= informed_deadline) break;
            }
        }
        std::sort(seeds.begin(), seeds.end());
        if (seeds.size() > 512) seeds.resize(512);
        std::cerr << "informed_targets=" << targets.size() << " seeds=" << seeds.size() << " ";
        return seeds;
    }

    State descend(State state, bool optimistic = false) {
        for (int iteration = 0; iteration < 30 && !stopped; ++iteration) {
            State next = state;
            for (uint64_t remaining = state.mask; remaining; remaining &= remaining - 1) {
                int removed = __builtin_ctzll(remaining);
                uint64_t base = state.mask ^ (1ull << removed);
                for (int added = 0; added < count; ++added) {
                    if ((state.mask >> added) & 1) continue;
                    uint64_t proposal = base | (1ull << added);
                    double score = evaluate(proposal, optimistic);
                    if (score < next.score - 1e-13) next = {score, proposal};
                    if (stopped) break;
                }
                if (stopped) break;
            }
            if (next.mask == state.mask) break;
            state = next;
        }
        return state;
    }

    uint64_t perturb(uint64_t mask, int strength) {
        uint64_t original = mask;
        for (int step = 0; step < strength; ++step) {
            int rank = random() % __builtin_popcountll(mask);
            uint64_t remaining = mask;
            while (rank--) remaining &= remaining - 1;
            mask ^= remaining & -remaining;
        }
        while (__builtin_popcountll(mask) < budget) {
            int tap = random() % count;
            if (!((original >> tap) & 1)) mask |= 1ull << tap;
        }
        return mask;
    }

    State double_descent(State state) {
        std::vector<int> selected, unused;
        for (int tap = 0; tap < count; ++tap)
            (((state.mask >> tap) & 1) ? selected : unused).push_back(tap);
        State next = state;
        for (int first = 0; first < budget && !stopped; ++first) {
            for (int second = first + 1; second < budget && !stopped; ++second) {
                uint64_t base = state.mask ^ (1ull << selected[first]) ^ (1ull << selected[second]);
                for (size_t left = 0; left < unused.size() && !stopped; ++left) {
                    for (size_t right = left + 1; right < unused.size(); ++right) {
                        uint64_t proposal = base | (1ull << unused[left]) | (1ull << unused[right]);
                        double score = evaluate(proposal);
                        if (score < next.score - 1e-13) next = {score, proposal};
                        if (stopped) break;
                    }
                }
            }
        }
        return descend(next);
    }

    void run() {
        auto beam = beam_search();
        if (!std::getenv("DECODER_NO_INFORMED") && best.score > 1e-14) {
            auto informed = informed_seeds();
            beam.insert(beam.end(), informed.begin(), informed.end());
        }
        if (best.score > 1e-14) {
            auto seeds = spectral_seeds();
            beam.insert(beam.end(), seeds.begin(), seeds.end());
        }
        std::sort(beam.begin(), beam.end());
        std::vector<State> elites;
        std::unordered_set<uint64_t> minima;
        std::unordered_set<uint64_t> doubled;
        for (size_t index = 0; index < beam.size() && index < 32 && !stopped && best.score > 1e-14; ++index) {
            State state = descend(beam[index]);
            if (minima.insert(state.mask).second) elites.push_back(state);
        }
        std::sort(elites.begin(), elites.end());
        for (int iteration = 0; !stopped && best.score > 1e-14; ++iteration) {
            if (elites.empty()) break;
            State state;
            int double_index = -1;
            if (iteration % 10 == 0)
                for (size_t index = 0; index < std::min<size_t>(24, elites.size()); ++index)
                    if (!doubled.count(elites[index].mask)) {
                        double_index = index;
                        break;
                    }
            if (iteration % 6 == 5 && !optimistic_archive.empty()) {
                auto pool = optimistic_archive;
                std::vector<State> optimistic_states;
                while (!pool.empty()) {
                    optimistic_states.push_back(pool.top());
                    pool.pop();
                }
                std::sort(optimistic_states.begin(), optimistic_states.end());
                size_t index = random() % std::min<size_t>(24, optimistic_states.size());
                uint64_t proposal = perturb(optimistic_states[index].mask, 2 + random() % (budget - 1));
                state = descend({evaluate(proposal, true), proposal}, true);
                state.score = evaluate(state.mask);
            } else if (double_index >= 0) {
                doubled.insert(elites[double_index].mask);
                state = double_descent(elites[double_index]);
            } else {
                size_t index = random() % std::min<size_t>(32, elites.size());
                int strength = 2 + (random() % (budget - 1));
                uint64_t proposal = perturb(elites[index].mask, strength);
                state = descend({evaluate(proposal), proposal});
            }
            if (minima.insert(state.mask).second) elites.push_back(state);
            std::sort(elites.begin(), elites.end());
            if (elites.size() > 96) elites.resize(96);
            if (Clock::now() >= deadline) stopped = true;
        }
        if (archive.empty()) {
            uint64_t fallback = (1ull << budget) - 1;
            evaluate(fallback);
        }
        std::vector<State> results;
        std::unordered_set<uint64_t> result_masks;
        while (!archive.empty()) {
            results.push_back(archive.top());
            result_masks.insert(archive.top().mask);
            archive.pop();
        }
        while (!optimistic_archive.empty()) {
            if (result_masks.insert(optimistic_archive.top().mask).second)
                results.push_back(optimistic_archive.top());
            optimistic_archive.pop();
        }
        std::sort(results.begin(), results.end());
        std::cout << "[";
        bool first = true;
        for (const auto &state : results) {
            Values difference[128];
            int table[128];
            int size = distribution(state.mask, difference);
            double score = fit(difference, size, table, true);
            if (!first) std::cout << ",";
            first = false;
            std::cout << "{\"selected\":[";
            bool first_tap = true;
            for (int tap = 0; tap < count; ++tap) if ((state.mask >> tap) & 1) {
                if (!first_tap) std::cout << ",";
                first_tap = false;
                std::cout << tap;
            }
            std::cout << "],\"correction\":[";
            for (int syndrome = 0; syndrome < size; ++syndrome) {
                if (syndrome) std::cout << ",";
                std::cout << table[syndrome];
            }
            std::cout << "],\"score\":" << std::setprecision(15) << score << "}";
        }
        std::cout << "]\n";
        std::cerr << "evaluations=" << evaluations << " fourier_misses=" << misses
                  << " best=" << best.score << " seconds="
                  << std::chrono::duration<double>(Clock::now() - start).count() << "\n";
    }
};

struct TableProblem {
    int regimes, size;
    double base[8], weights[8];
    Values difference[128];
    std::vector<int> initial;
    double bound;
};

struct TableSearch {
    struct Variable {
        int syndrome;
        double cost, impact;
        Values delta;
    };
    double best_score = 1;
    int best_index = 0;
    std::vector<int> best_table, table;
    std::vector<Variable> variables;
    std::vector<Values> suffix;
    double risks[8], lower;
    int regimes, candidate;
    uint64_t nodes = 0;
    Clock::time_point deadline;
    bool stopped = false;
    const TableProblem *problem;

    void visit(int position, double regret) {
        if ((++nodes & 4095) == 0 && Clock::now() >= deadline) stopped = true;
        if (stopped || lower + regret >= best_score - 1e-13) return;
        double maximum = -1;
        for (int regime = 0; regime < regimes; ++regime) {
            if (risks[regime] + suffix[position].value[regime] >= best_score - 1e-13) return;
            maximum = std::max(maximum, risks[regime]);
        }
        if (maximum < best_score - 1e-13) {
            best_score = maximum;
            best_index = candidate;
            best_table = table;
        }
        if (position == static_cast<int>(variables.size())) return;
        const auto &variable = variables[position];
        bool flip_first = table[variable.syndrome] != problem->initial[variable.syndrome];
        for (int branch = 0; branch < 2; ++branch) {
            bool flip = (branch == 0) == flip_first;
            if (flip) {
                if (lower + regret + variable.cost >= best_score - 1e-13) continue;
                table[variable.syndrome] ^= 1;
                for (int regime = 0; regime < regimes; ++regime) risks[regime] += variable.delta.value[regime];
                visit(position + 1, regret + variable.cost);
                for (int regime = 0; regime < regimes; ++regime) risks[regime] -= variable.delta.value[regime];
                table[variable.syndrome] ^= 1;
            } else {
                visit(position + 1, regret);
            }
            if (stopped) return;
        }
    }

    void solve(const TableProblem &input, int index, double seconds) {
        problem = &input;
        regimes = input.regimes;
        candidate = index;
        table.assign(input.size, 0);
        variables.clear();
        for (int regime = 0; regime < regimes; ++regime) risks[regime] = input.base[regime];
        lower = 0;
        for (int regime = 0; regime < regimes; ++regime) lower += input.weights[regime] * input.base[regime];
        for (int syndrome = 0; syndrome < input.size; ++syndrome) {
            double weighted = 0;
            double maximum_difference = -1;
            for (int regime = 0; regime < regimes; ++regime)
                weighted += input.weights[regime] * input.difference[syndrome].value[regime];
            for (int regime = 0; regime < regimes; ++regime)
                maximum_difference = std::max(maximum_difference, input.difference[syndrome].value[regime]);
            table[syndrome] = weighted < 0 || maximum_difference <= 0;
            if (table[syndrome]) {
                lower += weighted;
                for (int regime = 0; regime < regimes; ++regime)
                    risks[regime] += input.difference[syndrome].value[regime];
            }
            Variable variable{};
            variable.syndrome = syndrome;
            variable.cost = std::abs(weighted);
            variable.impact = 0;
            bool positive = false, negative = false;
            for (int regime = 0; regime < regimes; ++regime) {
                double delta = (1 - 2 * table[syndrome]) * input.difference[syndrome].value[regime];
                variable.delta.value[regime] = delta;
                variable.impact = std::max(variable.impact, std::abs(delta));
                positive |= delta > 1e-15;
                negative |= delta < -1e-15;
            }
            if (positive && negative) variables.push_back(variable);
        }
        variables.erase(std::remove_if(variables.begin(), variables.end(), [&](const Variable &variable) {
            return lower + variable.cost >= best_score - 1e-13;
        }), variables.end());
        std::sort(variables.begin(), variables.end(), [](const Variable &first, const Variable &second) {
            return first.impact > second.impact;
        });
        suffix.assign(variables.size() + 1, Values{});
        for (int position = static_cast<int>(variables.size()) - 1; position >= 0; --position)
            for (int regime = 0; regime < regimes; ++regime)
                suffix[position].value[regime] = suffix[position + 1].value[regime] +
                    std::min(0.0, variables[position].delta.value[regime]);
        stopped = false;
        deadline = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
        visit(0, 0);
    }

    void run(double seconds) {
        auto end = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
        int count;
        std::cin >> count;
        std::vector<TableProblem> problems(count);
        for (int index = 0; index < count; ++index) {
            auto &input = problems[index];
            std::cin >> input.regimes >> input.size;
            for (int regime = 0; regime < input.regimes; ++regime) std::cin >> input.base[regime];
            for (int syndrome = 0; syndrome < input.size; ++syndrome)
                for (int regime = 0; regime < input.regimes; ++regime)
                    std::cin >> input.difference[syndrome].value[regime];
            for (int regime = 0; regime < input.regimes; ++regime) std::cin >> input.weights[regime];
            input.initial.resize(input.size);
            for (auto &bit : input.initial) std::cin >> bit;
            double score = -1;
            for (int regime = 0; regime < input.regimes; ++regime) {
                double risk = input.base[regime];
                for (int syndrome = 0; syndrome < input.size; ++syndrome)
                    risk += input.initial[syndrome] * input.difference[syndrome].value[regime];
                score = std::max(score, risk);
            }
            if (score < best_score) {
                best_score = score;
                best_index = index;
                best_table = input.initial;
            }
        }
        for (int index = 0; index < count; ++index) {
            double remaining = std::chrono::duration<double>(end - Clock::now()).count();
            if (remaining < 0.02) break;
            solve(problems[index], index, std::min(0.8, remaining));
        }
        std::cout << "{\"candidate\":" << best_index << ",\"score\":" << std::setprecision(15)
                  << best_score << ",\"correction\":[";
        for (size_t syndrome = 0; syndrome < best_table.size(); ++syndrome) {
            if (syndrome) std::cout << ",";
            std::cout << best_table[syndrome];
        }
        std::cout << "]}\n";
        std::cerr << "table_nodes=" << nodes << " polished=" << best_score << "\n";
    }
};

int main(int argc, char **argv) {
    if (argc > 1 && std::string(argv[1]) == "tables") {
        TableSearch search;
        search.run(argc > 2 ? std::atof(argv[2]) : 3.0);
        return 0;
    }
    double seconds = argc > 1 ? std::atof(argv[1]) : 34;
    Optimizer optimizer(seconds);
    optimizer.run();
    return 0;
}
