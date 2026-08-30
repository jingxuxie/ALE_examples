#define NO_CRITICAL_MAIN
#include "critical.cpp"
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(42);auto circuit=load(argv[2]);FastMap compiled(circuit);int gates=countcx(circuit);
  for(int trial=0;trial<10000;trial++){
    array<int,3> omitted;do{omitted={randint(gates),randint(gates),randint(gates)};}while(omitted[0]==omitted[1]||omitted[0]==omitted[2]||omitted[1]==omitted[2]);sort(omitted.begin(),omitted.end());
    Bits rows[40],forward[40],inverse[40];maprows(circuit,rows,omitted);imagesfromrows(rows,forward,inverse);int expected=0;
    for(auto images:{forward,inverse})for(int qubit=0;qubit<nq;qubit++)for(Bits image:{images[qubit],images[nq+qubit],images[qubit]^images[nq+qubit]}){int deficit=max(0,3-weight(image));expected+=deficit*deficit;}
    if(singlecritical(inverse)!=expected){cerr<<"FAIL "<<trial<<" got="<<singlecritical(inverse)<<" expected="<<expected<<endl;return 1;}
  }
  cerr<<"OK"<<endl;return 0;}
