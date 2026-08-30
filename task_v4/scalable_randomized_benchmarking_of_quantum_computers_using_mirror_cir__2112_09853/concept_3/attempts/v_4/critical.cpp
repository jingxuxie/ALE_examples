#define NO_FULL_MAIN
#include "full.cpp"
int singlecritical(const Bits *columns) {
  int result=0;Bits seen1=0,seen2=0,seen3=0,yseen1=0,yseen2=0,yseen3=0,mask=(1ULL<<nq)-1;
  for(int qubit=0;qubit<nq;qubit++) {
    Bits ximage=columns[qubit],zimage=columns[nq+qubit];
    for(Bits image:{ximage,zimage,ximage^zimage}){int deficit=max(0,3-weight(image));result+=deficit*deficit;}
    Bits support=ximage|zimage,ysupport=((ximage^(ximage>>nq))|(zimage^(zimage>>nq)))&mask;
    seen3|=seen2&support;seen2|=seen1&support;seen1|=support;
    yseen3|=yseen2&ysupport;yseen2|=yseen1&ysupport;yseen1|=ysupport;
  }
  result+=4*__builtin_popcountll(seen1&~seen2)+__builtin_popcountll(seen2&~seen3);
  result+=4*__builtin_popcountll(yseen1&~yseen2)+__builtin_popcountll(yseen2&~yseen3);return result;
}
long criticalscore(const Circuit &circuit,double limit=1e100) {
  orderscenarios(countcx(circuit));FastMap compiled(circuit);long result=0;
  for(auto omitted:scenarios){Bits columns[40];compiled.columns(omitted,columns);result+=singlecritical(columns);if(result>limit)return result;}return result;
}
#ifndef NO_CRITICAL_MAIN
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};
  double idealweight=argc>6?atof(argv[6]):0.1;long critical=criticalscore(current);auto metrics=evaluate(current);double energy=critical+idealweight*metrics.energy,bestenergy=energy;
  bool safe=critical==0;long iterations=0,accepted=0;save(best,prefix);cerr<<"initial critical="<<critical<<" ideal="<<metrics.energy<<endl;
  if(safe){energy=metrics.energy;bestenergy=energy;}
  while(elapsed()<seconds) {
    Circuit candidate=current;mutate(candidate);bool same=true;for(int round=0;round<rounds;round++)if(candidate.layers[round].cx!=current.layers[round].cx || (round>0 && candidate.layers[round].local!=current.layers[round].local)){same=false;break;}if(same)continue;
    auto testedmetrics=evaluate(candidate);double temperature=(safe?2:3)*pow(0.025,(iterations%3000)/3000.0),limit=energy-temperature*log(max(1e-20,uniform01()));
    double idealpart=(safe?1:idealweight)*testedmetrics.energy;
    if(idealpart<=limit) {
      long testedcritical=criticalscore(candidate,safe?0:limit-idealpart);double tested=testedcritical+idealpart;
      if((!safe || testedcritical==0) && tested<=limit) {
        current=move(candidate);energy=tested;critical=testedcritical;metrics=testedmetrics;accepted++;
        if(energy<bestenergy){best=current;bestenergy=energy;save(best,prefix);cerr<<"BEST "<<iterations<<" t="<<elapsed()<<" critical="<<critical<<" E="<<energy;printmetrics(metrics);cerr<<endl;}
        if(!safe && critical==0){safe=true;best=current;energy=metrics.energy;bestenergy=energy;save(best,prefix+"_safe");save(best,prefix);cerr<<"SAFE MINIMUM TWO"<<endl;}
        if(safe && metrics.energy<1e-9){save(current,prefix);save(current,prefix+"_safe");cerr<<"SUCCESS_MIN2"<<endl;break;}
      }
    }
    iterations++;
    if(iterations%500==0)cerr<<iterations<<" t="<<elapsed()<<" best="<<bestenergy<<" current="<<energy<<" safe="<<safe<<" accept="<<accepted<<endl;
    if(iterations%3000==0){current=best;metrics=evaluate(current);critical=criticalscore(current);energy=critical+(safe?1:idealweight)*metrics.energy;}
  }
  save(best,prefix);cerr<<"END best="<<bestenergy<<endl;return 0;
}
#endif
