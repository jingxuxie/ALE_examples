#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

extern "C" int project_pairs(const double* values,double* result,const double* known,int size,int capacity) {
    int half=size/2,states=capacity+1;
    double infinity=std::numeric_limits<double>::infinity();
    std::vector<double> costs(half*states,infinity),previous(states),next(states);
    std::vector<int> back(half*states,-1),lower(half),upper(half),sums(half);
    for (int index=0;index<half;++index) {
        sums[index]=std::lround(known[index]);
        lower[index]=std::max(0,sums[index]-capacity);
        upper[index]=std::min(sums[index],capacity);
        for (int choice=lower[index];choice<=upper[index];++choice) {
            double first=choice-values[index],second=sums[index]-choice-values[index+half];
            costs[index*states+choice]=first*first+second*second;
        }
    }
    auto compatible=[&](int first,int second) {return (first+1)/2+(second+1)/2<=capacity/2;};
    double best=infinity;
    for (int initial=lower[0];initial<=upper[0];++initial) {
        std::fill(previous.begin(),previous.end(),infinity);
        previous[initial]=costs[initial];
        for (int index=1;index<half;++index) {
            std::fill(next.begin(),next.end(),infinity);
            for (int choice=lower[index];choice<=upper[index];++choice) {
                for (int preceding=lower[index-1];preceding<=upper[index-1];++preceding) {
                    if (!compatible(choice,preceding) || !compatible(sums[index]-choice,sums[index-1]-preceding)) continue;
                    double score=previous[preceding]+costs[index*states+choice];
                    if (score<next[choice]) {next[choice]=score;back[index*states+choice]=preceding;}
                }
            }
            previous.swap(next);
        }
        for (int last=lower[half-1];last<=upper[half-1];++last) {
            if (!compatible(last,sums[0]-initial) || !compatible(sums[half-1]-last,initial)) continue;
            if (previous[last]<best) {
                best=previous[last];
                int choice=last;
                for (int index=half-1;index>=0;--index) {
                    result[index]=choice;result[index+half]=sums[index]-choice;
                    if (index) choice=back[index*states+choice];
                }
            }
        }
    }
    return std::isfinite(best);
}
