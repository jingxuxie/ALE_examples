from refine import refine, np, Path, time
import search as engine

initial=np.load('refine_0a.npz')['variables']
for number, target in enumerate([.0205,.0201,.0205,.0205]):
    initial=refine(initial,np.array([0.,0.,1.,1.,.00045,target]),f'gradient{number}',1000)
    values=np.asarray(engine.metrics(initial))
    print('GRADIENT_MINIMUM',values.tolist(),flush=True)
