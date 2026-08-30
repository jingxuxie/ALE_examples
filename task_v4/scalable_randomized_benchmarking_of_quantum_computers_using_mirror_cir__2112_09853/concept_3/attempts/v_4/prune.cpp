#define NO_CRITICAL_MAIN
#include "critical.cpp"
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(42);Circuit current=load(argv[2]);string prefix=argv[3];long currentcost=criticalscore(current);cerr<<"initial "<<countcx(current)<<" critical="<<currentcost<<endl;
  while(true){FastMap compiled(current);Circuit best=current;long bestcost=currentcost;bool found=false;int gates=countcx(current);
    for(int first=0;first<gates;first++)for(int second=first+1;second<gates;second++){
      array<Bits,3> left={compiled.first[first],compiled.second[first],compiled.first[first]^compiled.second[first]},right={compiled.first[second],compiled.second[second],compiled.first[second]^compiled.second[second]};sort(left.begin(),left.end());sort(right.begin(),right.end());if(left!=right)continue;
      Circuit candidate=current;int instance=0;for(auto &layer:candidate.layers){vector<pair<int,int>> remaining;for(auto gate:layer.cx){if(instance!=first && instance!=second)remaining.push_back(gate);instance++;}layer.cx=remaining;}
      long score=criticalscore(candidate,bestcost);if(score<=bestcost){best=move(candidate);bestcost=score;found=true;cerr<<"remove "<<first<<','<<second<<" -> "<<score<<endl;}
    }
    if(!found)break;current=best;currentcost=bestcost;
  }
  save(current,prefix);cerr<<"FINAL gates="<<countcx(current)<<" critical="<<currentcost;printmetrics(evaluate(current));cerr<<endl;return 0;}
