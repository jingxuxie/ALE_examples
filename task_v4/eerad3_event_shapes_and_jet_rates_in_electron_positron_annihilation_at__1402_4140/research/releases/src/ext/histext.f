c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c-----------------------------------------------------------------------
c     Subroutine to fetch histograms and associated data.
c-----------------------------------------------------------------------       

c     Fetch number of booked histograms.
      integer(c_int) function nHist() bind(C, name="nHist")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), parameter :: nhisto=100
      integer(c_int)            :: jhist
      character(50)             :: stringhist(nhisto)
      common/histnew/jhist,stringhist
      nHist = jhist
      return
      end

************************************************************************

c     Fetch name of histogram with ID 'idhis'.
      type(c_ptr) function histName(idhis) bind(C, name="histName")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in):: idhis
      integer(c_int), parameter :: nhisto=100
      integer(c_int)            :: jhist
      integer(c_int), parameter :: slen=50
      character(slen), target   :: string
      character(slen)           :: stringhist(nhisto)
      common/histnew/jhist,stringhist
      string = stringhist(idhis)//c_null_char
      histName = c_loc(string)
      return
      end

************************************************************************

c     Fetch number of bins in histogram with ID 'idhis'.
      integer(c_int) function nBins(idhis) bind(C, name="nBins")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: idhis
      integer(c_int), parameter         :: nhisto=100
      integer(c_int), dimension(nhisto) :: ibin
      real(c_double), dimension(nhisto) :: hmin,hwidth
      common/hispar/hmin,hwidth,ibin
      nBins = ibin(idhis)
      return
      end

************************************************************************

c     Fetch lowest bin edge in histogram with ID 'idhis'.
      real(c_double) function xMin(idhis) bind(C, name="xMin")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: idhis
      integer(c_int), parameter         :: nhisto=100
      integer(c_int), dimension(nhisto) :: ibin
      real(c_double), dimension(nhisto) :: hmin,hwidth
      common/hispar/hmin,hwidth,ibin
      xMin = hmin(idhis)
      return
      end

************************************************************************

c     Fetch highest bin edge in histogram with ID 'idhis'.
      real(c_double) function xMax(idhis) bind(C, name="xMax")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: idhis
      integer(c_int), parameter         :: nhisto=100
      integer(c_int), dimension(nhisto) :: ibin
      real(c_double), dimension(nhisto) :: hmin,hwidth
      common/hispar/hmin,hwidth,ibin
      xMax = hmin(idhis)+dble(ibin(idhis))*hwidth(idhis)
      return
      end

c-----------------------------------------------------------------------
c     Subroutines to fetch data of a single histogram.
c-----------------------------------------------------------------------

c     Write bin contents to common block 'bins'.
      subroutine writeHist(idhis,xMin,xMax,wt,wt2,nn)
     .     bind(C, name="writeHist")
      use, intrinsic :: iso_c_binding
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      integer(kind=c_int), intent(in) :: idhis
      common/hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(6,idhis,ibin(idhis),hmin(idhis),hwidth(idhis))
      return
      end

************************************************************************

c     Fetch sum of weights in bin 'ibin'.
c     Note: first call writeHist above.
      real(c_double) function wt(ibin) bind(C, name="wt")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: ibin
      integer(c_int), parameter         :: maxbin=400
      integer(c_int), dimension(maxbin) :: nc
      real(c_double), dimension(maxbin) :: w,w2
      common/bins/w,w2,nc
      wt = w(ibin)
      return
      end

************************************************************************

c     Fetch sum of squared weights in bin 'ibin'.
c     Note: first call writeHist above.
      real(c_double) function wt2(ibin) bind(C, name="wt2")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: ibin
      integer(c_int), parameter         :: maxbin=400
      integer(c_int), dimension(maxbin) :: nc
      real(c_double), dimension(maxbin) :: w,w2
      common/bins/w,w2,nc
      wt2 = w2(ibin)
      return
      end

************************************************************************

c     Fetch number of entries in bin 'ibin'.
c     Note: first call writeHist above.
      integer(c_int) function n(ibin) bind(C, name="n")
      use, intrinsic :: iso_c_binding
      implicit none
      integer(c_int), intent(in)        :: ibin
      integer(c_int), parameter         :: maxbin=400
      integer(c_int), dimension(maxbin) :: nc
      real(c_double), dimension(maxbin) :: w,w2
      common/bins/w,w2,nc
      n = nc(ibin)
      return
      end

c-----------------------------------------------------------------------
