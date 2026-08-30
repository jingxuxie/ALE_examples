#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace std;
using Word = uint64_t;
const int MAXN = 40;
struct Gate {int control, target, duration;};
struct Instance {
    string name;
    int size, capCount, capDepth;
    vector<Gate> gates;
    array<Word,MAXN> original{}, inverse{};
    int distance[MAXN][MAXN]{};
    int duration[MAXN][MAXN]{};
};
struct State {
    array<Word,MAXN> rows{}, cols{}, invrows{}, invcols{};
};
mt19937_64 rng(917251);
double uniform() {return (rng() >> 11) * 0x1.0p-53;}
int weight(Word value) {return __builtin_popcountll(value);}
void transpose(const array<Word,MAXN>& rows, array<Word,MAXN>& cols, int size) {
    cols.fill(0);
    for(int row=0;row<size;row++) {
        Word bits=rows[row];
        while(bits) {int col=__builtin_ctzll(bits); bits&=bits-1; cols[col]|=Word(1)<<row;}
    }
}
State initial(const Instance& instance) {
    State state;
    state.rows=instance.original;
    state.invrows=instance.inverse;
    transpose(state.rows,state.cols,instance.size);
    transpose(state.invrows,state.invcols,instance.size);
    return state;
}
void rowop(array<Word,MAXN>& rows,array<Word,MAXN>& cols,int control,int target) {
    Word bits=rows[control]; rows[target]^=bits;
    while(bits) {int col=__builtin_ctzll(bits);bits&=bits-1;cols[col]^=Word(1)<<target;}
}
void apply(State& state,const Gate& gate,int side) {
    if(side==0) {
        rowop(state.rows,state.cols,gate.control,gate.target);
        rowop(state.invcols,state.invrows,gate.target,gate.control);
    } else {
        rowop(state.cols,state.rows,gate.target,gate.control);
        rowop(state.invrows,state.invcols,gate.control,gate.target);
    }
}
struct Heuristic {
    double weights[MAXN][MAXN]{};
    double invFactor=1;
    double logFactor=0;
    double logs[MAXN+1]{};
    Heuristic() {for(int count=1;count<=MAXN;count++)logs[count]=log2(count);}
    double lognorm(const State& state,int size) const {
        double result=0;
        for(int row=0;row<size;row++)result+=logs[weight(state.rows[row])]+logs[weight(state.cols[row])]+invFactor*(logs[weight(state.invrows[row])]+logs[weight(state.invcols[row])]);
        return result;
    }
    double norm(const array<Word,MAXN>& rows,int size) const {
        double result=0;
        for(int row=0;row<size;row++) {
            Word bits=rows[row];
            while(bits) {int col=__builtin_ctzll(bits);bits&=bits-1;result+=weights[row][col];}
        }
        return result;
    }
    double value(const State& state,int size) const {return norm(state.rows,size)+invFactor*norm(state.invrows,size)+logFactor*lognorm(state,size);}
    double logdiff(const array<Word,MAXN>& rows,const array<Word,MAXN>& cols,int control,int target) const {
        double result=logs[weight(rows[target]^rows[control])]-logs[weight(rows[target])];
        Word bits=rows[control];
        while(bits) {
            int col=__builtin_ctzll(bits);bits&=bits-1;int count=weight(cols[col]);
            result+=logs[count+((rows[target]>>col&1)?-1:1)]-logs[count];
        }
        return result;
    }
    double difference(const State& state,const Gate& gate,int side) const {
        int control=gate.control,target=gate.target;
        double change=0,invchange=0;
        if(side==0) {
            Word bits=state.rows[control];
            while(bits) {int col=__builtin_ctzll(bits);bits&=bits-1;change+=weights[target][col]*((state.rows[target]>>col&1)?-1:1);}
            bits=state.invcols[target];
            while(bits) {int row=__builtin_ctzll(bits);bits&=bits-1;invchange+=weights[row][control]*((state.invcols[control]>>row&1)?-1:1);}
        } else {
            Word bits=state.cols[target];
            while(bits) {int row=__builtin_ctzll(bits);bits&=bits-1;change+=weights[row][control]*((state.cols[control]>>row&1)?-1:1);}
            bits=state.invrows[control];
            while(bits) {int col=__builtin_ctzll(bits);bits&=bits-1;invchange+=weights[target][col]*((state.invrows[target]>>col&1)?-1:1);}
        }
        double result=change+invFactor*invchange;
        if(logFactor) {
            if(side==0)result+=logFactor*(logdiff(state.rows,state.cols,control,target)+invFactor*logdiff(state.invcols,state.invrows,target,control));
            else result+=logFactor*(logdiff(state.cols,state.rows,target,control)+invFactor*logdiff(state.invrows,state.invcols,control,target));
        }
        return result;
    }
};
bool solved(const State& state,int size) {
    for(int row=0;row<size;row++)if(state.rows[row]!=(Word(1)<<row))return false;
    return true;
}
bool commute(const Gate& first,const Gate& second) {
    return first.control!=second.target && first.target!=second.control;
}
vector<Gate> simplify(vector<Gate> circuit) {
    bool changed=true;
    while(changed) {
        changed=false;
        for(int pos=0;pos<int(circuit.size());pos++) {
            for(int next=pos+1;next<int(circuit.size());next++) {
                if(circuit[pos].control==circuit[next].control && circuit[pos].target==circuit[next].target) {
                    circuit.erase(circuit.begin()+next);circuit.erase(circuit.begin()+pos);changed=true;pos--;break;
                }
                if(!commute(circuit[pos],circuit[next]))break;
            }
        }
    }
    return circuit;
}
int depth(const vector<Gate>& circuit,int size) {
    array<int,MAXN> ready{};
    for(const Gate& gate:circuit) {
        int finish=max(ready[gate.control],ready[gate.target])+gate.duration;
        ready[gate.control]=ready[gate.target]=finish;
    }
    return *max_element(ready.begin(),ready.begin()+size);
}
vector<Gate> schedule(const vector<Gate>& circuit,int size,int attempts=15) {
    int length=circuit.size();
    vector<vector<int>> after(length);
    vector<int> indegrees(length),height(length);
    for(int pos=0;pos<length;pos++)for(int next=pos+1;next<length;next++) {
        if(!commute(circuit[pos],circuit[next])) {after[pos].push_back(next);indegrees[next]++;}
    }
    for(int pos=length-1;pos>=0;pos--) {
        for(int next:after[pos])height[pos]=max(height[pos],height[next]);
        height[pos]+=circuit[pos].duration;
    }
    vector<Gate> best=circuit;
    int bestDepth=depth(circuit,size);
    for(int attempt=0;attempt<attempts;attempt++) {
        vector<int> degree=indegrees,available;
        array<int,MAXN> ready{};
        for(int pos=0;pos<length;pos++)if(!degree[pos])available.push_back(pos);
        vector<Gate> result;
        double noise=attempt==0?0:uniform()*5;
        while(!available.empty()) {
            int choice=0;
            double bestScore=1e100;
            for(int pos=0;pos<int(available.size());pos++) {
                int index=available[pos];const Gate& gate=circuit[index];
                double score=max(ready[gate.control],ready[gate.target])-0.05*height[index]+noise*uniform();
                if(score<bestScore) {bestScore=score;choice=pos;}
            }
            int index=available[choice];available[choice]=available.back();available.pop_back();
            const Gate& gate=circuit[index];result.push_back(gate);
            ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;
            for(int next:after[index])if(!--degree[next])available.push_back(next);
        }
        int currentDepth=depth(result,size);
        if(currentDepth<bestDepth) {bestDepth=currentDepth;best=move(result);}
    }
    return best;
}
vector<Instance> load() {
    ifstream input("instances.txt");int count;input>>count;vector<Instance> instances(count);
    for(Instance& instance:instances) {
        int edgeCount;input>>instance.name>>instance.size>>edgeCount>>instance.capCount>>instance.capDepth;
        for(int row=0;row<instance.size;row++)input>>instance.original[row];
        for(int edge=0;edge<edgeCount;edge++) {Gate gate;input>>gate.control>>gate.target>>gate.duration;instance.gates.push_back(gate);instance.duration[gate.control][gate.target]=gate.duration;}
        for(int row=0;row<instance.size;row++)for(int col=0;col<instance.size;col++)instance.distance[row][col]=row==col?0:100;
        for(const Gate& gate:instance.gates)instance.distance[gate.control][gate.target]=1;
        for(int mid=0;mid<instance.size;mid++)for(int row=0;row<instance.size;row++)for(int col=0;col<instance.size;col++)instance.distance[row][col]=min(instance.distance[row][col],instance.distance[row][mid]+instance.distance[mid][col]);
        auto rows=instance.original;
        for(int row=0;row<instance.size;row++)instance.inverse[row]=Word(1)<<row;
        for(int col=0;col<instance.size;col++) {
            if(!(rows[col]>>col&1))for(int row=col+1;row<instance.size;row++)if(rows[row]>>col&1) {swap(rows[row],rows[col]);swap(instance.inverse[row],instance.inverse[col]);break;}
            for(int row=0;row<instance.size;row++)if(row!=col && (rows[row]>>col&1)) {rows[row]^=rows[col];instance.inverse[row]^=instance.inverse[col];}
        }
    }
    return instances;
}
void save(const Instance& instance,const vector<Gate>& circuit,string suffix="best") {
    ofstream output(instance.name+"_"+suffix+".txt");
    output<<circuit.size()<<" "<<depth(circuit,instance.size)<<"\n";
    for(const Gate& gate:circuit)output<<gate.control<<" "<<gate.target<<"\n";
}
int greedy_main(int argc,char** argv) {
    auto instances=load();int target=argc>1?stoi(argv[1]):0;double seconds=argc>2?stod(argv[2]):60;
    if(argc>3)rng.seed(stoull(argv[3]));
    const Instance& instance=instances[target];int size=instance.size;
    auto started=chrono::steady_clock::now();
    double bestQuality=1e100;int bestCount=100000,bestDepth=100000,successes=0;
    for(int trial=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;trial++) {
        State state=initial(instance);Heuristic heuristic;
        double distanceWeight=trial%5==0?0:uniform()*1.5;
        double diagonalWeight=uniform()*1.5;
        heuristic.invFactor=trial%4==0?0:exp((uniform()-.5)*3);
        for(int row=0;row<size;row++)for(int col=0;col<size;col++)heuristic.weights[row][col]=row==col?diagonalWeight:1+distanceWeight*instance.distance[row][col];
        vector<Gate> left,right;
        double current=heuristic.value(state,size),minimum=current;
        int stalled=0,lastAction=-1;
        int edgeCount=instance.gates.size();
        double noise=uniform()*1.5;
        for(int step=0;step<instance.capCount*3;step++) {
            if(solved(state,size)) {
                vector<Gate> circuit=right;for(auto iter=left.rbegin();iter!=left.rend();iter++)circuit.push_back(*iter);
                circuit=schedule(simplify(circuit),size);
                int count=circuit.size(),currentDepth=depth(circuit,size);successes++;
                double quality=max(double(count)/instance.capCount,double(currentDepth)/instance.capDepth)+.001*(count+currentDepth);
                if(quality<bestQuality) {bestQuality=quality;bestCount=count;bestDepth=currentDepth;save(instance,circuit);cerr<<instance.name<<" trial "<<trial<<" successes "<<successes<<" count "<<count<<" depth "<<currentDepth<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;}
                break;
            }
            double bestScore=1e100,bestChange=0;int choice=-1;
            for(int action=0;action<edgeCount*2;action++) {
                if(action==lastAction)continue;
                const Gate& gate=instance.gates[action%edgeCount];int side=action/edgeCount;
                double change=heuristic.difference(state,gate,side);
                double score=change+noise*uniform();
                if(score<bestScore) {bestScore=score;bestChange=change;choice=action;}
            }
            if(choice<0)break;
            if(bestChange>=-1e-6 && stalled>4) {
                double lookBest=1e100;int lookChoice=-1;
                for(int action=0;action<edgeCount*2;action++) {
                    if(action==lastAction)continue;
                    const Gate& gate=instance.gates[action%edgeCount];int side=action/edgeCount;
                    double change=heuristic.difference(state,gate,side);
                    apply(state,gate,side);
                    for(int next=0;next<edgeCount*2;next++) {
                        if(next==action)continue;
                        double total=change+heuristic.difference(state,instance.gates[next%edgeCount],next/edgeCount);
                        double score=total+noise*uniform();
                        if(score<lookBest) {lookBest=score;lookChoice=action;}
                    }
                    apply(state,gate,side);
                }
                choice=lookChoice;bestChange=heuristic.difference(state,instance.gates[choice%edgeCount],choice/edgeCount);
            }
            const Gate& gate=instance.gates[choice%edgeCount];int side=choice/edgeCount;
            apply(state,gate,side);(side==0?left:right).push_back(gate);current+=bestChange;lastAction=choice;
            if(current<minimum-1e-6) {minimum=current;stalled=0;}else stalled++;
            if(stalled>30)break;
        }
        if(trial%100==0) {
            int residual=0;for(int row=0;row<size;row++)residual+=weight(state.rows[row]^(Word(1)<<row));
            cerr<<instance.name<<" progress "<<trial<<" best "<<bestCount<<" "<<bestDepth<<" successes "<<successes<<" residual "<<residual<<" steps "<<left.size()+right.size()<<endl;
            ofstream output(instance.name+"_residual.txt");
            for(int row=0;row<size;row++)output<<state.rows[row]<<" ";output<<"\n";
        }
    }
    return 0;
}
