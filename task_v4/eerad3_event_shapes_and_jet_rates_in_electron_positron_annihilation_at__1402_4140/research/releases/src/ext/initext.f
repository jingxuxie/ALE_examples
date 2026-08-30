c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Subroutines for initialisation.

c-----------------------------------------------------------------------
c     Subroutine to read input file and initialise common blocks.
c-----------------------------------------------------------------------       

      subroutine init_ext(iseed, infile, slen) bind(C, name="init_ext")
      use, intrinsic :: iso_c_binding
      implicit real*8(a-h,o-z)
      integer(c_int), intent(in)        :: iseed
      integer(c_int), intent(in), value :: slen
      character(c_char), intent(in)     :: infile(slen)
      character(len=slen) :: fstring
      integer, parameter :: nhisto=100
      real(8), parameter :: pi=3.141592653589793238d0
      integer            :: stat
      integer            :: iseeds(1:2,0:9999),icolmax(0:2)
      integer            :: j,jhist
      integer            :: i1,i2
      character(len=slen) :: froot
      character(50)      :: stringhist(nhisto)
      character(10)      :: line
      character(4)       :: suffix
      character(8)       :: prefix,tmpprfx
      character(4)       :: channel
      character(20)      :: fname
c     Common blocks.
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/tcuts/ymin,y0
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2(1:5),shat
      common/rseeds/i1,i2
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2)
      common/outfile/fname,prefix,suffix
      common/ivegas/iwarm,iprod
      common/histnew/jhist,stringhist
      include '../core/iseeds.f'

c     Print EERAD3 banner.
      call printBanner()
      
c     Translate run-card name to fortran character array.
      froot = ''
      do j=1,slen
         if (infile(j) == c_null_char) exit
         froot(j:j) = infile(j)
      end do

c     Set seeds.
      if (iseed.lt.0.or.iseed.gt.9999)then
         stop "Unknown seed provided"
      endif
      i1 = iseeds(1,iseed)
      i2 = iseeds(2,iseed)

c     Read run card.
      call readruncard(froot, stat)

c     Propagate settings.
      if (itmax1.gt.0) iwarm = 1
      if (itmax2.gt.0) iprod = 1

c     Check consistency of input parameters.
      if (iproc.ne.1 .and. iproc.ne.21 .and. iproc.ne.22)then
         stop 'Unknown process id'
      endif
      if (nshot3.lt.1)then
         if (njets.eq.3.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot3 = 0'
         endif
      endif
      if (nshot4.lt.1)then
         if (njets.eq.4.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot4 = 0'
         endif
      endif
      if (nshot5(1).lt.1.or.nshot5(2).lt.1)then
         if (njets.eq.5.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot5 = 0'
         endif
      endif
      if (y0.gt.1d-4)then
         y0 = 1d-4
         write(6,*) 'Warning: y0 too large'
         write(6,'(A21,E4.1)') 'Reset to y0 = ',y0
      endif
      if (y0.lt.1d-12)then
         y0 = 1d-12
         write(6,*) 'Warning: y0 too small'
         write(6,'(A21,E4.1)') 'Reset to y0 = ',y0
      endif
      icolmax(0) = 0
      if (iproc.eq.22) icolmax(0) = 2
      icolmax(1) = 3
      if (iproc.eq.22) icolmax(1) = 4
      icolmax(2) = 6
      if (iproc.eq.22) icolmax(2) = 7
      nord = njets+abs(nloop)-3
      if (icol.le.0.or.icol.gt.icolmax(abs(nord))) icol = 0
      if (njets.eq.3.and.nloop.gt.2)then
         stop 'N3LO not implemented'
      endif
      if (njets.eq.4.and.nloop.gt.1)then
         stop 'NNLO not implemented for njets > 3'
      endif
      if (njets.eq.5.and.nloop.gt.2)then
         stop 'NLO not implemented for njets > 4'
      endif

c     Set output file names.
      if (iproc.eq.1)  fname='Zqq'
      if (iproc.eq.21) fname='Hbb'
      if (iproc.eq.22) fname='Hgg'
      fname = fname(1:3)//'.'//char(njets+48)//'j.0000'
      if (iseed.lt.10)then
         write(fname(11:11),'(I1)') iseed
      elseif (iseed.ge.10 .and. iseed.lt.100)then
         write(fname(10:11),'(I2)') iseed
      elseif (iseed.ge.100 .and. iseed.lt.1000)then
         write(fname(9:11),'(I3)') iseed
      elseif (iseed.ge.1000 .and. iseed.lt.10000)then
         write(fname(8:11),'(I4)') iseed
      endif
      channel = 'LO'
      if (ichan.eq.10) channel = 'NLO'
      if (ichan.eq.11) channel = 'V'
      if (ichan.eq.12) channel = 'R'
      if (ichan.eq.20) channel = 'NNLO'
      if (ichan.eq.21) channel = 'VV'
      if (ichan.eq.22) channel = 'RV'
      if (ichan.eq.23) channel = 'RR'
      fname  = fname(1:11)//'.'//trim(channel)//'.'//char(icol+48)//'.'
      fname  = trim(fname)
      suffix = ".dat"
      idist  = 0
      ymin   = 1d0

c     Initialise histogram counter.
      jhist = 0
      stringhist(:) = ''

c     Set particle masses.
      do i=1,5 
         rm2(i) = 0d0
      enddo

c     Set constants.
      as     = 2d0*pi
      nf     = 5d0
      cflo   = 4d0/3d0
      cf     = cflo
      tr     = 0.5d0*nf
      ca     = 3d0
      cn     = ca

c     Print settings.
      call printSettings()

      return
      end

c-----------------------------------------------------------------------
