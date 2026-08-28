import sys, os
from numpy import *
import matplotlib.pyplot as plt
from copy import deepcopy
from glob import glob

import pyalps
from pyalps.plot import plot as aplot
from matplotlib.ticker import ScalarFormatter, MultipleLocator

class FixedOrderFormatter(ScalarFormatter):
    """Formats axis ticks using scientific notation with a constant order of 
    magnitude"""
    def __init__(self, order_of_mag=0, useOffset=True, useMathText=False):
        self._order_of_mag = order_of_mag
        ScalarFormatter.__init__(self, useOffset=useOffset, 
                                 useMathText=useMathText)
    def _set_orderOfMagnitude(self, range):
        """Over-riding this to avoid having orderOfMagnitude reset elsewhere"""
        self.orderOfMagnitude = self._order_of_mag


resfiles = pyalps.getResultFiles(dirname='results', prefix='sim')
data = pyalps.loadEigenstateMeasurements(resfiles, ['Energy', 'EnergyVariance'])
en_vs_variance = pyalps.ResultsToXY(data, 'EnergyVariance', 'Energy', foreach=["L", "Nup_total", "Ndown_total"])
print en_vs_variance

extrap = []
fits   = []
for d in en_vs_variance:
    ## energy per particle
    d.y /= (d.props['Nup_total'] + d.props['Ndown_total'])
    
    ## linear fit for en vs. variance
    coeff = polyfit(d.x, d.y, deg=1)
    print 'extrapolation: ', coeff[-1]
    
    ## single point
    dd = pyalps.DataSet()
    dd.props = deepcopy(d.props)
    dd.props['MAXSTATES'] = 'inf'
    dd.x = array([0])
    dd.y = array([ coeff[-1] ])
    dd.props['label'] = 'energy $\\rightarrow %.3f$' % coeff[-1]
    extrap.append(dd)
    
    ## fit line
    dd = pyalps.DataSet()
    dd.props = deepcopy(d.props)
    dd.props['line']  = '-'
    dd.props['color'] = 'g'
    dd.props['label'] = ''
    dd.x = linspace(0, max(d.x))
    dd.y = polyval(coeff, dd.x)
    fits.append(dd)

## formatting
for d in en_vs_variance:
    d.props['line']   = 'scatter'
    d.props['marker'] = 'o'
    d.props['color']  = 'b'
    d.props['label']  = ''


for d in en_vs_variance:
    d.y -= extrap[0].y
for d in fits:
    d.y -= extrap[0].y

plt.figure(tight_layout=True)
aplot(fits)
aplot(en_vs_variance)

plt.xlim(xmin=0)
plt.ylim(ymin=0)

plt.xlabel(r'$\mathrm{Var}[\hat H]$', labelpad=8)
plt.ylabel('energy difference')

# xmajorLocator = MultipleLocator(0.05)
# xminorLocator = MultipleLocator(0.025)
# plt.gca().xaxis.set_major_locator( xmajorLocator )
# plt.gca().xaxis.set_minor_locator( xminorLocator )
#
# ymajorFormatter = FixedOrderFormatter(order_of_mag=-5)
# plt.gca().yaxis.set_major_formatter( ymajorFormatter )


plt.savefig('fig_hubbard_energy_extrapolation.pdf')
plt.show()
