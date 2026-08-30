#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <set>
#include <string>
#include <tuple>
#include <vector>

using Bits = uint64_t;
struct Gate { int control, target, edge; };
struct Layer { std::array<int,20> local{}; std::vector<Gate> gates; Bits ma=0,mb=0,mc=0,md=0; };
struct Circuit { std::vector<Layer> layers; };
struct Witness { Bits input; int first,second,third=-1; bool operator<(const Witness& other) const { return std::tie(input,first,second,third)<std::tie(other.input,other.first,other.second,other.third); } };
struct Metrics { double hard=0,soft=0,score=1; int mins[4]={99,99,99,99}; double means[4]={}; };
struct FaultResult { int minimum=99, failures=0, penalty=0, near=0, scenarios=0, failed_scenarios=0; std::vector<Witness> witnesses; };
int qubits,rounds,budget,single_target,double_target;
double single_mean,double_mean;
std::string family;
std::vector<std::pair<int,int>> edges;
Bits mask;
std::mt19937_64 rng;
std::vector<Witness> witnesses;
int random_int(int limit) { return rng()%limit; }
double uniform() { return (rng()>>11)*0x1.0p-53; }
int weight(Bits packed) { return __builtin_popcountll((packed|(packed>>qubits))&mask); }

void compile(Layer& layer) {
    layer.ma=layer.mb=layer.mc=layer.md=0;
    const int aa[6]={1,0,1,0,1,1},bb[6]={0,1,0,1,1,1},cc[6]={0,1,1,1,1,0},dd[6]={1,0,1,1,0,1};
    for(int site=0;site<qubits;site++) {
        int word=layer.local[site]; Bits bit=Bits(1)<<site;
        if(aa[word]) layer.ma|=bit;
        if(bb[word]) layer.mb|=bit;
        if(cc[word]) layer.mc|=bit;
        if(dd[word]) layer.md|=bit;
    }
}

void rows_for(const Circuit& circuit, Bits* rows, int first=-1,int second=-1,int third=-1) {
    for(int site=0;site<2*qubits;site++) rows[site]=Bits(1)<<site;
    for(int round=0;round<rounds;round++) {
        const Layer& layer=circuit.layers[round];
        for(int site=0;site<qubits;site++) {
            Bits xbits=rows[site],zbits=rows[site+qubits];
            switch(layer.local[site]) {
                case 1: rows[site]=zbits; rows[site+qubits]=xbits; break;
                case 2: rows[site+qubits]=xbits^zbits; break;
                case 3: rows[site]=zbits; rows[site+qubits]=xbits^zbits; break;
                case 4: rows[site]=xbits^zbits; rows[site+qubits]=xbits; break;
                case 5: rows[site]=xbits^zbits; break;
            }
        }
        for(const Gate& gate:layer.gates) {
            int identity=round*64+gate.edge;
            if(identity==first || identity==second || identity==third) continue;
            rows[gate.target]^=rows[gate.control];
            rows[qubits+gate.control]^=rows[qubits+gate.target];
        }
    }
}

void singles_for(const Bits* rows, Bits* singles, bool inverse) {
    Bits images[40]={};
    if(inverse) {
        for(int site=0;site<qubits;site++) {
            images[site]=((rows[qubits+site]&mask)<<qubits)|(rows[qubits+site]>>qubits);
            images[site+qubits]=((rows[site]&mask)<<qubits)|(rows[site]>>qubits);
        }
    } else {
        for(int site=0;site<2*qubits;site++) {
            Bits value=rows[site];
            while(value) { int column=__builtin_ctzll(value); images[column]|=Bits(1)<<site; value&=value-1; }
        }
    }
    for(int site=0;site<qubits;site++) {
        singles[3*site]=images[site]; singles[3*site+1]=images[site]^images[site+qubits]; singles[3*site+2]=images[site+qubits];
    }
}

Metrics measure(const Circuit& circuit) {
    Metrics metrics; Bits rows[40],singles[60]; rows_for(circuit,rows);
    for(int direction=0;direction<2;direction++) {
        singles_for(rows,singles,direction);
        int sums[2]={};
        for(int left=0;left<3*qubits;left++) {
            int observed=weight(singles[left]);
            metrics.mins[2*direction]=std::min(metrics.mins[2*direction],observed); sums[0]+=observed;
            int deficit=std::max(0,single_target-observed);
            metrics.hard+=5*deficit*deficit;
            metrics.soft+=0.06*std::pow(std::max(0,single_target+2-observed),2);
            for(int right=3*(left/3+1);right<3*qubits;right++) {
                observed=weight(singles[left]^singles[right]);
                metrics.mins[2*direction+1]=std::min(metrics.mins[2*direction+1],observed); sums[1]+=observed;
                deficit=std::max(0,double_target-observed);
                metrics.hard+=deficit*deficit;
                metrics.soft+=0.012*std::pow(std::max(0,double_target+1-observed),2);
            }
        }
        int counts[2]={3*qubits,9*qubits*(qubits-1)/2};
        for(int stratum=0;stratum<2;stratum++) {
            double target=stratum?double_mean:single_mean;
            double mean=double(sums[stratum])/counts[stratum]; metrics.means[2*direction+stratum]=mean;
            double deficit=std::max(0.0,target-mean);
            metrics.hard+=100*deficit*deficit;
            metrics.soft+=0.15*(qubits-mean);
            metrics.score=std::min(metrics.score,double(metrics.mins[2*direction+stratum])/(stratum?double_target:single_target));
            metrics.score=std::min(metrics.score,mean/target);
        }
    }
    return metrics;
}

int witness_weight(const Circuit& circuit,const Witness& witness) {
    Bits xbits=witness.input&mask,zbits=witness.input>>qubits;
    for(int round=0;round<rounds;round++) {
        const Layer& layer=circuit.layers[round];
        Bits updated=(xbits&layer.ma)^(zbits&layer.mb);
        zbits=(xbits&layer.mc)^(zbits&layer.md); xbits=updated;
        for(const Gate& gate:layer.gates) {
            int identity=round*64+gate.edge;
            if(identity==witness.first || identity==witness.second || identity==witness.third) continue;
            xbits^=((xbits>>gate.control)&1)<<gate.target;
            zbits^=((zbits>>gate.target)&1)<<gate.control;
        }
    }
    return __builtin_popcountll(xbits|zbits);
}

double cost(const Circuit& circuit,const Metrics& metrics) {
    double result=metrics.hard+metrics.soft;
    for(const Witness& witness:witnesses) {
        int deficit=std::max(0,3-witness_weight(circuit,witness));
        result+=8*deficit*deficit;
    }
    return result;
}

FaultResult faults_slow(const Circuit& circuit,bool collect=true,int limit=1000000000) {
    FaultResult result;
    std::vector<int> instances={-1};
    for(int round=0;round<rounds;round++) for(const Gate& gate:circuit.layers[round].gates) instances.push_back(round*64+gate.edge);
    Bits inputs[60];
    for(int site=0;site<qubits;site++) {
        inputs[3*site]=Bits(1)<<site; inputs[3*site+2]=Bits(1)<<(site+qubits);
        inputs[3*site+1]=inputs[3*site]^inputs[3*site+2];
    }
    for(int first=0;first<int(instances.size());first++)
    for(int second=first+(first!=0);second<int(instances.size());second++)
    for(int third=second+(second!=0);third<int(instances.size());third++) {
        Bits rows[40],singles[60];
        rows_for(circuit,rows,instances[first],instances[second],instances[third]); singles_for(rows,singles,false);
        bool failed=false; result.scenarios++;
        for(int left=0;left<3*qubits;left++) {
            int observed=weight(singles[left]); result.minimum=std::min(result.minimum,observed);
            result.near+=(observed==3);
            if(observed<3) {
                failed=true; result.minimum=1; result.failures++; result.penalty+=(3-observed)*(3-observed)+4;
                if(result.penalty>limit) return result;
                if(collect) result.witnesses.push_back({inputs[left],instances[first],instances[second],instances[third]});
            }
            for(int right=3*(left/3+1);right<3*qubits;right++) {
                observed=weight(singles[left]^singles[right]); result.minimum=std::min(result.minimum,observed);
                result.near+=(observed==3);
                if(observed<3) {
                    failed=true; result.failures++; result.penalty+=(3-observed)*(3-observed)+1;
                    if(result.penalty>limit) return result;
                    if(collect) result.witnesses.push_back({inputs[left]^inputs[right],instances[first],instances[second],instances[third]});
                }
            }
        }
        result.failed_scenarios+=failed;
    }
    return result;
}

struct ErrorMap { Bits first=0,second=0,first_dual=0,second_dual=0; };
Bits error_image(const ErrorMap& error,Bits image) {
    return image^((Bits(0)-Bits(__builtin_parityll(error.second_dual&image)))&error.first)
                ^((Bits(0)-Bits(__builtin_parityll(error.first_dual&image)))&error.second);
}

FaultResult faults_pair(const Circuit& circuit,bool collect=true,int limit=1000000000) {
    FaultResult result;
    std::vector<int> instances={-1};
    std::array<ErrorMap,768> errors;
    for(int round=0;round<rounds;round++) for(const Gate& gate:circuit.layers[round].gates) instances.push_back(round*64+gate.edge);
    Bits images[40],inputs[60],ideal[60];
    for(int site=0;site<2*qubits;site++) images[site]=Bits(1)<<site;
    for(int round=rounds-1;round>=0;round--) {
        const Layer& layer=circuit.layers[round];
        for(const Gate& gate:layer.gates) {
            ErrorMap& error=errors[round*64+gate.edge];
            error.first=images[gate.target]; error.second=images[qubits+gate.control];
            error.first_dual=((error.first&mask)<<qubits)|(error.first>>qubits);
            error.second_dual=((error.second&mask)<<qubits)|(error.second>>qubits);
            images[gate.control]^=images[gate.target];
            images[qubits+gate.target]^=images[qubits+gate.control];
        }
        for(int site=0;site<qubits;site++) {
            Bits xbits=images[site],zbits=images[site+qubits];
            switch(layer.local[site]) {
                case 1: images[site]=zbits; images[site+qubits]=xbits; break;
                case 2: images[site]=xbits^zbits; break;
                case 3: images[site]=zbits; images[site+qubits]=xbits^zbits; break;
                case 4: images[site]=xbits^zbits; images[site+qubits]=xbits; break;
                case 5: images[site+qubits]=xbits^zbits; break;
            }
        }
    }
    for(int site=0;site<qubits;site++) {
        inputs[3*site]=Bits(1)<<site; inputs[3*site+2]=Bits(1)<<(site+qubits); inputs[3*site+1]=inputs[3*site]^inputs[3*site+2];
        ideal[3*site]=images[site]; ideal[3*site+2]=images[site+qubits]; ideal[3*site+1]=images[site]^images[site+qubits];
    }
    for(int first=0;first<int(instances.size());first++) {
        Bits first_images[60];
        for(int site=0;site<3*qubits;site++) first_images[site]=first?error_image(errors[instances[first]],ideal[site]):ideal[site];
        for(int second=first+(first!=0);second<int(instances.size());second++) {
            Bits singles[60];
            for(int site=0;site<3*qubits;site++) singles[site]=second?error_image(errors[instances[second]],first_images[site]):first_images[site];
            for(int left=0;left<3*qubits;left++) {
                int observed=weight(singles[left]); result.minimum=std::min(result.minimum,observed);
                result.near+=(observed==3);
                if(observed<3) { result.minimum=1; result.failures++; result.penalty+=(3-observed)*(3-observed)+4; if(result.penalty>limit) return result; if(collect) result.witnesses.push_back({inputs[left],instances[first],instances[second]}); }
                for(int right=3*(left/3+1);right<3*qubits;right++) {
                    observed=weight(singles[left]^singles[right]); result.minimum=std::min(result.minimum,observed);
                    result.near+=(observed==3);
                    if(observed<3) { result.failures++; result.penalty+=(3-observed)*(3-observed)+1; if(result.penalty>limit) return result; if(collect) result.witnesses.push_back({inputs[left]^inputs[right],instances[first],instances[second]}); }
                }
            }
        }
    }
    return result;
}

FaultResult faults(const Circuit& circuit,bool collect=true,int limit=1000000000) {
    FaultResult result;
    std::vector<int> instances={-1};
    std::array<ErrorMap,768> errors;
    for(int round=0;round<rounds;round++) for(const Gate& gate:circuit.layers[round].gates) instances.push_back(round*64+gate.edge);
    Bits images[40],inputs[60],ideal[60];
    for(int site=0;site<2*qubits;site++) images[site]=Bits(1)<<site;
    for(int round=rounds-1;round>=0;round--) {
        const Layer& layer=circuit.layers[round];
        for(const Gate& gate:layer.gates) {
            ErrorMap& error=errors[round*64+gate.edge];
            error.first=images[gate.target]; error.second=images[qubits+gate.control];
            error.first_dual=((error.first&mask)<<qubits)|(error.first>>qubits);
            error.second_dual=((error.second&mask)<<qubits)|(error.second>>qubits);
            images[gate.control]^=images[gate.target];
            images[qubits+gate.target]^=images[qubits+gate.control];
        }
        for(int site=0;site<qubits;site++) {
            Bits xbits=images[site],zbits=images[site+qubits];
            switch(layer.local[site]) {
                case 1: images[site]=zbits; images[site+qubits]=xbits; break;
                case 2: images[site]=xbits^zbits; break;
                case 3: images[site]=zbits; images[site+qubits]=xbits^zbits; break;
                case 4: images[site]=xbits^zbits; images[site+qubits]=xbits; break;
                case 5: images[site+qubits]=xbits^zbits; break;
            }
        }
    }
    for(int site=0;site<qubits;site++) {
        inputs[3*site]=Bits(1)<<site; inputs[3*site+2]=Bits(1)<<(site+qubits); inputs[3*site+1]=inputs[3*site]^inputs[3*site+2];
        ideal[3*site]=images[site]; ideal[3*site+2]=images[site+qubits]; ideal[3*site+1]=images[site]^images[site+qubits];
    }
    for(int first=0;first<int(instances.size());first++) {
        Bits first_images[60];
        for(int site=0;site<3*qubits;site++) first_images[site]=first?error_image(errors[instances[first]],ideal[site]):ideal[site];
        for(int second=first+(first!=0);second<int(instances.size());second++) {
            Bits second_images[60];
            for(int site=0;site<3*qubits;site++) second_images[site]=second?error_image(errors[instances[second]],first_images[site]):first_images[site];
            for(int third=second+(second!=0);third<int(instances.size());third++) {
                Bits singles[60];
                for(int site=0;site<3*qubits;site++) singles[site]=third?error_image(errors[instances[third]],second_images[site]):second_images[site];
                bool failed=false; result.scenarios++;
                for(int left=0;left<3*qubits;left++) {
                    int observed=weight(singles[left]); result.minimum=std::min(result.minimum,observed);
                    result.near+=(observed==3);
                    if(observed<3) {
                        failed=true; result.minimum=1; result.failures++; result.penalty+=(3-observed)*(3-observed)+4;
                        if(result.penalty>limit) return result;
                        if(collect) result.witnesses.push_back({inputs[left],instances[first],instances[second],instances[third]});
                    }
                    for(int right=3*(left/3+1);right<3*qubits;right++) {
                        observed=weight(singles[left]^singles[right]); result.minimum=std::min(result.minimum,observed);
                        result.near+=(observed==3);
                        if(observed<3) {
                            failed=true; result.failures++; result.penalty+=(3-observed)*(3-observed)+1;
                            if(result.penalty>limit) return result;
                            if(collect) result.witnesses.push_back({inputs[left]^inputs[right],instances[first],instances[second],instances[third]});
                        }
                    }
                }
                result.failed_scenarios+=failed;
            }
        }
    }
    return result;
}

void save(const Circuit& circuit,const std::string& path) {
    const char* words[]={"I","H","S","HS","SH","HSH"};
    std::ofstream stream(path+".json"); stream<<"{\"family\":\""<<family<<"\",\"layers\":[";
    std::ofstream raw(path+".raw");
    for(int round=0;round<rounds;round++) {
        if(round) stream<<",";
        const Layer& layer=circuit.layers[round]; stream<<"{\"local\":[";
        for(int site=0;site<qubits;site++) { if(site) stream<<","; stream<<"\""<<words[layer.local[site]]<<"\""; raw<<layer.local[site]<<" "; }
        stream<<"],\"cx\":["; raw<<layer.gates.size()<<" ";
        for(int index=0;index<int(layer.gates.size());index++) { const Gate& gate=layer.gates[index]; if(index) stream<<","; stream<<"["<<gate.control<<","<<gate.target<<"]"; raw<<gate.control<<" "<<gate.target<<" "<<gate.edge<<" "; }
        stream<<"]}"; raw<<"\n";
    }
    stream<<"]}\n";
}

Circuit load(const std::string& path) {
    Circuit circuit; circuit.layers.resize(rounds); std::ifstream stream(path);
    for(Layer& layer:circuit.layers) {
        for(int site=0;site<qubits;site++) stream>>layer.local[site];
        int count; stream>>count; layer.gates.resize(count);
        for(Gate& gate:layer.gates) stream>>gate.control>>gate.target>>gate.edge;
        compile(layer);
    }
    return circuit;
}

int count_gates(const Circuit& circuit) { int count=0; for(const Layer& layer:circuit.layers) count+=layer.gates.size(); return count; }
bool insert(Circuit& circuit,int round,int edge) {
    auto [left,right]=edges[edge]; Layer& layer=circuit.layers[round];
    for(const Gate& gate:layer.gates) if(gate.control==left||gate.control==right||gate.target==left||gate.target==right) return false;
    if(random_int(2)) std::swap(left,right);
    layer.gates.push_back({left,right,edge}); return true;
}
void fill(Circuit& circuit) {
    int count=count_gates(circuit);
    for(int attempt=0;count<budget&&attempt<3000;attempt++) if(insert(circuit,random_int(rounds),random_int(edges.size()))) count++;
    while(count>budget) { Layer& layer=circuit.layers[random_int(rounds)]; if(layer.gates.empty()) continue; layer.gates.erase(layer.gates.begin()+random_int(layer.gates.size())); count--; }
}
Circuit random_circuit() {
    Circuit circuit; circuit.layers.resize(rounds);
    for(Layer& layer:circuit.layers) { for(int site=0;site<qubits;site++) layer.local[site]=random_int(6); compile(layer); }
    fill(circuit); return circuit;
}
void mutate(Circuit& circuit) {
    int kind=random_int(std::getenv("FIXED")?81:100),round=random_int(rounds); Layer& layer=circuit.layers[round];
    if(kind<73) {
        int local_round=1+random_int(rounds-1); Layer& local_layer=circuit.layers[local_round];
        int site=random_int(qubits); local_layer.local[site]=(local_layer.local[site]+1+random_int(5))%6; compile(local_layer);
        if(kind<8) { int other_round=1+random_int(rounds-1); Layer& other_layer=circuit.layers[other_round]; other_layer.local[site]=(other_layer.local[site]+1+random_int(5))%6; compile(other_layer); }
    }
    else if(kind<81&&!layer.gates.empty()) { Gate& gate=layer.gates[random_int(layer.gates.size())]; std::swap(gate.control,gate.target); }
    else if(kind<96) {
        int edge=random_int(edges.size()); auto [left,right]=edges[edge];
        layer.gates.erase(std::remove_if(layer.gates.begin(),layer.gates.end(),[&](const Gate& gate){return gate.control==left||gate.control==right||gate.target==left||gate.target==right;}),layer.gates.end());
        insert(circuit,round,edge); fill(circuit);
    } else if(kind<99) { int other=random_int(rounds); std::swap(layer.gates,circuit.layers[other].gates); }
    else { int other=random_int(rounds); std::swap(layer,circuit.layers[other]); }
}

void print_metrics(const Metrics& metrics) {
    std::cerr<<" ideal="<<metrics.score<<" hard="<<metrics.hard<<" min=";
    for(int value:metrics.mins) std::cerr<<value<<",";
    std::cerr<<" mean="; for(double value:metrics.means) std::cerr<<value<<",";
}

int exact_search(Circuit circuit,const std::string& output,double seconds) {
    auto started=std::chrono::steady_clock::now();
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();};
    Metrics metrics=measure(circuit); FaultResult fault=faults(circuit,false);
    double near_weight=std::getenv("NEAR")?std::stod(std::getenv("NEAR")):0.0;
    double max_temp=std::getenv("TEMP")?std::stod(std::getenv("TEMP")):3.0;
    double period=std::getenv("PERIOD")?std::stod(std::getenv("PERIOD")):120.0;
    double fault_scale=std::getenv("FAULT_SCALE")?std::stod(std::getenv("FAULT_SCALE")):1.0;
    double current=metrics.hard+metrics.soft+fault_scale*fault.penalty+near_weight*fault.near,bestcost=current;
    Circuit best=circuit; double bestscore=-1; int bestfails=1000000000;
    long evaluations=0,accepted=0; int last_cycle=0;
    for(long iteration=0;elapsed()<seconds;iteration++) {
        int this_cycle=int(elapsed()/period);
        if(this_cycle!=last_cycle && std::getenv("REBASE")) {
            circuit=best; metrics=measure(circuit); fault=faults(circuit,false);
            current=metrics.hard+metrics.soft+fault_scale*fault.penalty+near_weight*fault.near;
        }
        last_cycle=this_cycle;
        double position=std::fmod(elapsed(),period)/period;
        double temperature=max_temp*std::pow(0.025/max_temp,position);
        Circuit candidate=circuit; mutate(candidate);
        Metrics observed=measure(candidate);
        double ceiling=current-temperature*std::log(std::max(1e-100,uniform()));
        double base=observed.hard+observed.soft;
        if(base<=ceiling) {
            FaultResult tested=faults(candidate,false,int((ceiling-base)/fault_scale)); evaluations++;
            double candidatecost=base+fault_scale*tested.penalty+near_weight*tested.near;
            if(candidatecost<=ceiling) {
                circuit=std::move(candidate); metrics=observed; fault=tested; current=candidatecost; accepted++;
                double score=std::min(metrics.score,fault.minimum/3.0);
                if(current<bestcost) { bestcost=current; best=circuit; save(best,output+"_search"); }
                if(score>bestscore+1e-10 || (score>=bestscore-1e-10 && fault.failures<bestfails)) {
                    bestscore=score; bestfails=fault.failures; save(circuit,output);
                    std::cerr<<family<<" EXACT t="<<elapsed()<<" it="<<iteration<<" score="<<score<<" faults="<<fault.failures<<" penalty="<<fault.penalty; print_metrics(metrics); std::cerr<<"\n";
                }
                if(metrics.score>=1-1e-12 && fault.failures==0) { save(circuit,output); std::cerr<<"SUCCESS\n"; return 0; }
            }
        }
        if(iteration%1000==0) {
            std::cerr<<family<<" EXACT t="<<elapsed()<<" it="<<iteration<<" eval="<<evaluations<<" accepted="<<accepted<<" cost="<<current<<" best="<<bestcost<<" faults="<<fault.failures; print_metrics(metrics); std::cerr<<"\n";
        }
    }
    return 0;
}

struct SparseData { std::array<ErrorMap,768> errors; Bits images[40]; };
SparseData sparse_data(const Circuit& circuit) {
    SparseData data;
    for(int site=0;site<2*qubits;site++) data.images[site]=Bits(1)<<site;
    for(int round=rounds-1;round>=0;round--) {
        const Layer& layer=circuit.layers[round];
        for(const Gate& gate:layer.gates) {
            ErrorMap& error=data.errors[round*64+gate.edge];
            error.first=data.images[gate.target]; error.second=data.images[qubits+gate.control];
            error.first_dual=((error.first&mask)<<qubits)|(error.first>>qubits);
            error.second_dual=((error.second&mask)<<qubits)|(error.second>>qubits);
            data.images[gate.control]^=data.images[gate.target];
            data.images[qubits+gate.target]^=data.images[qubits+gate.control];
        }
        for(int site=0;site<qubits;site++) {
            Bits xbits=data.images[site],zbits=data.images[site+qubits];
            switch(layer.local[site]) {
                case 1: data.images[site]=zbits; data.images[site+qubits]=xbits; break;
                case 2: data.images[site]=xbits^zbits; break;
                case 3: data.images[site]=zbits; data.images[site+qubits]=xbits^zbits; break;
                case 4: data.images[site]=xbits^zbits; data.images[site+qubits]=xbits; break;
                case 5: data.images[site+qubits]=xbits^zbits; break;
            }
        }
    }
    return data;
}

int sparse_penalty(const Circuit& circuit,const std::vector<Witness>& pool) {
    SparseData data=sparse_data(circuit); int total=0;
    for(const Witness& witness:pool) {
        Bits support=witness.input; int left=__builtin_ctzll(support); support&=support-1;
        int right=support?__builtin_ctzll(support):-1;
        Bits left_images[3],right_images[3];
        for(int side=0;side<1+(right>=0);side++) {
            int site=side?right:left; Bits* images=side?right_images:left_images;
            for(int axis=0;axis<2;axis++) {
                Bits image=data.images[site+axis*qubits];
                if(witness.first>=0) image=error_image(data.errors[witness.first],image);
                if(witness.second>=0) image=error_image(data.errors[witness.second],image);
                if(witness.third>=0) image=error_image(data.errors[witness.third],image);
                images[2*axis]=image;
            }
            images[1]=images[0]^images[2];
        }
        for(int left_axis=0;left_axis<3;left_axis++) {
            for(int right_axis=0;right_axis<(right>=0?3:1);right_axis++) {
                int observed=weight(left_images[left_axis]^(right>=0?right_images[right_axis]:0));
                if(observed<3) total+=(3-observed)*(3-observed)+(right>=0?1:4);
            }
        }
    }
    return total;
}

int cex_search(Circuit circuit,const std::string& output,double seconds) {
    auto started=std::chrono::steady_clock::now();
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();};
    std::vector<Witness> pool; std::set<Witness> unique;
    auto add=[&](const FaultResult& fault) {
        for(Witness witness:fault.witnesses) {
            witness.input=(witness.input|(witness.input>>qubits))&mask;
            if(unique.insert(witness).second) pool.push_back(witness);
        }
    };
    FaultResult initial_fault=faults(circuit); add(initial_fault);
    Metrics metrics=measure(circuit); int penalty=sparse_penalty(circuit,pool);
    double scale=std::getenv("FAULT_SCALE")?std::stod(std::getenv("FAULT_SCALE")):1.0;
    double soft_scale=std::getenv("SOFT_SCALE")?std::stod(std::getenv("SOFT_SCALE")):1.0;
    double period=std::getenv("PERIOD")?std::stod(std::getenv("PERIOD")):45.0;
    double start_temp=std::getenv("TEMP")?std::stod(std::getenv("TEMP")):3.0;
    double current=metrics.hard+soft_scale*metrics.soft+scale*penalty,bestcost=current;
    Circuit best=circuit; double bestscore=std::min(metrics.score,initial_fault.minimum/3.0);
    int bestfails=initial_fault.failures,last_cycle=0; long checks=1,accepted=0;
    double last_check=0;
    save(circuit,output); save(circuit,output+"_search");
    std::cerr<<family<<" INITIAL t="<<elapsed()<<" score="<<bestscore<<" faults="<<bestfails<<" scenarios="<<initial_fault.scenarios<<" failed_scenarios="<<initial_fault.failed_scenarios<<" pool="<<pool.size(); print_metrics(metrics); std::cerr<<"\n";
    for(long iteration=0;elapsed()<seconds;iteration++) {
        int cycle=int(elapsed()/period);
        if(cycle!=last_cycle) {
            circuit=best; metrics=measure(circuit); penalty=sparse_penalty(circuit,pool);
            current=metrics.hard+soft_scale*metrics.soft+scale*penalty;
            last_cycle=cycle;
            std::cerr<<family<<" CYCLE t="<<elapsed()<<" it="<<iteration<<" cost="<<current<<" best="<<bestcost<<" pool="<<pool.size()<<" sparse="<<penalty<<" checks="<<checks<<" accepted="<<accepted; print_metrics(metrics); std::cerr<<"\n";
            save(best,output+"_search");
        }
        double temperature=start_temp*std::pow(0.02/start_temp,std::fmod(elapsed(),period)/period);
        Circuit candidate=circuit; mutate(candidate); Metrics observed=measure(candidate);
        double ceiling=current-temperature*std::log(std::max(1e-100,uniform()));
        if(observed.hard+soft_scale*observed.soft<=ceiling) {
            int candidatepenalty=sparse_penalty(candidate,pool);
            double candidatecost=observed.hard+soft_scale*observed.soft+scale*candidatepenalty;
            if(candidatecost<=ceiling && faults_pair(candidate,false,0).failures==0) { circuit=std::move(candidate); metrics=observed; penalty=candidatepenalty; current=candidatecost; accepted++; }
        }
        if(current<bestcost) { bestcost=current; best=circuit; }
        bool checkpoint=(metrics.hard<1e-12 && penalty==0) || (elapsed()-last_check>90 && current<bestcost+1e-8);
        if(checkpoint) {
            FaultResult fault=faults(circuit); checks++; last_check=elapsed();
            double score=std::min(metrics.score,fault.minimum/3.0);
            if(score>bestscore+1e-10 || (score>=bestscore-1e-10 && fault.failures<bestfails)) {
                bestscore=score; bestfails=fault.failures; save(circuit,output);
            }
            std::cerr<<family<<" FULL t="<<elapsed()<<" it="<<iteration<<" score="<<score<<" faults="<<fault.failures<<" failed_scenarios="<<fault.failed_scenarios<<" penalty="<<fault.penalty; print_metrics(metrics); std::cerr<<"\n";
            if(metrics.score>=1-1e-12 && fault.failures==0) { save(circuit,output); std::cerr<<"SUCCESS t="<<elapsed()<<"\n"; return 0; }
            size_t old_size=pool.size(); add(fault);
            if(penalty==0 && fault.failures && pool.size()==old_size) { std::cerr<<"INCONSISTENT SPARSE CHECK\n"; return 3; }
            penalty=sparse_penalty(circuit,pool); current=metrics.hard+soft_scale*metrics.soft+scale*penalty;
            Metrics bestmetrics=measure(best); bestcost=bestmetrics.hard+soft_scale*bestmetrics.soft+scale*sparse_penalty(best,pool);
            if(current<bestcost) { bestcost=current; best=circuit; }
        }
    }
    save(best,output+"_search");
    FaultResult final_fault=faults(best); Metrics final_metrics=measure(best);
    double final_score=std::min(final_metrics.score,final_fault.minimum/3.0);
    if(final_score>bestscore+1e-10 || (final_score>=bestscore-1e-10 && final_fault.failures<bestfails)) save(best,output);
    std::cerr<<family<<" FINAL t="<<elapsed()<<" score="<<final_score<<" faults="<<final_fault.failures<<" failed_scenarios="<<final_fault.failed_scenarios; print_metrics(final_metrics); std::cerr<<"\n";
    if(final_metrics.score>=1-1e-12 && final_fault.failures==0) { save(best,output); std::cerr<<"SUCCESS\n"; }
    return 0;
}

int main(int argc,char** argv) {
    if(argc<5) { std::cerr<<"config output seconds seed [initial.raw]\n"; return 1; }
    std::ifstream config(argv[1]); int edge_count; config>>family>>qubits>>rounds>>budget>>single_target>>double_target>>single_mean>>double_mean>>edge_count;
    edges.resize(edge_count); for(auto& edge:edges) config>>edge.first>>edge.second;
    mask=(Bits(1)<<qubits)-1; rng.seed(std::stoull(argv[4])); double seconds=std::stod(argv[3]); std::string output=argv[2];
    auto started=std::chrono::steady_clock::now();
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();};
    Circuit best,circuit=argc>5?load(argv[5]):random_circuit(); Metrics metrics=measure(circuit); double current=cost(circuit,metrics),bestcost=current;
    if(std::getenv("REPORT")) {
        auto fault=faults(circuit,false); std::cout<<argv[5]<<" score="<<std::min(metrics.score,fault.minimum/3.0)<<" faults="<<fault.failures<<" scenarios="<<fault.scenarios<<" failed_scenarios="<<fault.failed_scenarios<<" penalty="<<fault.penalty<<" near="<<fault.near<<" hard="<<metrics.hard<<" cost="<<metrics.hard+metrics.soft+fault.penalty<<"\n"; return 0;
    }
    if(std::getenv("VERIFY")) {
        for(int trial=0;trial<30;trial++) {
            FaultResult fast=faults(circuit),slow=faults_slow(circuit);
            std::set<Witness> fastset(fast.witnesses.begin(),fast.witnesses.end()),slowset(slow.witnesses.begin(),slow.witnesses.end());
            if(fast.minimum!=slow.minimum || fast.penalty!=slow.penalty || fastset.size()!=slowset.size() || fast.scenarios!=slow.scenarios || fast.failed_scenarios!=slow.failed_scenarios) { std::cerr<<"MISMATCH "<<fast.minimum<<" "<<slow.minimum<<" "<<fast.penalty<<" "<<slow.penalty<<"\n"; return 2; }
            for(const Witness& witness:fastset) if(!slowset.count(witness)) { std::cerr<<"WITNESS MISMATCH\n"; return 2; }
            mutate(circuit);
        }
        std::cerr<<"VERIFIED\n"; return 0;
    }
    if(std::getenv("EXACT")) return exact_search(circuit,output,seconds);
    if(std::getenv("CEX")) return cex_search(circuit,output,seconds);
    best=circuit; double bestscore=-1; int bestfails=10000000; long iterations=0; int checks=0,stale=0;
    const int cycle=30000;
    for(int epoch=0;elapsed()<seconds;epoch++) {
        if(epoch>0) {
            if(epoch%5==0 && argc<=5) { circuit=random_circuit(); witnesses.clear(); }
            else { circuit=best; int kicks=2+random_int(8); for(int kick=0;kick<kicks;kick++) mutate(circuit); }
            metrics=measure(circuit); current=cost(circuit,metrics); bestcost=cost(best,measure(best));
        }
        double start_temp=epoch==0?4.0:1.3;
        for(int iteration=0;iteration<cycle && elapsed()<seconds;iteration++,iterations++) {
            double temperature=start_temp*std::pow(0.012/start_temp,double(iteration)/cycle);
            Circuit candidate=circuit; mutate(candidate); Metrics observed=measure(candidate); double candidatecost=cost(candidate,observed);
            if(candidatecost<=current || uniform()<std::exp((current-candidatecost)/temperature)) { circuit=std::move(candidate); metrics=observed; current=candidatecost; }
            if(current<bestcost) { bestcost=current; best=circuit; stale=0; } else stale++;
            bool check=(metrics.hard<0.0000001 && (iteration%100==0 || current<bestcost+0.000001)) || (iterations%20000==0 && metrics.hard<20);
            if(check) {
                FaultResult fault=faults(circuit); checks++;
                double score=std::min(metrics.score,fault.minimum/3.0);
                if(score>bestscore+1e-10 || (score>=bestscore-1e-10 && fault.failures<bestfails)) {
                    bestscore=score; bestfails=fault.failures; save(circuit,output);
                    std::cerr<<family<<" t="<<elapsed()<<" it="<<iterations<<" score="<<score<<" faults="<<fault.failures<<" fmin="<<fault.minimum; print_metrics(metrics); std::cerr<<" pool="<<witnesses.size()<<"\n";
                }
                if(metrics.score>=1-1e-12 && fault.failures==0) { save(circuit,output); std::cerr<<"SUCCESS\n"; return 0; }
                if(!fault.witnesses.empty()) {
                    std::set<Witness> unique(witnesses.begin(),witnesses.end());
                    std::shuffle(fault.witnesses.begin(),fault.witnesses.end(),rng);
                    int additions=0;
                    for(const Witness& witness:fault.witnesses) if(unique.insert(witness).second) { witnesses.push_back(witness); if(++additions>=128) break; }
                    if(witnesses.size()>512) witnesses.erase(witnesses.begin(),witnesses.begin()+witnesses.size()-512);
                    current=cost(circuit,metrics); bestcost=cost(best,measure(best));
                }
            }
        }
        std::cerr<<family<<" epoch="<<epoch<<" t="<<elapsed()<<" cost="<<bestcost<<" checks="<<checks; print_metrics(measure(best)); std::cerr<<" pool="<<witnesses.size()<<"\n";
        save(best,output+"_search");
    }
    if(bestscore<0) { save(best,output); auto fault=faults(best); std::cerr<<"FINAL faults="<<fault.failures; print_metrics(measure(best)); std::cerr<<"\n"; }
    return 0;
}
