c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Tree-level double-unresolved subtraction terms for e+ e- -> 5j.
c     Equation numbers refer to arXiv:0710.0346.

c-----------------------------------------------------------------------
c     Five-parton double-unresolved subtraction terms.
c-----------------------------------------------------------------------

      function A345dsA40t(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt = 0d0

c     (o,p,q), analogous to 1/N^2 (A345qds) with j->k
c     Note:
c     A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0 
c     sum only over permutations 345 and 543 as this is the way
c     the 5-parton ME is included.
c     Overall factor 4 relative to (5.3) as usual to cancel with 
c     1/4 in overall cflo*(as/2d0/pi)**3/4d0 in sig3ds.
      fac = 1d0

c     (o): (i,k)=(3,5)
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -Aqppq(i1,i3,i5,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (o): (i,k)=(5,3)
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -Aqppq(i1,i5,i3,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (p): (i,k)=(3,5)
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (q): (p) with 3<->5 
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = 4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A345dsA40t = wt

      return
      end

************************************************************************

      function A345dsD40(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/s4/r12,r13,r14,r23,r24,r34
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt  = 0d0
c     Factor 4 overall factor, NOT divided by 3! as in (5.3),
c     because cyclic permus are not included in ME nor below.
c     Note that sig3ds contains 1/4*1/6*6 in N^2 part.
      fac = 4d0

c     Invariants.
      y12 = y(i1,i2)
      y13 = y(i1,i3)
      y14 = y(i1,i4)
      y15 = y(i1,i5)
      y23 = y(i2,i3)
      y24 = y(i2,i4)
      y25 = y(i2,i5)
      y34 = y(i3,i4)
      y35 = y(i3,i5)
      y45 = y(i4,i5)

c     (g): (i,j,k)=(3,4,5)
      D40 = D40i(i1,i3,i4,i5)
      Da  = D40a(y13,y14,y15,y34,y35,y45)
      Db  = D40a(y15,y14,y13,y45,y35,y34)
      Dc  = D40c(y13,y14,y15,y34,y35,y45)
      Dd  = D40c(y15,y14,y13,y45,y35,y34)
      Dleft = D40 -(Da+Db+Dc+Dd)
      Da  = Da + Dleft/2d0
      Db  = Db + Dleft/2d0

c     Mapping A: (1345)
      call pmap5to3(i1,i3,i4,i5,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Da*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping B: (1543).
      call pmap5to3(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Db*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping C: (1354).
      call pmap5to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Dc*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping D: (1354).
      call pmap5to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Dd*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (h): (i,j,k)=(3,4,5).
c     Split into:
c     (1) (i3i4tilde) unresolved in second step,
c     (2) i5 unresolved in second step,
      call pmap5to4to3C(i1,i3,i4,i5,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i3,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
      call pmap5to4to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i3,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (i): (i,j,k)=(3,4,5)
c     Split into
c     (1) (i4i5tilde) unresolved in second step
c     (2) (i3i4tilde) unresolved in second step
      call pmap5to4to3C(i3,i4,i5,i1,i2,3,1,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sf30y5(i3,i4,i5)*
     .        sd30y5map(w12,w23,w13)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      call pmap5to4to3D(i3,i4,i5,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sf30y5(i3,i4,i5)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (j): (h) with 3<->5.
      call pmap5to4to3C(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i5,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      call pmap5to4to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i5,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     For (k,l,m,n): interchange 1<->2 in (g,h,i,j).

c     (k): (i,j,k)=(3,4,5).
      D40 = D40i(i2,i3,i4,i5)
      Da  = D40a(y23,y24,y25,y34,y35,y45)
      Db  = D40a(y25,y24,y23,y45,y35,y34)
      Dc  = D40c(y23,y24,y25,y34,y35,y45)
      Dd  = D40c(y25,y24,y23,y45,y35,y34)
      Dleft = D40 -(Da+Db+Dc+Dd)
      Da  = Da + Dleft/2d0
      Db  = Db + Dleft/2d0

c     Mapping A: (2345).
      call pmap5to3(i2,i3,i4,i5,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Da*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping B: (2543).
      call pmap5to3(i2,i5,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Db*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping C: (2354).
      call pmap5to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Dc*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Mapping D: (2534).
      call pmap5to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Dd*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (l): (i,j,k)=(3,4,5).
      call pmap5to4to3C(i2,i3,i4,i5,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i3,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
      call pmap5to4to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i3,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (m): (i,j,k)=(3,4,5).
      call pmap5to4to3C(i3,i4,i5,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sf30y5(i3,i4,i5)*
     .        sd30y5map(w12,w23,w13)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      call pmap5to4to3D(i3,i4,i5,i2,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sf30y5(i3,i4,i5)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (n): (l) with 3<->5.
      call pmap5to4to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i5,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
      call pmap5to4to3C(i2,i5,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i5,i4)*
     .        sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif


c     (r): (i,j,k)=(3,4,5).
      call pmap5to4to3K(i1,i3,i4,i5,i2,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i3,i4)*sd30y5map(w12,w23,w13)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (s): (r) with 1<->2 and 3<->5.
      call pmap5to4to3K(i2,i5,i4,i3,i1,3,1,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i5,i4)*sd30y5map(w12,w23,w13)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (t): (s) with 1<->2.
      call pmap5to4to3K(i1,i5,i4,i3,i2,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i5,i4)*sd30y5map(w12,w23,w13)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

*     (u): (r) with 1<->2.
      call pmap5to4to3K(i2,i3,i4,i5,i1,3,1,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i3,i4)*sd30y5map(w12,w23,w13)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (v).
      call pmap5to4to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (w): (v) with 3<->5.
      call pmap5to4to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i5,i4)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (x): (v) with 1<->2.
      call pmap5to4to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i3,i4)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (y): (x) with 3<->5.
      call pmap5to4to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i5,i4)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (aa).
      call pmap5to4to3K(i2,i3,i1,i5,i4,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i3,i2)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (ab):
      call pmap5to4to3K(i4,i5,i1,i3,i2,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i5,i4)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (ac): (aa) with 3<->5.
      call pmap5to4to3K(i2,i5,i1,i3,i4,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i5,i2)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (ad): (ab) with 3<->5.
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
			
c     (ae): (aa) with 1<->2.
      call pmap5to4to3K(i1,i3,i2,i5,i4,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i2,i3,i1)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (af): (ab) with 1<->2.
      call pmap5to4to3K(i4,i5,i2,i3,i1,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i5,i4)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (ag): (ac) with 1<->2.
      call pmap5to4to3K(i1,i5,i2,i3,i4,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i2,i5,i1)*sd30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (ah): (ad) with 1<->2.
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i3,i4)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (ai): 1-5-3-2 antenna.
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i5,i2)*
     .        A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft = -( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (aj): (ai) with 5<->3.
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i3,i2)*
     .        A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac/2d0
         wtsoft = -( (sant(21,2,22)-sant(11,2,13))
     .        -(sant(23,2,22)-sant(23,2,13))
     .        -(sant(21,2,23)-sant(11,2,23)))
     .        *A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac/2d0
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A345dsD40 = wt

      return
      end

*********************************************************************

c     21.7.06  for N^0:
      function AN0a(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt = 0d0

c     Factor 4 cancels 1/4 from overall cflo*(as/2d0/pi)**3/4d0
c     in sig3ds, other factors as well as sum over (3,4) 
c     are included in sig111.f already.
      fac = 4d0

c     1-3-4-2 antenna.
c     (g):
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = A40i(i1,i3,i4,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     (h): 
      call pmap5to4to3C(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i1,i3,i4)*
     c        A30y5map(w12,w13,w23)*
     c        A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	
c     (i): exchange 1 <-> 2.
      call pmap5to4to3C(i2,i4,i3,i1,i5,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -sd30y5(i2,i4,i3)*
     .        A30y5map(w12,w23,w13)*
     .        A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AN0a = wt

      return
      end

************************************************************************

      function AN0b(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt = 0d0

c     Note:
c     A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0 
c     overall factor 4 relative to (6.2) as usual.
c     Factor -1/3 is already included in sig111.f.
      fac = 1d0

c     1-3-5-2 antenna.
c     Term (j) in (6.2):
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i3,i5,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Account for fact that i<->j needs to be added to construct A40tilde 
c     from Aqppq.

c     1-5-3-2 antenna.
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i5,i3,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-5-2 antenna.
c     Term (k) in (6.2):
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-3-2 antenna.
c     Term (l).
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AN0b = wt

      return
      end

************************************************************************

      function AN0c(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/checkplot/ic
      common/plots/plot
      logical plot 
      
      wt=0d0
c     Overall factor 1/2 and sum over 3<->4 are included in sig111.f.
      fac=1d0
      if (ic.eq.1) write(6,*) i1,i2,i3,i4,i5

c     Term (q) in (6.2).
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*A30y5map(w12,w13,w23)*
     .        A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Term (r): (q) with 1<->2.
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = sd30y5(i2,i3,i4)*A30y5map(w12,w23,w13)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     Term (s):
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i3,i2)*
     .        A30y5map(w12,w13,w23)*
     .        A30y5map(x12,x13,x23)*var*fac
         wtsoft = (-(sant(21,2,22)-sant(11,2,13))
     .        +(sant(21,2,23)-sant(11,2,23))
     .        +(sant(22,2,23)-sant(13,2,23)))
     .        *A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if (ic.eq.1) write(6,*) 's',wtsub,wtsoft,wtsub+wtsoft
         wtsub = wtsub + wtsoft
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AN0c = wt

      return
      end

************************************************************************

c     A34Qds is like A345qds of 1/N^2, but no sum over
c     (345) permutations.
      function A34Qds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt = 0d0

c     Factor 1/6 is included in signew.f already.
c     Note:
c     A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0
c     such that overall factor 4 relative to (6.2) is included
c     implicitly.
c     Factor 4 relative to (6.2) is "removed" in sig3ds by overall
c     factor cflo*(as/2d0/pi)**3/4d0.
      fac = 1d0

c     1-3-4-2 antenna.
c     Term (m) in (6.2).
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i3,i4,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3-2 antenna.
c     Term (m) in (6.2).
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i4,i3,i2)*
     .        A30y5map(s12,s13,s23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-4-2 antenna.
c     Term (n) in (6.2).
      call pmap5to4to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i3,i2)*
     .        A30y5map(w12,w13,w23)*
     .        A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3-2 antenna.
c     Term (o) in (6.2).
      call pmap5to4to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var*fac
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A34Qds = wt

      return
      end

************************************************************************

c     Subtraction term for 1/N^2 contribution.
      function A345qds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt=0d0

c     1-3-4-2 antenna.
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i3,i4,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3-2 antenna.
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i4,i3,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-5-2 antenna.
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i3,i5,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-3-2 antenna.
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i5,i3,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-5-2 antenna.
      call pmap5to3(i1,i4,i5,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i4,i5,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-4-2 antenna.
      call pmap5to3(i1,i5,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = Aqppq(i1,i5,i4,i2)*
     .        A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-4-2 antenna.
c     Aqgq=2*A30 => multiply with additional factor 2.
      call pmap5to4to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i3,i2)*
     .        A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3-2 antenna.
      call pmap5to4to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-5-2 antenna.
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-3-2 antenna.
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-5-2 antenna.
      call pmap5to4to3(i1,i4,i5,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-5-4-2 antenna.
      call pmap5to4to3(i1,i5,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      A345qds = wt

      return
      end

************************************************************************

c     Bfin = -2*C40*s1234, Aqgq=2*A30.
      function AAAAds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/plots/plot
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y15=y(i1,i5)
      y25=y(i2,i5)
      y35=y(i3,i5)
      y45=y(i4,i5)

      wt=0d0

c     2-3-4 triple collinear.
      call pmap5to3(i1,i2,i3,i4,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -4d0*C40i(i1,i3,i4,i2)
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      AAAAds = wt

      return
      end

************************************************************************

c     Corresponds to 4*(a40tilde(1342)+a40tilde(2431)) in (5.28)
c     see Aqppq.m.
c     (9.69)
      function Aqppq(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)

      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y1234=y12+y13+y14+y23+y24+y34
      y12=y12/y1234
      y13=y13/y1234
      y14=y14/y1234
      y23=y23/y1234
      y24=y24/y1234
      y34=y34/y1234
      y134=y13+y14+y34
      y234=y23+y24+y34

      wt = -2/y13 + (2*y12)/(y13*(y13 + y14)) - 2/y24 +
     .     (y12*(2*y12 + y14))/(y13*(y13 + y23)*y24) +
     .     (3*(2*y12 + y14 + y23))/(y13*y24) +
     .     (y12*(2*y12 + y24))/(y13*(y13 + y14)*(y13 + y23)) +
     .     (y12*(2*y12 + y23))/(y13*(y13 + y14)*(y14 + y24)) +
     .     (2*y12**3)/(y13*(y13 + y14)*(y13 + y23)*(y14 + y24)) +
     .     (y12*(2*y12 + y23))/(y13*y24*(y14 + y24)) +
     .     (2*y12**3)/(y13*(y13 + y23)*y24*(y14 + y24)) +
     .     (2*y12)/(y24*(y23 + y24)) +
     .     (y12*(2*y12 + y14))/((y13 + y23)*y24*(y23 + y24)) +
     .     (y12*(2*y12 + y13))/(y24*(y14 + y24)*(y23 + y24)) +
     .     (2*y12**3)/((y13 + y23)*y24*(y14 + y24)*(y23 + y24)) +
     .     (y12 + y23 + y24)/(y13 + y14 + y34)**2 +
     .     ((y12 + y23 + y24)*y34)/(y13*(y13 + y14 + y34)**2) +
     .     1/(y13 + y14 + y34) - (y23 + y24 - 2*y34)/
     .     (y13*(y13 + y14 + y34)) +
     .     (y12*(2*y12 + y23 + y34))/(y24*(y14 + y24)*
     .     (y13 + y14 + y34)) +
     .     (y12*(2*y12 + y24 + y34))/(y13*(y13 + y23)*
     .     (y13 + y14 + y34)) +
     .     (y12 + y13 + y14)/(y23 + y24 + y34)**2 +
     .     ((y12 + y13 + y14)*y34)/(y24*(y23 + y24 + y34)**2) +
     .     1/(y23 + y24 + y34) - (y13 + y14 - 2*y34)/
     .     (y24*(y23 + y24 + y34)) +
     .     (y12*(2*y12 + y13 + y34))/(y24*(y14 + y24)*
     .     (y23 + y24 + y34)) +
     .     (y12*(2*y12 + y14 + y34))/(y13*(y13 + y23)*
     .     (y23 + y24 + y34)) +
     .     (2*y12**3)/(y13*(y13 + y23)*
     .     (y13 + y14 + y34)*(y23 + y24 + y34)) +
     .     (2*y12**3)/(y24*(y14 + y24)*
     .     (y13 + y14 + y34)*(y23 + y24 + y34)) +
     .     (2*(y12 - y34))/((y13 + y14 + y34)*(y23 + y24 + y34)) +
     .     ((3*y12 - y13 - 2*y34)*y34)/
     .     (y24*(y13 + y14 + y34)*(y23 + y24 + y34)) +
     .     ((3*y12 - y24 - 2*y34)*y34)/
     .     (y13*(y13 + y14 + y34)*(y23 + y24 + y34)) +
     .     (-2*y12 + y13 - 2*y23 + 2*y34)/(y24*(y13 + y14 + y34)) +
     .     (-2*y12 - 2*y14 + y24 + 2*y34)/(y13*(y23 + y24 + y34)) +
     .     (4*y12**2 + y14**2 + 3*y12*(y14 - y34) - y14*y34 + y34**2)/
     .     (y13*y24*(y23 + y24 + y34)) +
     .     (4*y12**2 + y23**2 + 3*y12*(y23 - y34) - y23*y34 + y34**2)/
     .     (y13*y24*(y13 + y14 + y34)) +
     .     (2*y12**3 - 4*y12**2*y34 + 3*y12*y34**2 - y34**3)/
     .     (y13*y24*(y13 + y14 + y34)*(y23 + y24 + y34))

      Aqppq= 4d0*wt/y1234**2

      return
      end
      
************************************************************************

c     B50,a,b,ds for NF*N part of sig3ds.
      function B50ads(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/s4/z12,z13,z14,z23,z24,z34
      common/plots/plot
      logical plot 

      wt=0d0

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y15=y(i1,i5)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y25=y(i2,i5)
      y34=y(i3,i4)
      y35=y(i3,i5)
      y45=y(i4,i5)

      rinvmin = dmin1(y15,y25,y35,y45)
      qinvmin3 = dmin1(y13,y23,y35)
      qinvmin4 = dmin1(y14,y24,y45)

c     Relative factor 4 (program=4*(8.2)) has to be included.

c     1-3-4-5.
c     Distinguish 3-4 and 4-5 unresolved in pmap5to3 for E40.
c     Type A is proportional to 1/s15 or 1/s45, but NOT 1/s134
c     in pmap5to3(1,2,3,4,5) 2 and 3 are unresolved, 1,4 are radiators.

C     Term (e) in (8.2), part I.
      EG = E40G(i1,i3,i4,i5)
      EA = E40i(i1,i3,i4,i5) - EG
      call pmap5to3(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = EA
     .        *A30y5map(s12,s13,s23)*var*4d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif 

c     Subtraction term for (fake) singularities of E40 antenna.
c     5 unresolved, 1,4 radiators.
c     Term (f) in (8.2).
      call pmap5to4to3C(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i1,i5,i4)*E30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var*4d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif 
	
c     Now type G ~1/s34.
c     Term (e) in (8.2), part II.
      call pmap5to3(i5,i3,i4,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = EG
     .        *A30y5map(s12,s13,s23)*var*4d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif  

c     Term (g) in (8.2), part of split D30 where.
c     3||4 (3,5 rad), then 45tilde unres, 1 and 34tilde radiator.
      call pmap5to4to3D(i5,i4,i3,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -G30y5(i5,i4,i3)*sd30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var*4d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif
	      
c     Term (g) in (8.2), part of split D30 where
c     3||4 (3,5 rad), then  34tilde unres, 1 and 45tilde radiator.
      call pmap5to4to3C(i5,i4,i3,i1,i2,3,1,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -G30y5(i5,i4,i3)
     .        *sd30y5map(w12,w23,w13)  
     .        *A30y5map(x12,x13,x23)*var*4d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

      B50ads = wt

      return
      end

************************************************************************

c     B50bds: exchange 1<->2 and 3<->4 with respect to B50ads
c     => B50bds is not needed.
c     B50,c/d/e,ds for NF/N part of sig3ds.
      function B50cds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt=0d0

      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y15=y(i1,i5)
      y25=y(i2,i5)
      y35=y(i3,i5)
      y45=y(i4,i5)
      
c     (9.2) * (-4) as for sig4s case (see B50c,d,s in aversubnew.f )
c     B40i is symmetric under 1<->2 and 3<->4.

c     1-3-4.
c     Term (d) in (9.2).
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = B40i(i1,i3,i4,i2)*2d0
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     Subtraction term for (fake) singularities of B40i antenna.
c     Term (e) in 9.2.
      call pmap5to4to3C(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i1,i3,i4)*A30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     1<->2 , 3<->4.
      call pmap5to4to3C(i2,i4,i3,i1,i5,1,2,3)
      ss34=y34
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i2,i3,i4)*A30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif 
	
c     Exchange 3 <-> 4 explicitly.

c     1-4-3.
c     Term (d) in (9.2).
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = B40i(i1,i4,i3,i2)
     .        *A30y5map(s12,s13,s23)*var*2d0
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif  

c     Subtraction term for (fake) singularities of B40i antenna.
c     Term (e) in 9.2.
      call pmap5to4to3C(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i1,i4,i3)*A30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     1<->2.
      call pmap5to4to3C(i2,i3,i4,i1,i5,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i2,i4,i3)*A30y5map(w12,w13,w23)  
     .        *A30y5map(x12,x13,x23)*var
         trys4=-E30y5(i2,i4,i3)*A30y5map(w12,w13,w23)
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif 

 111  continue

      B50cds = wt

      return
      end

************************************************************************

      function B50dds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/u12,u13,u23
      common/sb3/w12,w13,w23
      common/sc3/x12,x13,x23
      common/plots/plot
      logical plot 

      wt=0d0

c     1-3-5.
c     Term (f) in (9.2).
      call pmap5to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E40tildi(i1,i3,i4,i5)
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wto=wtsub
      endif 

c     Subtraction term for (fake) singularities of E40til antenna.
c     Term (g) in (9.2).
      call pmap5to4to3D(i3,i5,i4,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i3,i5,i4)*E30y5map(w13,w12,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wts=wtsub
      endif  

c     1<->2.
c     Term (f) in (9.2).
      call pmap5to3(i2,i3,i5,i4,i1,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E40tildi(i2,i3,i4,i5)
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wto=wto+wtsub
      endif   

c     Subtraction term for (fake) singularities of E40til antenna.
c     Term (g) in (9.2).
      call pmap5to4to3D(i3,i5,i4,i2,i1,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i3,i5,i4)*E30y5map(w13,w12,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wts=wts+wtsub
      endif   

c     Exchange 3<->4  included explicitly.
      call pmap5to3(i1,i4,i5,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E40tildi(i1,i4,i3,i5)
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wto=wto+wtsub
      endif 

c     Subtraction term for (fake) singularities of E40til antenna.
      call pmap5to4to3D(i4,i5,i3,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i4,i5,i3)*E30y5map(w13,w12,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wts=wts+wtsub
      endif  

c     1<->2.
      call pmap5to3(i2,i4,i5,i3,i1,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = E40tildi(i2,i4,i3,i5)
     .        *A30y5map(s12,s13,s23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         wto=wto+wtsub
      endif   

c     Subtraction term for (fake) singularities of E40til antenna.
      call pmap5to4to3D(i4,i5,i3,i2,i1,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -A30y5(i4,i5,i3)*E30y5map(w13,w12,w23)  
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

 111  continue

      B50dds = wt

      return
      end

************************************************************************

      function B50eds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      logical plot
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/sa3/yij,yik,yjk
      common/sb3/wKm,wKl,wlm
      common/sc3/x12,x13,x23
      common/plots/plot
      common/pcut/ppar(4,5) 

      wt=0d0

c     1-4-3.
c     Term (h) in (9.2).
      call pmap5to4to3K(i3,i4,i1,i5,i2,1,2,3)
c     i_l's in position 2 and 4 are unresolved
c     i in position 3 is shared radiator.
c     i4=j in (9.2).
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
c     l=i5,m=i2.
         wtsub = -E30y5(i1,i4,i3)*A30y5map(wKm,wKl,wlm)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     3-4-2.
      call pmap5to4to3K(i3,i4,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i2,i4,i3)*A30y5map(wKm,wKl,wlm)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     Exchange 3<->4.

c     1-3-4.
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
c     i_l's in position 2 and 4 are unresolved 
c     i4=j in (9.2).
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
c     l=i5,m=i2.
         wtsub = -E30y5(i1,i3,i4)*A30y5map(wKm,wKl,wlm)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

c     2-3-4.
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -E30y5(i2,i3,i4)*A30y5map(wKm,wKl,wlm)
     .        *A30y5map(x12,x13,x23)*var
         if(plot)then
            call bino(1,wtplot*wtsub,5)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif   

      B50eds = wt

      return
      end

c-----------------------------------------------------------------------
