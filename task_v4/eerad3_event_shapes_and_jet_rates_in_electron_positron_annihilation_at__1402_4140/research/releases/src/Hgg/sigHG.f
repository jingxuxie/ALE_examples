c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Cross sections for Higgs-decays in the gluon channel.

c-----------------------------------------------------------------------
c     Cross sections in the three-parton, four-parton
c     and five-parton channel.
c     These routines supply the integrands for the vegas
c     integrations in the main program.
c-----------------------------------------------------------------------

      real(8) function sig3HGa(x,wgt)
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
      real(8), external   :: sig3HG
c     Common blocks.
      common/plots/plot
      common/pmom/p
      common/pcut/ppar
      common/yij3/y
      common/eventmom3p/pevt3
      common/eventinv3p/sevt3,ievt3

      sig3HGa = 0d0

      call phase3ee(x,wtps,ifail)
      wtps = wtps*psconv3
      if (ifail.eq.1) return
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
      sig3HGa = sig3HG(i1,i2,i3,wtplot,var)
      sig3HGa = sig3HGa*wtps*var

      return
      end

************************************************************************

      real(8) function sig4HGa(x,wgt)
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
      real(8)             :: wtps,wtdis,wtplot,var
      real(8)             :: sig4HGw,sig3HGsw,sig4HGasum
c     Externals.
      real(8), external   :: sig4HG,sig3HGs
c     Common blocks.
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p
      common/pcut/ppar
      common/yij4/y
      common/eventmom4p/pevt4
      common/eventinv4p/sevt4,ievt4

      sig4HGasum = 0d0

      call phase4ee(x,wtps,ifail)
      wtps = wtps*psconv4
      if (iang.eq.1) wtps=wtps/2d0
      if (ifail.eq.1) return
      call fillcommon4pee
      if (iang.eq.0) ievtmax = 6
      if (iang.eq.1) ievtmax = 12

      do ievt=1,ievtmax
         sig4HGw  = 0d0
         sig3HGsw = 0d0
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
               sig4HGw = sig4HG(i1,i2,i3,i4,wtplot,var)
               sig4HGw = sig4HGw*wtps*var
c     Include NLO real subtraction term if we require 3 jets or less.
               if (njets.le.3)then
                  sig3HGsw = sig3HGs(i1,i2,i3,i4,wtplot) 
                  sig3HGsw = sig3HGsw*wtps
               endif
               sig4HGw = sig4HGw-sig3HGsw
            endif
         endif
         sig4HGasum = sig4HGasum + sig4HGw
      enddo
      sig4HGa = sig4HGasum

      return
      end

************************************************************************

      real(8) function sig5HGa(x,wgt)
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
      real(8)             :: sig5HGw,sig4HGsw,sig3HGdsw,sig5HGasum
c     Externals.
      real(8), external   :: sig5HG,sig4HGs,sig3HGds
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

      sig5HGasum = 0d0

      if (ips.eq.1)then
         call phase5aee(x,wtps,ifail)
         if (ifail.eq.1) return
         wtps = wtps*psconv5
         call fillcommon5apee
         if (iang.eq.0) ievtmax = 30
         if (iang.eq.1) ievtmax = 120
      elseif (ips.eq.2)then
         call phase5bee(x,wtps,ifail)
         if (ifail.eq.1) return
         wtps = wtps*psconv5
         call fillcommon5bpee
         if (iang.eq.0) ievtmax = 15
         if (iang.eq.1) ievtmax = 60
      endif
      if (iang.eq.1) wtps=wtps/4d0

      do ievt=1,ievtmax
         sig5HGw   = 0d0
         sig4HGsw  = 0d0
         sig3HGdsw = 0d0
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
               sig5HGw = sig5HG(i1,i2,i3,i4,i5,wtplot,var)
               sig5HGw = sig5HGw*wtps*var
c     Include NLO real subtraction term for 4 jets or less.
               if (njets.le.4)then
                  sig4HGsw = sig4HGs(i1,i2,i3,i4,i5,wtplot)
                  sig4HGsw = sig4HGsw*wtps
               endif
c     Include NNLO double-real subtraction term for 3 jets or less.
               if (njets.le.3)then
                  sig3HGdsw = sig3HGds(i1,i2,i3,i4,i5,wtplot)
                  sig3HGdsw = sig3HGdsw*wtps
               endif
               sig5HGw = sig5HGw - sig4HGsw - sig3HGdsw
            endif
         endif
         sig5HGasum = sig5HGasum + sig5HGw
      enddo

      sig5HGa = sig5HGasum

      return
      end

c-----------------------------------------------------------------------
c     Differential cross sections called by VEGAS integrands above.
c-----------------------------------------------------------------------

c     Three-parton contributions.
c     Containing tree-level, one-loop, and two-loop contributions.
      real(8) function sig3HG(i1,i2,i3,wtplot,var3)
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
      real(8)             :: fac,wtdis,sig3HGV(-2:0),sig3HGTNLO(-2:0)
c     Externals.
      real(8), external   :: A3g0H,A3g1H,Ah3g1H
      real(8), external   :: A3g1HTNLO,Ah3g1HTNLO
      real(8), external   :: B1g0H,B1g1H,Bt1g1H,Bh1g1H
      real(8), external   :: B1g1HTNLO,Bt1g1HTNLO,Bh1g1HTNLO
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2,shat
      common/pmom/p

c     Normalisation to yield overall (as/2/pi) factor.
      fac    = 1d0/8d0/pi**2

      nf     = 2d0*tr      ! tr=nf/2
      sig3HG = 0d0
      if (njets.ne.3) return

c     Check which contributions to include.
      doTree  = .false.
      do1Loop = .false.
      do2Loop = .false.
      if (nloop.ge.0) doTree = .true.
      if (nloop.ge.1.or.nloop.eq.-1) do1Loop = .true.
      if (abs(nloop).eq.2) do2Loop = .true.

c     Tree-level contributions.
      if (doTree)then
c     NC contribution.
         if (icol.eq.0.or.icol.eq.1)then
            sig3HG = sig3HG
     .           + 1d0/3d0*(4d0*pi*as)*cn*(
     .           + A3g0H(p,i1,i2,i3)
     .           + A3g0H(p,i1,i3,i2)
     .           )
         endif
c     NF/NC contribution.
         if (icol.eq.0.or.icol.eq.2)then
            sig3HG = sig3HG
     .           + 2d0*(4d0*pi*as)*nf*B1g0H(p,i1,i3,i2)
         endif
      endif

c     One-loop contributions.
      if (do1Loop)then
         npole = 0
         if (idebug.ge.1) npole = -2
         sig3HGV(:)    = 0d0
         sig3HGTNLO(:) = 0d0

c     NC^2 terms.
         if (icol.eq.0.or.icol.eq.1)then
            do ipole=npole,0
               sig3HGV(ipole) = sig3HGV(ipole)
     .              + 1d0/3d0*(as/2d0/pi)*(4d0*pi*as)*cn**2*(
     .              + A3g1H(p,i1,i2,i3,shat,ipole)
     .              + A3g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HGTNLO(ipole) = sig3HGTNLO(ipole)
     .              + 1d0/3d0*(as/2d0/pi)*(4d0*pi*as)*cn**2*(
     .              + A3g1HTNLO(p,i1,i2,i3,shat,ipole)
     .              + A3g1HTNLO(p,i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif
c     NF*NC terms.
         if (icol.eq.0.or.icol.eq.2)then
            do ipole=npole,0
               sig3HGV(ipole) = sig3HGV(ipole)
     .              + 1d0/3d0*(as/2d0/pi)*(4d0*pi*as)*nf*cn*(
     .              + Ah3g1H(p,i1,i2,i3,shat,ipole)
     .              + Ah3g1H(p,i1,i3,i2,shat,ipole)
     .              )
     .              + 2d0*(as/2d0/pi)*(4d0*pi*as)*nf*cn*(
     .              + B1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HGTNLO(ipole) = sig3HGTNLO(ipole)
     .              + 1d0/3d0*(as/2d0/pi)*(4d0*pi*as)*nf*cn*(
     .              + Ah3g1HTNLO(p,i1,i2,i3,shat,ipole)
     .              + Ah3g1HTNLO(p,i1,i3,i2,shat,ipole)
     .              )
     .              + 2d0*(as/2d0/pi)*(4d0*pi*as)*nf*cn*(
     .              + B1g1HTNLO(p,i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif     
c     NF/NC terms.
         if (icol.eq.0.or.icol.eq.3)then
            do ipole=npole,0
               sig3HGV(ipole) = sig3HGV(ipole)
     .              - 2d0*(as/2d0/pi)*(4d0*pi*as)*nf/cn*(
     .              + Bt1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HGTNLO(ipole) = sig3HGTNLO(ipole)
     .              - 2d0*(as/2d0/pi)*(4d0*pi*as)*nf/cn*(
     .              + Bt1g1HTNLO(p,i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif
c     NF^2 terms.
         if (icol.eq.0.or.icol.eq.4)then
            do ipole=npole,0
               sig3HGV(ipole) = sig3HGV(ipole)
     .              + 2d0*(as/2d0/pi)*(4d0*pi*as)*nf**2*(
     .              + Bh1g1H(p,i1,i3,i2,shat,ipole)
     .              )
               sig3HGTNLO(ipole) = sig3HGTNLO(ipole)
     .              + 2d0*(as/2d0/pi)*(4d0*pi*as)*nf**2*(
     .              + Bh1g1HTNLO(p,i1,i3,i2,shat,ipole)
     .              )
            enddo
         endif

c     Check pole cancellation.
         if (idebug.ge.1)then
            ptest1 = 0d0
            ptest2 = 0d0
            if (sig3HGV(-1).gt.1d-9)
     .           ptest1 = abs((sig3HGV(-1)+sig3HGTNLO(-1))/sig3HGV(-1))
            if (sig3HGV(-2).gt.1d-9)
     .           ptest2 = abs((sig3HGV(-2)+sig3HGTNLO(-2))/sig3HGV(-2))
            if (idebug.eq.2)then
               print *, sig3HGV(-1),sig3HGTNLO(-1),ptest1
               print *, sig3HGV(-2),sig3HGTNLO(-2),ptest2
            endif
            if (ptest1.gt.1d-9.or.ptest2.gt.1d-9)then
               write(6,*) 'Error in sig3HG():',
     .              ' Incomplete pole cancellation!',ptest1,ptest2
               stop
            endif
         endif
         
c     Assemble final result.
         sig3HG = sig3HG + sig3HGV(0) + sig3HGTNLO(0)
      endif

c     Two-loop contributions.
      if (do2Loop)then
         stop'Two-loop corrections for H -> 3j not implemented'
      endif

      sig3HG = fac*sig3HG

      if (plot)then
         call bino(1,sig3HG*wtplot*var3,3)
      else
         call distrib(wtdis)
         sig3HG = sig3HG/wtdis
      endif

      return
      end

************************************************************************

c     Four-parton contributions.
c     Containing tree-level and one-loop contributions.
      real(8) function sig4HG(i1,i2,i3,i4,wtplot,var4)
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
      real(8)             :: ptest1,ptest2
      real(8)             :: fac,wtdis,sig4HGV(-2:0),sig4HGTNLO(-2:0)
c     Externals.
      real(8), external   :: A4g0H,B2g0H,Bt2g0H,C0g0H,D0g0H
      real(8), external   :: A4g1H,Ah4g1H
      real(8), external   :: B2g1H,Bt2g1H,Bh2g1H
      real(8), external   :: Btt2g1H,Bttt2g1H,Btth2g1H,Bhh2g1H
      real(8), external   :: C0g1H,Ct0g1H,Ch0g1H,D0g1H,Dt0g1H,Dh0g1H
      real(8), external   :: A4g1HTNLO,Ah4g1HTNLO
      real(8), external   :: B2g1HTNLO,Bt2g1HTNLO,Bh2g1HTNLO
      real(8), external   :: Btt2g1HTNLO,Bttt2g1HTNLO,Btth2g1HTNLO
      real(8), external   :: C0g1HTNLO,Ct0g1HTNLO,D0g1HTNLO,Dt0g1HTNLO
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2,shat
      common/yij4/y
      common/pmom/p

c     Normalisation to yield overall (as/2/pi) factor.
      fac    = (1d0/8d0/pi**2)**2

      nf     = int(2d0*tr)      ! tr=nf/2
      sig4HG = 0d0
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
c     NC^2 terms.
         if (icol.eq.0.or.icol.eq.1)then
            sig4HG = sig4HG
     .           + 1d0/12d0*(4d0*pi*as)**2*cn**2*(
     .           + A4g0H(p,i1,i2,i3,i4)
     .           + A4g0H(p,i1,i2,i4,i3)
     .           + A4g0H(p,i1,i3,i2,i4)
     .           + A4g0H(p,i1,i3,i4,i2)
     .           + A4g0H(p,i1,i4,i2,i3)
     .           + A4g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     NF*NC terms.
         if (icol.eq.0.or.icol.eq.2)then
            sig4HG = sig4HG
     .           + (4d0*pi*as)**2*cn*nf*(
     .           + B2g0H(p,i1,i3,i4,i2)
     .           + B2g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     NF/NC terms.
         if (icol.eq.0.or.icol.eq.3)then
            sig4HG = sig4HG
     .           - (4d0*pi*as)**2*nf/cn*(
     .           + Bt2g0H(p,i1,i3,i4,i2)
     .           )
         endif
c     NF^2 terms.
         if (icol.eq.0.or.icol.eq.4)then
            sig4HG = sig4HG
     .           + 2d0*(4d0*pi*as)**2*(nf-1d0)*nf*(
     .           + C0g0H(p,i1,i4,i3,i2)
     .           )
     .           + 1d0/2d0*(4d0*pi*as)**2*nf*(
     .           + C0g0H(p,i1,i4,i3,i2)
     .           + C0g0H(p,i1,i2,i3,i4)
     .           - 1d0/cn*D0g0H(p,i1,i4,i3,i2)
     .           )
         endif
      endif

c     One-loop contributions.
      if (doLoop)then
         npole = 0
         if (idebug.ge.1) npole = -2
         sig4HGV(:)    = 0d0
         sig4HGTNLO(:) = 0d0

c     NC^3 terms.
         if (icol.eq.0.or.icol.eq.1)then
            do ipole=npole,0
               sig4HGV(ipole) = sig4HGV(ipole)
     .              + 1d0/12d0*(as/2d0/pi)*(4d0*pi*as)**2*cn**3*(
     .              + A4g1H(p,i1,i2,i3,i4,shat,ipole)
     .              + A4g1H(p,i1,i2,i4,i3,shat,ipole)
     .              + A4g1H(p,i1,i3,i2,i4,shat,ipole)
     .              + A4g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + A4g1H(p,i1,i4,i2,i3,shat,ipole)
     .              + A4g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .              + 1d0/12d0*(as/2d0/pi)*(4d0*pi*as)**2*cn**3*(
     .              + A4g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              + A4g1HTNLO(i1,i2,i4,i3,shat,ipole)
     .              + A4g1HTNLO(i1,i3,i2,i4,shat,ipole)
     .              + A4g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + A4g1HTNLO(i1,i4,i2,i3,shat,ipole)
     .              + A4g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
            enddo
c     First-order expansion of Wilson coefficient.
            sig4HGV(0) = sig4HGV(0)
     .           + 1d0/12d0*(as/2d0/pi)*(4d0*pi*as)**2*11d0/3d0*cn**3*(
     .           + A4g0H(p,i1,i2,i3,i4)
     .           + A4g0H(p,i1,i2,i4,i3)
     .           + A4g0H(p,i1,i3,i2,i4)
     .           + A4g0H(p,i1,i3,i4,i2)
     .           + A4g0H(p,i1,i4,i2,i3)
     .           + A4g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     NF*NC^2 terms.
         if (icol.eq.0.or.icol.eq.2)then
            do ipole=npole,0
               sig4HGV(ipole) = sig4HGV(ipole)
     .              + 1d0/12d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*cn**2*(
     .              + Ah4g1H(p,i1,i2,i3,i4,shat,ipole)
     .              + Ah4g1H(p,i1,i2,i4,i3,shat,ipole)
     .              + Ah4g1H(p,i1,i3,i2,i4,shat,ipole)
     .              + Ah4g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + Ah4g1H(p,i1,i4,i2,i3,shat,ipole)
     .              + Ah4g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf*cn**2*(
     .              + B2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + B2g1H(p,i1,i4,i3,i2,shat,ipole)
     .              )

               sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .              + 1d0/12d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*cn**2*(
     .              + Ah4g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              + Ah4g1HTNLO(i1,i2,i4,i3,shat,ipole)
     .              + Ah4g1HTNLO(i1,i3,i2,i4,shat,ipole)
     .              + Ah4g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + Ah4g1HTNLO(i1,i4,i2,i3,shat,ipole)
     .              + Ah4g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf*cn**2*(
     .              + B2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              + B2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              )
            enddo
c     First-order expansion of Willson coefficient.
            sig4HGV(0) = sig4HGV(0)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*11d0/3d0*nf*cn**2*(
     .           + B2g0H(p,i1,i3,i4,i2)
     .           + B2g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     NF terms.
         if (icol.eq.0.or.icol.eq.3)then
            do ipole=npole,0
               sig4HGV(ipole) = sig4HGV(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf*(
     .              - Bt2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              - Bt2g1H(p,i1,i4,i3,i2,shat,ipole)
     .              - Btt2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              + Bhh2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              )
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(
     .              + D0g1H(p,i1,i2,i3,i4,shat,ipole)
     .              )

               sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf*(
     .              - Bt2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              - Bt2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .              - Btt2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              )
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(
     .              + D0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              )
            enddo
c     First-order expansion of Wilson coefficient.
            sig4HGV(0) = sig4HGV(0)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*11d0/3d0*nf*(
     .           - Bt2g0H(p,i1,i3,i4,i2)
     .           )
     .           - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*11d0/3d0*nf*(
     .           + D0g0H(p,i1,i4,i3,i2)
     .           )
         endif
c     NF/NC^2 terms.
         if (icol.eq.0.or.icol.eq.4)then
            do ipole=npole,0
               sig4HGV(ipole) = sig4HGV(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf/cn**2*(
     .              + Bttt2g1H(p,i1,i3,i4,i2,shat,ipole)
     .              )
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf/cn**2*(
     .              + Dt0g1H(p,i1,i2,i3,i4,shat,ipole)
     .              )

               sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .              + (as/2d0/pi)*(4d0*pi*as)**2*nf/cn**2*(
     .              + Bttt2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .              )
     .              - 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf/cn**2*(
     .              + Dt0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .              )
            enddo
         endif
c     NF^2*NC terms.
      if (icol.eq.0.or.icol.eq.5)then
         do ipole=npole,0
            sig4HGV(ipole) = sig4HGV(ipole)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*nf**2*cn*(
     .           + Bh2g1H(p,i1,i3,i4,i2,shat,ipole)
     .           + Bh2g1H(p,i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(nf-1d0)*cn*(
     .           + C0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*cn*(
     .           + C0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           + C0g1H(p,i1,i2,i3,i4,shat,ipole)
     .           )

            sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*nf**2*cn*(
     .           + Bh2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .           + Bh2g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(nf-1d0)*cn*(
     .           + C0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*cn*(
     .           + C0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .           + C0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .           )
         enddo 
c     First-order expansion of Wilson coefficient.
         sig4HGV(0) = sig4HGV(0)
     .        + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*11d0/3d0*nf*(nf-1d0)*cn*(
     .        + C0g0H(p,i1,i4,i3,i2)
     .        )
     .        + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*(11d0/3d0)*nf*cn*(
     .        + C0g0H(p,i1,i4,i3,i2)
     .        + C0g0H(p,i1,i2,i3,i4)
     .        )
      endif
c     NF^2/NC terms.
      if (icol.eq.0.or.icol.eq.6)then
         do ipole=npole,0
            sig4HGV(ipole) = sig4HGV(ipole)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*nf**2/cn*(
     .           - Btth2g1H(p,i1,i3,i4,i2,shat,ipole)
     .           )
     .           + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(nf-1d0)/cn*(
     .           - Ct0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf/cn*(
     .           - Ct0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           - Ct0g1H(p,i1,i2,i3,i4,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf/cn*(
     .           + Dh0g1H(p,i1,i2,i3,i4,shat,ipole)
     .           )

            sig4HGTNLO(ipole) = sig4HGTNLO(ipole)
     .           + (as/2d0/pi)*(4d0*pi*as)**2*nf**2/cn*(
     .           - Btth2g1HTNLO(i1,i3,i4,i2,shat,ipole)
     .           )
     .           + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf*(nf-1d0)/cn*(
     .           - Ct0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf/cn*(
     .           - Ct0g1HTNLO(i1,i4,i3,i2,shat,ipole)
     .           - Ct0g1HTNLO(i1,i2,i3,i4,shat,ipole)
     .           )
         enddo
      endif
c     NF^3 terms.
      if (icol.eq.0.or.icol.eq.7)then
         do ipole=npole,0
            sig4HGV(ipole) = sig4HGV(ipole)
     .           + 2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf**2*(nf-1d0)*(
     .           + Ch0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           )
     .           + 1d0/2d0*(as/2d0/pi)*(4d0*pi*as)**2*nf**2*(
     .           + Ch0g1H(p,i1,i4,i3,i2,shat,ipole)
     .           + Ch0g1H(p,i1,i2,i3,i4,shat,ipole)
     .           )
         enddo
      endif

c     Check pole cancellation.
         if (idebug.ge.1)then
            ptest1 = 0d0
            ptest2 = 0d0
            if (sig4HGV(-1).gt.1d-9)
     .           ptest1 = abs((sig4HGV(-1)+sig4HGTNLO(-1))/sig4HGV(-1))
            if (sig4HGV(-2).gt.1d-9)
     .           ptest2 = abs((sig4HGV(-2)+sig4HGTNLO(-2))/sig4HGV(-2))
            if (idebug.eq.2)then
               print *, sig4HGV(-1),sig4HGTNLO(-1),ptest1
               print *, sig4HGV(-2),sig4HGTNLO(-2),ptest2
            endif
            if (ptest1.gt.1d-9.or.ptest2.gt.1d-9)then
               write(6,*) 'Error in sig4HG():',
     .              ' Incomplete pole cancellation!',ptest1,ptest2
               stop
            endif
         endif

c     Assemble final result.
         sig4HG = sig4HG + sig4HGV(0) + sig4HGTNLO(0)
      endif

      sig4HG = fac*sig4HG

      if (plot)then
         call bino(1,sig4HG*wtplot*var4,4)
      else
         call distrib(wtdis)
         sig4HG = sig4HG/wtdis
      endif

      return
      end


c-----------------------------------------------------------------------

c     Five-parton contributions.
c     Containing tree-level contributions.
      function sig5HG(i1,i2,i3,i4,i5,wtplot,var5)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot,var5
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iproc,njets,nloop,icol,ichan
      real(8)             :: p(4,5)
      real(8)             :: sig5HG,fac,wt,wtdis
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external   :: A5g0H
      real(8), external   :: B3g0H,Bt3g0H,Btt3g0H
      real(8), external   :: C1g0Ha,C1g0Hb
      real(8), external   :: Ct1g0Ha,Ct1g0Hb,Ctt1g0H
      real(8), external   :: D1g0H,Dt1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p

c     Normalisation to yield overall factor (as/2d0/pi).
      fac    = (1d0/8d0/pi**2)**3

      nf     = int(2d0*tr)      ! tr=nf/2
      sig5HG = 0d0
      if (njets.gt.5) return

c     NC^3 terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig5HG = sig5HG
     .        + 1d0/60d0*(4d0*pi*as)**3*cn**3*(
     .        + A5g0H(p,i1,i2,i3,i4,i5)
     .        + A5g0H(p,i1,i2,i3,i5,i4)
     .        + A5g0H(p,i1,i2,i4,i3,i5)
     .        + A5g0H(p,i1,i2,i4,i5,i3)
     .        + A5g0H(p,i1,i2,i5,i3,i4)
     .        + A5g0H(p,i1,i2,i5,i4,i3)
     .        + A5g0H(p,i1,i3,i2,i4,i5)
     .        + A5g0H(p,i1,i3,i2,i5,i4)
     .        + A5g0H(p,i1,i4,i2,i3,i5)
     .        + A5g0H(p,i1,i4,i2,i5,i3)
     .        + A5g0H(p,i1,i5,i2,i3,i4)
     .        + A5g0H(p,i1,i5,i2,i4,i3)
     .        )
      endif
c     NF*NC^2 terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig5HG = sig5HG
     .        + 1d0/3d0*(4d0*pi*as)**3*nf*cn**2*(
     .        + B3g0H(p,i1,i3,i4,i5,i2)
     .        + B3g0H(p,i1,i3,i5,i4,i2)
     .        + B3g0H(p,i1,i4,i3,i5,i2)
     .        + B3g0H(p,i1,i4,i5,i3,i2)
     .        + B3g0H(p,i1,i5,i3,i4,i2)
     .        + B3g0H(p,i1,i5,i4,i3,i2)
     .        )
      endif
c     NF terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig5HG = sig5HG
     .        - 1d0/3d0*(4d0*pi*as)**3*nf*(
     .        + Bt3g0H(p,i1,i3,i4,i5,i2)
     .        + Bt3g0H(p,i1,i3,i5,i4,i2)
     .        + Bt3g0H(p,i1,i4,i3,i5,i2)
     .        + Bt3g0H(p,i1,i4,i5,i3,i2)
     .        + Bt3g0H(p,i1,i5,i3,i4,i2)
     .        + Bt3g0H(p,i1,i5,i4,i3,i2)
     .        )
     .        + 1d0/3d0*(4d0*pi*as)**3*nf*(
     .        + Btt3g0H(p,i1,i3,i4,i5,i2)
     .        )
     .        - 1d0/2d0*(4d0*pi*as)**3*nf*(
     .        + D1g0H(p,i1,i2,i3,i4,i5)
     .        - Dt1g0H(p,i1,i2,i3,i4,i5)
     .        )
      endif
c     NF/NC^2 terms.
      if (icol.eq.0.or.icol.eq.4)then
         sig5HG = sig5HG
     .        + 1d0/3d0*(4d0*pi*as)**3*nf/cn**2*(
     .        + Btt3g0H(p,i1,i3,i4,i5,i2)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf/cn**2*(
     .        + Dt1g0H(p,i1,i2,i3,i4,i5)
     .        )
      endif
c     NF^2*NC terms.
      if (icol.eq.0.or.icol.eq.5)then
         sig5HG = sig5HG
     .        + 2d0*(4d0*pi*as)**3*nf*(nf-1d0)*cn*(
     .        + C1g0Ha(p,i1,i5,i4,i3,i2)
     .        + C1g0Hb(p,i1,i4,i3,i5,i2)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf*cn*(
     .        + C1g0Ha(p,i1,i5,i4,i3,i2)
     .        + C1g0Hb(p,i1,i4,i3,i5,i2)
     .        + C1g0Ha(p,i1,i5,i2,i3,i4)
     .        + C1g0Hb(p,i1,i2,i3,i5,i4)
     .        )
      endif
c     NF^2/NC terms.
      if (icol.eq.0.or.icol.eq.6)then
c     Note: Ctt1g0H is symmetrised over momenta 3 and 4.
         sig5HG = sig5HG
     .        + 2d0*(4d0*pi*as)**3*nf*(nf-1d0)/cn*(
     .        + Ct1g0Ha(p,i1,i5,i2,i3,i4)
     .        + Ct1g0Hb(p,i1,i2,i3,i5,i4)
     .        - Ctt1g0H(p,i1,i2,i3,i4,i5)
     .        - Ctt1g0H(p,i1,i2,i4,i3,i5)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf/cn*(
     .        + Ct1g0Ha(p,i1,i5,i2,i3,i4)
     .        + Ct1g0Hb(p,i1,i2,i3,i5,i4)
     .        - Ctt1g0H(p,i1,i2,i3,i4,i5)
     .        - Ctt1g0H(p,i1,i2,i4,i3,i5)
     .        + Ct1g0Ha(p,i1,i5,i4,i3,i2)
     .        + Ct1g0Hb(p,i1,i4,i3,i5,i2)
     .        - Ctt1g0H(p,i1,i4,i3,i2,i5)
     .        - Ctt1g0H(p,i1,i4,i2,i3,i5)
     .        )
      endif
      sig5HG = fac*sig5HG

      if (plot)then
         call bino(1,sig5HG*wtplot*var5,5)
      else
         call distrib(wtdis)
         sig5HG = sig5HG/wtdis
      endif

      return
      end

c-----------------------------------------------------------------------
c     Differential subtraction terms called by VEGAS integrand above.
c-----------------------------------------------------------------------

c     3-jet NLO subtraction term.
      real(8) function sig3HGs(i1,i2,i3,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
      real(8), parameter  :: pi=3.141592653589793238d0
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: iproc,nloop,icol,njets,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: fac,wt,wt1,wt2,wt3,wt4,wt5
c     Externals.
      real(8), external   :: A4g0HSNLO,B2g0HSNLO,Bt2g0HSNLO,C0g0HSNLO
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/qcd/as,ca,cflo,cf,tr,cn

c     Normalisation to yield overall factor (as/2d0/pi).
      fac    = (1d0/8d0/pi**2)**2

      nf      = int(2d0*tr)     ! tr=nf/2
      sig3HGs = 0d0

c     Set plot weights.
      wt1 = -fac*wtplot*1d0/12d0*(4d0*pi*as)**2*cn**2
      wt2 = -fac*wtplot*(4d0*pi*as)**2*cn*nf
      wt3 = -fac*wtplot*(-(4d0*pi*as)**2*nf/cn)
      wt4 = -fac*wtplot*2d0*(4d0*pi*as)**2*(nf-1d0)*nf
      wt5 = -fac*wtplot*1d0/2d0*(4d0*pi*as)**2*nf

c     NC^2 terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig3HGs = sig3HGs
     .        + 1d0/12d0*(4d0*pi*as)**2*cn**2*(
     .        + A4g0HSNLO(i1,i2,i3,i4,wt1)
     .        + A4g0HSNLO(i1,i2,i4,i3,wt1)
     .        + A4g0HSNLO(i1,i3,i2,i4,wt1)
     .        + A4g0HSNLO(i1,i3,i4,i2,wt1)
     .        + A4g0HSNLO(i1,i4,i2,i3,wt1)
     .        + A4g0HSNLO(i1,i4,i3,i2,wt1)
     .        )
      endif
c     NF*NC terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig3HGs = sig3HGs
     .        + (4d0*pi*as)**2*cn*nf*(
     .        + B2g0HSNLO(i1,i3,i4,i2,wt2)
     .        + B2g0HSNLO(i1,i4,i3,i2,wt2)
     .        )
      endif
c     NF/NC terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig3HGs = sig3HGs
     .        - (4d0*pi*as)**2*nf/cn*(
     .        + Bt2g0HSNLO(i1,i3,i4,i2,wt3)
     .        )
      endif
c     NF^2 terms.
      if (icol.eq.0.or.icol.eq.4)then
         sig3HGs = sig3HGs
     .        + 2d0*(4d0*pi*as)**2*(nf-1d0)*nf*(
     .        + C0g0HSNLO(i1,i4,i3,i2,wt4)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**2*nf*(
     .        + C0g0HSNLO(i1,i4,i3,i2,wt5)
     .        + C0g0HSNLO(i1,i2,i3,i4,wt5)
     .        )
      endif

      sig3HGs = fac*sig3HGs

      return
      end

************************************************************************

c     4-jet real subtraction term.
      real(8) function sig4HGs(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iproc,njets,nloop,icol,ichan
      real(8)             :: as,ca,cflo,cf,tr,cn, nf
      real(8)             :: p(4,5)
      real(8)             :: fac,wt1,wt2,wt3,wt4,wt5
      real(8)             :: wt6,wt7,wt8,wt9,wt10,wt11
c     Externals.
      real(8), external   :: A5g0HSNLO
      real(8), external   :: B3g0HSNLO,Bt3g0HSNLO,Btt3g0HSNLO
      real(8), external   :: C1g0HSNLOa,C1g0HSNLOb
      real(8), external   :: Ct1g0HSNLOa,Ct1g0HSNLOb,Ctt1g0HSNLO
      real(8), external   :: D1g0HSNLO,Dt1g0HSNLO
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p

c     Normalisation to yield overall factor (as/2d0/pi).
      fac = (1d0/8d0/pi**2)**3

      nf      = int(2d0*tr)     ! tr=nf/2
      sig4HGs = 0d0

c     Set plot weights.
      wt1  = -fac*wtplot*1d0/60d0*(4d0*pi*as)**3*cn**3
      wt2  = -fac*wtplot*1d0/3d0*(4d0*pi*as)**3*nf*cn**2
      wt3  = -fac*wtplot*(-1d0/3d0*(4d0*pi*as)**3*nf)
      wt4  = -fac*wtplot*1d0/3d0*(4d0*pi*as)**3*nf
      wt5  = -fac*wtplot*(-1d0/2d0*(4d0*pi*as)**3*nf)
      wt6  = -fac*wtplot*1d0/3d0*(4d0*pi*as)**3*nf/cn**2
      wt7  = -fac*wtplot*1d0/2d0*(4d0*pi*as)**3*nf/cn**2
      wt8  = -fac*wtplot*2d0*(4d0*pi*as)**3*nf*(nf-1d0)*cn
      wt9  = -fac*wtplot*1d0/2d0*(4d0*pi*as)**3*nf*cn
      wt10 = -fac*wtplot*2d0*(4d0*pi*as)**3*nf*(nf-1d0)/cn
      wt11 = -fac*wtplot*1d0/2d0*(4d0*pi*as)**3*nf/cn

c     NC^3 terms.
      if (icol.eq.0.or.icol.eq.1)then
         sig4HGs = sig4HGs
     .        + 1d0/60d0*(4d0*pi*as)**3*cn**3*(
     .        + A5g0HSNLO(i1,i2,i3,i4,i5,wt1)
     .        + A5g0HSNLO(i1,i5,i4,i3,i2,wt1)
     .        + A5g0HSNLO(i1,i2,i3,i5,i4,wt1)
     .        + A5g0HSNLO(i1,i4,i5,i3,i2,wt1)
     .        + A5g0HSNLO(i1,i2,i4,i3,i5,wt1)
     .        + A5g0HSNLO(i1,i5,i3,i4,i2,wt1)
     .        + A5g0HSNLO(i1,i2,i4,i5,i3,wt1)
     .        + A5g0HSNLO(i1,i3,i5,i4,i2,wt1)
     .        + A5g0HSNLO(i1,i2,i5,i3,i4,wt1)
     .        + A5g0HSNLO(i1,i4,i3,i5,i2,wt1)
     .        + A5g0HSNLO(i1,i2,i5,i4,i3,wt1)
     .        + A5g0HSNLO(i1,i3,i4,i5,i2,wt1)
     .        + A5g0HSNLO(i1,i3,i2,i4,i5,wt1)
     .        + A5g0HSNLO(i1,i5,i4,i2,i3,wt1)
     .        + A5g0HSNLO(i1,i3,i2,i5,i4,wt1)
     .        + A5g0HSNLO(i1,i4,i5,i2,i3,wt1)
     .        + A5g0HSNLO(i1,i4,i2,i3,i5,wt1)
     .        + A5g0HSNLO(i1,i5,i3,i2,i4,wt1)
     .        + A5g0HSNLO(i1,i4,i2,i5,i3,wt1)
     .        + A5g0HSNLO(i1,i3,i5,i2,i4,wt1)
     .        + A5g0HSNLO(i1,i5,i2,i3,i4,wt1)
     .        + A5g0HSNLO(i1,i4,i3,i2,i5,wt1)
     .        + A5g0HSNLO(i1,i5,i2,i4,i3,wt1)
     .        + A5g0HSNLO(i1,i3,i4,i2,i5,wt1)
     .        )
      endif
c     NF*NC^2 terms.
      if (icol.eq.0.or.icol.eq.2)then
         sig4HGs = sig4HGs
     .        + 1d0/3d0*(4d0*pi*as)**3*nf*cn**2*(
     .        + B3g0HSNLO(i1,i3,i4,i5,i2,wt2)
     .        + B3g0HSNLO(i1,i3,i5,i4,i2,wt2)
     .        + B3g0HSNLO(i1,i4,i3,i5,i2,wt2)
     .        + B3g0HSNLO(i1,i4,i5,i3,i2,wt2)
     .        + B3g0HSNLO(i1,i5,i3,i4,i2,wt2)
     .        + B3g0HSNLO(i1,i5,i4,i3,i2,wt2)
     .        )
      endif
c     NF*NC^0 terms.
      if (icol.eq.0.or.icol.eq.3)then
         sig4HGs = sig4HGs
     .        - 1d0/3d0*(4d0*pi*as)**3*nf*(
     .        + Bt3g0HSNLO(i1,i3,i4,i5,i2,wt3)
     .        + Bt3g0HSNLO(i1,i3,i5,i4,i2,wt3)
     .        + Bt3g0HSNLO(i1,i4,i3,i5,i2,wt3)
     .        + Bt3g0HSNLO(i1,i4,i5,i3,i2,wt3)
     .        + Bt3g0HSNLO(i1,i5,i3,i4,i2,wt3)
     .        + Bt3g0HSNLO(i1,i5,i4,i3,i2,wt3)
     .        )
     .        + 1d0/3d0*(4d0*pi*as)**3*nf*(
     .        + Btt3g0HSNLO(i1,i3,i4,i5,i2,wt4)
     .        )
     .        - 1d0/2d0*(4d0*pi*as)**3*nf*(
     .        + D1g0HSNLO(i1,i2,i3,i4,i5,wt5)
     .        - Dt1g0HSNLO(i1,i2,i3,i4,i5,wt5)
     .        )
      endif
c     NF*(NC^0+1/NC^2) terms.
      if (icol.eq.0.or.icol.eq.4)then
         sig4HGs = sig4HGs
     .        + 1d0/3d0*(4d0*pi*as)**3*nf/cn**2*(
     .        + Btt3g0HSNLO(i1,i3,i4,i5,i2,wt6)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf/cn**2*(
     .        + Dt1g0HSNLO(i1,i2,i3,i4,i5,wt7)
     .        )
      endif
c     NF^2*NC^1 terms.
      if (icol.eq.0.or.icol.eq.5)then
         sig4HGs = sig4HGs
     .        + 2d0*(4d0*pi*as)**3*nf*(nf-1d0)*cn*(
     .        + C1g0HSNLOa(i1,i5,i4,i3,i2,wt8)
     .        + C1g0HSNLOb(i1,i4,i3,i5,i2,wt8)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf*cn*(
     .        + C1g0HSNLOa(i1,i5,i4,i3,i2,wt9)
     .        + C1g0HSNLOb(i1,i4,i3,i5,i2,wt9)
     .        + C1g0HSNLOa(i1,i5,i2,i3,i4,wt9)
     .        + C1g0HSNLOb(i1,i2,i3,i5,i4,wt9)
     .        )
      endif
c     NF^2/NC^1 terms.
      if (icol.eq.0.or.icol.eq.6)then
c     Note: Ctt1g0HSNLO is symmetrised over momenta 3 and 4.
         sig4HGs = sig4HGs
     .        + 2d0*(4d0*pi*as)**3*nf*(nf-1d0)/cn*(
     .        + Ct1g0HSNLOa(i1,i5,i2,i3,i4,wt10)
     .        + Ct1g0HSNLOb(i1,i2,i3,i5,i4,wt10)
     .        - Ctt1g0HSNLO(i1,i2,i3,i4,i5,-wt10)
     .        - Ctt1g0HSNLO(i1,i2,i4,i3,i5,-wt10)
     .        )
     .        + 1d0/2d0*(4d0*pi*as)**3*nf/cn*(
     .        + Ct1g0HSNLOa(i1,i5,i2,i3,i4,wt11)
     .        + Ct1g0HSNLOb(i1,i2,i3,i5,i4,wt11)
     .        - Ctt1g0HSNLO(i1,i2,i3,i4,i5,-wt11)
     .        - Ctt1g0HSNLO(i1,i2,i4,i3,i5,-wt11)
     .        + Ct1g0HSNLOa(i1,i5,i4,i3,i2,wt11)
     .        + Ct1g0HSNLOb(i1,i4,i3,i5,i2,wt11)
     .        - Ctt1g0HSNLO(i1,i4,i3,i2,i5,-wt11)
     .        - Ctt1g0HSNLO(i1,i4,i2,i3,i5,-wt11)
     .        )
      endif
      sig4HGs = fac*sig4HGs

      return
      end

************************************************************************

c     3-jet double-real subtraction term.
      real(8) function sig3HGds(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
      real(8), parameter  :: pi=3.141592653589793238d0
      logical             :: plot
      integer             :: iproc,njets,nloop,icol,ichan
      real(8)             :: p(4,5)
      real(8)             :: fac,wt1,wt2,wt3,wt4,wt5,wt6
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/inphys/iproc,nloop,icol,njets,ichan
      common/plots/plot
      common/pmom/p
c     Externals.
      real(8), external   :: A5g0HS

c     Normalisation to yield overall (as/2/pi) factor.
      fac      = (1d0/8d0/pi**2)**3

      nf       = int(2d0*tr)    ! tr=nf/2
      sig3HGds = 0d0

      stop 'sigHG: NNLO not yet implemented'

      sig3HGds = fac*sig3HGds

      return
      end

c-----------------------------------------------------------------------
