c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     NLO subtraction terms for H -> 4j and H -> 5j (gluon channel).

c-----------------------------------------------------------------------
c     Real four-parton subtraction terms.
c-----------------------------------------------------------------------

c     Real subtraction term for LC contribution of
c     H -> g(i1) g(i2) g(i3) g(i4).
      real(8) function A4g0HSNLO(i1,i2,i3,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: sf30n,A3g0H
c     Common blocks.
      common/plots/plot
      common/yij4/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Initialise.
      wt = 0d0

c     4-1-2 antenna.
      call pmap4to3(i4,i1,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(s24,s14,s12)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-2-3 antenna.
      call pmap4to3(i1,i2,i3,i4,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(s13,s12,s23)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap4to3(i2,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(s24,s23,s34)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-4-1 antenna.
      call pmap4to3(i3,i4,i1,i2,3,1,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(s13,s34,s14)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      A4g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function B2g0HSNLO(i1,i3,i4,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: sd30n,E30n,B1g0H,A3g0H
c     Common blocks.
      common/plots/plot
      common/yij4/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Initialise.
      wt = 0d0

c     D30 contributions.

c     1-3-4 antenna.
      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s14,s13,s34)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-4-3 antenna.
      call pmap4to3(i2,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s23,s24,s34)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif
     
c     E30 contributions.

c     3-1-2 antenna.
      call pmap4to3(i3,i1,i2,i4,1,2,3)  
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 0.5d0*E30n(s23,s13,s12)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif
      
c     4-2-1 antenna.
      call pmap4to3(i4,i2,i1,i3,2,1,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 0.5d0*E30n(s14,s24,s12)*A3g0H(p3,1,2,3)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      B2g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> q(i1) g(i3) g(i4) qbar(i2).
      real(8) function Bt2g0HSNLO(i1,i3,i4,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n,B1g0H
c     Common blocks.
      common/plots/plot
      common/yij4/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Initialise.
      wt = 0d0

c     1-3-2 antenna.
      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then 
         wtsub = A30n(s12,s13,s23)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-2 antenna.
      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s14,s24)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Bt2g0HSNLO = wt

      return
      end
      
************************************************************************

c     Real subtraction term for
c     H -> q(i1) qb(i2) Q(i3) Qbar(i4).
      real(8) function C0g0HSNLO(i1,i4,i3,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: E30n,B1g0H
c     Common blocks.
      common/plots/plot
      common/yij4/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Initialise.
      wt = 0d0

c     1st quark pair.

c     1-4-3 antenna.
      call pmap4to3(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s13,s14,s34)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-4-3 antenna.
      call pmap4to3(i2,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s23,s24,s34)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif
        
c     2nd quark pair.

c     4-1-2 antenna.
      call pmap4to3(i4,i1,i2,i3,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s24,s14,s12)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-2-1 antenna.
      call pmap4to3(i3,i2,i1,i4,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s13,s23,s12)*B1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      C0g0HSNLO = wt
      
      return
      end      

c-----------------------------------------------------------------------
c     Virtual four-parton subtraction terms.
c-----------------------------------------------------------------------

c     Virtual subtraction term for LC contribution of
c     H -> g(i1) g(i2) g(i3).
      real(8) function A3g1HTNLO(p,i1,i2,i3,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8)               :: sub,tree
      real(8)               :: s12,s13,s23
      real(8), external     :: dot,F30int,A3g0H

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Subtraction term.
      tree = A3g0H(p,i1,i2,i3)
      sub  =
     .     + 1d0/3d0*F30int(s12,renscale2,ipole)
     .     + 1d0/3d0*F30int(s13,renscale2,ipole)
     .     + 1d0/3d0*F30int(s23,renscale2,ipole)
      A3g1HTNLO = sub*tree

      return
      end

************************************************************************
      
c     Virtual subtraction term for QL contribution of
c     H -> g(i1) g(i2) g(i3).
      real(8) function Ah3g1HTNLO(p,i1,i2,i3,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8)               :: sub,tree
      real(8)               :: s12,s13,s23
      real(8), external     :: dot,E30int,A3g0H

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Subtraction term.
      tree = A3g0H(p,i1,i2,i3)
      sub  =
     .     + 1d0/2d0*E30int(s13,renscale2,ipole)
     .     + 1d0/2d0*E30int(s23,renscale2,ipole)
      Ah3g1HTNLO = 3d0*sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC contribution of
c     H -> q(i1) g(i3) qbar(i2).
      real(8) function B1g1HTNLO(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8)               :: sub,tree
      real(8)               :: s12,s13,s23
      real(8), external     :: dot,D30int,B1g0H

c     Invariants.
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Subtraction term.
      tree = B1g0H(p,i1,i3,i2)
      sub  =
     .     + 0.5d0*D30int(s13,renscale2,ipole)
     .     + 0.5d0*D30int(s23,renscale2,ipole)
      B1g1HTNLO = sub*tree

      return
      end      

************************************************************************

c     Virtual subtraction term for SLC contribution of
c     H -> q(i1) g(i3) qbar(i2).
      real(8) function Bt1g1HTNLO(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8)               :: sub,tree
      real(8)               :: s12,s13,s23
      real(8), external     :: dot,A30int,B1g0H

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))

c     Subtraction term.
      tree = B1g0H(p,i1,i3,i2)
      sub  = A30int(s12,renscale2,ipole)
      Bt1g1HTNLO = sub*tree

      return
      end      

************************************************************************

c     Virtual subtraction term for QL contribution to
c     H -> q(i1) g(i3) qbar(i2).
      real(8) function Bh1g1HTNLO(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8)               :: s12,s13,s23
      real(8)               :: sub,tree
      real(8), external     :: dot,E30int,B1g0H

c     Invariants.
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Subtraction term.
      tree = B1g0H(p,i1,i3,i2)
      sub  =
     .     + 1d0/2d0*E30int(s13,renscale2,ipole)
     .     + 1d0/2d0*E30int(s23,renscale2,ipole)
      Bh1g1HTNLO = sub*tree

      return
      end

c-----------------------------------------------------------------------
c     Real five-parton subtraction terms.
c-----------------------------------------------------------------------

c     Real subtraction term for
c     H -> g(i1) g(i2) g(i3) g(i4) g(i5).
      real(8) function A5g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: sf30n,A4g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     5-1-2 antenna.
      call pmap5to4(i5,i1,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y25,y15,y12)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-2-3 antenna.
      call pmap5to4(i1,i2,i3,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y13,y12,y23)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i3,i4,i5,i1,2,3,4,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y24,y23,y34)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-4-5 antenna.
      call pmap5to4(i3,i4,i5,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y35,y34,y45)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     4-5-1 antenna.
      call pmap5to4(i4,i5,i1,i2,i3,4,1,2,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y14,y45,y15)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      A5g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
      real(8) function B3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: sd30n,sf30n,G30n,B2g0H,A4g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(y14,y13,y34)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-4-5 antenna.
      call pmap5to4(i3,i4,i5,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sf30n(y35,y34,y45)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-5-4 antenna.
      call pmap5to4(i2,i5,i4,i1,i3,2,4,1,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(y24,y25,y45)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-1-2 antenna.
      call pmap5to4(i3,i1,i2,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*G30n(y23,y13,y12)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-2-1 antenna.
      call pmap5to4(i5,i2,i1,i3,i4,2,1,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*G30n(y15,y25,y12)*A4g0H(p4,1,2,3,4)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      B3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
      real(8) function Bt3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,sd30n,B2g0H,Bt2g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(y14,y13,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-4-3 antenna.
      call pmap5to4(i2,i4,i3,i5,i1,2,4,3,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(y23,y24,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Bt3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SSLC contribution to
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
      real(8) function Btt3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,Bt2g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-3-2 antenna.
      call pmap5to4(i1,i3,i2,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y13,y23)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-2 antenna.
      call pmap5to4(i1,i4,i2,i3,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y14,y24)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Btt3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> q(i1) g(i5) Qbar(i4) Q(i3) qbar(i2).
      real(8) function C1g0HSNLOa(i1,i5,i4,i3,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,G30n,B2g0H,C0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y14,y15,y45)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-1-2 antenna.
      call pmap5to4(i5,i1,i2,i3,i4,4,3,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(y25,y15,y12)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-4-3 antenna.
      call pmap5to4(i5,i4,i3,i2,i1,3,4,2,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(y35,y45,y34)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      C1g0HSNLOa = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> q(i1) Qbar(i4) Q(i3) g(i5) qbar(i2).
      real(8) function C1g0HSNLOb(i1,i4,i3,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,G30n,B2g0H,C0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y23,y35,y25)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-2-1 antenna.
      call pmap5to4(i5,i2,i1,i3,i4,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(y15,y25,y12)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-3-4 antenna.
      call pmap5to4(i5,i3,i4,i2,i1,4,3,2,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(y45,y35,y34)*B2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      C1g0HSNLOb = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> q(i1) g(i5) qbar(i2) Q(i3) Qbar(i4).
      real(8) function Ct1g0HSNLOa(i1,i5,i2,i3,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,E30n,Bt2g0H,C0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i3,i4,i5,i1,2,3,4,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y24,y23,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y13,y14,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Ct1g0HSNLOa = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> q(i1) qbar(i2) Q(i3) g(i5) Qbar(i4).
      real(8) function Ct1g0HSNLOb(i1,i2,i3,i5,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,E30n,Bt2g0H,C0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y34,y35,y45)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     4-1-2 antenna.
      call pmap5to4(i4,i1,i2,i5,i3,2,3,4,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y24,y14,y12)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-2-1 antenna.
      call pmap5to4(i3,i2,i1,i5,i4,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y13,y23,y12)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Ct1g0HSNLOb = wt

      return
      end

************************************************************************

c     Real subtraction term for colour-mixing SLC contribution to
c     H -> q(i1) qbar(i2) Q(i3) Qbar(i4) g(i5).
      real(8) function Ctt1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,E30n,Bt2g0H,C0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y14,y15,y45)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y34,y35,y45)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y23,y35,y25)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-3 antenna.
      call pmap5to4(i1,i5,i3,i2,i4,1,3,2,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = -A30n(y13,y15,y35)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-5-4 antenna.
      call pmap5to4(i2,i5,i4,i1,i3,2,4,1,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = -A30n(y24,y25,y45)*C0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     4-1-2 antenna.
      call pmap5to4(i4,i1,i2,i5,i3,2,3,4,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y24,y14,y12)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-2-1 antenna.
      call pmap5to4(i3,i2,i1,i5,i4,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y13,y23,y12)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i3,i4,i5,i1,2,3,4,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y24,y23,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(y13,y14,y34)*Bt2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Ctt1g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC interference contribution to
c     H -> q(i1) qbar(i2) q(i3) qbar(i4) g(i5).
      real(8) function D1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,D0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i4,i3,1,2,4,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y14,y15,y45)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y23,y35,y25)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y34,y35,y45)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      D1g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC interference contribution to
c     H -> q(i1) qbar(i2) q(i3) qbar(i4) g(i5).
      real(8) function Dt1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      logical             :: plot
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: ipass
      real(8), target     :: y(5,5)
      real(8), pointer    :: y12,y13,y14,y15,y23,y24,y25,y34,y35,y45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,wtsub,wtdis,var
c     Externals.
      real(8), external   :: A30n,D0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/yij5/y
      common/mapmomenta/p5,p4,p3

c     Invariants.
      y12 => y(i1,i2)
      y13 => y(i1,i3)
      y14 => y(i1,i4)
      y15 => y(i1,i5)
      y23 => y(i2,i3)
      y24 => y(i2,i4)
      y25 => y(i2,i5)
      y34 => y(i3,i4)
      y35 => y(i3,i5)
      y45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y12,y15,y25)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y14,y15,y45)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y23,y35,y25)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(y34,y35,y45)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-5-3 antenna.
      call pmap5to4(i1,i5,i3,i2,i4,1,3,2,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = -A30n(y13,y15,y35)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-5-4 antenna.
      call pmap5to4(i2,i5,i4,i1,i3,2,4,1,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = -A30n(y24,y25,y45)*D0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Dt1g0HSNLO = wt

      return
      end

c-----------------------------------------------------------------------
c     Virtual four-parton subtraction terms.
c-----------------------------------------------------------------------

c     Virtual subtraction term for LC contribution to
c     H -> g(i1) g(i2) g(i3) g(i4).
      real(8) function A4g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: F30int,A4g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = A4g0H(p,i1,i2,i3,i4)
      sub  =
     .     + 1d0/3d0*F30int(s12,renscale2,ipole)
     .     + 1d0/3d0*F30int(s23,renscale2,ipole)
     .     + 1d0/3d0*F30int(s34,renscale2,ipole)
     .     + 1d0/3d0*F30int(s14,renscale2,ipole)
      A4g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for QL contribution to
c     H -> g(i1) g(i2) g(i3) g(i4).
      real(8) function Ah4g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: G30int,A4g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = A4g0H(p,i1,i2,i3,i4)
      sub  =
     .     + 1d0/2d0*G30int(s12,renscale2,ipole)
     .     + 1d0/2d0*G30int(s34,renscale2,ipole)
      Ah4g1HTNLO = 4d0*sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function B2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: D30int,F30int,B2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = B2g0H(p,i1,i3,i4,i2)
      sub  =
     .     + 1d0/2d0*D30int(s13,renscale2,ipole)
     .     + 1d0/3d0*F30int(s34,renscale2,ipole)
     .     + 1d0/2d0*D30int(s24,renscale2,ipole)
      B2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function Bt2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,B2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = B2g0H(p,i1,i3,i4,i2)
      sub  =
     .     + A30int(s12,renscale2,ipole)
      Bt2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SSLC contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function Btt2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,D30int,Bt2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = Bt2g0H(p,i1,i3,i4,i2)
      sub  =
     .     - A30int(s12,renscale2,ipole)
     .     + 1d0/2d0*D30int(s13,renscale2,ipole)
     .     + 1d0/2d0*D30int(s14,renscale2,ipole)
     .     + 1d0/2d0*D30int(s23,renscale2,ipole)
     .     + 1d0/2d0*D30int(s24,renscale2,ipole)
      Btt2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SSSLC contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function Bttt2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,D30int,Bt2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = Bt2g0H(p,i1,i3,i4,i2)
      sub  =
     .     + A30int(s12,renscale2,ipole)
      Bttt2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC QL contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function Bh2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: G30int,B2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = B2g0H(p,i1,i3,i4,i2)
      sub  =
     .     + 2d0*G30int(s34,renscale2,ipole)
      Bh2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC QL contribution to
c     H -> q(i1) g(i3) g(i4) qb(i2).
      real(8) function Btth2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: E30int,Bt2g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = Bt2g0H(p,i1,i3,i4,i2)
      sub  =
     .     + 1d0/2d0*E30int(s13,renscale2,ipole)
     .     + 1d0/2d0*E30int(s14,renscale2,ipole)
     .     + 1d0/2d0*E30int(s23,renscale2,ipole)
     .     + 1d0/2d0*E30int(s24,renscale2,ipole)
      Btth2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC contribution to
c     H -> q(i1) Qbar(i4) Q(i3) qbar(i2).
      real(8) function C0g1HTNLO(i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,C0g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = C0g0H(p,i1,i4,i3,i2)
      sub  =
     .     + A30int(s14,renscale2,ipole)
     .     + A30int(s23,renscale2,ipole)
      C0g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution to
c     H -> q(i1) Qbar(i4) Q(i3) qbar(i2).
      real(8) function Ct0g1HTNLO(i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,C0g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = C0g0H(p,i1,i4,i3,i2)
      sub  =
     .     - A30int(s12,renscale2,ipole)
     .     - A30int(s34,renscale2,ipole)
     .     - 2d0*A30int(s14,renscale2,ipole)
     .     - 2d0*A30int(s23,renscale2,ipole)
     .     + 2d0*A30int(s13,renscale2,ipole)
     .     + 2d0*A30int(s24,renscale2,ipole)
      Ct0g1HTNLO = -sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC interference contribution to
c     H -> q(i1) qbar(i2) Q(i3) qbar(i4).
      real(8) function D0g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,D0g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = D0g0H(p,i1,i4,i3,i2)
      sub  =
     .     + A30int(s13,renscale2,ipole)
     .     + A30int(s24,renscale2,ipole)
      D0g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC interference contribution to
c     H -> q(i1) qbar(i2) Q(i3) qbar(i4).
      real(8) function Dt0g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: renscale2
      real(8)             :: sub,tree
      real(8)             :: p(1:4,5)
      real(8), target     :: y(4,4)
      real(8), pointer    :: s12,s13,s14,s23,s24,s34
c     Externals.
      real(8), external   :: A30int,D0g0H
c     Common blocks.
      common/pmom/p
      common/yij4/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      tree = D0g0H(p,i1,i4,i3,i2)
      sub  =
     .     + A30int(s12,renscale2,ipole)
     .     + A30int(s14,renscale2,ipole)
     .     + A30int(s23,renscale2,ipole)
     .     + A30int(s34,renscale2,ipole)
     .     - A30int(s13,renscale2,ipole)
     .     - A30int(s24,renscale2,ipole)
      Dt0g1HTNLO = -sub*tree

      return
      end

c-----------------------------------------------------------------------
