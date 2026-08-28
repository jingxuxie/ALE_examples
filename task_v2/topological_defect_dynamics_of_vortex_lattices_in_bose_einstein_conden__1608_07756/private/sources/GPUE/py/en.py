import os
CPUs = os.environ['SLURM_JOB_CPUS_PER_NODE']
print "Number of cores: " + str(CPUs)
from numpy import genfromtxt
import math as m
import matplotlib as mpl
import numpy as np
import scipy as sp
import numpy.matlib
mpl.use('Agg')
import ConfigParser
import random as r
from decimal import *

getcontext().prec = 4
c = ConfigParser.ConfigParser()
getcontext().prec = 4
c = ConfigParser.ConfigParser()
c.readfp(open(r'Params.dat'))

xDim = int(c.getfloat('Params','xDim'))
yDim = int(c.getfloat('Params','yDim'))
gndMaxVal = int(c.getfloat('Params','gsteps'))
evMaxVal = int(c.getfloat('Params','esteps'))
incr = int(c.getfloat('Params','print_out'))
sep = (c.getfloat('Params','dx'))
dx = (c.getfloat('Params','dx'))
dy = (c.getfloat('Params','dx'))
dt = (c.getfloat('Params','dt'))
xMax = (c.getfloat('Params','xMax'))
yMax = (c.getfloat('Params','yMax'))
num_vort = 0#int(c.getfloat('Params','Num_vort'))

data = numpy.ndarray(shape=(xDim,yDim))
K = np.reshape(np.array(open('K_0').read().splitlines(),dtype='f8'),(xDim,yDim))
V = np.reshape(np.array(open('V_0').read().splitlines(),dtype='f8'),(xDim,yDim))
X = np.array(open('x_0').read().splitlines(),dtype='f8')
Y = np.array(open('y_0').read().splitlines(),dtype='f8')
XM,YM = np.meshgrid(X,Y)
R = (XM**2+YM**2)
macheps = 7./3. - 4./3. - 1. #http://rstudio-pubs-static.s3.amazonaws.com/13303_daf1916bee714161ac78d3318de808a9.html
Q = (XM**2-YM**2)

def expectValueR(dataName,i,Val):
	real=open(dataName + '_' + str(i)).read().splitlines()
	img=open(dataName + 'i_' + str(i)).read().splitlines()
	a_r = np.array(real,dtype='f8') #64-bit double
	a_i = np.array(img,dtype='f8') #64-bit double
	wfcr = np.reshape(a_r[:] + 1j*a_i[:],(xDim,yDim))
	return np.real(np.trapz(np.trapz(np.conj(wfcr)*Val*wfcr))*dx*dy)

def energy_total(dataName,i):
	real=open(dataName + '_' + str(i)).read().splitlines()
	img=open(dataName + 'i_' + str(i)).read().splitlines()
	a_r = np.array(real,dtype='f8') #64-bit double
	a_i = np.array(img,dtype='f8') #64-bit double
	wfcr = np.reshape(a_r[:] + 1j*a_i[:],(xDim,yDim))
	wfcp = np.array(np.fft.fft2(wfcr))
	wfcr_c = np.conj(wfcr)
	
	E1 = np.fft.ifft2(K*wfcp)
	E2 = V*wfcr
	
	E_k = np.trapz(np.trapz(wfcr_c*E1))*dx*dy
	E_vi = np.trapz(np.trapz(wfcr_c*E2))*dx*dy
	return np.real(E_k + E_vi)

#for ii in range(0,gndMaxVal,incr):
#	print "E(t={} s)={}".format(ii*dt,energy_total('wfc_0_const',ii))	

for ii in range(0,evMaxVal,incr):
#	print "E(t={} s)={}".format(ii*dt,energy_total('wfc_ev',ii))	
	#print "R(t={} s)={}".format(ii*dt,rad('wfc_ev',ii))	
	print "{},{}".format(ii*dt,expectValueR('wfc_ev',ii,R))	

