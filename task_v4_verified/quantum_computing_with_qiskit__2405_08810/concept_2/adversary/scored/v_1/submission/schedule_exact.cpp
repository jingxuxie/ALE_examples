#include "search.cpp"
struct Scheduler {
    int size,cap;
    vector<int> duration;
    vector<pair<int,int>> conflicts;
    vector<int> answer;
    chrono::steady_clock::time_point deadline;
    uint64_t nodes=0;
    bool expired=false;
    void order(vector<int>& distance,int first,int second) {
        vector<int> before(size),after(size);
        for(int vertex=0;vertex<size;vertex++) {before[vertex]=distance[vertex*size+first];after[vertex]=distance[second*size+vertex];}
        for(int row=0;row<size;row++)if(before[row]>=0)for(int col=0;col<size;col++)if(after[col]>=0)distance[row*size+col]=max(distance[row*size+col],before[row]+duration[first]+after[col]);
    }
    bool search(vector<int> distance) {
        nodes++;
        if(nodes%1000==0&&chrono::steady_clock::now()>deadline) {expired=true;return false;}
        int choiceFirst=-1,choiceSecond=-1,bestPriority=1000000000;bool preferForward=true;
        while(true) {
            bool forced=false;choiceFirst=-1;
            for(auto [first,second]:conflicts) {
                if(distance[first*size+second]>=0||distance[second*size+first]>=0)continue;
                int forwardBound=distance[first]+duration[first]+distance[second*size+size-1];
                int backwardBound=distance[second]+duration[second]+distance[first*size+size-1];
                bool forward=forwardBound<=cap,backward=backwardBound<=cap;
                if(!forward&&!backward)return false;
                if(!forward||!backward) {order(distance,forward?first:second,forward?second:first);forced=true;break;}
                int priority=2*cap-forwardBound-backwardBound;
                if(choiceFirst<0||priority<bestPriority) {choiceFirst=first;choiceSecond=second;bestPriority=priority;preferForward=forwardBound<=backwardBound;}
            }
            if(!forced)break;
        }
        if(choiceFirst<0) {answer=move(distance);return true;}
        int first=preferForward?choiceFirst:choiceSecond,second=preferForward?choiceSecond:choiceFirst;
        auto next=distance;order(next,first,second);
        if(search(move(next)))return true;
        if(expired)return false;
        order(distance,second,first);return search(move(distance));
    }
};
int main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);const Instance& instance=instances[target];ifstream input(argv[2]);
    int length,oldDepth;input>>length>>oldDepth;vector<Gate> circuit;
    for(int position=0;position<length;position++) {int control,target;input>>control>>target;circuit.push_back({control,target,instance.duration[control][target]});}
    double seconds=argc>3?stod(argv[3]):60;int size=length+2;
    vector<int> initial(size*size,-1000000);for(int vertex=0;vertex<size;vertex++)initial[vertex*size+vertex]=0;
    Scheduler solver;solver.size=size;solver.duration.resize(size);solver.deadline=chrono::steady_clock::now()+chrono::milliseconds(int(seconds*1000));
    for(int first=0;first<length;first++) {
        solver.duration[first+1]=circuit[first].duration;initial[first+1]=0;initial[(first+1)*size+size-1]=circuit[first].duration;
        for(int second=first+1;second<length;second++) {
            if(!commute(circuit[first],circuit[second]))initial[(first+1)*size+second+1]=circuit[first].duration;
            else if(circuit[first].control==circuit[second].control||circuit[first].target==circuit[second].target)solver.conflicts.push_back({first+1,second+1});
        }
    }
    for(int middle=0;middle<size;middle++)for(int row=0;row<size;row++)if(initial[row*size+middle]>=0)for(int col=0;col<size;col++)if(initial[middle*size+col]>=0)initial[row*size+col]=max(initial[row*size+col],initial[row*size+middle]+initial[middle*size+col]);
    cerr<<"lower "<<initial[size-1]<<" original "<<oldDepth<<" conflicts "<<solver.conflicts.size()<<endl;
    for(int cap=max(instance.capDepth,initial[size-1]);cap<oldDepth;cap++) {
        solver.cap=cap;solver.expired=false;
        if(solver.search(initial)) {
            vector<int> indices(length);iota(indices.begin(),indices.end(),0);sort(indices.begin(),indices.end(),[&](int first,int second){return solver.answer[first+1]<solver.answer[second+1];});
            vector<Gate> result;for(int position:indices)result.push_back(circuit[position]);
            cerr<<"SOLVED "<<result.size()<<" "<<depth(result,instance.size)<<" nodes "<<solver.nodes<<endl;save(instance,result,argc>4?argv[4]:"scheduled");return 0;
        }
        cerr<<"infeasible "<<cap<<" nodes "<<solver.nodes<<" timeout "<<solver.expired<<endl;
        if(solver.expired)break;
    }
}
