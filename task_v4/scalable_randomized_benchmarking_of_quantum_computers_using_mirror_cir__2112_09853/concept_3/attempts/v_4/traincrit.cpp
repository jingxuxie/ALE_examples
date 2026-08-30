#define NO_TRAIN_MAIN
#include "train.cpp"
vector<Constraint> criticalfailures(const Circuit &circuit) {
  auto result=sweep(circuit);vector<Constraint> critical;
  for(auto &entry:result.constraints)if(entry.weight==1 || weight(entry.input)==1)critical.push_back(entry);return critical;
}
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  auto started=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
  auto failures=criticalfailures(best);addconstraints(failures,1000000);double bestenergy=evaluate(best).energy+2*constraintenergy(best,0,true),energy=bestenergy;
  long bestfailures=failures.size(),iterations=0,lastsweep=0;save(best,prefix+"_best");cerr<<"initial critical="<<failures.size()<<" pool="<<pool.size()<<" E="<<bestenergy<<endl;
  while(elapsed()<seconds) {
    Circuit candidate=current;mutate(candidate);bool changed=false;for(int round=0;round<rounds;round++)if(candidate.layers[round].cx.size()!=current.layers[round].cx.size())changed=true;if(changed)continue;
    double tested=evaluate(candidate).energy+2*constraintenergy(candidate,0,true),temperature=3*pow(0.03,(iterations%100000)/100000.0);
    if(tested<=energy || uniform01()<exp((energy-tested)/temperature)){current=move(candidate);energy=tested;}
    if(tested<bestenergy){best=current;bestenergy=tested;}
    iterations++;
    if(bestenergy<1e-9 || iterations-lastsweep>=300000) {
      lastsweep=iterations;failures=criticalfailures(best);auto metrics=evaluate(best);cerr<<"SWEEP "<<iterations<<" t="<<elapsed()<<" pool="<<pool.size()<<" E="<<bestenergy<<" critical="<<failures.size();printmetrics(metrics);cerr<<endl;save(best,prefix+"_latest");
      if(failures.size()<bestfailures && metrics.energy<1e-9){bestfailures=failures.size();save(best,prefix+"_best");}
      if(failures.empty() && metrics.energy<1e-9){save(best,prefix);cerr<<"SUCCESS_MIN2"<<endl;break;}
      if(pool.size()>500000){shuffle(pool.begin(),pool.end(),rng);pool.resize(400000);}
      addconstraints(failures,1000000);bestenergy=evaluate(best).energy+2*constraintenergy(best,0,true);current=best;energy=bestenergy;
    }
    if(iterations%100000==0){current=best;energy=bestenergy;cerr<<iterations<<" t="<<elapsed()<<" E="<<bestenergy<<" pool="<<pool.size()<<endl;}
  }
  save(best,prefix+"_latest");cerr<<"END "<<iterations<<" E="<<bestenergy<<endl;return 0;
}
