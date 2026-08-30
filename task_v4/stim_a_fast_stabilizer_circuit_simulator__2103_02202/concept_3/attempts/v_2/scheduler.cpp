#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

using Orders=std::array<std::vector<int>,36>;
struct Gate {uint64_t xmask,zmask;std::array<int,2>qubits;};
struct Graph {
    std::vector<std::array<int,2>>previous,next;
    std::vector<int>indegree,levels,tails,topological;
    int depth=0;long sum=0;bool valid=false;
    std::vector<std::pair<int,int>>critical;
};
bool commute(const Gate&first,const Gate&second){return ((__builtin_popcountll(first.xmask&second.zmask)+__builtin_popcountll(first.zmask&second.xmask))&1)==0;}
Graph evaluate(const Orders&orders,const std::vector<Gate>&gates) {
    int count=int(gates.size());Graph graph;
    graph.previous.assign(count,{-1,-1});graph.next.assign(count,{-1,-1});graph.indegree.assign(count,0);graph.levels.assign(count,1);graph.tails.assign(count,1);
    for(auto&wire:orders)for(int position=1;position<int(wire.size());position++) {
        int first=wire[position-1],second=wire[position];
        graph.previous[second][graph.previous[second][0]>=0]=first;
        graph.next[first][graph.next[first][0]>=0]=second;graph.indegree[second]++;
    }
    for(int index=0;index<count;index++)if(!graph.indegree[index])graph.topological.push_back(index);
    for(int position=0;position<int(graph.topological.size());position++) {
        int first=graph.topological[position];graph.depth=std::max(graph.depth,graph.levels[first]);graph.sum+=graph.levels[first];
        for(int second:graph.next[first])if(second>=0) {
            graph.levels[second]=std::max(graph.levels[second],graph.levels[first]+1);
            if(--graph.indegree[second]==0)graph.topological.push_back(second);
        }
    }
    if(int(graph.topological.size())!=count)return graph;
    graph.valid=true;
    for(int position=count-1;position>=0;position--) {
        int first=graph.topological[position];for(int second:graph.next[first])if(second>=0)graph.tails[first]=std::max(graph.tails[first],graph.tails[second]+1);
    }
    for(int qubit=0;qubit<36;qubit++)for(int position=1;position<int(orders[qubit].size());position++) {
        int first=orders[qubit][position-1],second=orders[qubit][position];
        if(graph.levels[first]+graph.tails[second]==graph.depth&&commute(gates[first],gates[second]))graph.critical.emplace_back(qubit,position-1);
    }
    return graph;
}
extern "C" int schedule_rotations(const uint64_t*xvalues,const uint64_t*zvalues,int count,int steps,int seed,int*output) {
    std::vector<Gate>gates;Orders orders;
    for(int index=0;index<count;index++) {
        uint64_t support=xvalues[index]|zvalues[index];int first=__builtin_ctzll(support);support&=support-1;int second=__builtin_ctzll(support);
        gates.push_back({xvalues[index],zvalues[index],{first,second}});orders[first].push_back(index);orders[second].push_back(index);
    }
    std::mt19937_64 random(seed);auto current=evaluate(orders,gates);auto best=current;auto bestorders=orders;
    for(int iteration=0;iteration<steps;iteration++) {
        if(iteration%5000==0){orders=bestorders;current=evaluate(orders,gates);}
        int qubit,position;
        if(!current.critical.empty()&&random()%5) {auto choice=current.critical[random()%current.critical.size()];qubit=choice.first;position=choice.second;}
        else {qubit=random()%36;if(orders[qubit].size()<2)continue;position=random()%(orders[qubit].size()-1);}
        int first=orders[qubit][position],second=orders[qubit][position+1];if(!commute(gates[first],gates[second]))continue;
        std::vector<std::pair<int,int>>swaps{{qubit,position}};
        int otherfirst=gates[first].qubits[0]^gates[first].qubits[1]^qubit;
        int othersecond=gates[second].qubits[0]^gates[second].qubits[1]^qubit;
        if(otherfirst==othersecond) {
            auto&wire=orders[otherfirst];int otherposition=int(std::find(wire.begin(),wire.end(),first)-wire.begin());
            if(otherposition+1>=int(wire.size())||wire[otherposition+1]!=second)continue;
            swaps.emplace_back(otherfirst,otherposition);
        }
        for(auto[wire,index]:swaps)std::swap(orders[wire][index],orders[wire][index+1]);
        auto next=evaluate(orders,gates);
        double temperature=0.05+0.7*(1.0-double(iteration%5000)/5000);
        double change=next.depth-current.depth+0.00001*(next.sum-current.sum);
        bool accept=next.valid&&(change<=0||double(random()%1000000)/1000000<std::exp(-change/temperature));
        if(accept) {
            current=std::move(next);
            if(current.depth<best.depth||(current.depth==best.depth&&current.sum<best.sum)){best=current;bestorders=orders;}
        }else for(auto[wire,index]:swaps)std::swap(orders[wire][index],orders[wire][index+1]);
    }
    auto order=best.topological;
    std::stable_sort(order.begin(),order.end(),[&](int first,int second){return best.levels[first]<best.levels[second];});
    for(int index=0;index<count;index++)output[index]=order[index];
    return best.depth;
}
