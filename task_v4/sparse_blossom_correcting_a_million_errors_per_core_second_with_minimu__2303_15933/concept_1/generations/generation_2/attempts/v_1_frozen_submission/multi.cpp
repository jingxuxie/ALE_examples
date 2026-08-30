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
namespace Original {
#include "original.cpp"
}
struct Entry {int label; float cost;};
struct Decoder {
    int detectors, variables, groups, words;
    vector<vector<int>> checks;
    vector<int> edge_var, logical, group, mask, mate, first;
    vector<std::array<float,4>> weights;
    vector<std::array<float,4>> channel_weights;
    int basis;
    vector<vector<int>> osd_checks;
    float gap_stop=4;
    std::array<vector<float>,3> bp_post;
    std::array<vector<uint8_t>,3> bp_hard;
    vector<vector<Word>> original;
    vector<float> table, soft;
    vector<Word> hashes;
    Decoder(int nd, int nv, int ng, const uint8_t* matrix, const uint8_t* bp_matrix, const uint8_t* obs, const float* costs, const int* grouping,int choice)
        : detectors(nd), variables(nv), groups(ng), words((nv+63)/64), checks(nd), logical(nv), group(grouping,grouping+nv), mask(nv,1), mate(nv,-1), first(ng,-1), weights(ng), channel_weights(ng),basis(choice),osd_checks(nd), original(nd,vector<Word>(words)), table(32770),soft(32770),hashes(nv) {
        if(std::getenv("GAP")) gap_stop=std::atof(std::getenv("GAP"));
        for(int index=0;index<32770;index++) {
            double value=std::max(0.00001,index/2048.0);
            table[index]=-std::log(std::tanh(value/2));
            soft[index]=std::log1p(std::exp(-value));
        }
        for(int grp=0;grp<groups;grp++) for(int state=0;state<4;state++) weights[grp][state]=costs[4*grp+state];
        channel_weights=weights;
        for(int var=0;var<variables;var++) {
            int grp=group[var];
            if(first[grp]<0) first[grp]=var;
            else {mask[var]=2;mate[var]=first[grp];mate[first[grp]]=var;}
            Word hash=var+0x9e3779b97f4a7c15ULL;
            hash=(hash^(hash>>30))*0xbf58476d1ce4e5b9ULL;
            hash=(hash^(hash>>27))*0x94d049bb133111ebULL;
            hashes[var]=hash^(hash>>31);
            for(int bit=0;bit<4;bit++) logical[var]|=int(obs[bit*nv+var])<<bit;
            for(int check=0;check<nd;check++) if(bp_matrix[check*nv+var]) {
                checks[check].push_back(edge_var.size());edge_var.push_back(var);
            }
            for(int check=0;check<nd;check++) if(matrix[check*nv+var]) {original[check][var/64]|=Word(1)<<(var%64);osd_checks[check].push_back(var);}
        }
        for(int grp=0;grp<groups;grp++) if(mate[first[grp]]>=0 && basis) {
            auto cost=weights[grp];
            weights[grp]=basis==1?std::array<float,4>{cost[0],cost[2],cost[3],cost[1]}:std::array<float,4>{cost[0],cost[1],cost[3],cost[2]};
            int left=first[grp],right=mate[left];
            Word hash_x=hashes[left],hash_z=hashes[right];
            hashes[left]=basis==1?hash_z:hash_x;hashes[right]=hash_x^hash_z;
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
        std::array<vector<float>,3> all_average;
        vector<std::array<float,4>> joint_average(groups);
        auto channel=channel_weights;
        for(int choice=0;choice<3;choice++) {all_average[choice].assign(variables,0);bp_post[choice].resize(variables);}
        for(int choice=0;choice<3;choice++) bp_hard[choice].resize(variables);
        auto assign_hard=[&](bool averaged) {
            for(int grp=0;grp<groups;grp++) {
                int left=first[grp],right=mate[left];
                if(right<0) {
                    for(int choice=0;choice<3;choice++) bp_hard[choice][left]=bp_post[choice][left]<0;
                    continue;
                }
                auto cost=channel[grp];
                cost[1]+=sums[left];cost[2]+=sums[right];cost[3]+=sums[left]+sums[right];
                if(averaged) cost=joint_average[grp];
                else for(int state=0;state<4;state++) joint_average[grp][state]=0.8f*joint_average[grp][state]+0.2f*cost[state];
                int state=std::min_element(cost.begin(),cost.end())-cost.begin();
                int component_x=state&1,component_z=state>>1;
                bp_hard[0][left]=component_x;bp_hard[0][right]=component_z;
                bp_hard[1][left]=component_x^component_z;bp_hard[1][right]=component_x;
                bp_hard[2][left]=component_x^component_z;bp_hard[2][right]=component_z;
            }
            hard=bp_hard[basis];
        };
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
                float physical=post(var,sums,channel);
                bp_post[0][var]=physical;
                if(mate[var]>=0) {
                    int left=first[group[var]],right=mate[left];
                    const auto& cost=channel[group[var]];
                    float parity=logadd(0,-cost[3]-sums[left]-sums[right])-logadd(-cost[1]-sums[left],-cost[2]-sums[right]);
                    bp_post[1][var]=mask[var]==1?parity:post(left,sums,channel);
                    bp_post[2][var]=mask[var]==1?parity:post(right,sums,channel);
                } else bp_post[1][var]=bp_post[2][var]=physical;
                for(int choice=0;choice<3;choice++) all_average[choice][var]=0.8f*all_average[choice][var]+0.2f*bp_post[choice][var];
                if(basis && mate[var]>=0) {
                    if(mask[var]==1) {
                        const auto& cost=channel[group[var]];
                        float sum_x=sums[var],sum_z=sums[mate[var]];
                        posterior[var]=logadd(0,-cost[3]-sum_x-sum_z)-logadd(-cost[1]-sum_x,-cost[2]-sum_z);
                    } else posterior[var]=post(basis==1?mate[var]:var,sums,channel);
                } else posterior[var]=post(var,sums,channel);
                hard[var]=posterior[var]<0;
                average[var]=0.8f*average[var]+0.2f*posterior[var];
            }
            assign_hard(false);
            bool valid=true;
            for(int check=0;check<detectors;check++) {
                int parity=syndrome[check];
                for(int edge:checks[check]) {
                    int var=edge_var[edge];
                    if(basis && mate[var]>=0) {
                        int left=first[group[var]],right=mate[left];
                        parity^=mask[var]==(basis==1?1:2)?hard[right]:(hard[left]^hard[right]);
                    } else parity^=hard[var];
                }
                if(parity) {valid=false;break;}
            }
            if(valid) return true;
        }
        posterior=average;
        bp_post=std::move(all_average);
        assign_hard(true);
        return false;
    }
    void osd(const uint8_t* syndrome,const vector<float>& posterior,const vector<uint8_t>& hard,int order,std::unordered_map<Word,Entry>& candidates,float& best_cost) {
        vector<int> sorted(variables);std::iota(sorted.begin(),sorted.end(),0);
        std::stable_sort(sorted.begin(),sorted.end(),[&](int left,int right){return std::abs(posterior[left])<std::abs(posterior[right]);});
        auto rows=original;
        vector<uint8_t> rhs(syndrome,syndrome+detectors);
        for(int check=0;check<detectors;check++) {
            for(int var:osd_checks[check]) rhs[check]^=hard[var];
        }
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
        auto insert=[&](Word hash,int label,float cost){best_cost=std::min(best_cost,cost);if(cost<best_cost+16) candidates.emplace(hash,Entry{label,cost});};
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
        float best_cost=1e30;
        int previous=-1;
        for(int trial=0;trial<ensemble;trial++) {
            bool valid=belief(syndrome,posterior,hard,iterations,trial);
            if(valid && trial==0 && early) {
                int label=0;for(int var=0;var<variables;var++) if(hard[var]) label^=logical[var];
                for(int state=0;state<16;state++) output_scores[state]=state==label?0:100;
                return label;
            }
            osd(syndrome,posterior,hard,order,candidates,best_cost);
            if(gap_stop>0) {
                std::array<double,16> totals{};
                for(auto& entry:candidates) totals[entry.second.label]+=std::exp(best_cost-entry.second.cost);
                int label=std::max_element(totals.begin(),totals.end())-totals.begin();
                double second=0;
                for(int other=0;other<16;other++) if(other!=label) second=std::max(second,totals[other]);
                if(trial>=1 && label==previous && std::log(totals[label]/(second+1e-100))>gap_stop) break;
                previous=label;
            }
        }
        float best=1e30;
        for(auto& entry:candidates) best=std::min(best,entry.second.cost);
        std::array<double,16> masses{};
        for(auto& entry:candidates) masses[entry.second.label]+=std::exp(best-entry.second.cost);
        for(int state=0;state<16;state++) output_scores[state]=best-std::log(masses[state]+1e-100);
        return std::max_element(masses.begin(),masses.end())-masses.begin();
    }
};
struct Ensemble {
    std::array<Decoder*,3> decoders;
    int variables,detectors;
    float gap;
    Original::Decoder* original;
    vector<int> original_columns;
    int bp_mode=2;
    Ensemble(int nd,int nv,int ng,const uint8_t* matrices,const uint8_t* observations,const float* weights,const int* grouping,int full_variables,const uint8_t* full_matrix,const uint8_t* full_obs,const double* full_prob,const int* columns):variables(nv),detectors(nd),gap(4),original_columns(columns,columns+nv) {
        for(int basis=0;basis<3;basis++) decoders[basis]=new Decoder(nd,nv,ng,matrices+basis*nd*nv,matrices,observations+basis*4*nv,weights,grouping,basis);
        original=new Original::Decoder(nd,full_variables,full_matrix,full_obs,full_prob);
        if(std::getenv("GAP")) gap=std::atof(std::getenv("GAP"));
        if(std::getenv("BPMODE")) bp_mode=std::atoi(std::getenv("BPMODE"));
    }
    ~Ensemble() {for(auto decoder:decoders) delete decoder;delete original;}
    int decode(const uint8_t* syndrome,float* scores,int iterations,int order,int trials,int basis_mask) {
        std::unordered_map<Word,Entry> candidates;
        candidates.reserve(16384);
        vector<float> posterior(variables);vector<uint8_t> hard(variables);
        float best=1e30;
        int previous=-1;
        for(int trial=0;trial<trials;trial++) {
            bool valid;
            int valid_label=0;
            if(bp_mode==1 || (bp_mode==2 && trial%2==0)) {
                vector<float> full_post(original->variables);
                vector<uint8_t> full_hard(original->variables);
                valid=original->belief(syndrome,full_post,full_hard,iterations,bp_mode==2?trial/2:trial);
                if(valid) for(int var=0;var<original->variables;var++) if(full_hard[var]) valid_label^=original->logical[var];
                for(int basis=0;basis<3;basis++) decoders[0]->bp_post[basis].resize(variables);
                for(int basis=0;basis<3;basis++) decoders[0]->bp_hard[basis].resize(variables);
                auto parity=[&](float left,float right) {
                    float value=original->phi(original->phi(std::abs(left))+original->phi(std::abs(right)));
                    return (left<0)^(right<0)?-value:value;
                };
                for(int var=0;var<variables;var++) {
                    int source=original_columns[var];
                    auto& decoder=*decoders[0];
                    if(decoder.mate[var]<0) for(int basis=0;basis<3;basis++) decoder.bp_post[basis][var]=full_post[source];
                    else {
                        int left=decoder.first[decoder.group[var]],origin=original_columns[left];
                        float component_x=parity(full_post[origin],full_post[origin+2]);
                        float component_z=parity(full_post[origin+1],full_post[origin+2]);
                        float component_y=parity(full_post[origin],full_post[origin+1]);
                        decoder.bp_post[0][var]=decoder.mask[var]==1?component_x:component_z;
                        decoder.bp_post[1][var]=decoder.mask[var]==1?component_y:component_x;
                        decoder.bp_post[2][var]=decoder.mask[var]==1?component_y:component_z;
                    }
                }
                for(int basis=0;basis<3;basis++) for(int var=0;var<variables;var++) decoders[0]->bp_hard[basis][var]=decoders[0]->bp_post[basis][var]<0;
            } else {
                valid=decoders[0]->belief(syndrome,posterior,hard,iterations,bp_mode==2?trial/2:trial);
                if(valid) for(int var=0;var<variables;var++) if(hard[var]) valid_label^=decoders[0]->logical[var];
            }
            if(valid && trial==0) {
                int label=valid_label;
                for(int state=0;state<16;state++) scores[state]=state==label?0:100;
                return label;
            }
            for(int basis=0;basis<3;basis++) if(basis_mask&(1<<basis)) {
                const auto& reliability=decoders[0]->bp_post[basis];
                hard=decoders[0]->bp_hard[basis];
                decoders[basis]->osd(syndrome,reliability,hard,order,candidates,best);
            }
            std::array<double,16> masses{};
            for(auto& entry:candidates) masses[entry.second.label]+=std::exp(best-entry.second.cost);
            int label=std::max_element(masses.begin(),masses.end())-masses.begin();
            double second=0;
            for(int other=0;other<16;other++) if(other!=label) second=std::max(second,masses[other]);
            if(gap>0 && trial>=1 && label==previous && std::log(masses[label]/(second+1e-100))>gap) break;
            previous=label;
        }
        std::array<double,16> masses{};
        for(auto& entry:candidates) masses[entry.second.label]+=std::exp(best-entry.second.cost);
        for(int label=0;label<16;label++) scores[label]=best-std::log(masses[label]+1e-100);
        return std::max_element(masses.begin(),masses.end())-masses.begin();
    }
};
extern "C" {
void* create_multi(int nd,int nv,int ng,const uint8_t* matrices,const uint8_t* observations,const float* weights,const int* grouping,int full_variables,const uint8_t* full_matrix,const uint8_t* full_obs,const double* full_prob,const int* columns) {return new Ensemble(nd,nv,ng,matrices,observations,weights,grouping,full_variables,full_matrix,full_obs,full_prob,columns);}
void destroy_multi(void* handle) {delete static_cast<Ensemble*>(handle);}
void run_multi(void* handle,int shots,const uint8_t* syndromes,uint8_t* output,float* scores,int iterations,int order,int trials,int basis_mask) {
    auto& ensemble=*static_cast<Ensemble*>(handle);
    for(int shot=0;shot<shots;shot++) {
        int label=ensemble.decode(syndromes+shot*ensemble.detectors,scores+shot*16,iterations,order,trials,basis_mask);
        for(int bit=0;bit<4;bit++) output[shot*4+bit]=(label>>bit)&1;
    }
}
void* create_group(int detectors,int variables,int groups,const uint8_t* matrix,const uint8_t* bp_matrix,const uint8_t* logical,const float* weights,const int* grouping,int basis) {
    return new Decoder(detectors,variables,groups,matrix,bp_matrix,logical,weights,grouping,basis);
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
