# ****************************************************************************
# 
# ALPS Project: Algorithms and Libraries for Physics Simulations
# 
# ALPS Libraries
# 
# Copyright (C) 2014 by Michele Dolfi <dolfim@phys.ethz.ch>
# 
# This software is part of the ALPS libraries, published under the ALPS
# Library License; you can use, redistribute it and/or modify it under
# the terms of the license, either version 1 or (at your option) any later
# version.
#  
# You should have received a copy of the ALPS Library License along with
# the ALPS Libraries; see the file LICENSE.txt. If not, the license is also
# available from http://alps.comp-phys.org/.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT 
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE 
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE, 
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.
# 
# ****************************************************************************

import os
import pyalps
import matplotlib.pyplot as plt
from pyalps.plot import plot as aplot
import numpy as np
from collections import OrderedDict
from copy import deepcopy
import scipy.special


basename = 'sim'

## common model parameters
model = OrderedDict()
model['LATTICE'] = 'open chain lattice'
model['L'      ] = 50
model['MODEL'                   ] = 'spin'
model['CONSERVED_QUANTUMNUMBERS'] = 'Sz'
model['Sz_total'                ] = 0
model['Jxy'                     ] = 1.
model['MAXSTATES'] = 40
model['MEASURE_LOCAL[Local Magnetization]'] = 'Sz'

## prepare the input parameters
parms = []
for tau in [20.0]:
        ns = 500
        dt = tau / ns
        p = deepcopy(model)
        p['init_state'      ] = 'local_quantumnumbers'
        p['initial_local_S' ] = ','.join(['0.5']*50)
        p['initial_local_Sz'] = ','.join(['-0.5']*25 + ['0.5']*25)
        p['te_order' ] = 'second'
        p['DT'       ] = dt
        p['TIMESTEPS'] = ns
        p['tau'      ] = tau # not used in the simulation, but useful in the evaluation below
        p['ALWAYS_MEASURE'] = 'Local Magnetization'
        p['chkp_each'     ] = ns
        p['measure_each'  ] = 5
        
        parms.append(p)


resfiles = pyalps.getResultFiles(prefix=basename)
if len(resfiles) == 0: ## run simulation only if needed
    ## write the input file and run the simulation
    input_file = pyalps.writeInputFiles(basename, parms)
    res        = pyalps.runApplication('mps_evolve', input_file)
    resfiles   = pyalps.getResultFiles(prefix=basename)

## simulation results
data = pyalps.loadIterationMeasurements(resfiles, what=['Local Magnetization'])

numeric_magnetization = []
for d in pyalps.flatten(data):
    L = d.props['L']
    for loc in range(1, 11):
        q = deepcopy(d)
        q.x = [0]
        q.y = np.array([ q.y[0][L/2-loc] ])
        q.props['loc'] = loc
        numeric_magnetization.append(q)

mag_vs_time = pyalps.collectXY(numeric_magnetization, x='Time', y='Local Magnetization', foreach=['loc'])
for d in mag_vs_time:
    d.x = (d.x + 1.) * d.props['dt'] # convert time index to real time
    # d.props['label'] = 'Numerical at n='+str(d.props['loc'])
    # d.props['label'] = '$\\langle \psi(t) | S_z(L/2 - %d) | \psi(t) \\rangle$' % d.props['loc']
    d.props['label'] = '$M(%d, t)$' % d.props['loc']

pyalps.CycleMarkers(mag_vs_time, foreach=['loc'])
pyalps.CycleColors(mag_vs_time, foreach=['loc'])
for d in mag_vs_time:
    d.props['line'] = d.props['line'].replace('-', '')
    d.props['fillmarkers'] = False

## exact solution
tgrid = np.linspace(0, 20, 500)
exact_magnetization = []
for d in mag_vs_time:
    dd = deepcopy(d)
    # dd.props['label'] = 'Exact at n='+str(dd.props['loc'])
    dd.props['label'] = ''
    dd.props['line'] = '-'
    
    n = dd.props['loc']
    dd.x = tgrid
    dd.y = np.zeros((len(tgrid),))
    for i in range(1-n,n):
        dd.y -= 0.5 * scipy.special.jn(i, dd.x)**2
    
    exact_magnetization.append(dd)


plt.figure(tight_layout=True)
aplot(mag_vs_time)
aplot(exact_magnetization)
plt.xlabel('$t$')
plt.ylabel('$M(n, t)$')
plt.ylim(-0.5,0)
# plt.legend(loc='best', frameon=False)

plt.savefig('fig_domain_wall_' + basename + '.pdf')

plt.show()
