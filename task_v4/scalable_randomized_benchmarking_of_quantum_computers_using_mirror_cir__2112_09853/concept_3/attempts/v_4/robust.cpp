#pragma once
#define main ideal_main
#include "optimize.cpp"
#undef main
struct Constraint { array<int,3> omitted; Bits input; int weight; };
struct FaultResult { long scenarios=0,failed=0,violations=0;int minimum=100;vector<Constraint> constraints; };
vector<Constraint> getviolations(const Circuit &circuit,array<int,3> omitted) {
  Bits rows[40],images[60],mask=(1ULL<<nq)-1;maprows(circuit,rows,omitted);
  for(int qubit=0;qubit<nq;qubit++) {
    Bits ximage=((rows[nq+qubit]&mask)<<nq)|(rows[nq+qubit]>>nq);
    Bits zimage=((rows[qubit]&mask)<<nq)|(rows[qubit]>>nq);
    images[3*qubit]=ximage;images[3*qubit+1]=ximage^zimage;images[3*qubit+2]=zimage;
  }
  vector<Constraint> result;
  auto input=[](int axis){return (axis%3<2?1ULL<<(axis/3):0)|(axis%3>0?1ULL<<(nq+axis/3):0);};
  for(int first=0;first<3*nq;first++) {
    int observed=weight(images[first]);if(observed<3)result.push_back({omitted,input(first),observed});
    for(int second=(first/3+1)*3;second<3*nq;second++) {
      observed=weight(images[first]^images[second]);if(observed<3)result.push_back({omitted,input(first)^input(second),observed});
    }
  }
  return result;
}
FaultResult sweep(const Circuit &circuit,string path="") {
  FaultResult result;int gates=countcx(circuit);
  auto check=[&](array<int,3> omitted) {
    auto violations=getviolations(circuit,omitted); result.scenarios++;
    if(violations.size()) {result.failed++;result.violations+=violations.size();for(auto &constraint:violations){result.minimum=min(result.minimum,constraint.weight);result.constraints.push_back(constraint);}}
  };
  check({-1,-1,-1});
  for(int first=0;first<gates;first++) {
    check({first,-1,-1});
    for(int second=first+1;second<gates;second++) {
      check({first,second,-1});
      for(int third=second+1;third<gates;third++)check({first,second,third});
    }
  }
  if(path.size()) {ofstream output(path);for(auto &constraint:result.constraints)output<<constraint.omitted[0]<<' '<<constraint.omitted[1]<<' '<<constraint.omitted[2]<<' '<<constraint.input<<' '<<constraint.weight<<'\n';}
  return result;
}
#ifndef NO_ROBUST_MAIN
int main(int argc,char **argv) {
  setup(atoi(argv[1]));auto circuit=load(argv[2]);auto start=chrono::steady_clock::now();auto result=sweep(circuit,argc>3?argv[3]:"");
  printmetrics(evaluate(circuit));cerr<<"\nscenarios="<<result.scenarios<<" failed="<<result.failed<<" violations="<<result.violations<<" min="<<result.minimum<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<endl;
}
#endif
