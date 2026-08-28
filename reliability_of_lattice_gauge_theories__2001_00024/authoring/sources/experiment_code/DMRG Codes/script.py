#!/usr/bin/python
# -*- coding: utf-8 -*-
import glob, os, sys
import subprocess as sp
import re
from decimal import *
import numpy as np
import time
L = 32
Nmax = 2 
jobInd = MYNUM 
storageFolder = '/data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/'
t = MYTIME 
dt = 0.0001
innerStep = 10

if t < 1e-10:
    print('cp psi0 psi.t0')
    os.system('cp psi0 psi.t0')

trunc = 1e-6;
finalCnt = 120
initialCnt = int(t/(innerStep*dt))

if initialCnt > 0:
    print('Continuing from time-step (lattice index) '+str(initialCnt))
else:
    print('Starting from time-step (lattice index) '+str(initialCnt))

for cnt in np.arange(initialCnt,finalCnt+1,1):
    start_time = time.time()
    print('We are evolving from t='+str(t)+' to t='+str(round(t+dt,4)))
    print('mp-evolve-krylov -H lattice_L'+str(L)+'_Nmax'+str(Nmax)+'_ts'+str(cnt)+'_job'+str(jobInd)+':''H_J+H_U+H_ramp'' -w psi.t'+str(t)+' -m 50 -x 10000 -T '+str(t)+' -t '+str(dt)+' -n '+str(innerStep)+' -s '+str(innerStep)+' -e '+str(trunc)+' -o psi')
    os.system('mp-evolve-krylov -H lattice_L'+str(L)+'_Nmax'+str(Nmax)+'_ts'+str(cnt)+'_job'+str(jobInd)+':''H_J+H_U+H_ramp'' -w psi.t'+str(t)+' -m 50 -x 10000 -T '+str(t)+' -t '+str(dt)+' -n '+str(innerStep)+' -s '+str(innerStep)+' -e '+str(trunc)+' -o psi')
    compTime = time.time()-start_time
    file = open(storageFolder+"timeKeeper.txt","a")
    file.write(str(compTime)+"\n")
    file.close() 
    print('mv psi.t'+str(t)+' '+storageFolder)
    os.system('mv psi.t'+str(t)+' '+storageFolder)
    t = round(t+innerStep*dt,4)
