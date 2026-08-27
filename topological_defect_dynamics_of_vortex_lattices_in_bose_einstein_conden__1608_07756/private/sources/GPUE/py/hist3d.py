from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
from numpy import genfromtxt
import math as m
import ConfigParser 

c = ConfigParser.ConfigParser()
c.readfp(open(r'Params.dat'))

xDim = int(c.getfloat('Params','xDim'))
yDim = int(c.getfloat('Params','yDim'))
gndMaxVal = int(c.getfloat('Params','gsteps'))
evMaxVal = int(c.getfloat('Params','esteps'))
incr = int(c.getfloat('Params','print_out'))
sep = (c.getfloat('Params','dx'))
dx = (c.getfloat('Params','dx'))
dt = (c.getfloat('Params','dt'))
xMax = (c.getfloat('Params','xMax'))
yMax = (c.getfloat('Params','yMax'))
num_vort = 0#int(c.getfloat('Params','Num_vort'))

sep=1.0
def plot_xyz_histogram(start,fin,incr, barcolor):
	fig = plt.figure()
	ax = Axes3D(fig)
	data =[]
	for i in range(start, fin, incr):	
		v_arr=genfromtxt('vort_lsq_' + str(i) + '.csv',delimiter=',' )
		datatmp=[]
		count=0

		for i1 in range(0,v_arr.size/2):
			for i2 in range(i1,v_arr.size/2):
				datatmp.append(m.sqrt( abs(v_arr[i1][0]*sep - v_arr[i2][0]*sep)**2  +  abs(v_arr[i1][1]*sep - v_arr[i2][1]*sep)**2 ))
				count = count + 1
		hist=np.histogram(datatmp,bins=np.arange(1.0,m.sqrt(xDim**2 + yDim**2),1.0))
		data.append(hist[:][0])
	""" Takes in a matrix (see structure above) and generate a pseudo-3D histogram by overlaying close, semitransparent bars. """
	for time, occurrence in zip(range(len(data)), data):
		dist = range(len(occurrence))
		barband = range(-45, 45, 5)
		#for modifier in barband:
		ax.bar(dist, occurrence, zs=time, zdir='y', color=np.random.rand(3,1), alpha=0.8)
			#ax.bar(current, occurrence, zs=duration+(float(modifier)/100), zdir='y', color=np.random.rand(3,1), alpha=0.6)

	ax.set_xlabel('Dist')
	ax.set_ylabel('Time')
	ax.set_zlabel('Occurrances')

	plt.savefig("HIST_N.pdf")
	plt.show()

def plot_hist_pcolor(start,fin,incr, barcolor):
	fig = plt.figure()
        
	data =[]
	for i in range(start, fin, incr):	
		v_arr=genfromtxt('vort_lsq_' + str(i) + '.csv',delimiter=',' )
		datatmp=[]
		count=0

		for i1 in range(0,v_arr.size/2):
			for i2 in range(i1,v_arr.size/2):
				m_tmp = m.sqrt(abs(v_arr[i1][0]*sep - v_arr[i2][0]*sep)**2  +  abs(v_arr[i1][1]*sep - v_arr[i2][1]*sep)**2 )
				datatmp.append( m_tmp )
				count = count + 1
		hist=np.histogram(datatmp,bins=np.arange(0.0,240.0,0.1))
		data.append(hist[:][0])

      #  print data
        ax = fig.add_subplot(111)
        ax.imshow(data)
	plt.gca().invert_yaxis()
        ax.set_aspect('auto')
#        plt.jet()
	fig.savefig("HIST_PCOLOR.pdf")
