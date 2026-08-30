#include <complex>
#include <cmath>
#include <algorithm>
using C=std::complex<double>;
extern "C" double testseed(int n,int m,const int* edges,const double* x,int mode,int dirs,const C* target){const int N=1<<n;C v[256]={};v[0]=1.;int p=0;
auto gate=[&](int q){double a=x[p++],bb=x[p++],cc=x[p++];double th,ph,la;double pi=3.14159265358979323846;th=2*pi*a;ph=2*pi*bb;la=2*pi*cc;if(mode==1){th-=pi;ph-=pi;la-=pi;}if(mode==2||mode==3){th=pi*a;if(mode==3){ph-=pi;la-=pi;}}if(mode==4||mode==5){th=2*acos(sqrt(a));if(mode==5){ph-=pi;la-=pi;}}if(mode==6){th=2*asin(sqrt(a));}if(mode==7){th=2*pi*a-pi;ph-=pi;la-=pi;std::swap(ph,la);}C c=cos(th/2),s=sin(th/2),ep=std::exp(C(0,ph)),el=std::exp(C(0,la));int h=1<<q;for(int i=0;i<N;++i)if(!(i&h)){C xx=v[i],yy=v[i+h];v[i]=c*xx-el*s*yy;v[i+h]=ep*s*xx+ep*el*c*yy;}};
for(int q=0;q<n;++q)gate(q);for(int k=0;k<m;++k){int a=edges[2*k],b=edges[2*k+1];bool flip=dirs==1 || (dirs==2&&k%2) || (dirs==3&&(k/(n-1))%2) || (dirs==4&&a%2);if(flip)std::swap(a,b);int ha=1<<a,hb=1<<b;for(int j=0;j<N;++j)if((j&ha)&&!(j&hb))std::swap(v[j],v[j+hb]);gate(edges[2*k]);gate(edges[2*k+1]);}
C z=0;for(int i=0;i<N;++i)z+=std::conj(target[i])*v[i];return std::norm(z);}
