#! /usr/bin/python3

# This file is part of the EERAD3 NNLO event generator.
# Copyright (C) 2025 the authors.
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version. See COPYING for details.

import numpy as np
from os import listdir
from itertools import product

#=======================================================================
# File-handling methods.
#=======================================================================

# Find all files in a directory matching the EERAD3 output file format.

def findFiles(directory, combine):
    # Load file names in current directory
    files  = listdir(directory)

    # Find all processes, observables, cuts, and parts
    # in current directory.
    procs = []
    njets = []
    seeds = []
    icols = []
    parts = []
    obs   = []
    for f in files:
        if len(f.split(".")) != 7: continue
        proc, njet, seed, part, icol, ob, dat = f.split(".")
        if proc not in procs: procs.append(proc)
        if njet not in njets: njets.append(njet)
        if seed not in seeds: seeds.append(seed)
        if icol not in icols: icols.append(icol)
        if part not in parts: parts.append(part)
        if ob not in obs: obs.append(ob)
    procs.sort()
    njets.sort()
    seeds.sort()
    icols.sort()
    parts.sort()
    obs.sort()

    # Create file list.
    flist = []
    # Find files with different seeds.
    if combine=="seeds":
        for pr,nj,ic,p,o in product(procs,njets,icols,parts,obs):
            proc = "{0}.{1}.".format(pr,nj)
            wildcard = ".{0}.{1}.{2}.dat".format(p,ic,o)
            # Find matching files.
            flist.append(
                [f for f in files if proc in f and wildcard in f])
    # Find files with different parts.
    elif combine=="parts":
        for pr,nj,s,ic,o in product(procs,njets,seeds,icols,obs):
            proc = "{0}.{1}.{2}.".format(pr,nj,s)
            wildcard = ".{0}.{1}.dat".format(ic,o)
            # Find matching files.
            flist.append(
                [f for f in files if proc in f and wildcard in f])
    else:
        print(" Unknown combination mode")
        quit()
    return flist

# Merge files containing histograms of statistically independent runs.
def mergeFiles(resdir, files, minseed=-1, maxseed=-1):
    if minseed>=0 and maxseed>minseed:
        nFiles = min(len(files),maxseed-minseed+1)
    else:
        nFiles = len(files)

    if nFiles==0: return None
    wc = files[0].split(".")
    if nFiles==1:
        print(" Copying",
              wc[0]+"."+wc[1]+".*."+wc[3]+"."+wc[4]+"."+wc[5]+"."+wc[6],
              "("+str(nFiles)+" file)")
    else:
        print(" Merging",
              wc[0]+"."+wc[1]+".*."+wc[3]+"."+wc[4]+"."+wc[5]+"."+wc[6],
              "("+str(nFiles)+" files)")

    hcomb = np.array(np.loadtxt(resdir+"/"+files[0])).T
    if nFiles==1: return hcomb.T

    hcomb[2] = np.zeros(len(hcomb[1]))
    hcomb[3] = np.zeros(len(hcomb[1]))
    hcomb[4] = np.zeros(len(hcomb[1]))
    wtsum    = np.zeros(len(hcomb[1]))
    for f in files:
        iseed = int(f.split(".")[2])
        if minseed >= 0 and iseed < minseed: continue
        if maxseed >= 0 and iseed > maxseed: continue
        h = np.loadtxt(resdir+"/"+f).T
        wts = np.array([1./e**2 if e>0. else 0. for e in h[3]])
        wtsum    += wts
        hcomb[2] += wts*h[2]
    hcomb[2] = np.divide(hcomb[2],wtsum,
                         out=np.zeros(len(hcomb[2])),
                         where=wtsum!=0.)
    nhist = 0
    for f in files:
        iseed = int(f.split(".")[2])
        if minseed >= 0 and iseed < minseed: continue
        if maxseed >= 0 and iseed > maxseed: continue
        h = np.loadtxt(resdir+"/"+f).T
        wts = np.array([1./e**2 if e>0. else 0. for e in h[2]])
        hcomb[3] += wts*(h[2]-hcomb[2])**2
        hcomb[4] += h[4]
        nhist += 1
    hcomb[3] = np.sqrt(
        np.divide(hcomb[3],wtsum,
                  out=np.zeros(len(hcomb[3])),where=wtsum!=0.)
        /(nhist-1.))
    return hcomb.T

#-----------------------------------------------------------------------

# Combine files containing different contributions of a perturbative
# coefficient:
# V, R -> NLO
# VV, RV, RR -> NNLO

def combineFiles(resdir, files):
    wc = files[0].split(".")
    parts = [f.split(".")[3] for f in files]

    doNNLO = False
    listNNLO = []
    if ("VV" in parts) and ("RV" in parts) and ("RR" in parts):
        doNNLO = True
        listNNLO = [f for f in files if ".VV." in f or ".RV." in f or ".RR." in f]
    doNLO = False
    listNLO = []
    if "V" in parts and "R" in parts:
        doNLO = True
        listNLO = [f for f in files if ".V." in f or ".R." in f]
    doLO = False
    listLO = []
    if "LO" in parts:
        doLO = True
        listLO = [f for f in files if ".LO." in f]

    listCombined = [np.array([]), np.array([]), np.array([])]
    if doLO:
        print(" Creating",listLO[0])
        hsum = np.array(np.loadtxt(resdir+"/"+listLO[0])).T
        listCombined[0] = hsum.T
    if doNLO:
        print(" Creating",wc[0]+"."+wc[1]+"."+wc[2]\
              +".NLO."+wc[4]+"."+wc[5]+"."+wc[6])
        hsum = np.array(np.loadtxt(resdir+"/"+listNLO[0])).T
        for f in listNLO[1:]:
            h = np.loadtxt(resdir+"/"+f).T
            hsum[2] += h[2]
            hsum[3]  = np.sqrt(hsum[3]**2+h[3]**2)
            hsum[4] += h[4]
        listCombined[1] = hsum.T
    if doNNLO:
        print(" Creating",wc[0]+"."+wc[1]+"."+wc[2]\
              +".NNLO."+wc[4]+"."+wc[5]+"."+wc[6])
        hsum = np.array(np.loadtxt(resdir+"/"+listNNLO[0])).T
        for f in listNNLO[1:]:
            h = np.loadtxt(resdir+"/"+f).T
            hsum[2] += h[2]
            hsum[3]  = np.sqrt(hsum[3]**2+h[3]**2)
            hsum[4] += h[4]
        listCombined[2] = hsum.T

    return listCombined

#-----------------------------------------------------------------------

# Write histogram 'hist' to file 'outfile'.

def writeFile(hist, outfile):
    of = open(outfile,"w")
    # Print histogram that is saved in dict.
    if isinstance(hist, dict):
        for i in range(hist['nBins']):
            xLo = hist['bins'][i]
            xHi = hist['bins'][i+1]
            wt  = hist['wt'][i]
            wt2 = hist['wt2'][i]
            n   = hist['n'][i]
            print("   {0:.6f}   {1:.6E}  {2:.4E}  {3:.4E}  {4:.4E}"\
                  .format(xLo,xHi,wt,wt2,n),file=of)
    else:
        # Print plain list.
        for v in hist:
            print("   {0:.6f}   {1:.6f}  {2:.4E}  {3:.4E}  {4:.4E}"\
                  .format(v[0],v[1],v[2],v[3],v[4]),file=of)

#=======================================================================
