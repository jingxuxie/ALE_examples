######################################################
# 
# Fock space Hamiltonian truncation for phi^4 theory in 2 dimensions
# Authors: Slava Rychkov (slava.rychkov@lpt.ens.fr) and Lorenzo Vitale (lorenzo.vitale@epfl.ch)
# December 2014
#
######################################################

import phi1234
import sys
import scipy

def main(argv):
    
    if len(argv) < 3:
        print("python genMatrix.py <L> <Emax>")
        sys.exit(-1)
    
    L = float(argv[1])
    Emax = float(argv[2])
    
    m = 1.

    a = phi1234.Phi1234()

    a.buildFullBasis(k=1, Emax=Emax, L=L, m=m)
    a.buildFullBasis(k=-1, Emax=Emax, L=L, m=m)

    print("K=1 basis size :", a.fullBasis[1].size)
    print("K=-1 basis size :", a.fullBasis[-1].size)

    fstr = "Emax="+str(a.fullBasis[1].Emax)+"_L="+str(a.L)

    a.buildMatrix()
    a.saveMatrix(fstr)

if __name__ == "__main__":
    main(sys.argv)
