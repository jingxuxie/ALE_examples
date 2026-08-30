#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>

using std::vector;
using Word = uint64_t;

struct Decoder {
    int detectors, variables, words;
    bool force_list = false;
    std::array<int, 8> temperature_labels{};
    int diagnostic_fast = 0;
    double diagnostic_gap = -1;
    double diagnostic_candidates = 0;
    double diagnostic_best = 0;
    double diagnostic_margin = 0;
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
                int sign = syndrome[check];
                for (int edge : checks[check]) {
                    float value = std::clamp(posterior[edge_var[edge]] - messages[edge], -30.0f, 30.0f);
                    incoming[edge] = value;
                    transformed[edge] = phi(std::abs(value));
                    total += transformed[edge];
                    sign ^= value < 0;
                }
                for (int edge : checks[check]) {
                    float value = std::min(30.0f, phi(std::max(0.0f, total - transformed[edge])));
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
             std::unordered_map<uint64_t, std::pair<int, float>>& candidates) {
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
            candidates.emplace(hash, std::make_pair(label, score));
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
        int count = std::min(order, int(ordervars.size()));
        vector<uint8_t> changed(variables, 0);
        float improved_score = base_score;
        int improved_first = -1, improved_second = -1;
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
                }
            }
            for (int var : flips[left]) changed[var] = 0;
        }
        for (int center = 0; center < 4 && improved_first >= 0; center++) {
            for (int index : {improved_first, improved_second}) if (index >= 0) {
                for (int var : flips[index]) {base[var] ^= 1; delta[var] = -delta[var];}
                base_hash ^= fliphashes[index];
                base_logical ^= fliplabels[index];
            }
            base_score = improved_score;
            improved_first = improved_second = -1;
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
                    }
                }
                for (int var : flips[left]) changed[var] = 0;
            }
        }
    }
    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble) {
        diagnostic_fast = 0;
        diagnostic_gap = -1;
        diagnostic_candidates = 0;
        diagnostic_best = 0;
        diagnostic_margin = 0;
        vector<float> posterior(variables);
        vector<uint8_t> hard(variables);
        std::unordered_map<uint64_t, std::pair<int, float>> candidates;
        for (int trial = 0; trial < ensemble; trial++) {
            bool valid = belief(syndrome, posterior, hard, iterations, trial);
            if (valid && trial == 0 && !force_list) {
                diagnostic_fast = 1;
                diagnostic_margin = 1e30;
                for (int variable = 0; variable < variables; variable++) {
                    diagnostic_margin = std::min(diagnostic_margin, double(std::abs(posterior[variable])));
                    if (hard[variable]) diagnostic_best += prior[variable];
                }
                int label = 0;
                for (int var = 0; var < variables; var++) if (hard[var]) label ^= logical[var];
                temperature_labels.fill(label);
                return label;
            }
            osd(syndrome, posterior, hard, order, candidates);
        }
        float best = 1e30;
        for (auto& entry : candidates) best = std::min(best, entry.second.second);
        std::array<double, 16> masses{};
        for (auto& entry : candidates) masses[entry.second.first] += std::exp(best - entry.second.second);
        int chosen = std::max_element(masses.begin(), masses.end()) - masses.begin();
        const std::array<double, 8> temperatures{0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 10.0};
        for (int control = 0; control < 8; control++) {
            std::array<double, 16> values{};
            for (auto& entry : candidates) values[entry.second.first] += std::exp(temperatures[control] * (best - entry.second.second));
            temperature_labels[control] = std::max_element(values.begin(), values.end()) - values.begin();
        }
    
        double runner_up = 0;
        for (int label = 0; label < 16; label++) if (label != chosen) runner_up = std::max(runner_up, masses[label]);
        diagnostic_gap = std::min(100.0, std::log((masses[chosen] + 1e-300) / (runner_up + 1e-300)));
        diagnostic_candidates = candidates.size();
        diagnostic_best = best;
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

void run_diagnostics(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, double* diagnostics,
                     int iterations, int order, int ensemble, int force_list) {
    auto& decoder = *static_cast<Decoder*>(handle);
    decoder.force_list = force_list != 0;
    for (int shot = 0; shot < shots; shot++) {
        int label = decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
        for (int bit = 0; bit < 4; bit++) output[shot * 4 + bit] = (label >> bit) & 1;
        diagnostics[shot * 5] = decoder.diagnostic_fast;
        diagnostics[shot * 5 + 1] = decoder.diagnostic_gap;
        diagnostics[shot * 5 + 2] = decoder.diagnostic_candidates;
        diagnostics[shot * 5 + 3] = decoder.diagnostic_best;
        diagnostics[shot * 5 + 4] = decoder.diagnostic_margin;
    }
}
}

extern "C" void run_temperatures(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        decoder.decode(syndromes + shot * decoder.detectors, 40, 40, ensemble);
        for (int control = 0; control < 8; control++) output[shot * 8 + control] = decoder.temperature_labels[control];
    }
}
