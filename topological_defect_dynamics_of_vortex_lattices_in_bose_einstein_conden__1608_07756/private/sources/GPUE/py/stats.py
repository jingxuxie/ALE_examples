import os
from numpy import genfromtxt
import math as m
#import matplotlib as mpl
import numpy as np
import numpy.matlib

import warnings

import ConfigParser
import random as r
from decimal import *

c = ConfigParser.ConfigParser()

try:
    c.readfp(open(r'Params.dat'))
    incr = int(c.getfloat('Params','printSteps'))
    xDim = int(c.getfloat('Params','xDim'))
    yDim = int(c.getfloat('Params','yDim'))

except Exception as e:
    print "Cannot find Params.dat; assuming default values: xDim=yDim=1024, incr=1000"
    incr=1000
    xDim=1024
    yDim=1024

def lsFit(start,end,incr):
    warnings.warn("deprecated", DeprecationWarning)
    L = np.matrix([
            [0,0,1],
            [1,0,1],
            [0,1,1],
            [1,1,1]
            ])
            
    LSQ = np.linalg.inv(np.transpose(L)*L)*np.transpose(L)
    for i in range(start,end,incr):
        v_arr=genfromtxt('vort_arr_' + str(i),delimiter=',' )
        real=open('wfc_ev_' + str(i)).read().splitlines()
        img=open('wfc_evi_' + str(i)).read().splitlines()
        a_r = np.asanyarray(real,dtype='f8') #64-bit double
        a_i = np.asanyarray(img,dtype='f8') #64-bit double
        a = a_r[:] + 1j*a_i[:]
        wfc = (np.reshape(a,(xDim,yDim)))

        indX = [row[0] for row in v_arr]
        indY = [row[2] for row in v_arr]
        sign = [row[4] for row in v_arr]
        data=[]
        for ii in range(0,len(indX)):
            p=np.matrix([[0],[0],[0],[0]],dtype=np.complex)
            p[0]=(wfc[indX[ii], indY[ii]])
            p[1]=(wfc[indX[ii]+1, indY[ii]])
            p[2]=(wfc[indX[ii], indY[ii]+1])
            p[3]=(wfc[indX[ii]+1, indY[ii]+1])
            rc = LSQ * np.real(p)
            ic = LSQ * np.imag(p)

            A=np.squeeze([row[0:2] for row in [rc,ic]])
            B=-np.squeeze([row[2] for row in [rc,ic]])
            r=np.linalg.lstsq(A,B)[0]
            data.append([indX[ii]+r[0],indY[ii]+r[1],sign[ii]])


        np.savetxt('vort_lsq_'+str(i)+'.csv',data,delimiter=',')

if __name__ == '__main__':
    warnings.warn("deprecated", DeprecationWarning)
    import sys
    st = int(sys.argv[1])
    en = int(sys.argv[2])
    lsFit(st, en, incr)
