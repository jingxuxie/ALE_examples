#define NO_CRITICAL_MAIN
#include "critical.cpp"
struct Candidate {double energy;Circuit circuit;};
void rotate(Circuit &circuit,int round,int qubit,int rotation){int inverse=rotation==3?4:rotation==4?3:rotation;circuit.layers[round].local[qubit]=localcompose(rotation,circuit.layers[round].local[qubit]);if(round+1<rounds)circuit.layers[round+1].local[qubit]=localcompose(circuit.layers[round+1].local[qubit],inverse);}
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit current=load(argv[5]);double currentenergy=criticalscore(current)+0.1*evaluate(current).energy;auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};save(current,prefix);cerr<<"initial "<<currentenergy<<endl;
  auto score=[&](Circuit &circuit,double limit){double ideal=0.1*evaluate(circuit).energy;if(ideal>limit)return ideal;return criticalscore(circuit,limit-ideal)+ideal;};
  for(int pass=0;pass<50 && elapsed()<seconds;pass++){
    vector<Candidate> localbeam,geometrybeam;Candidate best={currentenergy,current};
    auto retain=[&](Circuit candidate,vector<Candidate> &beam){double limit=beam.size()>=6?beam.back().energy:currentenergy+100;double energy=score(candidate,limit);if(energy>limit)return;beam.push_back({energy,move(candidate)});sort(beam.begin(),beam.end(),[](auto &left,auto &right){return left.energy<right.energy;});if(beam.size()>6)beam.pop_back();if(energy<best.energy)best=beam.front();};
    for(int round=0;round<rounds;round++)for(auto [control,target]:current.layers[round].cx)for(int first:{0,1,4})for(int second:{0,1,3})if(first||second){if(elapsed()>seconds)break;Circuit candidate=current;rotate(candidate,round,control,first);rotate(candidate,round,target,second);retain(move(candidate),localbeam);}
    for(int round=0;round<rounds;round++)for(auto edge:edges)for(int direction=0;direction<2;direction++){
      if(elapsed()>seconds)break;if(direction)swap(edge.first,edge.second);Circuit candidate=current;auto &layer=candidate.layers[round];
      layer.cx.erase(remove_if(layer.cx.begin(),layer.cx.end(),[&](auto gate){return gate.first==edge.first||gate.second==edge.first||gate.first==edge.second||gate.second==edge.second;}),layer.cx.end());layer.cx.push_back(edge);
      auto original=current.layers[round].cx,modified=layer.cx;sort(original.begin(),original.end());sort(modified.begin(),modified.end());if(original==modified)continue;
      if(countcx(candidate)<=budget)retain(move(candidate),geometrybeam);
    }
    localbeam.insert(localbeam.end(),geometrybeam.begin(),geometrybeam.end());
    for(auto &parent:localbeam)for(int round=0;round<rounds;round++)for(auto [control,target]:parent.circuit.layers[round].cx)for(int first:{0,1,4})for(int second:{0,1,3})if(first||second){
      if(elapsed()>seconds)break;Circuit candidate=parent.circuit;rotate(candidate,round,control,first);rotate(candidate,round,target,second);double energy=score(candidate,best.energy);if(energy+1e-9<best.energy){best={energy,move(candidate)};save(best.circuit,prefix);cerr<<"BEST pass="<<pass<<" t="<<elapsed()<<" E="<<energy;printmetrics(evaluate(best.circuit));cerr<<endl;}
    }
    cerr<<"PASS "<<pass<<" t="<<elapsed()<<" old="<<currentenergy<<" new="<<best.energy<<endl;
    if(best.energy+1e-9<currentenergy){current=best.circuit;currentenergy=best.energy;save(current,prefix);}else break;
    if(criticalscore(current)==0 && evaluate(current).ratio>=2.0/3){save(current,prefix+"_safe");cerr<<"SAFE"<<endl;break;}
  }
  save(current,prefix);return 0;}
