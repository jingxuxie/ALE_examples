import json
import numpy as np
from pathlib import Path

specs = [
    ('large_even',64,14,24,'even',1.5,-.035,.05,0.,1.5),
    ('large_odd',64,14,24,'odd',1.2,-.025,.05,0.,1.2),
    ('ordered_odd',32,8,12,'odd',.8,-.12,.18,0.,.4),
    ('large_field',64,12,20,'any',1.1,-.075,.1,.0008,1.1),
    ('critical_field',48,14,24,'any',1.4,-.03,.05,.001,1.4),
    ('profile',64,10,16,'any',1.,-.045,.13,.0006,1.),
    ('deep',48,14,16,'even',1.85,-.2,.05,0.,1.5),
    ('weak_links',40,10,16,'any',.9,-.085,.12,.001,.45),
]
for index, (name,length,dim,cap,sector,omega,mass,quartic,field,coupling) in enumerate(specs):
    request = dict(version=1,case_id=name,seed=300+index,n_sites=length,local_dim=dim,bond_cap=cap,sector=sector,budget_seconds=6.,wall_seconds=30.)
    for key,value in [('omega',omega),('mass2',mass),('lambda4',quartic),('field',field)]:
        request[key] = [value]*length
    request['coupling'] = [coupling]*(length-1)
    coordinate = np.linspace(0,1,length)
    if name in ('large_field','weak_links'):
        request['field'] = (field*np.cos(2*np.pi*coordinate)).tolist()
    if name == 'profile':
        request['omega'] = (1.+.3*np.sin(2*np.pi*coordinate)).tolist()
        request['mass2'] = (-.06+.03*np.cos(2*np.pi*coordinate)).tolist()
        request['lambda4'] = (.1+.04*np.sin(3*np.pi*coordinate)).tolist()
        request['field'] = (.0006*np.cos(3*np.pi*coordinate)).tolist()
        request['coupling'] = (.8+.6*np.sin(2*np.pi*coordinate[:-1])).tolist()
    if name == 'weak_links':
        request['coupling'] = [.06 if site in (8,19,28) else .6 for site in range(length-1)]
    Path('experiments/'+name+'.json').write_text(json.dumps(request))
