import os
from glob import glob
import pyalps
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from pyalps.plot import plot as aplot
from matplotlib.ticker import FormatStrFormatter, MultipleLocator


resfiles = pyalps.getResultFiles(dirname='results', prefix='sim')

e0_extrap = -0.725768711609 # for t=1.0, L=96, n=0.875

## load iteration history
iterations = pyalps.loadIterationMeasurements(resfiles, what=['Energy','TruncatedWeight'])
for d in pyalps.flatten(iterations): d.props['iteration'] = int(d.props['iteration'])

energy_iteration = pyalps.collectXY(pyalps.flatten(iterations), 'iteration', 'Energy', foreach=['L', 'MAXSTATES'])
for d in energy_iteration:
    d.x = np.linspace(0, d.props['nsweeps'], len(d.y), endpoint=False) + 1 # renormalized x-axis
    d.y = d.y / (d.props['Nup_total']+d.props['Ndown_total']) - e0_extrap # energy per particle - extrapolated value
    d.props['label'] = '$L = %d$, $M = %d$'% (d.props['L'], d.props['MAXSTATES'])
    d.props['line'] = '-'


for d in pyalps.flatten(iterations):
    if d.props['observable'] == 'TruncatedWeight':
        d.y = [sum(d.y)]
truncation_iteration = pyalps.collectXY(pyalps.flatten(iterations), 'iteration', 'TruncatedWeight', foreach=['L', 'MAXSTATES'])
for d in truncation_iteration:
    d.x = np.linspace(0, d.props['nsweeps'], len(d.y), endpoint=False) + 1 # renormalized x-axis
    d.props['label'] = '$L = %d$, $M = %d$'% (d.props['L'], d.props['MAXSTATES'])

energy_iteration.sort(key=lambda d: (d.props['L'], d.props['MAXSTATES']))
truncation_iteration.sort(key=lambda d: (d.props['L'], d.props['MAXSTATES']))
pyalps.CycleColors([energy_iteration, truncation_iteration], ['L', 'MAXSTATES'])

pyalps.CycleMarkers(truncation_iteration, ['L', 'MAXSTATES'])
for d in truncation_iteration: d.props['line'] = d.props['marker']


xmajorFormatter = FormatStrFormatter(fmt='%d')
xmajorLocator   = MultipleLocator(2)
xminorLocator   = MultipleLocator(1)


plt.figure(tight_layout=True)
ax1 = plt.subplot()
aplot(energy_iteration)
plt.yscale('log')
plt.ylabel('energy difference')

ax2 = ax1.twinx()
pyalps.plot.plot(truncation_iteration)
plt.yscale('log')
plt.xlim(1,16)
plt.ylabel('truncation error')

ax1.set_xlabel('sweep')
ax1.xaxis.set_major_formatter( xmajorFormatter )
ax1.xaxis.set_major_locator  ( xmajorLocator )
ax1.xaxis.set_minor_locator  ( xminorLocator )

plt.savefig('fig_hubbard_iterations.pdf')


plt.show()
