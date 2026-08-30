#! env python3

import os
import ctypes as ct
from platform import system

class EERAD3:
    # Initialise the API.
    def __init__(self, path=''):
        # Import the shared library.
        if path=='':
            path = os.path.dirname(os.path.realpath(__file__))
            path = path[:-5]+"lib"
        if path[-1] != "/": path = path+"/"
        libname = "libeerad3.dylib" if system().upper()=="DARWIN" \
            else "libeerad3.so"
        self.eerad3lib = ct.CDLL(path+libname)
        # Set return types of functions with c bindings.
        self.eerad3lib.nHist.restype = ct.c_int
        self.eerad3lib.histName.restype = ct.POINTER(ct.c_char * 50)
        self.eerad3lib.nBins.restype = ct.c_int
        self.eerad3lib.xMin.restype  = ct.c_double
        self.eerad3lib.xMax.restype  = ct.c_double
        self.eerad3lib.n.restype     = ct.c_int
        self.eerad3lib.wt.restype    = ct.c_double
        self.eerad3lib.wt2.restype   = ct.c_double
        # Prevent stupid things from happening.
        self.isInit = False

    # Initialise EERAD3.
    def init(self, iseed, infile):
        f = infile.encode()
        seed = ct.c_int(iseed)
        self.eerad3lib.init_ext(ct.byref(seed), f, len(f))
        self.isInit = True

    # Main routine for cross-section calculation.
    def cross(self):
        if not self.isInit:
            print("EERAD3 is not initialised")
            quit()
        avg = ct.c_double(0.0)
        sd  = ct.c_double(0.0)
        iproc = ct.c_int(1)
        self.eerad3lib.cross_ext(ct.byref(avg), ct.byref(sd), ct.byref(iproc))
        return avg.value, sd.value

    # Fetch all histograms.
    def getHists(self):
        if not self.isInit:
            print("EERAD3 is not initialised")
            quit()
        nHist = self.eerad3lib.nHist()
        hists = {}
        for i in range(1,nHist+1):
            ihist = ct.c_int(i)
            self.eerad3lib.writeHist(ct.byref(ihist))
            hName = self.eerad3lib.histName(ct.byref(ihist))
            hName = hName.contents.value.decode().strip()
            nBins = self.eerad3lib.nBins(ct.byref(ihist))
            xMin  = self.eerad3lib.xMin(ct.byref(ihist))
            xMax  = self.eerad3lib.xMax(ct.byref(ihist))
            xMin = xMin if abs(xMin)>1e-15 else 0.
            xMax = xMax if abs(xMax)>1e-15 else 0.
            xWidth = (xMax-xMin)/nBins
            xBins = [xMin+i*xWidth for i in range(0,nBins+1)]
            wt  = []
            wt2 = []
            n   = []
            for i in range(1,nBins+1):
                ibin = ct.c_int(i)
                wt.append(self.eerad3lib.wt(ct.byref(ibin)))
                wt2.append(self.eerad3lib.wt2(ct.byref(ibin)))
                n.append(self.eerad3lib.n(ct.byref(ibin)))

            hists[hName] = { 'id' : ihist.value,
                             'xMin' : xMin,
                             'xMax' : xMax,
                             'nBins' : nBins,
                             'bins' : xBins,
                             'wt' : wt,
                             'wt2' : wt2,
                             'n' : n}
        return hists
