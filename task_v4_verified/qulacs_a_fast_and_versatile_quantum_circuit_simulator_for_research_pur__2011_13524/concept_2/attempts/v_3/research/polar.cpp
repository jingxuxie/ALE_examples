#include <complex>
#include <vector>
#include <cstring>
using C=std::complex<double>;
static int N,M,D;static std::vector<int> qs;static std::vector<C> bs,F,F2,T,gg;
void apply(const C* in,C* out,int q,const C* G){int h=1<<q;for(int block=0;block<N;block+=4*h)for(int j=0;j<h;++j){int ids[4]={(block+j)*N,(block+j+h)*N,(block+j+2*h)*N,(block+j+3*h)*N};for(int k=0;k<N;++k){C x[4]={in[ids[0]+k],in[ids[1]+k],in[ids[2]+k],in[ids[3]+k]};for(int a=0;a<4;++a){C z=0.;for(int b=0;b<4;++b)z+=G[a*4+b]*x[b];out[ids[a]+k]=z;}}}}
extern "C" {
void setup(int n,int m,const int* q,const C* t,const C* g){N=1<<n;M=m;D=N*N;qs.assign(q,q+m);T.assign(t,t+D);gg.assign(g,g+16*m);bs.resize((size_t)(m+1)*D);F.resize(D);F2.resize(D);}
void prepare(){std::copy(T.begin(),T.end(),bs.begin()+(size_t)M*D);for(int j=M-1;j>=0;--j){C G[16];for(int a=0;a<4;++a)for(int b=0;b<4;++b)G[a*4+b]=std::conj(gg[16*j+b*4+a]);apply(bs.data()+(size_t)(j+1)*D,bs.data()+(size_t)j*D,qs[j],G);}std::fill(F.begin(),F.end(),C(0));for(int a=0;a<N;++a)F[a*N+a]=1.;}
void env(int j,C* H){std::fill(H,H+16,C(0));C* B=bs.data()+(size_t)(j+1)*D;int h=1<<qs[j];for(int block=0;block<N;block+=4*h)for(int a=0;a<h;++a){int ids[4]={(block+a)*N,(block+a+h)*N,(block+a+2*h)*N,(block+a+3*h)*N};for(int k=0;k<N;++k)for(int r=0;r<4;++r)for(int c=0;c<4;++c)H[r*4+c]+=B[ids[r]+k]*std::conj(F[ids[c]+k]);}}
void update(int j,const C* G){memcpy(gg.data()+16*j,G,16*sizeof(C));apply(F.data(),F2.data(),qs[j],G);F.swap(F2);}
double loss(){C z=0.;for(int k=0;k<D;++k)z+=std::conj(T[k])*F[k];return 1.-std::norm(z/double(N));}
void getg(C* G){memcpy(G,gg.data(),16*M*sizeof(C));}
}
