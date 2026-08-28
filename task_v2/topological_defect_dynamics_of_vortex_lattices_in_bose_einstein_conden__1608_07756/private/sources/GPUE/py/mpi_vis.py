import os
from mpi4py import MPI
CPUs = 1#os.environ['SLURM_JOB_CPUS_PER_NODE']
from numpy import genfromtxt
import math as m
import matplotlib as mpl
import matplotlib.tri as tri
import numpy as np
import scipy as sp
from scipy.spatial import Voronoi, voronoi_plot_2d
import numpy.matlib
mpl.use('Agg')
from matplotlib.ticker import ScalarFormatter
import matplotlib.pyplot as plt
from matplotlib import pyplot as plt
import matplotlib.patheffects as PathEffects
import ConfigParser
import random as r
from decimal import *
import stats
import hist3d

getcontext().prec = 4
c = ConfigParser.ConfigParser()
getcontext().prec = 4
c = ConfigParser.ConfigParser()
c.readfp(open(r'Params.dat'))

#Default value for wavefunction density max; modified by initially loaded wavefunction set, 
# and used for all subsequent plotting.
maxDensityVal=5e7 

xDim = int(c.getfloat('Params','xDim'))
yDim = int(c.getfloat('Params','yDim'))
gndMaxVal = int(c.getfloat('Params','gsteps'))
evMaxVal = int(c.getfloat('Params','esteps'))
incr = int(c.getfloat('Params','printSteps'))
sep = (c.getfloat('Params','dx'))
dx = (c.getfloat('Params','dx'))
dt = (c.getfloat('Params','dt'))
xMax = (c.getfloat('Params','xMax'))
yMax = (c.getfloat('Params','yMax'))
num_vort = 0#int(c.getfloat('Params','Num_vort'))

data = numpy.ndarray(shape=(xDim,yDim))

def image_gen_single(dataName, value, imgdpi,opmode, x_dat, cbarOn=True, plot_vtx=False):
    real=open(dataName + '_' + str(0)).read().splitlines()
    img=open(dataName + 'i_' + str(0)).read().splitlines()
    a1_r = numpy.asanyarray(real,dtype='f8') #128-bit complex
    a1_i = numpy.asanyarray(img,dtype='f8') #128-bit complex
    a1 = a1_r[:] + 1j*a1_i[:]
    b1 = np.reshape(a1,(xDim,yDim))

    if not os.path.exists(dataName+"r_"+str(value)+"_abspsi2.png"):
        real=open(dataName + '_' + str(value)).read().splitlines()
        img=open(dataName + 'i_' + str(value)).read().splitlines()
        a_r = numpy.asanyarray(real,dtype='f8') #128-bit complex
        a_i = numpy.asanyarray(img,dtype='f8') #128-bit complex
        a = a_r[:] + 1j*a_i[:]
        b = np.transpose(np.reshape(a,(xDim,yDim))) #Transpose to match matlab plots
        if value=0:
            maxDensityVal=np.max(np.abs(a)**2)
        startBit = 0x00

        try:
            vorts = np.loadtxt('vort_ord_' + str(value) + '.csv', delimiter=',', unpack=True)
        except Exception as e:
            print "Failed to load the required data file: %s"%e
            print "Please run vort.py before plotting the density, if you wih to have correctly numbered vortices"
            vorts = np.loadtxt('vort_arr_' + str(value), delimiter=',', unpack=True, skiprows=1)
            startBit=0x01

        if opmode & 0b100000 > 0:
            nameStr = dataName+"r_"+str(value)

            fig, ax = plt.subplots()
            f = plt.imshow( (abs(b)**2), cmap='hot', vmin=0, vmax=maxDensityVal, interpolation='none',)
                                #extent=[-xMax, xMax, -xMax, xMax])
            tstr =  str(value*dt)
            plt.title('t=' + tstr + " s", fontsize=28)

            if cbarOn==True:
                tbar = fig.colorbar(f)

            plt.gca().invert_yaxis()
            if plot_vtx==True:
                if startBit==0x00:
                    zVort = zip(vorts[0,:],vorts[1,:], vorts[3,:])
                else:
                    zVort = zip(vorts[1,:], vorts[3,:], [0, 1, 2, 3])
                for x, y, z in zVort:
                    if z==0:
                        txt = plt.text(x, y, str(int(z)), color='#379696', fontsize=6, alpha=0.7)
                        txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='#B9EA56')])
                    else:
                        txt = plt.text(x, y, str(int(z)), color='#B9EA56', fontsize=6, alpha=0.7)
                        txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='#379696')])
            plt.axis('equal')
            plt.axis('off')
            if plot_vtx==True:
                plt.savefig(dataName+"r_"+str(value)+"_abspsi2_num.png",dpi=imgdpi, bbox_inches='tight')
            else:
                plt.savefig(dataName+"r_"+str(value)+"_abspsi2_nonum.png",dpi=imgdpi, bbox_inches='tight')
            plt.close()

        print "Saved figure: " + str(value) + ".png"
        plt.close()
    else:
        print "File(s) " + str(value) +".png already exist."

if __name__ == '__main__':
    import sys
    cbarOn = sys.argv[1].lower() == 'true'
    plot_vtx = sys.argv[2].lower() == 'true'
    gndImgList=[]
    evImgList=[]
    x_coord = np.loadtxt('x_0', unpack=True)

    comm = MPI.COMM_WORLD
    size = comm.size
    rank = comm.rank
    print "Rank %d/%d initialised"%(rank,size-1)

    arrG = np.array_split( xrange(0,gndMaxVal,incr), size)
    arrE = np.array_split( xrange(0,evMaxVal,incr), size)

    for i in arrG[rank]:
        gndImgList.append(i)
    for i in arrE[rank]:
        evImgList.append(i)

    while gndImgList:

        print "Processing data index=%d on rank=%d"%(i,rank)
        i=gndImgList.pop()

        try:
            image_gen_single("wfc_0_ramp", i, 400, 0b100000, x_coord, cbarOn, plot_vtx)
        except Exception as e:
            print "Unable to process wfc_0_ramp data index=%d on rank=%d"%(i,rank)            
        try:
            image_gen_single("wfc_0_const", i, 400, 0b100000, x_coord, cbarOn, plot_vtx)
        except Exception as e:
            print "Unable to process wfc_0_const data index=%d on rank=%d"%(i,rank)

    while evImgList:
        print "Processing data index=%d on rank=%d"%(i,rank)
        i=evImgList.pop()
        try:
            image_gen_single("wfc_ev", i, 400, 0b100000, x_coord, cbarOn, plot_vtx)
            print "Processed data index=%d on rank=%d"%(i,rank)

        except Exception as e:
            print "Unable to process wfc_ev data index=%d on rank=%d"%(i,rank)
