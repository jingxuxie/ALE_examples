#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>
#include <cstdlib>

using std::vector;
using Word = uint64_t;

struct Candidates {
    vector<uint64_t> keys;
    int count = 0;
    std::array<double, 16> masses{};
    std::array<float, 16> minima;
    Candidates() : keys(16384, 0) {minima.fill(1e30f);}
    void add(uint64_t key, int label, float score) {
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
    vector<uint8_t> mc_base;
    vector<vector<int>> mc_flips;
    vector<int> mc_labels;
    float mc_best = 1e30f;
    float* mc_statistics = nullptr;
    int sweeps = std::getenv("SWEEPS") ? std::atoi(std::getenv("SWEEPS")) : 300;
    int mc_size = std::getenv("MCSIZE") ? std::atoi(std::getenv("MCSIZE")) : 160;
    float mc_gap = std::getenv("MCGAP") ? std::atof(std::getenv("MCGAP")) : 3;
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
        vector<vector<int>> flips;
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
        auto insert = [&](uint64_t hash, int label, float score) {
            candidates.add(hash, label, score);
        };
        insert(base_hash, base_logical, base_score);
        vector<float> delta(variables);
        for (int var = 0; var < variables; var++) delta[var] = base[var] ? -prior[var] : prior[var];
        vector<int> fliplabels;
        vector<uint64_t> fliphashes;
        for (int var : freevars) {
            vector<int> flip = {var};
            for (int index = 0; index < rank; index++) if ((rows[index][var / 64] >> (var % 64)) & 1) flip.push_back(pivots[index]);
            float score = 0;
            int label = 0;
            uint64_t hash = 0;
            for (int changed : flip) {score += delta[changed]; label ^= logical[changed]; hash ^= hashes[changed];}
            insert(base_hash ^ hash, base_logical ^ label, base_score + score);
            flips.push_back(std::move(flip));
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
                insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score);
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
                        insert(base_hash ^ fliphashes[left] ^ fliphashes[right] ^ fliphashes[last], base_logical ^ fliplabels[left] ^ fliplabels[right] ^ fliplabels[last], triple_score);
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
                insert(base_hash ^ fliphashes[index], base_logical ^ fliplabels[index], base_score + score);
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
                    insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score);
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
                            insert(base_hash ^ fliphashes[left] ^ fliphashes[right] ^ fliphashes[last], base_logical ^ fliplabels[left] ^ fliplabels[right] ^ fliplabels[last], triple_score);
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
        for (int index : {improved_first, improved_second, improved_third}) if (index >= 0) for (int var : flips[index]) base[var] ^= 1;
        save_mc(base, flips, fliplabels, improved_score);
    }
    void save_mc(const vector<uint8_t>& base, const vector<vector<int>>& flips, const vector<int>& labels, float score) {
        if (score >= mc_best - 0.0001f) return;
        mc_best = score;
        mc_base = base;
        vector<int> indexes(flips.size());
        vector<float> costs(flips.size());
        std::iota(indexes.begin(), indexes.end(), 0);
        for (int index = 0; index < int(flips.size()); index++) for (int var : flips[index]) costs[index] += base[var] ? -prior[var] : prior[var];
        std::sort(indexes.begin(), indexes.end(), [&](int left, int right) {return costs[left] < costs[right];});
        mc_flips.clear(); mc_labels.clear();
        std::array<int,16> counts{};
        for (int index : indexes) {
            if (int(mc_flips.size()) < mc_size || (labels[index] && counts[labels[index]] < 4)) {
                mc_flips.push_back(flips[index]);
                mc_labels.push_back(labels[index]);
                counts[labels[index]]++;
            }
        }
    }
    std::array<double,16> sample_mc(const uint8_t* syndrome) {
        std::array<double,16> histogram{};
        if (mc_base.empty()) return histogram;
        uint64_t random = 7387837;
        for (int check = 0; check < detectors; check++) random = (random ^ syndrome[check]) * 1099511628211ULL;
        auto draw = [&]() {random ^= random << 13; random ^= random >> 7; random ^= random << 17; return random;};
        const int replicas = 8;
        std::array<float,replicas> beta{1,0.90f,0.80f,0.70f,0.60f,0.50f,0.40f,0.30f};
        vector<vector<uint8_t>> states(replicas, mc_base);
        vector<float> energies(replicas, mc_best);
        vector<int> labels(replicas, 0);
        int base_label = 0;
        for (int var = 0; var < variables; var++) if (mc_base[var]) base_label ^= logical[var];
        std::fill(labels.begin(), labels.end(), base_label);
        for (int sweep = 0; sweep < sweeps; sweep++) {
            for (int replica = 0; replica < replicas; replica++) {
                auto& state = states[replica];
                for (int update = 0; update < int(mc_flips.size()); update++) {
                    int index = draw() % mc_flips.size();
                    float delta = 0;
                    for (int var : mc_flips[index]) delta += state[var] ? -prior[var] : prior[var];
                    if (delta <= 0 || float(draw() & 0xFFFFFF) < 16777216.0f * std::exp(-beta[replica] * delta)) {
                        for (int var : mc_flips[index]) state[var] ^= 1;
                        energies[replica] += delta;
                        labels[replica] ^= mc_labels[index];
                    }
                    if (replica == 0 && sweep >= sweeps / 3) histogram[labels[0]] += 1;
                }
            }
            for (int replica = sweep % 2; replica + 1 < replicas; replica += 2) {
                float difference = (beta[replica] - beta[replica+1]) * (energies[replica] - energies[replica+1]);
                if (difference >= 0 || float(draw() & 0xFFFFFF) < 16777216.0f * std::exp(difference)) {
                    std::swap(states[replica], states[replica+1]);
                    std::swap(energies[replica], energies[replica+1]);
                    std::swap(labels[replica], labels[replica+1]);
                }
            }
        }
        return histogram;
    }
    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble) {
        mc_best = 1e30f;
        mc_base.clear();
        vector<float> posterior(variables);
        vector<uint8_t> hard(variables);
        Candidates candidates;
        for (int trial = 0; trial < ensemble; trial++) {
            bool valid = belief(syndrome, posterior, hard, iterations, trial);
            if (valid && trial == 0 && !statistics) {
                int label = 0;
                for (int var = 0; var < variables; var++) if (hard[var]) label ^= logical[var];
                return label;
            }
            osd(syndrome, posterior, hard, order, candidates);
            if (statistics) {
                for (int label = 0; label < 16; label++) {
                    statistics[trial * 33 + label] = candidates.masses[label] > 0 ? std::log(candidates.masses[label]) : -1e30;
                    statistics[trial * 33 + 16 + label] = -candidates.minima[label];
                }
                statistics[trial * 33 + 32] = valid;
            }
        }
        int chosen = std::max_element(candidates.masses.begin(), candidates.masses.end()) - candidates.masses.begin();
        double runner_up = 0;
        for (int label = 0; label < 16; label++) if (label != chosen) runner_up = std::max(runner_up, candidates.masses[label]);
        double gap = std::log(candidates.masses[chosen] / std::max(runner_up, 1e-300));
        if (gap < mc_gap) {
            auto histogram = sample_mc(syndrome);
            if (mc_statistics) for (int label = 0; label < 16; label++) mc_statistics[label] = histogram[label];
            chosen = std::max_element(histogram.begin(), histogram.end()) - histogram.begin();
        } else if (mc_statistics) mc_statistics[chosen] = 1;
        return chosen;
    }
};

extern "C" {
void* create(int detectors, int variables, const uint8_t* matrix, const uint8_t* logical, const double* probabilities) {
    return new Decoder(detectors, variables, matrix, logical, probabilities);
}
void destroy(void* decoder) {delete static_cast<Decoder*>(decoder);}
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
void run_mc(void* handle, int shots, const uint8_t* syndromes, float* output, float* mc, int iterations, int order, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        decoder.statistics = output + shot * ensemble * 33;
        decoder.mc_statistics = mc + shot * 16;
        decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
    }
    decoder.statistics = nullptr;
    decoder.mc_statistics = nullptr;
}
}
