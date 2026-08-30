#! /usr/bin/python3

# This file is part of the EERAD3 NNLO event generator.
# Copyright (C) 2025 the authors.
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version. See COPYING for details.

import numpy as np
from math import exp,log,sqrt,pi

#=======================================================================
# QCD class for strong coupling etc.
#=======================================================================

class QCD:

    # Constructor.
    def __init__(self,mu,aSmu,NfIn=5,order=2):
        # Constants
        self.NC = 3.
        self.CA = self.NC
        self.CF = (self.NC**2-1.)/2./self.NC
        self.TR = 1./2.
        self.Nf = NfIn
        self.zeta2 = 1.6449340668482264365
        self.zeta3 = 1.2020569031595942854
        self.zeta4 = 1.0823232337111381915
        self.zeta5 = 1.0369277551433699263

        # Set scale, alphaS value, and order.
        self.mu    = mu
        self.aSmu  = aSmu
        self.order = order

        # Save beta-function coefficients.
        self.b0 = self.beta(0)
        self.b1 = self.beta(1)
        self.b2 = self.beta(2)

        # Set up running alphaS.
        self.l0  = 2.*pi/self.b0/self.aSmu
        self.lam = []
        for iorder in range(self.order+1):
            self.lam.append(exp(-self.l0/2.)*self.mu)
            aS0 = self.alphaS(self.mu,iorder)
            # Poor-man's version of a fixed-point algorithm.
            for i in range(0,50):
                if abs(1-aS0/self.aSmu) < 1e-14: break
                self.lam[iorder] *= (self.aSmu/aS0)**4
                aS0 = self.alphaS(self.mu,iorder)

    # Coefficients of the beta function [hep-ph:9703284].
    def beta(self,n):
        if n==0:
            return (11. - 2./3.*self.Nf)/2.
        if n==1:
            return (102. - 38./3.*self.Nf)/4.
        if n==2:
            return (2857./2. - 5033./18.*self.Nf \
                    + 325./54.*self.Nf**2)/8.
        if n==3:
            return ((149753./6. + 3564.*self.zeta3) \
                    - (1078361./162. + 6508./27.*self.zeta3)*self.Nf \
                    + (50065./162. + 6472./81.*self.zeta3)*self.Nf**2 \
                    + 1093./729.*self.Nf**3)/16.
        return 0.

    # Coefficients of the quark anomalous dimension [hep-ph:9703284].
    def gamma(self,n):
        if n==0:
            return 2.
        if n==1:
            return (202./3. - 20./9.*self.Nf)/4.
        if n==2:
            return (1249. \
                    + (-2216./27. - 160./3.*self.zeta3)*self.Nf \
                    - 140./81.*self.Nf**2)/8.
        if n==3:
            return (4603055./162. + 135680./27.*self.zeta3 - 8800.*self.zeta5 \
                    + (-91723./27. -34192./9.*self.zeta3 + 880.*self.zeta4 \
                       + 18400./9.*self.zeta5)*self.Nf \
                    + (5242./243. + 800./9.*self.zeta3 \
                       - 160./3.*self.zeta4)*self.Nf**2 \
                    + (-332./243. + 64./27.*self.zeta3)*self.Nf**3
                    )/16.
        return 0.

    # Running quark mass in the MSbar scheme.
    def runMqMSbar(self,mQ,muR):
        # Calculate strong couplings.
        asQ = self.alphaS(mQ,0)
        asR = self.alphaS(muR,0)

        # Shorthands.
        g0 = self.gamma(0)
        g1 = self.gamma(1)
        g2 = self.gamma(2)
        g3 = self.gamma(3)
        b0 = self.beta(0)
        b1 = self.beta(1)
        b2 = self.beta(2)
        b3 = self.beta(3)
        
        # Calculate running mass.
        e = + g0/b0*log(asR/asQ) \
            + (-b1*g0+b0*g1)/b0**2*(asR-asQ)/(2.*pi) \
            + (b1**2*g0-b0*b2*g0 \
               - b0*b1*g1+b0**2*g2)/b0**3*(asR**2-asQ**2)/(2.*pi)**2/2. \
            + (- b1**3*g0 \
               + 2.*b0*b1*b2*g0 \
               - b0**2*b3*g0 \
               + b0*b1**2*g1 \
               - b0**2*b2*g1 \
               - b0**2*b1*g2 \
               + b0**3*g3 \
               )/b0**4*(asR**3-asQ**3)/(2.*pi)**3/3.
        return mQ*np.exp(e)

    # Running strong coupling.
    def alphaS(self,mu,iorder=0):
        # Set scale.
        dl  = 2.*log(mu/self.lam[iorder])
        dll = log(dl)

        # Calculate running alphaS.
        aS = 2.*pi/self.b0/dl
        if iorder >= 1:
            aS += -2.*pi/self.b0/dl * self.b1/self.b0/self.b0*dll/dl
        if iorder >= 2:
            aS += 2.*pi/self.b0/dl \
                * 1./self.b0**2/dl**2 \
                * ((self.b1/self.b0)**2*(dll**2-dll-1.) + self.b2/self.b0)
        return aS

#=======================================================================
# Class containing inclusive cross sections and decay widths.
#=======================================================================

class Distribution:

    # Constructor.
    # Note: implicitly uses (alphaMZ,MW,MZ) scheme.
    def __init__(self, runcard, expandNorm=False, withBR=False):
        # Read runcard and print settings.
        params = self.readRuncard(runcard)
        self.printSettings(params)
        
        # Process.
        self.iproc = int(params["process"])

        # Masses.
        self.Mb = float(params["MASS[b]"])
        self.Mt = float(params["MASS[t]"])
        self.MZ = float(params["MASS[Z]"])
        self.MW = float(params["MASS[W]"])

        # Gmu EW input scheme.
        self.GF       = float(params["GF"])
        self.alphaEM  = sqrt(2.)*self.GF*self.MW**2 \
            *(1.-self.MW**2/self.MZ**2)/pi
        print(" EW input scheme: GF\n",
              "1/alphaEM =",1./self.alphaEM,"\n")

        # Strong coupling at MZ.
        self.alphaSMZ = float(params["aS[MZ]"])

        # Scales.
        self.Ecm       = float(params["sqrts"])
        self.s         = self.Ecm**2
        self.renscale  = float(params["muR"])
        self.renscale2 = self.renscale**2

        # Multiplicity.
        self.njets = int(params["njets"])

        # Histogram files.
        self.histograms = params["histograms"]

        # Whether to expand normalisation.
        self.expandNorm = expandNorm

        # Whether to include branching ratio.
        self.withBR = withBR

        # Setup QCD class.
        self.qcd = QCD(self.MZ, self.alphaSMZ)
        print(" QCD coupling:\n alphaS(ECM) = {0} | {1} | {2}".format(
            self.qcd.alphaS(self.Ecm,0),
            self.qcd.alphaS(self.Ecm,1),
            self.qcd.alphaS(self.Ecm,2)))

        # Print Born-level cross section/width.
        print("\n Process-dependent settings:")
        if self.iproc == 1:
            print(" sigma0(e+e- -> 2j) = {0} mb\n".format(
                  self.sigEpemqq(self.s,self.renscale2,0)*0.389379))
            print(" KNLO(H -> bb)   = {0}".format(
                  1.+self.VZqq(self.s,self.renscale2,1)))
            print(" KNNLO(H -> bb)  = {0} \n".format(
                  1.+self.VZqq(self.s,self.renscale2,1)
                  +self.VZqq(self.s,self.renscale2,2)))
        if self.iproc == 21:
            print(" mb(ECM)         = {0} GeV".format(
                self.qcd.runMqMSbar(self.Mb,self.Ecm)))
            print(" Gamma0(H -> bb) = {0} GeV".format(
                  self.GammaHbb(self.s,self.renscale2,0)))
            print(" KNLO(H -> bb)   = {0}".format(
                  1.+self.VHbb(self.s,self.renscale2,1)))
            print(" KNNLO(H -> bb)  = {0} \n".format(
                  1.+self.VHbb(self.s,self.renscale2,1)
                  +self.VHbb(self.s,self.renscale2,2)))
        if self.iproc == 22:
            print(" mt(ECM)         = {0} GeV".format(
                self.qcd.runMqMSbar(self.Mt,self.Ecm)))
            print(" Gamma0(H -> gg) = {0} GeV".format(
                  self.GammaHgg(self.s,self.renscale2,0)))
            print(" KNLO(H -> gg)   = {0}".format(
                  1.+self.VHgg(self.s,self.renscale2,1)))
            print(" KNNLO(H -> gg)  = {0} \n".format(
                  1.+self.VHgg(self.s,self.renscale2,1)
                  +self.VHgg(self.s,self.renscale2,2)))

        # Print Higgs-decay branching ratios.
        if self.withBR and self.iproc >= 20:
            print(" Branching ratios")
            print(" order |  0       |  1       |  2       ")
            print(" ------+----------+----------+----------")
            print(" H->bb |  {0:6.4f}  |  {1:6.4f}  |  {2:6.4f}".format(
                self.branchingRatio(21,self.s,self.s,0),
                self.branchingRatio(21,self.s,self.s,1),
                self.branchingRatio(21,self.s,self.s,2)))
            print(" ------+----------+----------+----------")
            print(" H->gg |  {0:6.4f}  |  {1:6.4f}  |  {2:6.4f}".format(
                self.branchingRatio(22,self.s,self.s,0),
                self.branchingRatio(22,self.s,self.s,1),
                self.branchingRatio(22,self.s,self.s,2)),"\n")

    # Read runcard.
    def readRuncard(self,runcard):
        # Read input file and parse settings.
        settings = {}
        with open(runcard,'r') as f:
            histmode = False
            histlist = []
            for line in f:
                # Skip empty lines, comments, etc.
                if len(line.strip()) == 0 or line.strip()[0] in ["!","#"]:
                    continue
                # Switch to histmode when encountering HISTOGRAMS block.
                if "HISTOGRAMS" in line.strip():
                    histmode = True
                    continue
                if "END HISTOGRAMS" in line.strip():
                    histmode = True
                    continue
                # Read histograms.
                if histmode: histlist.append(line.split())
                # Parse input, assign settings.
                else:
                    key, value = line.split("=")
                    settings[key.strip()] = value.strip()
            settings["histograms"] = histlist

        # Check that we have all necessary settings.
        if "MASS[b]" not in settings:
            settings["MASS[b]"] = 4.18
        if "MASS[t]" not in settings:
            settings["MASS[t]"] = 163.136
        if "MASS[Z]" not in settings:
            settings["MASS[Z]"] = 91.2
        if "MASS[W]" not in settings:
            settings["MASS[W]"] = 80.385
        if "aS[MZ]" not in settings:
            settings["aS[MZ]"]  = 0.118
        if "GF" not in settings:
            settings["GF"]      = 1.1664e-5
        if "sqrts" not in settings:
            print(" Error: sqrts must be specified in",filename)
            quit()
        if "njets" not in settings:
            print(" Error: njets must be specified in",filename)
            quit()
        if "muR" not in settings:
            settings["muR"]     = settings["sqrts"]

        # Return settings.
        return settings

    # Print settings.
    def printSettings(self,settings):
        print("\n",
        "********************************************************",
        "\n",
        "*  Settings:                                           *")
        for key in settings:
            if key == "histograms": continue
            print(\
            " *  {0:<7} = {1:<12}                              *"
            .format(key,settings[key]))
        print(\
        " ********************************************************",
        "\n")

    # Corrections to inclusive e+e- -> 2j cross section.
    def VZqq(self,q2,muR2,order):
        # Shorthands.
        CA = self.qcd.CA
        CF = self.qcd.CF
        NF = self.qcd.Nf
        TF = self.qcd.TR
        beta0 = 2.*self.qcd.b0
        beta1 = 4.*self.qcd.b1
        zeta2 = self.qcd.zeta2
        zeta3 = self.qcd.zeta3

        # Calculate strong coupling.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Scale logarithm.
        L = log(q2/muR2)

        # Coefficients from Eq. (5.1) and (5.2) in arXiv:1707.01044.
        r1 = 3*CF
        r2 = CF**2*(-3./2.) + CA*CF*(123./2.-44.*zeta3) \
            - 2*TF*NF*CF*(11.-8.*zeta3)
        if order==1: 
            return (aS/2./pi)*1./2.*r1
        if order==2:
            return (aS/2./pi)**2*1./4.*(r2-r1*beta0*L)
        return 0.

    # Inclusive e+ e- -> 2j cross section up to NNLO.
    def sigEpemqq(self,q2,muR2,order):
        # Leading-order cross section.
        sumeq2 = 0.
        for i in range(1,self.qcd.Nf+1):
            if i % 2 == 0: sumeq2 = sumeq2 + 4./9.
            else: sumeq2 = sumeq2 + 1./9.
        sig0 = 4.*pi*self.alphaEM/3./q2*self.qcd.NC*sumeq2

        # Calculate strong coupling.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Inclusive K-factor.
        R = 1.
        if order>=1:
            R += self.VZqq(q2,muR2,1)
        if order>=2:
            R += self.VZqq(q2,muR2,2)

        return R*sig0

    # Corrections to inclusive H -> bb decay width.
    def VHbb(self,q2,muR2,order):
        # Shorthands.
        CA = self.qcd.CA
        CF = self.qcd.CF
        NF = self.qcd.Nf
        TF = self.qcd.TR
        beta0  = 2.*self.qcd.b0
        beta1  = 4.*self.qcd.b1
        zeta2  = self.qcd.zeta2
        zeta3  = self.qcd.zeta3
        gamma0 = 2.*self.qcd.gamma(0)
        gamma1 = 4.*self.qcd.gamma(1)

        # Calculate strong coupling.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Scale logarithm.
        L = log(q2/muR2)

        # Coefficients from Eq. (4.2) and (4.3) in arXiv:1707.01044.
        r1 = 17*CF
        r2 = CF**2*(691./4.-36.*zeta2-36.*zeta3) \
            + CA*CF*(893./4.-22.*zeta2-62.*zeta3) \
            - 2*TF*NF*CF*(65./2.-4.*zeta2-8.*zeta3)
        if order==1: 
            return (aS/2./pi)*1./2.*(r1-2.*gamma0*L)
        if order==2:
            return (aS/2./pi)**2*1./4.*(r2\
                    - (2.*gamma1+2.*r1*gamma0+r1*beta0)*L\
                    + (2.*gamma0**2+beta0*gamma0)*L**2)
        return 0.

    # Inclusive H -> bb decay width up to NNLO.
    def GammaHbb(self,q2,muR2,order):
        # Running Yukawa coupling.
        runMb  = self.qcd.runMqMSbar(self.Mb,sqrt(muR2))
        yb     = runMb*sqrt(sqrt(2.)*self.GF)

        # Calculate strong coupling.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Calculate LO decay width.
        Gamma0 = self.qcd.NC*yb**2*sqrt(q2)/8./pi

        # Inclusive K-factors.
        R = 1.
        if order>=1:
            R += self.VHbb(q2,muR2,1)
        if order>=2:
            R += self.VHbb(q2,muR2,2)
        return R*Gamma0

    # Corrections to inclusive H -> gg decay width.
    def VHgg(self,q2,muR2,order):
        # Shorthands.
        CA = self.qcd.CA
        CF = self.qcd.CF
        NF = self.qcd.Nf
        TF = self.qcd.TR
        beta0  = 2.*self.qcd.b0
        beta1  = 4.*self.qcd.b1
        zeta2  = self.qcd.zeta2
        zeta3  = self.qcd.zeta3
        gamma0 = 2.*self.qcd.gamma(0)
        gamma1 = 4.*self.qcd.gamma(1)

        # Calculate strong coupling.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Scale logarithm.
        L = log(q2/muR2)

        # Corrections to Wilson coefficient from Eq. (2.5)
        # in arXiv:1707.01044.
        # TODO: would be nice to express c2 in terms of Casimirs.
        runMt = self.qcd.runMqMSbar(self.Mt,sqrt(muR2))
        Lt = log(muR2/runMt**2)
        c1 = 11./3.*CA
        c2 = 2777./18. + 19.*Lt - 2.*TF*NF*(67./6.-16./3.*Lt)

        # Coefficients from Eq. (3.2) and (3.3) in arXiv:1707.01044.
        g1 = 73./3.*CA - 28./3.*TF*NF
        g2 = CA**2*(37631./54.-242./3.*zeta2-110*zeta3) \
            - 2*TF*NF*CA*(6665./27.-88./3.*zeta2+4.*zeta3) \
            - 2*TF*NF*CF*(131./3.-24.*zeta3) \
            + 4*TF**2*NF**2*(508./27.-8./3.*zeta2)
        if order==1: 
            return (aS/2./pi)*1./2.*(g1-2.*beta0*L+2.*c1)
        if order==2:
            return (aS/2./pi)**2*1./4.*(g2 \
                    - (4*beta1+3*beta0*g1)*L + 3*beta0**2*L**2 \
                    + 2*c2 + 2*c1*(g1 - 2*beta0*L) + c1**2)
        return 0.

    # Inclusive H -> gg decay width up to NNLO.
    def GammaHgg(self,q2,muR2,order):
        # Calculate alphaS.
        aS = self.qcd.alphaS(sqrt(muR2),order)

        # Running effective Hgg coupling.
        lambda0 = aS/3./pi*sqrt(sqrt(2)*self.GF)

        # Calculate LO decay width.
        Gamma0 = lambda0**2*sqrt(q2)**3*(self.qcd.NC**2-1.)/64./pi

        # Shorthands.
        CA = self.qcd.CA
        CF = self.qcd.CF
        NC = self.qcd.NC
        TR = self.qcd.TR
        Nf = self.qcd.Nf

        # Inclusive K-factors.
        R = 1.
        if order>=1:
            R += self.VHgg(q2,muR2,1)
        if order>=2:
            R += self.VHgg(q2,muR2,2)
        return R*Gamma0

    # Wrapper for process-dependent corrections to inclusive K-factor.
    def V(self, q2, muR2, order):
        if self.iproc == 1: return self.VZqq(q2, muR2, order)
        if self.iproc == 21: return self.VHbb(q2, muR2, order)
        if self.iproc == 22: return self.VHgg(q2, muR2, order)
        return 0.

    # Wrapper for process-dependent branching ratios.
    def branchingRatio(self, iproc, q2, muR2, order):
        if iproc == 1: return 1.0
        denom = self.GammaHbb(self.s,muR2,order) \
            + self.GammaHgg(self.s,muR2,order)
        num = self.GammaHbb(self.s,muR2,order) \
            if iproc == 21 else self.GammaHgg(self.s,muR2,order)
        return num/denom

    # Differential distribution up to NNLO at scale mu.
    def dist(self, mu, valA, errA, valB, errB, valC, errC, order):
        # Shorthands.
        lmu = log(mu**2/self.s)
        b0  = self.qcd.beta(0)
        b1  = self.qcd.beta(1)
        fac = self.qcd.alphaS(mu, order)/2./pi
        BR  = self.branchingRatio(self.iproc, self.s, mu**2, order) \
            if self.withBR else 1.;

        # Corrections to the inclusive width/cross section.
        VNLO  = self.V(self.s, mu**2, 1) if order>=1 else 0.
        VNNLO = self.V(self.s, mu**2, 2) if order>=2 else 0.

        # If the normalisation is expanded, shift coefficients.
        if self.expandNorm:
            valBnorm = valB - VNLO*valA
            valCnorm = valC - VNLO*valB + (VNLO**2 - VNNLO)*valA
            errBnorm = errB - VNLO*errA
            errCnorm = errC - VNLO*errB + (VNLO**2 - VNNLO)*errA
            valB = valBnorm
            valC = valCnorm
            errB = errBnorm
            errC = errCnorm

        # Calculate the O(as) contribution.
        sigLO = fac*valA
        errLO = fac*errA
        sig = [BR*sigLO]
        err = [BR*errLO]

        # Optionally calculate the O(as^2) contribution.
        if order >= 1:
            sigNLO = sigLO \
                + fac**2*(valB + b0*lmu*valA)
            errNLO = np.sqrt(fac**2*errA**2 \
                + fac**4*(errB + b0*lmu*errA)**2)
            K = 1. if self.expandNorm else 1.+VNLO
            sig.append(BR*sigNLO/K)
            err.append(BR*errNLO/K)

        # Optionally calculate the O(as^3) contribution.
        if order >= 2:
            sigNNLO = sigNLO \
                + fac**3*(valC \
                          + 2.*b0*lmu*valB \
                          + (b0**2*lmu**2 + b1*lmu)*valA)
            errNNLO = np.sqrt(fac**2*errA**2 \
                + fac**4*(errB + 2.*b0*lmu*errA)**2 \
                + fac**6*(errC \
                          + 2.*b0*lmu*errB \
                          + (b0**2*lmu**2 + b1*lmu)*errA)**2)
            K = 1. if self.expandNorm else 1.+VNLO+VNNLO
            sig.append(BR*sigNNLO/K)
            err.append(BR*errNNLO/K)

        # Return the differential cross section and its error.
        return sig,err

    # Top-level function for differential cross section
    # with scale variation mu = k*Ecm with 1/kmu <= k <= kmu.
    def var(self, val, mcerr, order, kmu=2.):
        # For n-jet observables, shift order by (n-3).
        for i in range(3,self.njets): order+=1
        # Perform variation about central scale.
        sig = []
        err = []
        for i,imu in enumerate(range(-10,11)):
            muNow = kmu**(imu/10.)*self.renscale
            if self.njets == 3:
                sigNow, errNow = self.dist(muNow, val[0], mcerr[0],
                              val[1], mcerr[1],
                              val[2], mcerr[2], order)
            elif self.njets == 4:
                dummyA = np.zeros(len(val[0]))
                sigNow, errNow = self.dist(muNow, dummyA, dummyA,
                              val[0], mcerr[0],
                              val[1], mcerr[1], order)
            sig.append(sigNow)
            if imu==0: err = errNow

        # Save central results as well as up and down variation.
        sig = np.array(sig).T
        sigCt = np.array([[v[i][10] for v in sig]
                          for i in range(order+1)])
        sigLo = np.array([[min(v[i]) for v in sig]
                           for i in range(order+1)])
        sigHi = np.array([[max(v[i]) for v in sig]
                          for i in range(order+1)])

        return sigCt, sigLo, sigHi, err

    # Top-level method to calculate differential histograms.
    def calc(self, output, prefix=""):
        for files in self.histograms:
            # Load contribution histograms.
            fileLO   = files[1]
            fileNLO  = files[2] if len(files)>2 else None
            fileNNLO = files[3] if len(files)>3 else None
            order    = 2 if fileNNLO else 1 if fileNLO else 0
            # Tell user what we are doing.
            print(" Combining",fileLO,
                  (fileNLO if fileNLO != None else ""),
                  (fileNNLO if fileNNLO != None else ""))

            # Load LO coefficients.
            data = np.loadtxt(fileLO).T
            xLo    = np.array(data[0])
            xHi    = np.array(data[1])
            xMid   = (xLo+xHi)/2.
            coefLO = np.array(data[2])
            errLO  = np.array(data[3])
            numLO  = np.array(data[4])

            # Load NLO coefficients if available.
            coefNLO = np.zeros(len(coefLO))
            errNLO  = np.zeros(len(errLO))
            numNLO  = np.zeros(len(numLO))
            if fileNLO!=None:
                data = np.loadtxt(fileNLO).T
                coefNLO = np.array(data[2])
                errNLO  = np.array(data[3])
                numNLO  = np.array(data[4])

            # Load NNLO coefficients if available.
            coefNNLO = np.zeros(len(coefLO))
            errNNLO  = np.zeros(len(errLO))
            numNNLO  = np.zeros(len(numLO))
            if fileNNLO!=None:
                data = np.loadtxt(fileNNLO).T
                coefNNLO = np.array(data[2])
                errNNLO  = np.array(data[3])
                numNNLO  = np.array(data[4])

            # Calculate distribution with scale variation.
            sig, sigLo, sigHi, err = \
                self.var([coefLO,coefNLO,coefNNLO],
                         [errLO,errNLO,errNNLO],order)

            # Write histograms to file.
            if len(sig) > 0 and self.njets==3:
                self.writeHist(prefix, files[0], xLo, xMid, xHi,
                               sig[0], sigLo[0], sigHi[0], err[0],
                               numLO, output, path="LO")
            if len(sig) > 1 and self.njets<=4:
                path = "NLO" if self.njets==3 else "LO"
                self.writeHist(prefix, files[0], xLo, xMid, xHi,
                               sig[1], sigLo[1], sigHi[1], err[1],
                               numNLO, output, path=path)
            if len(sig) > 2:
                path = "NNLO"
                if self.njets==4: path = "NLO"
                if self.njets==5: path = "LO"
                self.writeHist(prefix, files[0], xLo, xMid, xHi,
                               sig[2], sigLo[2], sigHi[2], err[2],
                               numNNLO, output, path=path)

    # Function to write histogram files.
    def writeHist(self, prefix, filename, xLo, x, xHi,
                  sig, sigLo, sigHi, err, numEntries,
                  output, path):
        # Open file.
        name = filename.strip(prefix+"/").replace("_","-")
        if output == 'yoda': filename = path+".yoda"
        else: filename = filename+"."+path+".dat"
        filename = prefix+"/"+filename
        mode = 'a' if output=="yoda" else 'w'
        f = open(filename, mode)

        # Output in plain text format.
        if output == 'plain':
            # Histogram with variation.
            print("# xlow\t xhigh\t val\t mcerr\t errminus\t errplus",file=f)
            for i in range(0,len(x)):
                bw = abs(xHi[i]-xLo[i])
                print("{0:.6E}\t {1:.6E}\t {2:.11E}\t {3:.11E}\t {4:.11E}\t {5:.11E}".format(
                          xLo[i], xHi[i], sig[i]/bw, err[i]/bw,
                          (sig[i]-sigLo[i])/bw, (sigHi[i]-sig[i])/bw), file=f)
            print("",file=f)

        # Output in Yoda format.
        elif output == 'yoda':
            fullpath = "/analysis/"+name
            # Central result.
            print("\n",file=f)
            print("# BEGIN YODA_HISTO1D_V2",fullpath,file=f)
            print("Path:",fullpath,file=f)
            print("ScaledBy: 1.0",file=f)
            print("Title:",name,file=f)
            print("Type: Histo1D",file=f)
            print("---",file=f)
            print("# ID     ID      sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            print("Total           Total           "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      np.sum(sig),np.sum(err),
                      np.sum(x*sig),np.sum(x**2*err),np.sum(numEntries)),file=f)
            print("Underflow       Underflow       "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("Overflow        Overflow        "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("# xlow   xhigh   sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            for i in range(0,len(x)):
                print("{0:.6E}\t{1:.6E}\t{2:.11E}\t{3:.11E}\t{4:.11E}\t{5:.11E}\t{6:.11E}".format(
                    xLo[i],xHi[i],sig[i],err[i],
                    x[i]*sig[i],x[i]**2*err[i],numEntries[i]),file=f)
            print("# END YODA_HISTO1D_V2",file=f)
            # Down variation.
            print("\n",file=f)
            print("# BEGIN YODA_HISTO1D_V2",fullpath+"[MUR0.5_MUF1.0]",file=f)
            print("Path:",fullpath+"[MUR0.5_MUF1.0]",file=f)
            print("ScaledBy: 1.0",file=f)
            print("Title:",name,file=f)
            print("Type: Histo1D",file=f)
            print("---",file=f)
            print("# ID     ID      sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            print("Total           Total           "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      np.sum(sig),np.sum(err),
                      np.sum(x*sig),np.sum(x**2*err),np.sum(numEntries)),file=f)
            print("Underflow       Underflow       "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("Overflow        Overflow        "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("# xlow   xhigh   sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            for i in range(0,len(x)):
                print("{0:.6E}\t{1:.6E}\t{2:.11E}\t{3:.11E}\t{4:.11E}\t{5:.11E}\t{6:.11E}".format(
                    xLo[i],xHi[i], sigLo[i],err[i],
                    x[i]*sigLo[i],x[i]**2*err[i],numEntries[i]),file=f)
            print("# END YODA_HISTO1D_V2",file=f)
            # Up variation.
            print("\n",file=f)
            print("# BEGIN YODA_HISTO1D_V2",fullpath+"[MUR2.0_MUF1.0]",file=f)
            print("Path:",fullpath+"[MUR2.0_MUF1.0]",file=f)
            print("ScaledBy: 1.0",file=f)
            print("Title:",name,file=f)
            print("Type: Histo1D",file=f)
            print("---",file=f)
            print("# ID     ID      sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            print("Total           Total           "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      np.sum(sig),np.sum(err),
                      np.sum(x*sig),np.sum(x**2*err),np.sum(numEntries)),file=f)
            print("Underflow       Underflow       "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("Overflow        Overflow        "
                  + "{0:.11E}\t{1:.11E}\t{2:.11E}\t{3:.11E}\t{4:.11E}".format(
                      0.,0.,0.,0.,0.),file=f)
            print("# xlow   xhigh   sumw    sumw2   sumwx   sumwx2  numEntries",file=f)
            for i in range(0,len(x)):
                print("{0:.6E}\t{1:.6E}\t{2:.11E}\t{3:.11E}\t{4:.11E}\t{5:.11E}\t{6:.11E}".format(
                    xLo[i],xHi[i],sigHi[i],err[i],
                    x[i]*sigHi[i],x[i]**2*err[i],numEntries[i]),file=f)
            print("# END YODA_HISTO1D_V2",file=f)

        # Unsupported format.
        else:
            print("Unsupported format type",output)
            quit()

#=======================================================================
