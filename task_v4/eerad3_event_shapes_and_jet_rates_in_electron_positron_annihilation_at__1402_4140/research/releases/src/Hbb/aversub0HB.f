c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     NLO subtraction terms for H -> 4j and H -> 5j (b-quark channel).

c-----------------------------------------------------------------------
c     Real four-parton subtraction terms.
c-----------------------------------------------------------------------

c     Real subtraction term for LC contribution to
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function By2g0HSNLO(i1,i3,i4,i2,wtplot)
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
      real(8), external   :: sd30n,By1g0H
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

c     1-3-4 antenna.
      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s14,s13,s34)*By1g0H(p3,1,3,2)*var
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
         wtsub = sd30n(s23,s24,s34)*By1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      By2g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Bty2g0HSNLO(i1,i3,i4,i2,wtplot)
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
      real(8), external   :: A30n,By1g0H
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

c     1-3-2 antenna
      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s13,s23)*By1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-2 antenna
      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s14,s24)*By1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Bty2g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for
c     H -> b(i1) qbar(i4) q(i3) bbar(i2).
      real(8) function Cy0g0HSNLO(i1,i4,i3,i2,wtplot)
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
      real(8), external   :: E30n,By1g0H
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

c     1-4-3 antenna.
      call pmap4to3(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s13,s14,s34)*By1g0H(p3,1,3,2)*var
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
         wtsub = 1d0/2d0*E30n(s24,s23,s34)*By1g0H(p3,1,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Cy0g0HSNLO = wt

      return
      end

c-----------------------------------------------------------------------
c     Virtual three-parton subtraction terms.
c-----------------------------------------------------------------------

c     Leading-colour contribution to H -> b bbar g.
      real(8) function By1g1HTNLO(i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Variables.
      real(8)             :: p(1:4,5)
      real(8), target     :: y(3,3)
      real(8), pointer    :: s12,s13,s23
      real(8)             :: sub,tree
      real(8), external   :: D30int,By1g0H
c     Common blocks.
      common/pmom/p
      common/yij3/y

c     Invariants.
      s13 => y(i1,i3)
      s23 => y(i2,i3)

c     Result.
      sub  =
     .     + 1d0/2d0*D30int(s13,renscale2,ipole)
     .     + 1d0/2d0*D30int(s23,renscale2,ipole)
      tree = By1g0H(p,i1,i3,i2)
      By1g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> b bbar g.
      real(8) function Bty1g1HTNLO(i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Variables.
      real(8)             :: p(1:4,5)
      real(8), target     :: y(3,3)
      real(8), pointer    :: s12,s13,s23
      real(8)             :: sub,tree
      real(8), external   :: A30int,By1g0H
c     Common blocks.
      common/pmom/p
      common/yij3/y

c     Invariants.
      s12 => y(i1,i2)

c     Result.
      sub  = A30int(s12,renscale2,ipole)
      tree = By1g0H(p,i1,i3,i2)
      Bty1g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Quark-loop contribution to H -> b bbar g.
      real(8) function Bhy1g1HTNLO(i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Variables.
      real(8)             :: p(1:4,5)
      real(8), target     :: y(3,3)
      real(8), pointer    :: s12,s13,s23
      real(8)             :: sub,tree
      real(8), external   :: E30int,By1g0H
c     Common blocks.
      common/pmom/p
      common/yij3/y

c     Invariants.
      s13 => y(i1,i3)
      s23 => y(i2,i3)

c     Result.
      sub  =
     .     + 1d0/2d0*E30Int(s13,renscale2,ipole)
     .     + 1d0/2d0*E30Int(s23,renscale2,ipole)
      tree = By1g0H(p,i1,i3,i2)
      Bhy1g1HTNLO = sub*tree

      return
      end

c-----------------------------------------------------------------------
c     Real five-parton subtraction terms.
c-----------------------------------------------------------------------

c     Real subtraction term for LC contribution to
c     H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      real(8) function By3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: as,ca,cflo,cf,tr,cn
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: sd30n,sf30n
      real(8), external   :: By2g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s14,s13,s34)*By2g0H(p4,1,3,4,2)*var
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
         wtsub = sf30n(s35,s34,s45)*By2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-5-4 antenna.
      call pmap5to4(i2,i5,i4,i3,i1,2,4,3,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s24,s25,s45)*By2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      By3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      real(8) function Bty3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n,sd30n
      real(8), external   :: By2g0H,Bty2g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-3-2 antenna.
      call pmap5to4(i1,i3,i2,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s13,s23)*By2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     1-4-5 antenna.
      call pmap5to4(i1,i4,i5,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s15,s14,s45)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-5-4 antenna.
      call pmap5to4(i2,i5,i4,i3,i1,2,4,3,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = sd30n(s24,s25,s45)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Bty3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for SSLC contribution to
c     H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      real(8) function Btty3g0HSNLO(i1,i3,i4,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n
      real(8), external   :: Bty2g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-3-2 antenna.
      call pmap5to4(i1,i3,i2,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s13,s23)*Bty2g0H(p4,1,3,4,2)*var
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
         wtsub = A30n(s12,s14,s24)*Bty2g0H(p4,1,3,4,2)*var
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
         wtsub = A30n(s12,s15,s25)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Btty3g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> b(i1) g(i5) qbar(i4) q(i3) bbar(i2).
      real(8) function Cy1g0HSNLOa(i1,i5,i4,i3,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n,G30n
      real(8), external   :: By2g0H,Cy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i3,i2,1,4,3,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s14,s15,s45)*Cy0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-4-3 antenna.
      call pmap5to4(i5,i4,i3,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(s35,s45,s34)*By2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Cy1g0HSNLOa = wt

      return
      end

************************************************************************

c     Real subtraction term for LC contribution to
c     H -> b(i1) qbar(i4) q(i3) g(5) bbar(i2)
      real(8) function Cy1g0HSNLOb(i1,i4,i3,i5,i2,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n,G30n
      real(8), external   :: By2g0H,Cy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s23,s35,s25)*Cy0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     5-4-3 antenna.
      call pmap5to4(i5,i4,i3,i2,i1,4,3,2,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = G30n(s35,s45,s34)*By2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Cy1g0HSNLOb = wt

      return
      end

************************************************************************

c     Real subtraction term for SLC contribution to
c     H -> b(i1) g(i5) bbar(i2) q(i3) qbar(i4).
      real(8) function Cty1g0HSNLO(i1,i5,i2,i3,i4,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n,E30n
      real(8), external   :: Bty2g0H,Cy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s15,s25)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s34,s35,s45)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = 1d0/2d0*E30n(s13,s14,s34)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i4,i3,i5,i1,2,4,3,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s24,s23,s34)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Cty1g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for colour-mixing SLC contribution to
c     H -> b(i1) bbar(i2) q(i3) qbar(i4) g(i5).
      real(8) function Ctty1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,wtdis,wtsub,var
c     Externals.
      real(8), external   :: A30n,E30n
      real(8), external   :: Bty2g0H,Cy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s15,s25)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = -A30n(s14,s15,s45)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = -A30n(s23,s35,s25)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s34,s35,s45)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s13,s15,s35)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s24,s25,s45)*Cy0g0H(p4,1,4,3,2)*var
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
         wtsub = 1d0/2d0*E30n(s13,s14,s34)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i4,i3,i5,i1,2,4,3,1)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = 1d0/2d0*E30n(s24,s23,s34)*Bty2g0H(p4,1,3,4,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Ctty1g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC interference contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4) g(i5).
      real(8) function Dy1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
c     Variables.
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n
      real(8), external   :: Dy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i4,i3,1,2,4,3)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s15,s25)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s14,s15,s45)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s23,s35,s25)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s34,s35,s45)*Dy0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Dy1g0HSNLO = wt

      return
      end

************************************************************************

c     Real subtraction term for LC interference contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4) g(i5).
      real(8) function Dty1g0HSNLO(i1,i2,i3,i4,i5,wtplot)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: wtplot
      real(8), parameter  :: pi=3.141592653589793238d0
      logical             :: plot
      integer             :: ipass
      integer             :: iaver,imom,idist,iang,idebug
      real(8), target     :: y(5,5)
      real(8), pointer    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
      real(8)             :: wt,var,wtdis,wtsub
c     Externals.
      real(8), external   :: A30n
      real(8), external   :: Dy0g0H
c     Common blocks.
      common/plots/plot
      common/intech/iaver,imom,idist,iang,idebug
      common/mapmomenta/p5,p4,p3
      common/yij5/y

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s15 => y(i1,i5)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s25 => y(i2,i5)
      s34 => y(i3,i4)
      s35 => y(i3,i5)
      s45 => y(i4,i5)

c     Initialise.
      wt  = 0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if (ipass.eq.1)then
         wtsub = A30n(s12,s15,s25)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s14,s15,s45)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s23,s35,s25)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = A30n(s34,s35,s45)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = -A30n(s13,s15,s35)*Dy0g0H(p4,1,4,3,2)*var
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
         wtsub = -A30n(s24,s25,s45)*Dy0g0H(p4,1,4,3,2)*var
         if (plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt = wt+wtsub
      endif

      Dty1g0HSNLO = wt

      return
      end

c-----------------------------------------------------------------------
c     Virtual four-parton subtraction terms.
c-----------------------------------------------------------------------

c     Virtual subtraction term for LC contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function By2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: D30int,F30int,By2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s13 => y(i1,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      sub  =
     .     + 1d0/2d0*D30int(s13,renscale2,ipole)
     .     + 1d0/3d0*F30int(s34,renscale2,ipole)
     .     + 1d0/2d0*D30int(s24,renscale2,ipole)
      tree = By2g0H(p,i1,i3,i4,i2)
      By2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Bty2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,By2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s12 => y(i1,i2)

c     Subtraction term.
      sub  = A30int(s12,renscale2,ipole)
      tree = By2g0H(p,i1,i3,i4,i2)
      Bty2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC QL contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Bhy2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: G30int,By2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s34 => y(i3,i4)

c     Subtraction term.
      sub  = 2d0*G30int(s34,renscale2,ipole)
      tree = By2g0H(p,i1,i3,i4,i2)
      Bhy2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Btty2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,D30int,Bty2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)

c     Subtraction term.
      sub  =
     .     - A30int(s12,renscale2,ipole)
     .     + 1d0/2d0*D30int(s13,renscale2,ipole)
     .     + 1d0/2d0*D30int(s14,renscale2,ipole)
     .     + 1d0/2d0*D30int(s23,renscale2,ipole)
     .     + 1d0/2d0*D30int(s24,renscale2,ipole)
      tree = Bty2g0H(p,i1,i3,i4,i2)
      Btty2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SSSLC contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Bttty2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,Bty2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s12 => y(i1,i2)

c     Subtraction term.
      sub  = A30int(s12,renscale2,ipole)
      tree = Bty2g0H(p,i1,i3,i4,i2)
      Bttty2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC QL contribution of
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Btthy2g1HTNLO(i1,i3,i4,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: E30int,Bty2g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s13 => y(i1,i3)
      s23 => y(i2,i3)
      s24 => y(i2,i4)

c     Subtraction term.
      sub  = 2d0*(
     .     + 1d0/2d0*E30int(s13,renscale2,ipole)
     .     + 1d0/2d0*E30int(s24,renscale2,ipole)
     .     )
      tree = Bty2g0H(p,i1,i3,i4,i2)
      Btthy2g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC contribution to
c     H -> b(i1) bbar(i2) q(i3) qbar(i4).
      real(8) function Cy0g1HTNLO(i1,i4,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,Cy0g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s14 => y(i1,i4)
      s23 => y(i2,i3)

c     Subtraction term.
      sub  =
     .     + A30int(s14,renscale2,ipole)
     .     + A30int(s23,renscale2,ipole)
      tree = Cy0g0H(p,i1,i4,i3,i2)
      Cy0g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution to
c     H -> b(i1) bbar(i2) q(i3) qbar(i4).
      real(8) function Cty0g1HTNLO(i1,i4,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,Cy0g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      sub  =
     .     - A30int(s12,renscale2,ipole)
     .     - A30int(s34,renscale2,ipole)
     .     - 2d0*A30int(s14,renscale2,ipole)
     .     - 2d0*A30int(s23,renscale2,ipole)
     .     + 2d0*A30int(s13,renscale2,ipole)
     .     + 2d0*A30int(s24,renscale2,ipole)
      tree = Cy0g0H(p,i1,i4,i3,i2)
      Cty0g1HTNLO = -sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for LC contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4).
      real(8) function Dy0g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,Dy0g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s13 => y(i1,i3)
      s24 => y(i2,i4)

c     Subtraction term.
      sub  =
     .     + A30int(s13,renscale2,ipole)
     .     + A30int(s24,renscale2,ipole)
      tree = Dy0g0H(p,i1,i4,i3,i2)
      Dy0g1HTNLO = sub*tree

      return
      end

************************************************************************

c     Virtual subtraction term for SLC contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4).
      real(8) function Dty0g1HTNLO(i1,i2,i3,i4,renscale2,ipole)
      implicit none
      real(8), intent(in)    :: renscale2
      integer, intent(in)    :: i1,i2,i3,i4,ipole
c     Variables.
      real(8)                :: sub,tree
      real(8), pointer       :: s12,s13,s14,s23,s24,s34
      real(8), target        :: y(4,4)
      real(8)                :: p(1:4,5)
c     Externals.
      real(8), external      :: A30int,Dy0g0H
c     Common blocks.
      common/yij4/y
      common/pmom/p

c     Invariants.
      s12 => y(i1,i2)
      s13 => y(i1,i3)
      s14 => y(i1,i4)
      s23 => y(i2,i3)
      s24 => y(i2,i4)
      s34 => y(i3,i4)

c     Subtraction term.
      sub  =
     .     + A30int(s12,renscale2,ipole)
     .     + A30int(s14,renscale2,ipole)
     .     + A30int(s23,renscale2,ipole)
     .     + A30int(s34,renscale2,ipole)
     .     - A30int(s13,renscale2,ipole)
     .     - A30int(s24,renscale2,ipole)
      tree = Dy0g0H(p,i1,i4,i3,i2)
      Dty0g1HTNLO = -sub*tree

      return
      end

c-----------------------------------------------------------------------
