#define NO_TRAIN_MAIN
#include "train.cpp"
int faultscore(const Circuit &circuit,array<int,3> omitted) {
  Bits rows[40],images[60],mask=(1ULL<<nq)-1;maprows(circuit,rows,omitted);
  for(int qubit=0;qubit<nq;qubit++) {
    Bits ximage=((rows[nq+qubit]&mask)<<nq)|(rows[nq+qubit]>>nq),zimage=((rows[qubit]&mask)<<nq)|(rows[qubit]>>nq);
    images[3*qubit]=ximage;images[3*qubit+1]=ximage^zimage;images[3*qubit+2]=zimage;
  }
  int result=0;
  for(int first=0;first<3*nq;first++) {
    int deficit=max(0,3-weight(images[first]));result+=deficit*deficit;
    for(int second=(first/3+1)*3;second<3*nq;second++) {deficit=max(0,3-weight(images[first]^images[second]));result+=deficit*deficit;}
  }
  return result;
}
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  auto initial=sweep(best);long bestfaults=initial.violations;vector<array<int,3>> active;addconstraints(initial.constraints,256);
  auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};
  vector<array<int,3>> samples;
  int count=argc>6?atoi(argv[6]):256;
  double energy=0;long iterations=0,accepted=0;
  auto score=[&](const Circuit &circuit) {double result=2*constraintenergy(circuit);for(auto omitted:samples)result+=faultscore(circuit,omitted);return result;};
  auto resample=[&]() {
    samples.clear();int gates=countcx(current);
    for(int index=0;index<count;index++) {array<int,3> omitted;do{omitted={randint(gates),randint(gates),randint(gates)};}while(omitted[0]==omitted[1]||omitted[0]==omitted[2]||omitted[1]==omitted[2]);sort(omitted.begin(),omitted.end());samples.push_back(omitted);}
    energy=score(current);
  };
  resample();save(best,prefix);cerr<<"initial faults="<<bestfaults<<endl;
  while(elapsed()<seconds) {
    if(iterations%100==0)resample();
    Circuit candidate=current;
    int round=1+randint(rounds-1);auto &layer=candidate.layers[round];int choice=randint(100);
    if(choice<85)layer.local[randint(nq)]=randint(6);
    else if(choice<93 && layer.cx.size()) {auto &gate=layer.cx[randint(layer.cx.size())];swap(gate.first,gate.second);}
    else if(layer.cx.size()) {
      int selected=randint(layer.cx.size());Bits occupied=0;
      for(int index=0;index<(int)layer.cx.size();index++)if(index!=selected)occupied|=(1ULL<<layer.cx[index].first)|(1ULL<<layer.cx[index].second);
      auto edge=edges[randint(edges.size())];if(!(occupied&((1ULL<<edge.first)|(1ULL<<edge.second)))){if(randint(2))swap(edge.first,edge.second);layer.cx[selected]=edge;}
    }
    auto metrics=evaluate(candidate);
    if(metrics.energy<1e-9) {
      double tested=score(candidate),temperature=0.5*pow(0.1,(iterations%20000)/20000.0);
      if(tested<=energy || uniform01()<exp((energy-tested)/temperature)) {current=move(candidate);energy=tested;accepted++;}
    }
    iterations++;
    if(iterations%5000==0) {
      auto faults=sweep(current);cerr<<iterations<<" t="<<elapsed()<<" faults="<<faults.violations<<" min="<<faults.minimum<<" best="<<bestfaults<<" accepted="<<accepted<<" active="<<active.size()<<endl;
      save(current,prefix+"_latest");
      if(faults.violations<bestfaults){best=current;bestfaults=faults.violations;save(best,prefix);}
      if(!faults.violations){cerr<<"SUCCESS"<<endl;break;}
      addconstraints(faults.constraints,128);
      if(pool.size()>65536){shuffle(pool.begin(),pool.end(),rng);pool.resize(49152);compilepool();}
      if(iterations%20000==0)current=best;resample();
    }
  }
  save(best,prefix);cerr<<"END best="<<bestfaults<<endl;return 0;
}
