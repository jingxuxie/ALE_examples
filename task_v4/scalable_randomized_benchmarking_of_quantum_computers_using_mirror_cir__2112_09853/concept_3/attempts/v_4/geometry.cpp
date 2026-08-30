#define NO_CRITICAL_MAIN
#include "critical.cpp"
void rotate_at(Circuit &circuit,int round,int qubit,int rotation) {
  int inverse=rotation==3?4:rotation==4?3:rotation;circuit.layers[round].local[qubit]=localcompose(rotation,circuit.layers[round].local[qubit]);
  if(round+1<rounds)circuit.layers[round+1].local[qubit]=localcompose(circuit.layers[round+1].local[qubit],inverse);
}
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit current=load(argv[5]);
  double idealweight=0.1;long critical=criticalscore(current);double energy=critical+idealweight*evaluate(current).energy;long testedcount=0;auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};
  cerr<<"initial critical="<<critical<<" E="<<energy<<endl;save(current,prefix);
  for(int pass=0;pass<20 && elapsed()<seconds;pass++) {
    bool improved=false;vector<int> roundorder(rounds);iota(roundorder.begin(),roundorder.end(),0);shuffle(roundorder.begin(),roundorder.end(),rng);auto edgeorder=edges;shuffle(edgeorder.begin(),edgeorder.end(),rng);
    for(int round:roundorder)for(auto edge:edgeorder)for(int controlrotation:{0,1,4})for(int targetrotation:{0,1,3}) {
      if(elapsed()>seconds)break;Circuit candidate=current;auto &layer=candidate.layers[round];int first=-1;vector<int> conflicts;
      for(int index=0;index<(int)layer.cx.size();index++){auto gate=layer.cx[index];if(gate.first==edge.first||gate.second==edge.first||gate.first==edge.second||gate.second==edge.second)conflicts.push_back(index);}
      if(conflicts.size()==1)layer.cx[conflicts[0]]=edge;
      else {layer.cx.erase(remove_if(layer.cx.begin(),layer.cx.end(),[&](auto gate){return gate.first==edge.first||gate.second==edge.first||gate.first==edge.second||gate.second==edge.second;}),layer.cx.end());layer.cx.push_back(edge);}
      if(countcx(candidate)>budget)continue;rotate_at(candidate,round,edge.first,controlrotation);rotate_at(candidate,round,edge.second,targetrotation);
      auto metrics=evaluate(candidate);if(idealweight*metrics.energy>energy)continue;long candidatecritical=criticalscore(candidate,energy-idealweight*metrics.energy);double tested=candidatecritical+idealweight*metrics.energy;testedcount++;
      if(tested+1e-9<energy){current=move(candidate);energy=tested;critical=candidatecritical;improved=true;save(current,prefix);cerr<<"BEST "<<testedcount<<" t="<<elapsed()<<" critical="<<critical<<" E="<<energy;printmetrics(metrics);cerr<<endl;}
    }
    cerr<<"PASS "<<pass<<" t="<<elapsed()<<" E="<<energy<<" improved="<<improved<<endl;if(!improved || critical==0)break;
  }
  save(current,prefix);return 0;
}
