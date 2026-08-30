#include <complex>
#include <vector>
#include <cmath>
#include <algorithm>
using C=std::complex<double>;
static void local(int d,int q,const C *a,C *v){
 int s=1<<q;
 for(int i=0;i<d;i++) if(!(i&s)) for(int j=0;j<d;j++){
  C v0=v[i*d+j],v1=v[(i+s)*d+j];
  v[i*d+j]=a[0]*v0+a[1]*v1; v[(i+s)*d+j]=a[2]*v0+a[3]*v1;
 }
}
static void cnot(int d,int c,int t,C *v){
 int cs=1<<c,ts=1<<t;
 for(int i=0;i<d;i++)if((i&cs)&&!(i&ts))for(int j=0;j<d;j++)std::swap(v[i*d+j],v[(i+ts)*d+j]);
}
static void u3(const double *p,C *a,C *der){
 double c=cos(p[0]/2),s=sin(p[0]/2);C ep=std::polar(1.,p[1]),el=std::polar(1.,p[2]),epl=ep*el,I(0,1);
 a[0]=c;a[1]=-el*s;a[2]=ep*s;a[3]=epl*c;
 if(der){
 der[0]=-.5*s;der[1]=-.5*el*c;der[2]=.5*ep*c;der[3]=-.5*epl*s;
 der[4]=0;der[5]=0;der[6]=I*a[2];der[7]=I*a[3];
 der[8]=0;der[9]=I*a[1];der[10]=0;der[11]=I*a[3];
 }
}
extern "C" double evaluate(int n,int ng,const int* qubits,const int* ctrls,const double* pars,const C *target,double* grad,C *out){
 int d=1<<n,dd=d*d;
 std::vector<C> fs((ng+1)*dd,C(0)),gates(ng*4),b(target,target+dd);
 C *v=fs.data();for(int i=0;i<d;i++)v[i*d+i]=1.;
 int p=0;
 for(int k=0;k<ng;k++){
  std::copy(v,v+dd,v+dd);v+=dd;
  if(ctrls[k]<0){u3(pars+p,&gates[4*k],nullptr);local(d,qubits[k],&gates[4*k],v);p+=3;}
  else cnot(d,ctrls[k],qubits[k],v);
 }
 if(out)std::copy(v,v+dd,out);
 C ov=0.;for(int j=0;j<dd;j++)ov+=std::conj(target[j])*v[j];ov/=(double)d;
 if(!grad)return 1.-std::norm(ov);
 for(int k=ng-1;k>=0;k--){
  const C *f=&fs[k*dd];
  if(ctrls[k]>=0){cnot(d,ctrls[k],qubits[k],b.data());continue;}
  p-=3;C a[4],der[12];u3(pars+p,a,der);C vals[3]={0.,0.,0.};int s=1<<qubits[k];
  // Form the 2x2 local environment first, then contract the derivatives.
  C e[4]={0.,0.,0.,0.};
  for(int i=0;i<d;i++)if(!(i&s))for(int j=0;j<d;j++){
   C b0=std::conj(b[i*d+j]),b1=std::conj(b[(i+s)*d+j]);C f0=f[i*d+j],f1=f[(i+s)*d+j];
   e[0]+=b0*f0;e[1]+=b0*f1;e[2]+=b1*f0;e[3]+=b1*f1;
  }
  for(int z=0;z<3;z++){
   for(int j=0;j<4;j++)vals[z]+=e[j]*der[4*z+j];
   grad[p+z]=-2.*std::real(std::conj(ov)*vals[z])/(double)d;
  }
  C ah[4]={std::conj(a[0]),std::conj(a[2]),std::conj(a[1]),std::conj(a[3])};local(d,qubits[k],ah,b.data());
 }
 return 1.-std::norm(ov);
}
