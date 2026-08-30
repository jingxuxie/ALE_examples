#include "optimize.cpp"
#include <unordered_map>
#include <functional>
struct TimedGroup {
    int size;
    Word identity;
    vector<int> vertices;
    vector<Gate> native;
    vector<pair<int,int>> endpoints;
    const vector<int>* costs=nullptr;
    const vector<unsigned char>* distances=nullptr;
    function<int(Word)> lookup;
    int distance(Word code)const {
        if(costs)return (*costs)[code]/100;
        if(distances)return (*distances)[code];
        return lookup(code);
    }
};
struct TimedRecord {array<int,7> busy{};vector<array<int,8>> profiles;int countBound=0;};
struct TimedSolver {
    const TimedGroup& group;
    array<int,7> limit;
    int budget;
    int travel[7][7];
    vector<array<int,4>> cuts;
    unordered_map<Word,TimedRecord> records;
    vector<int> path,answer;
    int nodes=0,maxNodes=50000;
    TimedSolver(const TimedGroup& local):group(local) {
        for(int control=0;control<group.size;control++)for(int target=0;target<group.size;target++)travel[control][target]=control==target?0:10000;
        for(int action=0;action<int(group.native.size());action++) {auto [control,target]=group.endpoints[action];travel[control][target]=group.native[action].duration;}
        for(int middle=0;middle<group.size;middle++)for(int control=0;control<group.size;control++)for(int target=0;target<group.size;target++)travel[control][target]=min(travel[control][target],travel[control][middle]+travel[middle][target]);
        for(int action=0;action<int(group.native.size());action++) {
            auto [control,target]=group.endpoints[action];int reached=1<<control;
            for(int iteration=0;iteration<group.size;iteration++)for(auto [source,destination]:group.endpoints) {
                if((source==control&&destination==target)||(source==target&&destination==control))continue;
                if(reached>>source&1)reached|=1<<destination;
            }
            if(!(reached>>target&1))cuts.push_back({control,target,reached,group.native[action].duration});
        }
    }
    int rank(Word code,int rows,int columns)const {
        array<int,7> pivots{};int result=0;
        for(int row=0;row<group.size;row++)if(rows>>row&1) {
            int value=(code>>(row*group.size))&columns;
            while(value) {int bit=__builtin_ctz(value);if(pivots[bit])value^=pivots[bit];else {pivots[bit]=value;result++;break;}}
        }
        return result;
    }
    bool search(Word code,Word inverse,array<int,7> ready,int used,int previous) {
        if(++nodes>maxNodes)return false;
        if(code==group.identity) {answer=path;return true;}
        if(used+group.distance(code)>budget)return false;
        for(int row=0;row<group.size;row++) {
            if(ready[row]>limit[row])return false;
            for(int col=0;col<group.size;col++) {
                if((code>>(row*group.size+col)&1)&&ready[col]+travel[col][row]>limit[row])return false;
                if((inverse>>(row*group.size+col)&1)&&ready[row]+travel[col][row]>limit[col])return false;
            }
        }
        auto [found,inserted]=records.try_emplace(code);TimedRecord& record=found->second;
        if(inserted)for(const auto& cut:cuts) {
            auto [control,target,sourceMask,duration]=cut;
            int count=rank(code,((1<<group.size)-1)^sourceMask,sourceMask);
            record.busy[control]+=count*duration;record.busy[target]+=count*duration;
            record.countBound+=count;
        }
        if(used+record.countBound>budget)return false;
        for(int vertex=0;vertex<group.size;vertex++)if(ready[vertex]+record.busy[vertex]>limit[vertex])return false;
        for(const auto& profile:record.profiles) {
            if(profile[7]>used)continue;bool dominates=true;
            for(int vertex=0;vertex<group.size;vertex++)if(profile[vertex]>ready[vertex]) {dominates=false;break;}
            if(dominates)return false;
        }
        record.profiles.erase(remove_if(record.profiles.begin(),record.profiles.end(),[&](const array<int,8>& profile){if(used>profile[7])return false;for(int vertex=0;vertex<group.size;vertex++)if(ready[vertex]>profile[vertex])return false;return true;}),record.profiles.end());
        array<int,8> profile{ready[0],ready[1],ready[2],ready[3],ready[4],ready[5],ready[6],used};record.profiles.push_back(profile);
        vector<pair<double,int>> choices;
        for(int action=0;action<int(group.native.size());action++)if(action!=previous) {
            auto [control,target]=group.endpoints[action];int finish=max(ready[control],ready[target])+group.native[action].duration;
            if(finish>min(limit[control],limit[target]))continue;
            Word next=code;for(int row=0;row<group.size;row++)if(code>>(row*group.size+target)&1)next^=Word(1)<<(row*group.size+control);
            if(used+1+group.distance(next)>budget)continue;
            double score=group.distance(next)+.08*weight(next^group.identity)+.015*finish+uniform()*.02;
            choices.push_back({score,action});
        }
        sort(choices.begin(),choices.end());
        for(auto [score,action]:choices) {
            auto [control,target]=group.endpoints[action];auto nextReady=ready;nextReady[control]=nextReady[target]=max(ready[control],ready[target])+group.native[action].duration;
            Word next=code;for(int row=0;row<group.size;row++)if(code>>(row*group.size+target)&1)next^=Word(1)<<(row*group.size+control);
            Word nextInverse=inverse^(((inverse>>(control*group.size))&((Word(1)<<group.size)-1))<<(target*group.size));
            path.push_back(action);if(search(next,nextInverse,nextReady,used+1,action))return true;path.pop_back();
            if(nodes>maxNodes)break;
        }
        return false;
    }
};
Word inverseCode(Word code,int size) {
    array<int,7> rows{},inverse{};
    for(int row=0;row<size;row++) {rows[row]=code>>(row*size)&((1<<size)-1);inverse[row]=1<<row;}
    for(int col=0;col<size;col++) {
        if(!(rows[col]>>col&1))for(int row=col+1;row<size;row++)if(rows[row]>>col&1) {swap(rows[col],rows[row]);swap(inverse[col],inverse[row]);break;}
        for(int row=0;row<size;row++)if(row!=col&&(rows[row]>>col&1)) {rows[row]^=rows[col];inverse[row]^=inverse[col];}
    }
    Word result=0;for(int row=0;row<size;row++)result|=Word(inverse[row])<<(row*size);return result;
}
double smoothDepth(const vector<Gate>& circuit,int size) {
    array<int,MAXN> ready{},tail{};vector<int> start;int maximum=0;
    for(const Gate& gate:circuit) {int begin=max(ready[gate.control],ready[gate.target]);start.push_back(begin);ready[gate.control]=ready[gate.target]=begin+gate.duration;maximum=max(maximum,begin+gate.duration);}
    double total=0;
    for(int position=int(circuit.size())-1;position>=0;position--) {
        const Gate& gate=circuit[position];int remaining=max(tail[gate.control],tail[gate.target])+gate.duration;tail[gate.control]=tail[gate.target]=remaining;
        total+=gate.duration*exp((start[position]+remaining-maximum)/2.);
    }
    return maximum+2*log(total)+.01*circuit.size();
}
int timed_main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);const Instance& instance=instances[target];ifstream input(argv[2]);
    int length,oldDepth;input>>length>>oldDepth;vector<Gate> best;
    for(int position=0;position<length;position++) {int control,target;input>>control>>target;best.push_back({control,target,instance.duration[control][target]});}
    double seconds=stod(argv[3]);string suffix=argv[4];rng.seed(stoull(argv[5]));auto started=chrono::steady_clock::now();
    auto localGroups=groups(instance,4,100);double bestQuality=quality(instance,best);vector<Gate> current=best;bool reversed=false;int queries=0;
    save(instance,best,suffix);
    for(int iteration=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;iteration++) {
        const LocalGroup& group=localGroups[rng()%localGroups.size()];array<int,MAXN> local;local.fill(-1);for(int vertex=0;vertex<group.size;vertex++)local[group.vertices[vertex]]=vertex;
        vector<int> starts;for(int position=0;position<int(current.size());position++)if(local[current[position].control]>=0&&local[current[position].target]>=0)starts.push_back(position);
        if(starts.empty())continue;int start=starts[rng()%starts.size()],code=group.identity;vector<int> selected;vector<Gate> obstacles;
        for(int finish=start;finish<int(current.size())&&selected.size()<18;finish++) {
            const Gate& gate=current[finish];bool usable=local[gate.control]>=0&&local[gate.target]>=0;
            if(usable)for(const Gate& obstacle:obstacles)if(!commute(gate,obstacle)) {usable=false;break;}
            if(!usable) {obstacles.push_back(gate);continue;}
            selected.push_back(finish);code^=((code>>(local[gate.control]*group.size))&((1<<group.size)-1))<<(local[gate.target]*group.size);
        }
        if(selected.size()<2)continue;
        vector<Gate> prefix(current.begin(),current.begin()+start),suffixGates;int nextSelected=0;
        for(int position=start;position<int(current.size());position++) {if(nextSelected<int(selected.size())&&position==selected[nextSelected])nextSelected++;else suffixGates.push_back(current[position]);}
        array<int,MAXN> prefixReady{},suffixReady{};
        for(const Gate& gate:prefix)prefixReady[gate.control]=prefixReady[gate.target]=max(prefixReady[gate.control],prefixReady[gate.target])+gate.duration;
        for(auto iter=suffixGates.rbegin();iter!=suffixGates.rend();iter++)suffixReady[iter->control]=suffixReady[iter->target]=max(suffixReady[iter->control],suffixReady[iter->target])+iter->duration;
        int wanted=depth(current,instance.size);bool possible=true;
        for(int vertex=0;vertex<instance.size;vertex++)if(local[vertex]<0&&prefixReady[vertex]+suffixReady[vertex]>wanted) {possible=false;break;}
        if(!possible)continue;
        auto oldReady=prefixReady;for(int position:selected) {const Gate& gate=current[position];oldReady[gate.control]=oldReady[gate.target]=max(oldReady[gate.control],oldReady[gate.target])+gate.duration;}
        int focus=-1,focusBound=0;
        for(int vertex=0;vertex<group.size;vertex++) {
            int bound=oldReady[group.vertices[vertex]]+suffixReady[group.vertices[vertex]];
            if(bound>focusBound||(bound==focusBound&&uniform()<.3)) {focusBound=bound;focus=vertex;}
        }
        if(focus<0||focusBound<wanted-2)continue;
        TimedGroup converted{group.size,group.identity,group.vertices,group.native,group.endpoints,&group.costs,nullptr};
        queries++;TimedSolver solver(converted);array<int,7> startReady{};
        for(int vertex=0;vertex<group.size;vertex++) {solver.limit[vertex]=wanted-suffixReady[group.vertices[vertex]];startReady[vertex]=prefixReady[group.vertices[vertex]];}
        solver.limit[focus]--;
        solver.budget=min(int(selected.size())+4,max(instance.capCount,int(current.size()))-int(current.size())+int(selected.size()));
        if(solver.search(code,inverseCode(code,group.size),startReady,0,-1)) {
            vector<Gate> candidate=prefix;for(int action:solver.answer)candidate.push_back(group.native[action]);candidate.insert(candidate.end(),suffixGates.begin(),suffixGates.end());
            candidate=schedule(simplify(candidate),instance.size,30);
            if(smoothDepth(candidate,instance.size)<smoothDepth(current,instance.size)-1e-8)current=move(candidate);
            double score=quality(instance,current);
            if(score<bestQuality) {bestQuality=score;best=current;if(reversed)reverse(best.begin(),best.end());save(instance,best,suffix);cerr<<"improved "<<iteration<<" queries "<<queries<<" count "<<best.size()<<" depth "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;}
        }
        if(iteration%1000==999) {current=best;reversed=uniform()<.5;if(reversed)reverse(current.begin(),current.end());for(int pass=0;pass<20;pass++)for(int position=0;position+1<int(current.size());position++)if(commute(current[position],current[position+1])&&uniform()<.5)swap(current[position],current[position+1]);}
        if(queries%1000==0)cerr<<"queries "<<queries<<" best "<<best.size()<<" "<<depth(best,instance.size)<<endl;
    }
}
