import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='4'
from pathlib import Path
import numpy as np
import torch
from scipy.linalg import solve_triangular,svd

torch.set_num_threads(4)
torch.set_num_interop_threads(1)
OMEGA=.3125+.625*torch.arange(192)
ACOUSTIC=[(7,17,2,4),(10,28,2,4),(7,20,2,4),(10,30,2,3.7)]
CENTERS=[([21,53],[45,93]),([3,20,57],[12,46,100]),([27,5,76],[58,18,105]),([12,40,77],[40,74,105])]
WIDTHS=[([2.5,3.5],[9,12]),([1,2.5,3.5],[4,9,12]),([1.5,1.5,2.5],[7,7,11]),([4,4,4],[13,15,13])]


def decode(params,code):
    count=2 if code==0 else 3
    low,high,low_power,high_power=ACOUSTIC[code]
    scale=low+(high-low)*torch.sigmoid(params[...,0])
    power=low_power+(high_power-low_power)*torch.sigmoid(params[...,1])
    lower=params.new_tensor(CENTERS[code][0])
    upper=params.new_tensor(CENTERS[code][1])
    centers=lower+(upper-lower)*torch.sigmoid(params[...,2:2+count])
    if code==2:
        centers=torch.stack((centers[...,0]-.5*centers[...,1],centers[...,0]+.5*centers[...,1],centers[...,2]),dim=-1)
    lower=params.new_tensor(WIDTHS[code][0])
    upper=params.new_tensor(WIDTHS[code][1])
    widths=lower+(upper-lower)*torch.sigmoid(params[...,2+count:2+2*count])
    skew=.35*torch.tanh(params[...,2+2*count:2+3*count])
    weights=torch.softmax(params[...,2+3*count:],dim=-1)
    acoustic=OMEGA*torch.exp(-(OMEGA/scale[...,None])**power[...,None])
    standardized=(OMEGA[:,None]-centers[...,None,:])/widths[...,None,:]
    optical=torch.exp(-.5*standardized.square())*(1+skew[...,None,:]*torch.tanh(standardized))*(OMEGA/(OMEGA.square()+4))[:,None]
    bands=torch.cat((acoustic[...,None],optical),dim=-1)
    bands=bands/bands.sum(-2,keepdim=True).clamp_min(1e-20)
    return (bands*weights[...,None,:]).sum(-1)


def fit_prior(code):
    with np.load(Path(__file__).resolve().parent / 'posterior_prior.npz') as archive:
        return torch.tensor(archive['mean%d'%code]),torch.tensor(archive['precision%d'%code])


def sample(initial,matrix,target,code,steps=400,walkers=12):
    count=initial.shape[-1]
    mean,precision=fit_prior(code)
    identity=torch.eye(count)
    perturb=torch.cat((torch.zeros((1,count)),.002*identity),dim=0)
    parameter=initial.clone()
    def objective(candidate):
        probability=decode(candidate,code)
        predicted=probability@matrix.transpose(1,2) if candidate.ndim==3 else (matrix@probability[...,None]).squeeze(-1)
        residual=predicted-(target[:,None,:] if candidate.ndim==3 else target)
        difference=candidate-mean
        return residual.square().sum(-1)+(difference@precision*difference).sum(-1)
    for step in range(12):
        varied=parameter[:,None,:]+perturb[None,:,:]
        probability=decode(varied,code)
        forward=probability@matrix.transpose(1,2)
        residual=forward[:,0]-target
        jacobian=(forward[:,1:]-forward[:,:1]).transpose(1,2)/.002
        hessian=jacobian.double().transpose(1,2)@jacobian.double()+precision.double()
        gradient=(jacobian.transpose(1,2)@residual[:,:,None]).squeeze(-1)+(parameter-mean)@precision
        change=torch.linalg.solve(hessian,gradient.double()[:,:,None]).squeeze(-1).float().clamp(-.7,.7)
        cost=objective(parameter)
        for rate in [1,.5,.25,.125]:
            proposed=parameter-rate*change
            candidate_cost=objective(proposed)
            accepted=candidate_cost<cost
            parameter[accepted]=proposed[accepted]
            cost[accepted]=candidate_cost[accepted]
    inverse=torch.linalg.inv(hessian)
    inverse=(inverse+inverse.transpose(-1,-2))/2
    root=torch.linalg.cholesky(inverse+1e-6*identity).float()
    state=parameter[:,None,:]+.1*(torch.randn(len(parameter),walkers,count)@root.transpose(1,2))
    cost=objective(state)
    scale=torch.full((len(parameter),1,1),.55)
    accepted_count=torch.zeros(len(parameter))
    samples=[]
    for step in range(steps):
        proposed=state+scale*(torch.randn_like(state)@root.transpose(1,2))
        proposed_cost=objective(proposed)
        accepted=torch.log(torch.rand_like(cost))<.5*(cost-proposed_cost)
        state=torch.where(accepted[:,:,None],proposed,state)
        cost=torch.where(accepted,proposed_cost,cost)
        accepted_count+=accepted.float().mean(1)
        if step%40==39 and step<160:
            rate=accepted_count/40
            scale*=torch.exp((rate-.25)[:,None,None]).clamp(.7,1.4)
            accepted_count.zero_()
        if step>=160 and step%10==9:
            samples.append(decode(state,code).numpy())
    return np.concatenate(samples,axis=1)


def compressed_data(inputs,coupling):
    omega=inputs['omega_mev']
    matrices,targets=[],[]
    for row in range(len(coupling)):
        slots=np.flatnonzero(inputs['mask'][row])
        kernel=omega[None,:]**2/(omega[None,:]**2+inputs['nu_mev'][row,slots,None]**2)
        std=inputs['noise_std'][row,slots]
        rho,length=inputs['noise_rho'][row],inputs['noise_length'][row]
        cov=std[:,None]*std[None,:]*((1-rho)*np.eye(len(slots))+rho*np.exp(-np.abs(slots[:,None]-slots)/length))
        root=np.linalg.cholesky(cov)
        whitened=solve_triangular(root,kernel,lower=True)
        target=solve_triangular(root,inputs['interaction'][row,slots],lower=True)
        left,singular,right=svd(whitened,full_matrices=False)
        matrices.append(singular[:10,None]*right[:10]*coupling[row])
        targets.append(left[:,:10].T@target)
    return np.array(matrices),np.array(targets)


def predict(inputs,raw,coupling,steps=600,walkers=16,compressed=None):
    torch.set_num_threads(4)
    torch.manual_seed(819)
    raw=torch.tensor(raw,dtype=torch.float32)
    family=raw[:,56:].argmax(1).numpy()
    matrices,targets=compressed_data(inputs,coupling) if compressed is None else compressed
    matrices=torch.tensor(matrices,dtype=torch.float32)
    targets=torch.tensor(targets,dtype=torch.float32)
    posterior_mean=np.zeros((len(coupling),192))
    posterior_median=np.zeros_like(posterior_mean)
    offset=0
    for code in range(4):
        count=11 if code==0 else 15
        selected=np.flatnonzero(family==code)
        if len(selected):
            with torch.no_grad():
                samples=sample(raw[selected,offset:offset+count],matrices[selected],targets[selected],code,steps,walkers)
            posterior_mean[selected]=samples.mean(1)
            cdf=np.median(samples.cumsum(-1),axis=1)
            posterior_median[selected]=np.diff(cdf,axis=1,prepend=np.zeros((len(selected),1)))
        offset+=count
    probability=np.maximum(.5*(posterior_mean+posterior_median),0)
    return probability/probability.sum(1)[:,None]
