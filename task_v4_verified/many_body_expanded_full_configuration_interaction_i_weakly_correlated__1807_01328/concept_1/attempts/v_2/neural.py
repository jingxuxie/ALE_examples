import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import itertools
import time
import numpy as np
from quadrature import ORDERS, SINGLE, mobius

COMBINATIONS = {order: np.array(list(itertools.combinations(range(order),2))) for order in [4,5]}
TRIPLE_COMBINATIONS = {order: np.array(list(itertools.combinations(range(order),3))) for order in [4,5]}
SUBSETS = {order: np.flatnonzero(ORDERS == order) for order in [4,5]}
SITES = {order: np.array([[site for site in range(8) if mask & (1 << site)] for mask in SUBSETS[order]]) for order in [4,5]}

def inputs(terms, orbital, model_indices, sites, order, normalized_output=False):
    bits = 1 << sites
    singles = np.maximum(-terms[model_indices[:,None],bits],1e-14)
    average = np.maximum(singles.mean(axis=1),1e-12)
    regularized = singles + .03*average[:,None]
    pairs = COMBINATIONS[order]
    triples = TRIPLE_COMBINATIONS[order]
    pair_values = terms[model_indices[:,None],bits[:,pairs[:,0]] | bits[:,pairs[:,1]]]
    triple_values = terms[model_indices[:,None],bits[:,triples[:,0]] | bits[:,triples[:,1]] | bits[:,triples[:,2]]]
    pair_scale = np.sqrt(regularized[:,pairs[:,0]]*regularized[:,pairs[:,1]])
    triple_scale = (regularized[:,triples[:,0]]*regularized[:,triples[:,1]]*regularized[:,triples[:,2]])**(1/3)
    feature = np.concatenate((np.log(regularized/average[:,None])/2, orbital[model_indices[:,None],sites+3]-1.6, np.log(average[:,None]/.005)/3, pair_values/average[:,None]*8, pair_values/pair_scale*4, triple_values/average[:,None]*30, triple_values/triple_scale*15),axis=1)
    if normalized_output:
        magnitude = np.sort(abs(triple_values),axis=1)
        if order == 4:
            sigma = .04*np.sqrt(magnitude[:,-1]*magnitude[:,-2]) + .04*magnitude[:,-2]
        else:
            sigma = .04*np.sqrt(magnitude[:,-1]*magnitude[:,len(triples)//2]) + .02*magnitude[:,-2]
        average = 1000*np.maximum(sigma,average*1e-7)
    return np.clip(feature,-8,8), average

def forward(feature, weights):
    activations = [feature]
    for layer in range(len(weights)//2):
        value = activations[-1] @ weights[layer*2] + weights[layer*2+1]
        activations.append(np.tanh(value) if layer < len(weights)//2-1 else value)
    return activations

def predict(energies, orbital, weights, order, permutations=24, canonical=False):
    terms = np.array([mobius(table) for table in energies])
    all_sites = SITES[order]
    generator = np.random.default_rng(73519)
    if permutations >= np.math.factorial(order):
        permutes = np.array(list(itertools.permutations(range(order))))
    else:
        permutes = np.array([generator.permutation(order) for iteration in range(permutations)])
    prediction = []
    for model_index in range(len(energies)):
        if canonical:
            source = -terms[model_index,1 << all_sites]
            sites = np.take_along_axis(all_sites,np.argsort(-source,axis=1),axis=1)
        else:
            sites = all_sites[:,permutes].reshape(-1,order)
        feature, average = inputs(terms,orbital,np.full(len(sites),model_index),sites,order,canonical)
        output = forward(feature,weights)[-1][:,0]*average/1000
        prediction.append(output if canonical else output.reshape(len(all_sites),len(permutes)).mean(axis=1))
    return np.array(prediction)

def train(order, terms, orbital, allowed, steps=18000, seed=2341, canonical=False):
    generator = np.random.default_rng(seed+order)
    feature, average = inputs(terms,orbital,np.array([allowed[0]]),SITES[order][:1],order)
    sizes = [feature.shape[1],96,64,32,1]
    weights = []
    for left,right in zip(sizes[:-1],sizes[1:]):
        weights += [generator.normal(0,np.sqrt(2/(left+right)),(left,right)),np.zeros(right)]
    momentum = [np.zeros_like(weight) for weight in weights]
    velocity = [np.zeros_like(weight) for weight in weights]
    start = time.process_time()
    for step in range(steps):
        model_indices = generator.choice(allowed,512)
        subset_indices = generator.integers(len(SITES[order]),size=512)
        sites = SITES[order][subset_indices]
        permutations = np.argsort(terms[model_indices[:,None],1 << sites],axis=1) if canonical else np.argsort(generator.random(sites.shape),axis=1)
        sites = np.take_along_axis(sites,permutations,axis=1)
        feature, average = inputs(terms,orbital,model_indices,sites,order,canonical)
        target = terms[model_indices,SUBSETS[order][subset_indices]]/average*1000
        sample_weight = np.minimum((average/.005)**2,20) + .05
        sample_weight /= sample_weight.mean()
        activations = forward(feature,weights)
        delta = 2*(activations[-1][:,0]-target)[:,None]*sample_weight[:,None]/len(target)
        delta = np.clip(delta,-1,1)
        gradients = []
        for layer in range(len(sizes)-2,-1,-1):
            gradients[0:0] = [activations[layer].T @ delta + 1e-5*weights[layer*2],delta.sum(axis=0)]
            delta = (delta @ weights[layer*2].T)*(1-activations[layer]**2) if layer else None
        rate = .0015*(.08**(step/steps))
        for index in range(len(weights)):
            momentum[index] = .9*momentum[index]+.1*gradients[index]
            velocity[index] = .999*velocity[index]+.001*gradients[index]**2
            weights[index] -= rate*(momentum[index]/(1-.9**(step+1)))/(np.sqrt(velocity[index]/(1-.999**(step+1)))+1e-8)
        if step % 3000 == 2999:
            print('order',order,'step',step+1,'loss',round(np.mean((activations[-1][:,0]-target)**2*sample_weight),5),'cpu',round(time.process_time()-start,1),flush=True)
            np.savez(('canonical_' if canonical else 'neural_')+str(order)+'.npz',**{'weight'+str(index):weight for index,weight in enumerate(weights)})
    return weights

def load(order):
    archive = np.load('neural_'+str(order)+'.npz')
    return [archive['weight'+str(index)] for index in range(len(archive.files))]

if __name__ == '__main__':
    import json
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    synthetic = np.load('synthetic.npz')
    cancellation = np.load('cancellation.npz')
    energies = np.concatenate((synthetic['energies'],cancellation['energies']))
    orbital = np.concatenate((synthetic['orbital_energy'],cancellation['orbital_energy']))
    terms = np.array([mobius(table) for table in energies])
    allowed = np.flatnonzero(np.arange(len(energies)) % 5 != 0)
    validation = np.flatnonzero(np.arange(len(energies)) % 5 == 0)
    practice = np.load(ASSETS+'/input/practice.npz')['energies']
    practice_orbital = np.array([model['orbital_energy'] for model in json.load(open(ASSETS+'/input/practice_models.json'))])
    practice_terms = np.array([mobius(table) for table in practice])
    for order in [4,5]:
        weights = train(order,terms,orbital,allowed)
        predicted = predict(practice,practice_orbital,weights,order)
        validation_predicted = predict(energies[validation],orbital[validation],weights,order)
        np.savez('neural_predictions_'+str(order)+'.npz',practice=predicted,validation=validation_predicted,validation_indices=validation)
        error = (predicted-practice_terms[:,SUBSETS[order]])*1e6
        validation_error = (validation_predicted-terms[validation][:,SUBSETS[order]])*1e6
        print('order',order,'practice individual',np.sqrt(np.mean(error**2)),'sum',np.sqrt(np.mean(error.sum(axis=1)**2)),'validation individual',np.sqrt(np.mean(validation_error**2)),'sum',np.sqrt(np.mean(validation_error.sum(axis=1)**2)),flush=True)
