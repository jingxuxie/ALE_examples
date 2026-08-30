#define NO_CRITICAL_MAIN
#include "critical.cpp"
using Axes=array<array<int,20>,12>;
vector<int> visits[20];Circuit pattern;
int transformaxis(int word,int axis){for(char gate:words[word]){if(gate=='H')axis=((axis&1)<<1)|((axis>>1)&1);else if(gate=='S')axis^=(axis&1)<<1;}return axis;}
int inverseword(int word){return word==3?4:word==4?3:word;}
Circuit construct(const Axes &axes){Circuit circuit=pattern;int frames[20]={};
  for(int round=0;round<rounds;round++){
    circuit.layers[round].local.fill(0);
    for(auto [control,target]:circuit.layers[round].cx)for(int qubit:{control,target}){
      int native=qubit==control?2:1,frame=0;while(transformaxis(frame,axes[round][qubit])!=native)frame++;
      circuit.layers[round].local[qubit]=localcompose(frame,inverseword(frames[qubit]));frames[qubit]=frame;
    }
  }
  return circuit;
}
Axes extract(){Axes axes{};int frames[20]={};for(int round=0;round<rounds;round++){
  for(int qubit=0;qubit<nq;qubit++)frames[qubit]=localcompose(pattern.layers[round].local[qubit],frames[qubit]);
  for(auto [control,target]:pattern.layers[round].cx)for(int qubit:{control,target}){axes[round][qubit]=transformaxis(inverseword(frames[qubit]),qubit==control?2:1);visits[qubit].push_back(round);}
}return axes;}
void rebalance(Axes &axes){for(int qubit=0;qubit<nq;qubit++){
  int counts[4]={};for(int round:visits[qubit])counts[axes[round][qubit]]++;int cap=visits[qubit].size()-5;
  for(int repeat=0;repeat<20;repeat++){int largest=max_element(counts+1,counts+4)-counts,smallest=min_element(counts+1,counts+4)-counts;if(counts[largest]<=cap)break;
    vector<int> choices;for(int round:visits[qubit])if(axes[round][qubit]==largest)choices.push_back(round);axes[choices[randint(choices.size())]][qubit]=smallest;counts[largest]--;counts[smallest]++;
  }
}}
bool mutateaxes(Axes &axes){int qubit=randint(nq);auto &positions=visits[qubit];if(positions.size()<2)return false;
  int first=positions[randint(positions.size())],second=positions[randint(positions.size())];if(first==second)return false;
  if(randint(100)<80){if(axes[first][qubit]==axes[second][qubit])return false;swap(axes[first][qubit],axes[second][qubit]);return true;}
  int replacement=1+randint(3);if(replacement==axes[first][qubit])return false;int count=0;for(int round:positions)count+=axes[round][qubit]==replacement;if(count+1>int(positions.size())-5)return false;axes[first][qubit]=replacement;return true;
}
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];pattern=load(argv[5]);Axes best=extract();
  cerr<<"reconstruction original="<<evaluate(pattern).energy<<" reconstructed="<<evaluate(construct(best)).energy<<endl;rebalance(best);Axes current=best;Circuit currentcircuit=construct(current);
  double idealweight=0.1;long critical=criticalscore(currentcircuit);double energy=critical+idealweight*evaluate(currentcircuit).energy,bestenergy=energy;long iterations=0,accepted=0;
  auto start=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};save(currentcircuit,prefix);cerr<<"initial critical="<<critical<<" E="<<energy<<endl;
  while(elapsed()<seconds){Axes candidate=current;if(!mutateaxes(candidate))continue;Circuit circuit=construct(candidate);auto metrics=evaluate(circuit);double temperature=2*pow(0.025,(iterations%2000)/2000.0),limit=energy-temperature*log(max(1e-20,uniform01()));
    if(idealweight*metrics.energy<=limit){long testedcritical=criticalscore(circuit,limit-idealweight*metrics.energy);double tested=testedcritical+idealweight*metrics.energy;
      if(tested<=limit){current=candidate;currentcircuit=move(circuit);energy=tested;critical=testedcritical;accepted++;
        if(energy<bestenergy){best=current;bestenergy=energy;save(currentcircuit,prefix);cerr<<"BEST "<<iterations<<" t="<<elapsed()<<" critical="<<critical<<" E="<<energy;printmetrics(metrics);cerr<<endl;}
        if(critical==0){save(currentcircuit,prefix+"_safe");cerr<<"SAFE ratio="<<metrics.ratio<<endl;if(metrics.ratio>=2.0/3){save(currentcircuit,prefix);best=current;break;}}
      }
    }
    iterations++;if(iterations%500==0)cerr<<iterations<<" t="<<elapsed()<<" best="<<bestenergy<<" current="<<energy<<" accept="<<accepted<<endl;
    if(iterations%2000==0){current=best;currentcircuit=construct(current);energy=bestenergy;}
  }
  save(construct(best),prefix);cerr<<"END "<<iterations<<" best="<<bestenergy<<endl;return 0;
}
