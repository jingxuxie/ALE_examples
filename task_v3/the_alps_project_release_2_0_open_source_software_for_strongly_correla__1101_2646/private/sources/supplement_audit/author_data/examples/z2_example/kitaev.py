import pyalps
import numpy as np
import matplotlib.pyplot as plt
from pyalps.plot import plot
from copy import deepcopy
 
# This sets up the Kitaev wire model of A Yu Kitaev, Phys.-Usp. 44, 131 (2001)
# We set the superconducting gap, D=1, and leave t=1. For these parameters,
# the system is in a topological phase for mu < 2, and in a trivial phase
# at mu > 2; both phases are superconducting.
# At mu=2, there is a c=1/2 critical point (free Majorana fermion).
# Since simulations are performed for open boundary conditions, we observe that
# there is a two-fold ground state degeneracy, with one state being even and
# the other odd parity, in the topological phase. The splitting between the two
# ground state is exponentially small in the system size.

# Set up parameters.
parms = []
for L in [24]:
 for P in [0,1]:
  for mu in np.linspace(0,4,11):
   parms.append({ 
        'LATTICE'                   : "open chain lattice", 
        'L'                         : L,
        'MODEL_LIBRARY'             : "tsc.xml",
        'MODEL'                     : "tsc",
        'CONSERVED_QUANTUMNUMBERS'  : 'P',
        'symmetry'                  : 'Z2',
        'P_total'                   : P,
        'D'                         : 1,
        'mu'                        : mu,
        'SWEEPS'                    : 4,
        'MAXSTATES'                 : 20,
        'NUMBER_EIGENVALUES'        : 2,
       })

#write the input file and run the simulation
input_file = pyalps.writeInputFiles('parm_tsc',parms)
res = pyalps.runApplication('mps_optim',input_file,writexml=True)

data_ = pyalps.loadEigenstateMeasurements(pyalps.getResultFiles(prefix='parm_tsc'))

# calculate energy gaps at every point
data = []
for ds in pyalps.flatten(data_):
    for n in [0,1]:
        ds2 = deepcopy(ds)
        ds2.x = [ds.x[n]]
        ds2.y = [ds.y[n]]
        ds2.props['n'] = n
        data.append(ds2)

groups = pyalps.groupSets(pyalps.flatten(data), ['L', 'mu'])
for grp in groups:
    emin = min([ds.y[0] for ds in grp])
    for ds in grp:
        ds.y -= emin

p = pyalps.collectXY(data, 'mu', 'Energy', ['P_total', 'n'])
plot(p)

plt.legend(loc=0, frameon=False)

plt.show()
