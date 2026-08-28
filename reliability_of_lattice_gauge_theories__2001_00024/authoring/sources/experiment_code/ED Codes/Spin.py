#####################################################################
#              -- Staggered Bose-Hubbard model --		            #
#    Exact diagonalization of s=1/2 QLM using QuSpin	   		    #
#    		           R. Ott --  June 2019  --                     #
# 				based on T. V. Zache -- Mai & November 2018 --      #
# 				and Phillip Weinberg and Marin Bukov                #
#####################################################################

from quspin.operators import hamiltonian 	# Hamiltonians and operators
from quspin.operators import commutator
from quspin.basis import spin_basis_1d 		# Hilbert space spin basis

import numpy as np 							# generic math functions
import os									# for creating directories
import matplotlib.pyplot as plt
from numpy import random as rd
from sys import argv
from scipy.interpolate import interp1d

run_id = str(argv[1])


GAP_SIM = False
TIME_EVOLUTION = True
protect = 3000
bias = 1
####### -- Experimental -- ###############
Hz = 1
#tf = 0.14 /Hz
#Nsteps = 100

error_delta = 0. * Hz * 2. * np.pi
systematics_delta = 0. * Hz * 2. * np.pi
fluc = rd.normal(systematics_delta,error_delta)
##### -- Read exp data -- #####
times = np.loadtxt('data_exp_ramp/EXP_DATA/Time.txt')  	 # experimental time steps
Onsite = np.multiply(1.,np.loadtxt('data_exp_ramp/EXP_DATA/Onsite.txt')		) # experimental onsite energies
hop = np.loadtxt('data_exp_ramp/EXP_DATA/Hop.txt')				 # experimental hopping element
delta = np.multiply(1.,np.loadtxt('data_exp_ramp/EXP_DATA/delta.txt')	)		 # experimental detunings

U_int = interp1d(times,Onsite,kind='previous')
delta_int = interp1d(times,delta,kind='previous')
hop_int = interp1d(times,hop,kind='previous')


if GAP_SIM:
    steps = 250
    times = np.linspace(0,0.120,steps)
    Onsite = np.linspace(2.*np.pi*1510,2.*np.pi*1490,steps)
    delta = np.ones(steps)*2.*np.pi*750
    hop = np.ones(steps) * 2.*np.pi * 50

print(hop/(2.*np.pi))
tf = times[len(times)-1]
delta = np.add(delta,fluc)
print(delta/(2.*np.pi))

###############################

#detuning = 0. * Hz * 2. * np.pi
D = 57. * Hz * 2. * np.pi
#delta = np.add(np.divide(Onsite,2.) , detuning) 

#hop_eff = np.sqrt(2.) * (pow(np.subtract(delta,D),-1) + pow(np.subtract(np.subtract(Onsite,delta), D),-1) + pow(np.add(delta,D),-1) + pow(np.add(np.subtract(Onsite, delta),D),-1) )/2. * pow(hop,2)
###############################

m_vals = []
hop_vals = []



######## -- DEFINE FUNCTIONS -- #########
def print_state(psi_vec):
    for i in range(0,len(psi_vec)):
        if(abs(psi_vec[i])**2 > 0.005):
            state_str = "".join(str(int((basis[i]//basis.sps**(L-j-1))%basis.sps)) for j in range(L))
            print("State:  |{}> ".format(state_str) + "    Probability:  " + str(abs(psi_vec[i])**2) )
    return 0

#def ramp_m(t):												# Ramp of Onsite energy U
#    m_out = 0.5*np.interp(t,times,Onsite) - np.interp(t,times,delta)
#    m_vals.append(m_out/(2.*np.pi))
#    return m_out
#ramp_m_args=[]
									                    
#def ramp_hop(t):                                            # Ramp of hopping element
#    hop_out =  np.interp(t, times, hop_eff)
#    hop_vals.append(hop_out/(2.*np.pi))
#    return hop_out
#ramp_hop_args=[]

def ramp_m(t):												# Ramp of Onsite energy U
    t_ind = int( (t/tf)*(len(times)-1) )				# interpolates between time data points from experimental data
    if (t < tf):
        m_out = Onsite[t_ind]/2. - delta[t_ind]                   			# Sets U to onsite energy from data at times smaller than the max data time.
    else:													# Also: Shift U upwards if we pick another small delta, such that Ramp is more or less symmetric around critical value
        m_out = 100000 								# Beyond times of exp. input, return some arbitray value where we notice something went wrong
    return m_out
ramp_m_args=[]

def ramp_U(t):
	t_ind = int( (t/tf)*(len(times)-1) )
	if (t < tf):
		U_out = Onsite[t_ind] 
	else:
		U_out = 100000 
	return U_out
ramp_U_args=[]

def ramp_delta(t):
	t_ind = int( (t/tf)*(len(times)-1) )
	if (t < tf):
		delta_out = delta[t_ind] 
	else:
		delta_out = 100000 
	return delta_out
ramp_delta_args=[]
									# Same procedure for hopping element
def ramp_hop(t):
	if(t < tf):
		hop_out = np.sqrt(2) * (1./(ramp_delta(t)-D) + 1./(ramp_U(t)  - ramp_delta(t) - D) + 1./(ramp_delta(t)+D) + 1./(ramp_U(t)  - ramp_delta(t) + D) )/2 * hop[int( (t/tf)*(len(times)-1) )]**2 
	else:
		hop_out = 0
	return hop_out
ramp_hop_args=[]

#def ramp_hop(t):
#    if(t < tf):
#        hop_out =  hop_eff[int( (t/tf)*(len(times)-1) )]
#    else:
#        hop_out = 0
#    return hop_out
#ramp_hop_args=[]

#for t in range(0,len(times)-1):						# Save the values for U and hop
 #   m_vals.append((Onsite[t]/2. - delta[t])/(2.*np.pi))
  #  hop_vals.append((hop_eff[t])/(2.*np.pi))
	
##### define model parameters #############
L = 13			# system size
a = 1


folder = 'data_spin/'

folder_save = folder + 'PBC_L'+str(L)
if not os.path.exists(folder_save):
	os.makedirs(folder_save)




##### compute 2-level boson basis
basis = spin_basis_1d(L, Nup=None, m=None, S='1',a=1,kblock=0 )


##### Building initial state |+++++++++++... ++>

offset = 1.
init  = [[offset,i,i] for i in range(0,L)]

dynamic = []
static_init = [ 
            ["zz",init]
         ]

H_init = hamiltonian(static_init,dynamic,basis=basis,dtype=np.complex128,check_herm=True)

E_init, psi_init = H_init.eigsh(k=1,which="SA",maxiter=1E10)
print("Initial_state energy",E_init)
psi_init = psi_init[:,0]
psi_init = psi_init.reshape((-1,))
print("Initial state")
print(np.abs(psi_init)**2)
#print(basis)
del H_init

#### Building Hamiltonian for dynamics
mass_pref=1.
#mass0 = [[ m,i] for i in range(0,L)]

#mass1 = [[+0.5*m,i,(i+1)%L] for i in range(0,L)]
#mass2 = [[-0.5*m,i,i,(i+1)%L,(i+1)%L] for i in range(0,L)]
#mass3 = [[+0.5*m,i,(i+1)%L,(i+1)%L] for i in range(0,L)]
#mass4 = [[-0.5*m,i,i,(i+1)%L] for i in range(0,L)]
#mass5 = [[ 1*m,i,i] for i in range(0,L)]

mass1 = [[-0.25*mass_pref,i,(i+1)%L] for i in range(0,L)]
mass2 = [[+0.25*mass_pref,i,i,(i+1)%L,(i+1)%L] for i in range(0,L)]
mass3 = [[+0.25*mass_pref,i,(i+1)%L,(i+1)%L] for i in range(0,L)]
mass4 = [[-0.25*mass_pref,i,i,(i+1)%L] for i in range(0,L)]
mass5 = [[-  2.*mass_pref,i,i] for i in range(0,L)]

J=np.sqrt(2)/2  *np.sqrt(2)
pre = 1j*J/(8.*np.sqrt(2))

hop1  = [[ pre ,i,i,(i+1)%L,(i+1)%L,(i+1)%L,(i+1)%L,(i+1)%L] for i in range(0,L)]
hop2  = [[-pre ,i,i,(i+1)%L,(i+1)%L,(i+1)%L,(i+1)%L,(i+1)%L] for i in range(0,L)]

hop3  = [[ pre ,i,i,i,i,i,(i+1)%L,(i+1)%L] for i in range(0,L)]
hop4  = [[-pre ,i,i,i,i,i,(i+1)%L,(i+1)%L] for i in range(0,L)]

if GAP_SIM:
    gap = [[protect * 0.25*0.25 ,i,i,i,i,(i+1)%L,(i+1)%L,(i+1)%L,(i+1)%L] for i in range(0,L)]
    bias_Z2 = [[bias * 0.25 ,i,i,i,i] for i in range(0,L)]
static  = []
dynamic = [ 
            #["I",mass0,ramp_m,ramp_m_args], 
            ["zz",mass1,ramp_m,ramp_m_args], ["zzzz",mass2,ramp_m,ramp_m_args], ["zzz",mass3,ramp_m,ramp_m_args], ["zzz",mass4,ramp_m,ramp_m_args], ["zz",mass5,ramp_m,ramp_m_args],
            ["-++--++",hop1,ramp_hop,ramp_hop_args], ["-+--++-",hop2,ramp_hop,ramp_hop_args],
            ["-++--+-",hop3,ramp_hop,ramp_hop_args], ["++--++-",hop4,ramp_hop,ramp_hop_args]

         ]
if GAP_SIM:
    protection_term = ["++----++",gap]
    bias_term = ["++--",bias_Z2]
    static.append(protection_term)

H = hamiltonian(static,dynamic,basis=basis,dtype=np.complex128,check_herm=True)

######### Observables ##########
norm = 1./L
#pair density
density1 = [[ norm,i] for i in range(0,L)]
density2 = [[-norm,i,i] for i in range(0,L)]

static_density = [["I",density1],["zz",density2]]
dynamic = []
density = hamiltonian(static_density,dynamic,basis=basis,dtype=np.float64,check_herm=True)

############ -- Gap -- #############

orderparam = []
E1 = []
E2 = []
E3 = []
if GAP_SIM:
    for t in range(0,len(times)-1):
        eigsh_args={"k":3,"which":"SA","maxiter":1E4,"return_eigenvectors":False}
        E3_val,E2_val,E1_val=H.eigsh(time=times[t],**eigsh_args)
        proxy, groundstate = H.eigsh(time=times[t],k=1,which="SA",maxiter=1E10)
        
        orderparam.append(np.real(density.expt_value(groundstate)))
        E1.append(E1_val)
        E2.append(E2_val)
        E3.append(E3_val)

########## TIME evolution #######
overlap = []

pair_density = []
psi = psi_init
#print('Initial overlap  ',np.real(np.dot(psi,psi_init)) )
#pair_density.append(np.real(density.expt_value(psi)))
E_0 = np.vdot(psi_init,H.dot(psi_init))
print("Initial_state energy",E_0)
if TIME_EVOLUTION:
    for t in range(0,len(times)):
        print("time ",t)
        print(times[t]) 
        print(np.real(density.expt_value(psi)))
        #print(ramp_m(times[t])/(2.*np.pi))
        pair_density.append(np.real(density.expt_value(psi)))
        m_vals.append(ramp_m(times[t]))
        hop_vals.append(ramp_hop(times[t]))
        overlap.append(np.real(np.vdot(psi,psi_init)))
        try:
            psi = H.evolve(psi,times[t],times[t+1])
        except:
            print('Final time reached')
        print("State evolved")

print(times, len(times))
print(pair_density, len(pair_density))
np.savetxt(folder_save+'/pair_density.txt',pair_density)
np.savetxt(folder_save+'/time.txt',times)
np.savetxt(folder_save+'/m_vals.txt',m_vals)
np.savetxt(folder_save+'/hop_vals.txt',hop_vals)
np.savetxt(folder_save+'/overlap.txt',overlap)

np.savetxt(folder_save+'/orderparameter.txt',orderparam)
np.savetxt(folder_save+'/E1.txt',E1)
np.savetxt(folder_save+'/E2.txt',E2)
np.savetxt(folder_save+'/E3.txt',E3)
