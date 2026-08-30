"""Sequential Bayesian design and estimation for the disclosed Ramsey model.

All model information is obtained from the public simulator and protocol.
The strategy keeps no cross-episode state and performs no file or network I/O.
"""
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, logsumexp
from simulator import (BOUNDS, SCALES, MODES, probabilities, encode_actions,
                       parameter_dict, predictive_grid)


def find_peaks(y, distance=1):
    """Local maxima with distance suppression; avoids importing signal processing."""
    peaks=np.flatnonzero((y[1:-1]>y[:-2]) & (y[1:-1]>y[2:]))+1
    accepted=[]
    for k in peaks[np.argsort(y[peaks])[::-1]]:
        if all(abs(k-j)>=distance for j in accepted):
            accepted.append(int(k))
    return np.array(sorted(accepted),dtype=int), {}

TWOPI = 2 * np.pi
OPT_SCALE = np.array([.02,.02,.02,.07,.07,.3,.07,.07,.05,.05])
PRIOR_BOUNDS = [
    np.array([[.35,2.05],[.35,2.05],[.025,.16],[.10,.28],[.10,.28],[-.65,.65],[.78,.90],[.78,.90],[-.06,.06],[-.06,.06]]),
    np.array([[.45,1.90],[.475,2.00],[.10,.20],[.16,.34],[.16,.34],[-.85,.85],[.68,.88],[.68,.88],[-.08,.08],[-.08,.08]]),
    np.array([[.35,2.05],[.35,2.05],[.025,.20],[.24,.44],[.24,.44],[-.85,.85],[.50,.68],[.50,.68],[-.085,.085],[-.085,.085]])]
GRID = encode_actions(predictive_grid())


def experiment(mode, t, phase, shots):
    return {'type':'experiment', 'mode':MODES[mode], 'time':float(t),
            'phase':float((phase+np.pi) % TWOPI - np.pi), 'shots':int(shots)}


def batch_prob(theta, enc):
    # Population by experiment array, without Python loops over particles.
    m,t,phase=enc
    f1,f2,j,s1,s2,r,v1,v2,b1,b2=theta.T
    f=np.array([f1+j,f1-j,f2+j,f2-j,f1+f2,f1-f2]).T[:,m]
    d=np.array([s1*s1,s1*s1,s2*s2,s2*s2,s1*s1+s2*s2+2*r*s1*s2,s1*s1+s2*s2-2*r*s1*s2]).T[:,m]
    v=np.array([v1,v1,v2,v2,v1*v2,v1*v2]).T[:,m]
    b=np.array([b1,b1,b2,b2,b1*b2,b1*b2]).T[:,m]
    return np.clip(.5*(1+b+v*np.exp(-.5*d*t*t)*np.cos(TWOPI*f*t-phase)),1e-10,1-1e-10)


class Base:
    def __init__(self):
        self.history=[]
        self.rng=np.random.default_rng(172934)
        self.initial=[]
        for m in [0,2]:
            for phase in [0,np.pi]:
                self.initial.append(experiment(m,0,phase,80))
        for t in [.31,.83,2.13]:
            for m in [0,2]:
                for phase in [0,np.pi/2]:
                    self.initial.append(experiment(m,t,phase,64))
        self.theta=np.array([1.,1.5,.12,.25,.25,0.,.75,.75,0.,0.])
        self.family=None
        self.cov=None
        self.spent=0
        self.diag={}

    def data(self):
        enc=encode_actions([h['action'] for h in self.history])
        k=np.array([h['counts'][0] for h in self.history])
        n=np.array([sum(h['counts']) for h in self.history])
        return enc,k,n

    def initial_fit(self):
        enc,k,n=self.data()
        m,t,ph=enc
        vals=[]
        self.freq_alts=[]
        self.freq_confidence=[]
        for sensor in range(2):
            ix=m==2*sensor
            tt,pp,kk,nn=t[ix],ph[ix],k[ix],n[ix]
            freq=np.linspace(.26,2.36,1401)
            # Accurate global frequency search after estimating zero-time SPAM.
            v=np.clip((kk[0]/nn[0]-kk[1]/nn[1]),.48,.9)
            b=np.clip((kk[0]/nn[0]+kk[1]/nn[1]-1),-.09,.09)
            p=.5*(1+b+v*np.exp(-.5*.27**2*tt*tt)*np.cos(TWOPI*freq[:,None]*tt-pp))
            cost=-(np.log(p)@kk+np.log1p(-p)@(nn-kk))
            peaks=find_peaks(-cost,distance=30)[0]
            inds=np.unique(np.r_[peaks,0,len(freq)-1,np.argmin(cost)])
            inds=inds[np.argsort(cost[inds])[:8]]
            scale=np.array([.02,.07,.07,.05])
            def obj(z):
                f,s,v,b=z*scale
                arg=TWOPI*f*tt-pp
                e=np.exp(-.5*s*s*tt*tt)
                c=e*np.cos(arg)
                pr=np.clip(.5*(1+b+v*c),1e-10,1-1e-10)
                grad=np.array([-np.pi*v*e*np.sin(arg)*tt,-.5*v*c*s*tt*tt,.5*c,np.full(len(tt),.5)]).T
                residual=(nn*pr-kk)/(pr*(1-pr))
                loss=-(kk*np.log(pr)+(nn-kk)*np.log1p(-pr)).sum()
                # Mild stabilization only, not a restrictive family guess.
                loss+=.5*((s-.27)/.20)**2+.5*(b/.08)**2
                g=grad.T@residual+np.array([0,(s-.27)/.20**2,0,b/.08**2])
                return loss,g*scale
            best=None
            fitted=[]
            for ind in inds:
                result=minimize(obj,np.array([freq[ind],.27,v,b])/scale,jac=True,method='L-BFGS-B',
                    bounds=np.array([[.26,2.36],[.08,.46],[.48,.90],[-.09,.09]])/scale[:,None],
                    options={'maxiter':130,'ftol':1e-11,'gtol':1e-6})
                fitted.append((float(result.fun),result.x*scale))
                if best is None or result.fun<best[0]:
                    best=(result.fun,result.x*scale)
            vals.append(best[1])
            alternatives=[z for z in fitted if abs(z[1][0]-best[1][0])>.08]
            self.freq_alts.append([best]+alternatives)
            self.freq_confidence.append(min([z[0]-best[0] for z in alternatives]+[1000.]))
        a,b=vals
        self.theta=np.array([a[0]-.12,b[0]-.12,.12,a[1],b[1],0,a[2],b[2],a[3],b[3]])
        self.theta=np.clip(self.theta,BOUNDS[:,0]+1e-8,BOUNDS[:,1]-1e-8)
        self.plus=np.array([a[0],b[0]])

    def choose_family(self, theta):
        if -.005 < theta[1]-theta[0] < .14 and (theta[6]+theta[7])/2>.67:
            return 1
        return 0 if (theta[6]+theta[7])/2>.73 else 2

    def prior(self, theta, family=None):
        if family is None:
            lo,hi=BOUNDS.T
            mu=(lo+hi)/2
            sd=np.array([10,10,1,.20,.20,.7,.25,.25,.08,.08])
        else:
            pb=PRIOR_BOUNDS[family]
            lo,hi=pb.T
            mu=(lo+hi)/2
            sd=(hi-lo)/np.sqrt(12)
            sd[:3]=[10,10,1]
            if family==1:
                if abs(theta[5])>.25:
                    mu[5]=np.sign(theta[5])*.625
                    sd[5]=.45/np.sqrt(12)
                else:
                    sd[5]=.64
        return mu,1/sd**2

    def fit(self, family=None, reg=True):
        enc,k,n=self.data()
        mu,precision=self.prior(self.theta,family)
        bounds=BOUNDS if family is None else PRIOR_BOUNDS[family]
        # Permit zero/uncertain correlation while its sign is being identified.
        x0=np.clip(self.theta,bounds[:,0]+1e-7,bounds[:,1]-1e-7)
        if not reg:
            precision=np.zeros(10)
        def fun(z):
            theta=z*OPT_SCALE
            p,g=probabilities(theta,enc,jacobian=True)
            p=np.clip(p,1e-10,1-1e-10)
            val=-(k*np.log(p)+(n-k)*np.log1p(-p)).sum()+.5*np.dot((theta-mu)**2,precision)
            grad=g.T@((n*p-k)/(p*(1-p)))+(theta-mu)*precision
            return val,grad*OPT_SCALE
        res=minimize(fun,x0/OPT_SCALE,jac=True,method='L-BFGS-B',bounds=bounds/OPT_SCALE[:,None],
                     options={'maxiter':160,'ftol':1e-11,'gtol':2e-5})
        self.theta=res.x*OPT_SCALE
        p,g=probabilities(self.theta,enc,jacobian=True)
        fisher=g.T@((n/(p*(1-p)))[:,None]*g)
        cov=np.linalg.inv(fisher+np.diag(precision+1e-6))
        self.cov=cov
        return fisher

    def design(self, shots):
        theta=self.theta
        enc,k,n=self.data()
        p,g=probabilities(theta,enc,jacobian=True)
        # Posterior covariance handles the finite prior supports. Use ordinary
        # Fisher information early, while the family is still uncertain.
        if self.cov is None:
            _,prec=self.prior(theta,self.family)
            self.cov=np.linalg.inv(g.T@((n/(p*(1-p)))[:,None]*g)+np.diag(prec))
        cov=self.cov
        _,gg=probabilities(theta,GRID,jacobian=True)
        weight=.045*np.diag(1/SCALES**2)+(.55/.04**2)*(gg.T@gg)/len(gg)
        times=np.linspace(0,6,41)
        modes=np.repeat(np.arange(6),len(times)*8)
        ts=np.tile(np.repeat(times,8),6)
        angle=np.tile(np.arange(8)*np.pi/4,len(times)*6)
        f1,f2,j=theta[:3]
        freqs=np.array([f1+j,f1-j,f2+j,f2-j,f1+f2,f1-f2])
        phases=(TWOPI*freqs[modes]*ts-angle+np.pi)%TWOPI-np.pi
        cand=(modes,ts,phases)
        cp,cg=probabilities(theta,cand,jacobian=True)
        projected=cg@cov
        gains=shots*np.sum((projected@weight)*projected,axis=1)/(cp*(1-cp)+shots*np.sum(projected*cg,axis=1))
        ix=np.argmax(gains)
        return experiment(int(modes[ix]),ts[ix],phases[ix],shots)


class Strategy(Base):
    def __init__(self):
        super().__init__()
        self.centers={}
        self.samples=None
        self.weights=None
        self.famprob=np.ones(3)/3
        self.comp_samples={}
        self.deadline=float("inf")
        self.projection=np.random.default_rng(314159).normal(size=(598,30))
        self.acq_done=None
        for act in self.initial:
            if 0<act["time"]<1: act["shots"]=32

    def posterior(self,count=8000,family=None):
        enc,k,n=self.data()
        components=[]
        gap=self.theta[1]-self.theta[0]
        # Frequency supports are far apart after alias acquisition.
        possible=[0,2] if gap<-.015 or gap>.19 else [0,1,2]
        if len(self.history)>27 and np.max(self.famprob)>.99999:
            possible=[int(np.argmax(self.famprob))]
        logvolume=[np.log((1.7-.35)**2*.135*.18**2*1.3*.12**2*.12**2),
                   np.log(1.45*.075*.10*.18**2*.9*.20**2*.16**2),
                   np.log((1.7-.15)**2*.175*.20**2*1.7*.18**2*.17**2)]
        for fam in possible:
            if fam==0 and abs(gap)<.20:
                continue
            signs=[-1,1] if fam==1 else [0]
            for sign in signs:
                pb=PRIOR_BOUNDS[fam].copy()
                if fam==1:
                    pb[5]=[.40,.85] if sign==1 else [-.85,-.40]
                pm=pb.mean(axis=1)
                ps=(pb[:,1]-pb[:,0])/np.sqrt(12)
                ps[:3]=[10,10,1]
                precision=1/ps**2
                key=(fam,sign)
                start=self.centers.get(key,self.theta)
                start=np.clip(start,pb[:,0]+1e-7,pb[:,1]-1e-7)
                def fun(z):
                    th=z*OPT_SCALE
                    p,g=probabilities(th,enc,jacobian=True)
                    p=np.clip(p,1e-10,1-1e-10)
                    val=-(k*np.log(p)+(n-k)*np.log1p(-p)).sum()+.5*np.dot((th-pm)**2,precision)
                    grad=g.T@((n*p-k)/(p*(1-p)))+(th-pm)*precision
                    return val,grad*OPT_SCALE
                res=minimize(fun,start/OPT_SCALE,jac=True,method='L-BFGS-B',bounds=pb/OPT_SCALE[:,None],
                             options={'maxiter':110,'ftol':1e-10,'gtol':2e-5})
                mu=res.x*OPT_SCALE
                self.centers[key]=mu
                p,g=probabilities(mu,enc,jacobian=True)
                fisher=g.T@((n/(p*(1-p)))[:,None]*g)
                cov=np.linalg.inv(fisher+np.diag(precision))
                chol=np.linalg.cholesky((cov+cov.T)/2)
                z=self.rng.normal(size=(count,10))
                df=7.
                z*=np.sqrt(df/self.rng.chisquare(df,size=count))[:,None]
                samples=mu+1.25*z@chol.T
                valid=np.all((samples>=pb[:,0])&(samples<=pb[:,1]),axis=1)
                gg=samples[:,1]-samples[:,0]
                if fam==1:
                    valid &= (gg>=.025)&(gg<=.10)
                else:
                    valid &= np.abs(gg)>=(.35 if fam==0 else .15)
                samples=samples[valid];z=z[valid]
                if len(samples)==0:
                    continue
                p=batch_prob(samples,enc)
                ll=np.log(p)@k+np.log1p(-p)@(n-k)
                logprop=(gammaln((df+10)/2)-gammaln(df/2)-5*np.log(df*np.pi)
                         -np.log(np.diag(chol)).sum()-10*np.log(1.25)
                         -(df+10)/2*np.log1p(np.sum(z*z,axis=1)/df))
                lw=ll-logprop-logvolume[fam]
                components.append((fam,samples,lw))
        if not components:
            # Extremely unlikely numerical fallback, still a valid bounded estimate.
            self.fit(family=None)
            self.samples=None
            return self.theta,self.cov
        weights=np.concatenate([c[2] for c in components])
        samples=np.concatenate([c[1] for c in components])
        weights=np.exp(weights-logsumexp(weights))
        probs=np.zeros(3)
        off=0
        for fam,ss,ll in components:
            probs[fam]+=weights[off:off+len(ss)].sum()
            off+=len(ss)
        self.famprob=probs
        self.family=int(np.argmax(probs))
        mean=weights@samples
        dd=samples-mean
        cov=(dd.T*weights)@dd
        self.theta=mean
        self.cov=cov
        self.samples=samples
        self.weights=weights
        self.diag['ess']=float(1/(weights@weights))
        self.diag['families']=probs.tolist()
        return mean,cov

    def design(self,shots):
        if self.samples is None:
            return super().design(shots)
        # Common, stratified particles make all candidate comparisons low-noise.
        n=1024
        cdf=np.cumsum(self.weights)
        ix=np.searchsorted(cdf,(np.arange(n)+.5)/n)
        samples=self.samples[np.minimum(ix,len(cdf)-1)]
        dx=samples-samples.mean(axis=0)
        # Use the actual predictive grid as well as the parameter coordinates.
        # Correlation uncertainty is nonlinear at long times; a Jacobian at the
        # posterior mean alone can substantially underweight that uncertainty.
        features=np.empty((n,598))
        features[:,:10]=samples*(np.sqrt(.045)/SCALES)
        for j in range(0,n,256):
            features[j:j+256,10:]=batch_prob(samples[j:j+256],GRID)*np.sqrt(.55/(.04**2*588))
        features-=features.mean(axis=0)
        qq,_=np.linalg.qr(features@self.projection,mode='reduced')
        _,_,vv=np.linalg.svd(qq.T@features,full_matrices=False)
        target=features@vv.T
        self.diag["min_capture"]=min(self.diag.get("min_capture",1.),float(np.sum(target*target)/max(np.sum(features*features),1e-30)))
        times=np.linspace(0,6,41)
        modes=np.repeat(np.arange(6),len(times)*8)
        ts=np.tile(np.repeat(times,8),6)
        angles=np.tile(np.arange(8)*np.pi/4,len(times)*6)
        f1,f2,j=self.theta[:3]
        fs=np.array([f1+j,f1-j,f2+j,f2-j,f1+f2,f1-f2])
        phases=(TWOPI*fs[modes]*ts-angles+np.pi)%TWOPI-np.pi
        base_modes=np.repeat(np.arange(6),len(times))
        base_times=np.tile(times,6)
        f1,f2,j,s1,s2,r,v1,v2,b1,b2=samples.T
        f=np.array([f1+j,f1-j,f2+j,f2-j,f1+f2,f1-f2]).T[:,base_modes]
        d=np.array([s1*s1,s1*s1,s2*s2,s2*s2,s1*s1+s2*s2+2*r*s1*s2,s1*s1+s2*s2-2*r*s1*s2]).T[:,base_modes]
        v=np.array([v1,v1,v2,v2,v1*v2,v1*v2]).T[:,base_modes]
        b=np.array([b1,b1,b2,b2,b1*b2,b1*b2]).T[:,base_modes]
        delta=TWOPI*(f-fs[base_modes])*base_times
        amp=.5*v*np.exp(-.5*d*base_times**2)
        cc=amp*np.cos(delta)
        ss=amp*np.sin(delta)
        bb=.5*(1+b)
        mc=cc.mean(axis=0);ms=ss.mean(axis=0);mb=bb.mean(axis=0)
        cc-=mc;ss-=ms;bb-=mb
        ccross=target.T@cc/n;scross=target.T@ss/n;bcross=target.T@bb/n
        vc=np.mean(cc*cc,axis=0);vs=np.mean(ss*ss,axis=0);vb=np.mean(bb*bb,axis=0)
        ccs=np.mean(cc*ss,axis=0);cbc=np.mean(bb*cc,axis=0);cbs=np.mean(bb*ss,axis=0)
        ca=np.cos(np.arange(8)*np.pi/4);sa=np.sin(np.arange(8)*np.pi/4)
        cross=(bcross[:,:,None]+ccross[:,:,None]*ca-scross[:,:,None]*sa).reshape(target.shape[1],-1)
        mean=(mb[:,None]+mc[:,None]*ca-ms[:,None]*sa).reshape(-1)
        variance=(vb[:,None]+vc[:,None]*ca**2+vs[:,None]*sa**2
                  +2*cbc[:,None]*ca-2*cbs[:,None]*sa-2*ccs[:,None]*ca*sa).reshape(-1)
        gains=np.sum(cross*cross,axis=0)/(variance+(mean*(1-mean)-variance)/shots+1e-15)
        # Refine a diverse shortlist by the exact expected posterior mean-square
        # reduction for a binomial batch (rather than a local Fisher approximation).
        shortlisted=[]
        gr=gains.reshape(6,len(times),8)
        for mode in range(6):
            vals=gr[mode].copy()
            for repeat in range(4):
                tix,aix=np.unravel_index(np.argmax(vals),vals.shape)
                shortlisted.append((mode*len(times)+tix)*8+aix)
                vals[max(0,tix-3):tix+4,aix]=-np.inf
            tix,aix=np.unravel_index(np.argmax(gr[mode]),gr[mode].shape)
            for factor in [1.25,1.5]:
                t2=min(len(times)-1,int(round(tix*factor)))
                shortlisted.append((mode*len(times)+t2)*8+aix)
        shortlisted=np.unique(shortlisted)
        bin_k=np.arange(shots+1)
        comb=gammaln(shots+1)-gammaln(bin_k+1)-gammaln(shots-bin_k+1)
        localp=batch_prob(samples,(modes[shortlisted],ts[shortlisted],phases[shortlisted]))
        utilities=[]
        for col in range(len(shortlisted)):
            if utilities and time.monotonic()>self.deadline:
                break
            p=localp[:,col]
            q=np.exp(comb[None,:]+np.log(p)[:,None]*bin_k+np.log1p(-p)[:,None]*(shots-bin_k))/n
            pk=q.sum(axis=0)
            cm=target.T@q
            utilities.append(np.sum(np.sum(cm*cm,axis=0)/np.maximum(pk,1e-100)))
        best=shortlisted[int(np.argmax(utilities))]
        return experiment(int(modes[best]),ts[best],phases[best],shots)

    def decision(self):
        if self.samples is None:
            return self.theta
        n=4096
        cdf=np.cumsum(self.weights)
        ix=np.minimum(np.searchsorted(cdf,(np.arange(n)+.5)/n),len(cdf)-1)
        ss=self.samples[ix]
        ps=np.sqrt(.045)/SCALES
        pr=np.sqrt(.55/(.04**2*len(GRID[0])))
        feat=np.empty((n,10+len(GRID[0])))
        feat[:,:10]=ss*ps
        for j in range(0,n,512):
            feat[j:j+512,10:]=batch_prob(ss[j:j+512],GRID)*pr
        # Recenter to avoid cancellation in squared distances at high frequencies.
        center=feat.mean(axis=0)
        feat-=center
        norms=np.sum(feat*feat,axis=1)
        def obj(z):
            th=z*OPT_SCALE
            prob,grad=probabilities(th,GRID,jacobian=True)
            xx=np.r_[th*ps,prob*pr]-center
            ll=2*(feat@xx)-norms-np.dot(xx,xx)
            val=logsumexp(ll)
            ww=np.exp(ll-val)
            delta=xx-ww@feat
            derivative=2*(ps*delta[:10]+pr*grad.T@delta[10:])
            return -val,derivative*OPT_SCALE
        self.diag['posterior_mean']=self.theta.tolist()
        result=minimize(obj,self.theta/OPT_SCALE,jac=True,method='L-BFGS-B',bounds=BOUNDS/OPT_SCALE[:,None],
                        options={'maxiter':80,'ftol':1e-11,'gtol':1e-7})
        self.theta=result.x*OPT_SCALE
        return self.theta

    def disambiguate(self):
        sensor=int(np.argmin(self.freq_confidence))
        alts=self.freq_alts[sensor]
        vals=np.array([a[1] for a in alts])
        w=np.exp(-np.array([a[0]-alts[0][0] for a in alts]))
        w/=w.sum()
        tt=np.repeat(np.linspace(.05,4.5,90),16)
        ph=np.tile(np.arange(16)*np.pi/8,90)
        ff,ss,vv,bb=vals.T
        p=.5*(1+bb[:,None]+vv[:,None]*np.exp(-.5*ss[:,None]**2*tt**2)*np.cos(TWOPI*ff[:,None]*tt-ph))
        mean=w@p
        utility=w@((p-mean)**2)
        ix=np.argmax(utility)
        return experiment(sensor*2,tt[ix],ph[ix],128)

    def current_estimate(self):
        theta=np.where(np.isfinite(self.theta),self.theta,BOUNDS.mean(axis=1))
        return {"type":"estimate","parameters":parameter_dict(np.clip(theta,BOUNDS[:,0],BOUNDS[:,1]))}

    def next(self,message):
        if message['type']=='observation':
            self.history.append(message)
            self.spent+=sum(message['counts'])
        i=len(self.history)
        if i<16:
            return self.initial[i]
        if self.acq_done is None:
            self.initial_fit()
            if min(self.freq_confidence)<12 and i<20:
                return self.disambiguate()
            self.acq_done=i
            gap=self.plus[1]-self.plus[0]
            vis=(self.theta[6]+self.theta[7])/2
            if -.005<gap<.135 and vis>.71:
                self.jcenter,self.jtime=.15,1.45
            elif abs(gap)>.25 and vis>.76:
                self.jcenter,self.jtime=.0925,1.20
            elif vis<.70:
                self.jcenter,self.jtime=.1125,.95
            else:
                self.jcenter,self.jtime=.1175,.82
        if i in (self.acq_done,self.acq_done+1):
            sensor=i-self.acq_done
            m=2*sensor+1
            f=self.plus[sensor]-2*self.jcenter
            return experiment(m,self.jtime,TWOPI*f*self.jtime-np.pi/2,96)
        if i==self.acq_done+2:
            self.fit(family=None)
        if i==48 or time.monotonic()>self.deadline:
            self.posterior(count=70000 if time.monotonic()<self.deadline-2 else 12000)
            if time.monotonic()<self.deadline+5:
                self.decision()
            return {'type':'estimate','parameters':parameter_dict(np.clip(self.theta,BOUNDS[:,0],BOUNDS[:,1]))}
        self.posterior(count=6500)
        shots=int(round((6144-self.spent)/(48-i)))
        return self.design(shots)
