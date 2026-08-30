#include <cmath>
#include <complex>
#include <algorithm>
#include <cstddef>

using Real = double;
using Complex = std::complex<Real>;
struct Vector {
    Real energy,px,py,pz;
    Vector operator+(const Vector& rhs) const {return {energy+rhs.energy,px+rhs.px,py+rhs.py,pz+rhs.pz};}
    Vector operator-(const Vector& rhs) const {return {energy-rhs.energy,px-rhs.px,py-rhs.py,pz-rhs.pz};}
    Vector operator*(Real scale) const {return {energy*scale,px*scale,py*scale,pz*scale};}
};
inline Real dot(Vector lhs,Vector rhs) {return lhs.energy*rhs.energy-lhs.px*rhs.px-lhs.py*rhs.py-lhs.pz*rhs.pz;}
struct Spinor {
    Complex first,second;
    Spinor operator+(const Spinor& rhs) const {return {first+rhs.first,second+rhs.second};}
    Spinor operator*(Real scale) const {return {first*scale,second*scale};}
};
inline Spinor row_b(Spinor row,Vector vec) {return {row.first*(vec.energy+vec.pz)+row.second*Complex(vec.px,vec.py),row.first*Complex(vec.px,-vec.py)+row.second*(vec.energy-vec.pz)};}
inline Spinor row_a(Spinor row,Vector vec) {return {row.first*(vec.energy-vec.pz)-row.second*Complex(vec.px,vec.py),-row.first*Complex(vec.px,-vec.py)+row.second*(vec.energy+vec.pz)};}
inline Spinor col_b(Vector vec,Spinor col) {return {(vec.energy+vec.pz)*col.first+Complex(vec.px,-vec.py)*col.second,Complex(vec.px,vec.py)*col.first+(vec.energy-vec.pz)*col.second};}
inline Spinor col_a(Vector vec,Spinor col) {return {(vec.energy-vec.pz)*col.first-Complex(vec.px,-vec.py)*col.second,-Complex(vec.px,vec.py)*col.first+(vec.energy+vec.pz)*col.second};}
inline Spinor external(Vector vec) {
    if(vec.pz>=0) {
        Real root=std::sqrt(vec.energy+vec.pz);
        return {-Complex(vec.px,-vec.py)/root,root};
    }
    Real root=std::sqrt(vec.energy-vec.pz);
    return {-root,Complex(vec.px,vec.py)/root};
}
inline Vector vertex(Vector lhs,Vector rhs,Vector pl,Vector pr) {
    return lhs*(2*dot(pl,rhs))-rhs*(2*dot(pr,lhs))-(pl-pr)*dot(lhs,rhs);
}
inline void polarization(Vector momentum,Vector* output) {
    Real norm=std::sqrt(momentum.px*momentum.px+momentum.py*momentum.py+momentum.pz*momentum.pz);
    Real nx=momentum.px/norm,ny=momentum.py/norm,nz=momentum.pz/norm;
    if(std::abs(nz)<0.8) {
        Real inv=1/std::sqrt(nx*nx+ny*ny);
        output[0]={0,ny*inv,-nx*inv,0};
    } else {
        Real inv=1/std::sqrt(nz*nz+ny*ny);
        output[0]={0,0,nz*inv,-ny*inv};
    }
    output[1]={0,ny*output[0].pz-nz*output[0].py,nz*output[0].px-nx*output[0].pz,nx*output[0].py-ny*output[0].px};
}
inline Real matrix_element(const Vector* currents,const Vector* leftmom,const Vector* rightmom,const Real* leftinv,const Real* rightinv,Spinor left,Spinor right) {
    Spinor lefts[4],rights[4];
    lefts[0]={std::conj(left.first),std::conj(left.second)};
    rights[3]=right;
    lefts[1]=row_a(row_b(lefts[0],currents[0]),leftmom[0])*leftinv[0];
    lefts[2]=row_a(row_b(lefts[0],currents[3])+row_b(lefts[1],currents[1]),leftmom[1])*leftinv[1];
    lefts[3]=row_a(row_b(lefts[0],currents[5])+row_b(lefts[1],currents[4])+row_b(lefts[2],currents[2]),leftmom[2])*leftinv[2];
    rights[2]=col_a(rightmom[2],col_b(currents[2],rights[3]))*(-rightinv[2]);
    rights[1]=col_a(rightmom[1],col_b(currents[4],rights[3])+col_b(currents[1],rights[2]))*(-rightinv[1]);
    rights[0]=col_a(rightmom[0],col_b(currents[5],rights[3])+col_b(currents[3],rights[2])+col_b(currents[0],rights[1]))*(-rightinv[0]);
    Complex aa=0,ab=0,ba=0,bb=0;
    for(int split=0;split<4;++split) {
        aa+=lefts[split].first*rights[split].first;
        ab+=lefts[split].first*rights[split].second;
        ba+=lefts[split].second*rights[split].first;
        bb+=lefts[split].second*rights[split].second;
    }
    return 2*(std::norm(ab)+std::norm(ba))-4*std::real(aa*std::conj(bb));
}

inline Real evaluate(const double* source, const Vector* particles) {
    Real invariant[5][5]{};
    int offset=0;
    for(int first=0;first<5;++first) for(int second=first+1;second<5;++second) invariant[first][second]=invariant[second][first]=source[offset++];
    Vector pol[3][2];
    for(int gluon=0;gluon<3;++gluon) polarization(particles[gluon+2],pol[gluon]);
    Vector leftmom[2][3],rightmom[2][3];
    Real leftinv[2][3],rightinv[2][3];
    Spinor ext[2]={external(particles[0]),external(particles[1])};
    for(int order=0;order<2;++order) {
        leftmom[order][0]=particles[order]+particles[2];
        leftmom[order][1]=leftmom[order][0]+particles[3];
        leftmom[order][2]=leftmom[order][1]+particles[4];
        rightmom[order][2]=particles[1-order]+particles[4];
        rightmom[order][1]=rightmom[order][2]+particles[3];
        rightmom[order][0]=rightmom[order][1]+particles[2];
        leftinv[order][0]=1/invariant[order][2];
        leftinv[order][1]=1/(invariant[order][2]+invariant[order][3]+invariant[2][3]);
        leftinv[order][2]=1/(invariant[order][2]+invariant[order][3]+invariant[order][4]+invariant[2][3]+invariant[2][4]+invariant[3][4]);
        rightinv[order][2]=1/invariant[1-order][4];
        rightinv[order][1]=1/(invariant[1-order][4]+invariant[1-order][3]+invariant[3][4]);
        rightinv[order][0]=1/(invariant[1-order][2]+invariant[1-order][3]+invariant[1-order][4]+invariant[2][3]+invariant[2][4]+invariant[3][4]);
    }
    Real inv34=1/source[7], inv45=1/source[9], inv345=1/(source[7]+source[8]+source[9]);
    Real result=0;
    for(int state=0;state<8;++state) {
        Vector currents[6]={pol[0][state&1],pol[1][(state>>1)&1],pol[2][(state>>2)&1]};
        currents[3]=vertex(currents[0],currents[1],particles[2],particles[3])*inv34;
        currents[4]=vertex(currents[1],currents[2],particles[3],particles[4])*inv45;
        currents[5]=(vertex(currents[0],currents[4],particles[2],particles[3]+particles[4])+vertex(currents[3],currents[2],particles[2]+particles[3],particles[4])+currents[1]*(2*dot(currents[0],currents[2]))-currents[0]*dot(currents[1],currents[2])-currents[2]*dot(currents[0],currents[1]))*inv345;
        for(int order=0;order<2;++order) result+=matrix_element(currents,leftmom[order],rightmom[order],leftinv[order],rightinv[order],ext[order],ext[1-order]);
    }
    return std::log(result/8);
}

inline void reconstruct(const double* source,Vector* particles) {
    long double invariant[5][5]{};
    int anchor_a=0,anchor_b=1,offset=0;
    for(int first=0;first<5;++first) for(int second=first+1;second<5;++second) {
        invariant[first][second]=invariant[second][first]=source[offset++];
        if(invariant[first][second]>invariant[anchor_a][anchor_b]) {anchor_a=first;anchor_b=second;}
    }
    long double mass=std::sqrt(invariant[anchor_a][anchor_b]);
    long double energy[5]{},longitudinal[5]{},transverse[5]{},coordx[5]{},coordy[5]{};
    energy[anchor_a]=energy[anchor_b]=mass/2;
    longitudinal[anchor_a]=mass/2; longitudinal[anchor_b]=-mass/2;
    int anchor_c=-1;
    for(int idx=0;idx<5;++idx) if(idx!=anchor_a && idx!=anchor_b) {
        energy[idx]=(invariant[anchor_a][idx]+invariant[anchor_b][idx])/(2*mass);
        longitudinal[idx]=(invariant[anchor_b][idx]-invariant[anchor_a][idx])/(2*mass);
        transverse[idx]=invariant[anchor_a][idx]*invariant[anchor_b][idx]/invariant[anchor_a][anchor_b];
        if(anchor_c<0 || transverse[idx]/(energy[idx]*energy[idx])>transverse[anchor_c]/(energy[anchor_c]*energy[anchor_c])) anchor_c=idx;
    }
    coordx[anchor_c]=std::sqrt(transverse[anchor_c]);
    int anchor_d=-1,anchor_e=-1;
    long double max_ysq=-1,max_score=-1;
    for(int idx=0;idx<5;++idx) if(idx!=anchor_a && idx!=anchor_b && idx!=anchor_c) {
        coordx[idx]=((invariant[anchor_a][anchor_c]*invariant[anchor_b][idx]+invariant[anchor_b][anchor_c]*invariant[anchor_a][idx])/invariant[anchor_a][anchor_b]-invariant[anchor_c][idx])/(2*coordx[anchor_c]);
        long double ysq=transverse[idx]-coordx[idx]*coordx[idx];
        long double score=ysq/(energy[idx]*energy[idx]);
        if(score>max_score) {anchor_e=anchor_d;anchor_d=idx;max_ysq=ysq;max_score=score;} else anchor_e=idx;
    }
    if(max_score>1e-28L) {
        coordy[anchor_d]=std::sqrt(max_ysq);
        coordy[anchor_e]=(((invariant[anchor_a][anchor_d]*invariant[anchor_b][anchor_e]+invariant[anchor_b][anchor_d]*invariant[anchor_a][anchor_e])/invariant[anchor_a][anchor_b]-invariant[anchor_d][anchor_e])/2-coordx[anchor_d]*coordx[anchor_e])/coordy[anchor_d];
    }
    for(int idx=0;idx<5;++idx) particles[idx]={(Real)energy[idx],(Real)coordx[idx],(Real)coordy[idx],(Real)longitudinal[idx]};
}

extern "C" void predict(std::size_t count,const double* invariants,const double* momenta,double* output,int use_momenta) {
    for(std::size_t event=0;event<count;++event) {
        Vector particles[5];
        if(use_momenta) for(int idx=0;idx<5;++idx) {const double* ptr=momenta+event*20+idx*4;particles[idx]={ptr[3],ptr[0],ptr[1],ptr[2]};}
        else reconstruct(invariants+event*10,particles);
        output[event]=evaluate(invariants+event*10,particles);
    }
}
