#include <complex>
#include <vector>
#include <cmath>
#include <cstring>
using C=std::complex<double>;struct Gate{int kind,q,t;};static int N,L,P;static std::vector<Gate>gs;static std::vector<C>T,fs,b,b2,mats;
void mul1(const C*s,C*d,int q,const C*a){int h=1<<q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int k=0;k<N;++k){C x=s[i0+k],y=s[i1+k];d[i0+k]=a[0]*x+a[1]*y;d[i1+k]=a[2]*x+a[3]*y;}}}
void cx(const C*s,C*d,int q,int t){for(int i=0;i<N;++i){int j=i^(((i>>q)&1)<<t);memcpy(d+j*N,s+i*N,N*sizeof(C));}}
extern "C" {
void setup(int n,int l,const int*sp,const C*tt){N=1<<n;L=l;P=0;gs.clear();for(int i=0;i<L;++i){gs.push_back({sp[3*i],sp[3*i+1],sp[3*i+2]});if(!sp[3*i])P+=8;}T.assign(tt,tt+N*N);fs.resize((size_t)(L+1)*N*N);b.resize(N*N);b2.resize(N*N);mats.resize(4*L);}
double calc(const double*x,double*grad,double lam){int D=N*N;std::fill(fs.begin(),fs.begin()+D,C(0));for(int i=0;i<N;++i)fs[i*N+i]=1.;int p=0;double pen=0;for(int k=0;k<L;++k){auto g=gs[k];if(g.kind)cx(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,g.t);else{for(int j=0;j<4;++j)mats[4*k+j]=C(x[p+2*j],x[p+2*j+1]);p+=8;mul1(fs.data()+(size_t)k*D,fs.data()+(size_t)(k+1)*D,g.q,mats.data()+4*k);}}
double f=0;for(int i=0;i<D;++i){b[i]=fs[(size_t)L*D+i]-T[i];f+=std::norm(b[i])/N;}
for(int k=L-1;k>=0;--k){auto g=gs[k];if(g.kind){cx(b.data(),b2.data(),g.q,g.t);b.swap(b2);}else{p-=8;C e[4]={};C*G=mats.data()+4*k;const C* F=fs.data()+(size_t)k*D;int h=1<<g.q;for(int base=0;base<N;base+=2*h)for(int j=0;j<h;++j){int i0=(base+j)*N,i1=i0+h*N;for(int t=0;t<N;++t){C x=F[i0+t],y=F[i1+t],u=std::conj(b[i0+t]),v=std::conj(b[i1+t]);e[0]+=u*x;e[1]+=u*y;e[2]+=v*x;e[3]+=v*y;}}
C Cc[4]={};for(int a=0;a<2;++a)for(int z=0;z<2;++z){for(int j=0;j<2;++j)Cc[a*2+z]+=std::conj(G[j*2+a])*G[j*2+z];if(a==z)Cc[a*2+z]-=1.;pen+=std::norm(Cc[a*2+z]);}
for(int j=0;j<4;++j){C pp=0;for(int z=0;z<2;++z)pp+=G[2*(j/2)+z]*Cc[2*z+j%2];grad[p+2*j]=2.*std::real(e[j])/N+4*lam*std::real(pp);grad[p+2*j+1]=-2.*std::imag(e[j])/N+4*lam*std::imag(pp);}
C A[4]={std::conj(G[0]),std::conj(G[2]),std::conj(G[1]),std::conj(G[3])};mul1(b.data(),b2.data(),g.q,A);b.swap(b2);}}
return f+lam*pen;}
}
