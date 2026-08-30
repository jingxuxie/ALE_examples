#define NO_ROBUST_MAIN
#include "robust.cpp"
#include <set>
#include <tuple>
struct Batch { array<Bits,40> inputs{};array<Bits,120> enabled;Bits active=0,needs3=0; };
vector<Constraint> pool;
vector<Batch> batches;
void compilepool() {
  batches.clear();
  for(size_t start=0;start<pool.size();start+=64) {
    Batch batch;batch.enabled.fill(~0ULL);
    for(size_t index=start;index<min(start+64,pool.size());index++) {
      Bits bit=1ULL<<(index-start);batch.active|=bit;Bits input=pool[index].input;
      if(weight(input)==1)batch.needs3|=bit;
      while(input) {int position=__builtin_ctzll(input);input&=input-1;batch.inputs[position]|=bit;}
      for(int omitted:pool[index].omitted)if(omitted>=0 && omitted<120)batch.enabled[omitted]&=~bit;
    }
    batches.push_back(batch);
  }
}
double constraintenergy(const Circuit &circuit,double margin=0,bool criticalonly=false) {
  double result=0;int gates=countcx(circuit);
  for(auto &batch:batches) {
    Bits rows[40];copy(batch.inputs.begin(),batch.inputs.begin()+2*nq,rows);int instance=gates;
    for(int round=rounds-1;round>=0;round--) {
      auto &layer=circuit.layers[round];
      for(int index=layer.cx.size()-1;index>=0;index--) {
        auto [control,target]=layer.cx[index];Bits mask=batch.enabled[--instance];rows[target]^=rows[control]&mask;rows[nq+control]^=rows[nq+target]&mask;
      }
      if(round==0)break;
      for(int qubit=0;qubit<nq;qubit++) {
        Bits xbits=rows[qubit],zbits=rows[nq+qubit];
        switch(layer.local[qubit]) {
          case 0: break;
          case 1: rows[qubit]=zbits;rows[nq+qubit]=xbits;break;
          case 2: rows[nq+qubit]=xbits^zbits;break;
          case 3: rows[qubit]=xbits^zbits;rows[nq+qubit]=xbits;break;
          case 4: rows[qubit]=zbits;rows[nq+qubit]=xbits^zbits;break;
          case 5: rows[qubit]=xbits^zbits;break;
        }
      }
    }
    Bits seen1=0,seen2=0,seen3=0,seen4=0;
    for(int qubit=0;qubit<nq;qubit++) {Bits support=rows[qubit]|rows[nq+qubit];seen4|=seen3&support;seen3|=seen2&support;seen2|=seen1&support;seen1|=support;}
    result+=4*__builtin_popcountll(batch.active&seen1&~seen2)+__builtin_popcountll((criticalonly?batch.needs3:batch.active)&seen2&~seen3)+margin*__builtin_popcountll(batch.active&seen3&~seen4);
  }
  return result;
}
void addconstraints(vector<Constraint> constraints,int limit) {
  shuffle(constraints.begin(),constraints.end(),rng);
  stable_sort(constraints.begin(),constraints.end(),[](auto &left,auto &right){return count(left.omitted.begin(),left.omitted.end(),-1)>count(right.omitted.begin(),right.omitted.end(),-1);});
  set<tuple<int,int,int,Bits>> known;
  for(auto &entry:pool)known.insert({entry.omitted[0],entry.omitted[1],entry.omitted[2],entry.input});
  int added=0;
  for(auto &entry:constraints) {
    Bits support=(entry.input|(entry.input>>nq))&((1ULL<<nq)-1);int first=__builtin_ctzll(support);support&=support-1;int second=support?__builtin_ctzll(support):-1;
    bool changed=false;
    for(int firstaxis=1;firstaxis<=3;firstaxis++)for(int secondaxis=1;secondaxis<=(second<0?1:3);secondaxis++) {
      Bits input=(firstaxis&1?1ULL<<first:0)|(firstaxis&2?1ULL<<(nq+first):0);
      if(second>=0)input|=(secondaxis&1?1ULL<<second:0)|(secondaxis&2?1ULL<<(nq+second):0);
      if(known.insert({entry.omitted[0],entry.omitted[1],entry.omitted[2],input}).second) {pool.push_back({entry.omitted,input,entry.weight});changed=true;}
    }
    if(changed && ++added>=limit)break;
  }
  compilepool();
}
#ifndef NO_TRAIN_MAIN
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit initial=load(argv[5]);
  auto started=chrono::steady_clock::now();auto elapsed=[&](){return chrono::duration<double>(chrono::steady_clock::now()-started).count();};
  auto faults=sweep(initial);cerr<<"initial faults="<<faults.violations<<endl;
  addconstraints(faults.constraints,1000000);
  cerr<<"initial batch energy="<<constraintenergy(initial)<<" expected=";int expected=0;for(auto &entry:pool)expected+=(3-entry.weight)*(3-entry.weight);cerr<<expected<<endl;
  Circuit best=initial,current=initial;double bestenergy=evaluate(best).energy+2*constraintenergy(best),energy=bestenergy;
  long bestviolations=faults.violations;save(initial,prefix+"_best");
  long iterations=0,lastsweep=0;int epochs=0;
  while(elapsed()<seconds) {
    Circuit candidate=current;mutate(candidate);
    bool changed=false;for(int round=0;round<rounds;round++)if(candidate.layers[round].cx.size()!=current.layers[round].cx.size())changed=true;
    if(changed)continue;
    double tested=evaluate(candidate).energy+2*constraintenergy(candidate);
    double phase=(iterations%100000)/100000.0,temperature=4*pow(0.025,phase);
    if(tested<=energy || uniform01()<exp((energy-tested)/temperature)) {current=move(candidate);energy=tested;}
    if(tested<bestenergy) {best=current;bestenergy=tested;}
    iterations++;
    if(bestenergy<1e-9 || iterations-lastsweep>=300000) {
      lastsweep=iterations;faults=sweep(best);auto metrics=evaluate(best);
      cerr<<"SWEEP "<<iterations<<" t="<<elapsed()<<" pool="<<pool.size()<<" E="<<bestenergy<<" faults="<<faults.violations<<" scenarios="<<faults.failed;printmetrics(metrics);cerr<<endl;
      save(best,prefix+"_latest");
      if(metrics.energy<1e-9 && faults.violations<bestviolations) {bestviolations=faults.violations;save(best,prefix+"_best");}
      if(faults.violations==0 && metrics.energy<1e-9) {save(best,prefix);cerr<<"SUCCESS"<<endl;break;}
      if(pool.size()>500000) {shuffle(pool.begin(),pool.end(),rng);pool.resize(400000);}
      addconstraints(faults.constraints,1000000);epochs++;
      bestenergy=evaluate(best).energy+2*constraintenergy(best);current=best;energy=bestenergy;
    }
    if(iterations%100000==0) {current=best;energy=bestenergy;cerr<<iterations<<" t="<<elapsed()<<" E="<<bestenergy<<" pool="<<pool.size()<<endl;}
  }
  save(best,prefix+"_latest");cerr<<"END "<<iterations<<" t="<<elapsed()<<" E="<<bestenergy<<endl;return 0;
}
#endif
