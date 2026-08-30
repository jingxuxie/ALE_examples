import time
import numpy as np
import exact_labels

inputs=dict(np.load('dev/validation.npz'))
predictions=np.full_like(inputs['gaps'],np.nan)
started=time.process_time()
for count,index in enumerate(np.flatnonzero(inputs['n_sites']==10)):
    predictions[index]=exact_labels.predict_instance(inputs['hopping'][index,:10,:10],inputs['interaction'][index,:10],inputs['potential'][index,:10])
    if count%25==24:
        print(count+1,time.process_time()-started,flush=True)
np.save('dev/exact10_predictions.npy',predictions)
print('finished',time.process_time()-started,'max_error',np.nanmax(np.abs(predictions-inputs['gaps'])),flush=True)
