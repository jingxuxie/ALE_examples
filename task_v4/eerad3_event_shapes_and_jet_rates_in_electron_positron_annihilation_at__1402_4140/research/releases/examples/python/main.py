#! env python3

import os, sys

path = os.path.abspath("../../pyext/")
sys.path.append(path)
from pyrad import EERAD3
from eerad3hist.filetools import writeFile

if __name__ == "__main__":
    # Setup the interface to EERAD3.
    eerad3 = EERAD3()

    # Write a run card
    runcardName = 'LO.input'
    with open(runcardName, 'w') as runcard:
        print("process    = 21",   file=runcard)
        print("njets      = 3",    file=runcard)
        print("channel    = LO",   file=runcard)
        print("warmup     = 5",    file=runcard)
        print("production = 5",    file=runcard)
        print("shots      = 100k", file=runcard)

    # Intialise EERAD3 on a seed number and the run card above
    eerad3.init(0, runcardName)

    # Calculate the cross section.
    xsec, err = eerad3.cross()

    # Fetch histograms and print names of all histograms.
    hists = eerad3.getHists()
    print("\n Hists:")
    for h in hists: print('',h)

    # For thrust print histogram.
    print("\n Thrust histogram with id",hists['T1']['id'])
    for i in range(hists['T1']['nBins']):
        xLo = hists['T1']['bins'][i]
        xHi = hists['T1']['bins'][i+1]
        wt  = hists['T1']['wt'][i]
        wt2 = hists['T1']['wt2'][i]
        print(' {0:.6E} {1:.6E} {2:.6E} {3:.6E}'.format(xLo,xHi,wt,wt2))

    # Print thrust histogram to file.
    writeFile(hists['T1'], 'T1.dat')
