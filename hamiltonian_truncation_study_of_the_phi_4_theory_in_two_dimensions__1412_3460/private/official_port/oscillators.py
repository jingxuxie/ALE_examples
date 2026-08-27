######################################################
# 
# Fock space Hamiltonian truncation for phi^4 theory in 2 dimensions
# Authors: Slava Rychkov (slava.rychkov@lpt.ens.fr) and Lorenzo Vitale (lorenzo.vitale@epfl.ch)
# December 2014
#
######################################################

import scipy
from scipy import pi, sqrt, product
from operator import attrgetter
from statefuncs import omega, State, NotInBasis

tol = 0.0001

class NormalOrderedOperator():
    """ abstract class for normal ordered operator """
    def __init__(self,clist,dlist,L,m,extracoeff=1):
        self.clist=clist
        self.dlist=dlist
        self.L=L
        self.m=m
        self.coeff = extracoeff/product([sqrt(2.*L*omega(n,L,m)) for n in clist+dlist])
        self.deltaE = sum([omega(n,L,m) for n in clist]) - sum([omega(n,L,m) for n in dlist])
        
    def __repr__(self):
        return str(self.clist)+" "+str(self.dlist) 
    
    def _transformState(self, state0):        
        state = State(state0.occs[:], state0.nmax, fast=True)
        n = 1.
        for i in self.dlist:
            if state[i] == 0:
                return(0,None)
            n *= state[i]
            state[i] -= 1
        for i in self.clist:
            n *= state[i]+1
            state[i] += 1
        return (n, state)

    def apply(self, basis, i, lookupbasis=None):
        """ Takes a state index in basis, returns another state index (if it
        belongs to the lookupbasis) and a proportionality coefficient. Otherwise raises NotInBasis.
        lookupbasis can be different from basis, but it's assumed that they have the same nmax"""
        if lookupbasis == None:
            lookupbasis = basis
        if self.deltaE+basis[i].energy < 0.-tol or self.deltaE+basis[i].energy > lookupbasis.Emax+tol:
            # The trasformed element surely does not belong to the basis if E>Emax or E<0
            raise NotInBasis()
        n, newstate = self._transformState(basis[i])
        if n==0:
            return (0, None)
        m, j = lookupbasis.lookup(newstate)
        c = 1.
        if basis[i].isParityEigenstate():
            c = 1/sqrt(2.)
            # Required for state normalization
        return (m*c*sqrt(n)*self.coeff, j)
