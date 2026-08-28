#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

using Bits = std::vector<uint64_t>;

struct Group {
    std::vector<int> original;
    std::array<double, 4> energy{};
    std::array<int, 4> representation{};
    std::vector<int> edges;
    int states;
};

struct Edge {
    int group;
    int check;
    int mask;
};

struct Decoder {
    int rows, columns, words, hwords;
    const uint8_t* matrix;
    std::vector<Group> groups;
    std::vector<Edge> edges;
    std::vector<std::vector<int>> checks;
    std::vector<Bits> hcols;
    std::vector<int> active;
    std::vector<double> weights;
    std::mt19937_64 random;
    Bits best;
    double bestcost;
    int improvements = 0;

    Decoder(int m, int n, int k, const uint8_t* h, const uint8_t* logical,
            const double* prior, bool grouped) : rows(m), columns(n), matrix(h), random(20260827) {
        weights.resize(n);
        for (int col = 0; col < n; ++col) weights[col] = std::log((1-prior[col])/prior[col]);
        std::vector<std::string> keys(n, std::string((m+k+7)/8, '\0'));
        std::unordered_map<std::string, int> lookup;
        for (int col = 0; col < n; ++col) {
            for (int row = 0; row < m; ++row) if (h[row*n+col]) keys[col][row/8] ^= 1<<(row%8);
            for (int row = 0; row < k; ++row) if (logical[row*n+col]) keys[col][(m+row)/8] ^= 1<<((m+row)%8);
            lookup[keys[col]] = col;
        }
        std::vector<bool> used(n, false);
        if (grouped) {
            for (int first = 0; first < n; ++first) {
                if (used[first]) continue;
                for (int second = first+1; second < n; ++second) {
                    if (used[second]) continue;
                    std::string key = keys[first];
                    for (size_t byte = 0; byte < key.size(); ++byte) key[byte] ^= keys[second][byte];
                    auto found = lookup.find(key);
                    if (found == lookup.end()) continue;
                    int third = found->second;
                    if (third == first || third == second || used[third]) continue;
                    std::array<int, 3> triple{first,second,third};
                    std::sort(triple.begin(), triple.end(), [&](int left, int right) {
                        int leftweight = 0, rightweight = 0;
                        for (int row = 0; row < m; ++row) {
                            leftweight += h[row*n+left]; rightweight += h[row*n+right];
                        }
                        return leftweight < rightweight || (leftweight == rightweight && left < right);
                    });
                    Group group;
                    group.original = {triple[0],triple[1],triple[2]};
                    group.states = 4;
                    groups.push_back(group);
                    used[first] = used[second] = used[third] = true;
                    break;
                }
            }
        }
        for (int col = 0; col < n; ++col) if (!used[col]) {
            Group group;
            group.original = {col}; group.states = 2;
            groups.push_back(group);
        }
        words = (2*groups.size()+63)/64;
        hwords = (m+63)/64;
        checks.resize(m);
        hcols.resize(2*groups.size(), Bits(hwords, 0));
        for (int index = 0; index < int(groups.size()); ++index) {
            Group& group = groups[index];
            std::array<double,4> mass{};
            std::array<double,4> mincost;
            mincost.fill(1e100);
            for (int rep = 0; rep < (1<<group.original.size()); ++rep) {
                int state = group.states == 2 ? rep : ((rep&1)^((rep>>2)&1)) | ((((rep>>1)&1)^((rep>>2)&1))<<1);
                double probability = 1, cost = 0;
                for (int part = 0; part < int(group.original.size()); ++part) {
                    int col = group.original[part];
                    probability *= (rep>>part)&1 ? prior[col] : 1-prior[col];
                    if ((rep>>part)&1) cost += weights[col];
                }
                mass[state] += probability;
                if (cost < mincost[state]) { mincost[state] = cost; group.representation[state] = rep; }
            }
            for (int state = 0; state < group.states; ++state) group.energy[state] = -std::log(mass[state]/mass[0]);
            for (int part = 0; part < (group.states == 4 ? 2 : 1); ++part) {
                int bit = 2*index+part;
                active.push_back(bit);
                for (int row = 0; row < m; ++row) if (h[row*n+group.original[part]]) hcols[bit][row/64] |= 1ULL<<(row%64);
            }
            for (int row = 0; row < m; ++row) {
                int mask = h[row*n+group.original[0]];
                if (group.states == 4) mask |= h[row*n+group.original[1]]<<1;
                if (!mask) continue;
                int edge = edges.size();
                edges.push_back({index,row,mask}); checks[row].push_back(edge); group.edges.push_back(edge);
            }
        }
    }

    static int parity(int value) { return __builtin_parity(unsigned(value)); }
    static void toggle(Bits& target, const Bits& source) {
        for (size_t word = 0; word < target.size(); ++word) target[word] ^= source[word];
    }
    static int highest(const Bits& value) {
        for (int word = int(value.size())-1; word >= 0; --word)
            if (value[word]) return 64*word+63-__builtin_clzll(value[word]);
        return -1;
    }
    double cost(const Bits& candidate) const {
        double total = 0;
        for (int word = 0; word < words; ++word) {
            uint64_t value = candidate[word];
            while (value) {
                int offset = __builtin_ctzll(value) & ~1;
                int state = (value>>offset)&3;
                total += groups[word*32+offset/2].energy[state];
                value &= ~(3ULL<<offset);
            }
        }
        return total;
    }
    void consider(const Bits& candidate) {
        double candidatecost = cost(candidate);
        if (candidatecost < bestcost-1e-9) { bestcost = candidatecost; best = candidate; ++improvements; }
    }

    void osd(const uint8_t* syndrome, const std::vector<double>& reliability,
             const Bits& hard, int depth, double noise) {
        std::vector<int> order = active;
        std::vector<double> ranking(reliability.size());
        std::normal_distribution<double> normal(0,1);
        for (int bit : active) ranking[bit] = std::abs(reliability[bit]) + noise*normal(random);
        std::stable_sort(order.begin(), order.end(), [&](int left, int right) { return ranking[left] < ranking[right]; });
        std::vector<Bits> basis(rows), combination(rows);
        std::vector<Bits> kernels;
        Bits target(hwords,0), correction = hard;
        for (int row = 0; row < rows; ++row) if (syndrome[row]) target[row/64] |= 1ULL<<(row%64);
        for (int bit : active) if ((hard[bit/64]>>(bit%64))&1) toggle(target,hcols[bit]);
        for (int bit : order) {
            Bits column = hcols[bit], combo(words,0);
            combo[bit/64] |= 1ULL<<(bit%64);
            int pivot;
            while ((pivot = highest(column)) >= 0) {
                if (basis[pivot].empty()) { basis[pivot] = column; combination[pivot] = combo; break; }
                toggle(column,basis[pivot]); toggle(combo,combination[pivot]);
            }
            if (pivot < 0) kernels.push_back(std::move(combo));
        }
        int pivot;
        while ((pivot=highest(target)) >= 0) {
            if (basis[pivot].empty()) return;
            toggle(target,basis[pivot]); toggle(correction,combination[pivot]);
        }
        consider(correction);
        if (!depth) return;
        Bits candidate(words);
        std::vector<double> singlecost(kernels.size());
        for (size_t index = 0; index < kernels.size(); ++index) {
            for (int word = 0; word < words; ++word) candidate[word] = correction[word]^kernels[index][word];
            singlecost[index] = cost(candidate);
            consider(candidate);
        }
        std::vector<int> selected(kernels.size());
        std::iota(selected.begin(),selected.end(),0);
        int limit = std::min(depth,int(kernels.size()));
        if (limit < int(selected.size())) {
            std::partial_sort(selected.begin(),selected.begin()+limit,selected.end(),[&](int left,int right) { return singlecost[left]<singlecost[right]; });
            selected.resize(limit);
        }
        for (int first = 0; first < int(selected.size()); ++first) {
            for (int second = 0; second < first; ++second) {
                for (int word = 0; word < words; ++word) candidate[word] = correction[word]^kernels[selected[first]][word]^kernels[selected[second]][word];
                consider(candidate);
            }
        }
        for (int sweep = 0; sweep < 3; ++sweep) {
            double before = bestcost;
            for (const auto& kernel : kernels) {
                for (int word = 0; word < words; ++word) candidate[word] = best[word]^kernel[word];
                consider(candidate);
            }
            if (bestcost == before) break;
        }
    }

    void decode(const uint8_t* syndrome, const double* soft, uint8_t* output,
                double* diagnostics, int attempts, int iterations, int depth, double seconds, int mode) {
        bestcost = 1e100; best.assign(words,0); improvements=0;
        auto started = std::chrono::steady_clock::now();
        std::normal_distribution<double> normal(0,1);
        std::vector<double> reliability(2*groups.size(), 0), bestrel;
        Bits hard(words,0), savedhard;
        for (int index = 0; index < int(groups.size()); ++index) {
            for (int part = 0; part < (groups[index].states==4?2:1); ++part) reliability[2*index+part] = weights[groups[index].original[part]];
        }
        osd(syndrome,reliability,hard,depth,0);
        int completed = 0, validbp = 0;
        for (int attempt = 0; attempt < attempts; ++attempt) {
            if (attempt && std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count() > seconds) break;
            ++completed;
            std::vector<std::array<double,4>> priorenergy(groups.size());
            double perturb = attempt == 0 ? 0 : (attempt%3 == 0 ? 1.5 : .6);
            double scale = attempt == 0 ? 1 : (.7 + .15*(attempt%5));
            double damping = attempt%4==0 ? .2 : (attempt%4==1 ? .5 : 0.0);
            for (int index = 0; index < int(groups.size()); ++index) {
                for (int state = 0; state < groups[index].states; ++state)
                    priorenergy[index][state] = scale*groups[index].energy[state] + (state ? perturb*normal(random) : 0);
            }
            std::vector<double> message(edges.size(),0), variable(edges.size(),0);
            std::vector<bool> enabled(rows,true);
            if (mode == 1 || (mode == 3 && attempt%4 == 3)) {
                std::vector<int> roworder(rows);
                std::iota(roworder.begin(),roworder.end(),0);
                if (attempt) std::shuffle(roworder.begin(),roworder.end(),random);
                std::stable_sort(roworder.begin(),roworder.end(),[&](int left,int right) { return checks[left].size()<checks[right].size(); });
                std::vector<Bits> rowbasis(2*groups.size());
                for (int row : roworder) {
                    Bits vector(words,0);
                    for (int edge : checks[row]) {
                        int index=edges[edge].group;
                        vector[index/32] ^= uint64_t(edges[edge].mask)<<(2*(index%32));
                    }
                    int pivot;
                    while ((pivot=highest(vector))>=0) {
                        if (rowbasis[pivot].empty()) { rowbasis[pivot]=vector; break; }
                        toggle(vector,rowbasis[pivot]);
                    }
                    enabled[row]=pivot>=0;
                }
            }
            bestrel = reliability; savedhard = hard;
            int leastresidual = rows+1;
            double residualcost = 1e100;
            for (int iteration = 0; iteration < iterations; ++iteration) {
                hard.assign(words,0);
                for (int index = 0; index < int(groups.size()); ++index) {
                    Group& group = groups[index];
                    std::array<double,4> energies = priorenergy[index];
                    for (int edge : group.edges) {
                        int mask = edges[edge].mask;
                        for (int state = 0; state < group.states; ++state) if (parity(state&mask)) energies[state] += message[edge];
                    }
                    int chosen = 0;
                    for (int state = 1; state < group.states; ++state) if (energies[state] < energies[chosen]) chosen=state;
                    hard[index/32] |= uint64_t(chosen)<<(2*(index%32));
                    for (int part = 0; part < (group.states==4?2:1); ++part) {
                        double zero = 0, one = 0;
                        for (int state = 0; state < group.states; ++state) {
                            double probability = std::exp(std::max(-700.0,energies[chosen]-energies[state]));
                            if ((state>>part)&1) one+=probability; else zero+=probability;
                        }
                        reliability[2*index+part] = std::log(std::max(1e-300,zero)/std::max(1e-300,one));
                    }
                    for (int edge : group.edges) {
                        int mask=edges[edge].mask;
                        double minimum = 1e100;
                        std::array<double,4> extrinsic{};
                        for (int state = 0; state < group.states; ++state) {
                            extrinsic[state] = energies[state] - (parity(state&mask) ? message[edge] : 0);
                            minimum = std::min(minimum,extrinsic[state]);
                        }
                        double zero = 0, one = 0;
                        for (int state = 0; state < group.states; ++state) {
                            double probability=std::exp(std::max(-700.0,minimum-extrinsic[state]));
                            if (parity(state&mask)) one+=probability; else zero+=probability;
                        }
                        variable[edge] = std::max(-35.0,std::min(35.0,std::log(std::max(1e-300,zero)/std::max(1e-300,one))));
                    }
                }
                int residual = 0;
                for (int row = 0; row < rows; ++row) {
                    int value = syndrome[row];
                    for (int edge : checks[row]) {
                        int index = edges[edge].group;
                        int state = (hard[index/32]>>(2*(index%32)))&3;
                        value ^= parity(state&edges[edge].mask);
                    }
                    residual += value;
                }
                if (!residual) { consider(hard); ++validbp; }
                double currentcost=cost(hard);
                if (residual < leastresidual || (residual == leastresidual && currentcost < residualcost)) {
                    leastresidual=residual; residualcost=currentcost; bestrel=reliability; savedhard=hard;
                }
                if (!residual && iteration > 5) break;
                for (int row = 0; row < rows; ++row) {
                    if (!enabled[row]) continue;
                    if (mode == 2 || (mode == 3 && attempt%4 == 2)) {
                        double firstmin=35, secondmin=35;
                        int sign=syndrome[row] ? -1 : 1;
                        int minimumedge=-1;
                        for (int edge : checks[row]) {
                            double absolute=std::abs(variable[edge]);
                            if (variable[edge]<0) sign=-sign;
                            if (absolute<firstmin) { secondmin=firstmin; firstmin=absolute; minimumedge=edge; }
                            else if (absolute<secondmin) secondmin=absolute;
                        }
                        for (int edge : checks[row]) {
                            double update=(edge==minimumedge ? secondmin : firstmin)*(.7+.05*(attempt%4));
                            update *= variable[edge]<0 ? -sign : sign;
                            message[edge]=damping*message[edge]+(1-damping)*update;
                        }
                        continue;
                    }
                    double product = syndrome[row] ? -1.0 : 1.0;
                    int zeros=0;
                    for (int edge : checks[row]) {
                        double value=std::tanh(variable[edge]*.5);
                        if (std::abs(value)<1e-15) ++zeros; else product *= value;
                    }
                    for (int edge : checks[row]) {
                        double value=std::tanh(variable[edge]*.5), excluded=0;
                        if (!zeros) excluded=product/value;
                        else if (zeros==1 && std::abs(value)<1e-15) excluded=product;
                        excluded=std::max(-1+1e-14,std::min(1-1e-14,excluded));
                        double update=std::log((1+excluded)/(1-excluded));
                        message[edge] = damping*message[edge] + (1-damping)*update;
                    }
                }
            }
            osd(syndrome,bestrel,savedhard,depth,attempt%4==3?.5:0);
            if (leastresidual && attempt%2==0) osd(syndrome,reliability,hard,depth,0);
        }
        std::fill(output,output+columns,0);
        for (int index=0; index<int(groups.size()); ++index) {
            int state=(best[index/32]>>(2*(index%32)))&3;
            int rep=groups[index].representation[state];
            for (int part=0; part<int(groups[index].original.size()); ++part) output[groups[index].original[part]]=(rep>>part)&1;
        }
        diagnostics[0]=bestcost; diagnostics[1]=completed; diagnostics[2]=validbp;
        diagnostics[3]=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
        diagnostics[4]=improvements;
    }
};

extern "C" int decode_batch(int rows,int columns,int logicals,int frames,
    const uint8_t* matrix,const uint8_t* logical,const double* prior,
    const uint8_t* syndromes,const double* soft,uint8_t* output,double* diagnostics,
    int grouped,int attempts,int iterations,int depth,double seconds,int mode) {
    try {
        Decoder decoder(rows,columns,logicals,matrix,logical,prior,grouped);
        for (int frame=0; frame<frames; ++frame)
            decoder.decode(syndromes+frame*rows,soft+frame*columns,output+frame*columns,
                           diagnostics+frame*5,attempts,iterations,depth,seconds,mode);
        return decoder.groups.size();
    } catch (...) { return -1; }
}
