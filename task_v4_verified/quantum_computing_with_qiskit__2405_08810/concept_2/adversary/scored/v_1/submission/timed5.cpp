#include "five.cpp"
#include "timed.cpp"
int main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);const Instance& instance=instances[target];ifstream input(argv[2]);
    int length,oldDepth;input>>length>>oldDepth;vector<Gate> best;
    for(int position=0;position<length;position++) {int control,target;input>>control>>target;best.push_back({control,target,instance.duration[control][target]});}
    double seconds=stod(argv[3]);string suffix=argv[4];rng.seed(stoull(argv[5]));auto started=chrono::steady_clock::now();
    auto five=fiveGroups(instance);vector<TimedGroup> localGroups;
    for(const FiveGroup& source:five) {TimedGroup group;group.size=5;group.identity=source.space->identity;group.vertices.assign(source.vertices.begin(),source.vertices.end());group.native=source.gates;group.endpoints=source.space->edges;group.distances=&source.space->distances;localGroups.push_back(move(group));}
    cerr<<"groups "<<localGroups.size()<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    double bestQuality=quality(instance,best);vector<Gate> current=best;bool reversed=false;int queries=0;
    save(instance,best,suffix);
    for(int iteration=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;iteration++) {
        const TimedGroup& group=localGroups[rng()%localGroups.size()];array<int,MAXN> local;local.fill(-1);for(int vertex=0;vertex<5;vertex++)local[group.vertices[vertex]]=vertex;
        vector<int> starts;for(int position=0;position<int(current.size());position++)if(local[current[position].control]>=0&&local[current[position].target]>=0)starts.push_back(position);
        if(starts.empty())continue;int start=starts[rng()%starts.size()],code=group.identity;vector<int> selected;vector<Gate> obstacles;
        for(int finish=start;finish<int(current.size())&&selected.size()<20;finish++) {
            const Gate& gate=current[finish];bool usable=local[gate.control]>=0&&local[gate.target]>=0;
            if(usable)for(const Gate& obstacle:obstacles)if(!commute(gate,obstacle)) {usable=false;break;}
            if(!usable) {obstacles.push_back(gate);continue;}
            selected.push_back(finish);code^=((code>>(local[gate.control]*5))&31)<<(local[gate.target]*5);
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
        for(int vertex=0;vertex<5;vertex++) {
            int bound=oldReady[group.vertices[vertex]]+suffixReady[group.vertices[vertex]];
            if(bound>focusBound||(bound==focusBound&&uniform()<.3)) {focusBound=bound;focus=vertex;}
        }
        if(focus<0||focusBound<wanted-2)continue;
        queries++;TimedSolver solver(group);solver.maxNodes=100000;array<int,5> startReady{};
        for(int vertex=0;vertex<5;vertex++) {solver.limit[vertex]=wanted-suffixReady[group.vertices[vertex]];startReady[vertex]=prefixReady[group.vertices[vertex]];}
        solver.limit[focus]--;
        solver.budget=min(int(selected.size())+4,max(instance.capCount,int(current.size()))-int(current.size())+int(selected.size()));
        if(solver.search(code,inverseCode(code,5),startReady,0,-1)) {
            vector<Gate> candidate=prefix;for(int action:solver.answer)candidate.push_back(group.native[action]);candidate.insert(candidate.end(),suffixGates.begin(),suffixGates.end());candidate=schedule(simplify(candidate),instance.size,30);
            if(smoothDepth(candidate,instance.size)<smoothDepth(current,instance.size)-1e-8)current=move(candidate);
            double score=quality(instance,current);
            if(score<bestQuality) {bestQuality=score;best=current;if(reversed)reverse(best.begin(),best.end());save(instance,best,suffix);cerr<<"improved "<<iteration<<" queries "<<queries<<" count "<<best.size()<<" depth "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;}
        }
        if(queries%500==0) {current=best;reversed=uniform()<.5;if(reversed)reverse(current.begin(),current.end());for(int pass=0;pass<20;pass++)for(int position=0;position+1<int(current.size());position++)if(commute(current[position],current[position+1])&&uniform()<.5)swap(current[position],current[position+1]);}
        if(queries%1000==0)cerr<<"queries "<<queries<<" best "<<best.size()<<" "<<depth(best,instance.size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    }
}
