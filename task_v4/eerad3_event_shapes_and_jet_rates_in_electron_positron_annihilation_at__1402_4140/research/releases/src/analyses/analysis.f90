! This file is part of the EERAD3 NNLO event generator.
! Copyright (C) 2025 the authors.
! This program is free software: you can redistribute it and/or
! modify it under the terms of the GNU General Public License as
! published by the Free Software Foundation, either version 3 of
! the License, or any later version. See COPYING for details.

module analysis_mod
  implicit none

  ! Observables
  real(8) :: y45,y34,y23
  real(8) :: Cpar,Dpar,Spar,Apar,Planar,Tpar
  real(8) :: Tmajor,Tminor,Opar,em2h,em2l,em2d
  real(8) :: Bmax,Bmin,Bsum,Bdiff
  real(8) :: FC0,FC1,FC2,FC3
  real(8) :: BKS0,BKS1,BKS2,BKS3
  real(8) :: tausd(3),rhosd(3)
  
  ! Cuts.
  real(8) :: cut,ycut,Bcut,Ccut,Dcut,Fcut,Tcut,em2hcut,em2lcut

  ! Histogram IDs.
  integer :: iT1,iT2,iTL,iTL10
  integer :: iC1,iC2,iCL,iCL10
  integer :: iMH1,iMH2,iMHL,iMHL10
  integer :: iBW1,iBW2,iBWL,iBWL10
  integer :: iBT1,iBT2,iBTL,iBTL10
  integer :: iF0,iF1,iF2,iF3
  integer :: iTsd0,iTsd0L,iTsd0L10
  integer :: iTsd1,iTsd1L,iTsd1L10
  integer :: iTsd2,iTsd2L,iTsd2L10
  integer :: iMsd0,iMsd0L,iMsd0L10
  integer :: iMsd1,iMsd1L,iMsd1L10
  integer :: iMsd2,iMsd2L,iMsd2L10
  integer :: iTMin1,iTMin2,iTMinL,iTMinL10
  integer :: iD1,iD2,iDL,iDL10
  integer :: iML1,iML2,iMLL,iMLL10
  integer :: iBN1,iBN2,iBNL,iBNL10
  integer :: iy23,iLogy23,iLog10y23
  integer :: iy34,iLogy34,iLog10y34
  integer :: iy45,iLogy45,iLog10y45
  integer :: iR3,iR4,iR5

  ! Common blocks - do not touch!
  integer :: iaver,imom,idist,iang,idebug
  integer :: iproc,nloop,icol,njets,ichan
  common/intech/iaver,imom,idist,iang,idebug
  common/inphys/iproc,nloop,icol,njets,ichan

  ! Jacobian factor for log10 binning.
  !real(8), parameter :: dl10=2.302585092994046d0

contains

  ! Initialise analysis.
  subroutine initanalysis()
    implicit none
    integer, external :: bookhist
    character(1)      :: star 
    character(9)      :: short
    character(39)     :: sblank
    character(60)     :: starline,sno,slong

    ! Read cuts.
    call readparm('cut         ', cut,    1d-5)
    call readparm('ycut        ', ycut,    cut)
    call readparm('Bcut        ', Bcut,    cut)
    call readparm('Ccut        ', Ccut,    cut)
    call readparm('Dcut        ', Dcut,    cut)
    call readparm('Fcut        ', Fcut,    cut)
    call readparm('Tcut        ', Tcut,    cut)
    call readparm('m2hcut      ', em2hcut, cut)
    call readparm('m2lcut      ', em2lcut, cut)

    ! Print cuts.
    starline = &
         '************************************************************'
    sblank = ' '
    sno = ' '
    star = '*'
    write(6,*) sno
    write(6,*) star,starline,star
    write(6,*) star,sno,star
    slong = ' Cuts:'
    write(6,*) star,slong,star
    write(6,*) star,sno,star
    short = '  ymn >= '
    write(6,10)star,short,ycut,sblank,star
    short = '  B   >= '
    write(6,10)star,short,Bcut,sblank,star
    short = '  C   >= '
    write(6,10)star,short,Ccut,sblank,star
    short = '  D   >= '
    write(6,10)star,short,Dcut,sblank,star
    short = '  T   >= '
    write(6,10)star,short,Tcut,sblank,star
    short = '  FCx >= '
    write(6,10)star,short,Fcut,sblank,star
    short = '  MH2 >= '
    write(6,10)star,short,em2hcut,sblank,star
    short = '  ML2 >= '
    write(6,10)star,short,em2lcut,sblank,star
    write(6,*) star,sno,star
    write(6,*) star,starline,star

    ! Book histograms.
    ! 1-T.
    iT1   = bookhist('T1',       0d0, 0.5d0, 200)
    iT2   = bookhist('T2',       0d0, 0.5d0, 200)
    iTL   = bookhist('LogT',   -10d0,   0d0, 200)
    iTL10 = bookhist('Log10T',  -5d0,   0d0, 200)

    ! C.
    iC1   = bookhist('C1',       0d0,  1d0, 400)
    iC2   = bookhist('C2',       0d0,  1d0, 400)
    iCL   = bookhist('LogC',   -10d0,  0d0, 200)
    iCL10 = bookhist('Log10C',  -5d0,  0d0, 200)

    ! rho=MH^2/s.
    iMH1   = bookhist('MH1',      0d0, 0.5d0, 200)
    iMH2   = bookhist('MH2',      0d0, 0.5d0, 200)
    iMHL   = bookhist('LogMH',  -10d0,   0d0, 200)
    iMHL10 = bookhist('Log10MH', -5d0,   0d0, 200)

    ! BW.
    iBW1   = bookhist('BW1',       0d0, 0.5d0, 200)
    iBW2   = bookhist('BW2',       0d0, 0.5d0, 200)
    iBWL   = bookhist('LogBW',   -10d0,   0d0, 200)
    iBWL10 = bookhist('Log10BW',  -5d0,   0d0, 200)

    ! BT.
    iBT1   = bookhist('BT1',       0d0, 0.5d0, 200)
    iBT2   = bookhist('BT2',       0d0, 0.5d0, 200)
    iBTL   = bookhist('LogBT',   -10d0,   0d0, 200)
    iBTL10 = bookhist('Log10BT',  -5d0,   0d0, 200)

    ! FCx.
    iF0 = bookhist('LogFC0', -10d0, 0d0, 200)
    iF1 = bookhist('LogFC1', -10d0, 0d0, 200)
    iF2 = bookhist('LogFC2', -10d0, 0d0, 200)
    iF3 = bookhist('LogFC3', -10d0, 0d0, 200)

    ! Soft-drop thrust.
    iTsd0    = bookhist('Tsd_1d-1_0d0',        0d0, 0.5d0, 200)
    iTsd0L   = bookhist('LogTsd_1d-1_0d0',   -10d0,   0d0, 200)
    iTsd0L10 = bookhist('Log10Tsd_1d-1_0d0',  -5d0,   0d0, 200)
    iTsd1    = bookhist('Tsd_1d-1_1d0',        0d0, 0.5d0, 200)
    iTsd1L   = bookhist('LogTsd_1d-1_1d0',   -10d0,   0d0, 200)
    iTsd1L10 = bookhist('Log10Tsd_1d-1_1d0',  -5d0,   0d0, 200)
    iTsd2    = bookhist('Tsd_1d-1_2d0',        0d0, 0.5d0, 200)
    iTsd2L   = bookhist('LogTsd_1d-1_2d0',   -10d0,   0d0, 200)
    iTsd2L10 = bookhist('Log10Tsd_1d-1_2d0',  -5d0,   0d0, 200)

    ! Soft-drop jet mass.
    iMsd0    = bookhist('Msd_1d-1_0d0',        0d0, 0.5d0, 200)
    iMsd0L   = bookhist('LogMsd_1d-1_0d0',   -10d0,   0d0, 200)
    iMsd0L10 = bookhist('Log10Msd_1d-1_0d0',  -5d0,   0d0, 200)
    iMsd1    = bookhist('Msd_1d-1_1d0',        0d0, 0.5d0, 200)
    iMsd1L   = bookhist('LogMsd_1d-1_1d0',   -10d0,   0d0, 200)
    iMsd1L10 = bookhist('Log10Msd_1d-1_1d0',  -5d0,   0d0, 200)
    iMsd2    = bookhist('Msd_1d-1_2d0',        0d0, 0.5d0, 200)
    iMsd2L   = bookhist('LogMsd_1d-1_2d0',   -10d0,   0d0, 200)
    iMsd2L10 = bookhist('Log10Msd_1d-1_2d0',  -5d0,   0d0, 200)

    ! TMinor.
    iTMin1   = bookhist('TMin1',       0d0, 0.5d0, 200)
    iTMin2   = bookhist('TMin2',       0d0, 0.5d0, 200)
    iTMinL   = bookhist('LogTMin',   -10d0,   0d0, 200)
    iTMinL10 = bookhist('Log10TMin',  -8d0,   0d0, 200)

    ! D.
    iD1   = bookhist('D1',       0d0, 1d0, 200)
    iD2   = bookhist('D2',       0d0, 1d0, 200)
    iDL   = bookhist('LogD',   -10d0, 0d0, 200)
    iDL10 = bookhist('Log10D',  -8d0, 0d0, 200)

    ! ML^2/s.
    iML1   = bookhist('ML1',       0d0, 0.2d0, 200)
    iML2   = bookhist('ML2',       0d0, 0.2d0, 200)
    iMLL   = bookhist('LogML',   -10d0,   0d0, 200)
    iMLL10 = bookhist('Log10ML',  -8d0,   0d0, 200)

    ! BN.
    iBN1   = bookhist('BN1',       0d0, 0.2d0, 200)
    iBN2   = bookhist('BN2',       0d0, 0.2d0, 200)
    iBNL   = bookhist('LogBN',   -10d0,   0d0, 200)
    iBNL10 = bookhist('Log10BN',  -8d0,   0d0, 200)

    ! Jet-resolution scales.
    iy23      = bookhist('y23',       0d0, 1d0, 400)
    iLogy23   = bookhist('Logy23',  -10d0, 0d0, 200)
    iLog10y23 = bookhist('Log10y23', -5d0, 0d0, 200)
    iy34      = bookhist('y34',       0d0, 1d0, 400)
    iLogy34   = bookhist('Logy34',  -10d0, 0d0, 200)
    iLog10y34 = bookhist('Log10y34', -5d0, 0d0, 200)
    iy45      = bookhist('y45',       0d0, 1d0, 400)
    iLogy45   = bookhist('Logy45',  -10d0, 0d0, 200)
    iLog10y45 = bookhist('Log10y45', -5d0, 0d0, 200)

    ! Integrated jet rates.
    iR3 = bookhist('R3', -10d0, 0d0, 200)
    iR4 = bookhist('R4', -10d0, 0d0, 200)
    iR5 = bookhist('R5', -10d0, 0d0, 200)

    ! Print histogram information.
    call printhistdata()

10  format(1x,A,A,1pe12.4,A,A)
  end subroutine initanalysis

  ! Observables and cuts.
  subroutine ecuts_ana(npar,var,ipass)
    implicit none
    integer, intent(in)    :: npar
    integer, intent(inout) :: ipass
    real(8), intent(inout) :: var

    ! Calculate observables.
    call getjet(y45,y34,y23,npar,2,1)
    call getCD(Cpar,Dpar,npar)
    call getSAP(Spar,Apar,Planar,npar)
    call getT(Tpar,Tmajor,Tminor,Opar,em2h,em2l,em2d, &
         Bmax,Bmin,Bsum,Bdiff,FC0,FC1,FC2,FC3, &
         BKS0,BKS1,BKS2,BKS3,npar)
    call getSD(tausd(1),rhosd(1),npar,0.1d0,0d0)
    call getSD(tausd(2),rhosd(2),npar,0.1d0,1d0)
    call getSD(tausd(3),rhosd(3),npar,0.1d0,2d0)

    ! Set variable for cross section.
    call getvar(var)

    ! Apply cuts.
    ipass=0
    if (iaver.eq.0)then
       if (njets.eq.3)then
          if (y23.gt.ycut) ipass=1
          if (Bmax.gt.Bcut) ipass=1
          if (Bsum.gt.Bcut) ipass=1
          if (Cpar.gt.Ccut) ipass=1
          if (1d0-Tpar.gt.Tcut) ipass=1
          if (em2h.gt.em2hcut) ipass=1
          if (FC0.gt.Fcut) ipass=1
          if (FC1.gt.Fcut) ipass=1
          if (FC2.gt.Fcut) ipass=1
          if (FC3.gt.Fcut) ipass=1
          if (tausd(1).gt.Tcut) ipass=1
          if (tausd(2).gt.Tcut) ipass=1
          if (tausd(3).gt.Tcut) ipass=1
          if (rhosd(1).gt.em2hcut) ipass=1
          if (rhosd(2).gt.em2hcut) ipass=1
          if (rhosd(3).gt.em2hcut) ipass=1
       endif
       if (njets.eq.4)then
          if (y34.gt.ycut) ipass=1
          if (Tminor.gt.Tcut) ipass=1
          if (Dpar.gt.Dcut) ipass=1
          if (em2l.gt.em2lcut) ipass=1
          if (Bmin.gt.Bcut) ipass=1
       endif
       if (njets.eq.5)then
          if (y45.gt.ycut) ipass=1
       endif
    elseif (iaver.eq.1)then
       if (Bmax.gt.Bcut) ipass=1
    elseif (iaver.eq.2)then
       if (Cpar.gt.Ccut) ipass=1
    elseif (iaver.eq.3)then
       if (em2h.gt.em2hcut) ipass=1
    elseif (iaver.eq.4)then
       if (1-Tpar.gt.Tcut) ipass=1
    elseif (iaver.eq.5)then
       if (Bsum.gt.Bcut) ipass=1
    elseif (iaver.eq.6)then
       if (FC0.gt.Fcut) ipass=1
    elseif (iaver.eq.7)then
       if (FC1.gt.Fcut) ipass=1
    elseif (iaver.eq.8)then
       if (FC2.gt.Fcut) ipass=1
    elseif (iaver.eq.9)then
       if (FC3.gt.Fcut) ipass=1
    elseif (iaver.eq.10)then
       if (tausd(1).gt.Tcut) ipass=1
    elseif (iaver.eq.11)then
       if (tausd(2).gt.Tcut) ipass=1
    elseif (iaver.eq.12)then
       if (tausd(3).gt.Tcut) ipass=1
    elseif (iaver.eq.13)then
       if (rhosd(1).gt.em2hcut) ipass=1
    elseif (iaver.eq.14)then
       if (rhosd(2).gt.em2hcut) ipass=1
    elseif (iaver.eq.15)then
       if (rhosd(3).gt.em2hcut) ipass=1
    elseif (iaver.eq.16)then
       if (Tminor.gt.Tcut) ipass=1
    elseif (iaver.eq.17)then
       if (Dpar.gt.Dcut) ipass=1
    elseif (iaver.eq.18)then
       if (em2l.gt.em2lcut) ipass=1
    elseif (iaver.eq.19)then
       if (Bmin.gt.Bcut) ipass=1
    elseif (iaver.eq.20)then
       if (y23.gt.ycut) ipass=1
    elseif (iaver.eq.21)then
       if (y34.gt.ycut) ipass=1
    elseif (iaver.eq.22)then
       if (y45.gt.ycut) ipass=1
    endif

  end subroutine ecuts_ana

  ! Fill histograms.
  subroutine fillhists(wgt,npar)
    implicit none
    integer, intent(in) :: npar
    real(8), intent(in) :: wgt
    real(8)             :: var,wt
    integer             :: iy,nbin
    real(8)             :: ybin,dly,dly23,dly34,dly45

    call getvar(var)
    wt = wgt/var

    ! Classical three-jet event shapes.
    if (1d0-Tpar.gt.Tcut)then
       call histoa(iT1,1d0-Tpar,wt*(1d0-Tpar))
       call histoa(iT2,1d0-Tpar,wt)
       call histoa(iTL,dlog(1d0-Tpar),wt)
       call histoa(iTL10,dlog10(1d0-Tpar),wt)
    endif

    if (Cpar.gt.Ccut)then
       call histoa(iC1,Cpar,wt*Cpar)
       call histoa(iC2,Cpar,wt)
       call histoa(iCL,dlog(Cpar),wt)
       call histoa(iCL10,dlog10(Cpar),wt)
    endif

    if (em2h.gt.em2hcut)then
       call histoa(iMH1,em2h,wt*em2h)
       call histoa(iMH2,em2h,wt)
       call histoa(iMHL,dlog(em2h),wt)
       call histoa(iMHL10,dlog10(em2h),wt)
    endif

    if (Bmax.gt.Bcut)then
       call histoa(iBW1,Bmax,wt*Bmax)
       call histoa(iBW2,Bmax,wt)
       call histoa(iBWL,dlog(Bmax),wt)
       call histoa(iBWL10,dlog10(Bmax),wt)
    endif

    if (Bsum.gt.Bcut)then
       call histoa(iBT1,Bsum,wt*Bsum)
       call histoa(iBT2,Bsum,wt)
       call histoa(iBTL,dlog(Bsum),wt)
       call histoa(iBTL10,dlog10(Bsum),wt)
    endif

    ! Classical four-jet event shapes.
    if (Tminor.gt.Tcut)then
       call histoa(iTMin1,Tminor,wt*Tminor)
       call histoa(iTMin2,Tminor,wt)
       call histoa(iTMinL,dlog(Tminor),wt)
       call histoa(iTMinL10,dlog10(Tminor),wt)
    endif

    if (Dpar.gt.Dcut)then
       call histoa(iD1,Dpar,wt*Dpar)
       call histoa(iD2,Dpar,wt)
       call histoa(iDL,dlog(Dpar),wt)
       call histoa(iDL10,dlog10(Dpar),wt)
    endif

    if (em2l.gt.em2lcut)then
       call histoa(iML1,em2l,wt*em2l)
       call histoa(iML2,em2l,wt)
       call histoa(iMLL,dlog(em2l),wt)
       call histoa(iMLL10,dlog10(em2l),wt)
    endif

    if (Bmin.gt.Bcut)then
       call histoa(iBN1,Bmin,wt*Bmin)
       call histoa(iBN2,Bmin,wt)
       call histoa(iBNL,dlog(Bmin),wt)
       call histoa(iBNL10,dlog10(Bmin),wt)
    endif

    ! FCx observables
    if (FC0.gt.Fcut) call histoa(iF0,dlog(FC0),wt)
    if (FC1.gt.Fcut) call histoa(iF1,dlog(FC1),wt)
    if (FC2.gt.Fcut) call histoa(iF2,dlog(FC2),wt)
    if (FC3.gt.Fcut) call histoa(iF3,dlog(FC3),wt)

    ! Soft-drop observables
    if (tausd(1).gt.Tcut)then
       call histoa(iTsd0,tausd(1),wt*tausd(1))
       call histoa(iTsd0L,dlog(tausd(1)),wt)
       call histoa(iTsd0L10,dlog10(tausd(1)),wt)
    endif
    if (tausd(2).gt.Tcut)then
       call histoa(iTsd1,tausd(2),wt*tausd(2))
       call histoa(iTsd1L,dlog(tausd(2)),wt)
       call histoa(iTsd1L10,dlog10(tausd(2)),wt)
    endif
    if (tausd(3).gt.Tcut)then
       call histoa(iTsd2,tausd(3),wt*tausd(3))
       call histoa(iTsd2L,dlog(tausd(3)),wt)
       call histoa(iTsd2L10,dlog10(tausd(3)),wt)
    endif
    if (rhosd(1).gt.em2hcut)then
       call histoa(iMsd0,rhosd(1),wt*rhosd(1))
       call histoa(iMsd0L,dlog(rhosd(1)),wt)
       call histoa(iMsd0L10,dlog(rhosd(1)),wt)
    endif
    if (rhosd(2).gt.em2hcut)then
       call histoa(iMsd1,rhosd(2),wt*rhosd(2))
       call histoa(iMsd1L,dlog(rhosd(2)),wt)
       call histoa(iMsd1L10,dlog(rhosd(2)),wt)
    endif
    if (rhosd(3).gt.em2hcut)then
       call histoa(iMsd2,rhosd(3),wt*rhosd(3))
       call histoa(iMsd2L,dlog(rhosd(3)),wt)
       call histoa(iMsd2L10,dlog(rhosd(3)),wt)
    endif

    ! Differential jet rates (resolution scales).
    dly23 = -20d0
    dly34 = -20d0
    dly45 = -20d0
    if (y23.gt.ycut) dly23 = dlog(y23)
    if (y34.gt.ycut) dly34 = dlog(y34)
    if (y45.gt.ycut) dly45 = dlog(y45)
    if (y45.gt.ycut)then
       call histoa(iy45,y45,wt*y45)
       call histoa(iLogy45,dly45,wt)
       call histoa(iLog10y45,dlog10(y45),wt)
    endif
    if (y34.gt.ycut)then
       call histoa(iy34,y34,wt*y34)
       call histoa(iLogy34,dly34,wt)
       call histoa(iLog10y34,dlog10(y34),wt)
    endif 
    if (y23.gt.ycut)then
       call histoa(iy23,y23,wt*y23)
       call histoa(iLogy23,dly23,wt)
       call histoa(iLog10y23,dlog10(y23),wt)
    endif

    ! Integrated jet rates.
    nbin = 200
    ybin = 10d0/real(nbin)
    do iy = 0,nbin
       dly = -real(iy)*ybin
       if (dly.lt.dly23)then
          if (dly.lt.dly34)then
             if (dly.lt.dly45) call histoa(iR5,dly-ybin/2d0,wt*ybin)
             if (dly.ge.dly45) call histoa(iR4,dly-ybin/2d0,wt*ybin)
          else
             call histoa(iR3,dly-ybin/2d0,wt*ybin)
          endif
       endif
    enddo

  end subroutine fillhists

  ! Get variable for phase-space optimisation.
  subroutine getvar(var)
    implicit none
    real(8), intent(out) :: var

    var = 1d0
    if (iaver.eq.0)then
       if (njets.eq.3) var = y23
       if (njets.eq.4) var = y34
       if (njets.eq.5) var = y45
    elseif (iaver.eq.1)then
       var = Bmax
    elseif (iaver.eq.2)then
       var = Cpar
    elseif (iaver.eq.3)then
       var = em2h
    elseif (iaver.eq.4)then
       var = 1d0-Tpar
    elseif (iaver.eq.5)then
       var = Bsum
    elseif (iaver.eq.6)then
       var = FC0
    elseif (iaver.eq.7)then
       var = FC1
    elseif (iaver.eq.8)then
       var = FC2
    elseif (iaver.eq.9)then
       var = FC3
    elseif (iaver.eq.10)then
       var = tausd(1)
    elseif (iaver.eq.11)then
       var = tausd(2)
    elseif (iaver.eq.12)then
       var = tausd(3)
    elseif (iaver.eq.13)then
       var = rhosd(1)
    elseif (iaver.eq.14)then
       var = rhosd(2)
    elseif (iaver.eq.15)then
       var = rhosd(3)
    elseif (iaver.eq.16)then
       var = Tminor
    elseif (iaver.eq.17)then
       var = Dpar
    elseif (iaver.eq.18)then
       var = em2l
    elseif (iaver.eq.19)then
       var = Bmin
    elseif (iaver.eq.20)then
       var = y23
    elseif (iaver.eq.21)then
       var = y34
    elseif (iaver.eq.22)then
       var = y45
    endif
    var = var**imom

  end subroutine getvar

end module analysis_mod
