#include <cmath>
#include <algorithm>
extern "C" void polynomial(const int* word, const double* half, double* cubic, double* jac) {
    double first[5]={}, second[25]={}, dfirst[5][17]={}, dsecond[25][17]={};
    std::fill(cubic,cubic+125,0.0);
    std::fill(jac,jac+125*17,0.0);
    for(int stage=0;stage<33;stage++) {
        int index=stage<17?stage:32-stage;
        int comp=word[index]; double coeff=half[index];
        for(int left=0;left<5;left++) for(int middle=0;middle<5;middle++) {
            int pair=left*5+middle, triple=pair*5+comp;
            cubic[triple]+=coeff*second[pair];
            for(int variable=0;variable<17;variable++) jac[triple*17+variable]+=coeff*dsecond[pair][variable];
            jac[triple*17+index]+=second[pair];
        }
        for(int left=0;left<5;left++) {
            int triple=left*25+comp*5+comp;
            cubic[triple]+=coeff*coeff*0.5*first[left];
            for(int variable=0;variable<17;variable++) jac[triple*17+variable]+=coeff*coeff*0.5*dfirst[left][variable];
            jac[triple*17+index]+=coeff*first[left];
        }
        int triple=comp*31;
        cubic[triple]+=coeff*coeff*coeff/6;
        jac[triple*17+index]+=coeff*coeff/2;
        for(int left=0;left<5;left++) {
            int pair=left*5+comp;
            second[pair]+=coeff*first[left];
            for(int variable=0;variable<17;variable++) dsecond[pair][variable]+=coeff*dfirst[left][variable];
            dsecond[pair][index]+=first[left];
        }
        second[comp*6]+=coeff*coeff/2;
        dsecond[comp*6][index]+=coeff;
        first[comp]+=coeff;
        dfirst[comp][index]+=1;
    }
    for(int triple=0;triple<125;triple++) cubic[triple]-=1.0/6;
}
