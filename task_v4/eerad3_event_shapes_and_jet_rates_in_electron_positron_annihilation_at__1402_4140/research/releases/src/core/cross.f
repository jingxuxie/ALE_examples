c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Top-level cross-section subroutine.

c-----------------------------------------------------------------------

c     Top-level function to calculate cross-section.

      subroutine cross(ave,sd,iproc)
      implicit none
      integer, intent(in) :: iproc
      real(8) :: ave,sd
c     Externals.
      real(8), external :: sig3ZQa,sig4ZQa,sig5ZQa
      real(8), external :: sig3HBa,sig4HBa,sig5HBa
      real(8), external :: sig3HGa,sig4HGa,sig5HGa

c     Calculate differential cross section depending on process.
      if (iproc.eq.1)then
         call calcCross(ave,sd,sig3ZQa,sig4ZQa,sig5ZQa)
      elseif (iproc.eq.21)then
         call calcCross(ave,sd,sig3HBa,sig4HBa,sig5HBa)
      elseif (iproc.eq.22)then
         call calcCross(ave,sd,sig3HGa,sig4HGa,sig5HGa)
      endif

      return
      end

************************************************************************

c     Compute cross section (ave) with standard deviation (sd) from
c     itmax2 iterations.
      subroutine calcCross(ave,sd,sig3,sig4,sig5)
      implicit real*8(a-h,o-z)
      logical plot 
      logical, external :: activePS
      common/BVEG3/NDIM3,NCALL3,NPRN3
      common/BVEG4/NDIM4(1),NCALL4(1),NPRN4
      common/BVEG5/NDIM5(2),NCALL5(2),NPRN5
      common/plots/plot
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2)
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/phase/ips
      common/ivegas/iwarm,iprod
      external sig3,sig4,sig5

c     Set Vegas constants.
      nprn3=1
      nprn4=1
      nprn5=1
      ndim3=2
      ndim4(1)=5
      ndim5(1)=8
      ndim5(2)=8

c     Number of shots for warmup run.
      if (iprod.eq.1) then
         ncall3=nshot3/5d0
         ncall4(1)=nshot4/5d0
         do i=1,2
            ncall5(i)=nshot5(i)/5d0
         enddo
      else
         ncall3=nshot3
         ncall4(1)=nshot4
         do i=1,2
            ncall5(i)=nshot5(i)
         enddo
      endif
      plot=.false.

      init = 0
      if (iwarm.eq.1) then
         init = 1
      endif

c     Initialise analysis.
      call bino(0,0d0,0)

c     Initialize vegas.
c     init=1  cold start
c     init=0  input grid from previous run
      if (activePS(3))then
         call vegas3(init,sig3,ave3,sd3,chi2)
      endif
      if (activePS(4))then
         do ips4=1,1
            call vegas4a(init,sig4,ips4,ave4,sd4,chi2)
         enddo
      endif
      if(activePS(5))then
         do ips=1,2
            call vegas5(init,sig5,ips,ave5,sd5,chi2)
         enddo
      endif

c     Vegas sweeps with grid adjustments.
      if (init.eq.1)then
         write(6,'(/,A)') " >> Starting warmup run..."
         do it=1,itmax1
            write(6,18) it
            if (activePS(3))then
               call vegas3(3,sig3,ave3,sd3,chi2)
               write(6,10) ave3,sd3
            endif
            if (activePS(4))then
               rsum4 = 0d0
               sdsum4 = 0d0
               do ips4=1,1
                  call vegas4a(3,sig4,ips4,ave4,sd4,chi2)
                  rsum4 = rsum4 + ave4
                  sdsum4 = sdsum4 + sd4**2
               enddo
               ave4 = rsum4
               sd4 = sqrt(sdsum4)
               write(6,11) ave4,sd4
            endif
            if (activePS(5))then
               rsum=0d0
               sdsum=0d0
               do ips=1,2
                  call vegas5(3,sig5,ips,ave5,sd5,chi2)
                  rsum=rsum+ave5
                  sdsum=sdsum+sd5**2  
               enddo
               write(6,12) rsum,sqrt(sdsum)
            endif
            write(6,13) ave3+ave4+rsum,sqrt(sd3**2+sd4**2+sdsum)
         enddo
      endif

c     Main run.
      if (iprod.eq.1) then
         write(6,'(/,A)') " >> Starting production run..."
         ncall3=nshot3
         ncall4=nshot4
         do i=1,2
            ncall5(i)=nshot5(i)
         enddo
         plot=.true.
C         call bino(0,0d0,0)

c     Initialize vegas.
         if (activePS(3))then
            call vegas3(2,sig3,ave3,sd3,chi2)
         endif
         if (activePS(4))then
            do ips4=1,1
               call vegas4a(2,sig4,ips4,ave4,sd4,chi2)
            enddo
         endif
         if (activePS(5))then
            do ips=1,2
               call vegas5(2,sig5,ips,ave5,sd5,chi2)
            enddo
         endif

c     Vegas sweeps with frozen grid.
         sum=0d0
         sum2=0d0
         do it=1,itmax2
            write(6,18) it
            if (activePS(3))then
               call vegas3(4,sig3,ave3,sd3,chi2)
               if(it.eq.itmax2)then
                  sum=sum+ave3
                  sum2=sum2+sd3**2
               endif
c     Print three-parton result.
               if (it.lt.itmax2) write(6,10) ave3,sd3
               if (it.eq.itmax2) write(6,14) ave3,sd3
            endif
            if (activePS(4))then
               rsum4 = 0d0
               sdsum4 = 0d0
               do ips4=1,1
                  call vegas4a(4,sig4,ips4,ave4,sd4,chi2)
                  rsum4 = rsum4 + ave4
                  sdsum4 = sdsum4 + sd4**2
               enddo
               ave4 = rsum4
               sd4 = sqrt(sdsum4)
               if (it.eq.itmax2)then
                  sum=sum+ave4
                  sum2=sum2+sd4**2
               endif
c     Print four-parton result.
               if (it.lt.itmax2) write(6,11) ave4,sd4
               if (it.eq.itmax2) write(6,15) ave4,sd4
            endif
            if (activePS(5))then
               rsum=0d0
               sdsum=0d0
               do ips=1,2
                  call vegas5(4,sig5,ips,ave5,sd5,chi2)
                  if(it.eq.itmax2)then
                     sum=sum+ave5
                     sum2=sum2+sd5**2
                  endif
                  rsum=rsum+ave5
                  sdsum=sdsum+sd5**2  
               enddo
               if (it.lt.itmax2) write(6,12) rsum,sqrt(sdsum)
               if (it.eq.itmax2) write(6,16) rsum,sqrt(sdsum)
            endif
            call bino(2,0d0,0)
c     Print total result.
            if (it.lt.itmax2)then
               write(6,13) ave3+ave4+rsum,sqrt(sd3**2+sd4**2+sdsum)
            else
               write(6,17) ave3+ave4+rsum,sqrt(sd3**2+sd4**2+sdsum)
            endif
         enddo
         call bino(3,0d0,0)
      endif
 10   format(' Sweep 3 parton        ',g14.6,' +- ',g14.6)
 11   format(' Sweep 4 parton        ',g14.6,' +- ',g14.6)
 12   format(' Sweep 5 parton        ',g14.6,' +- ',g14.6)
 13   format(' Total result          ',g14.6,' +- ',g14.6)
 14   format(' Final sweep 3 parton  ',g14.6,' +- ',g14.6)
 15   format(' Final sweep 4 parton  ',g14.6,' +- ',g14.6)
 16   format(' Final sweep 5 parton  ',g14.6,' +- ',g14.6)
 17   format(' Final total result    ',g14.6,' +- ',g14.6)
 18   format(/,' Iteration ',I2)

      ave=sum
      sd=sqrt(sum2)

      return
      end
