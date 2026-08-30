#pragma once
#include "search.cpp"
#include <queue>
struct LocalGroup {
    int size;
    vector<int> vertices;
    vector<Gate> native;
    vector<pair<int,int>> endpoints;
    vector<vector<int>> patterns;
    vector<int> costs,parents,actions;
    int identity;
    LocalGroup(const Instance& instance,vector<int> selected,int countCost):size(selected.size()),vertices(move(selected)) {
        int bound=1<<(size*size);costs.assign(bound,1000000000);parents.assign(bound,-1);actions.assign(bound,-1);identity=0;
        for(int row=0;row<size;row++)identity|=1<<(row*size+row);
        for(int control=0;control<size;control++)for(int target=0;target<size;target++)if(instance.duration[vertices[control]][vertices[target]]) {
            native.push_back({vertices[control],vertices[target],instance.duration[vertices[control]][vertices[target]]});endpoints.push_back({control,target});
        }
        for(int index=0;index<int(native.size());index++)patterns.push_back({index});
        if(countCost<0)for(int first=0;first<int(native.size());first++)for(int second=first+1;second<int(native.size());second++) {
            const Gate& firstGate=native[first];const Gate& secondGate=native[second];
            if(firstGate.control!=secondGate.control&&firstGate.control!=secondGate.target&&firstGate.target!=secondGate.control&&firstGate.target!=secondGate.target)patterns.push_back({first,second});
        }
        priority_queue<pair<int,int>,vector<pair<int,int>>,greater<pair<int,int>>> queue;
        costs[identity]=0;queue.push({0,identity});
        while(!queue.empty()) {
            auto [cost,code]=queue.top();queue.pop();if(cost!=costs[code])continue;
            for(int index=0;index<int(patterns.size());index++) {
                int next=code,maximumDuration=0;
                for(int action:patterns[index]) {
                    auto [control,target]=endpoints[action];next^=((next>>(control*size))&((1<<size)-1))<<(target*size);maximumDuration=max(maximumDuration,native[action].duration);
                }
                int newCost=cost+(countCost<0?100*maximumDuration+int(patterns[index].size()):countCost+maximumDuration);
                if(newCost<costs[next]) {costs[next]=newCost;parents[next]=code;actions[next]=index;queue.push({newCost,next});}
            }
        }
    }
    vector<Gate> circuit(int code) const {
        vector<Gate> result;
        while(code!=identity) {int index=actions[code];if(index<0)throw runtime_error("invalid group element");for(auto iter=patterns[index].rbegin();iter!=patterns[index].rend();iter++)result.push_back(native[*iter]);code=parents[code];}
        reverse(result.begin(),result.end());return result;
    }
};
bool connected(const Instance& instance,const vector<int>& vertices) {
    Word visited=Word(1)<<vertices[0];
    for(int iteration=0;iteration<int(vertices.size());iteration++)for(int control:vertices)if(visited>>control&1)for(int target:vertices)if(instance.duration[control][target])visited|=Word(1)<<target;
    return weight(visited)==int(vertices.size());
}
vector<LocalGroup> groups(const Instance& instance,int maxSize,int countCost) {
    vector<LocalGroup> result;
    auto addGroup=[&](vector<int> vertices){shuffle(vertices.begin(),vertices.end(),rng);result.emplace_back(instance,move(vertices),countCost);};
    for(int first=0;first<instance.size;first++)for(int second=first+1;second<instance.size;second++)for(int third=second+1;third<instance.size;third++) {
        vector<int> vertices{first,second,third};
        if(connected(instance,vertices))addGroup(vertices);
        if(maxSize>=4)for(int fourth=third+1;fourth<instance.size;fourth++) {vertices={first,second,third,fourth};if(connected(instance,vertices))addGroup(vertices);}
    }
    return result;
}
bool smoothObjective=false;
double quality(const Instance& instance,const vector<Gate>& circuit) {
    int currentDepth=depth(circuit,instance.size);
    double worst=max(double(circuit.size())/instance.capCount,double(currentDepth)/instance.capDepth);
    if(!smoothObjective||worst<=1)return (worst<=1?.9:worst)+.0001*(circuit.size()+currentDepth);
    static array<double,128> exponentials=[](){array<double,128> result{};for(int index=0;index<128;index++)result[index]=exp(-index/2.);return result;}();
    array<int,MAXN> ready{},tail{};vector<int> starts;starts.reserve(circuit.size());
    for(const Gate& gate:circuit) {int begin=max(ready[gate.control],ready[gate.target]);starts.push_back(begin);ready[gate.control]=ready[gate.target]=begin+gate.duration;}
    double mass=0;
    for(int position=int(circuit.size())-1;position>=0;position--) {
        const Gate& gate=circuit[position];int remaining=max(tail[gate.control],tail[gate.target])+gate.duration;tail[gate.control]=tail[gate.target]=remaining;
        mass+=gate.duration*exponentials[min(127,max(0,currentDepth-starts[position]-remaining))];
    }
    return worst+.02*log(mass)+.0001*circuit.size();
}
int optimizer_main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);Instance instance=instances[target];
    ifstream input(argv[2]);int length,oldDepth;input>>length>>oldDepth;
    vector<Gate> best;
    for(int pos=0;pos<length;pos++) {int control,target;input>>control>>target;best.push_back({control,target,instance.duration[control][target]});}
    if(argc>5)rng.seed(stoull(argv[5]));
    double seconds=argc>3?stod(argv[3]):60;int countCost=argc>6?stoi(argv[6]):100;
    double temperature=argc>7?stod(argv[7]):0;
    bool transposed=argc>8?stoi(argv[8]):false;
    smoothObjective=argc>9?stoi(argv[9]):false;
    if(transposed) {
        for(Gate& gate:best)swap(gate.control,gate.target);
        for(int control=0;control<instance.size;control++)for(int target=control+1;target<instance.size;target++)swap(instance.duration[control][target],instance.duration[target][control]);
    }
    auto saveBest=[&](const vector<Gate>& circuit){auto output=circuit;if(transposed)for(Gate& gate:output)swap(gate.control,gate.target);save(instance,output,argv[4]);};
    auto started=chrono::steady_clock::now();
    auto localGroups=groups(instance,4,countCost);
    cerr<<"groups "<<localGroups.size()<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    best=schedule(simplify(best),instance.size,200);saveBest(best);
    double bestQuality=quality(instance,best);vector<Gate> current=best;
    bool reversed=false;
    for(int iteration=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;iteration++) {
        bool changed=false;
        vector<int> indices(localGroups.size());iota(indices.begin(),indices.end(),0);shuffle(indices.begin(),indices.end(),rng);
        for(int groupIndex:indices) {
            const LocalGroup& group=localGroups[groupIndex];
            array<int,MAXN> local;local.fill(-1);for(int pos=0;pos<group.size;pos++)local[group.vertices[pos]]=pos;
            for(int start=0;start<int(current.size());start++) {
                if(local[current[start].control]<0||local[current[start].target]<0)continue;
                int code=group.identity,selectedCost=0;
                vector<int> selected;vector<Gate> obstacles;
                double currentQuality=quality(instance,current);
                for(int finish=start;finish<int(current.size());finish++) {
                    const Gate& gate=current[finish];
                    bool usable=local[gate.control]>=0&&local[gate.target]>=0;
                    if(usable)for(const Gate& obstacle:obstacles)if(!commute(gate,obstacle)) {usable=false;break;}
                    if(!usable) {obstacles.push_back(gate);continue;}
                    selected.push_back(finish);selectedCost+=countCost+gate.duration;
                    code^=((code>>(local[gate.control]*group.size))&((1<<group.size)-1))<<(local[gate.target]*group.size);
                    if(countCost>=0&&group.costs[code]>selectedCost)continue;
                    auto replacement=group.circuit(code);
                    if(temperature&&uniform()<.12) {
                        int altered=code;vector<Gate> suffix;
                        int extras=1+rng()%3;
                        for(int extra=0;extra<extras;extra++) {
                            int index=rng()%group.native.size();auto [control,target]=group.endpoints[index];
                            altered^=((altered>>(control*group.size))&((1<<group.size)-1))<<(target*group.size);
                            suffix.push_back(group.native[index]);
                        }
                        replacement=group.circuit(altered);
                        for(auto iter=suffix.rbegin();iter!=suffix.rend();iter++)replacement.push_back(*iter);
                    }
                    if(replacement.size()==selected.size()&&equal(replacement.begin(),replacement.end(),selected.begin(),[&](const Gate& candidate,int pos){return candidate.control==current[pos].control&&candidate.target==current[pos].target;}))continue;
                    vector<Gate> candidate;candidate.insert(candidate.end(),current.begin(),current.begin()+start);candidate.insert(candidate.end(),replacement.begin(),replacement.end());
                    int nextSelected=0;
                    for(int pos=start;pos<int(current.size());pos++) {
                        if(nextSelected<int(selected.size())&&pos==selected[nextSelected])nextSelected++;else candidate.push_back(current[pos]);
                    }
                    double candidateQuality=quality(instance,candidate);
                    if(candidateQuality<currentQuality-1e-8||(candidateQuality<=currentQuality+1e-8&&uniform()<.03)||(temperature&&uniform()<.003*exp((currentQuality-candidateQuality)/temperature))) {
                        current=move(candidate);changed=true;break;
                    }
                }
            }
        }
        current=schedule(simplify(current),instance.size,30);
        double currentQuality=quality(instance,current);
        if(currentQuality<bestQuality-1e-8) {
            best=current;if(reversed)reverse(best.begin(),best.end());bestQuality=currentQuality;saveBest(best);
            cerr<<"improved "<<iteration<<" count "<<best.size()<<" depth "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
        }
        if(!changed||iteration%10==9) {
            current=best;
            reversed=uniform()<.5;if(reversed)reverse(current.begin(),current.end());
            for(int pass=0;pass<20;pass++)for(int pos=0;pos+1<int(current.size());pos++)if(commute(current[pos],current[pos+1])&&uniform()<.5)swap(current[pos],current[pos+1]);
        }
    }
    return 0;
}
