#define NO_FULL_MAIN
#include "full.cpp"
int main(int argc,char **argv) {
  setup(atoi(argv[1]));rng.seed(91);Circuit circuit=load(argv[2]);FastMap compiled(circuit);int gates=countcx(circuit);
  for(int trial=0;trial<10000;trial++) {
    array<int,3> omitted;do{omitted={randint(gates),randint(gates),randint(gates)};}while(omitted[0]==omitted[1]||omitted[0]==omitted[2]||omitted[1]==omitted[2]);sort(omitted.begin(),omitted.end());
    for(int index=0;index<trial%4;index++)omitted[2-index]=-1;
    Bits rows[40],forward[40],inverse[40],columns[40];maprows(circuit,rows,omitted);imagesfromrows(rows,forward,inverse);compiled.columns(omitted,columns);
    for(int index=0;index<2*nq;index++)if(columns[index]!=inverse[index]){cerr<<"FAIL "<<trial<<' '<<index<<endl;return 1;}
  }
  auto start=chrono::steady_clock::now();auto score=exactscore(circuit);cerr<<"OK critical="<<score.critical<<" ordinary="<<score.ordinary<<" time="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<endl;return 0;
}
