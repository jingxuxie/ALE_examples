#include "optimize.cpp"
#include <unordered_map>
#include <memory>
struct Space {
    vector<pair<int,int>> edges;
    vector<unsigned char> distances;
    uint32_t identity=0;
    Space(uint32_t graph) {
        for(int row=0;row<5;row++)identity|=1u<<(row*5+row);
        for(int control=0;control<5;control++)for(int target=0;target<5;target++)if(graph>>(control*5+target)&1)edges.push_back({control,target});
        distances.assign(1u<<25,255);distances[identity]=0;
        vector<uint32_t> queue;queue.reserve(10000000);queue.push_back(identity);
        for(size_t position=0;position<queue.size();position++) {
            uint32_t code=queue[position];unsigned char distance=distances[code]+1;
            for(auto [control,target]:edges) {
                uint32_t next=code^(((code>>(control*5))&31)<<(target*5));
                if(distances[next]==255) {distances[next]=distance;queue.push_back(next);}
            }
        }
        cerr<<"space "<<graph<<" size "<<queue.size()<<endl;
    }
};
struct FiveGroup {array<int,5> vertices;shared_ptr<Space> space;vector<Gate> gates;};
vector<FiveGroup> fiveGroups(const Instance& instance) {
    vector<FiveGroup> result;unordered_map<uint32_t,shared_ptr<Space>> spaces;
    for(int first=0;first<instance.size;first++)for(int second=first+1;second<instance.size;second++)for(int third=second+1;third<instance.size;third++)for(int fourth=third+1;fourth<instance.size;fourth++)for(int fifth=fourth+1;fifth<instance.size;fifth++) {
        vector<int> selected{first,second,third,fourth,fifth};int edgeCount=0;
        for(int control:selected)for(int target:selected)edgeCount+=instance.duration[control][target]>0;
        if(edgeCount<8||!connected(instance,selected))continue;
        array<int,5> permutation{0,1,2,3,4},best{};uint32_t bestCode=UINT32_MAX;
        do {
            uint32_t code=0;
            for(int control=0;control<5;control++)for(int target=0;target<5;target++)if(instance.duration[selected[permutation[control]]][selected[permutation[target]]])code|=1u<<(control*5+target);
            if(code<bestCode) {bestCode=code;best=permutation;}
        }while(next_permutation(permutation.begin(),permutation.end()));
        if(!spaces.count(bestCode))spaces[bestCode]=make_shared<Space>(bestCode);
        FiveGroup group;group.space=spaces[bestCode];
        for(int vertex=0;vertex<5;vertex++)group.vertices[vertex]=selected[best[vertex]];
        for(auto [control,target]:group.space->edges) {int physicalControl=group.vertices[control],physicalTarget=group.vertices[target];group.gates.push_back({physicalControl,physicalTarget,instance.duration[physicalControl][physicalTarget]});}
        result.push_back(move(group));
    }
    return result;
}
struct Profile {array<int,5> ready;vector<unsigned char> path;};
struct LocalSolver {
    const FiveGroup& group;
    array<int,5> start,tail;
    int limit;
    unordered_map<uint32_t,vector<Profile>> cache;
    int value(const Profile& profile)const {int result=0;for(int vertex=0;vertex<5;vertex++)result=max(result,profile.ready[vertex]+tail[vertex]);return result;}
    const vector<Profile>& solve(uint32_t code) {
        auto found=cache.find(code);if(found!=cache.end())return found->second;
        vector<Profile> profiles;
        if(code==group.space->identity)profiles.push_back({start,{}});
        else if(cache.size()<30000) {
            int distance=group.space->distances[code];
            for(int action=0;action<int(group.gates.size());action++) {
                auto [control,target]=group.space->edges[action];
                uint32_t previous=code^(((code>>(control*5))&31)<<(target*5));
                if(group.space->distances[previous]!=distance-1)continue;
                const auto& parents=solve(previous);
                for(const Profile& parent:parents) {
                    Profile candidate=parent;candidate.path.push_back(action);
                    candidate.ready[control]=candidate.ready[target]=max(candidate.ready[control],candidate.ready[target])+group.gates[action].duration;
                    if(value(candidate)>limit)continue;
                    bool dominated=false;
                    for(const Profile& other:profiles) {
                        bool better=true;for(int vertex=0;vertex<5;vertex++)if(other.ready[vertex]>candidate.ready[vertex]) {better=false;break;}
                        if(better) {dominated=true;break;}
                    }
                    if(dominated)continue;
                    profiles.erase(remove_if(profiles.begin(),profiles.end(),[&](const Profile& other){for(int vertex=0;vertex<5;vertex++)if(candidate.ready[vertex]>other.ready[vertex])return false;return true;}),profiles.end());
                    profiles.push_back(move(candidate));
                    if(profiles.size()>8) {
                        sort(profiles.begin(),profiles.end(),[&](const Profile& first,const Profile& second){return value(first)*1000+accumulate(first.ready.begin(),first.ready.end(),0)<value(second)*1000+accumulate(second.ready.begin(),second.ready.end(),0);});profiles.resize(8);
                    }
                }
            }
        }
        return cache.emplace(code,move(profiles)).first->second;
    }
};
int five_main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);const Instance& instance=instances[target];
    ifstream input(argv[2]);int length,oldDepth;input>>length>>oldDepth;vector<Gate> best;
    for(int position=0;position<length;position++) {int control,target;input>>control>>target;best.push_back({control,target,instance.duration[control][target]});}
    double seconds=stod(argv[3]);string suffix=argv[4];rng.seed(stoull(argv[5]));
    auto started=chrono::steady_clock::now();auto localGroups=fiveGroups(instance);
    cerr<<"groups "<<localGroups.size()<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    double bestQuality=quality(instance,best);vector<Gate> current=best;
    save(instance,best,suffix);
    for(int iteration=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;iteration++) {
        const FiveGroup& group=localGroups[rng()%localGroups.size()];array<int,MAXN> local;local.fill(-1);
        for(int vertex=0;vertex<5;vertex++)local[group.vertices[vertex]]=vertex;
        vector<int> starts;for(int position=0;position<int(current.size());position++)if(local[current[position].control]>=0&&local[current[position].target]>=0)starts.push_back(position);
        if(starts.empty())continue;
        int start=starts[rng()%starts.size()];uint32_t code=group.space->identity;int used=0;
        vector<int> selected;vector<Gate> obstacles;int maxLength=8+rng()%13;
        for(int finish=start;finish<int(current.size())&&int(selected.size())<maxLength;finish++) {
            const Gate& gate=current[finish];bool usable=local[gate.control]>=0&&local[gate.target]>=0;
            if(usable)for(const Gate& obstacle:obstacles)if(!commute(gate,obstacle)) {usable=false;break;}
            if(!usable) {obstacles.push_back(gate);continue;}
            selected.push_back(finish);used|=(1<<local[gate.control])|(1<<local[gate.target]);
            code^=((code>>(local[gate.control]*5))&31)<<(local[gate.target]*5);
        }
        if(used!=31||selected.size()<5||group.space->distances[code]>14)continue;
        vector<Gate> prefix(current.begin(),current.begin()+start),suffixGates;
        int nextSelected=0;
        for(int position=start;position<int(current.size());position++) {if(nextSelected<int(selected.size())&&position==selected[nextSelected])nextSelected++;else suffixGates.push_back(current[position]);}
        array<int,MAXN> startReady{},endReady{};
        for(const Gate& gate:prefix)startReady[gate.control]=startReady[gate.target]=max(startReady[gate.control],startReady[gate.target])+gate.duration;
        for(auto iter=suffixGates.rbegin();iter!=suffixGates.rend();iter++)endReady[iter->control]=endReady[iter->target]=max(endReady[iter->control],endReady[iter->target])+iter->duration;
        LocalSolver solver{group,{},{},depth(current,instance.size)+1,{}};
        for(int vertex=0;vertex<5;vertex++) {solver.start[vertex]=startReady[group.vertices[vertex]];solver.tail[vertex]=endReady[group.vertices[vertex]];}
        const auto& profiles=solver.solve(code);
        if(!profiles.empty()) {
            const auto& profile=*min_element(profiles.begin(),profiles.end(),[&](const Profile& first,const Profile& second){return solver.value(first)<solver.value(second);});
            vector<Gate> candidate=prefix;for(int action:profile.path)candidate.push_back(group.gates[action]);candidate.insert(candidate.end(),suffixGates.begin(),suffixGates.end());
            double currentQuality=quality(instance,current),candidateQuality=quality(instance,candidate);
            if(candidateQuality<currentQuality+1e-8&&(candidateQuality<currentQuality-1e-8||uniform()<.05))current=move(candidate);
        }
        if(iteration%100==0)current=schedule(simplify(current),instance.size,20);
        double currentQuality=quality(instance,current);
        if(currentQuality<bestQuality-1e-8) {bestQuality=currentQuality;best=current;save(instance,best,suffix);cerr<<"improved "<<iteration<<" count "<<best.size()<<" depth "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;}
        if(iteration%1000==999) {current=best;for(int pass=0;pass<20;pass++)for(int position=0;position+1<int(current.size());position++)if(commute(current[position],current[position+1])&&uniform()<.5)swap(current[position],current[position+1]);}
    }
}
