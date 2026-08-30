c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Tree-level NLO subtraction terms
c     for e+ e- -> 4j and e+ e- -> 5j.

c-----------------------------------------------------------------------
c     Four-parton tree-level subtraction terms.
c-----------------------------------------------------------------------

c     Leading-colour contribution to e+ e- -> q qb g g.
c     (one colour ordering).
      function A40s(i1,i2,i3,i4,wtplot)
      implicit double precision(a-h,o-z)
      common /s3/s12,s13,s23
      common /yij4/y(4,4)
      common /plots/plot
      logical plot 

      wt=0d0
      
c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30(i1,i3,i4)*T(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-4-2 antenna.
      call pmap4to3old(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30(i2,i4,i3)*T(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A40s = wt

      return
      end

************************************************************************

c     Subleading-colour contribution to e+ e- -> q qb g g.
      function A40tildes(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      common/s3/s12,s13,s23
      common/yij4/y(4,4)
      common/plots/plot
      logical plot 

      wt=0d0

c     1-3-2 antenna.
      call pmap4to3old(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30(i1,i3,i2)*T(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-2 antenna.
      call pmap4to3old(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30(i1,i4,i2)*T(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A40tildes = wt

      return
      end

************************************************************************

c     has been Bpoles in old notation
      function B40s(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      common /s3/s12,s13,s23
      common /plots/plot
      logical plot 

      wt=0d0

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30(i1,i3,i4)*T(s12,s13,s23)*var/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-4-2 antenna.
      call pmap4to3old(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30(i2,i3,i4)*T(s12,s13,s23)*var/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B40s = wt

      return
      end

c-----------------------------------------------------------------------
c     Five-parton single-unresolved subtraction terms.
c-----------------------------------------------------------------------

      function A345s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0
      
* non-cyclic permus are included explicitly in tt0 of sig4s
* global factor 4: 2 because 2*A40=A34, 2 because the antenna functions 
* are half of Nigel's antenna functions => factor 4    
* 10.7.06: do NOT add cyclic permutations of (3,4,5) explicitly
* as 5-parton ME also does not contain them 
* 

* there is another factor 1/2, since the subtraction term is 
* the average of the two permutations. In sig4s, one is not allowed 
* to have symmetry factors since all subtraction terms write directly into
* the histograms
      fac=2d0

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*
     .        A40(s12,s13,s14,s23,s24,s34)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-4-5 antenna.
      call pmap5to4(i3,i4,i5,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
        if(ipass.eq.1)then
           wtsub = sf30y5(i3,i4,i5)*
     .          A40(s12,s13,s14,s23,s24,s34)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

c     4-5-2 antenna.
      call pmap5to4(i2,i5,i4,i1,i3,2,4,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i5,i4)*
     .        A40(s12,s13,s14,s23,s24,s34)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	      
      A345s = wt

      return
      end

************************************************************************

      function A345ps(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

* factor 2 from A34=2*A40, factor 2 from Aqgg sim 2*d30,
* factor 1/2 from explicit inclusion of 3<->4 =>overall factor 2

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*2d0*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     2-4-3 antenna.
      call pmap5to4(i2,i4,i3,i1,i5,2,4,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i4,i3)*2d0*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i5,i2,1,3,4,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i4,i3)*2d0*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap5to4(i2,i3,i4,i1,i5,2,4,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i3,i4)*2d0*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-2 antenna.
c     A34=2*A40, Aqgq=2*A30 => multiply with  factor 4*1/2 
c     1/2 from explicit symmetrisation 3<->4 in pmap.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*2d0*
     .        A40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then 
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
      call pmap5to4(i1,i5,i2,i4,i3,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*2d0*
     .        A40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then 
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A345ps = wt

      return
      end

************************************************************************

*     Aslc=2*A40tilde, Aqgq=2*A30 => multiply with overall factor 4.
      function A345qs(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s4/s12,s13,s14,s23,s24,s34
      common /plots/plot
      logical plot 
      wt=0d0
      
c     1-3-2 antenna.
      call pmap5to4(i1,i3,i2,i4,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i3,i2)*
     .        4d0*A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif


c     1-4-2 antenna.
      call pmap5to4(i1,i4,i2,i3,i5,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i4,i2)*
     .        4d0*A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*
     .        4d0*A40tilde(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A345qs = wt

      return
      end

************************************************************************

      function A15432s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s4/s12,s13,s14,s23,s24,s34
      common /plots/plot
      logical plot 
      wt=0d0

c     factors of two below because Bpole=2*B40, A34=2*A40,
c     Aqgq=2*A30, E30(i1,i3,i4) is symmetric in i3,i4, same for G30
c     but Aqqx,Axqq are NOT symmetric
c     G30(1,3,4)=(Axqq(1,3,4)+Aqqx(3,4,1))/2.

c     1-5-4 antenna, (a) in (8.2) of 3jet.tex
      call pmap5to4(i1,i5,i4,i2,i3,1,4,2,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i4)*4d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     5-4-3 antenna (c) in (8.2).
c     (4 unresolved, G30 is symmetric in last 2 arguments)
      call pmap5to4(i5,i4,i3,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = G30y5(i5,i4,i3)*4d0*
     .        A40(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A15432s = wt

      return
      end

************************************************************************

      function A14352s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s4/s12,s13,s14,s23,s24,s34
      common /plots/plot
      logical plot 
      wt=0d0

c     3-5-2 antenna (b) in (8.2).
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i3,i5,i2)*4d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     5-4-3 antenna (d) in (8.2).
      call pmap5to4(i5,i4,i3,i1,i2,4,3,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = G30y5(i5,i3,i4)*4d0*
     .        A40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A14352s = wt

      return
      end

************************************************************************

c     B50cs+B50es has been B15234s.
c     Note that whole expression (9.2)
c     =-1/4*[B50cs+B50ds+B50es+B50cds+B50dds+B50eds].
      function B50cs(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*2d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Exchange 3<->4.
      call pmap5to4(i1,i5,i2,i4,i3,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*2d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B50cs=wt

      return
      end
	
************************************************************************

c     Has been B12354s.
c     2*B40=Bpole,Aqgq=2*A30 => factor 4 times 1/2 from 3<->4 in (9.2).
      function B50ds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s4/s12,s13,s14,s23,s24,s34
      common /plots/plot
      logical plot 
      wt=0d0

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i3,i5,i4)*2d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-5-3 antenna.
      call pmap5to4(i4,i5,i3,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i4,i5,i3)*2d0*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B50ds=wt

      return
      end

************************************************************************

c     B50cs+B50es has been B15234s.
      function B50es(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     2-4-3 antenna.
      call pmap5to4(i2,i4,i3,i1,i5,2,3,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i2,i4,i3)*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i2,i5,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i1,i4,i3)*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Exchange 3<->4.
c     2-3-4 antenna.
      call pmap5to4(i2,i3,i4,i1,i5,2,4,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i2,i3,i4)*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-4 antenna.
      call pmap5to4(i1,i3,i4,i2,i5,1,4,2,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i1,i3,i4)*
     .        A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B50es = wt

      return
      end

************************************************************************

      function B15234s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*
     .        4d0*B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-3-2 antenna.
      call pmap5to4(i4,i3,i2,i1,i5,3,2,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
c     Aslc=2*A40tilde, therefore factor 2.
         wtsub = E30y5(i2,i4,i3)*
     .        2d0*A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i2,i5,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i1,i4,i3)*
     .        2d0*A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B15234s = wt

      return
      end

************************************************************************

      function B12354s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i3,i5,i4)*
     .        4d0*B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      B12354s = wt

      return
      end

************************************************************************

      function AABBs(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s4/s12,s13,s14,s23,s24,s34
      common /plots/plot
      logical plot 
      wt=0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i1,i5,i2)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i3,i5,i4)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i2,i3,1,4,2,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i1,i5,i4)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i3,i5,i2)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-3 antenna - minus sign.
      call pmap5to4(i1,i5,i3,i2,i4,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i3)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-5-2 antenna - minus sign.
      call pmap5to4(i4,i5,i2,i1,i3,4,2,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i4,i5,i2)*
     .        B40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-3-2 antenna.
      call pmap5to4(i4,i3,i2,i1,i5,4,2,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i2,i3,i4)*
     .        2d0*A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap5to4(i1,i4,i3,i2,i5,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = E30y5(i1,i4,i3)*
     .        2d0*A40tilde(s12,s13,s14,s23,s24,s34)*var 
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AABBs = wt

      return
      end

************************************************************************

c     Bfin = -2*C40, Aqgq=2*A30 => multiply with overall factor -4.
      function AAAAs(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-2 antenna.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i2)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i3,i5,i4)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i2,i3,1,4,2,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i4)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i3,i5,i2)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-3 antenna - minus sign.
      call pmap5to4(i1,i5,i3,i2,i4,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i1,i5,i3)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-5-2 antenna - minus sign.
      call pmap5to4(i4,i5,i2,i1,i3,4,2,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i4,i5,i2)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AAAAs = wt

      return
      end

************************************************************************

c     Combination af AAAAs-AB....s for N^0 part.
      function ACs(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-3 antenna.
      call pmap5to4(i1,i5,i3,i2,i4,1,3,2,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 2d0*A30y5(i1,i5,i3)*
     .        (C40(s12,s13,s14,s23,s24,s34)
     .        +C40(s12,s24,s23,s14,s13,s34))*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-5-2 antenna.
      call pmap5to4(i4,i5,i2,i1,i3,4,2,1,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = 2d0*A30y5(i4,i5,i2)*
     .        (C40(s12,s13,s14,s23,s24,s34)
     .        +C40(s12,s24,s23,s14,s13,s34))*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
      ACs = wt

      return
      end

************************************************************************

      function AB12354s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     3-5-4 antenna.
      call pmap5to4(i3,i5,i4,i1,i2,3,4,1,2)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i3,i5,i4)*(-4d0)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AB12354s = wt

      return
      end

************************************************************************

      function AB15234s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-2 antenna.
c     factors: Bfin=-2*C40, Aqgq=2*A30 => factor -4.
      call pmap5to4(i1,i5,i2,i3,i4,1,2,3,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i2)*(-4d0)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AB15234s = wt

      return
      end

************************************************************************

      function AB15432s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     1-5-4 antenna.
      call pmap5to4(i1,i5,i4,i2,i3,1,4,2,3)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i1,i5,i4)*(-4d0)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AB15432s = wt

      return
      end

************************************************************************

      function AB14352s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s4/s12,s13,s14,s23,s24,s34
      common/plots/plot
      logical plot 
      wt=0d0

c     3-5-2 antenna.
      call pmap5to4(i3,i5,i2,i1,i4,3,2,1,4)
      call ecuts(4,var,ipass)
      if(ipass.eq.1)then
         wtsub = A30y5(i3,i5,i2)*(-4d0)*
     .        C40(s12,s13,s14,s23,s24,s34)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AB14352s = wt

      return
      end

c-----------------------------------------------------------------------
