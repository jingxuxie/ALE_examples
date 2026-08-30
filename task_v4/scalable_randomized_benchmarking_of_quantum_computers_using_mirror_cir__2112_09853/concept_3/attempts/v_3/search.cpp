#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <vector>
using namespace std;
using Bits = uint64_t;
struct Layer { array<int,20> local{}; vector<pair<int,int>> cx; };
struct Circuit { vector<Layer> layers; };
struct Witness { Bits input; array<int,3> omit; int count; };
struct Error { Bits first, second, dual_first, dual_second; };
struct Compiled { array<Bits,40> images{},inverse{}; array<Error,400> errors{},inverse_errors{}; array<int,100> active{}; int count; };
int qubits, rounds, budget, target_single, target_double;
int robust_target=3;
int local_permutation[6][6][16];
int composition[6][6],inverse_word[6];
bool use_isolation=false;
bool global_scenarios=false;
bool fixed_geometry=false;
bool beam_proxy=false;
double fault_scale=8.0,temperature_start=5.0;
int required_single,required_double;
double required_mean_single,required_mean_double;
bool record_acceptance=false;
int edge_lookup[20][20];
vector<array<int,3>> scenario_pool;
double mean_single, mean_double;
Bits mask;
vector<pair<int,int>> edges;
mt19937_64 random_engine;
vector<Witness> witnesses;
const string words[] = {"I","H","S","HS","SH","HSH"};
int draw(int bound) { return random_engine()%bound; }
double uniform() { return (random_engine()>>11)*0x1.0p-53; }
int weight(Bits value) { return __builtin_popcountll((value | (value >> qubits)) & mask); }
Bits dual(Bits value) { return (value >> qubits) | ((value & mask) << qubits); }
Bits apply_error(Bits value, const Error &error) {
    return value ^ (-(Bits)__builtin_parityll(value & error.dual_second) & error.first)
                 ^ (-(Bits)__builtin_parityll(value & error.dual_first) & error.second);
}
Compiled compile(const Circuit &circuit) {
    Compiled result;
    for(int index=0;index<2*qubits;index++) result.images[index]=1ULL<<index;
    result.count=0;
    for(const auto &layer:circuit.layers) result.count+=layer.cx.size();
    int instance=result.count;
    for(int round=rounds-1;round>=0;round--) {
        const auto &layer=circuit.layers[round];
        for(int gate=(int)layer.cx.size()-1;gate>=0;gate--) {
            auto [control,target]=layer.cx[gate];
            Bits first=result.images[target],second=result.images[qubits+control];
            int identifier=round*edges.size()+edge_lookup[control][target];
            result.errors[identifier]={first,second,dual(first),dual(second)};
            result.active[--instance]=identifier;
            result.images[control]^=result.images[target];
            result.images[qubits+target]^=result.images[qubits+control];
        }
        for(int site=0;site<qubits;site++) {
            const string &word=words[layer.local[site]];
            for(int letter=(int)word.size()-1;letter>=0;letter--) {
                if(word[letter]=='H') swap(result.images[site],result.images[qubits+site]);
                if(word[letter]=='S') result.images[site]^=result.images[qubits+site];
            }
        }
    }
    for(int index=0;index<2*qubits;index++) result.inverse[index]=1ULL<<index;
    for(int round=0;round<rounds;round++) {
        const auto &layer=circuit.layers[round];
        for(int site=0;site<qubits;site++) for(char letter:words[layer.local[site]]) {
            if(letter=='H') swap(result.inverse[site],result.inverse[qubits+site]);
            if(letter=='S') result.inverse[site]^=result.inverse[qubits+site];
        }
        for(auto [control,target]:layer.cx) {
            Bits first=result.inverse[target],second=result.inverse[qubits+control];
            int identifier=round*edges.size()+edge_lookup[control][target];
            result.inverse_errors[identifier]={first,second,dual(first),dual(second)};
            result.inverse[control]^=result.inverse[target];
            result.inverse[qubits+target]^=result.inverse[qubits+control];
        }
    }
    return result;
}
array<Bits,40> inverse_images(const array<Bits,40> &images) {
    array<Bits,40> inverse{};
    for(int index=0;index<2*qubits;index++) {
        Bits value=images[index];
        int output=index<qubits?index+qubits:index-qubits;
        while(value) {
            int position=__builtin_ctzll(value); value&=value-1;
            int input=position<qubits?position+qubits:position-qubits;
            inverse[input]|=1ULL<<output;
        }
    }
    return inverse;
}
array<Bits,60> singles_of(const array<Bits,40> &images) {
    array<Bits,60> singles{};
    for(int site=0;site<qubits;site++) {
        singles[3*site]=images[site]; singles[3*site+1]=images[site]^images[qubits+site]; singles[3*site+2]=images[qubits+site];
    }
    return singles;
}
Bits input_of(int index) {
    int site=index/3, axis=index%3;
    return (axis!=2?1ULL<<site:0) | (axis!=0?1ULL<<(qubits+site):0);
}
double ideal_cost(const Compiled &compiled, bool verbose=false) {
    double cost=0;
    for(int direction=0;direction<2;direction++) {
        auto images=direction?compiled.inverse:compiled.images;
        auto singles=singles_of(images);
        int sum_single=0,sum_double=0,min_single=qubits,min_double=qubits;
        for(int index=0;index<3*qubits;index++) {
            int observed=weight(singles[index]);
            sum_single+=observed; min_single=min(min_single,observed);
            if(observed<target_single) cost+=3.0*(target_single-observed)*(target_single-observed);
            for(int other=3*(index/3+1);other<3*qubits;other++) {
                int pair_weight=weight(singles[index]^singles[other]);
                sum_double+=pair_weight; min_double=min(min_double,pair_weight);
                if(pair_weight<target_double) cost+=(target_double-pair_weight)*(target_double-pair_weight);
            }
        }
        double single_average=(double)sum_single/(3*qubits);
        double double_average=(double)sum_double/(9*qubits*(qubits-1)/2);
        cost+=30*pow(max(0.0,mean_single-single_average),2)+50*pow(max(0.0,mean_double-double_average),2);
        if(verbose) cerr<<(direction?" inverse ":" forward ")<<min_single<<"/"<<single_average<<" "<<min_double<<"/"<<double_average;
    }
    if(verbose) cerr<<" idealcost="<<cost;
    return cost;
}
Bits image_of(Bits input, const Compiled &compiled) {
    Bits value=0;
    while(input) { int index=__builtin_ctzll(input); input&=input-1; value^=compiled.images[index]; }
    return value;
}
double fault_cost(const Compiled &compiled) {
    double cost=0;
    for(const auto &witness:witnesses) {
        Bits support=witness.input;
        array<Bits,6> axes{};
        int sites=0;
        while(support) {
            int site=__builtin_ctzll(support); support&=support-1;
            Bits first=compiled.images[site],second=compiled.images[qubits+site];
            for(int index=0;index<witness.count;index++) {
                first=apply_error(first,compiled.errors[witness.omit[index]]);
                second=apply_error(second,compiled.errors[witness.omit[index]]);
            }
            axes[3*sites]=first; axes[3*sites+1]=first^second; axes[3*sites+2]=second; sites++;
        }
        for(int first=0;first<3;first++) for(int second=0;second<(sites==2?3:1);second++) {
            int observed=weight(axes[first]^(sites==2?axes[3+second]:0));
            if(observed<robust_target) cost+=8.0*(robust_target-observed)*(robust_target-observed);
        }
    }
    return cost;
}
double scenario_cost(const Compiled &compiled,double limit) {
    double cost=0;
    auto ideal_singles=singles_of(compiled.images);
    auto ideal_inverse=singles_of(compiled.inverse);
    for(int scenario=-compiled.count;scenario<(int)scenario_pool.size();scenario++) {
        array<int,3> omissions=scenario<0?array<int,3>{compiled.active[scenario+compiled.count],-1,-1}:scenario_pool[scenario];
        double scenario_scale=fault_scale*(beam_proxy?(scenario<0?100:omissions[2]<0?10:1):1);
        auto singles=ideal_singles;
        auto inverse_singles=ideal_inverse;
        for(int omitted:omissions) if(omitted>=0) {
            const auto &error=compiled.errors[omitted];
            if(!error.first) continue;
            for(int index=0;index<3*qubits;index++) singles[index]=apply_error(singles[index],error);
        }
        if(robust_target==2) {
            for(int index=2;index>=0;index--) if(omissions[index]>=0) {
                const auto &error=compiled.inverse_errors[omissions[index]];
                if(!error.first) continue;
                for(int site=0;site<3*qubits;site++) inverse_singles[site]=apply_error(inverse_singles[site],error);
            }
            for(int index=0;index<3*qubits;index++) {
                int observed=weight(singles[index]),reverse_weight=weight(inverse_singles[index]);
                if(observed<3) cost+=scenario_scale*(3-observed)*(3-observed);
                if(reverse_weight<3) cost+=scenario_scale*(3-reverse_weight)*(3-reverse_weight);
            }
            if(cost>limit) return cost;
            continue;
        }
        for(int index=0;index<3*qubits;index++) {
            int observed=weight(singles[index]);
            if(observed<robust_target) cost+=scenario_scale*(robust_target-observed)*(robust_target-observed);
            for(int other=3*(index/3+1);other<3*qubits;other++) {
                int pair_weight=weight(singles[index]^singles[other]);
                if(pair_weight<robust_target) cost+=scenario_scale*(robust_target-pair_weight)*(robust_target-pair_weight);
            }
        }
        if(cost>limit) return cost;
    }
    return cost;
}
double isolation_cost(const Circuit &circuit);
double total_cost(const Circuit &circuit,double limit=1e100) {
    auto compiled=compile(circuit);
    double cost=ideal_cost(compiled)+isolation_cost(circuit);
    if(cost>limit) return cost;
    return cost+(global_scenarios?scenario_cost(compiled,limit-cost):fault_cost(compiled));
}
void initialize_local_permutations() {
    for(int first=0;first<6;first++) for(int second=0;second<6;second++) for(int state=0;state<16;state++) {
        int output=state;
        for(int site=0;site<2;site++) for(char letter:words[site?second:first]) {
            if(letter=='H') { int difference=((output>>site)^(output>>(site+2)))&1; output^=(difference<<site)|(difference<<(site+2)); }
            if(letter=='S') output^=((output>>site)&1)<<(site+2);
        }
        local_permutation[first][second][state]=output;
    }
    for(int first=0;first<6;first++) for(int second=0;second<6;second++) for(int result=0;result<6;result++) {
        bool equal=true;
        for(int state:{1,4}) if(local_permutation[second][0][local_permutation[first][0][state]]!=local_permutation[result][0][state]) equal=false;
        if(equal) { composition[first][second]=result; if(result==0) inverse_word[first]=second; }
    }
}
double isolation_cost(const Circuit &circuit) {
    if(!use_isolation) return 0;
    int roles[12][20]{},partners[12][20];
    fill(&partners[0][0],&partners[0][0]+240,-1);
    for(int round=0;round<rounds;round++) for(auto [control,target]:circuit.layers[round].cx) {
        roles[round][control]=1; roles[round][target]=2;
        partners[round][control]=target; partners[round][target]=control;
    }
    double cost=0;
    for(auto [first,second]:edges) {
        array<int,16> distances{};
        for(int round=0;round<rounds;round++) {
            array<int,16> after_local{},after_cx{};
            const auto &layer=circuit.layers[round];
            auto &permutation=local_permutation[layer.local[first]][layer.local[second]];
            for(int state=1;state<16;state++) after_local[permutation[state]]=distances[state];
            if(partners[round][first]==second) {
                int control=roles[round][first]==1?0:1,target=1-control;
                for(int state=1;state<16;state++) {
                    int output=state^(((state>>control)&1)<<target)^(((state>>(target+2))&1)<<(control+2));
                    after_cx[state]=min(after_local[output],after_local[state]+1);
                }
            } else {
                for(int state=1;state<16;state++) {
                    int extra=0;
                    if(roles[round][first]) extra+=(state>>(roles[round][first]==1?0:2))&1;
                    if(roles[round][second]) extra+=(state>>(roles[round][second]==1?1:3))&1;
                    after_cx[state]=after_local[state]+extra;
                }
            }
            distances=after_cx;
        }
        for(int state=1;state<16;state++) {
            int output_weight=__builtin_popcount((state|(state>>2))&3);
            if(output_weight<robust_target && distances[state]<4) cost+=4.0*(4-distances[state])*(4-distances[state]);
        }
    }
    return cost;
}
vector<pair<int,int>> random_matching(int required=-1) {
    vector<pair<int,int>> best;
    for(int attempt=0;attempt<100;attempt++) {
        auto shuffled=edges; shuffle(shuffled.begin(),shuffled.end(),random_engine);
        vector<pair<int,int>> selected; unsigned occupied=0;
        for(auto [first,second]:shuffled) if(!(occupied & ((1U<<first)|(1U<<second)))) {
            occupied|=(1U<<first)|(1U<<second);
            if(draw(2)) swap(first,second);
            selected.emplace_back(first,second);
        }
        if(selected.size()>best.size()) best=selected;
        if(required>=0 && (int)best.size()>=required) { best.resize(required); return best; }
    }
    return best;
}
Circuit random_circuit() {
    Circuit circuit; circuit.layers.resize(rounds);
    int count=0;
    for(auto &layer:circuit.layers) {
        for(int site=0;site<qubits;site++) layer.local[site]=draw(6);
        layer.cx=random_matching(); count+=layer.cx.size();
    }
    while(count>budget) {
        auto &layer=circuit.layers[draw(rounds)];
        if(layer.cx.empty()) continue;
        layer.cx.erase(layer.cx.begin()+draw(layer.cx.size())); count--;
    }
    return circuit;
}
void mutate(Circuit &circuit) {
    int round=draw(rounds),kind=draw(fixed_geometry?76:100);
    auto &layer=circuit.layers[round];
    if(kind<65 && !layer.cx.empty()) {
        auto gate=layer.cx[draw(layer.cx.size())];
        int site=draw(2)?gate.first:gate.second;
        int change=draw(2)?1:(site==gate.first?4:3);
        layer.local[site]=composition[layer.local[site]][change];
        if(round+1<rounds) circuit.layers[round+1].local[site]=composition[inverse_word[change]][circuit.layers[round+1].local[site]];
    } else if(kind<76) {
        int site=draw(qubits); layer.local[site]=(layer.local[site]+1+draw(5))%6;
        if(kind<5) { site=draw(qubits); layer.local[site]=draw(6); }
    } else if(kind<82 && !layer.cx.empty()) {
        auto &gate=layer.cx[draw(layer.cx.size())]; swap(gate.first,gate.second);
    } else if(kind<89) {
        if(layer.cx.empty()) return;
        auto edge=edges[draw(edges.size())];
        int first_gate=-1,second_gate=-1,first_other=-1,second_other=-1;
        for(int index=0;index<(int)layer.cx.size();index++) {
            auto [control,target]=layer.cx[index];
            if(control==edge.first || target==edge.first) { first_gate=index; first_other=control^target^edge.first; }
            if(control==edge.second || target==edge.second) { second_gate=index; second_other=control^target^edge.second; }
        }
        if(first_gate>=0 && second_gate>=0 && first_gate!=second_gate && edge_lookup[first_other][second_other]>=0) {
            layer.cx[first_gate]=edge;
            layer.cx[second_gate]={first_other,second_other};
            if(draw(2)) swap(layer.cx[first_gate].first,layer.cx[first_gate].second);
            if(draw(2)) swap(layer.cx[second_gate].first,layer.cx[second_gate].second);
        } else if((first_gate>=0) != (second_gate>=0)) {
            layer.cx[max(first_gate,second_gate)]=edge;
        }
    } else if(kind<92) {
        layer.cx=random_matching(layer.cx.size());
    } else if(kind<96) {
        int other=draw(rounds); swap(layer.cx,circuit.layers[other].cx);
    } else {
        int other=draw(rounds);
        if(other==round || layer.cx.empty()) return;
        auto &destination=circuit.layers[other];
        unsigned occupied=0; for(auto [first,second]:destination.cx) occupied|=(1U<<first)|(1U<<second);
        vector<pair<int,int>> available;
        for(auto edge:edges) if(!(occupied & ((1U<<edge.first)|(1U<<edge.second)))) available.push_back(edge);
        if(available.empty()) return;
        layer.cx.erase(layer.cx.begin()+draw(layer.cx.size()));
        auto edge=available[draw(available.size())]; if(draw(2)) swap(edge.first,edge.second); destination.cx.push_back(edge);
    }
}
void save(const Circuit &circuit,const string &path) {
    ofstream output(path);
    output<<qubits<<" "<<rounds<<"\n";
    for(const auto &layer:circuit.layers) {
        for(int site=0;site<qubits;site++) output<<layer.local[site]<<" ";
        output<<layer.cx.size();
        for(auto [first,second]:layer.cx) output<<" "<<first<<" "<<second;
        output<<"\n";
    }
}
Circuit load(const string &path) {
    ifstream input(path); int width,depth; input>>width>>depth;
    if(!input || width!=qubits || depth!=rounds) throw runtime_error("bad circuit file");
    Circuit circuit; circuit.layers.resize(rounds);
    for(auto &layer:circuit.layers) {
        for(int site=0;site<qubits;site++) input>>layer.local[site];
        int count; input>>count;
        while(count--) { int first,second; input>>first>>second; layer.cx.emplace_back(first,second); }
    }
    return circuit;
}
struct Scan { long scenarios=0,failures=0,violations=0,minimal=0,points=0; int minimum=100; vector<Witness> found; vector<array<int,3>> patterns; };
const Compiled *active_scan;
bool collect_scan_patterns=false;
void add_failure(Bits input,const array<int,3> &omissions,int count,Scan &scan) {
    Bits ideal=image_of(input,*active_scan);
    int required=weight(input)==1?3:robust_target;
    for(int skip=0;skip<count;skip++) {
        Bits output=ideal;
        for(int index=0;index<count;index++) if(index!=skip) output=apply_error(output,active_scan->errors[omissions[index]]);
        if(weight(output)<required) return;
    }
    scan.minimal++;
    Witness witness{input,omissions,count};
    if(scan.found.size()<20000) scan.found.push_back(witness);
    else { long position=random_engine()%scan.minimal; if(position<20000) scan.found[position]=witness; }
}
void inspect(const array<Bits,60> &singles,const array<int,3> &omissions,int count,Scan &scan) {
    scan.scenarios++;
    bool failed=false;
    for(int index=0;index<3*qubits;index++) {
        int observed=weight(singles[index]); scan.minimum=min(scan.minimum,observed<=2?1:observed);
        if(observed<3) {
            failed=true; scan.violations++;
            scan.points+=(3-observed)*(3-observed);
            add_failure(input_of(index),omissions,count,scan);
        }
        for(int other=3*(index/3+1);other<3*qubits;other++) {
            int pair_weight=weight(singles[index]^singles[other]); scan.minimum=min(scan.minimum,pair_weight);
            if(pair_weight<robust_target) {
                failed=true; scan.violations++;
                scan.points+=(robust_target-pair_weight)*(robust_target-pair_weight);
                add_failure(input_of(index)^input_of(other),omissions,count,scan);
            }
        }
    }
    scan.failures+=failed;
    if(failed && count>1 && collect_scan_patterns) {
        auto sorted=omissions; sort(sorted.begin(),sorted.begin()+count); scan.patterns.push_back(sorted);
    }
}
array<Bits,60> transform(const array<Bits,60> &singles,const Error &error) {
    array<Bits,60> result;
    for(int index=0;index<3*qubits;index++) result[index]=apply_error(singles[index],error);
    return result;
}
Scan scan_faults(const Compiled &compiled,int maximum=3,bool collect=false) {
    active_scan=&compiled;
    collect_scan_patterns=collect;
    Scan scan; auto singles=singles_of(compiled.images);
    inspect(singles,{-1,-1,-1},0,scan);
    for(int first=0;first<compiled.count && maximum>=1;first++) {
        int first_id=compiled.active[first];
        auto once=transform(singles,compiled.errors[first_id]); inspect(once,{first_id,-1,-1},1,scan);
        for(int second=first+1;second<compiled.count && maximum>=2;second++) {
            int second_id=compiled.active[second];
            auto twice=transform(once,compiled.errors[second_id]); inspect(twice,{first_id,second_id,-1},2,scan);
            for(int third=second+1;third<compiled.count && maximum>=3;third++) {
                int third_id=compiled.active[third];
                auto thrice=transform(twice,compiled.errors[third_id]); inspect(thrice,{first_id,second_id,third_id},3,scan);
            }
        }
    }
    return scan;
}
void append_witnesses(const vector<Witness> &found) {
    for(auto witness:found) {
        sort(witness.omit.begin(),witness.omit.begin()+witness.count);
        if(global_scenarios) {
            if(witness.count>1 && find(scenario_pool.begin(),scenario_pool.end(),witness.omit)==scenario_pool.end()) scenario_pool.insert(scenario_pool.begin(),witness.omit);
            continue;
        }
        witness.input=(witness.input | (witness.input>>qubits)) & mask;
        bool duplicate=false;
        for(const auto &previous:witnesses) if(previous.input==witness.input && previous.omit==witness.omit && previous.count==witness.count) { duplicate=true; break; }
        if(!duplicate) witnesses.push_back(witness);
    }
}
void save_witnesses(const string &path) {
    ofstream output(path);
    if(global_scenarios) {
        for(auto omissions:scenario_pool) output<<omissions[0]<<" "<<omissions[1]<<" "<<omissions[2]<<"\n";
        return;
    }
    for(auto witness:witnesses) output<<witness.input<<" "<<witness.count<<" "<<witness.omit[0]<<" "<<witness.omit[1]<<" "<<witness.omit[2]<<"\n";
}
void load_witnesses(const string &path) {
    ifstream input(path); Witness witness;
    if(global_scenarios) {
        array<int,3> omissions;
        while(input>>omissions[0]>>omissions[1]>>omissions[2]) scenario_pool.push_back(omissions);
        return;
    }
    while(input>>witness.input>>witness.count>>witness.omit[0]>>witness.omit[1]>>witness.omit[2]) {
        witness.input=(witness.input | (witness.input>>qubits)) & mask;
        witnesses.push_back(witness);
    }
}
struct ExactSingles { long cost=0; vector<array<int,3>> patterns; array<long,120> input_cost{}; double soft=0; };
ExactSingles exact_singles(const Compiled &compiled,bool collect=false) {
    ExactSingles result;
    int current_direction=0;
    auto inspect_singles=[&](const array<Bits,60> &singles,array<int,3> omissions) {
        bool failed=false;
        for(int index=0;index<3*qubits;index++) {
            int observed=weight(singles[index]);
            if(observed<3) { result.cost+=(3-observed)*(3-observed); result.input_cost[current_direction*3*qubits+index]+=(3-observed)*(3-observed); failed=true; }
            else if(observed==3) result.soft+=1;
            else if(observed==4) result.soft+=0.05;
            else if(observed==5) result.soft+=0.002;
        }
        if(failed && collect && omissions[1]>=0) {
            int count=omissions[2]>=0?3:2;
            sort(omissions.begin(),omissions.begin()+count);
            result.patterns.push_back(omissions);
        }
    };
    for(int direction=0;direction<2;direction++) {
        current_direction=direction;
        auto singles=singles_of(direction?compiled.inverse:compiled.images);
        const auto &errors=direction?compiled.inverse_errors:compiled.errors;
        auto identifier=[&](int position){return compiled.active[direction?compiled.count-1-position:position];};
        inspect_singles(singles,{-1,-1,-1});
        for(int first=0;first<compiled.count;first++) {
            int first_id=identifier(first);
            auto once=transform(singles,errors[first_id]); inspect_singles(once,{first_id,-1,-1});
            for(int second=first+1;second<compiled.count;second++) {
                int second_id=identifier(second);
                auto twice=transform(once,errors[second_id]); inspect_singles(twice,{first_id,second_id,-1});
                for(int third=second+1;third<compiled.count;third++) {
                    int third_id=identifier(third);
                    auto thrice=transform(twice,errors[third_id]); inspect_singles(thrice,{first_id,second_id,third_id});
                }
            }
        }
    }
    if(collect) {
        sort(result.patterns.begin(),result.patterns.end());
        result.patterns.erase(unique(result.patterns.begin(),result.patterns.end()),result.patterns.end());
    }
    return result;
}
ExactSingles exact_singles_fast(const Compiled &compiled,bool collect=false) {
    constexpr int table_size=1<<19;
    static vector<Bits> keys(table_size);
    static vector<int> stamps(table_size),sums(table_size),heads(table_size);
    static int epoch=0;
    struct Node { int gate,next; };
    vector<Node> nodes; if(collect) nodes.reserve(180000);
    vector<pair<Bits,int>> low;
    for(int first=0;first<3*qubits;first++) {
        low.emplace_back(input_of(first),4);
        for(int second=3*(first/3+1);second<3*qubits;second++) low.emplace_back(input_of(first)^input_of(second),1);
    }
    auto bucket=[&](Bits value) {
        Bits hashed=(value^(value>>23))*0x9e3779b97f4a7c15ULL;
        int position=hashed>>(64-19);
        while(stamps[position]==epoch && keys[position]!=value) position=(position+1)&(table_size-1);
        return position;
    };
    ExactSingles result;
    for(int direction=0;direction<2;direction++) {
        epoch++; nodes.clear();
        auto singles=singles_of(direction?compiled.inverse:compiled.images);
        const auto &errors=direction?compiled.inverse_errors:compiled.errors;
        auto identifier=[&](int position){return compiled.active[direction?compiled.count-1-position:position];};
        array<array<Bits,60>,100> once;
        for(int axis=0;axis<3*qubits;axis++) {
            int observed=weight(singles[axis]); if(observed<3) result.cost+=(3-observed)*(3-observed);
        }
        for(int first=0;first<compiled.count;first++) {
            once[first]=transform(singles,errors[identifier(first)]);
            for(int axis=0;axis<3*qubits;axis++) { int observed=weight(once[first][axis]); if(observed<3) result.cost+=(3-observed)*(3-observed); }
        }
        for(int second=compiled.count-1;second>=1;second--) {
            if(second+1<compiled.count) {
                int third=second+1;
                const auto &error=errors[identifier(third)];
                for(auto [value,penalty]:low) {
                    Bits transformed=apply_error(value,error);
                    int position=bucket(transformed);
                    if(stamps[position]!=epoch) { stamps[position]=epoch; keys[position]=transformed; sums[position]=0; heads[position]=-1; }
                    sums[position]+=penalty;
                    if(collect) { nodes.push_back({third,heads[position]}); heads[position]=nodes.size()-1; }
                }
            }
            const auto &error=errors[identifier(second)];
            for(int first=0;first<second;first++) for(int axis=0;axis<3*qubits;axis++) {
                Bits value=apply_error(once[first][axis],error);
                int observed=weight(value);
                if(observed==3) result.soft+=1;
                else if(observed==4) result.soft+=0.02;
                if(observed<3) {
                    result.cost+=(3-observed)*(3-observed);
                    if(collect) { array<int,3> pattern{identifier(first),identifier(second),-1}; sort(pattern.begin(),pattern.begin()+2); result.patterns.push_back(pattern); }
                }
                int position=bucket(value);
                if(stamps[position]!=epoch) continue;
                result.cost+=sums[position];
                if(collect) for(int node=heads[position];node>=0;node=nodes[node].next) {
                    array<int,3> pattern{identifier(first),identifier(second),identifier(nodes[node].gate)};
                    sort(pattern.begin(),pattern.end()); result.patterns.push_back(pattern);
                }
            }
        }
    }
    if(collect) { sort(result.patterns.begin(),result.patterns.end()); result.patterns.erase(unique(result.patterns.begin(),result.patterns.end()),result.patterns.end()); }
    return result;
}
ExactSingles exact_metric(const Compiled &compiled,bool collect=false) {
    if(robust_target==2) return exact_singles_fast(compiled,collect);
    auto scan=scan_faults(compiled,3,collect);
    return {scan.points,move(scan.patterns)};
}
double balance_cost(const Circuit &circuit) {
    array<int,20> degrees{};
    for(const auto &layer:circuit.layers) for(auto [control,target]:layer.cx) { degrees[control]++; degrees[target]++; }
    double cost=0;
    for(int site=0;site<qubits;site++) if(degrees[site]<8) cost+=4.0*(8-degrees[site])*(8-degrees[site]);
    return cost;
}
int faulted_site_minimum(const Compiled &compiled,const array<int,3> &omissions,int direction,int site) {
    const auto &images=direction?compiled.inverse:compiled.images;
    const auto &errors=direction?compiled.inverse_errors:compiled.errors;
    Bits first=images[site],second=images[qubits+site];
    for(int position=0;position<3;position++) {
        int omitted=omissions[direction?2-position:position];
        if(omitted<0) continue;
        first=apply_error(first,errors[omitted]); second=apply_error(second,errors[omitted]);
    }
    return min({weight(first),weight(second),weight(first^second)});
}
void mutate_near(Circuit &circuit,int site,int direction) {
    vector<int> neighbors;
    for(auto [first,second]:edges) { if(first==site) neighbors.push_back(second); if(second==site) neighbors.push_back(first); }
    int neighbor=neighbors[draw(neighbors.size())];
    int round=min(draw(rounds),draw(rounds)); if(direction) round=rounds-1-round;
    auto &layer=circuit.layers[round];
    int first_gate=-1,second_gate=-1,first_other=-1,second_other=-1;
    for(int index=0;index<(int)layer.cx.size();index++) {
        auto [control,target]=layer.cx[index];
        if(control==site || target==site) { first_gate=index; first_other=control^target^site; }
        if(control==neighbor || target==neighbor) { second_gate=index; second_other=control^target^neighbor; }
    }
    auto oriented=[&](int first,int second){return draw(2)?pair<int,int>{first,second}:pair<int,int>{second,first};};
    if(first_gate>=0 && second_gate>=0 && first_gate!=second_gate && edge_lookup[first_other][second_other]>=0) {
        layer.cx[first_gate]=oriented(site,neighbor); layer.cx[second_gate]=oriented(first_other,second_other);
    } else if((first_gate>=0)!=(second_gate>=0)) {
        layer.cx[max(first_gate,second_gate)]=oriented(site,neighbor);
    } else if(first_gate<0 && second_gate<0) {
        array<int,20> degrees{};
        for(const auto &existing:circuit.layers) for(auto [control,target]:existing.cx) { degrees[control]++; degrees[target]++; }
        int donor_round=-1,donor_index=-1,best_degree=-100;
        for(int trial=0;trial<12;trial++) {
            int selected_round=draw(rounds);
            auto &selected=circuit.layers[selected_round]; if(selected.cx.empty()) continue;
            int index=draw(selected.cx.size()); auto gate=selected.cx[index];
            int degree=degrees[gate.first]+degrees[gate.second];
            if(degree>best_degree && gate.first!=site && gate.second!=site) { best_degree=degree; donor_round=selected_round; donor_index=index; }
        }
        if(donor_round>=0) {
            auto &donor=circuit.layers[donor_round].cx; donor.erase(donor.begin()+donor_index);
            layer.cx.push_back(oriented(site,neighbor));
        }
    }
    if(draw(2)) {
        int change=1+draw(5);
        layer.local[site]=composition[layer.local[site]][change];
        if(round+1<rounds) circuit.layers[round+1].local[site]=composition[inverse_word[change]][circuit.layers[round+1].local[site]];
    }
}
void beam_search(Circuit current,const string &prefix,double seconds) {
    beam_proxy=true;
    auto started=chrono::steady_clock::now();
    auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
    auto exact=exact_metric(compile(current),true);
    double score=exact.cost+0.002*exact.soft+10*ideal_cost(compile(current))+balance_cost(current);
    double best_score=score;
    Circuit best=current;
    int iteration=0,stalled=0;
    cerr<<"BEAM initial="<<score<<" faults="<<exact.cost<<" patterns="<<exact.patterns.size()<<" seconds="<<elapsed()<<"\n";
    while(elapsed()<seconds) {
        scenario_pool=exact.patterns;
        if(scenario_pool.size()>1200) { shuffle(scenario_pool.begin(),scenario_pool.end(),random_engine); scenario_pool.resize(1200); }
        auto base=compile(current);
        array<int,3> focus_pattern{-1,-1,-1};
        int focus_direction=0,focus_site=-1;
        if(robust_target==2 && !exact.patterns.empty()) {
            focus_pattern=exact.patterns[draw(exact.patterns.size())];
            vector<pair<int,int>> vulnerable;
            for(int direction=0;direction<2;direction++) for(int site=0;site<qubits;site++) if(faulted_site_minimum(base,focus_pattern,direction,site)<3) vulnerable.emplace_back(direction,site);
            if(!vulnerable.empty()) { auto chosen=vulnerable[draw(vulnerable.size())]; focus_direction=chosen.first; focus_site=chosen.second; }
        }
        if(exact.patterns.size()<600) for(const auto &pattern:exact.patterns) {
            if(pattern[2]>=0) for(int removed=0;removed<3;removed++) {
                array<int,3> pair{-1,-1,-1}; int position=0;
                for(int index=0;index<3;index++) if(index!=removed) pair[position++]=pattern[index];
                scenario_pool.push_back(pair);
            }
            for(int sample=0;sample<6;sample++) {
                auto neighbor=pattern;
                int count=pattern[2]>=0?3:2,index=draw(count),old=pattern[index];
                auto old_edge=edges[old%edges.size()];
                for(int attempt=0;attempt<20;attempt++) {
                    int replacement=base.active[draw(base.count)];
                    auto new_edge=edges[replacement%edges.size()];
                    if(abs(old/(int)edges.size()-replacement/(int)edges.size())>3) continue;
                    if(old_edge.first!=new_edge.first && old_edge.first!=new_edge.second && old_edge.second!=new_edge.first && old_edge.second!=new_edge.second) continue;
                    if(find(neighbor.begin(),neighbor.end(),replacement)!=neighbor.end()) continue;
                    neighbor[index]=replacement; break;
                }
                sort(neighbor.begin(),neighbor.begin()+count); scenario_pool.push_back(neighbor);
            }
        }
        sort(scenario_pool.begin(),scenario_pool.end());
        scenario_pool.erase(unique(scenario_pool.begin(),scenario_pool.end()),scenario_pool.end());
        for(int sample=0;sample<96;sample++) {
            array<int,3> omissions;
            do { for(int index=0;index<3;index++) omissions[index]=base.active[draw(base.count)]; }
            while(omissions[0]==omissions[1] || omissions[0]==omissions[2] || omissions[1]==omissions[2]);
            sort(omissions.begin(),omissions.end()); scenario_pool.push_back(omissions);
        }
        struct Candidate { double proxy; Circuit circuit; };
        vector<Candidate> candidates;
        for(int trial=0;trial<(focus_site>=0?768:192);trial++) {
            Circuit candidate=current;
            int changes=stalled>15?1+draw(4):(draw(5)==0?2:1);
            if(focus_site>=0 && draw(3)==0) mutate_near(candidate,focus_site,focus_direction);
            else for(int change=0;change<changes;change++) mutate(candidate);
            auto compiled=compile(candidate);
            if(focus_site>=0 && faulted_site_minimum(compiled,focus_pattern,focus_direction,focus_site)<3) continue;
            double ideal=10*ideal_cost(compiled)+balance_cost(candidate);
            double proposal_temperature=max(1.0,min(8.0,score*0.05));
            double noise=proposal_temperature*log(-log(max(1e-100,uniform())));
            double limit=candidates.size()<6?1e100:candidates.back().proxy-noise;
            if(ideal>limit) continue;
            double proxy=ideal+scenario_cost(compiled,limit-ideal);
            if(proxy>limit) continue;
            bool duplicate=false;
            for(const auto &previous:candidates) {
                bool same=true;
                for(int round=0;round<rounds;round++) if(candidate.layers[round].local!=previous.circuit.layers[round].local || candidate.layers[round].cx!=previous.circuit.layers[round].cx) { same=false; break; }
                if(same) duplicate=true;
            }
            if(duplicate) continue;
            candidates.push_back({proxy+noise,move(candidate)});
            stable_sort(candidates.begin(),candidates.end(),[](const Candidate &first,const Candidate &second){return first.proxy<second.proxy;});
            if(candidates.size()>6) candidates.pop_back();
        }
        double chosen_score=1e100;
        long chosen_faults=0;
        Circuit chosen;
        vector<pair<double,Circuit>> alternatives;
        vector<long> alternative_faults;
        for(auto &candidate:candidates) {
            auto compiled=compile(candidate.circuit);
            auto checked=exact_metric(compiled);
            double candidate_score=checked.cost+0.002*checked.soft+10*ideal_cost(compiled)+balance_cost(candidate.circuit);
            alternatives.push_back({candidate_score,candidate.circuit}); alternative_faults.push_back(checked.cost);
            if(checked.cost==0) {
                save(candidate.circuit,prefix+".robust_done");
                if(robust_target==2 || ideal_cost(compiled)<1e-10) {
                    save(candidate.circuit,prefix+".done");
                    cerr<<"BEAM ROBUST DONE t="<<elapsed(); ideal_cost(compiled,true); cerr<<"\n";
                    return;
                }
            }
            if(candidate_score<chosen_score) { chosen_score=candidate_score; chosen_faults=checked.cost; chosen=candidate.circuit; }
        }
        if(focus_site<0 && chosen_score>=score-1e-10 && !alternatives.empty()) {
            int index=draw(alternatives.size()); chosen_score=alternatives[index].first; chosen=alternatives[index].second; chosen_faults=alternative_faults[index];
        }
        double temperature=max(1.0,min(8.0,score*0.05));
        if(chosen_score<=score || (focus_site>=0 && stalled>5 && chosen_score<1e99) || uniform()<exp((score-chosen_score)/temperature)) {
            current=chosen; score=chosen_score; exact=exact_metric(compile(current),true);
            if(score<best_score) {
                best=current; best_score=score; save(best,prefix+".best"); stalled=0;
                cerr<<"BEAM t="<<elapsed()<<" it="<<iteration<<" score="<<score<<" faults="<<chosen_faults<<" patterns="<<exact.patterns.size()<<"\n";
            } else stalled++;
        } else stalled++;
        iteration++;
        if(iteration%20==0) cerr<<"BEAM t="<<elapsed()<<" it="<<iteration<<" best="<<best_score<<" current="<<score<<" stalled="<<stalled<<"\n";
        if(stalled>300) { current=best; exact=exact_metric(compile(current),true); score=best_score; stalled=15; }
    }
    save(best,prefix+".best");
}
double one_fault_margin(const Compiled &compiled) {
    double cost=0;
    for(int direction=0;direction<2;direction++) {
        auto singles=singles_of(direction?compiled.inverse:compiled.images);
        const auto &errors=direction?compiled.inverse_errors:compiled.errors;
        for(int position=0;position<compiled.count;position++) {
            const auto &error=errors[compiled.active[position]];
            for(int axis=0;axis<3*qubits;axis++) {
                int observed=weight(apply_error(singles[axis],error));
                if(observed==3) cost+=0.2;
                else if(observed==4) cost+=0.02;
                else if(observed==5) cost+=0.001;
            }
        }
    }
    return cost;
}
double partial_ideal_cost(const Compiled &compiled) {
    int previous_single=target_single,previous_double=target_double;
    double previous_mean_single=mean_single,previous_mean_double=mean_double;
    target_single=(2*required_single+2)/3; target_double=(2*required_double+2)/3;
    mean_single=required_mean_single*2/3; mean_double=required_mean_double*2/3;
    double cost=ideal_cost(compiled);
    target_single=previous_single; target_double=previous_double;
    mean_single=previous_mean_single; mean_double=previous_mean_double;
    return cost;
}
double partial_fitness(const Compiled &compiled,const Circuit &circuit) {
    return 10*partial_ideal_cost(compiled)+0.05*ideal_cost(compiled)+balance_cost(circuit)+one_fault_margin(compiled);
}
void exact_anneal(Circuit current,const string &prefix,double seconds) {
    auto started=chrono::steady_clock::now();
    auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
    auto compiled=compile(current);
    auto initial_exact=exact_singles_fast(compiled);
    long faults=initial_exact.cost;
    double cost=faults+0.1*initial_exact.soft+partial_fitness(compiled,current);
    Circuit best=current; double best_cost=cost; long best_faults=faults;
    save(best,prefix+".best"); save(best,prefix+".robust");
    long iteration=0,accepted=0;
    cerr<<"EXACT initial="<<cost<<" faults="<<faults<<"\n";
    while(elapsed()<seconds) {
        double temperature=temperature_start*pow(0.015,(iteration%4000)/4000.0);
        double limit=record_acceptance?best_cost+2+temperature:cost-temperature*log(max(1e-100,uniform()));
        Circuit candidate=current;
        if(draw(6)==0) {
            array<int,20> degrees{};
            for(const auto &layer:current.layers) for(auto [control,target]:layer.cx) { degrees[control]++; degrees[target]++; }
            int site=draw(qubits);
            for(int trial=0;trial<3;trial++) { int another=draw(qubits); if(degrees[another]<degrees[site]) site=another; }
            mutate_near(candidate,site,draw(2));
        } else mutate(candidate);
        compiled=compile(candidate);
        double candidate_cost=partial_fitness(compiled,candidate);
        if(candidate_cost<=limit) {
            auto candidate_exact=exact_singles_fast(compiled);
            long candidate_faults=candidate_exact.cost;
            candidate_cost+=candidate_faults+0.1*candidate_exact.soft;
            if(candidate_faults==0 && partial_ideal_cost(compiled)<1e-10) {
                save(candidate,prefix+".done");
                cerr<<"EXACT DONE t="<<elapsed()<<" it="<<iteration; ideal_cost(compiled,true); cerr<<"\n";
                return;
            }
            if(candidate_faults<best_faults) { best_faults=candidate_faults; save(candidate,prefix+".robust"); }
            if(candidate_cost<=limit) {
                current=move(candidate); cost=candidate_cost; faults=candidate_faults; accepted++;
                if(cost<best_cost) {
                    best=current; best_cost=cost; save(best,prefix+".best");
                    cerr<<"EXACT t="<<elapsed()<<" it="<<iteration<<" best="<<best_cost<<" faults="<<faults<<"\n";
                }
            }
        }
        iteration++;
        if(iteration%1000==0) cerr<<"EXACT t="<<elapsed()<<" it="<<iteration<<" best="<<best_cost<<" current="<<cost<<" minfaults="<<best_faults<<" accepted="<<accepted<<"\n";
        if(iteration%4000==0) { current=best; cost=best_cost; }
    }
    save(best,prefix+".best");
}
vector<array<int,4>> regions;
int region_local[6][4][256],region_cx[4][4][256],region_weight[256];
void initialize_regions() {
    for(int state=0;state<256;state++) {
        region_weight[state]=__builtin_popcount((state|(state>>4))&15);
        for(int word=0;word<6;word++) for(int site=0;site<4;site++) {
            int output=state;
            for(char letter:words[word]) {
                if(letter=='H') { int difference=((output>>site)^(output>>(4+site)))&1; output^=(difference<<site)|(difference<<(4+site)); }
                if(letter=='S') output^=((output>>site)&1)<<(4+site);
            }
            region_local[word][site][state]=output;
        }
        for(int control=0;control<4;control++) for(int target=0;target<4;target++) region_cx[control][target][state]=state^(((state>>control)&1)<<target)^(((state>>(4+target))&1)<<(4+control));
    }
    for(int first=0;first<qubits;first++) for(int second=first+1;second<qubits;second++) for(int third=second+1;third<qubits;third++) for(int fourth=third+1;fourth<qubits;fourth++) {
        array<int,4> sites{first,second,third,fourth}; bool square=true;
        for(int site:sites) { int degree=0; for(int other:sites) degree+=edge_lookup[site][other]>=0; if(degree!=2) square=false; }
        if(square) regions.push_back(sites);
    }
}
double region_cost(const Circuit &circuit) {
    double cost=0;
    for(const auto &sites:regions) {
        array<int,20> lookup; lookup.fill(-1); for(int index=0;index<4;index++) lookup[sites[index]]=index;
        for(int direction=0;direction<2;direction++) {
            array<unsigned char,256> distances;
            for(int state=0;state<256;state++) distances[state]=region_weight[state]==1?0:4;
            auto apply_locals=[&](const Layer &layer) {
                for(int site=0;site<4;site++) {
                    int word=layer.local[sites[site]]; if(direction) word=inverse_word[word]; if(!word) continue;
                    array<unsigned char,256> after;
                    for(int state=0;state<256;state++) after[region_local[word][site][state]]=distances[state];
                    distances=after;
                }
            };
            auto apply_cx=[&](const Layer &layer) {
                for(auto [control,target]:layer.cx) {
                    int first=lookup[control],second=lookup[target];
                    if(first>=0 && second>=0) {
                        array<unsigned char,256> after;
                        for(int state=0;state<256;state++) after[state]=min((int)distances[region_cx[first][second][state]],(int)distances[state]+1);
                        distances=after;
                    } else if(first>=0 || second>=0) {
                        int affected=first>=0?first:second+4;
                        for(int state=0;state<256;state++) if(state>>affected&1) distances[state]=min(4,(int)distances[state]+1);
                    }
                }
            };
            for(int index=0;index<rounds;index++) {
                const auto &layer=circuit.layers[direction?rounds-1-index:index];
                if(direction) { apply_cx(layer); apply_locals(layer); }
                else { apply_locals(layer); apply_cx(layer); }
            }
            for(int state=1;state<256;state++) if(region_weight[state]<=2 && distances[state]<4) cost+=(4-distances[state])*(4-distances[state]);
        }
    }
    return cost;
}
void region_search(Circuit current,const string &prefix,double seconds) {
    initialize_regions();
    scenario_pool=exact_singles_fast(compile(current),true).patterns;
    auto started=chrono::steady_clock::now();
    auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
    auto objective=[&](const Circuit &circuit) { auto compiled=compile(circuit); return 2*region_cost(circuit)+partial_fitness(compiled,circuit)+scenario_cost(compiled,1e100); };
    double cost=objective(current),best_cost=cost;
    Circuit best=current; long best_faults=1000000000;
    long iteration=0;
    cerr<<"REGIONS "<<regions.size()<<" initial="<<cost<<"\n";
    while(elapsed()<seconds) {
        double temperature=5*pow(0.02,(iteration%20000)/20000.0);
        Circuit candidate=current; mutate(candidate);
        double candidate_cost=objective(candidate);
        if(candidate_cost<cost || uniform()<exp((cost-candidate_cost)/temperature)) { current=move(candidate); cost=candidate_cost; }
        if(cost<best_cost) { best=current; best_cost=cost; save(best,prefix+".best"); }
        iteration++;
        if(iteration%5000==0) {
            auto compiled=compile(best); auto exact=exact_singles_fast(compiled,true);
            cerr<<"REGIONS t="<<elapsed()<<" it="<<iteration<<" cost="<<best_cost<<" region="<<region_cost(best)<<" faults="<<exact.cost<<" pool="<<scenario_pool.size()<<"\n";
            if(exact.cost<best_faults) { best_faults=exact.cost; save(best,prefix+".robust"); }
            if(exact.cost==0 && partial_ideal_cost(compiled)<1e-10) { save(best,prefix+".done"); return; }
            {
                shuffle(exact.patterns.begin(),exact.patterns.end(),random_engine);
                if(exact.patterns.size()>64) exact.patterns.resize(64);
                for(auto pattern:exact.patterns) if(find(scenario_pool.begin(),scenario_pool.end(),pattern)==scenario_pool.end()) scenario_pool.insert(scenario_pool.begin(),pattern);
                current=best; cost=best_cost=objective(best);
            }
        }
        if(iteration%20000==0) { current=best; cost=best_cost; }
    }
    save(best,prefix+".best");
}
int main(int argc,char **argv) {
    if(argc<5) { cerr<<"search FAMILY SEED SECONDS PREFIX [LOAD] [MODE]\n"; return 1; }
    string family=argv[1],prefix=argv[4],mode=argc>6?argv[6]:"search";
    robust_target=argc>7?stoi(argv[7]):3;
    use_isolation=argc>8 && string(argv[8])=="isolate";
    global_scenarios=argc>8 && string(argv[8]).find("global")==0;
    fixed_geometry=argc>8 && (string(argv[8])=="globalfixed" || string(argv[8])=="fixed");
    fault_scale=argc>9?stod(argv[9]):8.0;
    temperature_start=argc>10?stod(argv[10]):5.0;
    initialize_local_permutations();
    random_engine.seed(stoull(argv[2])); double seconds=stod(argv[3]);
    ifstream spec(family+".spec"); int edge_count,single_milli,double_milli;
    spec>>qubits>>rounds>>budget>>edge_count>>target_single>>target_double>>single_milli>>double_milli;
    mean_single=single_milli/1000.0; mean_double=double_milli/1000.0; mask=(1ULL<<qubits)-1;
    required_single=target_single; required_double=target_double; required_mean_single=mean_single; required_mean_double=mean_double;
    if(argc>11) {
        double scale=stod(argv[11]);
        target_single=ceil(target_single*scale); target_double=ceil(target_double*scale);
        mean_single*=scale; mean_double*=scale;
    }
    fill(&edge_lookup[0][0],&edge_lookup[0][0]+400,-1);
    for(int index=0;index<edge_count;index++) { int first,second; spec>>first>>second; edges.emplace_back(first,second); edge_lookup[first][second]=edge_lookup[second][first]=index; }
    Circuit current=argc>5 && string(argv[5])!="-"?load(argv[5]):random_circuit();
    if(mode=="regions") { region_search(current,prefix,seconds); return 0; }
    if(mode=="exact" || mode=="record") { record_acceptance=mode=="record"; exact_anneal(current,prefix,seconds); return 0; }
    if(mode=="mitmtest") {
        auto compiled=compile(current);
        auto started=chrono::steady_clock::now(); auto slow=exact_singles(compiled,true);
        auto middle=chrono::steady_clock::now(); auto fast=exact_singles_fast(compiled,true);
        auto ended=chrono::steady_clock::now();
        cerr<<"slow="<<slow.cost<<" fast="<<fast.cost<<" patterns="<<slow.patterns.size()<<"/"<<fast.patterns.size()<<" seconds="<<chrono::duration<double>(middle-started).count()<<"/"<<chrono::duration<double>(ended-middle).count()<<"\n";
        if(slow.cost!=fast.cost || slow.patterns!=fast.patterns) throw runtime_error("MITM mismatch");
        return 0;
    }
    if(mode=="diagnose") {
        auto exact=exact_singles(compile(current));
        cerr<<"exact="<<exact.cost<<"\n";
        for(int direction=0;direction<2;direction++) for(int site=0;site<qubits;site++) {
            long subtotal=0;
            for(int axis=0;axis<3;axis++) subtotal+=exact.input_cost[direction*3*qubits+3*site+axis];
            if(subtotal) cerr<<(direction?"inverse":"forward")<<" site="<<site<<" cost="<<subtotal<<"\n";
        }
        return 0;
    }
    if(mode=="beam") { beam_search(current,prefix,seconds); return 0; }
    if(mode=="selftest") {
        auto compiled=compile(current);
        if(compiled.inverse!=inverse_images(compiled.images)) throw runtime_error("inverse mismatch");
        for(int trial=0;trial<1000;trial++) {
            vector<int> omissions;
            while((int)omissions.size()<trial%4) {
                int identifier=compiled.active[draw(compiled.count)];
                if(find(omissions.begin(),omissions.end(),identifier)==omissions.end()) omissions.push_back(identifier);
            }
            sort(omissions.begin(),omissions.end());
            Circuit faulted=current;
            for(int round=0;round<rounds;round++) {
                auto &gates=faulted.layers[round].cx;
                gates.erase(remove_if(gates.begin(),gates.end(),[&](auto gate){return find(omissions.begin(),omissions.end(),round*(int)edges.size()+edge_lookup[gate.first][gate.second])!=omissions.end();}),gates.end());
            }
            auto expected=compile(faulted);
            if(expected.inverse!=inverse_images(expected.images)) throw runtime_error("fault inverse mismatch");
            for(int index=0;index<2*qubits;index++) {
                Bits forward=compiled.images[index],inverse=compiled.inverse[index];
                for(int omitted:omissions) forward=apply_error(forward,compiled.errors[omitted]);
                for(auto omitted=omissions.rbegin();omitted!=omissions.rend();omitted++) inverse=apply_error(inverse,compiled.inverse_errors[*omitted]);
                if(forward!=expected.images[index] || inverse!=expected.inverse[index]) throw runtime_error("omission mismatch");
            }
        }
        cerr<<"1000 exact forward/inverse omission-map checks passed\n";
        return 0;
    }
    if(mode=="check") {
        auto compiled=compile(current); ideal_cost(compiled,true); auto scan=scan_faults(compiled);
        cerr<<" faults minimum="<<scan.minimum<<" failures="<<scan.failures<<" violations="<<scan.violations<<" scenarios="<<scan.scenarios<<"\n";
        append_witnesses(scan.found); save_witnesses(prefix+".witnesses"); return 0;
    }
    load_witnesses(prefix+".witnesses");
    auto started=chrono::steady_clock::now();
    auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
    double cost=total_cost(current);
    Circuit best=current; double best_cost=cost; double best_quality=1e100;
    long iteration=0,last_improvement=0,last_scan=-100000;
    int cycle_length=60000;
    bool ideal_only=mode=="ideal";
    while(elapsed()<seconds) {
        double progress=(iteration%cycle_length)/(double)cycle_length;
            double temperature=temperature_start*pow(0.01,progress);
        Circuit candidate=current; mutate(candidate);
        double acceptance_limit=cost-temperature*log(max(uniform(),1e-100));
        double candidate_cost=total_cost(candidate,acceptance_limit);
        if(candidate_cost<=acceptance_limit) { current=move(candidate); cost=candidate_cost; }
        iteration++;
        if(cost<best_cost-1e-10) {
            best=current; best_cost=cost; last_improvement=iteration;
            save(best,prefix+".best");
            if(best_cost<1e-10 || iteration%1000==0) cerr<<family<<" t="<<elapsed()<<" it="<<iteration<<" best="<<best_cost<<" pool="<<(global_scenarios?scenario_pool.size():witnesses.size())<<"\n";
        }
        bool ready_to_scan=(best_cost<1e-10 || (best_cost<=20 && iteration%2000==0)) && (iteration-last_scan>500 || last_scan<0);
        if(ready_to_scan && global_scenarios) ready_to_scan=scenario_cost(compile(best),1e100)<1e-10;
        if(ready_to_scan) {
            if(ideal_only && best_cost>1e-10) continue;
            if(ideal_only) { save(best,prefix+".best"); cerr<<"IDEAL DONE "<<family; ideal_cost(compile(best),true); cerr<<"\n"; break; }
            auto compiled_best=compile(best); auto scan=scan_faults(compiled_best); last_scan=iteration;
            cerr<<family<<" t="<<elapsed()<<" scan min="<<scan.minimum<<" failures="<<scan.failures<<" violations="<<scan.violations<<" minimal="<<scan.minimal<<" pool="<<(global_scenarios?scenario_pool.size():witnesses.size())<<"\n";
            double quality=scan.violations;
            if(quality<best_quality) { best_quality=quality; save(best,prefix+".robust"); }
            if(!scan.failures && (robust_target==2 || ideal_cost(compiled_best)<1e-10)) { save(best,prefix+".done"); cerr<<"DONE "<<family<<"\n"; break; }
            append_witnesses(scan.found); save_witnesses(prefix+".witnesses");
            current=best; cost=total_cost(best); best_cost=cost;
            last_improvement=iteration;
        }
        if(iteration%cycle_length==0) {
            cerr<<family<<" t="<<elapsed()<<" it="<<iteration<<" best="<<best_cost<<" current="<<cost<<" pool="<<(global_scenarios?scenario_pool.size():witnesses.size())<<"\n";
            current=best; cost=best_cost;
            if(iteration-last_improvement>3*cycle_length) {
                for(int count=0;count<20;count++) mutate(current);
                cost=total_cost(current);
            }
        }
    }
    save(best,prefix+".best");
    cerr<<family<<" END t="<<elapsed()<<" it="<<iteration<<" best="<<best_cost; ideal_cost(compile(best),true); cerr<<" pool="<<witnesses.size()<<"\n";
}
