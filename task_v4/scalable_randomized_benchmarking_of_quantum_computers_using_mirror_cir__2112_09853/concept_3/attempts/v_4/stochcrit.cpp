#define NO_TRAIN_MAIN
#include "train.cpp"
#define NO_CRITICAL_MAIN
#include "critical.cpp"
vector<Constraint> failures(const Circuit &circuit) {auto result=sweep(circuit);vector<Constraint> filtered;for(auto &entry:result.constraints)if(entry.weight==1 || weight(entry.input)==1)filtered.push_back(entry);return filtered;}
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};auto bad=failures(best);addconstraints(bad,1000000);
  double bestreal=bad.size()+0.1*evaluate(best).energy;save(best,prefix);long iterations=0,accepted=0;int samplecount=argc>6?atoi(argv[6]):512;
  cerr<<"initial critical="<<bad.size()<<" E="<<bestreal<<endl;
  while(elapsed()<seconds){
    Circuit candidate=current;mutate(candidate);bool same=true;for(int round=0;round<rounds;round++)if(candidate.layers[round].cx!=current.layers[round].cx || (round>0 && candidate.layers[round].local!=current.layers[round].local)){same=false;break;}if(same)continue;
    double oldenergy=0.1*evaluate(current).energy+constraintenergy(current,0,true),newenergy=0.1*evaluate(candidate).energy+constraintenergy(candidate,0,true);
    double temperature=0.5*pow(0.1,(iterations%10000)/10000.0),limit=-temperature*log(max(1e-20,uniform01()));
    FastMap oldmap(current),newmap(candidate);int gates=min(countcx(current),countcx(candidate));long oldscore=0,newscore=0;
    for(int sample=0;sample<samplecount;sample++){
      array<int,3> omitted;do{omitted={randint(gates),randint(gates),randint(gates)};}while(omitted[0]==omitted[1]||omitted[0]==omitted[2]||omitted[1]==omitted[2]);sort(omitted.begin(),omitted.end());Bits oldcolumns[40],newcolumns[40];oldmap.columns(omitted,oldcolumns);newmap.columns(omitted,newcolumns);oldscore+=singlecritical(oldcolumns);newscore+=singlecritical(newcolumns);
    }
    double delta=newenergy-oldenergy+20*(newscore-oldscore);
    if(delta<=limit){current=move(candidate);accepted++;}
    iterations++;
    if(iterations%2000==0){
      bad=failures(current);auto metrics=evaluate(current);double real=bad.size()+0.1*metrics.energy;
      cerr<<iterations<<" t="<<elapsed()<<" critical="<<bad.size()<<" E="<<real<<" best="<<bestreal<<" pool="<<pool.size()<<" accept="<<accepted;printmetrics(metrics);cerr<<endl;save(current,prefix+"_latest");
      if(real<bestreal){bestreal=real;best=current;save(best,prefix);}
      if(bad.empty()){save(current,prefix+"_safe");cerr<<"SAFE MINIMUM TWO"<<endl;if(metrics.ratio>=2.0/3){save(current,prefix);break;}}
      addconstraints(bad,1000000);if(pool.size()>100000){shuffle(pool.begin(),pool.end(),rng);pool.resize(80000);compilepool();}
      if(real>bestreal+10 || iterations%10000==0)current=best;
    }
  }
  save(best,prefix);cerr<<"END best="<<bestreal<<endl;return 0;
}
