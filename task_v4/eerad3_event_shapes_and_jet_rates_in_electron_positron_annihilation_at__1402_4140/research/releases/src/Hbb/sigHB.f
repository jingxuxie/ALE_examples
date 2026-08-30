c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Cross sections for Higgs-decays in the b-quark channel.

c-----------------------------------------------------------------------
c     Cross sections in the three-parton, four-parton
c     and five-parton channel.
c     These routines supply the integrands for the vegas
c     integrations in the main program.
c----------------------------------------------------------------------- 

      real(8) function sig3HBa(x,wgt)
      implicit none
      real(8)             :: x(10),wgt
c     Parameters.
      integer, parameter  :: i1=1,i2=2,i3=3
      real(8), parameter  :: psconv3=1984.401707539188d0 ! 64*pi^3
c     Variables.
      logical             :: plot
      integer             :: i,j,ipass,ifail
      integer             :: ievt3(1)
      real(8)             :: p(4,5),ppar(4,5),pevt3(4,3,1),sevt3(3,3,1)
      real(8)             :: y(3,3)
      real(8)             :: wtps,wtplot,var
c     Externals.
      real(8), external   :: sig3HB
c     Common blocks.
      common/plots/plot
      common/pmom/p
      common/pcut/ppar
      common/yij3/y
      common/eventmom3p/pevt3
      common/eventinv3p/sevt3,ievt3

      sig3HBa = 0d0

      call phase3ee(x,wtps,ifail)
      wtps = wtps*psconv3
      if (ifail.eq.1)return
      call fillcommon3pee

      do i=1,3
         do j=1,4
            ppar(j,i) = pevt3(j,i,1)
            p(j,i)    = pevt3(j,i,1)
         enddo
      enddo
      do i=1,3
         do j=1,3
            y(i,j) = sevt3(i,j,1)
         enddo
      enddo

      call ecuts(3,var,ipass)
      if (ipass.eq.0) return
      wtplot  = wtps*wgt
      sig3HBa = sig3HB(i1,i2,i3,wtplot,var)
      sig3HBa = sig3HBa*wtps*var

      return
      end

************************************************************************

      real(8) function sig4HBa(x,wgt)
      implicit none
      real(8), intent(in) :: x(10),wgt
c     Parameters.
      integer, parameter  :: i1=1,i2=2,i3=3,i4=4
      real(8), parameter  :: psconv4=156682.0786100641d0 ! 512*pi^5
c     Variables.
      logical             :: plot
      integer             :: i,j,ievt,ievtmax,ipass,ifail
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      integer             :: ievt4(12)
      real(8)             :: p(4,5),ppar(4,5),y(4,4)
      real(8)             :: pevt4(4,4,12),sevt4(4,4,12)
      real(8)             :: wtps,wtplot,var
      real(8)             :: sig4HBw,sig3HBsw,sig4HBasum
c     Externals.
      real(8), external   :: sig4HB,sig3HBs
c     Common blocks.
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p
      common/pcut/ppar
      common/yij4/y
      common/eventmom4p/pevt4
      common/eventinv4p/sevt4,ievt4

      sig4HBa    = 0d0
      sig4HBasum = 0d0

      call phase4ee(x,wtps,ifail)
      wtps = wtps*psconv4
      if (iang.eq.1) wtps = wtps/2d0
      if (ifail.eq.1) return
      call fillcommon4pee()
      if (iang.eq.0) ievtmax = 6
      if (iang.eq.1) ievtmax = 12

      do ievt=1,ievtmax
         sig4HBw  = 0d0
         sig3HBsw = 0d0
         if (ievt4(ievt).eq.1)then
            do i=1,4
               do j=1,4
                  ppar(j,i) = pevt4(j,i,ievt)
                  p(j,i) = pevt4(j,i,ievt)
               enddo
            enddo
            do i=1,4
               do j=1,4
                  y(i,j) = sevt4(i,j,ievt)
               enddo
            enddo
            call ecuts(4,var,ipass)
            if (ipass.ne.0) then
               wtplot  = wtps*wgt
               sig4HBw = sig4HB(i1,i2,i3,i4,wtplot,var)
               sig4HBw = sig4HBw*wtps*var
c     Include NLO real subtraction term if we require 3 jets or less.
               if (njets.eq.3) then
                  sig3HBsw = sig3HBs(i1,i2,i3,i4,wtplot)
                  sig3HBsw = sig3HBsw*wtps
               endif
               sig4HBw = sig4HBw - sig3HBsw
            endif
         endif
         sig4HBasum = sig4HBasum + sig4HBw
      enddo

      sig4HBa = sig4HBasum

      return
      end

************************************************************************

      real(8) function sig5HBa(x,wgt)
      implicit none
      real(8), intent(in) :: x(10),wgt
c     Parameters.
      integer, parameter  :: i1=1,i2=2,i3=3,i4=4,i5=5
      real(8), parameter  :: psconv5=1.237112106097374d7 ! 4096*pi^7
c     Variables.
      logical             :: plot
      integer             :: i,j,ievt,ievtmax,ievt5,ipass,ifail
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      integer             :: ips
      integer             :: ievt5a(120),ievt5b(60)
      real(8)             :: ppar(4,5),p(4,5),y(5,5)
      real(8)             :: sijang5(5,5,4),iacc(4)
      real(8)             :: pevt5a(4,5,120),sevt5a(5,5,120)
      real(8)             :: pevt5b(4,5,60),sevt5b(5,5,60)
      real(8)             :: wtps,wtplot,var
      real(8)             :: sig5HBw,sig4HBsw,sig3HBdsw,sig5HBasum
c     Externals.
      real(8), external   :: sig5HB,sig4HBs,sig3HBds
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/phase/ips
      common/pcut/ppar
      common/pmom/p
      common/yij5/y
      common/invarang5/sijang5,iacc
      common/eventmom5ap/pevt5a
      common/eventinv5ap/sevt5a,ievt5a
      common/eventmom5bp/pevt5b
      common/eventinv5bp/sevt5b,ievt5b

      sig5HBa    = 0d0
      sig5HBasum = 0d0

      if (ips.eq.1)then
         call phase5aee(x,wtps,ifail)
         if (ifail.eq.1) return
         wtps = wtps*psconv5
         call fillcommon5apee()
         if (iang.eq.0) ievtmax = 30
         if (iang.eq.1) ievtmax = 120
      elseif (ips.eq.2)then
         call phase5bee(x,wtps,ifail)
         if (ifail.eq.1)return
         wtps = wtps*psconv5
         call fillcommon5bpee()
         if (iang.eq.0) ievtmax = 15
         if (iang.eq.1) ievtmax = 60
      endif
      if (iang.eq.1) wtps=wtps/4d0

      do ievt=1,ievtmax
         sig5HBw   = 0d0
         sig4HBsw  = 0d0
         sig3HBdsw = 0d0
         if (ips.eq.1) ievt5 = ievt5a(ievt)
         if (ips.eq.2) ievt5 = ievt5b(ievt)
         if (ievt5.eq.1)then
            do i=1,5
               do j=1,4
                  if (ips.eq.1) ppar(j,i) = pevt5a(j,i,ievt)
                  if (ips.eq.2) ppar(j,i) = pevt5b(j,i,ievt)
                  p(j,i) = ppar(j,i)
               enddo
            enddo
            do i=1,5
               do j=1,5
                  if (ips.eq.1) y(i,j) = sevt5a(i,j,ievt)
                  if (ips.eq.2) y(i,j) = sevt5b(i,j,ievt)
               enddo
            enddo
            call ecuts(5,var,ipass)
            if (ipass.ne.0)then
               wtplot  = wtps*wgt
               sig5HBw = sig5HB(i1,i2,i3,i4,i5,wtplot,var)
               sig5HBw = sig5HBw*wtps*var
c     Include NLO real subtraction term for 4 jets or less.
               if (njets.le.4)then
                  sig4HBsw = sig4HBs(i1,i2,i3,i4,i5,wtplot)
                  sig4HBsw = sig4HBsw*wtps
               endif
c     Include NNLO double-real subtraction term for 3 jets or less.
               if (njets.eq.3)then
                  sig3HBdsw = sig3HBds(i1,i2,i3,i4,i5,wtplot)
                  sig3HBdsw = sig3HBdsw*wtps
               endif
               sig5HBw = sig5HBw - sig4HBsw - sig3HBdsw
            endif
         endif
         sig5HBasum = sig5HBasum + sig5HBw
      enddo

      sig5HBa = sig5HBasum

      return
      end

c-----------------------------------------------------------------------
c     Differential cross sections called by VEGAS integrands above.
c-----------------------------------------------------------------------

c     Three-parton contributions.
c     Containing tree-level, one-loop, and two-loop contributions.
      real(8) function sig3HB(i1,i2,i3,wtplot,var3)
      implicit none
      integer, intent(in) :: i1,i2,i3
      real(8), intent(in) :: wtplot,var3
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot,doTree,do1Loop,do2Loop
      integer             :: ipole,npole
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: rm2(1:5),shat
      real(8)             :: p(1:4,5)
      real(8)             :: ptest1,ptest2
      real(8)             :: fac,wtdis,sig3HBV(-2:0),sig3HBTNLO(-2:0)
c     Externals.
      real(8), external   :: By1g0H,By1g1H,Bty1g1H,Bhy1g1H
      real(8), external   :: By1g1HTNLO,Bty1g1HTNLO,Bhy1g1HTNLO
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2,shat
      common/pmom/p

c     Normalisation to yield overall (as/2/pi) factor.
      fac    = 1d0/8d0/pi**2

      nf     = int(2d0*tr)      ! tr=nf/2
      sig3HB = 0d0
      if (njets.gt.3) return

c     Check which contributions to include.
      doTree  = .false.
      do1Loop = .false.
      do2Loop = .false.
      if (nloop.ge.0) doTree = .true.
      if (nloop.ge.1.or.nloop.eq.-1) do1Loop = .true.
      if (abs(nloop).eq.2) do2Loop = .true.

c     Tree-level contributions.
      if (doTree)then
         sig3HB = (4d0*pi*as)*2d0*cf*By1g0H(p,i1,i3,i2)
      endif

c     One-loop contributions.
      if (do1Loop)then
         npole = 0
         if (idebug.ge.1) npole = -2
         sig3HBV(:)    = 0d0
         sig3HBTNLO(:) = 0d0

c     NC terms.
         if (icol.eq.0.or.icol.eq.1)then
            do ipole=npole,0
               sig3HBV(ipole) = sig3HBV(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)*2d0*cf*cn*(
     .              + By1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HBTNLO(ipole) = sig3HBTNLO(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)*2d0*cf*cn*(
     .              + By1g1HTNLO(i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif
c     1/NC terms.
         if (icol.eq.0.or.icol.eq.2)then
            do ipole=npole,0
               sig3HBV(ipole) = sig3HBV(ipole)
     .              - (as/2d0/pi)*(4d0*pi*as)*2d0*cf*1d0/cn*(
     .              + Bty1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HBTNLO(ipole) = sig3HBTNLO(ipole)
     .              - (as/2d0/pi)*(4d0*pi*as)*2d0*cf*1d0/cn*(
     .              + Bty1g1HTNLO(i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif
c     NF terms.
         if (icol.eq.0.or.icol.eq.3)then
            do ipole=npole,0
               sig3HBV(ipole) = sig3HBV(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)*2d0*cf*nf*(
     .              + Bhy1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HBTNLO(ipole) = sig3HBTNLO(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)*2d0*cf*nf*(
     .              + Bhy1g1HTNLO(i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif

c     Check pole cancellation.
         if (idebug.ge.1)then
            ptest1 = 0d0
            ptest2 = 0d0
            if (sig3HBV(-1).gt.1d-9)
     .           ptest1 = abs((sig3HBV(-1)+sig3HBTNLO(-1))/sig3HBV(-1))
            if (sig3HBV(-2).gt.1d-9)
     .           ptest2 = abs((sig3HBV(-2)+sig3HBTNLO(-2))/sig3HBV(-2))
            if (idebug.eq.2)then
               print *, sig3HBV(-1),sig3HBTNLO(-1),ptest1
               print *, sig3HBV(-2),sig3HBTNLO(-2),ptest2
            endif
            if (ptest1.ge.1d-9.or.ptest2.ge.1d-9)then
               write(6,*) 'Error in sig3HB():',
     .              ' Incomplete pole cancellation!',ptest1,ptest2
               stop
            endif
         endif
         
c     Assemble final result.
         sig3HB = sig3HB + sig3HBV(0) + sig3HBTNLO(0)
      endif

c     Two-loop contributions.
      if (do2Loop)then
         stop 'Two-loop corrections for H -> 3j not implemented'
      endif

      sig3HB = fac*sig3HB

      if (plot)then
         call bino(1,sig3HB*wtplot*var3,3)
      else
         call distrib(wtdis)
         sig3HB = sig3HB/wtdis
      endif

      return
      end

************************************************************************

c     Four-parton contributions.
c     Containing tree-level and one-loop contributions.
      real(8) function sig4HB(i1,i2,i3,i4,wtplot,var4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot,var4
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot,doTree,doLoop
      integer             :: iproc,nloop,icol,njets,ichan
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: npole,ipole
      real(8)             :: y(4,4)
      real(8)             :: p(4,5)
      real(8)             :: rm2(1:5),shat
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: ptest
      real(8)             :: fac,wtdis
      real(8)             :: wtBy2g1H(-2:0),wtCy0g1H(-2:0)
      real(8)             :: wtDy0g1H(-2:0),sig4HBV(-2:0)
      real(8)             :: wtBy2g1HTNLO(-2:0),wtCy0g1HTNLO(-2:0)
      real(8)             :: wtDy0g1HTNLO(-2:0),sig4HBTNLO(-2:0)
c     Externals.
      real(8), external   :: By2g0H,Bty2g0H,Cy0g0H,Dy0g0H
      real(8), external   :: By2g1H,Bty2g1H,Bhy2g1H
      real(8), external   :: Btty2g1H,Bttty2g1H,Btthy2g1H,Bhhy2g1H
      real(8), external   :: Cy0g1H,Cty0g1H,Chy0g1H
      real(8), external   :: Dy0g1H,Dty0g1H,Dhy0g1H
      real(8), external   :: By2g1HTNLO,Bty2g1HTNLO,Bhy2g1HTNLO
      real(8), external   :: Btty2g1HTNLO,Bttty2g1HTNLO,Btthy2g1HTNLO
      real(8), external   :: Cy0g1HTNLO,Cty0g1HTNLO
      real(8), external   :: Dy0g1HTNLO,Dty0g1HTNLO
      real(8), external   :: FullBy2g1H,FullCy0g1H,FullDy0g1H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2,shat
      common/yij4/y
      common/pmom/p

c     Normalisation to yield overall (as/2/pi) factor.
      fac = (1d0/8d0/pi**2)**2

      nf     = int(2d0*tr)      ! tr=nf/2
      sig4HB = 0d0
      if (njets.gt.4) return

c     Check which contributions to include.
      doTree = .false.
      doLoop = .false.
      if (njets.eq.3.and.abs(nloop).eq.1) doTree = .true.
      if (njets.eq.3.and.nloop.eq.2) doTree = .true.
      if (njets.eq.4.and.nloop.ge.0) doTree = .true.
      if (njets.eq.3.and.abs(nloop).eq.2) doLoop = .true.
      if (njets.eq.4.and.abs(nloop).eq.1) doLoop = .true.

c     Tree-level contributions.
      if (doTree)then
c     NC terms.
         if(icol.eq.0.or.icol.eq.1)then
            sig4HB = sig4HB
     .           + 1d0/2d0*(4d0*pi*as)**2*2d0*cf*cn*(
     .           + By2g0H(p,i1,i3,i4,i2)
     .           + By2g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     1/NC terms.
         if(icol.eq.0.or.icol.eq.2)then
            sig4HB = sig4HB
     .           - 1d0/2d0*(4d0*pi*as)**2*2d0*cf*1d0/cn*(
     .           + Bty2g0H(p,i1,i3,i4,i2)
     .           )
     .           - 1d0/4d0*(4d0*pi*as)**2*2d0*cf*1d0/cn*(
     .           + Dy0g0H(p,i1,i2,i3,i4)
     .           )
         endif
c     NF terms.
         if(icol.eq.0.or.icol.eq.3)then
            sig4HB = sig4HB
     .           + (4d0*pi*as)**2*2d0*cf*(nf-1d0)*(
     .           + Cy0g0H(p,i1,i4,i3,i2)
     .           )
     .           + 1d0/4d0*(4d0*pi*as)**2*2d0*cf*(
     .           + Cy0g0H(p,i1,i4,i3,i2)
     .           + Cy0g0H(p,i1,i2,i3,i4)
     .           + Cy0g0H(p,i3,i4,i1,i2)
     .           + Cy0g0H(p,i3,i2,i1,i4)
     .           )
         endif
      endif

c     One-loop contributions.
      if (doLoop)then
c     One-loop matrix elements.
         wtBy2g1H(:) = 0d0
         wtCy0g1H(:) = 0d0
         wtDy0g1H(:) = 0d0
c     NLO virtual subtraction terms.
         wtBy2g1HTNLO(:) = 0d0
         wtCy0g1HTNLO(:) = 0d0
         wtDy0g1HTNLO(:) = 0d0
c     Calculate pole terms only in debug mode.
         npole = 0
         if (idebug.ge.1) npole = -2
         do ipole=npole,0
c     NC^2 terms.
            if (icol.eq.0.or.icol.eq.1) then
               wtBy2g1H(ipole) = wtBy2g1H(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn**2*(
     .              + By2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + By2g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtBy2g1HTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn**2*(
     .              + By2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + By2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
            endif
c     NC^0 terms.
            if (icol.eq.0.or.icol.eq.2) then
               wtBy2g1H(ipole) = wtBy2g1H(ipole)
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(
     .              + Bty2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + Bty2g1H(p,i1,i4,i3,i2,shat,ipole)
     .              + Btty2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              - Bhhy2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              )

               wtDy0g1H(ipole) = wtDy0g1H(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(
     .              + Dy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtBy2g1HTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(
     .              + Bty2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + Bty2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              + Btty2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              )

               wtDy0g1HTNLO(ipole) = wtDy0g1HTNLO(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(
     .              + Dy0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
            endif
c     1/NC^2 terms.
            if (icol.eq.0.or.icol.eq.3) then
               wtBy2g1H(ipole) = wtBy2g1H(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn**2*(
     .              + Bttty2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              )

               wtDy0g1H(ipole) = wtDy0g1H(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn**2*(
     .              + Dty0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtBy2g1HTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn**2*(
     .              + Bttty2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              )

               wtDy0g1HTNLO(ipole) = wtDy0g1HTNLO(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn**2*(
     .              + Dty0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
            endif
c     NF*NC terms.
            if (icol.eq.0.or.icol.eq.4) then
               wtBy2g1H(ipole) = wtBy2g1H(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf*cn*(
     .              + Bhy2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + Bhy2g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtCy0g1H(ipole) = wtCy0g1H(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(nf-1d0)*cn*(
     .              + Cy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtDy0g1H(ipole) = wtDy0g1H(ipole)
     .              + 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn*(
     .              + Cy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              + Cy0g1H(p,i1,i2,i3,i4,shat,ipole)
     .              + Cy0g1H(p,i3,i4,i1,i2,shat,ipole)
     .              + Cy0g1H(p,i3,i2,i1,i4,shat,ipole)
     .              )

               wtBy2g1HTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .              + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf*cn*(
     .              + Bhy2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + Bhy2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )

               wtCy0g1HTNLO(ipole) = wtCy0g1HTNLO(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(nf-1d0)*cn*(
     .              + Cy0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )

               wtDy0g1HTNLO(ipole) = wtDy0g1HTNLO(ipole)
     .              + 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn*(
     .              + Cy0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              + Cy0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              + Cy0g1HTNLO(i3,i4,i1,i2,shat,ipole)
     .              + Cy0g1HTNLO(i3,i2,i1,i4,shat,ipole)
     .              )
            endif
c     NF/NC terms.
            if (icol.eq.0.or.icol.eq.5) then
               wtBy2g1H(ipole) = wtBy2g1H(ipole)
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf/cn*(
     .              + Btthy2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              )

               wtCy0g1H(ipole) = wtCy0g1H(ipole)
     .              - (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(nf-1d0)/cn*(
     .              + Cty0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtDy0g1H(ipole) = wtDy0g1H(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn*(
     .              + Cty0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              + Cty0g1H(p,i1,i2,i3,i4,shat,ipole)
     .              + Cty0g1H(p,i3,i4,i1,i2,shat,ipole)
     .              + Cty0g1H(p,i3,i2,i1,i4,shat,ipole)
     .              )
     .              + 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf/cn*(
     .              + Dhy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtBy2g1HTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf/cn*(
     .              + Btthy2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              )

               wtCy0g1HTNLO(ipole) = wtCy0g1HTNLO(ipole)
     .              - (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(nf-1d0)/cn*(
     .              + Cty0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )

               wtDy0g1HTNLO(ipole) = wtDy0g1HTNLO(ipole)
     .              - 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf/cn*(
     .              + Cty0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              + Cty0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              + Cty0g1HTNLO(i3,i4,i1,i2,shat,ipole)
     .              + Cty0g1HTNLO(i3,i2,i1,i4,shat,ipole)
     .              )
            endif
c     NF^2 terms.
            if (icol.eq.0.or.icol.eq.6) then
               wtCy0g1H(ipole) = wtCy0g1H(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*(nf-1d0)*nf*(
     .              + Chy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               wtDy0g1H(ipole) = wtDy0g1H(ipole)
     .              + 1d0/4d0*(as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*nf*(
     .              + Chy0g1H(p,i1,i4,i3,i2,shat,ipole)
     .              + Chy0g1H(p,i1,i2,i3,i4,shat,ipole)
     .              + Chy0g1H(p,i3,i4,i1,i2,shat,ipole)
     .              + Chy0g1H(p,i3,i2,i1,i4,shat,ipole)
     .              )
            endif
            sig4HBV(ipole)    = wtBy2g1H(ipole)
     .           + wtCy0g1H(ipole)
     .           + wtDy0g1H(ipole)
            sig4HBTNLO(ipole) = wtBy2g1HTNLO(ipole)
     .           + wtCy0g1HTNLO(ipole)
     .           + wtDy0g1HTNLO(ipole)

c     Check pole cancellation.
            if (ipole.lt.0) then
               ptest = 0d0
               if (sig4HBV(ipole).ne.0d0)
     .              ptest = abs(1d0
     .              - abs(sig4HBTNLO(ipole)/sig4HBV(ipole)))
               if (idebug.eq.2)then
                  print *, sig4HBV(ipole),sig4HBTNLO(ipole),ptest
               endif
               if (ptest.gt.1d-6)then
                  write(6,*) 'Error in sig4HB():',
     .                 ' Incomplete pole cancellation',ipole,ptest
                  stop
               endif
            endif
         enddo

c     Assemble final result.
         sig4HB = sig4HB + sig4HBV(0) + sig4HBTNLO(0)
      endif

      sig4HB = fac*sig4HB

      if (plot)then
         call bino(1,sig4HB*wtplot*var4,4)
      else
         call distrib(wtdis)
         sig4HB = sig4HB/wtdis
      endif

      return
      end

************************************************************************

c     Five-parton contributions.
c     Containing tree-level contributions.
      real(8) function sig5HB(i1,i2,i3,i4,i5,wtplot,var5)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot,var5
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: p(4,5)
      real(8)             :: fac,wtdis
c     Externals.
      real(8), external   :: By3g0H,Bty3g0H,Btty3g0H
      real(8), external   :: Cy1g0Ha,Cy1g0Hb
      real(8), external   :: Cty1g0Ha,Cty1g0Hb,Ctty1g0H
      real(8), external   :: Dy1g0H,Dty1g0H
c     Common blocks.
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/qcd/as,ca,cflo,cf,tr,cn
      common/pmom/p

c     Normalisation to yield overall (as/2/pi) factor.
      fac = (1d0/8d0/pi**2)**3

      nf     = int(2d0*tr)      ! tr=nf/2
      sig5HB = 0d0
      if (njets.gt.5) return

c     NC^2 terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig5HB = sig5HB
     .        + 1d0/6d0*(4d0*pi*as)**3*2d0*cf*cn**2*(
     .        + By3g0H(p,i1,i3,i4,i5,i2)
     .        + By3g0H(p,i1,i3,i5,i4,i2)
     .        + By3g0H(p,i1,i4,i3,i5,i2)
     .        + By3g0H(p,i1,i4,i5,i3,i2)
     .        + By3g0H(p,i1,i5,i3,i4,i2)
     .        + By3g0H(p,i1,i5,i4,i3,i2)
     .        )
      endif
c     NC^0 terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig5HB = sig5HB
     .        - 1d0/6d0*(4d0*pi*as)**3*2d0*cf*(
     .        + Bty3g0H(p,i1,i3,i4,i5,i2)
     .        + Bty3g0H(p,i1,i3,i5,i4,i2)
     .        + Bty3g0H(p,i1,i4,i3,i5,i2)
     .        + Bty3g0H(p,i1,i4,i5,i3,i2)
     .        + Bty3g0H(p,i1,i5,i3,i4,i2)
     .        + Bty3g0H(p,i1,i5,i4,i3,i2)
     .        - Btty3g0H(p,i1,i3,i4,i5,i2)
     .        )
     .        - 1d0/4d0*(4d0*pi*as)**3*2d0*cf*(
     .        + Dy1g0H(p,i1,i2,i3,i4,i5)
     .        + Dy1g0H(p,i1,i4,i3,i2,i5)
     .        + Dy1g0H(p,i3,i4,i1,i2,i5)
     .        + Dy1g0H(p,i3,i2,i1,i4,i5)
     .        - Dty1g0H(p,i1,i2,i3,i4,i5)
     .        - Dty1g0H(p,i2,i1,i4,i3,i5)
     .        - Dty1g0H(p,i1,i4,i3,i2,i5)
     .        - Dty1g0H(p,i4,i1,i2,i3,i5)
     .        - Dty1g0H(p,i3,i4,i1,i2,i5)
     .        - Dty1g0H(p,i4,i3,i2,i1,i5)
     .        - Dty1g0H(p,i3,i2,i1,i4,i5)
     .        - Dty1g0H(p,i2,i3,i4,i1,i5)
     .        )
      endif
c     1/NC^2 terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig5HB = sig5HB
     .        + 1d0/6d0*(4d0*pi*as)**3*2d0*cf*1d0/cn**2*(
     .        + Btty3g0H(p,i1,i3,i4,i5,i2)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*1d0/cn**2*(
     .        + Dty1g0H(p,i1,i2,i3,i4,i5)
     .        + Dty1g0H(p,i2,i1,i4,i3,i5)
     .        + Dty1g0H(p,i1,i4,i3,i2,i5)
     .        + Dty1g0H(p,i4,i1,i2,i3,i5)
     .        + Dty1g0H(p,i3,i4,i1,i2,i5)
     .        + Dty1g0H(p,i4,i3,i2,i1,i5)
     .        + Dty1g0H(p,i3,i2,i1,i4,i5)
     .        + Dty1g0H(p,i2,i3,i4,i1,i5)
     .        )
      endif
c     NF*NC terms.
      if (icol.eq.0.or.icol.eq.4)then
         sig5HB = sig5HB
     .        + (4d0*pi*as)**3*2d0*cf*(nf-1d0)*cn*(
     .        + Cy1g0Ha(p,i1,i5,i4,i3,i2)
     .        + Cy1g0Hb(p,i1,i4,i3,i5,i2)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*cn*(
     .        + Cy1g0Ha(p,i1,i5,i4,i3,i2)
     .        + Cy1g0Ha(p,i1,i5,i2,i3,i4)
     .        + Cy1g0Ha(p,i3,i5,i2,i1,i4)
     .        + Cy1g0Ha(p,i3,i5,i4,i1,i2)
     .        + Cy1g0Hb(p,i1,i4,i3,i5,i2)
     .        + Cy1g0Hb(p,i1,i2,i3,i5,i4)
     .        + Cy1g0Hb(p,i3,i2,i1,i5,i4)
     .        + Cy1g0Hb(p,i3,i4,i1,i5,i2)
     .        )
      endif
c     NF/NC terms.
      if (icol.eq.0.or.icol.eq.5)then
c     Note: Ctty1g0H symmetrised over momenta 3 and 4.
         sig5HB = sig5HB
     .        + (4d0*pi*as)**3*2d0*cf*(nf-1d0)/cn*(
     .        + Cty1g0Ha(p,i1,i5,i2,i3,i4)
     .        + Cty1g0Hb(p,i1,i2,i3,i5,i4)
     .        - Ctty1g0H(p,i1,i2,i3,i4,i5)
     .        - Ctty1g0H(p,i1,i2,i4,i3,i5)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*1d0/cn*(
     .        + Cty1g0Ha(p,i1,i5,i2,i3,i4)
     .        + Cty1g0Ha(p,i1,i5,i4,i3,i2)
     .        + Cty1g0Ha(p,i3,i5,i4,i1,i2)
     .        + Cty1g0Ha(p,i3,i5,i2,i1,i4)
     .        + Cty1g0Hb(p,i1,i2,i3,i5,i4)
     .        + Cty1g0Hb(p,i1,i4,i3,i5,i2)
     .        + Cty1g0Hb(p,i3,i4,i1,i5,i2)
     .        + Cty1g0Hb(p,i3,i2,i1,i5,i4)
     .        - Ctty1g0H(p,i1,i2,i3,i4,i5)
     .        - Ctty1g0H(p,i1,i4,i3,i2,i5)
     .        - Ctty1g0H(p,i3,i4,i1,i2,i5)
     .        - Ctty1g0H(p,i3,i2,i1,i4,i5)
     .        - Ctty1g0H(p,i1,i2,i4,i3,i5)
     .        - Ctty1g0H(p,i1,i4,i2,i3,i5)
     .        - Ctty1g0H(p,i3,i4,i2,i1,i5)
     .        - Ctty1g0H(p,i3,i2,i4,i1,i5)
     .        )
      endif

      sig5HB = fac*sig5HB

      if (plot)then
         call bino(1,sig5HB*wtplot*var5,5)
      else
         call distrib(wtdis)
         sig5HB = sig5HB/wtdis
      endif

      return
      end

c-----------------------------------------------------------------------
c     Differential subtraction terms called by VEGAS integrands above.
c-----------------------------------------------------------------------

c     3-jet real subtraction term.
      real(8) function sig3HBs(i1,i2,i3,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
      real(8), parameter  :: pi=3.141592653589793238d0
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: fac,wt,wt1,wt2,wt3,wt4
c     Externals.
      real(8), external   :: By2g0HSNLO,Bty2g0HSNLO,Cy0g0HSNLO
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn

c     Normalisation to yield overall factor (as/2d0/pi).
      fac    = (1d0/8d0/pi**2)**2

      nf      = int(2d0*tr)     ! tr=nf/2
      sig3HBs = 0d0

c     Set plot weights.
      wt1 = -fac*wtplot*1d0/2d0*(4d0*pi*as)**2*2d0*cf*cn
      wt2 = -fac*wtplot*(-1d0/2d0*(4d0*pi*as)**2*2d0*cf*1d0/cn)
      wt3 = -fac*wtplot*(4d0*pi*as)**2*2d0*cf*(nf-1d0)
      wt4 = -fac*wtplot*1d0/4d0*(4d0*pi*as)**2*2d0*cf

c     NC terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig3HBs = sig3HBs
     .        + 1d0/2d0*(4d0*pi*as)**2*2d0*cf*cn*(
     .        + By2g0HSNLO(i1,i3,i4,i2,wt1)
     .        + By2g0HSNLO(i1,i4,i3,i2,wt1)
     .        )
      endif
c     1/NC terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig3HBs = sig3HBs
     .        - 1d0/2d0*(4d0*pi*as)**2*2d0*cf*1d0/cn*(
     .        + Bty2g0HSNLO(i1,i3,i4,i2,wt2)
     .        )
      endif
c     NF*NC^0 terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig3HBs = sig3HBs
     .           + (4d0*pi*as)**2*2d0*cf*(nf-1d0)*(
     .           + Cy0g0HSNLO(i1,i4,i3,i2,wt3)
     .           )
     .           + 1d0/4d0*(4d0*pi*as)**2*2d0*cf*(
     .           + Cy0g0HSNLO(i1,i4,i3,i2,wt4)
     .           + Cy0g0HSNLO(i1,i2,i3,i4,wt4)
     .           + Cy0g0HSNLO(i3,i4,i1,i2,wt4)
     .           + Cy0g0HSNLO(i3,i2,i1,i4,wt4)
     .           )
      endif

      sig3HBs = fac*sig3HBs

      return
      end

************************************************************************

c     4-jet real subtraction term.
      real(8) function sig4HBs(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: p(1:4,5)
      real(8)             :: fac,wt,wt1,wt2,wt3,wt4,wt5,wt6,wt7,wt8,wt9
c     Externals.
      real(8), external   :: By3g0HSNLO,Bty3g0HSNLO,Btty3g0HSNLO
      real(8), external   :: Cy1g0HSNLOa,Cy1g0HSNLOb
      real(8), external   :: Cty1g0HSNLO,Ctty1g0HSNLO
      real(8), external   :: Dy1g0HSNLO,Dty1g0HSNLO
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p

c     Normalisation to yield overall factor (as/2d0/pi).
      fac = (1d0/8d0/pi**2)**3

      nf      = int(2d0*tr)         ! tr=nf/2
      sig4HBs = 0d0

c     Set plot weights.
      wt1 = -fac*wtplot*1d0/6d0*(4d0*pi*as)**3*2d0*cf*cn**2
      wt2 = -fac*wtplot*(-1d0/6d0*(4d0*pi*as)**3*2d0*cf)
      wt3 = -fac*wtplot*(-(4d0*pi*as)**3*2d0*cf)
      wt4 = -fac*wtplot*1d0/6d0*(4d0*pi*as)**3*2d0*cf*1d0/cn**2
      wt5 = -fac*wtplot*(4d0*pi*as)**3*2d0*cf*1d0/cn**2
      wt6 = -fac*wtplot*(4d0*pi*as)**3*2d0*cf*(nf-1d0)*cn
      wt7 = -fac*wtplot*1d0/4d0*(4d0*pi*as)**3*2d0*cf*cn
      wt8 = -fac*wtplot*(4d0*pi*as)**3*2d0*cf*(nf-1d0)/cn
      wt9 = -fac*wtplot*1d0/4d0*(4d0*pi*as)**3*2d0*cf*1d0/cn

c     NC^2 terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig4HBs = sig4HBs
     .        + 1d0/6d0*(4d0*pi*as)**3*2d0*cf*cn**2*(
     .        + By3g0HSNLO(i1,i3,i4,i5,i2,wt1)
     .        + By3g0HSNLO(i1,i3,i5,i4,i2,wt1)
     .        + By3g0HSNLO(i1,i4,i3,i5,i2,wt1)
     .        + By3g0HSNLO(i1,i4,i5,i3,i2,wt1)
     .        + By3g0HSNLO(i1,i5,i3,i4,i2,wt1)
     .        + By3g0HSNLO(i1,i5,i4,i3,i2,wt1)
     .        )
      endif
c     NC^0 terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig4HBs = sig4HBs
     .        - 1d0/6d0*(4d0*pi*as)**3*2d0*cf*(
     .        + Bty3g0HSNLO(i1,i3,i4,i5,i2,wt2)
     .        + Bty3g0HSNLO(i1,i3,i5,i4,i2,wt2)
     .        + Bty3g0HSNLO(i1,i4,i3,i5,i2,wt2)
     .        + Bty3g0HSNLO(i1,i4,i5,i3,i2,wt2)
     .        + Bty3g0HSNLO(i1,i5,i3,i4,i2,wt2)
     .        + Bty3g0HSNLO(i1,i5,i4,i3,i2,wt2)
     .        - Btty3g0HSNLO(i1,i3,i4,i5,i2,-wt2)
     .        )
     .        - 1d0/4d0*(4d0*pi*as)**3*2d0*cf*(
     .        + Dy1g0HSNLO(i1,i2,i3,i4,i5,wt3)
     .        - Dty1g0HSNLO(i1,i2,i3,i4,i5,-wt3)
     .        )
      endif
c     1/NC^2 terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig4HBs = sig4HBs
     .        + 1d0/6d0*(4d0*pi*as)**3*2d0*cf*1d0/cn**2*(
     .        + Btty3g0HSNLO(i1,i3,i4,i5,i2,wt4)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*1d0/cn**2*(
     .        + Dty1g0HSNLO(i1,i2,i3,i4,i5,wt5)
     .        )
      endif
c     NF*NC terms.
      if (icol.eq.0.or.icol.eq.4)then
         sig4HBs = sig4HBs
     .        + (4d0*pi*as)**3*2d0*cf*(nf-1d0)*cn*(
     .        + Cy1g0HSNLOa(i1,i5,i4,i3,i2,wt6)
     .        + Cy1g0HSNLOb(i1,i4,i3,i5,i2,wt6)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*cn*(
     .        + Cy1g0HSNLOa(i1,i5,i4,i3,i2,wt7)
     .        + Cy1g0HSNLOa(i1,i5,i2,i3,i4,wt7)
     .        + Cy1g0HSNLOa(i3,i5,i2,i1,i4,wt7)
     .        + Cy1g0HSNLOa(i3,i5,i4,i1,i2,wt7)
     .        + Cy1g0HSNLOb(i1,i4,i3,i5,i2,wt7)
     .        + Cy1g0HSNLOb(i1,i2,i3,i5,i4,wt7)
     .        + Cy1g0HSNLOb(i3,i2,i1,i5,i4,wt7)
     .        + Cy1g0HSNLOb(i3,i4,i1,i5,i2,wt7)
     .        )
      endif
c     NF/NC terms.
      if (icol.eq.0.or.icol.eq.5)then
         sig4HBs = sig4HBs
     .        + (4d0*pi*as)**3*2d0*cf*(nf-1d0)/cn*(
     .        + Cty1g0HSNLO(i1,i5,i2,i3,i4,wt8)
     .        - Ctty1g0HSNLO(i1,i2,i3,i4,i5,-wt8)
     .        - Ctty1g0HSNLO(i1,i2,i4,i3,i5,-wt8)
     .        )
     .        + 1d0/4d0*(4d0*pi*as)**3*2d0*cf*1d0/cn*(
     .        + Cty1g0HSNLO(i1,i5,i2,i3,i4,wt9)
     .        + Cty1g0HSNLO(i1,i5,i4,i3,i2,wt9)
     .        + Cty1g0HSNLO(i3,i5,i4,i1,i2,wt9)
     .        + Cty1g0HSNLO(i3,i5,i2,i1,i4,wt9)
     .        - Ctty1g0HSNLO(i1,i2,i3,i4,i5,-wt9)
     .        - Ctty1g0HSNLO(i1,i4,i3,i2,i5,-wt9)
     .        - Ctty1g0HSNLO(i3,i4,i1,i2,i5,-wt9)
     .        - Ctty1g0HSNLO(i3,i2,i1,i4,i5,-wt9)
     .        - Ctty1g0HSNLO(i1,i2,i4,i3,i5,-wt9)
     .        - Ctty1g0HSNLO(i1,i4,i2,i3,i5,-wt9)
     .        - Ctty1g0HSNLO(i3,i4,i2,i1,i5,-wt9)
     .        - Ctty1g0HSNLO(i3,i2,i4,i1,i5,-wt9)
     .        )
      endif

      sig4HBs = fac*sig4HBs

      return
      end

************************************************************************

c     3-jet double-real subtraction term.
      real(8) function sig3HBds(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: fac,wt1
c     Externals.
      real(8), external   :: By3g0HS
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn

c     Normalisation to yield overall (as/2/pi) factor.
      fac      = (1d0/8d0/pi**2)**3

      nf        = int(2d0*tr)   ! tr=nf/2
      sig3HBds  = 0d0

      stop 'sigHB: NNLO not yet implemented'

      sig3HBds = fac*sig3HBds

      return
      end
      
c-----------------------------------------------------------------------
