#include "optimize.cpp"
#include <unordered_map>
#include <unordered_set>
struct MiddleGroup {vector<int> vertices;vector<Gate> gates;vector<pair<int,int>> edges;Word identity;};
vector<MiddleGroup> middleGroups(const Instance& instance,int size) {
    array<Word,MAXN> adjacency{};for(const Gate& gate:instance.gates)adjacency[gate.control]|=Word(1)<<gate.target;
    unordered_set<Word> sets;for(int vertex=0;vertex<instance.size;vertex++)sets.insert(Word(1)<<vertex);
    for(int count=1;count<size;count++) {
        unordered_set<Word> next;
        for(Word selected:sets) {
            Word neighbors=0,bits=selected;
            while(bits) {int vertex=__builtin_ctzll(bits);bits&=bits-1;neighbors|=adjacency[vertex];}
            neighbors&=~selected;
            while(neighbors) {Word addition=neighbors&-neighbors;neighbors&=neighbors-1;next.insert(selected|addition);}
        }
        sets=move(next);
    }
    vector<MiddleGroup> result;
    for(Word selected:sets) {
        MiddleGroup group;group.identity=0;Word bits=selected;
        while(bits) {group.vertices.push_back(__builtin_ctzll(bits));bits&=bits-1;}
        for(int vertex=0;vertex<size;vertex++)group.identity|=Word(1)<<(vertex*size+vertex);
        for(int control=0;control<size;control++)for(int target=0;target<size;target++) {
            int physicalControl=group.vertices[control],physicalTarget=group.vertices[target];
            if(instance.duration[physicalControl][physicalTarget]) {group.gates.push_back({physicalControl,physicalTarget,instance.duration[physicalControl][physicalTarget]});group.edges.push_back({control,target});}
        }
        result.push_back(move(group));
    }
    return result;
}
struct MiddleNode {Word code;int parent,cost;unsigned char action,distance;};
struct MiddleTable {
    vector<MiddleNode> nodes;
    unordered_map<Word,int> index;
    MiddleTable(const MiddleGroup& group,int radius,Word initial) {
        int size=group.vertices.size();nodes.reserve(100000);index.reserve(100000);nodes.push_back({initial,-1,0,0,0});index[initial]=0;
        for(int position=0;position<int(nodes.size());position++) {
            MiddleNode node=nodes[position];if(node.distance>=radius)continue;
            for(int action=0;action<int(group.gates.size());action++) {
                auto [control,target]=group.edges[action];Word next=node.code^(((node.code>>(control*size))&((Word(1)<<size)-1))<<(target*size));
                int cost=node.cost+group.gates[action].duration;
                auto found=index.find(next);
                if(found==index.end()) {int nextIndex=nodes.size();index[next]=nextIndex;nodes.push_back({next,position,cost,static_cast<unsigned char>(action),static_cast<unsigned char>(node.distance+1)});}
                else {MiddleNode& previous=nodes[found->second];if(previous.distance==node.distance+1&&cost<previous.cost) {previous.parent=position;previous.action=action;previous.cost=cost;}}
            }
        }
    }
    vector<int> path(int position,bool reversePath) const {
        vector<int> result;while(nodes[position].parent>=0) {result.push_back(nodes[position].action);position=nodes[position].parent;}
        if(reversePath)reverse(result.begin(),result.end());return result;
    }
};
int middle_main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);const Instance& instance=instances[target];
    ifstream input(argv[2]);int length,oldDepth;input>>length>>oldDepth;vector<Gate> best;
    for(int position=0;position<length;position++) {int control,target;input>>control>>target;best.push_back({control,target,instance.duration[control][target]});}
    double seconds=stod(argv[3]);string suffix=argv[4];rng.seed(stoull(argv[5]));
    int localSize=argc>6?stoi(argv[6]):6,radius=argc>7?stoi(argv[7]):6;
    auto started=chrono::steady_clock::now();auto groups=middleGroups(instance,localSize);
    cerr<<"groups "<<groups.size()<<endl;double bestQuality=quality(instance,best);vector<Gate> current=best;save(instance,best,suffix);
    for(int iteration=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;iteration++) {
        const MiddleGroup& group=groups[rng()%groups.size()];MiddleTable forward(group,radius,group.identity);
        array<int,MAXN> local;local.fill(-1);for(int vertex=0;vertex<localSize;vertex++)local[group.vertices[vertex]]=vertex;
        vector<int> starts;for(int position=0;position<int(current.size());position++)if(local[current[position].control]>=0&&local[current[position].target]>=0)starts.push_back(position);
        shuffle(starts.begin(),starts.end(),rng);
        for(int start:starts) {
            if(start>=int(current.size())||chrono::duration<double>(chrono::steady_clock::now()-started).count()>seconds)break;
            Word code=group.identity;int used=0;vector<int> selected;vector<Gate> obstacles;int maxLength=7+rng()%11;
            for(int finish=start;finish<int(current.size())&&int(selected.size())<maxLength;finish++) {
                const Gate& gate=current[finish];bool usable=local[gate.control]>=0&&local[gate.target]>=0;
                if(usable)for(const Gate& obstacle:obstacles)if(!commute(gate,obstacle)) {usable=false;break;}
                if(!usable) {obstacles.push_back(gate);continue;}
                selected.push_back(finish);used|=(1<<local[gate.control])|(1<<local[gate.target]);code^=((code>>(local[gate.control]*localSize))&((Word(1)<<localSize)-1))<<(local[gate.target]*localSize);
            }
            if(__builtin_popcount(used)<4||selected.size()<5)continue;
            vector<Gate> prefix(current.begin(),current.begin()+start),suffixGates;int nextSelected=0;
            for(int position=start;position<int(current.size());position++) {if(nextSelected<int(selected.size())&&position==selected[nextSelected])nextSelected++;else suffixGates.push_back(current[position]);}
            array<int,MAXN> prefixReady{},suffixReady{};
            for(const Gate& gate:prefix)prefixReady[gate.control]=prefixReady[gate.target]=max(prefixReady[gate.control],prefixReady[gate.target])+gate.duration;
            for(auto iter=suffixGates.rbegin();iter!=suffixGates.rend();iter++)suffixReady[iter->control]=suffixReady[iter->target]=max(suffixReady[iter->control],suffixReady[iter->target])+iter->duration;
            MiddleTable backward(group,min(radius,int(selected.size())),code);
            double currentQuality=quality(instance,current),bestCandidateQuality=currentQuality;vector<int> bestPath;
            for(int position=0;position<int(backward.nodes.size());position++) {
                const MiddleNode& node=backward.nodes[position];auto found=forward.index.find(node.code);if(found==forward.index.end())continue;
                int newLength=node.distance+forward.nodes[found->second].distance;if(newLength>int(selected.size())+2)continue;
                auto path=forward.path(found->second,true);auto second=backward.path(position,false);path.insert(path.end(),second.begin(),second.end());
                auto ready=prefixReady;
                for(int action:path) {const Gate& gate=group.gates[action];ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;}
                int candidateDepth=0;for(int vertex=0;vertex<instance.size;vertex++)candidateDepth=max(candidateDepth,ready[vertex]+suffixReady[vertex]);
                int candidateCount=current.size()-selected.size()+newLength;double worst=max(double(candidateCount)/instance.capCount,double(candidateDepth)/instance.capDepth);
                double candidateQuality=(worst<=1?.9:worst)+.0001*(candidateCount+candidateDepth);
                if(candidateQuality<bestCandidateQuality-1e-8||(candidateQuality<=bestCandidateQuality+1e-8&&uniform()<.005)) {bestCandidateQuality=candidateQuality;bestPath=move(path);}
            }
            if(!bestPath.empty()) {
                vector<Gate> candidate=prefix;for(int action:bestPath)candidate.push_back(group.gates[action]);candidate.insert(candidate.end(),suffixGates.begin(),suffixGates.end());current=move(candidate);
            }
            double currentScore=quality(instance,current);
            if(currentScore<bestQuality-1e-8) {bestQuality=currentScore;best=current;save(instance,best,suffix);cerr<<"improved "<<iteration<<" count "<<best.size()<<" depth "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;}
        }
        current=schedule(simplify(current),instance.size,30);
        if(quality(instance,current)<bestQuality-1e-8) {bestQuality=quality(instance,current);best=current;save(instance,best,suffix);cerr<<"scheduled "<<best.size()<<" "<<depth(best,instance.size)<<endl;}
        if(iteration%10==9) {current=best;for(int pass=0;pass<20;pass++)for(int position=0;position+1<int(current.size());position++)if(commute(current[position],current[position+1])&&uniform()<.5)swap(current[position],current[position+1]);}
        if(iteration%20==0)cerr<<"progress "<<iteration<<" "<<best.size()<<" "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    }
}
