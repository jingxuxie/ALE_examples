#define main old_ideal_main
#include "optimize.cpp"
#undef main
bool perfect(Bits available,vector<pair<int,int>> &selected,bool bridge) {
  if(!available)return true;
  int chosen=-1;vector<int> choices;
  for(int qubit=0;qubit<nq;qubit++)if(available&(1ULL<<qubit)) {
    vector<int> neighbors;for(auto edge:edges)if(bridge || edge!=pair<int,int>{4,13}){if(edge.first==qubit && (available&(1ULL<<edge.second)))neighbors.push_back(edge.second);if(edge.second==qubit && (available&(1ULL<<edge.first)))neighbors.push_back(edge.first);}
    if(chosen<0 || neighbors.size()<choices.size()){chosen=qubit;choices=neighbors;}
  }
  shuffle(choices.begin(),choices.end(),rng);
  for(int neighbor:choices) {selected.push_back({chosen,neighbor});if(perfect(available^(1ULL<<chosen)^(1ULL<<neighbor),selected,bridge))return true;selected.pop_back();}
  return false;
}
Circuit balanced() {
  while(true) {
    Circuit circuit;circuit.layers.resize(rounds);vector<int> corners={0,2,6,8};shuffle(corners.begin(),corners.end(),rng);int internal=0;int usage[20][20]={};
    for(int round=0;round<rounds;round++) {
      auto &layer=circuit.layers[round];for(int qubit=0;qubit<nq;qubit++)layer.local[qubit]=randint(6);Bits available=(1ULL<<nq)-1;
      if(nq==18) {
        if(round==2 || round==4 || round==7 || round==9){layer.cx.push_back({4,13});available^=(1ULL<<4)|(1ULL<<13);}
        else {available^=(1ULL<<corners[internal%4])|(1ULL<<(9+corners[(internal+1+internal/4)%4]));internal++;}
      }
      auto forced=layer.cx;double bestcost=1e100;
      for(int trial=0;trial<128;trial++) {
        auto proposal=forced;if(!perfect(available,proposal,nq!=18))return randomcircuit();double cost=0;
        for(auto [control,target]:proposal)cost+=usage[min(control,target)][max(control,target)]+uniform01()*0.3;
        if(cost<bestcost){bestcost=cost;layer.cx=proposal;}
      }
      for(auto [control,target]:layer.cx)usage[min(control,target)][max(control,target)]++;
      for(auto &gate:layer.cx)if(randint(2))swap(gate.first,gate.second);
    }
    int degrees[20]={};for(auto &layer:circuit.layers)for(auto [control,target]:layer.cx){degrees[control]++;degrees[target]++;}
    for(int attempt=0;attempt<10000 && countcx(circuit)>budget;attempt++) {
      auto &layer=circuit.layers[randint(rounds)];if(layer.cx.empty())continue;int index=randint(layer.cx.size());auto [control,target]=layer.cx[index];
      if(nq==18 && min(control,target)==4 && max(control,target)==13)continue;
      int minimum=nq==20?8:9;if(degrees[control]<=minimum || degrees[target]<=minimum)continue;
      layer.cx.erase(layer.cx.begin()+index);degrees[control]--;degrees[target]--;
    }
    if(countcx(circuit)==budget)return circuit;
  }
}
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=balanced(),current=best;
  double bestenergy=evaluate(best).energy,energy=bestenergy;auto start=chrono::steady_clock::now();long iterations=0;double elapsed=0;
  save(best,prefix);cerr<<"initial E="<<bestenergy<<endl;
  while(elapsed<seconds) {
    Circuit candidate=current;mutate(candidate);bool changed=false;
    for(int round=0;round<rounds;round++) {auto old=current.layers[round].cx,now=candidate.layers[round].cx;for(auto &gate:old)if(gate.first>gate.second)swap(gate.first,gate.second);for(auto &gate:now)if(gate.first>gate.second)swap(gate.first,gate.second);sort(old.begin(),old.end());sort(now.begin(),now.end());if(old!=now)changed=true;}
    if(changed)continue;double tested=evaluate(candidate).energy,temperature=5*pow(0.02,(iterations%100000)/100000.0);
    if(tested<=energy || uniform01()<exp((energy-tested)/temperature)){current=move(candidate);energy=tested;}
    if(tested<bestenergy){best=current;bestenergy=tested;save(best,prefix);}
    iterations++;
    if(iterations%10000==0 || bestenergy<1e-9){elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();cerr<<iterations<<" t="<<elapsed<<" E="<<bestenergy<<endl;}
    if(iterations%100000==0){current=best;energy=bestenergy;}
    if(bestenergy<1e-9)break;
  }
  save(best,prefix);printmetrics(evaluate(best));cerr<<endl;return 0;
}
