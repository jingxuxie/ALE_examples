#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace std;
using Bits = uint64_t;
struct Layer { array<int,20> local{}; vector<pair<int,int>> cx; };
struct Circuit { vector<Layer> layers; };
struct Metrics { int minimum[4]; double mean[4]; double energy=0, ratio=1; };
int nq, rounds, budget, targetmin[2];
double targetmean[2];
string family;
vector<pair<int,int>> edges;
mt19937_64 rng;
int randint(int bound) { return rng()%bound; }
double uniform01() { return (rng()>>11)*0x1.0p-53; }
const string words[6]={"I","H","S","HS","SH","HSH"};
int localcompose(int after,int before) {
  auto transform=[](int word,int axis) {for(char gate:words[word]){if(gate=='H')axis=((axis&1)<<1)|((axis>>1)&1);else if(gate=='S')axis^=(axis&1)<<1;}return axis;};
  int first=transform(after,transform(before,1)),second=transform(after,transform(before,2));
  for(int word=0;word<6;word++)if(transform(word,1)==first && transform(word,2)==second)return word;return 0;
}
void setup(int index) {
  family=vector<string>{"ladder16","grid20","bridge18"}[index];
  nq=vector<int>{16,20,18}[index]; rounds=index==1?10:12; budget=vector<int>{80,84,90}[index];
  targetmin[0]=index==1?9:8; targetmin[1]=vector<int>{6,7,5}[index];
  targetmean[0]=vector<double>{11.5,14,12.25}[index]; targetmean[1]=vector<double>{11.75,14.75,13}[index];
  int height=index==0?2:index==1?4:3, width=index==0?8:index==1?5:3;
  for(int block=0;block<(index==2?2:1);block++) for(int row=0;row<height;row++) for(int col=0;col<width;col++) {
    int site=block*9+row*width+col;
    if(row+1<height) edges.push_back({site,site+width});
    if(col+1<width) edges.push_back({site,site+1});
  }
  if(index==2) edges.push_back({4,13});
}
int countcx(const Circuit &circuit) { int count=0; for(auto &layer:circuit.layers) count+=layer.cx.size(); return count; }
vector<pair<int,int>> matching() {
  auto shuffled=edges; shuffle(shuffled.begin(),shuffled.end(),rng); Bits occupied=0; vector<pair<int,int>> result;
  for(auto [control,target]:shuffled) if(!(occupied&((1ULL<<control)|(1ULL<<target)))) {
    occupied|=(1ULL<<control)|(1ULL<<target); if(randint(2)) swap(control,target); result.push_back({control,target});
  }
  return result;
}
Circuit randomcircuit() {
  Circuit circuit; circuit.layers.resize(rounds);
  for(auto &layer:circuit.layers) {
    for(int qubit=0;qubit<nq;qubit++) layer.local[qubit]=randint(6);
    for(int attempt=0;attempt<5;attempt++) { auto candidate=matching(); if(candidate.size()>layer.cx.size()) layer.cx=candidate; }
  }
  while(countcx(circuit)>budget) { auto &layer=circuit.layers[randint(rounds)]; if(layer.cx.size()) layer.cx.erase(layer.cx.begin()+randint(layer.cx.size())); }
  return circuit;
}
void maprows(const Circuit &circuit, Bits *rows, array<int,3> omitted={-1,-1,-1}) {
  for(int index=0;index<2*nq;index++) rows[index]=1ULL<<index;
  int instance=0;
  for(auto &layer:circuit.layers) {
    for(int qubit=0;qubit<nq;qubit++) {
      Bits xbits=rows[qubit],zbits=rows[nq+qubit];
      switch(layer.local[qubit]) {
        case 0: break;
        case 1: rows[qubit]=zbits; rows[nq+qubit]=xbits; break;
        case 2: rows[nq+qubit]=zbits^xbits; break;
        case 3: rows[qubit]=zbits; rows[nq+qubit]=xbits^zbits; break;
        case 4: rows[qubit]=xbits^zbits; rows[nq+qubit]=xbits; break;
        case 5: rows[qubit]=xbits^zbits; break;
      }
    }
    for(auto [control,target]:layer.cx) {
      if(instance!=omitted[0] && instance!=omitted[1] && instance!=omitted[2]) { rows[target]^=rows[control]; rows[nq+control]^=rows[nq+target]; }
      instance++;
    }
  }
}
void imagesfromrows(const Bits *rows, Bits *forward, Bits *inverse) {
  Bits mask=(1ULL<<nq)-1;
  for(int index=0;index<2*nq;index++) {
    forward[index]=0;
    Bits packed=rows[(index+nq)%(2*nq)]; inverse[index]=((packed&mask)<<nq)|(packed>>nq);
  }
  for(int index=0;index<2*nq;index++) {
    Bits packed=rows[index];
    while(packed) { int column=__builtin_ctzll(packed); forward[column]|=1ULL<<index; packed&=packed-1; }
  }
}
inline int weight(Bits packed) { return __builtin_popcountll((packed|(packed>>nq))&((1ULL<<nq)-1)); }
Metrics evaluate(const Circuit &circuit) {
  Bits rows[40],forward[40],inverse[40]; maprows(circuit,rows); imagesfromrows(rows,forward,inverse);
  Metrics result;
  for(int direction=0;direction<2;direction++) {
    Bits *images=direction?inverse:forward, singles[60];
    int total[2]={0,0}, minimum[2]={nq,nq}, counts[2]={3*nq,9*nq*(nq-1)/2};
    for(int qubit=0;qubit<nq;qubit++) {
      singles[3*qubit]=images[qubit]; singles[3*qubit+1]=images[qubit]^images[nq+qubit]; singles[3*qubit+2]=images[nq+qubit];
    }
    for(int first=0;first<3*nq;first++) {
      int observed=weight(singles[first]); total[0]+=observed; minimum[0]=min(minimum[0],observed);
      int deficit=max(0,targetmin[0]-observed); result.energy+=2*deficit*deficit;
      for(int second=(first/3+1)*3;second<3*nq;second++) {
        observed=weight(singles[first]^singles[second]); total[1]+=observed; minimum[1]=min(minimum[1],observed);
        deficit=max(0,targetmin[1]-observed); result.energy+=deficit*deficit;
      }
    }
    for(int stratum=0;stratum<2;stratum++) {
      double mean=double(total[stratum])/counts[stratum], deficit=max(0.0,targetmean[stratum]-mean);
      result.energy+=100*deficit*deficit;
      result.minimum[2*direction+stratum]=minimum[stratum]; result.mean[2*direction+stratum]=mean;
      result.ratio=min(result.ratio,min(double(minimum[stratum])/targetmin[stratum],mean/targetmean[stratum]));
    }
  }
  return result;
}
void save(const Circuit &circuit,string prefix) {
  ofstream text(prefix+".txt"); text<<nq<<' '<<rounds<<'\n';
  ofstream json(prefix+".json"); json<<"{\"family\":\""<<family<<"\",\"layers\":[";
  for(int round=0;round<rounds;round++) {
    auto &layer=circuit.layers[round]; if(round) json<<','; json<<"{\"local\":[";
    for(int qubit=0;qubit<nq;qubit++) { text<<layer.local[qubit]<<' '; if(qubit)json<<',';json<<'"'<<words[layer.local[qubit]]<<'"'; }
    text<<layer.cx.size(); json<<"],\"cx\":[";
    for(int gate=0;gate<(int)layer.cx.size();gate++) {auto [control,target]=layer.cx[gate]; text<<' '<<control<<' '<<target;if(gate)json<<',';json<<'['<<control<<','<<target<<']';}
    text<<'\n';json<<"]}";
  }
  json<<"]}\n";
}
Circuit load(string filename) {
  ifstream text(filename); int count,depth; text>>count>>depth; Circuit circuit; circuit.layers.resize(depth);
  for(auto &layer:circuit.layers) { for(int qubit=0;qubit<count;qubit++)text>>layer.local[qubit];int gates;text>>gates;for(int gate=0;gate<gates;gate++){int control,target;text>>control>>target;layer.cx.push_back({control,target});} }
  return circuit;
}
void mutate(Circuit &circuit) {
  if(randint(100)<45) {
    int round=randint(rounds);auto &layer=circuit.layers[round];if(layer.cx.empty())return;
    auto gate=layer.cx[randint(layer.cx.size())];int sites[2]={gate.first,gate.second};if(randint(2))swap(sites[0],sites[1]);int count=randint(4)==0?2:1;
    for(int index=0;index<count;index++) {
      int qubit=sites[index],rotation;do{rotation=1+randint(5);}while(rotation==(qubit==gate.first?2:5));int inverse=rotation==3?4:rotation==4?3:rotation;
      layer.local[qubit]=localcompose(rotation,layer.local[qubit]);
      if(round+1<rounds)circuit.layers[round+1].local[qubit]=localcompose(circuit.layers[round+1].local[qubit],inverse);
    }
    return;
  }
  int choice=randint(100), round=randint(rounds); auto &layer=circuit.layers[round];
  if(choice<70) { layer.local[randint(nq)]=randint(6); }
  else if(choice<78) { if(layer.cx.size()) {auto &gate=layer.cx[randint(layer.cx.size())];swap(gate.first,gate.second);} }
  else if(choice<92 && layer.cx.size()>=2) {
    int first=randint(layer.cx.size()),second=randint(layer.cx.size());if(first==second)return;
    Bits occupied=0;for(int index=0;index<(int)layer.cx.size();index++)if(index!=first && index!=second)occupied|=(1ULL<<layer.cx[index].first)|(1ULL<<layer.cx[index].second);
    vector<pair<int,int>> allowed;for(auto edge:edges)if(!(occupied&((1ULL<<edge.first)|(1ULL<<edge.second))))allowed.push_back(edge);
    shuffle(allowed.begin(),allowed.end(),rng);vector<pair<int,int>> selected;
    for(auto edge:allowed)if(!(occupied&((1ULL<<edge.first)|(1ULL<<edge.second)))){occupied|=(1ULL<<edge.first)|(1ULL<<edge.second);if(randint(2))swap(edge.first,edge.second);selected.push_back(edge);if(selected.size()==2)break;}
    if(selected.size()==2){layer.cx[first]=selected[0];layer.cx[second]=selected[1];}
  }
  else if(choice<98) {
    auto edge=edges[randint(edges.size())]; if(randint(2))swap(edge.first,edge.second);
    int conflict=-1,conflicts=0;
    for(int index=0;index<(int)layer.cx.size();index++){auto gate=layer.cx[index];if(gate.first==edge.first||gate.second==edge.first||gate.first==edge.second||gate.second==edge.second){conflict=index;conflicts++;}}
    if(conflicts==1){layer.cx[conflict]=edge;return;}
    layer.cx.erase(remove_if(layer.cx.begin(),layer.cx.end(),[&](auto gate){return gate.first==edge.first||gate.second==edge.first||gate.first==edge.second||gate.second==edge.second;}),layer.cx.end());
    if(countcx(circuit)<budget)layer.cx.push_back(edge);
  } else { layer.cx=matching(); while(countcx(circuit)>budget && layer.cx.size())layer.cx.erase(layer.cx.begin()+randint(layer.cx.size())); }
}
void printmetrics(const Metrics &metrics) {
  cerr<<" E="<<metrics.energy<<" ratio="<<metrics.ratio<<" min=";
  for(int index=0;index<4;index++)cerr<<metrics.minimum[index]<<',';cerr<<" mean=";for(int index=0;index<4;index++)cerr<<metrics.mean[index]<<',';
}
int main(int argc,char **argv) {
  int index=atoi(argv[1]), seed=atoi(argv[2]), seconds=atoi(argv[3]); setup(index);rng.seed(seed);string prefix=argc>4?argv[4]:family;
  Circuit best=argc>5?load(argv[5]):randomcircuit(), current=best; Metrics bestmetrics=evaluate(best), metrics=bestmetrics;
  auto start=chrono::steady_clock::now(); long iterations=0,lastbest=0;double elapsed=0;
  save(best,prefix);cerr<<family<<" start";printmetrics(bestmetrics);cerr<<endl;
  while(elapsed<seconds) {
    Circuit candidate=current;mutate(candidate); Metrics tested=evaluate(candidate);
    double phase=(iterations%100000)/100000.0, temperature=8*pow(0.03,phase);
    if(tested.energy<=metrics.energy || uniform01()<exp((metrics.energy-tested.energy)/temperature)) {current=move(candidate);metrics=tested;}
    if(tested.energy<bestmetrics.energy) {
      best=current;bestmetrics=tested;lastbest=iterations;save(best,prefix);
      if(bestmetrics.energy<20 || iterations%1000<10) {cerr<<iterations;printmetrics(bestmetrics);cerr<<endl;}
      if(bestmetrics.energy<1e-9)break;
    }
    iterations++;
    if(iterations%100000==0) {
      if(iterations-lastbest>500000) {current=randomcircuit();metrics=evaluate(current);} else {current=best;metrics=bestmetrics;}
      elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();
      cerr<<iterations<<" time="<<elapsed;printmetrics(bestmetrics);cerr<<endl;
    }
  }
  save(best,prefix);cerr<<"FINAL "<<iterations;printmetrics(bestmetrics);cerr<<endl;
  return 0;
}
