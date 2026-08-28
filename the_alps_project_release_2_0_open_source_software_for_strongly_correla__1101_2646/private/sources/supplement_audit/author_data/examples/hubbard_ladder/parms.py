import pyalps

parms = []
for M in [800, 1200, 1600, 2000, 2800, 3200, 3600]:
  p = dict()
  p['SWEEPS'    ] = 16
  p['MAXSTATES' ] = M
  p['init_state'] = 'thin'
  p['LATTICE'   ] = 'open ladder'
  p['L'         ] = 96
  p['MODEL_LIBRARY'] = 'mymodel.xml'
  p['MODEL'    ] = 'fermion Hubbard'
  p['t'        ] = 1
  p['U'        ] = 8
  p['CONSERVED_QUANTUMNUMBERS'] = 'Nup,Ndown'
  p['Nup_total'               ] = 84
  p['Ndown_total'             ] = 84
  p['MEASURE[EnergyVariance]'] = 1
  p['MEASURE_HALF_CORRELATIONS[pair field 1]'] = 'field_du:fielddag_ud'
  p['MEASURE_HALF_CORRELATIONS[pair field 2]'] = 'field_du:fielddag_du'
  p['MEASURE_HALF_CORRELATIONS[pair field 3]'] = 'field_ud:fielddag_ud'
  p['MEASURE_HALF_CORRELATIONS[pair field 4]'] = 'field_ud:fielddag_du'
  p['storagedir'] = 'storage'
  parms.append(p)

## write the input file and run the simulation
infiles=pyalps.writeInputFiles('sim',parms)
res=pyalps.runApplication('mps_optim',infiles)

