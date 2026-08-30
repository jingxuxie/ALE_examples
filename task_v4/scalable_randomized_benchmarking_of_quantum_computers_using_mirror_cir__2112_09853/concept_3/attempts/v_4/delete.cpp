#define NO_CRITICAL_MAIN
#include "critical.cpp"
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(42);Circuit current=load(argv[2]);string prefix=argv[3];double energy=criticalscore(current)+0.1*evaluate(current).energy;save(current,prefix);cerr<<"initial "<<energy<<endl;
  for(int pass=0;pass<30;pass++){Circuit best=current;double bestenergy=energy;bool found=false;
    for(int round=0;round<rounds;round++)for(int index=0;index<(int)current.layers[round].cx.size();index++){Circuit candidate=current;candidate.layers[round].cx.erase(candidate.layers[round].cx.begin()+index);auto metrics=evaluate(candidate);double ideal=0.1*metrics.energy;if(ideal>=bestenergy)continue;long critical=criticalscore(candidate,bestenergy-ideal);double tested=critical+ideal;if(tested<bestenergy){best=candidate;bestenergy=tested;found=true;cerr<<"candidate "<<pass<<" critical="<<critical<<" E="<<tested<<endl;}}
    if(!found)break;current=best;energy=bestenergy;save(current,prefix);if(criticalscore(current)==0){save(current,prefix+"_safe");break;}
  }
  cerr<<"FINAL critical="<<criticalscore(current);printmetrics(evaluate(current));cerr<<endl;save(current,prefix);return 0;}
