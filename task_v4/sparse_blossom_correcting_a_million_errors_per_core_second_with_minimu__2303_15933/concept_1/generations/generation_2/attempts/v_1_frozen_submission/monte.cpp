#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>
using std::vector;
using Word=uint64_t;
struct Chain {
    vector<uint8_t> state;
    vector<int> active,position;
    float energy=0;
    int label=0;
    void toggle(int var) {
        if(state[var]) {
            int last=active.back();
            active[position[var]]=last;position[last]=position[var];active.pop_back();
        } else {position[var]=active.size();active.push_back(var);}
        state[var]^=1;
    }
};
struct Monte {
    int variables;
    vector<float> prior;
    vector<vector<int>> moves,incident;
    vector<float> invdegree,totals;
    Word rng;
    Word random() {rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;return rng;}
    double uniform() {return (random()>>11)*0x1.0p-53;}
    Monte(int nv,int nm,const double* probabilities,const int* offsets,const int* indexes):variables(nv),prior(nv),moves(nm),incident(nv),invdegree(nv),totals(nm) {
        for(int var=0;var<nv;var++) prior[var]=std::log((1-probabilities[var])/probabilities[var]);
        for(int index=0;index<nm;index++) {
            moves[index].assign(indexes+offsets[index],indexes+offsets[index+1]);
            for(int var:moves[index]) incident[var].push_back(index);
        }
        for(int var=0;var<nv;var++) invdegree[var]=incident[var].empty()?0:1.0f/incident[var].size();
        for(int index=0;index<nm;index++) for(int var:moves[index]) totals[index]+=invdegree[var];
    }
    void decode(const uint8_t* refs,const float* costs,float* output,int blocks,int replicas,int localsteps,float topbeta,float hotbeta,float activeprob) {
        int best=std::min_element(costs,costs+16)-costs;
        vector<int> labels;
        for(int label=0;label<16;label++) if(costs[label]<costs[best]+12) labels.push_back(label);
        std::fill(output,output+32,0);
        for(int label=0;label<16;label++) output[16+label]=costs[label];
        if(labels.size()==1) {output[best]=1;return;}
        vector<vector<int>> templates(256);
        for(int left:labels) for(int right:labels) if(left!=right) {
            auto& diff=templates[left*16+right];
            for(int var=0;var<variables;var++) if(refs[left*variables+var]!=refs[right*variables+var]) diff.push_back(var);
        }
        vector<Chain> chains(replicas);
        vector<float> beta(replicas);
        rng=91238723;
        for(int var=0;var<variables;var++) rng=(rng^refs[best*variables+var])*1099511628211ULL;
        for(int replica=0;replica<replicas;replica++) {
            auto& chain=chains[replica];
            int label=replica==0?best:labels[replica%labels.size()];
            chain.label=label;chain.state.assign(refs+label*variables,refs+(label+1)*variables);
            chain.position.resize(variables);
            for(int var=0;var<variables;var++) if(chain.state[var]) {chain.position[var]=chain.active.size();chain.active.push_back(var);chain.energy+=prior[var];}
            beta[replica]=replicas==1?topbeta:topbeta+(hotbeta-topbeta)*replica/(replicas-1);
        }
        float uniformprob=(1-activeprob)/moves.size();
        for(int block=0;block<blocks;block++) {
            for(int replica=0;replica<replicas;replica++) {
                auto& chain=chains[replica];
                for(int step=0;step<localsteps;step++) {
                    int chosen;
                    if(uniform()<activeprob && !chain.active.empty()) {
                        int var=chain.active[random()%chain.active.size()];
                        if(incident[var].empty()) continue;
                        chosen=incident[var][random()%incident[var].size()];
                    } else chosen=random()%moves.size();
                    const auto& move=moves[chosen];
                    float delta=0,activeweight=0;
                    int count=0;
                    for(int var:move) {
                        if(chain.state[var]) {delta-=prior[var];activeweight+=invdegree[var];count++;}
                        else delta+=prior[var];
                    }
                    int reverse_count=chain.active.size()+move.size()-2*count;
                    float forward=uniformprob+activeprob*activeweight/std::max(1,int(chain.active.size()));
                    float reverse=uniformprob+activeprob*(totals[chosen]-activeweight)/std::max(1,reverse_count);
                    if(uniform()*forward<std::exp(-beta[replica]*delta)*reverse) {
                        for(int var:move) chain.toggle(var);
                        chain.energy+=delta;
                        output[16+chain.label]=std::min(output[16+chain.label],chain.energy);
                    }
                }
                std::array<float,16> delta{};
                float minimum=0;
                for(int label:labels) {
                    float diff=0;
                    for(int var:templates[chain.label*16+label]) diff+=chain.state[var]?-prior[var]:prior[var];
                    delta[label]=diff;minimum=std::min(minimum,diff);
                    output[16+label]=std::min(output[16+label],chain.energy+diff);
                }
                std::array<double,16> mass{};
                double total=0;
                for(int label:labels) {mass[label]=std::exp(-beta[replica]*(delta[label]-minimum));total+=mass[label];}
                if(replica==0 && block>=blocks/4) for(int label:labels) output[label]+=mass[label]/total;
                double choice=uniform()*total;
                int selected=chain.label;
                for(int label:labels) {choice-=mass[label];if(choice<=0) {selected=label;break;}}
                if(selected!=chain.label) {
                    for(int var:templates[chain.label*16+selected]) chain.toggle(var);
                    chain.energy+=delta[selected];chain.label=selected;
                }
            }
            if(replicas>1) {
                for(int replica=block%2;replica+1<replicas;replica+=2) {
                    double logprob=(beta[replica]-beta[replica+1])*(chains[replica].energy-chains[replica+1].energy);
                    if(uniform()<std::exp(logprob)) std::swap(chains[replica],chains[replica+1]);
                }
            }
        }
        for(int label=0;label<16;label++) output[label]/=blocks-blocks/4;
    }
};
extern "C" {
void* create_monte(int nv,int nm,const double* probabilities,const int* offsets,const int* indexes) {return new Monte(nv,nm,probabilities,offsets,indexes);}
void destroy_monte(void* handle) {delete static_cast<Monte*>(handle);}
void run_monte(void* handle,int shots,const uint8_t* states,const float* costs,float* output,int blocks,int replicas,int steps,float topbeta,float hotbeta,float activeprob) {
    auto& monte=*static_cast<Monte*>(handle);
    for(int shot=0;shot<shots;shot++) monte.decode(states+shot*16*monte.variables,costs+shot*16,output+shot*32,blocks,replicas,steps,topbeta,hotbeta,activeprob);
}
}
