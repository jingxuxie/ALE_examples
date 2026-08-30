import itertools
import json
from pathlib import Path
import numpy as np
from search import pack, unpack, Problem, BOUNDS, SPIN_MODES, EVEN_MODES
from certify import PAULI, H_OFFSET, H_BASIS, certificate

path=Path('witness.json')
witness=json.loads(path.read_text())
assert set(witness)=={'schema_version','mass','spin_orbit','orbital_mass','scalar'}
assert witness['schema_version']==1 and type(witness['schema_version']) is int
assert [len(witness[key]) for key in ['spin_orbit','orbital_mass','scalar']]==[11,9,9]
params=pack(witness)
assert all(type(value) in [float,int] and np.isfinite(value) for value in [witness['mass']]+witness['spin_orbit']+witness['orbital_mass']+witness['scalar'])
assert all(low<=value<=high for value,(low,high) in zip(params,BOUNDS))
assert np.count_nonzero(params[1:])<=8
assert path.stat().st_size<=32768

hopping={}
def add(horizontal,vertical,matrix):
    position=(horizontal%8,vertical%8)
    hopping[position]=hopping.get(position,np.zeros((2,2),complex))+matrix

def exponential(order,odd=False):
    if order==0:
        return [(0,1.)]
    return [(order,-.5j if odd else .5),(-order,.5j if odd else .5)]

def product(horizontal,vertical,horizontal_odd,vertical_odd,coefficient,matrix):
    for first,first_weight in exponential(horizontal,horizontal_odd):
        for second,second_weight in exponential(vertical,vertical_odd):
            add(first,second,coefficient*first_weight*second_weight*matrix)

add(0,0,params[0]*PAULI[3])
product(1,0,True,False,1,PAULI[1])
product(0,1,False,True,1,PAULI[2])
for coefficient,(order,cross) in zip(witness['spin_orbit'],SPIN_MODES):
    product(order,cross,True,False,coefficient,PAULI[1])
    product(cross,order,False,True,coefficient,PAULI[2])
for key,matrix in [('orbital_mass',PAULI[3]),('scalar',PAULI[0])]:
    for coefficient,(order,cross) in zip(witness[key],EVEN_MODES):
        product(order,cross,False,False,coefficient,matrix)
        if order!=cross:
            product(cross,order,False,False,coefficient,matrix)
analytic=np.zeros_like(H_OFFSET)
for position,matrix in hopping.items():
    analytic[position]=matrix
fourier=H_OFFSET+np.einsum('xyjab,j->xyab',H_BASIS,params)
fourier_error=float(np.max(abs(analytic-fourier)))
assert fourier_error<2e-14

report=certificate(params)
assert report['W_cert']<=.175
assert report['direct_cert']>=3
assert report['indirect_cert']>=3
assert report['g_star']>0
for topology in report['topology']:
    assert abs(topology['chern']+1)<2e-8
    assert abs(topology['degree']-1)<2e-8
    assert topology['max_plaquette_phase']<np.pi/2
    assert topology['min_link']>0
    assert topology['homotopy_radius']<topology['min_radius']

active=np.flatnonzero(params[1:])+1
problem=Problem(161,[(mass,anisotropy) for mass in [-.05,.05] for anisotropy in [-.06,.06]])
worst_width=0.
smallest_gap=np.inf
for signs in itertools.product([-1,1],repeat=len(active)):
    manufactured=params.copy()
    manufactured[active]*=1+.004*np.array(signs)
    width,direct,indirect=problem.metrics(manufactured)
    worst_width=max(worst_width,width)
    smallest_gap=min(smallest_gap,direct,indirect)
assert worst_width<=report['W_cert']
assert smallest_gap>=min(report['direct_cert'],report['indirect_cert'])
report['validation']={'analytic_fourier_max_error':fourier_error,'manufacturing_box_corners_tested':4*2**len(active),'corner_sampled_max_bandwidth':worst_width,'corner_sampled_min_gap':smallest_gap}
Path('validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
