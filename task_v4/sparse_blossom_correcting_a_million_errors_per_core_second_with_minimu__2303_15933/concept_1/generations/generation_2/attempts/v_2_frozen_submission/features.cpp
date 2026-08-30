#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>
#include <cstdlib>
#include <unordered_set>

using std::vector;
using Word = uint64_t;

struct Candidates {
    vector<uint64_t> keys;
    int count = 0;
    float best = 1e30f;
    std::array<double, 16> masses{};
    std::array<float, 16> minima;
    Candidates() : keys(16384, 0) {minima.fill(1e30f);}
    void add(uint64_t key, int label, float score) {
        if (score > best + 20) return;
        best = std::min(best, score);
        if (!key) key = 1;
        size_t slot = key & (keys.size() - 1);
        while (keys[slot] && keys[slot] != key) slot = (slot + 1) & (keys.size() - 1);
        if (keys[slot]) return;
        keys[slot] = key;
        masses[label] += std::exp(-double(score));
        minima[label] = std::min(minima[label], score);
        if (++count * 2 > int(keys.size())) {
            vector<uint64_t> larger(keys.size() * 2, 0);
            for (uint64_t value : keys) if (value) {
                size_t dest = value & (larger.size() - 1);
                while (larger[dest]) dest = (dest + 1) & (larger.size() - 1);
                larger[dest] = value;
            }
            keys.swap(larger);
        }
    }
};

struct Decoder {
    std::array<float,16> class_best;
    std::array<vector<uint8_t>,16> class_states;
    vector<int> kinds;
    vector<vector<int>> local_moves;
    float* features = nullptr;
    float cutoff = std::getenv("CUTOFF") ? std::atof(std::getenv("CUTOFF")) : 5.0f;
    int minimum_trials = std::getenv("MINTRIALS") ? std::atoi(std::getenv("MINTRIALS")) : 2;
    int triple = std::getenv("TRIPLE") ? std::atoi(std::getenv("TRIPLE")) : 0;
    float* statistics = nullptr;
    int sortmode = std::getenv("SORT") ? std::atoi(std::getenv("SORT")) : 0;
    float minsum = std::getenv("MINSUM") ? std::atof(std::getenv("MINSUM")) : 0;
    int detectors, variables, words;
    vector<vector<int>> checks;
    vector<int> edge_var, logical;
    vector<float> prior;
    vector<vector<Word>> original;
    vector<float> table;
    Decoder(int nd, int nv, const uint8_t* matrix, const uint8_t* obs, const double* probabilities)
        : detectors(nd), variables(nv), words((nv + 63) / 64), checks(nd), logical(nv), prior(nv), original(nd, vector<Word>(words)), table(32769) {
        for (int index = 0; index <= 32768; index++) {
            double value = std::max(0.00001, index / 2048.0);
            table[index] = -std::log(std::tanh(value / 2));
        }
        for (int var = 0; var < nv; var++) {
            prior[var] = std::log((1 - probabilities[var]) / probabilities[var]);
            for (int bit = 0; bit < 4; bit++) logical[var] |= int(obs[bit * nv + var]) << bit;
            for (int check = 0; check < nd; check++) if (matrix[check * nv + var]) {
                int edge = edge_var.size();
                edge_var.push_back(var);
                checks[check].push_back(edge);
                original[check][var / 64] |= Word(1) << (var % 64);
            }
        }
    }
    float phi(float value) const {
        if (value >= 16) return 0.0000002f;
        float position = std::max(value * 2048, 0.02f);
        int index = int(position);
        return table[index] + (position - index) * (table[index + 1] - table[index]);
    }
    bool belief(const uint8_t* syndrome, vector<float>& posterior, vector<uint8_t>& hard, int iterations, int trial) {
        vector<float> messages(edge_var.size(), 0), incoming(edge_var.size()), transformed(edge_var.size());
        posterior = prior;
        vector<float> channel = prior;
        if (trial) {
            uint64_t seed = 1234567 + trial * 8191;
            for (int check = 0; check < detectors; check++) seed = (seed ^ syndrome[check]) * 1099511628211ULL;
            for (int var = 0; var < variables; var++) {
                seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
                channel[var] *= 0.7f + 0.6f * float(seed & 65535) / 65535;
            }
            posterior = channel;
        }
        vector<float> average(variables, 0);
        for (int iteration = 0; iteration < iterations; iteration++) {
            for (int check = 0; check < detectors; check++) {
                float total = 0;
                float minimum = 1e30f, next = 1e30f;
                int minedge = -1;
                int sign = syndrome[check];
                for (int edge : checks[check]) {
                    float value = std::clamp(posterior[edge_var[edge]] - messages[edge], -30.0f, 30.0f);
                    incoming[edge] = value;
                    transformed[edge] = phi(std::abs(value));
                    total += transformed[edge];
                    if (std::abs(value) < minimum) {next = minimum; minimum = std::abs(value); minedge = edge;}
                    else next = std::min(next, std::abs(value));
                    sign ^= value < 0;
                }
                for (int edge : checks[check]) {
                    float value = std::min(30.0f, phi(std::max(0.0f, total - transformed[edge])));
                    if (minsum) value = minsum * (edge == minedge ? next : minimum);
                    if (sign ^ (incoming[edge] < 0)) value = -value;
                    float updated = value * 0.7f + messages[edge] * 0.3f;
                    posterior[edge_var[edge]] += updated - messages[edge];
                    messages[edge] = updated;
                }
            }
            for (int var = 0; var < variables; var++) {
                hard[var] = posterior[var] < 0;
                average[var] = 0.8f * average[var] + 0.2f * posterior[var];
            }
            bool valid = true;
            for (int check = 0; check < detectors; check++) {
                int parity = syndrome[check];
                for (int edge : checks[check]) parity ^= hard[edge_var[edge]];
                if (parity) { valid = false; break; }
            }
            if (valid) return true;
        }
        posterior = average;
        for (int var = 0; var < variables; var++) hard[var] = posterior[var] < 0;
        return false;
    }
    void osd(const uint8_t* syndrome, const vector<float>& posterior, const vector<uint8_t>& hard, int order,
             Candidates& candidates) {
        vector<int> sorted(variables);
        std::iota(sorted.begin(), sorted.end(), 0);
        std::stable_sort(sorted.begin(), sorted.end(), [&](int left, int right) {return std::abs(posterior[left]) < std::abs(posterior[right]);});
        auto rows = original;
        vector<uint8_t> rhs(syndrome, syndrome + detectors);
        for (int check = 0; check < detectors; check++) for (int edge : checks[check]) rhs[check] ^= hard[edge_var[edge]];
        vector<int> pivots, freevars;
        int rank = 0;
        for (int var : sorted) {
            int pivot = rank;
            Word mask = Word(1) << (var % 64);
            int block = var / 64;
            while (pivot < detectors && !(rows[pivot][block] & mask)) pivot++;
            if (pivot == detectors) {freevars.push_back(var); continue;}
            std::swap(rows[rank], rows[pivot]);
            std::swap(rhs[rank], rhs[pivot]);
            for (int check = 0; check < detectors; check++) if (check != rank && (rows[check][block] & mask)) {
                for (int word = 0; word < words; word++) rows[check][word] ^= rows[rank][word];
                rhs[check] ^= rhs[rank];
            }
            pivots.push_back(var);
            rank++;
        }
        vector<uint8_t> base = hard;
        for (int index = 0; index < rank; index++) base[pivots[index]] ^= rhs[index];
        vector<vector<int>> flips(freevars.size());
        vector<int> free_index(variables, -1);
        for (int index = 0; index < int(freevars.size()); index++) {
            free_index[freevars[index]] = index;
            flips[index].reserve(32);
            flips[index].push_back(freevars[index]);
        }
        for (int index = 0; index < rank; index++) {
            for (int word = 0; word < words; word++) {
                Word active = rows[index][word];
                while (active) {
                    int var = word * 64 + __builtin_ctzll(active);
                    if (free_index[var] >= 0) flips[free_index[var]].push_back(pivots[index]);
                    active &= active - 1;
                }
            }
        }
        vector<float> costs;
        float base_score = 0;
        int base_logical = 0;
        uint64_t base_hash = 0;
        vector<uint64_t> hashes(variables);
        for (int var = 0; var < variables; var++) {
            uint64_t hash = var + 0x9e3779b97f4a7c15ULL;
            hash = (hash ^ (hash >> 30)) * 0xbf58476d1ce4e5b9ULL;
            hash = (hash ^ (hash >> 27)) * 0x94d049bb133111ebULL;
            hashes[var] = hash ^ (hash >> 31);
            if (base[var]) {base_score += prior[var]; base_logical ^= logical[var]; base_hash ^= hashes[var];}
        }
        auto insert = [&](uint64_t hash, int label, float score, const vector<int>* first = nullptr, const vector<int>* second = nullptr, const vector<int>* third = nullptr) {
            candidates.add(hash, label, score);
            if (score < class_best[label] - 0.0001f) {
                class_best[label] = score;
                class_states[label] = base;
                for (auto move : {first, second, third}) if (move) for (int var : *move) class_states[label][var] ^= 1;
            }
        };
        insert(base_hash, base_logical, base_score);
        vector<float> delta(variables);
        for (int var = 0; var < variables; var++) delta[var] = base[var] ? -prior[var] : prior[var];
        vector<int> fliplabels;
        vector<uint64_t> fliphashes;
        for (const auto& flip : flips) {
            float score = 0;
            int label = 0;
            uint64_t hash = 0;
            for (int changed : flip) {score += delta[changed]; label ^= logical[changed]; hash ^= hashes[changed];}
            insert(base_hash ^ hash, base_logical ^ label, base_score + score, &flip);
            costs.push_back(score);
            fliplabels.push_back(label);
            fliphashes.push_back(hash);
        }
        vector<int> ordervars(freevars.size());
        std::iota(ordervars.begin(), ordervars.end(), 0);
        std::stable_sort(ordervars.begin(), ordervars.end(), [&](int left, int right) {return costs[left] < costs[right];});
        if (sortmode == 1) std::iota(ordervars.begin(), ordervars.end(), 0);
        if (sortmode == 2) {
            vector<int> mixed;
            for (int index = 0; index < order / 2 && index < int(ordervars.size()); index++) mixed.push_back(index);
            for (int index : ordervars) if (index >= order / 2) mixed.push_back(index);
            ordervars = mixed;
        }
        int count = std::min(order, int(ordervars.size()));
        vector<uint8_t> changed(variables, 0);
        float improved_score = base_score;
        int improved_first = -1, improved_second = -1, improved_third = -1;
        for (int index = 0; index < int(flips.size()); index++) {
            if (base_score + costs[index] < improved_score - 0.0001f) {
                improved_score = base_score + costs[index];
                improved_first = index;
            }
        }
        for (int first = 0; first < count; first++) {
            int left = ordervars[first];
            for (int var : flips[left]) changed[var] = 1;
            for (int second = first + 1; second < count; second++) {
                int right = ordervars[second];
                float score = base_score + costs[left] + costs[right];
                for (int var : flips[right]) if (changed[var]) score -= 2 * delta[var];
                insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score, &flips[left], &flips[right]);
                if (score < improved_score - 0.0001f) {
                    improved_score = score;
                    improved_first = left;
                    improved_second = right;
                    improved_third = -1;
                }
                if (second < triple) {
                    for (int var : flips[right]) changed[var] ^= 1;
                    for (int third = second + 1; third < std::min(triple, count); third++) {
                        int last = ordervars[third];
                        float triple_score = score + costs[last];
                        for (int var : flips[last]) if (changed[var]) triple_score -= 2 * delta[var];
                        insert(base_hash ^ fliphashes[left] ^ fliphashes[right] ^ fliphashes[last], base_logical ^ fliplabels[left] ^ fliplabels[right] ^ fliplabels[last], triple_score, &flips[left], &flips[right], &flips[last]);
                        if (triple_score < improved_score - 0.0001f) {
                            improved_score = triple_score;
                            improved_first = left;
                            improved_second = right;
                            improved_third = last;
                        }
                    }
                    for (int var : flips[right]) changed[var] ^= 1;
                }
            }
            for (int var : flips[left]) changed[var] = 0;
        }
        for (int center = 0; center < 4 && improved_first >= 0; center++) {
            for (int index : {improved_first, improved_second, improved_third}) if (index >= 0) {
                for (int var : flips[index]) {base[var] ^= 1; delta[var] = -delta[var];}
                base_hash ^= fliphashes[index];
                base_logical ^= fliplabels[index];
            }
            base_score = improved_score;
            improved_first = improved_second = improved_third = -1;
            for (int index = 0; index < int(flips.size()); index++) {
                float score = 0;
                for (int var : flips[index]) score += delta[var];
                costs[index] = score;
                insert(base_hash ^ fliphashes[index], base_logical ^ fliplabels[index], base_score + score, &flips[index]);
                if (base_score + score < improved_score - 0.0001f) {
                    improved_score = base_score + score;
                    improved_first = index;
                }
            }
            std::stable_sort(ordervars.begin(), ordervars.end(), [&](int left, int right) {return costs[left] < costs[right];});
            if (sortmode == 1) std::iota(ordervars.begin(), ordervars.end(), 0);
            if (sortmode == 2) {
                vector<int> mixed;
                for (int index = 0; index < order / 2 && index < int(ordervars.size()); index++) mixed.push_back(index);
                for (int index : ordervars) if (index >= order / 2) mixed.push_back(index);
                ordervars = mixed;
            }
            for (int first = 0; first < count; first++) {
                int left = ordervars[first];
                for (int var : flips[left]) changed[var] = 1;
                for (int second = first + 1; second < count; second++) {
                    int right = ordervars[second];
                    float score = base_score + costs[left] + costs[right];
                    for (int var : flips[right]) if (changed[var]) score -= 2 * delta[var];
                    insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score, &flips[left], &flips[right]);
                    if (score < improved_score - 0.0001f) {
                        improved_score = score;
                        improved_first = left;
                        improved_second = right;
                        improved_third = -1;
                    }
                    if (second < triple) {
                        for (int var : flips[right]) changed[var] ^= 1;
                        for (int third = second + 1; third < std::min(triple, count); third++) {
                            int last = ordervars[third];
                            float triple_score = score + costs[last];
                            for (int var : flips[last]) if (changed[var]) triple_score -= 2 * delta[var];
                            insert(base_hash ^ fliphashes[left] ^ fliphashes[right] ^ fliphashes[last], base_logical ^ fliplabels[left] ^ fliplabels[right] ^ fliplabels[last], triple_score, &flips[left], &flips[right], &flips[last]);
                            if (triple_score < improved_score - 0.0001f) {
                                improved_score = triple_score;
                                improved_first = left;
                                improved_second = right;
                                improved_third = last;
                            }
                        }
                        for (int var : flips[right]) changed[var] ^= 1;
                    }
                }
                for (int var : flips[left]) changed[var] = 0;
            }
        }
    }
    void build_local() {
        vector<uint64_t> column_hashes(variables, 0), variable_hashes(variables);
        auto hash = [](uint64_t value) {
            value += 0x9e3779b97f4a7c15ULL;
            value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
            value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
            return value ^ (value >> 31);
        };
        for (int var = 0; var < variables; var++) variable_hashes[var] = hash(var + 81917);
        for (int check = 0; check < detectors; check++) for (int edge : checks[check]) column_hashes[edge_var[edge]] ^= hash(check);
        std::unordered_map<uint64_t,int> column_map;
        for (int var = 0; var < variables; var++) column_map[column_hashes[var]] = var;
        std::unordered_map<uint64_t, vector<std::pair<int,int>>> pair_map;
        std::unordered_set<uint64_t> pairs_seen, moves_seen;
        auto add = [&](vector<int> move) {
            std::sort(move.begin(), move.end());
            vector<int> compact;
            for (int var : move) {
                if (!compact.empty() && compact.back() == var) compact.pop_back();
                else compact.push_back(var);
            }
            if (compact.empty()) return;
            uint64_t key = 0;
            int label = 0;
            for (int var : compact) {key ^= variable_hashes[var]; label ^= logical[var];}
            if (label || !moves_seen.insert(key).second) return;
            for (int check = 0; check < detectors; check++) {
                int parity = 0;
                for (int var : compact) parity ^= (original[check][var / 64] >> (var % 64)) & 1;
                if (parity) return;
            }
            local_moves.push_back(std::move(compact));
        };
        for (const auto& check : checks) for (int first = 0; first < int(check.size()); first++) for (int second = first + 1; second < int(check.size()); second++) {
            int left = edge_var[check[first]], right = edge_var[check[second]];
            if (left > right) std::swap(left, right);
            uint64_t pair_key = (uint64_t(left) << 32) | right;
            if (!pairs_seen.insert(pair_key).second) continue;
            uint64_t key = column_hashes[left] ^ column_hashes[right];
            auto found = column_map.find(key);
            if (found != column_map.end()) add({left, right, found->second});
            auto& partners = pair_map[key];
            for (const auto& partner : partners) add({left, right, partner.first, partner.second});
            partners.push_back({left, right});
        }
    }
    void score_features(const Candidates& candidates) {
        if (local_moves.empty()) build_local();
        for (int label = 0; label < 16; label++) {
            float* output = features + label * 12;
            output[0] = -class_best[label];
            if (class_states[label].empty() || candidates.masses[label] <= 0) continue;
            output[1] = std::log(candidates.masses[label]) + class_best[label];
            const auto& state = class_states[label];
            for (int var = 0; var < variables; var++) if (state[var]) output[4 + kinds[var]]++;
            for (const auto& move : local_moves) {
                float delta = 0;
                for (int var : move) delta += state[var] ? -prior[var] : prior[var];
                float entropy = std::max(-delta,0.0f) + std::log1p(std::exp(-std::abs(delta)));
                output[move.size() == 3 ? 2 : 3] += entropy;
            }
            auto improved = state;
            float score = class_best[label];
            for (int step = 0; step < 5; step++) {
                bool changed = false;
                for (const auto& move : local_moves) {
                    float delta = 0;
                    for (int var : move) delta += improved[var] ? -prior[var] : prior[var];
                    if (delta < -0.0001f) {
                        for (int var : move) improved[var] ^= 1;
                        score += delta; changed = true;
                    }
                }
                if (!changed) break;
            }
            output[11] = class_best[label] - score;
        }
    }
    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble) {
        class_best.fill(1e30f);
        for (auto& state : class_states) state.clear();
        vector<float> posterior(variables);
        vector<uint8_t> hard(variables);
        Candidates candidates;
        int previous = -1;
        for (int trial = 0; trial < ensemble; trial++) {
            bool valid = belief(syndrome, posterior, hard, iterations, trial);
            if (valid && trial == 0 && !statistics) {
                int label = 0;
                for (int var = 0; var < variables; var++) if (hard[var]) label ^= logical[var];
                return label;
            }
            osd(syndrome, posterior, hard, order, candidates);
            if (!statistics && cutoff > 0) {
                int chosen = std::max_element(candidates.masses.begin(), candidates.masses.end()) - candidates.masses.begin();
                double runner_up = 0;
                for (int label = 0; label < 16; label++) if (label != chosen) runner_up = std::max(runner_up, candidates.masses[label]);
                if (trial + 1 >= minimum_trials && chosen == previous && candidates.masses[chosen] > std::exp(cutoff) * runner_up) return chosen;
                previous = chosen;
            }
            if (statistics) {
                for (int label = 0; label < 16; label++) {
                    statistics[trial * 33 + label] = candidates.masses[label] > 0 ? std::log(candidates.masses[label]) : -1e30;
                    statistics[trial * 33 + 16 + label] = -candidates.minima[label];
                }
                statistics[trial * 33 + 32] = valid;
            }
        }
        if (features) score_features(candidates);
        return std::max_element(candidates.masses.begin(), candidates.masses.end()) - candidates.masses.begin();
    }
};

extern "C" {
void* create(int detectors, int variables, const uint8_t* matrix, const uint8_t* logical, const double* probabilities) {
    return new Decoder(detectors, variables, matrix, logical, probabilities);
}
void destroy(void* decoder) {delete static_cast<Decoder*>(decoder);}
void set_kinds(void* handle, const int* kinds) {
    auto& decoder = *static_cast<Decoder*>(handle);
    decoder.kinds.assign(kinds, kinds + decoder.variables);
}
void run_features(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, float* features, int iterations, int order, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        decoder.features = features + shot * 16 * 12;
        int label = decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
        for (int bit = 0; bit < 4; bit++) output[shot * 4 + bit] = (label >> bit) & 1;
    }
    decoder.features = nullptr;
}
void run(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, int iterations, int order, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        int label = decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
        for (int bit = 0; bit < 4; bit++) output[shot * 4 + bit] = (label >> bit) & 1;
    }
}
void run_stats(void* handle, int shots, const uint8_t* syndromes, float* output, int iterations, int order, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        decoder.statistics = output + shot * ensemble * 33;
        decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
    }
    decoder.statistics = nullptr;
}
}
