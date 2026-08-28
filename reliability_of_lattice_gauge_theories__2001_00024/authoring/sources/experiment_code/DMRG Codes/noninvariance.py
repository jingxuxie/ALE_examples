#!/usr/bin/python
# -*- coding: utf-8 -*-
import glob, os, sys
import subprocess as sp
import re
from decimal import *
import numpy as np
import time

storageFolder = '/data2/sclms/halimeh/QuantumLinkModel/new/job'
L = 32
Nmax = 2
initialCnt = 0
finalCnt = 120
dt = 0.001
counter = 0
for tnc in range(200):
    if os.path.exists(storageFolder+str(tnc)+'/psi.t0.12'):
        print('Job '+str(tnc)+' has finished. Checking for processing...')
        counter = counter+1

        if os.path.exists(storageFolder+str(tnc)+'/done_noninvariance.txt'):
            print('Job '+str(tnc)+' already processed.')
        else:
            print('Job '+str(tnc)+' not processed. Processing now...')
            t = 0
            for cnt in np.arange(initialCnt,finalCnt+1,1):
                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj001 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj001 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj001_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj100 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj100 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj100_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj101 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj101 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj101_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj011 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj011 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj011_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj110 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj110 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj110_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj210 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj210 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj210_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                print('rm temp.txt')
                os.system('rm temp.txt')
                print('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj012 > temp.txt')
                os.system('mp-expectation '+storageFolder+str(tnc)+'/psi.t'+str(t)+' lattice_analysis:Proj012 > temp.txt')
                f = open('temp.txt','r')
                x = f.readlines()
                f.close()
                f = open('Proj012_L'+str(L)+'_Nmax'+str(Nmax)+'_job'+str(tnc)+'.txt','a')
                f.write(x[0].replace('(', '').replace(')', ' ').replace(',', ' ').split(' ')[0]+' ')
                f.close()

                t = round(t+dt,3)

            f = open(storageFolder+str(tnc)+'/done_noninvariance.txt','w')
            f.write(str(1))
            f.close()
    else:
        print('JOB '+str(tnc)+' STILL RUNNING!!!')

print(str(counter)+' jobs have finished.')
