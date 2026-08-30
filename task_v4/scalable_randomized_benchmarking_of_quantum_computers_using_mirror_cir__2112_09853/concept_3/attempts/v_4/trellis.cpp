#define NO_ROBUST_MAIN
#include "robust.cpp"
#include <unordered_map>
struct CXTransition {vector<pair<int,int>> pairs;vector<int> outside;};
vector<Bits> states;
unordered_map<Bits,int> stateindex;
vector<pair<int,int>> localmoves[20][2];
CXTransition cxmoves[20][20];
vector<int> finalstates;
int statebound;
void enumeratestates(int begin,int remaining,Bits packed) {
  if(remaining==0){stateindex[packed]=states.size();states.push_back(packed);return;}
  for(int qubit=begin;qubit<=nq-remaining;qubit++)for(int axis=1;axis<=3;axis++)enumeratestates(qubit+1,remaining-1,packed|(axis&1?1ULL<<qubit:0)|(axis&2?1ULL<<(nq+qubit):0));
}
void prepare(int bound) {
  statebound=bound;for(int count=1;count<=bound;count++){enumeratestates(0,count,0);if(count==2)for(int index=0;index<(int)states.size();index++)finalstates.push_back(index);}
  for(int qubit=0;qubit<nq;qubit++)for(int kind=0;kind<2;kind++)for(int index=0;index<(int)states.size();index++) {
    Bits packed=states[index],changed=packed;
    if(kind==0) {Bits difference=((packed>>qubit)^(packed>>(nq+qubit)))&1;changed^=(difference<<qubit)|(difference<<(nq+qubit));}
    else changed^=((packed>>qubit)&1)<<(nq+qubit);
    int other=stateindex.at(changed);if(other>index)localmoves[qubit][kind].push_back({index,other});
  }
  for(auto edge:edges)for(int direction=0;direction<2;direction++) {
    int control=direction?edge.second:edge.first,target=direction?edge.first:edge.second;auto &moves=cxmoves[control][target];
    for(int index=0;index<(int)states.size();index++) {
      Bits packed=states[index],changed=packed^(((packed>>control)&1)<<target)^(((packed>>(nq+target))&1)<<(nq+control));
      auto found=stateindex.find(changed);
      if(found==stateindex.end())moves.outside.push_back(index);else if(found->second>index)moves.pairs.push_back({index,found->second});
    }
  }
  cerr<<"trellis states="<<states.size()<<" outputs="<<finalstates.size()<<endl;
}
double pathscore(const Circuit &circuit) {
  vector<uint8_t> costs(states.size(),4);fill(costs.begin(),costs.begin()+finalstates.size(),0);
  for(int round=0;round<rounds;round++) {
    auto &layer=circuit.layers[round];
    if(round)for(int qubit=0;qubit<nq;qubit++)for(char gate:words[layer.local[qubit]])if(gate!='I') {
      for(auto [first,second]:localmoves[qubit][gate=='H'?0:1])swap(costs[first],costs[second]);
    }
    for(auto [control,target]:layer.cx) {
      auto &moves=cxmoves[control][target];
      for(auto [first,second]:moves.pairs) {int firstcost=costs[first],secondcost=costs[second];costs[first]=min(secondcost,firstcost+1);costs[second]=min(firstcost,secondcost+1);}
      for(int index:moves.outside)costs[index]=min(4,int(costs[index])+1);
    }
  }
  double score=0;double penalty[5]={64,16,4,1,0};
  for(int index:finalstates)score+=penalty[costs[index]];
  return score;
}
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  prepare(argc>6?atoi(argv[6]):2);
  double bestenergy=evaluate(best).energy+2*pathscore(best),energy=bestenergy;auto start=chrono::steady_clock::now();long iterations=0;double elapsed=0;
  cerr<<"initial E="<<bestenergy<<" path="<<pathscore(best)<<endl;
  while(elapsed<seconds) {
    Circuit candidate=current;mutate(candidate);double tested=evaluate(candidate).energy+2*pathscore(candidate);
    double temperature=4*pow(0.03,(iterations%50000)/50000.0);
    if(tested<=energy || uniform01()<exp((energy-tested)/temperature)) {current=move(candidate);energy=tested;}
    if(tested<bestenergy){best=current;bestenergy=tested;save(best,prefix);}
    iterations++;
    if(iterations%10000==0 || bestenergy<1e-9) {elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();cerr<<iterations<<" t="<<elapsed<<" E="<<bestenergy<<" path="<<pathscore(best);printmetrics(evaluate(best));cerr<<endl;}
    if(iterations%50000==0){current=best;energy=bestenergy;}
    if(bestenergy<1e-9)break;
  }
  auto faults=sweep(best);cerr<<"FINAL faults="<<faults.violations<<" min="<<faults.minimum<<endl;save(best,prefix);return 0;
}
