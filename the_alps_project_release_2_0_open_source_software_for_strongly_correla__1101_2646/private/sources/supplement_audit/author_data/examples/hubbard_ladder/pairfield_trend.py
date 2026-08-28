import sys, os
from numpy import *
import matplotlib.pyplot as plt
from copy import deepcopy
from glob import glob

import pyalps
from pyalps.plot import plot as aplot

resfiles = pyalps.getResultFiles(dirname='results', prefix='sim')

refdecay_l = 7
refdecay_slope = -1.
refdecay_bond = 3600

def propsort(data,pn):
    '''sort datasets in data using the property named pn as key'''
    data.sort(cmp=lambda x,y:cmp(x.props[pn],y.props[pn]))

def select(ll, which):
    for lli in ll:
        if lli.props['observable'] == which:
            return lli

def argsort_corr(x):
    if len(x.shape) > 1:
        x = x.reshape( x.shape[0], prod(x.shape[1:]) )
        keys = []
        for i in reversed(range(x.shape[1])):
            keys.append(x[:,i])
        ind=lexsort(keys)
    else:
        ind = argsort(x)
    return ind

def sum_DataSets (data, what):
    d = []
    sign = []
    for meas in what:
        if meas[0]=='-':
            d.append(select(data, meas[1:]))
            sign.append(-1.)
        else:
            d.append(select(data, meas))
            sign.append(1.)
    
    ret = pyalps.DataSet()
    ret.props = deepcopy(d[0].props)
    
    x = deepcopy(d[0].x)
    ret.x = x[argsort_corr(x)]
    
    ret.y = zeros(len(d[0].y[0]))
    for di,s in zip(d,sign):
        ind = argsort_corr(di.x)
        print 'Test equal x:', all(abs(ret.x-di.x[ind]) < 1e-8)
        ret.y += s*array(di.y[0][ind])
    return ret



data = pyalps.loadEigenstateMeasurements(resfiles, ['pair field 1','pair field 2', 'pair field 3', 'pair field 4'])
groupdata = pyalps.groupSets(pyalps.flatten(data), for_each=['MAXSTATES'])

## number of entries around the middle used to average the finite size oscillations
shifts = range(-5, 6)
## 2d coordinate for j=i+delta and l=k+delta in cdag_up(i)*cdag_down(j)*c_up(k)*c_down(l) (and similar terms).
delta = (0,1)

sets = []
for sim in groupdata:
    common_props = pyalps.dict_intersect([d.props for d in pyalps.flatten(sim)])
    print 'Computing L = %d, M = %d.' % (common_props['L'], common_props['MAXSTATES'])
    
    L  = int(common_props['L'])
    n1 = int(common_props['Nup_total'])
    n2 = int(common_props['Ndown_total'])
    n  = n1+n2
    
    
    corr = sum_DataSets(sim, what=['pair field 1','-pair field 2', '-pair field 3', 'pair field 4'])
    
    ## distance between operators in units of ladder rungs. from 1 to maximum distance where averaging is still possible
    l = range(1, int(L-1-2*max(shifts)), 1)
    res = []
    for li in l:
        
        ix = empty( (len(shifts), 2, 2), dtype=int )
        sel = []
        for i, shift in enumerate(shifts):
            m = empty((4, 2), dtype=int)
            m[0, :] = [ L/2. - li/2. + shift, 0 ]
            m[1, :] = m[0, :] + array(delta)
            m[2, :] = [ m[0,0]+li, 0 ]
            m[3, :] = m[2, :] + array(delta)
            
            ii = where( all(corr.x==m, axis=(1,2)) )[0]
            if len(ii) != 1:
                print 'Problem while selecting positions.', m
            sel.append( ii[0] )
        sel = array(sel)
        
        tmp = sum(corr.y[sel]) / len(sel)
        res.append(tmp)
        
    q = pyalps.DataSet()
    q.props = deepcopy(corr.props)
    q.props['observable'] = 'pair field average'
    q.props['label'] = '$M = %d$' % common_props['MAXSTATES']
    q.x = array(l)
    q.y = array(res)
    sets.append(q)

## plot reference lines
refs = []
for d in sets:
    if d.props['MAXSTATES'] != refdecay_bond:
        continue
    
    match_y = d.y[d.x == refdecay_l]
    xgrid = linspace(min(d.x), max(d.x))
    
    q = pyalps.DataSet()
    q.x = xgrid
    a = match_y / refdecay_l**(refdecay_slope)
    q.y = a * xgrid**refdecay_slope
    
    q.props['line']  = '--'
    refs.append(q)
    

sets.sort(key=lambda d: d.props['MAXSTATES'], reverse=True)

plt.figure(tight_layout=True)
aplot(sets)
aplot(refs)

plt.xscale('log')
plt.yscale('log')

plt.legend(loc='lower left', frameon=False)

plt.xlabel('$l$')
plt.ylabel('$D(l)$')

plt.savefig('fig_hubbard_pairfield_decay_trend.pdf')
plt.show()
