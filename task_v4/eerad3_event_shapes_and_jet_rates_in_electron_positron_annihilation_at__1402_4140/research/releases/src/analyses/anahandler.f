c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains the top-level subroutines for analyses.
c     These only call the subroutines relevant to the different
c     n-jet cases.

c-----------------------------------------------------------------------

c     Top-level subroutine to initialise, fill, and write histograms.
c     Depends on value of istat
c     0: book histograms
c     1: fill histograms
c     2: accumulate event errors for sweep and increase sweep counter
c     3: calculate standard deviation as error estimate
      subroutine bino(istat,wgt,npar)
      use analysis_mod, only : initanalysis, fillhists
      implicit none
      integer, intent(in)   :: istat,npar
      real(8), intent(in)   :: wgt
      integer, parameter    :: nhisto=100
      integer               :: i
      integer               :: iproc,nloop,icol,njets,ichan
c     Common blocks.
      common/inphys/iproc,nloop,icol,njets,ichan

c     Book histograms.
      if (istat.eq.0) call initanalysis()

c     Fill histograms.
      if (istat.eq.1) call fillhists(wgt,npar)

c     Event errors manipulation request, pipe through.
      if (istat.eq.2 .or. istat.eq.3)then
         do i=1,nhisto
            call histoe(istat,i)
         enddo
      endif

      return
      end

************************************************************************

c     Top-level subroutine for ecuts.
      subroutine ecuts(npar,var,ipass)
      use analysis_mod
      implicit none
      integer, intent(in)    :: npar
      integer, intent(inout) :: ipass
      real(8), intent(inout) :: var

      call ecuts_ana(npar,var,ipass)

      return
      end

************************************************************************

c     Top-level subroutine to write histograms to files.
      subroutine outfiles()
      implicit none
      integer, parameter :: nhisto=100
      integer            :: ihist,jhist
      character(50)      :: stringhist(nhisto)
      character(4)       :: suffix
      character(8)       :: prefix
      character(20)      :: fname
      common/histnew/jhist,stringhist
      common/outfile/fname,prefix,suffix

      call system('mkdir -p '//trim(adjustl(prefix)))
      do ihist=1,jhist
         if (stringhist(ihist).ne.'') call writehist(stringhist(ihist))
      enddo

      return
      end

c-----------------------------------------------------------------------
