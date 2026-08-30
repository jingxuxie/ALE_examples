#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>
using std::vector;
using Word=uint64_t;
struct Worm {
    int variables,detectors;
    vector<float> prior;
    vector<vector<int>> moves,incident;
    vector<int> endpoints,logical;
    Word rng;
    Word random() {rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;return rng;}
    double uniform() {return (random()>>11)*0x1.0p-53;}
    Worm(int nv,int nd,int nm,const double* probabilities,const int* offsets,const int* indexes,const int* ends,const int* labels):variables(nv),detectors(nd),prior(nv),moves(nm),incident(nd),endpoints(ends,ends+nm*2),logical(labels,labels+nm) {
        for(int var=0;var<nv;var++) prior[var]=std::log((1-probabilities[var])/probabilities[var]);
        for(int index=0;index<nm;index++) {
            moves[index].assign(indexes+offsets[index],indexes+offsets[index+1]);
            incident[endpoints[2*index]].push_back(index);incident[endpoints[2*index+1]].push_back(index);
        }
    }
    void decode(const uint8_t* refs,const float* costs,float* output,int steps,float beta,float fugacity,int gibbs) {
        int best=std::min_element(costs,costs+16)-costs;
        vector<uint8_t> state(refs+best*variables,refs+(best+1)*variables);
        int label=best,head=0,tail=0;
        float energy=0;for(int var=0;var<variables;var++) if(state[var]) energy+=prior[var];
        rng=721937;
        for(int var=0;var<variables;var++) rng=(rng^state[var])*1099511628211ULL;
        std::fill(output,output+32,0);
        vector<vector<int>> templates(256);
        vector<int> labels;
        for(int choice=0;choice<16;choice++) if(costs[choice]<1e20) labels.push_back(choice);
        for(int left:labels) for(int right:labels) if(left!=right) {
            for(int var=0;var<variables;var++) if(refs[left*variables+var]!=refs[right*variables+var]) templates[left*16+right].push_back(var);
        }
        int samples=0;
        for(int step=0;step<steps;step++) {
            if(head==tail) {
                if(step>=steps/4) {output[label]++;samples++;}
                head=tail=random()%detectors;
            }
            if(gibbs>0 && step%gibbs==0 && costs[label]<1e20) {
                std::array<float,16> delta{};
                std::array<double,16> mass{};
                float minimum=0;
                for(int other:labels) {
                    float diff=0;
                    for(int var:templates[label*16+other]) diff+=state[var]?-prior[var]:prior[var];
                    delta[other]=diff;minimum=std::min(minimum,diff);
                }
                double total=0;
                for(int other:labels) {mass[other]=std::exp(-beta*(delta[other]-minimum));total+=mass[other];}
                double choice=uniform()*total;
                int selected=label;
                for(int other:labels) {choice-=mass[other];if(choice<=0) {selected=other;break;}}
                for(int var:templates[label*16+selected]) state[var]^=1;
                energy+=delta[selected];label=selected;
            }
            int move=incident[head][random()%incident[head].size()];
            int other=endpoints[2*move]^endpoints[2*move+1]^head;
            float delta=0;
            for(int var:moves[move]) delta+=state[var]?-prior[var]:prior[var];
            double ratio=double(incident[head].size())/incident[other].size();
            if(head==tail) ratio*=fugacity;
            if(other==tail) ratio/=fugacity;
            if(uniform()<std::exp(-beta*delta)*ratio) {
                for(int var:moves[move]) state[var]^=1;
                energy+=delta;label^=logical[move];head=other;
            }
        }
        if(samples) for(int state_index=0;state_index<16;state_index++) output[state_index]/=samples;
        else output[best]=1;
        output[16]=samples;output[17]=energy;
    }
};
extern "C" {
void* create_worm(int nv,int nd,int nm,const double* probabilities,const int* offsets,const int* indexes,const int* endpoints,const int* labels) {return new Worm(nv,nd,nm,probabilities,offsets,indexes,endpoints,labels);}
void destroy_worm(void* handle) {delete static_cast<Worm*>(handle);}
void run_worm(void* handle,int shots,const uint8_t* states,const float* costs,float* output,int steps,float beta,float fugacity,int gibbs) {
    auto& worm=*static_cast<Worm*>(handle);
    for(int shot=0;shot<shots;shot++) worm.decode(states+shot*16*worm.variables,costs+shot*16,output+shot*32,steps,beta,fugacity,gibbs);
}
}
