#include "optimize.cpp"
#include <unordered_set>
struct SeenRecord {
    array<unsigned short,MAXN> left,right;
    int count;
    double score;
};
struct BlockElement {
    array<int,3> masks,inverseMasks;
    vector<int> actions;
    int duration;
    int clock[2][3][3];
};
struct Block {
    vector<int> vertices;
    vector<BlockElement> elements;
};
struct BlockNode {
    State state;
    vector<unsigned short> path;
    double value;
    array<unsigned short,MAXN> leftReady{},rightReady{};
};
struct BlockExpansion {
    double score,value;
    int parent,block,element,side;
    bool operator<(const BlockExpansion& other)const {return score<other.score;}
};
uint64_t mix(uint64_t value) {value^=value>>30;value*=0xbf58476d1ce4e5b9ULL;value^=value>>27;value*=0x94d049bb133111ebULL;return value^(value>>31);}
uint64_t stateHash(const State& state,int size) {uint64_t hash=0;for(int row=0;row<size;row++)hash^=mix(state.rows[row]+0x9e3779b97f4a7c15ULL*(row+1));return hash;}
int main(int argc,char** argv) {
    auto instances=load();int target=stoi(argv[1]);Instance instance=instances[target];
    if(argc>12&&string(argv[12])!="-") {
        ifstream matrixInput(argv[12]);
        for(int row=0;row<instance.size;row++)matrixInput>>instance.original[row];
        matrixInput>>instance.capCount>>instance.capDepth;
        auto rows=instance.original;
        for(int row=0;row<instance.size;row++)instance.inverse[row]=Word(1)<<row;
        for(int col=0;col<instance.size;col++) {
            if(!(rows[col]>>col&1))for(int row=col+1;row<instance.size;row++)if(rows[row]>>col&1) {swap(rows[col],rows[row]);swap(instance.inverse[col],instance.inverse[row]);break;}
            for(int row=0;row<instance.size;row++)if(row!=col&&(rows[row]>>col&1)) {rows[row]^=rows[col];instance.inverse[row]^=instance.inverse[col];}
        }
    }
    int width=stoi(argv[2]);double distanceWeight=stod(argv[3]),diagonalWeight=stod(argv[4]),inverseFactor=stod(argv[5]);
    double countFactor=stod(argv[6]),depthFactor=stod(argv[7]);string suffix=argv[8];
    if(argc>9)rng.seed(stoull(argv[9]));
    double noise=argc>10?stod(argv[10]):0;
    bool decay=argc>11?stoi(argv[11]):false;
    int hardDepth=argc>13?stoi(argv[13]):0;
    bool softBounds=argc>14?stoi(argv[14]):false;
    int edgeCount=instance.gates.size(),size=instance.size;
    int travel[MAXN][MAXN];
    for(int control=0;control<size;control++)for(int target=0;target<size;target++)travel[control][target]=control==target?0:10000;
    for(const Gate& gate:instance.gates)travel[gate.control][gate.target]=gate.duration;
    for(int middle=0;middle<size;middle++)for(int control=0;control<size;control++)for(int target=0;target<size;target++)travel[control][target]=min(travel[control][target],travel[control][middle]+travel[middle][target]);
    int edgeIndex[MAXN][MAXN];fill(&edgeIndex[0][0],&edgeIndex[0][0]+MAXN*MAXN,-1);
    for(int index=0;index<edgeCount;index++)edgeIndex[instance.gates[index].control][instance.gates[index].target]=index;
    auto localGroups=groups(instance,3,100);
    vector<Block> blocks;
    for(const LocalGroup& group:localGroups) {
        Block block;block.vertices=group.vertices;
        for(int code=0;code<int(group.costs.size());code++)if(group.costs[code]<1000000000&&code!=group.identity) {
            BlockElement element;array<int,3> rows,inverse;
            for(int row=0;row<3;row++) {element.masks[row]=rows[row]=code>>(row*3)&7;inverse[row]=1<<row;}
            for(int col=0;col<3;col++) {
                if(!(rows[col]>>col&1))for(int row=col+1;row<3;row++)if(rows[row]>>col&1) {swap(rows[col],rows[row]);swap(inverse[col],inverse[row]);break;}
                for(int row=0;row<3;row++)if(row!=col&&(rows[row]>>col&1)) {rows[row]^=rows[col];inverse[row]^=inverse[col];}
            }
            for(int col=0;col<3;col++) {element.inverseMasks[col]=0;for(int row=0;row<3;row++)element.inverseMasks[col]|=(inverse[row]>>col&1)<<row;}
            element.duration=0;
            for(int side=0;side<2;side++)for(int row=0;row<3;row++)for(int col=0;col<3;col++)element.clock[side][row][col]=row==col?0:-10000;
            for(const Gate& gate:group.circuit(code)) {
                element.actions.push_back(edgeIndex[gate.control][gate.target]);element.duration+=gate.duration;
                int control=find(group.vertices.begin(),group.vertices.end(),gate.control)-group.vertices.begin();
                int target=find(group.vertices.begin(),group.vertices.end(),gate.target)-group.vertices.begin();
                for(int side=0;side<2;side++)for(int col=0;col<3;col++) {
                    int finish=max(element.clock[side][control][col],element.clock[side][target][col])+(side==0?gate.duration:instance.duration[gate.target][gate.control]);
                    element.clock[side][control][col]=element.clock[side][target][col]=finish;
                }
            }
            block.elements.push_back(move(element));
        }
        blocks.push_back(move(block));
    }
    Heuristic heuristic;heuristic.invFactor=inverseFactor;
    double goalValue=0;
    for(int row=0;row<size;row++)for(int col=0;col<size;col++) {
        heuristic.weights[row][col]=(row==col?diagonalWeight:1+distanceWeight*instance.distance[row][col])*exp(noise*(uniform()-.5));
        if(row==col)goalValue+=heuristic.weights[row][col]*(1+inverseFactor);
    }
    BlockNode root;root.state=initial(instance);root.value=heuristic.value(root.state,size);
    vector<BlockNode> beam{root};unordered_set<uint64_t> seen;seen.insert(stateHash(root.state,size));
    unordered_map<uint64_t,vector<SeenRecord>> records;
    records[stateHash(root.state,size)].push_back({root.leftReady,root.rightReady,0,0});
    auto started=chrono::steady_clock::now();
    for(int step=0;step<200;step++) {
        priority_queue<BlockExpansion> heap;
        int capacity=width*30;
        for(int parent=0;parent<int(beam.size());parent++) {
            const BlockNode& node=beam[parent];
            int rowBounds[MAXN]{},colBounds[MAXN]{};
            if(hardDepth)for(int row=0;row<size;row++) {
                rowBounds[row]=colBounds[row]=node.leftReady[row]+node.rightReady[row];
            }
            if(hardDepth)for(int row=0;row<size;row++) {
                Word bits=node.state.rows[row];
                while(bits) {
                    int col=__builtin_ctzll(bits);bits&=bits-1;
                    int bound=node.leftReady[row]+node.rightReady[col]+travel[col][row];
                    rowBounds[row]=max(rowBounds[row],bound);colBounds[col]=max(colBounds[col],bound);
                }
                bits=node.state.invrows[row];
                while(bits) {
                    int col=__builtin_ctzll(bits);bits&=bits-1;
                    int bound=node.leftReady[col]+node.rightReady[row]+travel[col][row];
                    rowBounds[col]=max(rowBounds[col],bound);colBounds[row]=max(colBounds[row],bound);
                }
            }
            if(solved(node.state,size)) {
                vector<Gate> left,right;
                for(int action:node.path)(action/edgeCount==0?left:right).push_back(instance.gates[action%edgeCount]);
                vector<Gate> circuit=right;for(auto iter=left.rbegin();iter!=left.rend();iter++)circuit.push_back(*iter);
                circuit=schedule(simplify(circuit),size,100);save(instance,circuit,suffix);
                cerr<<"SOLVED "<<circuit.size()<<" "<<depth(circuit,size)<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;return 0;
            }
            for(int blockIndex=0;blockIndex<int(blocks.size());blockIndex++)for(int side=0;side<2;side++) {
                const Block& block=blocks[blockIndex];
                Word combos[8]{},inverseCombos[8]{};
                for(int mask=1;mask<8;mask++) {
                    int slot=__builtin_ctz(mask);int previous=mask&(mask-1),vertex=block.vertices[slot];
                    combos[mask]=combos[previous]^(side==0?node.state.rows[vertex]:node.state.cols[vertex]);
                    inverseCombos[mask]=inverseCombos[previous]^(side==0?node.state.invcols[vertex]:node.state.invrows[vertex]);
                }
                double values[3][8]{},inverseValues[3][8]{};
                int potentials[3][8]{},inversePotentials[3][8]{},outsideBound=0,outsideSum=0;
                if(hardDepth)for(int vertex=0;vertex<size;vertex++)if(find(block.vertices.begin(),block.vertices.end(),vertex)==block.vertices.end()) {
                    int bound=side==0?rowBounds[vertex]:colBounds[vertex];outsideBound=max(outsideBound,bound);outsideSum+=bound;
                }
                for(int slot=0;slot<3;slot++)for(int mask=1;mask<8;mask++) {
                    int vertex=block.vertices[slot];Word bits=combos[mask];
                    while(bits) {
                        int other=__builtin_ctzll(bits);bits&=bits-1;values[slot][mask]+=side==0?heuristic.weights[vertex][other]:heuristic.weights[other][vertex];
                        if(hardDepth)potentials[slot][mask]=max(potentials[slot][mask],side==0?node.rightReady[other]+travel[other][vertex]:node.leftReady[other]+travel[vertex][other]);
                    }
                    bits=inverseCombos[mask];
                    while(bits) {
                        int other=__builtin_ctzll(bits);bits&=bits-1;inverseValues[slot][mask]+=inverseFactor*(side==0?heuristic.weights[other][vertex]:heuristic.weights[vertex][other]);
                        if(hardDepth)inversePotentials[slot][mask]=max(inversePotentials[slot][mask],side==0?node.rightReady[other]+travel[vertex][other]:node.leftReady[other]+travel[other][vertex]);
                    }
                }
                double base=0;for(int slot=0;slot<3;slot++)base+=values[slot][1<<slot]+inverseValues[slot][1<<slot];
                for(int elementIndex=0;elementIndex<int(block.elements.size());elementIndex++) {
                    const BlockElement& element=block.elements[elementIndex];double value=node.value-base;
                    for(int slot=0;slot<3;slot++)value+=values[slot][element.masks[slot]]+inverseValues[slot][element.inverseMasks[slot]];
                    double phase=decay?min(1.,max(0.,(value-goalValue)/(size*4*(1+distanceWeight)*(1+inverseFactor)))):1;
                    double score=value+phase*countFactor*(node.path.size()+element.actions.size());
                    if(hardDepth) {
                        int combinedDepth=outsideBound,combinedSum=outsideSum;
                        for(int row=0;row<3;row++) {
                            int finish=0;
                            for(int col=0;col<3;col++)finish=max(finish,int(side==0?node.leftReady[block.vertices[col]]:node.rightReady[block.vertices[col]])+element.clock[side][row][col]);
                            int bound=finish+max({potentials[row][element.masks[row]],inversePotentials[row][element.inverseMasks[row]],int(side==0?node.rightReady[block.vertices[row]]:node.leftReady[block.vertices[row]])});
                            combinedDepth=max(combinedDepth,bound);combinedSum+=bound;
                        }
                        if(combinedDepth>hardDepth)continue;
                        score+=depthFactor*(softBounds?double(combinedSum)/size:combinedDepth);
                    } else if(depthFactor) {
                        auto leftReady=node.leftReady,rightReady=node.rightReady;auto& ready=side==0?leftReady:rightReady;
                        for(int action:element.actions) {
                            Gate gate=instance.gates[action];if(side==1) {swap(gate.control,gate.target);gate.duration=instance.duration[gate.control][gate.target];}
                            ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;
                        }
                        int combinedDepth=0;for(int vertex=0;vertex<size;vertex++)combinedDepth=max(combinedDepth,int(leftReady[vertex]+rightReady[vertex]));
                        score+=phase*depthFactor*combinedDepth;
                    }
                    if(abs(value-goalValue)<1e-6)score=-1e90;
                    if(int(heap.size())<capacity||score<heap.top().score) {heap.push({score,value,parent,blockIndex,elementIndex,side});if(int(heap.size())>capacity)heap.pop();}
                }
            }
        }
        vector<BlockExpansion> expansions;while(!heap.empty()) {expansions.push_back(heap.top());heap.pop();}reverse(expansions.begin(),expansions.end());
        vector<BlockNode> next;
        unordered_map<uint64_t,int> layerCounts;
        for(const BlockExpansion& expansion:expansions) {
            BlockNode node=beam[expansion.parent];node.value=expansion.value;
            for(int action:blocks[expansion.block].elements[expansion.element].actions) {
                Gate gate=instance.gates[action];if(expansion.side==1) {swap(gate.control,gate.target);gate.duration=instance.duration[gate.control][gate.target];action=edgeIndex[gate.control][gate.target];}
                node.path.push_back(action+expansion.side*edgeCount);apply(node.state,gate,expansion.side);
                auto& ready=expansion.side==0?node.leftReady:node.rightReady;ready[gate.control]=ready[gate.target]=max(ready[gate.control],ready[gate.target])+gate.duration;
            }
            uint64_t hash=stateHash(node.state,size);
            if(hardDepth) {
                if(layerCounts[hash]>=3)continue;
                auto& previous=records[hash];bool dominated=false;
                for(const SeenRecord& record:previous) {
                    if(record.count>int(node.path.size()))continue;
                    bool better=true;
                    for(int vertex=0;vertex<size;vertex++)if(record.left[vertex]>node.leftReady[vertex]||record.right[vertex]>node.rightReady[vertex]) {better=false;break;}
                    if(better) {dominated=true;break;}
                }
                if(dominated)continue;
                previous.erase(remove_if(previous.begin(),previous.end(),[&](const SeenRecord& record){
                    if(record.count<int(node.path.size()))return false;
                    for(int vertex=0;vertex<size;vertex++)if(node.leftReady[vertex]>record.left[vertex]||node.rightReady[vertex]>record.right[vertex])return false;
                    return true;
                }),previous.end());
                int maximum=0,total=0;
                for(int vertex=0;vertex<size;vertex++) {int clock=node.leftReady[vertex]+node.rightReady[vertex];maximum=max(maximum,clock);total+=clock;}
                double score=maximum+.03*total+.1*node.path.size();
                if(previous.size()>=8) {
                    auto worst=max_element(previous.begin(),previous.end(),[](const SeenRecord& first,const SeenRecord& second){return first.score<second.score;});
                    if(worst->score<score)continue;
                    previous.erase(worst);
                }
                previous.push_back({node.leftReady,node.rightReady,int(node.path.size()),score});layerCounts[hash]++;
            } else if(!seen.insert(hash).second)continue;
            next.push_back(move(node));if(int(next.size())>=width)break;
        }
        beam=move(next);if(beam.empty()) {cerr<<"empty beam\n";break;}
        if(beam[0].path.size()>instance.capCount*2)break;
        if(step%5==0) {
            int residual=0,combinedDepth=0;
            for(int vertex=0;vertex<size;vertex++) {residual+=weight(beam[0].state.rows[vertex]^(Word(1)<<vertex));combinedDepth=max(combinedDepth,int(beam[0].leftReady[vertex]+beam[0].rightReady[vertex]));}
            cerr<<"step "<<step+1<<" count "<<beam[0].path.size()<<" depth "<<combinedDepth<<" h "<<beam[0].value<<" residual "<<residual<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
        }
    }
}
