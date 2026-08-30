#define NO_FULL_MAIN
#include "full.cpp"
int main(int argc,char **argv){setup(atoi(argv[1]));rng.seed(42);auto circuit=load(argv[2]);auto metrics=evaluate(circuit);auto faults=exactscore(circuit);double robust=faults.critical?1.0/3:faults.ordinary?2.0/3:1;
  cout<<setprecision(15)<<"{\"core_score\":"<<min(metrics.ratio,robust)<<",\"ideal_score\":"<<metrics.ratio<<",\"critical\":"<<faults.critical<<",\"ordinary\":"<<faults.ordinary<<",\"ideal_energy\":"<<metrics.energy<<"}\n";return 0;}
