#include <cmath>
#include <complex>
#include <algorithm>

using Real = double;
using Complex = std::complex<Real>;
struct Vec {
    Real energy,px,py,pz;
    Vec operator+(const Vec& rhs) const { return {energy+rhs.energy,px+rhs.px,py+rhs.py,pz+rhs.pz}; }
    Vec operator-(const Vec& rhs) const { return {energy-rhs.energy,px-rhs.px,py-rhs.py,pz-rhs.pz}; }
    Vec operator*(Real scale) const { return {energy*scale,px*scale,py*scale,pz*scale}; }
};
static Real dot(const Vec& left,const Vec& right) { return left.energy*right.energy-left.px*right.px-left.py*right.py-left.pz*right.pz; }
struct Spin {
    Complex first,second;
    Spin operator+(const Spin& rhs) const {return {first+rhs.first,second+rhs.second};}
    Spin operator*(Real scale) const {return {first*scale,second*scale};}
};
static Spin column(const Vec& vec,const Spin& spin,int sign) {
    return {(vec.energy+sign*vec.pz)*spin.first+Complex(sign*vec.px,-sign*vec.py)*spin.second,
            Complex(sign*vec.px,sign*vec.py)*spin.first+(vec.energy-sign*vec.pz)*spin.second};
}
static Spin row(const Spin& spin,const Vec& vec,int sign) {
    return {(vec.energy+sign*vec.pz)*spin.first+Complex(sign*vec.px,sign*vec.py)*spin.second,
            Complex(sign*vec.px,-sign*vec.py)*spin.first+(vec.energy-sign*vec.pz)*spin.second};
}
static Spin spinor(const Vec& momentum) {
    if(momentum.pz>=0) {
        Real scale=std::sqrt(momentum.energy+momentum.pz);
        return {-Complex(momentum.px,-momentum.py)/scale,scale};
    }
    Real scale=std::sqrt(momentum.energy-momentum.pz);
    return {-scale,Complex(momentum.px,momentum.py)/scale};
}
static void polarizations(const Vec& momentum,Vec* result) {
    Vec direction=momentum*(1/momentum.energy);
    Vec first;
    if(std::abs(direction.px)<=std::abs(direction.py) && std::abs(direction.px)<=std::abs(direction.pz))
        first={0,0,direction.pz,-direction.py};
    else if(std::abs(direction.py)<=std::abs(direction.pz)) first={0,-direction.pz,0,direction.px};
    else first={0,direction.py,-direction.px,0};
    first=first*(1/std::sqrt(-dot(first,first)));
    result[0]=first;
    result[1]={0,direction.py*first.pz-direction.pz*first.py,direction.pz*first.px-direction.px*first.pz,direction.px*first.py-direction.py*first.px};
}
static Vec three(const Vec& left,const Vec& right,const Vec& pl,const Vec& pr) {
    return (pr-pl)*dot(left,right)+left*(2*dot(pl,right))-right*(2*dot(pr,left));
}
static Real fermion(const Spin* endpoint,const Vec current[3][4],const Vec prefix[2][3],const Vec suffix[2][3],int quark,int antiquark) {
    Spin left[4],right[4];
    left[0]={std::conj(endpoint[quark].first),std::conj(endpoint[quark].second)};
    right[3]=endpoint[antiquark];
    for(int end=1;end<=3;++end) {
        Spin value={0,0};
        for(int start=0;start<end;++start) value=value+row(left[start],current[start][end],1);
        left[end]=row(value,prefix[quark][end-1],-1);
    }
    for(int start=2;start>=0;--start) {
        Spin value={0,0};
        for(int end=start+1;end<=3;++end) value=value+column(current[start][end],right[end],1);
        right[start]=column(suffix[antiquark][start],value,-1);
    }
    Complex amp0=0,amp1=0,amp2=0,amp3=0;
    for(int split=0;split<=3;++split) {
        Complex aa=left[split].first*right[split].first;
        Complex ab=left[split].first*right[split].second;
        Complex ba=left[split].second*right[split].first;
        Complex bb=left[split].second*right[split].second;
        amp0+=aa+bb;
        amp1-=ab+ba;
        amp2+=Complex(0,1)*(ab-ba);
        amp3+=bb-aa;
    }
    return std::norm(amp1)+std::norm(amp2)+std::norm(amp3)-std::norm(amp0);
}
static Real evaluate(const Vec* momentum,const Real inv[5][5]) {
    Vec total[3][4],pol[3][2];
    for(int start=0;start<3;++start) {
        polarizations(momentum[2+start],pol[start]);
        total[start][start+1]=momentum[2+start];
        for(int end=start+2;end<=3;++end) total[start][end]=total[start][end-1]+momentum[1+end];
    }
    Spin endpoint[2]={spinor(momentum[0]),spinor(momentum[1])};
    Vec prefix[2][3],suffix[2][3];
    for(int quark=0;quark<2;++quark) {
        for(int end=1;end<=3;++end) {
            Real denominator=0;
            for(int start=0;start<end;++start) {
                denominator+=inv[quark][2+start];
                for(int next=start+1;next<end;++next) denominator+=inv[2+start][2+next];
            }
            prefix[quark][end-1]=(momentum[quark]+total[0][end])*(1/denominator);
        }
        for(int start=0;start<3;++start) {
            Real denominator=0;
            for(int end=start;end<3;++end) {
                denominator+=inv[quark][2+end];
                for(int next=end+1;next<3;++next) denominator+=inv[2+end][2+next];
            }
            suffix[quark][start]=(momentum[quark]+total[start][3])*(-1/denominator);
        }
    }
    Vec pair[2][2][2];
    for(int start=0;start<2;++start) {
        for(int first=0;first<2;++first) for(int second=0;second<2;++second)
            pair[start][first][second]=three(pol[start][first],pol[start+1][second],momentum[2+start],momentum[3+start])*(1/inv[2+start][3+start]);
    }
    Real inverse_triple=1/(inv[2][3]+inv[2][4]+inv[3][4]);
    Real result=0;
    for(int helicity=0;helicity<8;++helicity) {
        Vec current[3][4];
        for(int start=0;start<3;++start) current[start][start+1]=pol[start][(helicity>>start)&1];
        for(int start=0;start<2;++start)
            current[start][start+2]=pair[start][(helicity>>start)&1][(helicity>>(start+1))&1];
        Vec triple=three(current[0][1],current[1][3],total[0][1],total[1][3])+three(current[0][2],current[2][3],total[0][2],total[2][3]);
        triple=triple+current[1][2]*(2*dot(current[0][1],current[2][3]))-current[0][1]*dot(current[1][2],current[2][3])-current[2][3]*dot(current[0][1],current[1][2]);
        current[0][3]=triple*inverse_triple;
        result+=fermion(endpoint,current,prefix,suffix,0,1)+fermion(endpoint,current,prefix,suffix,1,0);
    }
    return result/8;
}
static void reconstruct(const double* input,Vec* momentum,Real inv[5][5]) {
    long double sij[5][5]={};
    int slot=0,anchor=0,other=1;
    for(int left=0;left<5;++left) for(int right=left+1;right<5;++right) {
        sij[left][right]=sij[right][left]=input[slot];
        inv[left][right]=inv[right][left]=input[slot++];
        if(sij[left][right]>sij[anchor][other]) {anchor=left;other=right;}
    }
    long double mass=sqrtl(sij[anchor][other]);
    momentum[anchor]={(Real)(mass/2),0,0,(Real)(mass/2)};
    momentum[other]={(Real)(mass/2),0,0,(Real)(-mass/2)};
    int rest[3],count=0;
    for(int idx=0;idx<5;++idx) if(idx!=anchor && idx!=other) rest[count++]=idx;
    long double radius[5]={},xx[5]={},yy[5]={};
    for(int idx:rest) radius[idx]=sij[anchor][idx]*sij[other][idx]/sij[anchor][other];
    if(radius[rest[1]]>radius[rest[0]]) std::swap(rest[0],rest[1]);
    if(radius[rest[2]]>radius[rest[0]]) std::swap(rest[0],rest[2]);
    int pivot=rest[0];
    xx[pivot]=sqrtl(radius[pivot]);
    for(int pos=1;pos<3;++pos) {
        int idx=rest[pos];
        xx[idx]=(sij[anchor][pivot]*sij[other][idx]+sij[other][pivot]*sij[anchor][idx]-sij[anchor][other]*sij[pivot][idx])/(2*sij[anchor][other]*xx[pivot]);
        yy[idx]=sqrtl(std::max(0.L,radius[idx]-xx[idx]*xx[idx]));
    }
    int first=rest[1],second=rest[2];
    long double transverse=(sij[anchor][first]*sij[other][second]+sij[other][first]*sij[anchor][second]-sij[anchor][other]*sij[first][second])/(2*sij[anchor][other]);
    if(transverse-xx[first]*xx[second]<0) yy[second]=-yy[second];
    for(int idx:rest) momentum[idx]={(Real)((sij[anchor][idx]+sij[other][idx])/(2*mass)),(Real)xx[idx],(Real)yy[idx],(Real)((sij[other][idx]-sij[anchor][idx])/(2*mass))};
}
extern "C" void predict(const double* invariants,double* output,int count) {
    for(int event=0;event<count;++event) {
        Vec momentum[5];Real inv[5][5]={};
        reconstruct(invariants+10*event,momentum,inv);
        output[event]=std::log(evaluate(momentum,inv));
    }
}
extern "C" void predict_p(const double* invariants,const double* points,double* output,int count) {
    for(int event=0;event<count;++event) {
        Vec momentum[5];Real inv[5][5]={};
        reconstruct(invariants+10*event,momentum,inv);
        for(int idx=0;idx<5;++idx) {
            const double* point=points+20*event+4*idx;
            momentum[idx]={point[3],point[0],point[1],point[2]};
        }
        output[event]=std::log(evaluate(momentum,inv));
    }
}
