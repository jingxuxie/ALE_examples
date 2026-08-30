#include "search.cpp"
#include <unordered_map>
#include <unordered_set>
struct BeamNode {
    State state;
    vector<unsigned short> path;
    double value;
    uint64_t hash;
    array<unsigned short,MAXN> leftReady{},rightReady{};
};
struct Expansion {
    double score,value;
    int parent,action;
    uint64_t hash;
};
struct Move {vector<int> actions;};
uint64_t bitHash[MAXN][MAXN];
uint64_t rowHash[MAXN][5][256],colHash[MAXN][5][256];
uint64_t hashBits(Word bits,int index,bool columns) {
    uint64_t result=0;
    for(int byte=0;byte<5;byte++) {result^=columns?colHash[index][byte][bits&255]:rowHash[index][byte][bits&255];bits>>=8;}
    return result;
}
void initHashes(int size) {
    for(int row=0;row<size;row++)for(int col=0;col<size;col++)bitHash[row][col]=rng();
    for(int vertex=0;vertex<size;vertex++)for(int byte=0;byte<5;byte++)for(int value=0;value<256;value++) {
        for(int bit=0;bit<8;bit++)if(value>>bit&1) {
            rowHash[vertex][byte][value]^=bitHash[vertex][byte*8+bit];
            colHash[vertex][byte][value]^=bitHash[byte*8+bit][vertex];
        }
    }
}
int main(int argc,char** argv) {
    auto instances=load();int target=argc>1?stoi(argv[1]):0;int width=argc>2?stoi(argv[2]):500;
    int mode=argc>3?stoi(argv[3]):0;double distanceWeight=argc>4?stod(argv[4]):.2;
    double invFactor=argc>5?stod(argv[5]):1;double depthFactor=argc>6?stod(argv[6]):0;
    const Instance& instance=instances[target];int size=instance.size,edgeCount=instance.gates.size();
    initHashes(size);
    Heuristic heuristic;heuristic.invFactor=invFactor;
    if(argc>7)heuristic.logFactor=stod(argv[7]);
    int macroMode=argc>8?stoi(argv[8]):0;
    double countFactor=argc>9?stod(argv[9]):0;
    vector<Move> moves;
    int edgeIndex[MAXN][MAXN];fill(&edgeIndex[0][0],&edgeIndex[0][0]+MAXN*MAXN,-1);
    for(int index=0;index<edgeCount;index++)edgeIndex[instance.gates[index].control][instance.gates[index].target]=index;
    for(int action=0;action<2*edgeCount;action++)if(!(mode==1&&action>=edgeCount)&&!(mode==2&&action<edgeCount))moves.push_back({{action}});
    if(macroMode)for(int side=0;side<2;side++) {
        if((mode==1&&side==1)||(mode==2&&side==0))continue;
        for(int index=0;index<edgeCount;index++) {
            const Gate& gate=instance.gates[index];int reverse=edgeIndex[gate.target][gate.control];
            moves.push_back({{side*edgeCount+index,side*edgeCount+reverse}});
            if(gate.duration<=instance.gates[reverse].duration)moves.push_back({{side*edgeCount+index,side*edgeCount+reverse,side*edgeCount+index}});
            if(macroMode>1)for(int next=0;next<edgeCount;next++)if(instance.gates[next].control==gate.target&&instance.gates[next].target!=gate.control) {
                moves.push_back({{side*edgeCount+index,side*edgeCount+next,side*edgeCount+index,side*edgeCount+next}});
            }
        }
    }
    double diagonalWeight=argc>11?stod(argv[11]):1;
    for(int row=0;row<size;row++)for(int col=0;col<size;col++)heuristic.weights[row][col]=row==col?diagonalWeight:1+distanceWeight*instance.distance[row][col];
    BeamNode root;root.state=initial(instance);root.value=heuristic.value(root.state,size);root.hash=0;
    for(int row=0;row<size;row++)root.hash^=hashBits(root.state.rows[row],row,false);
    vector<BeamNode> beam{root};
    unordered_set<uint64_t> seen;seen.insert(root.hash);
    auto started=chrono::steady_clock::now();
    for(int step=0;step<instance.capCount*2;step++) {
        vector<Expansion> expansions;expansions.reserve(beam.size()*edgeCount*2);
        for(int parent=0;parent<int(beam.size());parent++) {
            const BeamNode& node=beam[parent];
            if(solved(node.state,size)) {
                vector<Gate> left,right;
                for(int action:node.path)(action/edgeCount==0?left:right).push_back(instance.gates[action%edgeCount]);
                vector<Gate> circuit=right;for(auto iter=left.rbegin();iter!=left.rend();iter++)circuit.push_back(*iter);
                circuit=schedule(simplify(circuit),size,100);
                cerr<<"SOLVED "<<instance.name<<" "<<circuit.size()<<" "<<depth(circuit,size)<<endl;
                save(instance,circuit,argc>10?argv[10]:"beam");return 0;
            }
            for(int moveIndex=0;moveIndex<int(moves.size());moveIndex++) {
                const Move& move=moves[moveIndex];
                uint64_t hash=node.hash;double value=node.value;State temporary=node.state;
                for(int action:move.actions) {
                    const Gate& gate=instance.gates[action%edgeCount];int side=action/edgeCount;
                    hash^=side==0?hashBits(temporary.rows[gate.control],gate.target,false):hashBits(temporary.cols[gate.target],gate.control,true);
                    value+=heuristic.difference(temporary,gate,side);
                    if(move.actions.size()>1)apply(temporary,gate,side);
                }
                if(seen.count(hash))continue;
                double score=value+countFactor*(node.path.size()+move.actions.size());
                if(depthFactor) {
                    auto leftReady=node.leftReady,rightReady=node.rightReady;
                    for(int action:move.actions) {
                        const Gate& gate=instance.gates[action%edgeCount];int side=action/edgeCount;
                        auto& ready=side==0?leftReady:rightReady;
                        ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;
                    }
                    int combinedDepth=0;
                    for(int vertex=0;vertex<size;vertex++)combinedDepth=max(combinedDepth,int(leftReady[vertex]+rightReady[vertex]));
                    score+=depthFactor*combinedDepth;
                }
                expansions.push_back({score,value,parent,moveIndex,hash});
            }
        }
        sort(expansions.begin(),expansions.end(),[](const Expansion& first,const Expansion& second){return first.score<second.score;});
        vector<BeamNode> next;next.reserve(width);
        for(const Expansion& expansion:expansions) {
            if(!seen.insert(expansion.hash).second)continue;
            BeamNode node=beam[expansion.parent];node.value=expansion.value;node.hash=expansion.hash;
            for(int action:moves[expansion.action].actions) {
                node.path.push_back(action);
                const Gate& gate=instance.gates[action%edgeCount];int side=action/edgeCount;
                apply(node.state,gate,side);
                auto& ready=side==0?node.leftReady:node.rightReady;
                ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;
            }
            next.push_back(move(node));if(int(next.size())>=width)break;
        }
        beam=move(next);if(beam.empty())break;
        if(step%10==0) {
            int residual=0;for(int row=0;row<size;row++)residual+=weight(beam[0].state.rows[row]^(Word(1)<<row));
            int combinedDepth=0;for(int vertex=0;vertex<size;vertex++)combinedDepth=max(combinedDepth,int(beam[0].leftReady[vertex]+beam[0].rightReady[vertex]));
            cerr<<"step "<<step+1<<" count "<<beam[0].path.size()<<" depth "<<combinedDepth<<" h "<<beam[0].value<<" residual "<<residual<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
        }
    }
    return 1;
}
