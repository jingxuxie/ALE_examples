#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <unordered_map>
#include <vector>

using std::vector;
using Word = uint64_t;
struct Entry {int label; float cost;};
struct Decoder {
    int detectors, variables, groups, words;
    vector<vector<int>> checks;
    vector<int> edge_var, logical, group, mask, mate, first;
    vector<std::array<float,4>> weights;
    vector<vector<Word>> original;
    vector<float> table, soft;
    vector<Word> hashes;
    Decoder(int nd, int nv, int ng, const uint8_t* matrix, const uint8_t* obs, const float* costs, const int* grouping)
        : detectors(nd), variables(nv), groups(ng), words((nv+63)/64), checks(nd), logical(nv), group(grouping,grouping+nv), mask(nv,1), mate(nv,-1), first(ng,-1), weights(ng), original(nd,vector<Word>(words)), table(32770),soft(32770),hashes(nv) {
        for(int index=0;index<32770;index++) {
            double value=std::max(0.00001,index/2048.0);
            table[index]=-std::log(std::tanh(value/2));
            soft[index]=std::log1p(std::exp(-value));
        }
        for(int grp=0;grp<groups;grp++) for(int state=0;state<4;state++) weights[grp][state]=costs[4*grp+state];
        for(int var=0;var<variables;var++) {
            int grp=group[var];
            if(first[grp]<0) first[grp]=var;
            else {mask[var]=2;mate[var]=first[grp];mate[first[grp]]=var;}
            Word hash=var+0x9e3779b97f4a7c15ULL;
            hash=(hash^(hash>>30))*0xbf58476d1ce4e5b9ULL;
            hash=(hash^(hash>>27))*0x94d049bb133111ebULL;
            hashes[var]=hash^(hash>>31);
            for(int bit=0;bit<4;bit++) logical[var]|=int(obs[bit*nv+var])<<bit;
            for(int check=0;check<nd;check++) if(matrix[check*nv+var]) {
                checks[check].push_back(edge_var.size());edge_var.push_back(var);
                original[check][var/64]|=Word(1)<<(var%64);
            }
        }
    }
    float phi(float value) const {
        if(value>=16) return 0.0000002f;
        float position=std::max(value*2048,0.02f);
        int index=int(position);
        return table[index]+(position-index)*(table[index+1]-table[index]);
    }
    float softplus(float value) const {
        if(value>=16) return 0;
        float position=value*2048;
        int index=int(position);
        return soft[index]+(position-index)*(soft[index+1]-soft[index]);
    }
    float logadd(float left,float right) const {
        return std::max(left,right)+softplus(std::abs(left-right));
    }
    float post(int var, const vector<float>& sums, const vector<std::array<float,4>>& channel) const {
        const auto& cost=channel[group[var]];
        if(mate[var]<0) return sums[var]+cost[1];
        int bit=mask[var], other=3^bit;
        float other_sum=sums[mate[var]];
        return sums[var]+logadd(0,-cost[other]-other_sum)-logadd(-cost[bit],-cost[3]-other_sum);
    }
    bool belief(const uint8_t* syndrome,vector<float>& posterior,vector<uint8_t>& hard,int iterations,int trial) {
        vector<float> messages(edge_var.size(),0),incoming(edge_var.size()),transformed(edge_var.size()),sums(variables,0),average(variables,0);
        auto channel=weights;
        if(trial) {
            Word seed=1234567+trial*8191;
            for(int check=0;check<detectors;check++) seed=(seed^syndrome[check])*1099511628211ULL;
            for(int grp=0;grp<groups;grp++) {
                seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;
                float factor=0.7f+0.6f*float(seed&65535)/65535;
                for(int state=1;state<4;state++) channel[grp][state]*=factor;
            }
        }
        for(int iteration=0;iteration<iterations;iteration++) {
            for(int check=0;check<detectors;check++) {
                float total=0;int sign=syndrome[check];
                for(int edge:checks[check]) {
                    int var=edge_var[edge];
                    float value=std::clamp(post(var,sums,channel)-messages[edge],-30.0f,30.0f);
                    incoming[edge]=value;transformed[edge]=phi(std::abs(value));
                    total+=transformed[edge];sign^=value<0;
                }
                for(int edge:checks[check]) {
                    float value=std::min(30.0f,phi(std::max(0.0f,total-transformed[edge])));
                    if(sign^(incoming[edge]<0)) value=-value;
                    float updated=value*0.7f+messages[edge]*0.3f;
                    sums[edge_var[edge]]+=updated-messages[edge];messages[edge]=updated;
                }
            }
            for(int var=0;var<variables;var++) {
                posterior[var]=post(var,sums,channel);
                hard[var]=posterior[var]<0;
                average[var]=0.8f*average[var]+0.2f*posterior[var];
            }
            bool valid=true;
            for(int check=0;check<detectors;check++) {
                int parity=syndrome[check];
                for(int edge:checks[check]) parity^=hard[edge_var[edge]];
                if(parity) {valid=false;break;}
            }
            if(valid) return true;
        }
        posterior=average;
        for(int var=0;var<variables;var++) hard[var]=posterior[var]<0;
        return false;
    }
    void osd(const uint8_t* syndrome,const vector<float>& posterior,const vector<uint8_t>& hard,int order,std::unordered_map<Word,Entry>& candidates) {
        vector<int> sorted(variables);std::iota(sorted.begin(),sorted.end(),0);
        std::stable_sort(sorted.begin(),sorted.end(),[&](int left,int right){return std::abs(posterior[left])<std::abs(posterior[right]);});
        auto rows=original;
        vector<uint8_t> rhs(syndrome,syndrome+detectors);
        for(int check=0;check<detectors;check++) for(int edge:checks[check]) rhs[check]^=hard[edge_var[edge]];
        vector<int> pivots,freevars;int rank=0;
        for(int var:sorted) {
            int pivot=rank,block=var/64;Word flag=Word(1)<<(var%64);
            while(pivot<detectors && !(rows[pivot][block]&flag)) pivot++;
            if(pivot==detectors) {freevars.push_back(var);continue;}
            std::swap(rows[rank],rows[pivot]);std::swap(rhs[rank],rhs[pivot]);
            for(int check=0;check<detectors;check++) if(check!=rank && (rows[check][block]&flag)) {
                for(int word=0;word<words;word++) rows[check][word]^=rows[rank][word];
                rhs[check]^=rhs[rank];
            }
            pivots.push_back(var);rank++;
        }
        vector<uint8_t> base=hard;
        for(int index=0;index<rank;index++) base[pivots[index]]^=rhs[index];
        vector<uint8_t> states(groups,0);
        Word base_hash=0;int base_label=0;
        for(int var=0;var<variables;var++) if(base[var]) {states[group[var]]^=mask[var];base_hash^=hashes[var];base_label^=logical[var];}
        float base_cost=0;
        for(int grp=0;grp<groups;grp++) base_cost+=weights[grp][states[grp]];
        vector<std::array<float,4>> delta(groups);
        auto update_delta=[&]() {
            for(int grp=0;grp<groups;grp++) for(int state=0;state<4;state++) delta[grp][state]=weights[grp][states[grp]^state]-weights[grp][states[grp]];
        };
        update_delta();
        auto insert=[&](Word hash,int label,float cost){candidates.emplace(hash,Entry{label,cost});};
        insert(base_hash,base_label,base_cost);
        vector<vector<int>> flips;
        vector<float> costs;
        vector<int> labels;
        vector<Word> fliphash;
        vector<uint8_t> touched(groups,0);
        vector<int> active;
        for(int var:freevars) {
            vector<int> changed={var};
            for(int index=0;index<rank;index++) if((rows[index][var/64]>>(var%64))&1) changed.push_back(pivots[index]);
            int label=0;Word hash=0;
            active.clear();
            for(int item:changed) {
                int grp=group[item];
                if(!touched[grp]) active.push_back(grp);
                touched[grp]^=mask[item];
                label^=logical[item];hash^=hashes[item];
            }
            vector<int> flip;float cost=0;
            for(int grp:active) {flip.push_back(grp*4+touched[grp]);cost+=delta[grp][touched[grp]];touched[grp]=0;}
            insert(base_hash^hash,base_label^label,base_cost+cost);
            flips.push_back(std::move(flip));costs.push_back(cost);labels.push_back(label);fliphash.push_back(hash);
        }
        vector<int> ordervars(freevars.size());std::iota(ordervars.begin(),ordervars.end(),0);
        int count=std::min(order,int(ordervars.size()));
        for(int center=0;center<5;center++) {
            float improved_cost=base_cost;int improved_first=-1,improved_second=-1;
            if(center) {
                update_delta();
                for(int index=0;index<int(flips.size());index++) {
                    float cost=0;for(int code:flips[index]) cost+=delta[code/4][code%4];
                    costs[index]=cost;insert(base_hash^fliphash[index],base_label^labels[index],base_cost+cost);
                }
            }
            for(int index=0;index<int(flips.size());index++) if(base_cost+costs[index]<improved_cost-0.0001f) {
                improved_cost=base_cost+costs[index];improved_first=index;
            }
            std::partial_sort(ordervars.begin(),ordervars.begin()+count,ordervars.end(),[&](int left,int right){return costs[left]<costs[right];});
            for(int first_index=0;first_index<count;first_index++) {
                int left=ordervars[first_index];
                for(int code:flips[left]) touched[code/4]=code%4;
                for(int second=first_index+1;second<count;second++) {
                    int right=ordervars[second];float cost=base_cost+costs[left]+costs[right];
                    for(int code:flips[right]) {
                        int grp=code/4,bit=code%4,other=touched[grp];
                        if(other) cost+=delta[grp][bit^other]-delta[grp][bit]-delta[grp][other];
                    }
                    insert(base_hash^fliphash[left]^fliphash[right],base_label^labels[left]^labels[right],cost);
                    if(cost<improved_cost-0.0001f) {improved_cost=cost;improved_first=left;improved_second=right;}
                }
                for(int code:flips[left]) touched[code/4]=0;
            }
            if(improved_first<0) break;
            for(int index:{improved_first,improved_second}) if(index>=0) {
                for(int code:flips[index]) states[code/4]^=code%4;
                base_hash^=fliphash[index];base_label^=labels[index];
            }
            base_cost=improved_cost;
        }
    }
    int decode(const uint8_t* syndrome,float* output_scores,int iterations,int order,int ensemble,int early) {
        vector<float> posterior(variables);vector<uint8_t> hard(variables);
        std::unordered_map<Word,Entry> candidates;
        candidates.reserve(16384);
        for(int trial=0;trial<ensemble;trial++) {
            bool valid=belief(syndrome,posterior,hard,iterations,trial);
            if(valid && trial==0 && early) {
                int label=0;for(int var=0;var<variables;var++) if(hard[var]) label^=logical[var];
                for(int state=0;state<16;state++) output_scores[state]=state==label?0:100;
                return label;
            }
            osd(syndrome,posterior,hard,order,candidates);
        }
        float best=1e30;
        for(auto& entry:candidates) best=std::min(best,entry.second.cost);
        std::array<double,16> masses{};
        for(auto& entry:candidates) masses[entry.second.label]+=std::exp(best-entry.second.cost);
        for(int state=0;state<16;state++) output_scores[state]=best-std::log(masses[state]+1e-100);
        return std::max_element(masses.begin(),masses.end())-masses.begin();
    }
};
extern "C" {
void* create_group(int detectors,int variables,int groups,const uint8_t* matrix,const uint8_t* logical,const float* weights,const int* grouping) {
    return new Decoder(detectors,variables,groups,matrix,logical,weights,grouping);
}
void destroy_group(void* decoder) {delete static_cast<Decoder*>(decoder);}
void run_group(void* handle,int shots,const uint8_t* syndromes,uint8_t* output,float* scores,int iterations,int order,int ensemble,int early) {
    auto& decoder=*static_cast<Decoder*>(handle);
    for(int shot=0;shot<shots;shot++) {
        int label=decoder.decode(syndromes+shot*decoder.detectors,scores+shot*16,iterations,order,ensemble,early);
        for(int bit=0;bit<4;bit++) output[shot*4+bit]=(label>>bit)&1;
    }
}
}
