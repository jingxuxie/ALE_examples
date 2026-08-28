#!/usr/bin/python
# -*- coding: utf-8 -*-
import glob, os, sys
import subprocess as sp
import re
from decimal import *
import numpy as np
import time

jobInitial = 191 
jobFinal = 199

for jobInd in np.arange(jobInitial,jobFinal+1,1):
    print('mkdir job'+str(jobInd))
    os.system('mkdir job'+str(jobInd))
    print('mkdir /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/')
    os.system('mkdir /data2/sclms/halimeh/QuantumLinkModel/new/job'+str(jobInd)+'/')
    print('cp /data2/sclms/halimeh/QuantumLinkModel/new/*job'+str(jobInd)+' job'+str(jobInd)+'/')
    os.system('cp /data2/sclms/halimeh/QuantumLinkModel/new/*job'+str(jobInd)+' job'+str(jobInd)+'/')
    os.system("cat bh | sed -e 's/MYNUM/"+str(jobInd)+"/g' > job"+str(jobInd)+"/bhj"+str(jobInd))
    os.system("cat script.py | sed -e 's/MYNUM/"+str(jobInd)+"/g' > job"+str(jobInd)+"/command.py")
    print('cp psi0 job'+str(jobInd))
    os.system('cp psi0 job'+str(jobInd))
    print('sbatch job'+str(jobInd)+'/bhj'+str(jobInd))
    os.system('sbatch job'+str(jobInd)+'/bhj'+str(jobInd))
