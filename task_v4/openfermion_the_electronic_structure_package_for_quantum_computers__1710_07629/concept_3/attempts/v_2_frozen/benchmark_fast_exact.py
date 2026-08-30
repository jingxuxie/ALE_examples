import time
import numpy as np
import fast_exact

inputs=dict(np.load('dev/validation.npz'))
predictions=np.full_like(inputs['gaps'],np.nan)
started=time.process_time()
for count,index in enumerate(np.flatnonzero(inputs['n_sites']==10)):
    predictions[index]=fast_exact.calculate(inputs['hopping'][index,:10,:10],inputs['interaction'][index,:10],inputs['potential'][index,:10])
    if count%25==24:
        print(count+1,time.process_time()-started,flush=True)
np.save('dev/fast_exact10_predictions.npy',predictions)
errors=predictions-inputs['gaps']
print('finished',time.process_time()-started,'rmse',np.sqrt(np.nanmean(errors**2,axis=0)),'max_error',np.nanmax(np.abs(errors)),flush=True)
for index in np.flatnonzero(np.any(np.abs(errors)>0.001,axis=1)):
    print(index,int(inputs['family'][index]),errors[index],flush=True)
