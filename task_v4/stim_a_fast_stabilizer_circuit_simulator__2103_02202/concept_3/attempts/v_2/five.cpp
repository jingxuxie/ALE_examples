#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

using Key=unsigned __int128;
using Small=std::array<int,10>;
struct Hash {size_t operator()(Key key)const{return uint64_t(key)^uint64_t(key>>64)*0x9e3779b97f4a7c15ULL;}};
struct Operation {char gate;int first,second,axis1,axis2;};
struct State {Key key;int parent,depth;Operation move;std::array<int,5>locals;};
struct Library {std::vector<State>states;std::unordered_map<Key,int,Hash>lookup;std::vector<std::pair<int,int>>edges;};
std::array<Library,4>libraries;
const std::array<std::string,6>words{"","H","S","HS","SH","HSH"};
Small unpack(Key key){Small columns{};for(int index=0;index<10;index++){columns[index]=key&1023;key>>=10;}return columns;}
Key pack(const Small&columns){Key key=0;for(int index=0;index<10;index++)key|=Key(columns[index])<<(10*index);return key;}
State transition(Key key,const Operation&move) {
    auto columns=unpack(key);int change=0;
    if(move.axis1&2)change^=columns[2*move.first];if(move.axis1&1)change^=columns[2*move.first+1];
    if(move.axis2&2)change^=columns[2*move.second];if(move.axis2&1)change^=columns[2*move.second+1];
    if(move.axis1&1)columns[2*move.first]^=change;if(move.axis1&2)columns[2*move.first+1]^=change;
    if(move.axis2&1)columns[2*move.second]^=change;if(move.axis2&2)columns[2*move.second+1]^=change;
    std::array<int,5>locals{};
    for(int qubit=0;qubit<5;qubit++) {
        int first=columns[2*qubit],second=columns[2*qubit+1];std::array<int,3>values{first,second,first^second};std::sort(values.begin(),values.end());
        for(int index=0;index<6;index++) {
            int trialfirst=first,trialsecond=second;
            for(char gate:words[index]){if(gate=='H')std::swap(trialfirst,trialsecond);else trialsecond^=trialfirst;}
            if(trialfirst==values[0]&&trialsecond==values[1]){locals[qubit]=index;break;}
        }
        columns[2*qubit]=values[0];columns[2*qubit+1]=values[1];
    }
    return {pack(columns),-1,0,move,locals};
}
void initialize(int topology) {
    auto&library=libraries[topology];if(!library.states.empty())return;
    if(topology==0)library.edges={{0,1},{1,2},{2,3},{3,4}};
    if(topology==1)library.edges={{0,1},{0,2},{0,3},{0,4}};
    if(topology==2)library.edges={{0,1},{1,2},{0,3},{0,4}};
    if(topology==3)library.edges={{0,1},{1,2},{2,3},{3,0},{0,4}};
    Small identity{};for(int qubit=0;qubit<5;qubit++){identity[2*qubit]=1<<qubit;identity[2*qubit+1]=1<<(qubit+5);}
    auto key=pack(identity);library.states.push_back({key,-1,0,{},{}});library.lookup[key]=0;
    for(int index=0;index<int(library.states.size());index++) {
        auto current=library.states[index];if(current.depth==3)continue;
        for(auto[first,second]:library.edges)for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++) {
            auto next=transition(current.key,{'R',first,second,axis1,axis2});if(library.lookup.count(next.key))continue;
            next.parent=index;next.depth=current.depth+1;library.lookup[next.key]=int(library.states.size());library.states.push_back(next);
        }
    }
}
std::vector<Operation> path(const std::vector<State>&states,int index) {
    std::vector<int>chain;while(states[index].parent!=-1){chain.push_back(index);index=states[index].parent;}
    std::reverse(chain.begin(),chain.end());std::vector<Operation>result;
    for(auto position:chain) {
        auto state=states[position];result.push_back(state.move);
        for(int qubit=0;qubit<5;qubit++)for(char gate:words[state.locals[qubit]])result.push_back({gate,qubit,0,0,0});
    }
    return result;
}
extern "C" const char* solve_five(uint64_t low,uint64_t high,int topology,int bound) {
    Key target=Key(low)|(Key(high)<<64);static std::string output;output.clear();initialize(topology);auto&library=libraries[topology];
    int foundforward=-1,foundbackward=0;auto existing=library.lookup.find(target);
    std::vector<State>backward{{target,-1,0,{},{}}};std::unordered_map<Key,int,Hash>seen{{target,0}};
    if(existing!=library.lookup.end()&&library.states[existing->second].depth<=bound)foundforward=existing->second;
    if(foundforward<0&&bound>3) {
        for(int index=0;index<int(backward.size())&&foundforward<0;index++) {
            auto current=backward[index];if(current.depth>=bound-3)continue;
            for(auto[first,second]:library.edges) {
                for(int axis1=1;axis1<=3&&foundforward<0;axis1++)for(int axis2=1;axis2<=3&&foundforward<0;axis2++) {
                    auto next=transition(current.key,{'R',first,second,axis1,axis2});if(seen.count(next.key))continue;
                    next.parent=index;next.depth=current.depth+1;int position=int(backward.size());seen[next.key]=position;backward.push_back(next);
                    auto match=library.lookup.find(next.key);
                    if(match!=library.lookup.end()&&next.depth+library.states[match->second].depth<=bound){foundforward=match->second;foundbackward=position;}
                }
                if(foundforward>=0)break;
            }
        }
    }
    if(foundforward<0)return nullptr;
    auto operations=path(library.states,foundforward);auto tail=path(backward,foundbackward);std::reverse(tail.begin(),tail.end());operations.insert(operations.end(),tail.begin(),tail.end());
    for(auto operation:operations) {
        output+=operation.gate;output+=',';output+=std::to_string(operation.first);
        if(operation.gate=='R')output+=','+std::to_string(operation.second)+','+std::to_string(operation.axis1)+','+std::to_string(operation.axis2);
        output+=';';
    }
    return output.c_str();
}
