###############################################################################
import os
from numpy import genfromtxt
import math as m
import numpy as np
import copy as cp
import ConfigParser
import sys

###############################################################################
if (len(sys.argv) == 2):
    data_dir = "../" + sys.argv[1] + "/"
else:
    data_dir = ""
c = ConfigParser.ConfigParser()
c.readfp(open(data_dir + 'Params.dat', "r"))

xDim = int(c.getfloat('Params','xDim'))
yDim = int(c.getfloat('Params','yDim'))
gndMaxVal = int(c.getfloat('Params','gsteps'))
evMaxVal = int(c.getfloat('Params','esteps'))
incr = int(c.getfloat('Params','printSteps'))
dx = (c.getfloat('Params','dx'))
dt = (c.getfloat('Params','dt'))
xMax = (c.getfloat('Params','xMax'))
yMax = (c.getfloat('Params','yMax'))

# quick check to make sure evMax Steps is right. This is simply because of the 
# way GPUE outputs data.
if (evMaxVal % incr == 0):
    evMaxVal = evMaxVal - incr

###############################################################################
class Vortex: #Tracks indivisual vortices over time.
###############################################################################
###############################################################################
    def __init__(self,uid,x,y,isOn,sign=1):
    ###############################################################################
        self.uid = uid
        self.x = x
        self.y = y
        self.sign = sign
        self.isOn = isOn
        self.next = None

###############################################################################
    def update_uid(self,uid):
###############################################################################
        self.uid = uid

###############################################################################
    def update_on(self,isOn): #Vortex is trackable
###############################################################################
        self.isOn = isOn

###############################################################################
    def update_next(self,next): #Get next vortex
###############################################################################
        self.next = next

###############################################################################
    def dist(self,vtx): #Distance between self and vtx
###############################################################################
        r = m.sqrt((self.x - vtx.x)**2 + (self.y - vtx.y)**2)
        return r

###############################################################################
class VtxList: #Linked-list for tracking vortices
###############################################################################
###############################################################################
    def __init__(self):
###############################################################################
        self.head = None
        self.tail = None
        self.length = 0

###############################################################################
    def element(self,pos): #Get vtx at position pos
###############################################################################
        pos_l = 0
        if pos < self.length:
            vtx = self.head
            while pos_l < pos:
                pos_l = pos_l +1
                vtx = vtx.next
        else:
            print "Out of bounds"
            exit(-1)
        return vtx

###############################################################################
    def vtx_uid(self,uid): #Get vtx with identifier uid
###############################################################################
        vtx = self.head
        pos = 0
        while vtx.uid != uid:
            vtx = vtx.next
            pos = pos +1
        return [vtx,pos]

###############################################################################
    def max_uid(self): #Return position and value of largest uid
###############################################################################
        val = 0
        vtx = self.head
        val = vtx.uid
        pos = 0
        #while pos < self.length:
        while True:
            vtx = vtx.next
            if(vtx == None):
                break
            if vtx.uid > val:
                val = vtx.uid
            pos = pos +1
        return [val,pos]

###############################################################################
    def add(self,Vtx,index=None): #Add a vtx at index, otherwise end
###############################################################################
        if self.length == 0:
            self.head = Vtx
            self.tail = Vtx
            self.length = 1
        elif index == None:
            self.tail.next = Vtx
            self.tail = Vtx
            self.length = self.length +1
        else:
            Vtx.next = self.element(index)
            self.element(index-1).next = Vtx
            self.length = self.length + 1

###############################################################################
    def as_np(self): #Return numpy array with format x,y,sign,uid,isOn
###############################################################################
        dtype = [('x',float),('y',float),('sign',int),('uid',int),('isOn',int)]
        data =[]# np.array([],dtype=dtype)
        i = 0
        vtx = self.head
        while vtx != None:
            data.append([vtx.x, vtx.y, vtx.sign, vtx.uid, vtx.isOn])
            vtx = vtx.next
            i = i+1
        return (data)

###############################################################################
    def write_out(self,time,data): #Write out CSV file as  x,y,sign,uid,isOn
###############################################################################
        np.savetxt(data_dir+'vort_ord_'+str(time)+'.csv',data,fmt='%10.5f,%10.5f,%i,%i,%i',delimiter=',')

###############################################################################
    def idx_min_dist(self,vortex, isSelf=False): #Closest vtx to self
###############################################################################
        counter = 0
        ret_idx = counter
        vtx = self.head
        if vtx != None:
            r = vtx.dist(vortex)
            while vtx.next != None:
                vtx = vtx.next
                counter = counter +1
                if r > vtx.dist(vortex):
                    r = vtx.dist(vortex)
                    ret_idx = counter
        return (ret_idx,r)

###############################################################################
    def remove(self,pos): #Remove vortices outside artificial boundary
###############################################################################
        if self.length > 1 and pos > 1:
            current = self.element(pos-1).next
            self.element(pos - 1).next = current.next
            current.next = None
            self.length = self.length - 1
            return current
        elif pos == 0:
            current = self.head
            self.head = self.head.next
            self.length = self.length - 1
            return current
        else:
            self.head = None
            self.length = 0
            return None

###############################################################################
    def swap_uid(self,uid_i,uid_f): #Swap uid between vtx
###############################################################################
        vtx_pos = self.vtx_uid(uid_i)
        self.remove(pos_i)
        self.add(vtx,index=pos_f)

###############################################################################
    def vort_decrease(self,positions,vorts_p): #Turn off vortex timeline
###############################################################################
        for i4 in positions:
            #print positions, "Decrease"
            vtx = cp.copy(i4)
            vtx.update_on(False)
            vtx.update_next(None) 
            self.add(vtx)

###############################################################################
    def vort_increase(self,positions,vorts_p): #Add new vtx to tracking
###############################################################################
        counter = 1
        max_uid = vorts_p.max_uid()
        for i4 in positions:
            #print positions, "Increase"
            self.element(i4).update_uid(max_uid[0] + counter)
            counter = counter+1

###############################################################################
def run(start,fin,incr): #Performs the tracking
###############################################################################
	v_arr_p=genfromtxt(data_dir+'vort_arr_' + str(incr),delimiter=',')
	for i in range( start + incr*2, fin + 1, incr): #loop over samples in time
		vorts_p = VtxList()
		vorts_c = VtxList()
		v_arr_c=genfromtxt(data_dir+'vort_arr_' + str(i), delimiter=',')
		if i==start + incr*2:
        		#from IPython import embed; embed()
			v_arr_p_coords = np.array([a for a in v_arr_p[:,[1,3]]]) # Select the coordinates from the previous timestep
			v_arr_c_coords = np.array([a for a in v_arr_c[:,[1,3]]]) # Select the coordinates from the current timestep
			v_arr_p_sign = np.array([a for a in v_arr_p[:,4]]) # Select the vortex signs from previous
			v_arr_c_sign = np.array([a for a in v_arr_c[:,4]]) # Select the vortex signs from current
		else:
			v_arr_p_coords = np.array([a for a in v_arr_p[:,[0,1]]]) #Previous coords
			v_arr_p_sign = np.array([a for a in v_arr_p[:,2]]) #Previous sign

        v_arr_c_coords = np.array([a for a in v_arr_c[:,[1,3]]]) #Current coords
        v_arr_c_sign = np.array([a for a in v_arr_c[:,4]]) #Current sign
        for i1 in range(0,v_arr_p_coords.size/2): #loop over previous coordinates for a given time
            vtx_p = Vortex(i1,v_arr_p_coords[i1][0],v_arr_p_coords[i1][1],True,sign=v_arr_p_sign[i1]) # Create a vortex object with uid given by number i1
            vorts_p.add(vtx_p)#Add vortex to the list

        for i2 in range(0,v_arr_c_coords.size/2): #loop over current coordinates for a given time
            vtx_c = Vortex(-1-i2,v_arr_c_coords[i2][0],v_arr_c_coords[i2][1],True,sign=v_arr_c_sign[i2]) # Create a vortex object with uid -1 - i2
            vorts_c.add(vtx_c) #Add vortex object to list

        for i3 in range(0,vorts_p.length): # For all previous vortices in list
            index_r = vorts_c.idx_min_dist(vorts_p.element(i3)) # Find the smallest distance vortex index between current and previous data

            v0c = vorts_c.element(index_r[0]).sign #Get the sign of the smallest distance vortex
            v0p = vorts_p.element(i3).sign # Get the sign of the current vortex at index i3
            v1c = vorts_c.element(index_r[0]).uid #Get uid of current vortex
            #Check if distance is less than 7 grid points, and that the sign is matched between previous and current vortices, and that the current vortex has a negative uid, indicating that a pair has not yet been found. If true, then update the current vortex index to that of the previous vortex index, and turn vortex on --- may be dangerous
	    if (index_r[1] < 30) and (vorts_c.element(index_r[0]).sign == vorts_p.element(i3).sign) and (vorts_c.element(index_r[0]).uid < 0) and (vorts_p.element(i3).isOn == True):
		vorts_c.element(index_r[0]).update_uid(vorts_p.element(i3).uid)
		vorts_c.element(index_r[0]).update_on(True)
	    else:
	        print "Failed to find any matching vortex. Entering interactive mode. Exit with Ctrl+D"
       	        from IPython import embed; embed()
				

        #You will never remember why this works
        uid_c = [[a for a in b][3] for b in vorts_c.as_np()] # Slice the uids for current data
        uid_p = [[a for a in b][3] for b in vorts_p.as_np()] # Slice uids for previous data
        #Check the difference between current and previous vtx data
        dpc = set(uid_p).difference(set(uid_c)) # Creates a set and checks the elements for differences. Namely, finds which uids are unique to previous (ie which ones are no longer in current due to annihilation or falling outside boundary), which uids are only in current (ie newly found vortices, or older vortices that have reappeared)
        dcp = set(uid_c).difference(set(uid_p))
        vtx_pos_p=[]
        vtx_pos_c=[]
                #For all elements in the set of previous to current, note [vtx, pos] vtx for previous, and pos for current
        for i5 in dpc:
            vtx_pos_p = np.append(vtx_pos_p,vorts_p.vtx_uid(i5)[0]) #vtx
        for i6 in dcp:
            vtx_pos_c = np.append(vtx_pos_c,vorts_c.vtx_uid(i6)[1]) #pos
        if len(dpc or dcp) >= 1: #if any differences were found, call the below functions
            vorts_c.vort_decrease(vtx_pos_p,vorts_p)
            vorts_c.vort_increase(vtx_pos_c,vorts_p)

                # Sort the vortices in current based on uid value, and write out the data
        vorts_c_update=sorted(vorts_c.as_np(),key=lambda vtx: vtx[3])
        vorts_c.write_out(i,np.asarray(vorts_c_update))
        print "[" + str(i) +"]", "Length of previous=" + str(len(v_arr_p_coords)), "Length of current=" + str(len(vorts_c_update))
        v_arr_p=genfromtxt(data_dir+'vort_ord_' + str(i) + '.csv',delimiter=',' )

###############################################################################
###############################################################################
run(0, evMaxVal, incr)
