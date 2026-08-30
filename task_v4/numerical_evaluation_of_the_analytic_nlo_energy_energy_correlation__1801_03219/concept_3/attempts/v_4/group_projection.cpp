#include <algorithm>
#include <limits>
#include <numeric>
#include <vector>

extern "C" void project_groups(const double* values,double* result,const int* totals,int groups,int size) {
    int length=size/groups;
    std::vector<int> ordering(size),back(groups*257,-1);
    std::vector<double> prefix(groups*(length+1)),previous(257,-1e100),next(257),scores(length+1);
    previous[0]=0;
    for (int group=0;group<groups;++group) {
        auto first=ordering.begin()+group*length;
        for (int index=0;index<length;++index) first[index]=group+index*groups;
        std::sort(first,first+length,[&](int left,int right){return values[left]>values[right];});
        double* sums=prefix.data()+group*(length+1);
        for (int index=0;index<length;++index) sums[index+1]=sums[index]+values[first[index]];
        int maximum=std::min(totals[group]/2,256),minimum=std::max(0,totals[group]-length);
        for (int twos=minimum;twos<=maximum;++twos) scores[twos]=2*sums[twos]+2*sums[totals[group]-twos]-2*twos-totals[group];
        std::fill(next.begin(),next.end(),-1e100);
        for (int total=0;total<=256;++total) for (int twos=minimum;twos<=maximum && twos<=total;++twos) {
            double score=previous[total-twos]+scores[twos];
            if (score>next[total]) {next[total]=score;back[group*257+total]=twos;}
        }
        previous.swap(next);
    }
    std::fill(result,result+size,0);
    int remaining=256;
    for (int group=groups-1;group>=0;--group) {
        int twos=back[group*257+remaining];remaining-=twos;
        for (int index=0;index<totals[group]-twos;++index) result[ordering[group*length+index]]=index<twos ? 2 : 1;
    }
}
