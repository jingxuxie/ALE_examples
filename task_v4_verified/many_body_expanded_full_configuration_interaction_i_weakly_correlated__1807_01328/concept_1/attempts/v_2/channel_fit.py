import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares
from quadrature import ORDERS,SUBSET,LEFT,RIGHT,SINGLE
from response_fit import MASKS

class ChannelFit:
    def __init__(self,angle_fit):
        self.angle_fit=angle_fit
        self.masks=angle_fit.masks
        self.values=angle_fit.values
        self.single=angle_fit.single
        self.base=angle_fit.denominator-.22
        self.transform=angle_fit.transform
        self.scale=angle_fit.scale
        self.beta=.4
        self.last=None

    def evaluate(self,parameters,masks,energy=None,jacobian=False):
        angles=parameters[28:44].reshape(8,2)
        azimuth,elevation=angles[:,0],angles[:,1]
        unit=np.array([np.cos(azimuth)*np.cos(elevation),np.sin(azimuth)*np.cos(elevation),np.sin(elevation)]).T
        shift=.4*np.tanh(parameters[44:])
        diagonal=self.base[:,None]+np.array([.45,.22,0.])[None]+shift[:,None]
        amplitude=np.sqrt(self.single[:,None]*(diagonal+self.beta*self.single[:,None]))
        source=amplitude*unit
        active=MASKS[masks]
        hopping=.9*np.tanh(parameters[:28])
        matrices=np.zeros((len(masks),3,8,8))
        for channel in range(3):
            matrices[:,channel,np.arange(8),np.arange(8)]=diagonal[:,channel][None]*active+(1-active)
            if energy is not None:
                matrices[:,channel,np.arange(8),np.arange(8)]-=self.beta*energy[:,None]*active
            edges=-hopping*active[:,LEFT]*active[:,RIGHT]
            matrices[:,channel,LEFT,RIGHT]=edges
            matrices[:,channel,RIGHT,LEFT]=edges
        selected=source.T[None]*active[:,None,:]
        vectors=np.linalg.solve(matrices,selected[:,:,:,None])[:,:,:,0]
        prediction=-np.sum(vectors*selected,axis=(1,2))
        if not jacobian:
            return prediction
        edge_gradient=-2*np.sum(vectors[:,:,LEFT]*vectors[:,:,RIGHT],axis=1)*.9*(1-np.tanh(parameters[:28])**2)
        derivative_azimuth=np.array([-np.sin(azimuth)*np.cos(elevation),np.cos(azimuth)*np.cos(elevation),np.zeros(8)]).T*amplitude
        derivative_elevation=np.array([-np.cos(azimuth)*np.sin(elevation),-np.sin(azimuth)*np.sin(elevation),np.cos(elevation)]).T*amplitude
        gradient_azimuth=-2*np.sum(vectors*derivative_azimuth.T[None],axis=1)
        gradient_elevation=-2*np.sum(vectors*derivative_elevation.T[None],axis=1)
        angle_gradient=np.stack((gradient_azimuth,gradient_elevation),axis=2).reshape(len(masks),-1)
        shift_gradient=np.sum(vectors**2-vectors*(source/(diagonal+self.beta*self.single[:,None])).T[None],axis=1)*.4*(1-np.tanh(parameters[44:])**2)
        return prediction,np.concatenate((edge_gradient,angle_gradient,shift_gradient),axis=1)

    def residual(self,parameters):
        prediction,gradient=self.evaluate(parameters,self.masks,self.values,True)
        values=self.transform@((prediction-self.values)/self.scale)
        self.gradient=self.transform@(gradient/self.scale)
        values=np.r_[values,parameters[44:]*1e-5]
        regularization=np.zeros((8,52))
        regularization[:,44:]=np.eye(8)*1e-5
        self.gradient=np.concatenate((self.gradient,regularization),axis=0)
        self.last=parameters.copy()
        return values

    def jacobian(self,parameters):
        if self.last is None or np.any(self.last!=parameters):
            self.residual(parameters)
        return self.gradient

    def initialize(self):
        previous=self.angle_fit.parameters
        hopping=.85*np.tanh(previous[:28])*np.sqrt(self.angle_fit.denominator[LEFT]*self.angle_fit.denominator[RIGHT])
        angles=np.zeros((8,2))
        angles[1,0]=previous[28]
        angles[2:]=previous[29:].reshape(6,2)
        return np.r_[np.arctanh(np.clip(hopping/.9,-.98,.98)),angles.ravel(),np.zeros(8)]

    def fit(self,starts=2,iterations=400):
        generator=np.random.default_rng(2167)
        initial=self.initialize()
        best=None
        for start in range(starts):
            parameters=initial.copy()
            if start:
                parameters[28:44]+=generator.normal(0,.15,16)
            fitted=least_squares(self.residual,parameters,jac=self.jacobian,method='lm',max_nfev=iterations,ftol=1e-9,gtol=1e-9,xtol=1e-9)
            score=np.linalg.norm(fitted.fun)
            if best is None or score<best[0]:
                best=score,fitted.x
        self.parameters=best[1]
        self.score=best[0]
        predicted=self.evaluate(self.parameters,np.arange(256))
        for iteration in range(8):
            predicted=self.evaluate(self.parameters,np.arange(256),predicted)
        return predicted

if __name__=='__main__':
    import json
    import time
    from angle_fit import AngleFit
    from design import covariance,design,estimate
    from quadrature import features,HIGH,CANDIDATES,SELECTOR,PAIR,TRIPLES,mobius
    ASSETS='/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    tables=np.load(ASSETS+'/input/practice.npz')['energies']
    models=json.load(open(ASSETS+'/input/practice_models.json'))
    factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
    start=time.process_time()
    for index in [14,26,29,32,3,7,15,19]:
        table=tables[index]
        matrix=covariance(features(table)[1]*factor,.7,8)
        chosen=design(matrix,'anchor')
        angle=AngleFit(table,models[index]['orbital_energy'],np.r_[PAIR,TRIPLES,CANDIDATES[chosen]])
        predicted=angle.fit(starts=5,iterations=350)
        target=SELECTOR@mobius(table)[HIGH]
        initial_error=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
        channel=ChannelFit(angle)
        predicted=channel.fit(starts=2,iterations=500)
        error=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
        print(index,'angle',initial_error,'channel',error,'score',angle.score,channel.score,'cpu',time.process_time()-start,flush=True)
