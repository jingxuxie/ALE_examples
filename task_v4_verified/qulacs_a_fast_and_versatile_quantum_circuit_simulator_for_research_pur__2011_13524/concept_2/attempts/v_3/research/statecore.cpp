#include <complex>
#include <vector>
#include <cmath>
#include <cstring>
using C=std::complex<double>;
struct Gate{int kind,q,t;};static int N,K,L,P;static std::vector<Gate> gs;static std::vector<C> S,T,fs,b,b2,mats,ders;
static void mul1(const C*src,C*dst,int q,const C*a){int h=1<<q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*K,i1=i0+h*K;for(int k=0;k<K;++k){C x=src[i0+k],y=src[i1+k];dst[i0+k]=a[0]*x+a[1]*y;dst[i1+k]=a[2]*x+a[3]*y;}}}
static void cx(const C*src,C*dst,int q,int t){for(int i=0;i<N;++i){int j=i^(((i>>q)&1)<<t);memcpy(dst+j*K,src+i*K,K*sizeof(C));}}
static void u3(const double*x,C*a,C*der){double c=cos(x[0]/2),s=sin(x[0]/2);C ep=std::exp(C(0,x[1])),el=std::exp(C(0,x[2]));a[0]=c;a[1]=-el*s;a[2]=ep*s;a[3]=ep*el*c;der[0]=-.5*s;der[1]=-.5*el*c;der[2]=.5*ep*c;der[3]=-.5*ep*el*s;der[4]=0.;der[5]=0.;der[6]=C(0,1)*a[2];der[7]=C(0,1)*a[3];der[8]=0.;der[9]=C(0,1)*a[1];der[10]=0.;der[11]=C(0,1)*a[3];}
extern "C" {
void setup(int n,int k,int l,const int*spec,const C*ss,const C*tt){N=1<<n;K=k;L=l;P=0;gs.clear();for(int i=0;i<L;++i){gs.push_back({spec[3*i],spec[3*i+1],spec[3*i+2]});if(!spec[3*i])P+=3;}S.assign(ss,ss+N*K);T.assign(tt,tt+N*K);fs.resize((size_t)(L+1)*N*K);b.resize(N*K);b2.resize(N*K);mats.resize(4*L);ders.resize(12*L);}
double calc(const double*x,double*grad,int mode){int D=N*K;std::copy(S.begin(),S.end(),fs.begin());int p=0;for(int j=0;j<L;++j){auto g=gs[j];if(g.kind)cx(fs.data()+(size_t)j*D,fs.data()+(size_t)(j+1)*D,g.q,g.t);else{u3(x+p,mats.data()+4*j,ders.data()+12*j);p+=3;mul1(fs.data()+(size_t)j*D,fs.data()+(size_t)(j+1)*D,g.q,mats.data()+4*j);}}
std::vector<C> z(K,C(0));for(int i=0;i<D;++i)z[i%K]+=std::conj(T[i])*fs[(size_t)L*D+i];double f=1.;if(!mode){C zz=0.;for(C a:z)zz+=a;zz/=K;for(C&a:z)a=zz;f-=std::norm(zz);}else for(C a:z)f-=std::norm(a)/K;for(int i=0;i<D;++i)b[i]=T[i]*z[i%K];
for(int j=L-1;j>=0;--j){auto g=gs[j];if(g.kind){cx(b.data(),b2.data(),g.q,g.t);b.swap(b2);}else{p-=3;C e[4]={};const C* f0=fs.data()+(size_t)j*D;int h=1<<g.q;for(int base=0;base<N;base+=2*h)for(int a=0;a<h;++a){int i0=(base+a)*K,i1=i0+h*K;for(int t=0;t<K;++t){C x=f0[i0+t],y=f0[i1+t],u=std::conj(b[i0+t]),v=std::conj(b[i1+t]);e[0]+=u*x;e[1]+=u*y;e[2]+=v*x;e[3]+=v*y;}}
for(int a=0;a<3;++a){C dz=0.;for(int t=0;t<4;++t)dz+=e[t]*ders[12*j+4*a+t];grad[p+a]=-2.*std::real(dz)/K;}C a[4]={std::conj(mats[4*j]),std::conj(mats[4*j+2]),std::conj(mats[4*j+1]),std::conj(mats[4*j+3])};mul1(b.data(),b2.data(),g.q,a);b.swap(b2);}}
return f;}
}
