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

struct Decoder {
    int detectors, variables, words;
    vector<vector<int>> checks;
    vector<int> edge_var, logical;
    vector<float> prior;
    vector<vector<Word>> original;
    vector<float> table;
    int schedule=0;
    float perturb=0.3f, damping=0.3f;
    float gap_stop=0;
    int min_trials=2;
    float alpha=1, channel_scale=1, minsum=0;
    int guide=0;
    vector<int> guidevars;
    vector<uint8_t> guidebase;
    float rerank=0;
    int higher_order=0;
    vector<vector<int>> neighbors;
    vector<vector<uint8_t>> solutions;
    std::array<float,16> solution_costs;
    Decoder(int nd, int nv, const uint8_t* matrix, const uint8_t* obs, const double* probabilities)
        : detectors(nd), variables(nv), words((nv + 63) / 64), checks(nd), logical(nv), prior(nv), original(nd, vector<Word>(words)), table(32769) {
        for (int index = 0; index <= 32768; index++) {
            double value = std::max(0.00001, index / 2048.0);
            table[index] = -std::log(std::tanh(value / 2));
        }
        if(std::getenv("SCHEDULE")) schedule=std::atoi(std::getenv("SCHEDULE"));
        if(std::getenv("PERTURB")) perturb=std::atof(std::getenv("PERTURB"));
        if(std::getenv("DAMPING")) damping=std::atof(std::getenv("DAMPING"));
        if(std::getenv("GAP")) gap_stop=std::atof(std::getenv("GAP"));
        if(std::getenv("MIN_TRIALS")) min_trials=std::atoi(std::getenv("MIN_TRIALS"));
        if(std::getenv("ALPHA")) alpha=std::atof(std::getenv("ALPHA"));
        if(std::getenv("CHANNEL")) channel_scale=std::atof(std::getenv("CHANNEL"));
        if(std::getenv("MS")) minsum=std::atof(std::getenv("MS"));
        if(std::getenv("GUIDE")) guide=std::atoi(std::getenv("GUIDE"));
        if(std::getenv("RERANK")) rerank=std::atof(std::getenv("RERANK"));
        if(std::getenv("HORDER")) higher_order=std::atoi(std::getenv("HORDER"));
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
        neighbors.resize(variables);
        for(const auto& check:checks) for(int left:check) for(int right:check) if(left!=right) neighbors[edge_var[left]].push_back(edge_var[right]);
        for(auto& adjacent:neighbors) {std::sort(adjacent.begin(),adjacent.end());adjacent.erase(std::unique(adjacent.begin(),adjacent.end()),adjacent.end());}
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
        for(int var=0;var<variables;var++) channel[var]*=channel_scale;
        posterior=channel;
        if (trial) {
            uint64_t seed = 1234567 + trial * 8191;
            for (int check = 0; check < detectors; check++) seed = (seed ^ syndrome[check]) * 1099511628211ULL;
            for (int var = 0; var < variables; var++) {
                seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
                channel[var] *= 1-perturb + 2*perturb * float(seed & 65535) / 65535;
            }
            posterior = channel;
        }
        vector<float> average(variables, 0);
        if(guide && trial && !guidevars.empty()) {
            int var=guidevars[(trial-1)%guidevars.size()];
            channel[var]=guidebase[var]?15:-15;
            posterior=channel;
        }
        vector<int> check_order(detectors);
        std::iota(check_order.begin(),check_order.end(),0);
        uint64_t rng=937123+trial*8191;
        for(int check=0;check<detectors;check++) rng=(rng^syndrome[check])*1099511628211ULL;
        auto shuffle=[&]() {
            for(int index=detectors-1;index>0;index--) {
                rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;
                std::swap(check_order[index],check_order[rng%(index+1)]);
            }
        };
        if(schedule==1 && trial) shuffle();
        for (int iteration = 0; iteration < iterations; iteration++) {
            if(schedule==2 || (schedule==3 && trial)) shuffle();
            for (int check : check_order) {
                float total = 0;
                float minimum=1e30,second_minimum=1e30;
                int sign = syndrome[check];
                for (int edge : checks[check]) {
                    float value = std::clamp(posterior[edge_var[edge]] - messages[edge], -30.0f, 30.0f);
                    incoming[edge] = value;
                    float magnitude=std::abs(value);
                    if(magnitude<minimum) {second_minimum=minimum;minimum=magnitude;}
                    else if(magnitude<second_minimum) second_minimum=magnitude;
                    transformed[edge] = minsum>0?magnitude:phi(magnitude);
                    total += transformed[edge];
                    sign ^= value < 0;
                }
                for (int edge : checks[check]) {
                    float value = minsum>0?minsum*(transformed[edge]==minimum?second_minimum:minimum):std::min(30.0f, phi(std::max(0.0f, total - transformed[edge])));
                    if (sign ^ (incoming[edge] < 0)) value = -value;
                    float updated = value * (1-damping) + messages[edge] * damping;
                    posterior[edge_var[edge]] += (updated - messages[edge])/alpha;
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
             std::unordered_map<uint64_t, std::pair<int, float>>& candidates, float& best_cost) {
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
        auto insert = [&](uint64_t hash, int label, float score, const vector<int>* left=nullptr, const vector<int>* right=nullptr, const vector<int>* third=nullptr) {
            if(score<best_cost) best_cost=score;
            if(score<best_cost+16) candidates.emplace(hash, std::make_pair(label, score));
            if(score<solution_costs[label]-0.0001f) {
                solution_costs[label]=score;solutions[label]=base;
                if(left) for(int var:*left) solutions[label][var]^=1;
                if(right) for(int var:*right) solutions[label][var]^=1;
                if(third) for(int var:*third) solutions[label][var]^=1;
            }
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
            insert(base_hash ^ hash, base_logical ^ label, base_score + score, &flip);
            flips.push_back(std::move(flip));
            costs.push_back(score);
            fliplabels.push_back(label);
            fliphashes.push_back(hash);
        }
        vector<int> ordervars(freevars.size());
        std::iota(ordervars.begin(), ordervars.end(), 0);
        int count = std::min(order, int(ordervars.size()));
        auto compare=[&](int left,int right){return costs[left]!=costs[right]?costs[left]<costs[right]:left<right;};
        std::partial_sort(ordervars.begin(), ordervars.begin()+count, ordervars.end(), compare);
        vector<uint8_t> changed(variables, 0);
        float improved_score = base_score;
        int improved_first = -1, improved_second = -1;
        int improved_third=-1;
        vector<int> free_index(variables,-1);
        for(int index=0;index<int(freevars.size());index++) free_index[freevars[index]]=index;
        auto adjacent_pairs=[&]() {
            for(int left=0;left<int(freevars.size());left++) {
                for(int var:flips[left]) changed[var]=1;
                for(int neighbor:neighbors[freevars[left]]) {
                    int right=free_index[neighbor];
                    if(right<=left) continue;
                    float score=base_score+costs[left]+costs[right];
                    for(int var:flips[right]) if(changed[var]) score-=2*delta[var];
                    insert(base_hash^fliphashes[left]^fliphashes[right],base_logical^fliplabels[left]^fliplabels[right],score,&flips[left],&flips[right]);
                    if(score<improved_score-0.0001f) {improved_score=score;improved_first=left;improved_second=right;improved_third=-1;}
                }
                for(int var:flips[left]) changed[var]=0;
            }
        };
        auto triples=[&]() {
            int limit=std::min(higher_order,count);
            for(int first=0;first<limit;first++) {
                int left=ordervars[first];
                for(int var:flips[left]) changed[var]^=1;
                for(int second=first+1;second<limit;second++) {
                    int middle=ordervars[second];
                    float partial=base_score+costs[left]+costs[middle];
                    for(int var:flips[middle]) if(changed[var]) partial-=2*delta[var];
                    for(int var:flips[middle]) changed[var]^=1;
                    for(int third=second+1;third<limit;third++) {
                        int right=ordervars[third];
                        float score=partial+costs[right];
                        for(int var:flips[right]) if(changed[var]) score-=2*delta[var];
                        insert(base_hash^fliphashes[left]^fliphashes[middle]^fliphashes[right],base_logical^fliplabels[left]^fliplabels[middle]^fliplabels[right],score,&flips[left],&flips[middle],&flips[right]);
                        if(score<improved_score-0.0001f) {
                            improved_score=score;improved_first=left;improved_second=middle;improved_third=right;
                        }
                    }
                    for(int var:flips[middle]) changed[var]^=1;
                }
                for(int var:flips[left]) changed[var]^=1;
            }
        };
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
                }
            }
            for (int var : flips[left]) changed[var] = 0;
        }
        if(improved_first<0) adjacent_pairs();
        if(improved_first<0) triples();
        for (int center = 0; center < 8 && improved_first >= 0; center++) {
            for (int index : {improved_first, improved_second,improved_third}) if (index >= 0) {
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
            std::partial_sort(ordervars.begin(), ordervars.begin()+count, ordervars.end(), compare);
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
                    }
                }
                for (int var : flips[left]) changed[var] = 0;
            }
            if(improved_first<0) adjacent_pairs();
            if(improved_first<0) triples();
        }
    }
    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble, float* scores=nullptr) {
        vector<float> posterior(variables);
        vector<uint8_t> hard(variables);
        std::unordered_map<uint64_t, std::pair<int, float>> candidates;
        float best_cost=1e30;
        solutions.assign(16,vector<uint8_t>(variables,0));solution_costs.fill(1e30);
        int prev_label=-1,stable=0;
        vector<float> reference_posterior;
        uint64_t ranking_rng=2819281;
        for(int check=0;check<detectors;check++) ranking_rng=(ranking_rng^syndrome[check])*1099511628211ULL;
        for (int trial = 0; trial < ensemble; trial++) {
            bool valid=false;
            if(rerank>0 && trial>0) {
                posterior=reference_posterior;
                int label=std::min_element(solution_costs.begin(),solution_costs.end())-solution_costs.begin();
                hard=solutions[label];
                for(int var=0;var<variables;var++) {
                    ranking_rng^=ranking_rng<<13;ranking_rng^=ranking_rng>>7;ranking_rng^=ranking_rng<<17;
                    posterior[var]*=std::exp(rerank*(2.0f*float(ranking_rng&65535)/65535-1));
                }
            } else {
                valid = belief(syndrome, posterior, hard, iterations, trial);
                reference_posterior=posterior;
            }
            if (valid && trial == 0) {
                int label = 0;
                for (int var = 0; var < variables; var++) if (hard[var]) label ^= logical[var];
                if(scores) for(int index=0;index<80;index++) scores[index]=(index%16)==label?0:100;
                solutions[label]=hard;solution_costs[label]=0;
                for(int var=0;var<variables;var++) if(hard[var]) solution_costs[label]+=prior[var];
                return label;
            }
            osd(syndrome, posterior, hard, order, candidates,best_cost);
            if(guide && trial==0) {
                int selected=std::min_element(solution_costs.begin(),solution_costs.end())-solution_costs.begin();
                guidebase=solutions[selected];guidevars.clear();
                for(int var=0;var<variables;var++) if(guide==1 || guidebase[var]) guidevars.push_back(var);
                std::stable_sort(guidevars.begin(),guidevars.end(),[&](int left,int right) {return std::abs(posterior[left])<std::abs(posterior[right]);});
            }
            if(gap_stop>0) {
                std::array<double,16> totals{};
                for(auto& entry:candidates) totals[entry.second.first]+=std::exp(best_cost-entry.second.second);
                int label=std::max_element(totals.begin(),totals.end())-totals.begin();
                stable=label==prev_label?stable+1:0;
                prev_label=label;
                double second=0;
                for(int other=0;other<16;other++) if(other!=label) second=std::max(second,totals[other]);
                if(trial+1>=min_trials && stable>=1 && std::log(totals[label]/(second+1e-100))>gap_stop) break;
            }
        }
        float best = 1e30;
        for (auto& entry : candidates) best = std::min(best, entry.second.second);
        std::array<double, 16> masses{};
        for (auto& entry : candidates) masses[entry.second.first] += std::exp(best - entry.second.second);
        if(scores) {
            for(int beta_index=0;beta_index<5;beta_index++) {
                std::array<double,16> totals{};
                float beta=0.5f+0.25f*beta_index;
                for(auto& entry:candidates) totals[entry.second.first]+=std::exp(beta*(best-entry.second.second));
                for(int label=0;label<16;label++) scores[beta_index*16+label]=best-std::log(totals[label]+1e-100)/beta;
            }
        }
        return std::max_element(masses.begin(), masses.end()) - masses.begin();
    }
};

extern "C" {
void* create(int detectors, int variables, const uint8_t* matrix, const uint8_t* logical, const double* probabilities) {
    return new Decoder(detectors, variables, matrix, logical, probabilities);
}
void destroy(void* decoder) {delete static_cast<Decoder*>(decoder);}
void run_info(void* handle,int shots,const uint8_t* syndromes,uint8_t* output,float* scores,int iterations,int order,int ensemble) {
    auto& decoder=*static_cast<Decoder*>(handle);
    for(int shot=0;shot<shots;shot++) {
        int label=decoder.decode(syndromes+shot*decoder.detectors,iterations,order,ensemble,scores+shot*80);
        for(int bit=0;bit<4;bit++) output[shot*4+bit]=(label>>bit)&1;
    }
}
void run_states(void* handle,int shots,const uint8_t* syndromes,float* scores,uint8_t* states,float* costs,int iterations,int order,int ensemble) {
    auto& decoder=*static_cast<Decoder*>(handle);
    for(int shot=0;shot<shots;shot++) {
        decoder.decode(syndromes+shot*decoder.detectors,iterations,order,ensemble,scores+shot*80);
        for(int label=0;label<16;label++) {
            costs[shot*16+label]=decoder.solution_costs[label];
            std::copy(decoder.solutions[label].begin(),decoder.solutions[label].end(),states+(shot*16+label)*decoder.variables);
        }
    }
}
void run(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, int iterations, int order, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        int label = decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
        for (int bit = 0; bit < 4; bit++) output[shot * 4 + bit] = (label >> bit) & 1;
    }
}
}
