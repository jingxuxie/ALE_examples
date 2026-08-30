#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>
using std::vector;
using Word=uint64_t;
struct Cluster {
    int variables,words;
    vector<float> prior;
    vector<vector<int>> moves;
    Cluster(int nv,int nm,const double* prob,const int* offsets,const int* indexes):variables(nv),words((nv+63)/64),prior(nv),moves(nm) {
        for(int var=0;var<nv;var++) prior[var]=std::log((1-prob[var])/prob[var]);
        for(int index=0;index<nm;index++) moves[index].assign(indexes+offsets[index],indexes+offsets[index+1]);
    }
    float partition(const uint8_t* state,float cost,float cutoff,int maxrank) {
        vector<std::pair<float,int>> sorted;
        for(int index=0;index<int(moves.size());index++) {
            float delta=0;for(int var:moves[index]) delta+=state[var]?-prior[var]:prior[var];
            if(delta<cutoff) sorted.emplace_back(delta,index);
        }
        std::sort(sorted.begin(),sorted.end());
        vector<int> parent(variables),ranks(variables,0);
        std::iota(parent.begin(),parent.end(),0);
        auto root=[&](int var) {while(parent[var]!=var) {parent[var]=parent[parent[var]];var=parent[var];}return var;};
        vector<vector<Word>> basis(variables);
        vector<int> selected;
        vector<Word> row(words);
        for(auto item:sorted) {
            const auto& move=moves[item.second];
            vector<int> roots;
            for(int var:move) roots.push_back(root(var));
            std::sort(roots.begin(),roots.end());roots.erase(std::unique(roots.begin(),roots.end()),roots.end());
            int total=1;for(int component:roots) total+=ranks[component];
            if(total>maxrank) continue;
            std::fill(row.begin(),row.end(),0);
            for(int var:move) row[var/64]^=Word(1)<<(var%64);
            int pivot=-1;
            for(int block=words-1;block>=0;block--) {
                while(row[block]) {
                    int bit=63-__builtin_clzll(row[block]);
                    int position=block*64+bit;
                    if(basis[position].empty()) {pivot=position;break;}
                    for(int word=0;word<=block;word++) row[word]^=basis[position][word];
                }
                if(pivot>=0) break;
            }
            if(pivot<0) continue;
            basis[pivot]=row;selected.push_back(item.second);
            for(int component:roots) parent[component]=roots[0];
            ranks[roots[0]]=total;
        }
        vector<vector<int>> components(variables);
        for(int index:selected) components[root(moves[index][0])].push_back(index);
        vector<uint8_t> current(state,state+variables);
        double entropy=0;
        for(const auto& component:components) if(!component.empty()) {
            double delta=0,mass=1;
            int count=1<<component.size();
            for(int step=1;step<count;step++) {
                int chosen=component[__builtin_ctz(unsigned(step))];
                for(int var:moves[chosen]) {delta+=current[var]?-prior[var]:prior[var];current[var]^=1;}
                mass+=std::exp(-delta);
            }
            entropy+=std::log(mass);
            for(int index:component) for(int var:moves[index]) current[var]=state[var];
        }
        return cost-entropy;
    }
};
extern "C" {
void* create_cluster(int nv,int nm,const double* probabilities,const int* offsets,const int* indexes) {return new Cluster(nv,nm,probabilities,offsets,indexes);}
void destroy_cluster(void* handle) {delete static_cast<Cluster*>(handle);}
void run_cluster(void* handle,int shots,const uint8_t* states,const float* costs,float* output,float cutoff,int maxrank) {
    auto& cluster=*static_cast<Cluster*>(handle);
    for(int shot=0;shot<shots;shot++) {
        float best=*std::min_element(costs+shot*16,costs+(shot+1)*16);
        for(int label=0;label<16;label++) {
            float cost=costs[shot*16+label];
            output[shot*16+label]=cost<best+18?cluster.partition(states+(shot*16+label)*cluster.variables,cost,cutoff,maxrank):cost;
        }
    }
}
}
