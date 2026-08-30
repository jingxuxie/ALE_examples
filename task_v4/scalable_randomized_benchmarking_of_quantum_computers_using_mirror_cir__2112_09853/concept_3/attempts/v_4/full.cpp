#define NO_ROBUST_MAIN
#include "robust.cpp"
#include "fastmap.hpp"
struct ExactScore {long critical=0,ordinary=0;double energy=0;bool complete=true;};
vector<array<int,3>> scenarios;
int scenario_gates=-1;
void orderscenarios(int gates) {
  if(gates==scenario_gates)return;scenario_gates=gates;scenarios.clear();scenarios.push_back({-1,-1,-1});
  for(int first=0;first<gates;first++){scenarios.push_back({first,-1,-1});for(int second=first+1;second<gates;second++){scenarios.push_back({first,second,-1});for(int third=second+1;third<gates;third++)scenarios.push_back({first,second,third});}}
  shuffle(scenarios.begin(),scenarios.end(),rng);
}
ExactScore exactscore(const Circuit &circuit,double limit=1e100,double criticalweight=100) {
  orderscenarios(countcx(circuit));ExactScore result;FastMap compiled(circuit);
  for(auto omitted:scenarios) {
    Bits columns[40],images[60];compiled.columns(omitted,columns);
    for(int qubit=0;qubit<nq;qubit++) {
      Bits ximage=columns[qubit],zimage=columns[nq+qubit];
      images[3*qubit]=ximage;images[3*qubit+1]=ximage^zimage;images[3*qubit+2]=zimage;
    }
    for(int first=0;first<3*nq;first++) {
      int observed=weight(images[first]);if(observed<3)result.critical++;
      for(int second=(first/3+1)*3;second<3*nq;second++) {observed=weight(images[first]^images[second]);result.critical+=observed<2;result.ordinary+=observed==2;}
    }
    result.energy=criticalweight*result.critical+result.ordinary;
    if(result.energy>limit){result.complete=false;break;}
  }
  return result;
}
#ifndef NO_FULL_MAIN
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};
  double idealweight=argc>6?atof(argv[6]):10000,criticalweight=argc>7?atof(argv[7]):100;
  double maxtemperature=argc>8?atof(argv[8]):100;
  auto currentmetrics=evaluate(current);auto currentscore=exactscore(current,1e100,criticalweight);double energy=currentscore.energy+idealweight*currentmetrics.energy;
  double bestenergy=energy;long iterations=0,accepted=0;save(best,prefix);
  cerr<<"initial critical="<<currentscore.critical<<" ordinary="<<currentscore.ordinary<<" E="<<energy<<endl;
  while(elapsed()<seconds) {
    Circuit candidate=current;mutate(candidate);
    bool same=true;for(int round=0;round<rounds;round++)if(candidate.layers[round].cx!=current.layers[round].cx || (round>0 && candidate.layers[round].local!=current.layers[round].local)){same=false;break;}if(same)continue;
    auto metrics=evaluate(candidate);double temperature=maxtemperature*pow(0.05,(iterations%1000)/1000.0),limit=energy-temperature*log(max(1e-20,uniform01()));
    if(metrics.energy*idealweight<=limit) {
      auto score=exactscore(candidate,limit-metrics.energy*idealweight,criticalweight);double tested=score.energy+idealweight*metrics.energy;
      if(score.complete && tested<=limit) {
        current=move(candidate);energy=tested;currentscore=score;currentmetrics=metrics;accepted++;
        if(energy<bestenergy) {best=current;bestenergy=energy;save(best,prefix);cerr<<"BEST "<<iterations<<" t="<<elapsed()<<" critical="<<score.critical<<" ordinary="<<score.ordinary<<" E="<<energy;printmetrics(metrics);cerr<<endl;}
        if(score.critical==0 && metrics.energy<1e-9)save(current,prefix+"_safe");
        if(score.energy==0 && metrics.energy<1e-9){cerr<<"SUCCESS"<<endl;break;}
      }
    }
    iterations++;
    if(iterations%100==0)cerr<<iterations<<" t="<<elapsed()<<" best="<<bestenergy<<" current="<<energy<<" accept="<<accepted<<endl;
    if(iterations%1000==0){current=best;currentmetrics=evaluate(current);currentscore=exactscore(current,1e100,criticalweight);energy=currentscore.energy+idealweight*currentmetrics.energy;}
  }
  save(best,prefix);cerr<<"END "<<iterations<<" best="<<bestenergy<<endl;return 0;
}
#endif
