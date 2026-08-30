#define NO_ROBUST_MAIN
#include "robust.cpp"
double onescore(const Circuit &circuit,int desired=5) {
  double result=0;
  for(int omitted=0;omitted<countcx(circuit);omitted++) {
    Bits rows[40],forward[40],inverse[40];maprows(circuit,rows,{omitted,-1,-1});imagesfromrows(rows,forward,inverse);
    for(int direction=0;direction<2;direction++) {
      Bits *images=direction?inverse:forward,singles[60];
      for(int qubit=0;qubit<nq;qubit++) {singles[3*qubit]=images[qubit];singles[3*qubit+1]=images[qubit]^images[nq+qubit];singles[3*qubit+2]=images[nq+qubit];}
      for(int first=0;first<3*nq;first++) {
        int deficit=max(0,desired-weight(singles[first]));result+=deficit*deficit;
        for(int second=(first/3+1)*3;second<3*nq;second++) {deficit=max(0,desired-weight(singles[first]^singles[second]));result+=deficit*deficit;}
      }
    }
  }
  return result;
}
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(atoi(argv[2]));int seconds=atoi(argv[3]);string prefix=argv[4];Circuit best=load(argv[5]),current=best;
  int desired=argc>6?atoi(argv[6]):5;
  double bestenergy=evaluate(best).energy+0.1*onescore(best,desired),energy=bestenergy;
  auto start=chrono::steady_clock::now();long iterations=0;double elapsed=0;
  while(elapsed<seconds) {
    Circuit candidate=current;mutate(candidate);double tested=evaluate(candidate).energy+0.1*onescore(candidate,desired);
    double temperature=2*pow(0.03,(iterations%30000)/30000.0);
    if(tested<=energy || uniform01()<exp((energy-tested)/temperature)) {current=move(candidate);energy=tested;}
    if(tested<bestenergy){best=current;bestenergy=tested;save(best,prefix);}
    iterations++;
    if(iterations%10000==0 || bestenergy<1e-9) {elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();cerr<<iterations<<" t="<<elapsed<<" E="<<bestenergy<<" one="<<onescore(best,desired);printmetrics(evaluate(best));cerr<<endl;}
    if(iterations%30000==0){current=best;energy=bestenergy;}
    if(bestenergy<1e-9)break;
  }
  auto faults=sweep(best);cerr<<"FINAL faults="<<faults.violations<<" min="<<faults.minimum<<endl;save(best,prefix);return 0;
}
