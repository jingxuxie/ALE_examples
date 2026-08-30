#include "search.cpp"
#include <queue>
struct Elimination {
    State state;
    Word active;
    vector<Gate> left,right;
};
vector<int> candidates(const Instance& instance,Word active) {
    vector<int> result;
    for(int root=0;root<instance.size;root++)if(active>>root&1) {
        Word remain=active^(Word(1)<<root),reached=0;
        if(remain) {
            int start=__builtin_ctzll(remain);reached=Word(1)<<start;
            vector<int> queue{start};
            for(int pos=0;pos<int(queue.size());pos++)for(const Gate& gate:instance.gates)if(gate.control==queue[pos]&&(remain>>gate.target&1)&&!(reached>>gate.target&1)) {queue.push_back(gate.target);reached|=Word(1)<<gate.target;}
        }
        if(reached==remain)result.push_back(root);
    }
    return result;
}
vector<vector<int>> tree(const Instance& instance,Word active,Word terminals,int root,double noise,double durationFactor) {
    int size=instance.size;
    vector<vector<int>> adjacency(size);
    Word reached=Word(1)<<root;
    while(terminals&~reached) {
        array<double,MAXN> distance;distance.fill(1e100);
        array<int,MAXN> parent;parent.fill(-1);
        Word visited=~active;
        for(int vertex=0;vertex<size;vertex++)if(reached>>vertex&1)distance[vertex]=0;
        int closest=-1;
        for(int iteration=0;iteration<size;iteration++) {
            int vertex=-1;
            for(int other=0;other<size;other++)if(!(visited>>other&1)&&(vertex<0||distance[other]<distance[vertex]))vertex=other;
            if(vertex<0)break;
            if((terminals>>vertex&1)&&!(reached>>vertex&1)) {closest=vertex;break;}
            visited|=Word(1)<<vertex;
            for(const Gate& gate:instance.gates)if(gate.control==vertex&&!(visited>>gate.target&1)) {
                double cost=1+durationFactor*gate.duration+noise*uniform();
                if(distance[gate.target]>distance[vertex]+cost) {distance[gate.target]=distance[vertex]+cost;parent[gate.target]=vertex;}
            }
        }
        if(closest<0)throw runtime_error("tree disconnected");
        int vertex=closest;
        while(!(reached>>vertex&1)) {
            reached|=Word(1)<<vertex;int previous=parent[vertex];
            adjacency[vertex].push_back(previous);adjacency[previous].push_back(vertex);vertex=previous;
        }
    }
    for(auto& neighbors:adjacency)shuffle(neighbors.begin(),neighbors.end(),rng);
    return adjacency;
}
void eliminateTree(Elimination& elimination,const Instance& instance,const vector<vector<int>>& adjacency,int vertex,int parent,int root,int side) {
    for(int child:adjacency[vertex])if(child!=parent) {
        eliminateTree(elimination,instance,adjacency,child,vertex,root,side);
        Word bits=side==0?elimination.state.cols[root]:elimination.state.rows[root];
        if(!(bits>>child&1))continue;
        if(!(bits>>vertex&1)) {
            int control=side==0?child:vertex,target=side==0?vertex:child;
            Gate gate{control,target,instance.duration[control][target]};apply(elimination.state,gate,side);(side==0?elimination.left:elimination.right).push_back(gate);
        }
        int control=side==0?vertex:child,target=side==0?child:vertex;
        Gate gate{control,target,instance.duration[control][target]};apply(elimination.state,gate,side);(side==0?elimination.left:elimination.right).push_back(gate);
    }
}
void eliminate(Elimination& elimination,const Instance& instance,int root,int firstSide,double noise,double durationFactor) {
    for(int order=0;order<2;order++) {
        int side=order^firstSide;
        Word terminals=side==0?elimination.state.cols[root]:elimination.state.rows[root];
        terminals&=elimination.active;
        auto adjacency=tree(instance,elimination.active,terminals,root,noise,durationFactor);
        eliminateTree(elimination,instance,adjacency,root,-1,root,side);
    }
    elimination.active^=Word(1)<<root;
}
int main(int argc,char** argv) {
    auto instances=load();int target=argc>1?stoi(argv[1]):0;double seconds=argc>2?stod(argv[2]):60;
    if(argc>3)rng.seed(stoull(argv[3]));
    const Instance& instance=instances[target];int size=instance.size;
    auto started=chrono::steady_clock::now();double bestQuality=1e100;int bestCount=100000,bestDepth=100000;
    for(int trial=0;chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds;trial++) {
        Elimination elimination{initial(instance),(Word(1)<<size)-1,{},{}};
        double noise=uniform(),durationFactor=uniform()*.3;
        double countFactor=2+uniform()*4,remainingFactor=uniform()*.6,randomFactor=uniform()*15;
        Heuristic heuristic;heuristic.invFactor=uniform();
        for(int row=0;row<size;row++)for(int col=0;col<size;col++)heuristic.weights[row][col]=1;
        while(elimination.active) {
            auto roots=candidates(instance,elimination.active);
            double bestScore=1e100;Elimination best;
            for(int root:roots)for(int side=0;side<2;side++) {
                Elimination candidate=elimination;
                eliminate(candidate,instance,root,side,noise,durationFactor);
                double score=countFactor*(candidate.left.size()+candidate.right.size())+remainingFactor*heuristic.value(candidate.state,size)+randomFactor*uniform();
                if(score<bestScore) {bestScore=score;best=move(candidate);}
            }
            elimination=move(best);
        }
        if(!solved(elimination.state,size))throw runtime_error("not identity");
        vector<Gate> circuit=elimination.right;for(auto iter=elimination.left.rbegin();iter!=elimination.left.rend();iter++)circuit.push_back(*iter);
        circuit=schedule(simplify(circuit),size,10);
        int count=circuit.size(),currentDepth=depth(circuit,size);
        double quality=max(double(count)/instance.capCount,double(currentDepth)/instance.capDepth)+.0001*(count+currentDepth);
        if(quality<bestQuality) {
            bestQuality=quality;bestCount=count;bestDepth=currentDepth;save(instance,circuit,"steiner");
            cerr<<instance.name<<" trial "<<trial<<" count "<<count<<" depth "<<currentDepth<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
        }
        if(trial%100==0)cerr<<"progress "<<trial<<" best "<<bestCount<<" "<<bestDepth<<endl;
    }
}
