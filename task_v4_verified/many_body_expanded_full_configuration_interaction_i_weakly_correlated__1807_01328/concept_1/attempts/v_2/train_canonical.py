import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import json
import numpy as np
from neural import train,predict,SUBSETS
from quadrature import mobius
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
    weights = train(order,terms,orbital,allowed,steps=12000,canonical=True)
    predicted = predict(practice,practice_orbital,weights,order,canonical=True)
    validation_predicted = predict(energies[validation],orbital[validation],weights,order,canonical=True)
    np.savez('canonical_predictions_'+str(order)+'.npz',practice=predicted,validation=validation_predicted,validation_indices=validation)
    error = (predicted-practice_terms[:,SUBSETS[order]])*1e6
    validation_error = (validation_predicted-terms[validation][:,SUBSETS[order]])*1e6
    print('order',order,'practice individual',np.sqrt(np.mean(error**2)),'sum',np.sqrt(np.mean(error.sum(axis=1)**2)),'validation individual',np.sqrt(np.mean(validation_error**2)),'sum',np.sqrt(np.mean(validation_error.sum(axis=1)**2)),flush=True)
