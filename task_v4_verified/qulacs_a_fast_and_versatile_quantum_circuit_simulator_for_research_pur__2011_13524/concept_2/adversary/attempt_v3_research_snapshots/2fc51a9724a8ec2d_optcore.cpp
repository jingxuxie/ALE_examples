#include <complex>
#include <vector>
#include <cmath>
#include <cstring>
using C=std::complex<double>;
struct Gate{int kind, q, t;};
static int N,L,P;static std::vector<Gate> gs;static std::vector<C> target,fs,b,b2;static std::vector<C> mats,ders;
static void mul1(const C* src,C* dst,int q,const C* a){int h=1<<q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int k=0;k<N;++k){C x=src[i0+k],y=src[i1+k];dst[i0+k]=a[0]*x+a[1]*y;dst[i1+k]=a[2]*x+a[3]*y;}}}
static void cx(const C* src,C* dst,int q,int t){for(int i=0;i<N;++i){int j=i^(((i>>q)&1)<<t);memcpy(dst+j*N,src+i*N,N*sizeof(C));}}
static void u3(const double* x,C* a,C* der){double c=cos(x[0]/2),s=sin(x[0]/2);C ep=std::exp(C(0,x[1])),el=std::exp(C(0,x[2]));a[0]=c;a[1]=-el*s;a[2]=ep*s;a[3]=ep*el*c;
if(der){der[0]=-.5*s;der[1]=-.5*el*c;der[2]=.5*ep*c;der[3]=-.5*ep*el*s;der[4]=0.;der[5]=0.;der[6]=C(0,1)*a[2];der[7]=C(0,1)*a[3];der[8]=0.;der[9]=C(0,1)*a[1];der[10]=0.;der[11]=C(0,1)*a[3];}}
extern "C" {
void setup(int n,int l,const int* spec,const C* T){N=1<<n;L=l;P=0;gs.clear();for(int i=0;i<L;++i){gs.push_back({spec[3*i],spec[3*i+1],spec[3*i+2]});if(!spec[3*i])P+=3;}target.assign(T,T+N*N);fs.resize((size_t)(L+1)*N*N);b.resize(N*N);b2.resize(N*N);mats.resize(4*L);ders.resize(12*L);}
double calc(const double* x,double* grad){int D=N*N;std::fill(fs.begin(),fs.begin()+D,C(0));for(int i=0;i<N;++i)fs[i*N+i]=1.;int p=0;
for(int k=0;k<L;++k){auto g=gs[k];if(g.kind)cx(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,g.t);else{u3(x+p,mats.data()+4*k,ders.data()+12*k);p+=3;mul1(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,mats.data()+4*k);}}
C z=0.;for(int i=0;i<D;++i)z+=std::conj(target[i])*fs[(size_t)L*D+i];z/=N;double f=1.-std::norm(z);if(!grad)return f;
b=target;
for(int k=L-1;k>=0;--k){auto g=gs[k];if(g.kind){cx(b.data(),b2.data(),g.q,g.t);b.swap(b2);}else{p-=3;C e[4]={0.,0.,0.,0.};const C* f0=fs.data()+(size_t)k*D;int h=1<<g.q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int t=0;t<N;++t){C x=f0[i0+t],y=f0[i1+t],u=std::conj(b[i0+t]),v=std::conj(b[i1+t]);e[0]+=u*x;e[1]+=u*y;e[2]+=v*x;e[3]+=v*y;}}
for(int j=0;j<3;++j){C dz=0.;for(int t=0;t<4;++t)dz+=e[t]*ders[12*k+4*j+t];grad[p+j]=-2.*std::real(std::conj(z)*dz)/N;}
C a[4]={std::conj(mats[4*k]),std::conj(mats[4*k+2]),std::conj(mats[4*k+1]),std::conj(mats[4*k+3])};mul1(b.data(),b2.data(),g.q,a);b.swap(b2);}}
return f;}
double localcalc(const double* x,double* grad,int mode){int D=N*N;std::copy(target.begin(),target.end(),fs.begin());int p=0;
for(int k=0;k<L;++k){auto g=gs[k];if(g.kind)cx(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,g.t);else{u3(x+p,mats.data()+4*k,ders.data()+12*k);p+=3;mul1(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,mats.data()+4*k);}}
C* w=fs.data()+(size_t)L*D;std::fill(b.begin(),b.end(),C(0));double score=0;int nq=0;for(int h=1;h<N;h*=2){nq++;
if(mode==0){for(int r=0;r<N;r++)if(!(r&h))for(int c=0;c<N;c++)if(!(c&h)){C z=.5*(w[r*N+c]+w[(r+h)*N+c+h]);score+=2.*std::norm(z)/N;b[r*N+c]+=z;b[(r+h)*N+c+h]+=z;}}
else{C rho[16]={};for(int r=0;r<N;r++)if(!(r&h))for(int c=0;c<N;c++)if(!(c&h)){C v[4]={w[r*N+c],w[r*N+c+h],w[(r+h)*N+c],w[(r+h)*N+c+h]};for(int a=0;a<4;++a)for(int z=0;z<4;++z)rho[a*4+z]+=v[a]*std::conj(v[z])/double(N);}
for(int a=0;a<16;++a)score+=std::norm(rho[a]);
for(int r=0;r<N;r++)if(!(r&h))for(int c=0;c<N;c++)if(!(c&h)){int ids[4]={r*N+c,r*N+c+h,(r+h)*N+c,(r+h)*N+c+h};for(int a=0;a<4;++a)for(int z=0;z<4;++z)b[ids[a]]+=2.*rho[a*4+z]*w[ids[z]];}
}}
for(int a=0;a<D;++a)b[a]/=nq;
for(int k=L-1;k>=0;--k){auto g=gs[k];if(g.kind){cx(b.data(),b2.data(),g.q,g.t);b.swap(b2);}else{p-=3;C e[4]={0.,0.,0.,0.};const C* f0=fs.data()+(size_t)k*D;int h=1<<g.q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int t=0;t<N;++t){C x=f0[i0+t],y=f0[i1+t],u=std::conj(b[i0+t]),v=std::conj(b[i1+t]);e[0]+=u*x;e[1]+=u*y;e[2]+=v*x;e[3]+=v*y;}}
for(int j=0;j<3;++j){C dz=0.;for(int t=0;t<4;++t)dz+=e[t]*ders[12*k+4*j+t];grad[p+j]=-2.*std::real(dz)/N;}
C a[4]={std::conj(mats[4*k]),std::conj(mats[4*k+2]),std::conj(mats[4*k+1]),std::conj(mats[4*k+3])};mul1(b.data(),b2.data(),g.q,a);b.swap(b2);}}
return 1.-score/nq;}
void backprop(const C* B,double* grad){int D=N*N;int p=P;std::copy(B,B+D,b.begin());for(int k=L-1;k>=0;--k){auto g=gs[k];if(g.kind){cx(b.data(),b2.data(),g.q,g.t);b.swap(b2);}else{p-=3;C e[4]={0.,0.,0.,0.};const C* f0=fs.data()+(size_t)k*D;int h=1<<g.q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int t=0;t<N;++t){C x=f0[i0+t],y=f0[i1+t],u=std::conj(b[i0+t]),v=std::conj(b[i1+t]);e[0]+=u*x;e[1]+=u*y;e[2]+=v*x;e[3]+=v*y;}}
for(int j=0;j<3;++j){C dz=0.;for(int t=0;t<4;++t)dz+=e[t]*ders[12*k+4*j+t];grad[p+j]=-2.*std::real(dz)/N;}
C a[4]={std::conj(mats[4*k]),std::conj(mats[4*k+2]),std::conj(mats[4*k+1]),std::conj(mats[4*k+3])};mul1(b.data(),b2.data(),g.q,a);b.swap(b2);}}
}
void forward_on(const double* x,const C* init,C* V){int D=N*N;std::copy(init,init+D,fs.begin());int p=0;
for(int k=0;k<L;++k){auto g=gs[k];if(g.kind)cx(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,g.t);else{u3(x+p,mats.data()+4*k,ders.data()+12*k);p+=3;mul1(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,mats.data()+4*k);}}
memcpy(V,fs.data()+(size_t)L*D,D*sizeof(C));}
void matrix(const double* x,C* V){calc(x,nullptr);memcpy(V,fs.data()+(size_t)L*N*N,N*N*sizeof(C));}
}
