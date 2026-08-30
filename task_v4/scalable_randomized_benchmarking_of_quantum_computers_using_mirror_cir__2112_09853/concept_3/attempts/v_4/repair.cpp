#define NO_CRITICAL_MAIN
#include "critical.cpp"
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(atoi(argv[2]));Circuit source=load(argv[3]),best=source;string prefix=argv[4];double bestenergy=1e100;
  for(int trial=0;trial<64;trial++){
    Circuit candidate=source;int degrees[20]={};for(auto &layer:candidate.layers)for(auto gate:layer.cx){degrees[gate.first]++;degrees[gate.second]++;}
    for(int step=0;step<100;step++){
      vector<array<int,4>> moves;
      for(int qubit=0;qubit<nq;qubit++)if(degrees[qubit]<8)for(int round=0;round<rounds;round++){
        bool occupied=false;for(auto gate:candidate.layers[round].cx)if(gate.first==qubit || gate.second==qubit)occupied=true;if(occupied)continue;
        for(auto edge:edges)if(edge.first==qubit || edge.second==qubit){int neighbor=edge.first==qubit?edge.second:edge.first;
          for(int index=0;index<(int)candidate.layers[round].cx.size();index++){auto gate=candidate.layers[round].cx[index];int other=gate.first==neighbor?gate.second:gate.second==neighbor?gate.first:-1;if(other>=0 && degrees[other]>8)moves.push_back({round,index,qubit,other});}
        }
      }
      if(moves.empty())break;auto move=moves[randint(moves.size())];auto &gate=candidate.layers[move[0]].cx[move[1]];if(gate.first==move[3])gate.first=move[2];else gate.second=move[2];degrees[move[2]]++;degrees[move[3]]--;
    }
    if(*min_element(degrees,degrees+nq)<8)continue;auto metrics=evaluate(candidate);long critical=criticalscore(candidate,bestenergy-0.1*metrics.energy);double energy=critical+0.1*metrics.energy;
    if(energy<bestenergy){best=candidate;bestenergy=energy;cerr<<trial<<" critical="<<critical<<" E="<<energy<<endl;}
  }
  save(best,prefix);cerr<<"END E="<<bestenergy<<endl;return 0;}
