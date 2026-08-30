#include <cmath>
#include <cstdint>
#include <algorithm>
#include <vector>
#include <queue>

extern "C" void infer(int count, const double* probabilities, int syndrome, int physical, double* values, double* gradients, uint64_t* solutions) {
    for (int sample = 0; sample < count; ++sample) {
        const double* rates = probabilities + 39 * sample;
        double hm[6][16], hc[6][16], vm[5][8], vc[5][8], weights[39];
        for (int edge = 0; edge < 39; ++edge) weights[edge] = std::log((1-rates[edge])/rates[edge]);
        for (int column = 0; column < 6; ++column) for (int mask = 0; mask < 16; ++mask) {
            hm[column][mask] = 1; hc[column][mask] = 0;
            for (int row = 0; row < 4; ++row) {
                int edge = 4*column+row;
                bool bit = mask & (1 << row);
                hm[column][mask] *= bit ? rates[edge] : 1-rates[edge];
                if (bit) hc[column][mask] += weights[edge];
            }
        }
        for (int column = 0; column < 5; ++column) for (int mask = 0; mask < 8; ++mask) {
            vm[column][mask] = 1; vc[column][mask] = 0;
            for (int row = 0; row < 3; ++row) {
                int edge = 24+3*column+row;
                bool bit = mask & (1 << row);
                vm[column][mask] *= bit ? rates[edge] : 1-rates[edge];
                if (bit) vc[column][mask] += weights[edge];
            }
        }
        double forward[6][2][16] = {}, costs[2][16];
        uint64_t masks[2][16] = {};
        for (int logical = 0; logical < 2; ++logical) for (int mask = 0; mask < 16; ++mask) {
            costs[logical][mask] = 1e100;
            if ((__builtin_popcount((unsigned)mask)&1) == logical) {
                forward[0][logical][mask] = hm[0][mask];
                costs[logical][mask] = hc[0][mask]; masks[logical][mask] = mask;
            }
        }
        for (int column = 0; column < 5; ++column) {
            double nextcost[2][16]; uint64_t nextmask[2][16];
            int required = (syndrome >> (4*column)) & 15;
            for (int logical = 0; logical < 2; ++logical) for (int out = 0; out < 16; ++out) {
                double mass = 0, best = 1e100; uint64_t bestmask = 0;
                for (int vert = 0; vert < 8; ++vert) {
                    int in = out ^ vert ^ (vert<<1) ^ required;
                    mass += forward[column][logical][in]*vm[column][vert];
                    double cost = costs[logical][in]+vc[column][vert];
                    if (cost < best) {
                        best = cost;
                        bestmask = masks[logical][in] | ((uint64_t)vert << (24+3*column));
                    }
                }
                forward[column+1][logical][out] = mass*hm[column+1][out];
                nextcost[logical][out] = best+hc[column+1][out];
                nextmask[logical][out] = bestmask | ((uint64_t)out << (4*(column+1)));
            }
            std::copy(&nextcost[0][0], &nextcost[0][0]+32, &costs[0][0]);
            std::copy(&nextmask[0][0], &nextmask[0][0]+32, &masks[0][0]);
        }
        double joint[2] = {}, best[2] = {1e100,1e100}; uint64_t bestmask[2] = {};
        for (int logical = 0; logical < 2; ++logical) for (int mask = 0; mask < 16; ++mask) {
            joint[logical] += forward[5][logical][mask];
            if (costs[logical][mask] < best[logical]) {best[logical] = costs[logical][mask]; bestmask[logical] = masks[logical][mask];}
        }
        int opposite = 1-physical;
        values[3*sample] = best[opposite]-best[physical];
        values[3*sample+1] = std::log(joint[opposite]/joint[physical]);
        values[3*sample+2] = std::log(joint[0]+joint[1]);
        if (solutions) {solutions[2*sample] = bestmask[physical]; solutions[2*sample+1] = bestmask[opposite];}
        if (!gradients) continue;
        double expectation[2][39] = {}, backward[2][16];
        std::fill(&backward[0][0], &backward[0][0]+32, 1.0);
        for (int column = 4; column >= 0; --column) {
            double previous[2][16] = {};
            int required = (syndrome >> (4*column)) & 15;
            for (int logical = 0; logical < 2; ++logical) for (int out = 0; out < 16; ++out) {
                double horizontal_count = 0;
                for (int vert = 0; vert < 8; ++vert) {
                    int in = out ^ vert ^ (vert<<1) ^ required;
                    double transition = vm[column][vert]*hm[column+1][out]*backward[logical][out];
                    previous[logical][in] += transition;
                    double contribution = forward[column][logical][in]*transition/joint[logical];
                    horizontal_count += contribution;
                    for (int row = 0; row < 3; ++row) if (vert & (1<<row)) expectation[logical][24+3*column+row] += contribution;
                }
                for (int row = 0; row < 4; ++row) if (out & (1<<row)) expectation[logical][4*(column+1)+row] += horizontal_count;
            }
            std::copy(&previous[0][0], &previous[0][0]+32, &backward[0][0]);
        }
        for (int mask = 0; mask < 16; ++mask) {
            int logical = __builtin_popcount((unsigned)mask)&1;
            double contribution = hm[0][mask]*backward[logical][mask]/joint[logical];
            for (int row = 0; row < 4; ++row) if (mask & (1<<row)) expectation[logical][row] += contribution;
        }
        for (int edge = 0; edge < 39; ++edge) {
            double denominator = rates[edge]*(1-rates[edge]);
            double mean = (joint[0]*expectation[0][edge]+joint[1]*expectation[1][edge])/(joint[0]+joint[1]);
            gradients[(3*sample)*39+edge] = (double(int((bestmask[physical]>>edge)&1))-double(int((bestmask[opposite]>>edge)&1)))/denominator;
            gradients[(3*sample+1)*39+edge] = (expectation[opposite][edge]-expectation[physical][edge])/denominator;
            gradients[(3*sample+2)*39+edge] = (mean-rates[edge])/denominator;
        }
    }
}

extern "C" void scan_mode(const double* rates, int keep, int* syndromes, double* scores, int mode, int* physicals) {
    const int state_count = 1<<21;
    std::vector<double> masses(state_count), costs(state_count);
    int incidence[39];
    for (int cut = 0; cut < 6; ++cut) for (int row = 0; row < 4; ++row) {
        int mask = 0;
        if (cut>0) mask ^= 1<<(4*(cut-1)+row);
        if (cut<5) mask ^= 1<<(4*cut+row);
        if (cut==0) mask ^= 1<<20;
        incidence[4*cut+row]=mask;
    }
    for (int column = 0; column < 5; ++column) for (int row = 0; row < 3; ++row)
        incidence[24+3*column+row]=(1<<(4*column+row))^(1<<(4*column+row+1));
    double weights[39];
    for (int edge = 0; edge < 39; ++edge) weights[edge]=std::log((1-rates[edge])/rates[edge]);
    double mass=1, cost=0;
    for (int edge = 0; edge < 21; ++edge) mass*=1-rates[edge];
    int syndrome=0,gray=0;
    masses[0]=mass;costs[0]=cost;
    for (int index = 1; index < state_count; ++index) {
        int bit=__builtin_ctz((unsigned)index);
        syndrome ^= incidence[bit];
        gray ^= 1<<bit;
        if (gray & (1<<bit)) {mass*=rates[bit]/(1-rates[bit]);cost+=weights[bit];}
        else {mass*=(1-rates[bit])/rates[bit];cost-=weights[bit];}
        masses[syndrome]=mass; costs[syndrome]=cost;
    }
    for (int edge = 21; edge < 39; ++edge) {
        int mask=incidence[edge];
        int low=mask & -mask;
        double rate=rates[edge], weight=weights[edge];
        for (int block = 0; block < state_count; block+=2*low) for (int offset=0;offset<low;++offset) {
            int first=block+offset,second=first^mask;
            double first_mass=masses[first],second_mass=masses[second];
            masses[first]=(1-rate)*first_mass+rate*second_mass;
            masses[second]=(1-rate)*second_mass+rate*first_mass;
            double first_cost=costs[first],second_cost=costs[second];
            costs[first]=std::min(first_cost,second_cost+weight);
            costs[second]=std::min(second_cost,first_cost+weight);
        }
    }
    std::priority_queue<std::pair<double,int>,std::vector<std::pair<double,int>>,std::greater<std::pair<double,int>>> heap;
    for (int syndrome=0;syndrome<(1<<20);++syndrome) {
        int count=__builtin_popcount((unsigned)syndrome);
        if (count<3 || count>6) continue;
        int rows=0,columns=0;
        for (int column=0;column<5;++column) {
            int field=(syndrome>>(4*column))&15;
            rows |= field;
            if (field) columns |= 1<<column;
        }
        if (__builtin_popcount((unsigned)rows)<3 || __builtin_popcount((unsigned)columns)<3)continue;
        int physical=costs[syndrome+(1<<20)]<costs[syndrome];
        double gap=std::abs(costs[syndrome+(1<<20)]-costs[syndrome]);
        double odds=std::log(masses[syndrome+((1-physical)<<20)]/masses[syndrome+(physical<<20)]);
        double total=masses[syndrome]+masses[syndrome+(1<<20)];
        double score=std::min({(gap-.112)/1.08,(odds-.112)/std::log(.85/.15),total*std::exp(-.112)/1.75e-5});
        if (mode) {
            double entropy=gap+odds;
            if (entropy<0) {physical=1-physical;entropy=-entropy;}
            score=std::min((entropy-.224)/(1.08+std::log(.85/.15)),total*std::exp(-.112)/1.75e-5);
        }
        int code=syndrome+(physical<<20);
        if ((int)heap.size()<keep)heap.push({score,code});
        else if(score>heap.top().first) {heap.pop();heap.push({score,code});}
    }
    for (int index=keep-1;index>=0;--index) {scores[index]=heap.top().first;syndromes[index]=heap.top().second&((1<<20)-1);if(physicals)physicals[index]=heap.top().second>>20;heap.pop();}
}

extern "C" void scan(const double* rates, int keep, int* syndromes, double* scores) {
    scan_mode(rates,keep,syndromes,scores,0,nullptr);
}
