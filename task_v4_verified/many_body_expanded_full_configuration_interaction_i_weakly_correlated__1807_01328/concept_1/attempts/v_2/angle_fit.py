import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares
from quadrature import ORDERS, SUBSET, PAIR, LEFT, RIGHT, SINGLE, TRIPLES, HIGH, SELECTOR, CANDIDATES, mobius, features
from response_fit import MASKS

class AngleFit:
    def __init__(self,table,orbital,masks):
        self.masks = np.array(sorted(masks,key=lambda mask:(ORDERS[mask],mask)))
        self.values = table[self.masks]
        self.single = np.maximum(-table[SINGLE],1e-14)
        self.denominator = np.array(orbital)[3:]+.22
        self.beta = .4
        self.source = np.sqrt(self.single*(1+self.beta*self.single/self.denominator))
        self.scale = max(np.max(self.single),1e-6)
        self.transform = np.eye(len(masks))
        for row,mask in enumerate(self.masks):
            for column in range(row):
                if SUBSET[mask,self.masks[column]]:
                    self.transform[row] -= self.transform[column]
        self.transform[ORDERS[self.masks]==2] *= .2
        self.transform[ORDERS[self.masks]>=4] *= 2.
        self.pairs = -table[PAIR]
        self.last = None

    def evaluate(self,parameters,masks,energy=None,jacobian=False):
        angles = np.zeros((8,2))
        angles[1,0] = parameters[28]
        angles[2:] = parameters[29:].reshape(6,2)
        azimuth,elevation = angles[:,0],angles[:,1]
        unit = np.array([np.cos(azimuth)*np.cos(elevation),np.sin(azimuth)*np.cos(elevation),np.sin(elevation)]).T
        source = unit*self.source[:,None]
        active = MASKS[masks]
        hopping = .85*np.tanh(parameters[:28])
        matrices = np.broadcast_to(np.eye(8),(len(masks),8,8)).copy()
        edges = -hopping*active[:,LEFT]*active[:,RIGHT]
        matrices[:,LEFT,RIGHT] = edges
        matrices[:,RIGHT,LEFT] = edges
        if energy is not None:
            matrices[:,np.arange(8),np.arange(8)] -= self.beta*energy[:,None]/self.denominator
        selected = source[None]*active[:,:,None]
        vectors = np.linalg.solve(matrices,selected)
        prediction = -np.sum(vectors*selected,axis=(1,2))
        if not jacobian:
            return prediction
        derivative_azimuth = np.array([-np.sin(azimuth)*np.cos(elevation),np.cos(azimuth)*np.cos(elevation),np.zeros(8)]).T*self.source[:,None]
        derivative_elevation = np.array([-np.cos(azimuth)*np.sin(elevation),-np.sin(azimuth)*np.sin(elevation),np.cos(elevation)]).T*self.source[:,None]
        gradient_azimuth = -2*np.sum(vectors*derivative_azimuth[None],axis=2)
        gradient_elevation = -2*np.sum(vectors*derivative_elevation[None],axis=2)
        angle_gradient = np.stack((gradient_azimuth[:,2:],gradient_elevation[:,2:]),axis=2).reshape(len(masks),-1)
        edge_gradient = -2*np.sum(vectors[:,LEFT]*vectors[:,RIGHT],axis=2)*.85*(1-np.tanh(parameters[:28])**2)
        return prediction,np.concatenate((edge_gradient,gradient_azimuth[:,1:2],angle_gradient),axis=1)

    def residual(self,parameters):
        prediction,gradient = self.evaluate(parameters,self.masks,self.values,True)
        values = self.transform@((prediction-self.values)/self.scale)
        self.gradient = self.transform@(gradient/self.scale)
        matrix = np.eye(8)
        matrix[LEFT,RIGHT] = -.85*np.tanh(parameters[:28])
        matrix[RIGHT,LEFT] = matrix[LEFT,RIGHT]
        eigenvalue,eigenvector = np.linalg.eigh(matrix)
        extra = np.zeros(41)
        if eigenvalue[0] < .1:
            extra[:28] = -.1*eigenvector[LEFT,0]*eigenvector[RIGHT,0]*.85*(1-np.tanh(parameters[:28])**2)
        values = np.r_[values,.05*min(eigenvalue[0]-.1,0),parameters[:28]*1e-6]
        self.gradient = np.concatenate((self.gradient,extra[None],np.pad(np.eye(28)*1e-6,((0,0),(0,13)))),axis=0)
        self.last = parameters.copy()
        return values

    def jacobian(self,parameters):
        if self.last is None or np.any(self.last != parameters):
            self.residual(parameters)
        return self.gradient

    def fit(self,starts=8,iterations=500,initialization='random',time_budget=None):
        import time
        start_time=time.process_time()
        generator = np.random.default_rng(12537)
        best = None
        self.fits=[]
        for start in range(starts):
            if start and time_budget is not None and time.process_time()-start_time>=time_budget:
                break
            angles = generator.normal(0,1.2,13)
            angles[0] = generator.uniform(-np.pi,np.pi)
            parameters = np.r_[generator.normal(0,.1,28),angles]
            if initialization=='pairs' and start%3!=2:
                full_angles=np.zeros((8,2))
                full_angles[1,0]=angles[0]
                full_angles[2:]=angles[1:].reshape(6,2)
                azimuth,elevation=full_angles[:,0],full_angles[:,1]
                unit=np.array([np.cos(azimuth)*np.cos(elevation),np.sin(azimuth)*np.cos(elevation),np.sin(elevation)]).T
                product=self.source[LEFT]*self.source[RIGHT]*np.sum(unit[LEFT]*unit[RIGHT],axis=1)
                diagonal_left=1+self.beta*self.pairs/self.denominator[LEFT]
                diagonal_right=1+self.beta*self.pairs/self.denominator[RIGHT]
                constant=self.source[LEFT]**2*diagonal_right+self.source[RIGHT]**2*diagonal_left-self.pairs*diagonal_left*diagonal_right
                discriminant=np.sqrt(np.maximum(product**2-self.pairs*constant,0))
                roots=np.array([(-product+discriminant)/self.pairs,(-product-discriminant)/self.pairs])
                small=np.argmin(abs(roots),axis=0)
                hopping=roots[small,np.arange(28)]
                if start%3==1:
                    large=roots[1-small,np.arange(28)]
                    replace=(abs(large)<.65)&(generator.random(28)<.2)
                    hopping[replace]=large[replace]
                parameters[:28]=np.arctanh(np.clip(hopping/.85,-.9,.9))
            fitted = least_squares(self.residual,parameters,jac=self.jacobian,method='lm',max_nfev=iterations,ftol=1e-9,gtol=1e-9,xtol=1e-9)
            score = np.linalg.norm(fitted.fun)
            self.fits.append((score,fitted.x.copy()))
            if best is None or score < best[0]:
                best = score,fitted.x
        self.parameters = best[1]
        self.score = best[0]
        predicted = self.evaluate(self.parameters,np.arange(256))
        for iteration in range(8):
            predicted = self.evaluate(self.parameters,np.arange(256),predicted)
        return predicted

if __name__ == '__main__':
    import json
    import time
    from design import covariance,design,estimate
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    tables=np.load(ASSETS+'/input/practice.npz')['energies']
    models=json.load(open(ASSETS+'/input/practice_models.json'))
    variance_factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
    start=time.process_time()
    for index in [3,7,14,15,19,26,29,32]:
        table=tables[index]
        weights=features(table)[1]*variance_factor
        matrix=covariance(weights,.7,8)
        chosen=design(matrix,'anchor')
        masks=np.r_[PAIR,TRIPLES,CANDIDATES[chosen]]
        fit=AngleFit(table,models[index]['orbital_energy'],masks)
        predicted=fit.fit()
        actual_terms=mobius(table)[HIGH]
        predicted_terms=mobius(predicted)[HIGH]
        result=estimate(matrix,SELECTOR@predicted_terms,SELECTOR@actual_terms,chosen)[0]
        error=(result-actual_terms.sum())*1e6
        print(index,'fit',fit.score,'direct',(predicted[-1]-table[-1])*1e6,'corrected',error,'cpu',time.process_time()-start,flush=True)
