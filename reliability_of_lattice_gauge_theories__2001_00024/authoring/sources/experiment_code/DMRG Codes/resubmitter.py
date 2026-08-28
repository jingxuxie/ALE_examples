#!/usr/bin/python
# -*- coding: utf-8 -*-
import glob, os, sys
import subprocess as sp
import re
from decimal import *
import numpy as np
import time

jobInitial = 0 
jobFinal = 199
storageFolder = '/data2/sclms/halimeh/QuantumLinkModel/new/job'
dt = 0.001

for jobInd in np.arange(jobInitial,jobFinal+1,1):
    if os.path.exists(storageFolder+str(jobInd)+'/done.txt'):
        print('Job already completed!')
    else:
        t = 0
        while os.path.exists(storageFolder+str(jobInd)+'/psi.t'+str(t)):
            t = round(t+dt,3)

        t = round(t-dt,3)
        if t < dt:
            t = 0
        print('Job index '+str(jobInd)+' reached only t='+str(t)+'. Resubmitting...')
        print('mkdir job'+str(jobInd))
        os.system('mkdir job'+str(jobInd))
        print('mkdir /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/')
        os.system('mkdir /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/')
        #print('cp /data2/sclms/halimeh/QuantumLinkModel/new/*job'+str(jobInd)+' job'+str(jobInd)+'/')
        #os.system('cp /data2/sclms/halimeh/QuantumLinkModel/new/*job'+str(jobInd)+' job'+str(jobInd)+'/')
        os.system("cat bh | sed -e 's/MYNUM/"+str(jobInd)+"/g' > job"+str(jobInd)+"/bhj"+str(jobInd))
        os.system("cat script.py | sed -e 's/MYNUM/"+str(jobInd)+"/g' > job"+str(jobInd)+"/temp.py")
        os.system("cat job"+str(jobInd)+"/temp.py | sed -e 's/MYTIME/"+str(t)+"/g' > job"+str(jobInd)+"/command.py")
        print('rm job'+str(jobInd)+'/temp.py')
        os.system('rm job'+str(jobInd)+'/temp.py')
        print('cp /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/psi.t'+str(t)+' job'+str(jobInd))
        os.system('cp /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/psi.t'+str(t)+' job'+str(jobInd))
        print('sbatch job'+str(jobInd)+'/bhj'+str(jobInd))
        os.system('sbatch job'+str(jobInd)+'/bhj'+str(jobInd))   
