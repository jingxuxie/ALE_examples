c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     One-loop real-radiation subtraction terms for e+ e- -> 4j.
c     Equation numbers refer to arXiv:0710.0346.

c-----------------------------------------------------------------------
c     Four-parton real-virtual subtraction terms.
c-----------------------------------------------------------------------

c     Function for N^2 part, sig3s.
c     Virtual unresolved subtraction terms of type (b) and (c).
      function VS1bcN2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/plots/plot
      common/yij4/y(4,4)
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y123=y12+y13+y23
      y124=y12+y14+y24
      y134=y13+y14+y34
      y234=y23+y24+y34

      beta = 11d0/6d0    

      calD30 = 34d0/3d0
      calF30 = 73d0/4d0
c     Six different antenna functions:
c     1-3-4, 1-4-3, 3-4-2, 4-3-2, 1-3-2, 1-4-2.

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = var* (
     .        sd30(i1,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + calD30*sd30(i1,i3,i4)*T(s12,s13,s23)
     .        + 1d0/3d0*calF30*sd30(i1,i3,i4)*T(s12,s13,s23)
     .        - beta*log(y134)*sd30(i1,i3,i4)*T(s12,s13,s23)
     .        + sd31(i1,i3,i4)*T(s12,s13,s23)
     .        )
c     Left-over from terms h,i.
         zx= -0.5d0*(
     .        1d0/2d0*dlog(s23)**2
     .        -1d0/2d0*dlog(y24)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y14)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -1d0/2d0*dlog(y12)**2
     .        -5d0/3d0*dlog(s23/y24)+5d0/3d0*dlog(s13/y14)
     .        -3d0/2d0*dlog(s12/y12)
     .        )*sd30(i1,i3,i4)*T(s12,s13,s23)*var
c     With this, one is left with
c     div= -0.5d0*( log(y24*y12/y14) - log(s23*s12/s13))/e
c     .         *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c     New soft terms.
         zy = -0.5d0*softfinite(11,13,23,21,22)
     .        *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c     Comes with 
c     div= -0.5d0*( -log(y24*y12/y14) + log(s23*s12/s13))/e
c     .         *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c     and cancels divergency.
         wtsub = wtsub+zx+zy
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap4to3old(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = var* (
     .        sd30(i1,i4,i3)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + calD30*sd30(i1,i4,i3)*T(s12,s13,s23)
     .        + 1d0/3d0*calF30*sd30(i1,i4,i3)*T(s12,s13,s23)
     .        - beta*log(y134)*sd30(i1,i4,i3)*T(s12,s13,s23)
     .        + sd31(i1,i4,i3)*T(s12,s13,s23)
     .        )
c     Left-over from terms h,i
         zx= -0.5d0*(
     .        1d0/2d0*dlog(s23)**2
     .        -1d0/2d0*dlog(y23)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y13)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -1d0/2d0*dlog(y12)**2
     .        -5d0/3d0*dlog(s23/y23)+5d0/3d0*dlog(s13/y13)
     .        -3d0/2d0*dlog(s12/y12)
     .        )*sd30(i1,i4,i3)*T(s12,s13,s23)*var
c     New soft terms 
         zy = -0.5d0*softfinite(11,13,23,21,22)
     .        *sd30(i1,i4,i3)*T(s12,s13,s23)*var
         wtsub = wtsub+zx+zy
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
         wtsub = var* (
     .        sd30(i2,i4,i3)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + calD30*sd30(i2,i4,i3)*T(s12,s13,s23)
     .        + 1d0/3d0*calF30*sd30(i2,i4,i3)*T(s12,s13,s23)
     .        - beta*log(y234)*sd30(i2,i4,i3)*T(s12,s13,s23)
     .        + sd31(i2,i4,i3)*T(s12,s13,s23)
     .        )
c     Left-over from terms h,i.
         zx= -0.5d0*(
     .        1d0/2d0*dlog(s13)**2
     .        -1d0/2d0*dlog(y13)**2
     .        -1d0/2d0*dlog(s23)**2
     .        +1d0/2d0*dlog(y23)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -1d0/2d0*dlog(y12)**2
     .        -5d0/3d0*dlog(s13/y13)+5d0/3d0*dlog(s23/y23)
     .        -3d0/2d0*dlog(s12/y12)
     .        )*sd30(i2,i4,i3)*T(s12,s13,s23)*var
c     New soft terms.
         zy = -0.5d0*softfinite(11,13,23,21,22)
     .        *sd30(i2,i4,i3)*T(s12,s13,s23)*var
         wtsub = wtsub+zx+zy
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-3-2 antenna.
      call pmap4to3old(i4,i3,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = var* (
     .        sd30(i2,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + calD30*sd30(i2,i3,i4)*T(s12,s13,s23)
     .        + 1d0/3d0*calF30*sd30(i2,i3,i4)*T(s12,s13,s23)
     .        - beta*log(y234)*sd30(i2,i3,i4)*T(s12,s13,s23)
     .        + sd31(i2,i3,i4)*T(s12,s13,s23)
     .        )
c     Left-over from terms h,i
         zx= -0.5d0*(
     .        1d0/2d0*dlog(s13)**2
     .        -1d0/2d0*dlog(y14)**2
     .        -1d0/2d0*dlog(s23)**2
     .        +1d0/2d0*dlog(y24)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -1d0/2d0*dlog(y12)**2
     .        -5d0/3d0*dlog(s13/y14)+5d0/3d0*dlog(s23/y24)
     .        -3d0/2d0*dlog(s12/y12)
     .        )*sd30(i2,i3,i4)*T(s12,s13,s23)*var
c     New soft terms 
         zy = -0.5d0*softfinite(11,13,23,21,22)
     .        *sd30(i2,i3,i4)*T(s12,s13,s23)*var
         wtsub = wtsub+zx+zy
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-2 antenna.
      call pmap4to3old(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -var*
     .        A31t(y12,y13,y23)*T(s12,s13,s23) 
         zx = -0.5d0*(
     .        +1d0/2d0*dlog(y14)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y24)**2
     .        -1d0/2d0*dlog(s23)**2
     .        +5d0/3d0*dlog(s13/y14)+5d0/3d0*dlog(s23/y24)
     .        -1d0/2d0*dlog(y12)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -3d0/2d0*dlog(s12/y12)
     .        ) *A30(i1,i3,i2)*T(s12,s13,s23)*var
c     New soft terms.
         zy = +0.5d0*softfinite(11,13,23,21,22)
     .        *A30(i1,i3,i2)*T(s12,s13,s23)*var
         wtsub = wtsub+zx+zy
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
         wtsub = -var*
     .        A31t(y12,y14,y24)*T(s12,s13,s23) 
         zx = -0.5d0*(
     .        +1d0/2d0*dlog(y13)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y23)**2
     .        -1d0/2d0*dlog(s23)**2
     .        +5d0/3d0*dlog(s13/y13)+5d0/3d0*dlog(s23/y23)
     .        -1d0/2d0*dlog(y12)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -3d0/2d0*dlog(s12/y12)
     .        ) *A30(i1,i4,i2)*T(s12,s13,s23)*var
c     New soft terms.
         zy = +0.5d0*softfinite(11,13,23,21,22)
     .        *A30(i1,i4,i2)*T(s12,s13,s23)*var
         wtsub = wtsub+zx+zy
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bcN2 = wt

      return
      end

************************************************************************

*     Function for N^0 part, sig3s.
*     Virtual unresolved subtraction terms of type (b) and (c).
      function VS1bcN0(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/plots/plot
      common/yij4/y(4,4)
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y123=y12+y13+y23
      y124=y12+y14+y24
      y134=y13+y14+y34
      y234=y23+y24+y34

      beta = 11d0/6d0    
      calA30 = 19d0/4d0
      calD30 = 34d0/3d0

c     Six different antenna functions:
c     1-3-4, 1-4-3, 3-4-2, 4-3-2, 1-3-2, 1-4-2.

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -1d0*var*
     .        (sd30(i1,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + sd30(i1,i3,i4)*calA30*T(s12,s13,s23) )
c     -2*calA30 terms match ee2b.
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-4-3 antenna.
      call pmap4to3old(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -1d0*var*
     .        (sd30(i1,i4,i3)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + sd30(i1,i4,i3)*calA30*T(s12,s13,s23) )
c     -2*calA30 terms match ee2b.
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
         wtsub = -1d0*var*
     .        (sd30(i2,i4,i3)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + sd30(i2,i4,i3)*calA30*T(s12,s13,s23) )
c     -2*calA30 terms match ee2b.
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     4-3-2 antenna.
      call pmap4to3old(i4,i3,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -1d0*var*
     .        (sd30(i2,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + sd30(i2,i3,i4)*calA30*T(s12,s13,s23) )
c     -2*calA30 terms match ee2b.
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-2 antenna.
      call pmap4to3old(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = -1d0*var* (
     .        ( A31t(y12,y13,y23) !fLB34
     .        + A31(y12,y13,y23)
     .        + (calD30
     .        +1d0/2d0*dlog(y14)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y24)**2
     .        -1d0/2d0*dlog(s23)**2
     .        -1d0/2d0*dlog(y12)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -5d0/3d0*dlog(y14/s13)-5d0/3d0*dlog(y24/s23) 
     .        + 3d0/2d0*dlog(y12/y123)
     .        )*A30(i1,i3,i2)
     .        + (calD30-calA30)*A30(i1,i3,i2)
     .        - beta*dlog(y123)*A30(i1,i3,i2)
     .        )*T(s12,s13,s23) 
     .        + A30(i1,i3,i2)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        )
c     New soft terms.
         zy = softfinite(11,13,23,21,22)
     .        *A30(i1,i3,i2)*T(s12,s13,s23)*var
         wtsub = wtsub+zy
c     -2*calD30 terms match ee2a.
c     +calA30 terms match ee4n.
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
         wtsub = -1d0*var* (
     .        (A31t(y12,y14,y24) !fLB34
     .        + A31(y12,y14,y24)
     .        + (calD30
     .        +1d0/2d0*dlog(y13)**2
     .        -1d0/2d0*dlog(s13)**2
     .        +1d0/2d0*dlog(y23)**2
     .        -1d0/2d0*dlog(s23)**2
     .        -1d0/2d0*dlog(y12)**2
     .        +1d0/2d0*dlog(s12)**2
     .        -5d0/3d0*dlog(y13/s13)-5d0/3d0*dlog(y23/s23)  
     .        + 3d0/2d0*dlog(y12/y124)
     .        )*A30(i1,i4,i2)
     .        + (calD30-calA30)*A30(i1,i4,i2)
     .        - beta*dlog(y124)*A30(i1,i4,i2)
     .        )*T(s12,s13,s23) 
     .        + A30(i1,i4,i2)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        )
c     New soft terms.
         zy = softfinite(11,13,23,21,22)
     .        *A30(i1,i4,i2)*T(s12,s13,s23)*var
         wtsub = wtsub+zy
c     -2*calD30 terms match ee2a.
c     + calA30 terms match ee4n.
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bcN0 = wt

      return
      end

************************************************************************

c     One-loop single unresolved subtraction term for 1/N^2.
c     (9.78) and (9.79) combined.
      function VS1bc1oN2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/plots/plot
      common/yij4/y(4,4)
      logical plot 
      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0

c     1-3-2 antenna.
      call pmap4to3old(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         ee2=19d0/4d0
         ff2=-4d0
c     s12 = y123
         wtsub = var*( 
     .        tilda31(y12,y13,y23)*T(s12,s13,s23) 
     .        + A30(i1,i3,i2)*
     .        (tilda31(s12,s13,s23)+ff2*T(s12,s13,s23))    
     .        + A30(i1,i3,i2)*ee2*T(s12,s13,s23) ) ! (9.79) 
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
         ee2=19d0/4d0
         ff2=-4d0
         wtsub = var*( 
     .        tilda31(y12,y14,y24)*T(s12,s13,s23) 
     .        + A30(i1,i4,i2)*
     .        (tilda31(s12,s13,s23)+ff2*T(s12,s13,s23))    
     .        + A30(i1,i4,i2)*ee2*T(s12,s13,s23) )      
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bc1oN2 = wt

      return
      end

************************************************************************

c     Function for NF*N part, sig3s.
c     Virtual unresolved subtraction terms of type (b) and (c).
      function VS1bcNFN(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/plots/plot
      common/yij4/y(4,4)
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y134=y13+y14+y34
      y234=y23+y24+y34

      beta = 11d0/6d0
      betaf=-1d0/3d0    

c     Two different antenna functions: 1-3-4, 3-4-2.

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
c     First bracket here.
         calD30 = 34d0/3d0
         calA30 = 19d0/4d0
         wtsub = var*
     .        0.5d0*(E30(i1,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .        + (  E31(i1,i3,i4) + 2d0*calA30*E30(i1,i3,i4)
     .        - beta*dlog(y134)*E30(i1,i3,i4) 
     .        )* T(s12,s13,s23) )
c     Second bracket here.
c     Note that we have cancellations between A31hat and D31hat here
c     therefore, we keep the explicit logs with the calE30 and calG30.
         A31hat = 0d0
         D31hat = -1d0/3d0/y34
         calE30a = 1d0/3d0*dlog(y13/y134)-1d0
         calE30b = 1d0/3d0*dlog(y24/y134)-1d0
         calG30  = 1d0/3d0*dlog(y34/y134)-7d0/6d0
         wtsub = wtsub+var*
     .        (  sd30(i1,i3,i4)*A31hat 
     .        + (D31hat/2d0
     .        +(2d0*calG30)*sd30(i1,i3,i4)
     .        - 2d0*betaf*dlog(y134)*sd30(i1,i3,i4) 
     .        ) * T(s12,s13,s23) )
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
c     First bracket here.
         calD30 = 34d0/3d0
         calA30 = 19d0/4d0
         wtsub = var*
     .        0.5d0*( E30(i2,i3,i4)*(A31(s12,s13,s23)
     .        -4d0*T(s12,s13,s23))
     .        + (  E31(i2,i3,i4) + 2d0*calA30*E30(i2,i3,i4)
     .        - beta*dlog(y234)*E30(i2,i3,i4) 
     .        )* T(s12,s13,s23) )
c     Second bracket here.
c     Note that we have cancellations between A31hat and D31hat here
c     therefore, we keep the explicit logs with the calE30 and calG30.
         A31hat = 0d0
         D31hat = -1d0/3d0/y34
         calE30a = 1d0/3d0*dlog(y13/y234)-1d0
         calE30b = 1d0/3d0*dlog(y24/y234)-1d0
         calG30  = 1d0/3d0*dlog(y34/y234)-7d0/6d0

         wtsub = wtsub+var*
     .        (  sd30(i2,i4,i3)*A31hat 
     .        + (D31hat/2d0 
     .        +(2d0*calG30)*sd30(i2,i4,i3)
     .        - 2d0*betaf*dlog(y234)*sd30(i2,i4,i3) 
     .        ) * T(s12,s13,s23) )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bcNFN = wt

      return
      end

************************************************************************

c     Function for NF/N part, sig3s.
c     Virtual unresolved subtraction terms of type (b) and (c).
      function VS1bcNFoN(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/plots/plot
      common/yij4/y(4,4)
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y123=y12+y13+y23
      y124=y12+y14+y24
      y134=y13+y14+y34
      y234=y23+y24+y34

      betaf=-1d0/3d0    
      calA30 = 19d0/4d0
      calE30 = -1d0
      calG30 = -7d0/6d0

c     Four different antenna functions: 1-3-4, 3-4-2, 1-3-2, 1-4-2.

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = var*
     .        ( 0.5d0)*(E30(i1,i3,i4)*(A31t(s12,s13,s23)
     .        -4d0*T(s12,s13,s23))
     .        + ( E31t(i1,i3,i4) + 2d0*calA30*E30(i1,i3,i4)
     .        )* T(s12,s13,s23) )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     2-3-4 antenna.
      call pmap4to3old(i2,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         wtsub = var*
     .        ( 0.5d0)*(E30(i2,i3,i4)*(A31t(s12,s13,s23)
     .        -4d0*T(s12,s13,s23))
     .        + ( E31t(i2,i3,i4) + 2d0*calA30*E30(i2,i3,i4)
     .        )* T(s12,s13,s23) )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

c     1-3-2 antenna.
      call pmap4to3old(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         A31hat1 = 1d0/6d0*dlog(s13*s23)*T(s12,s13,s23)
         A31hat2 = 1d0/6d0*dlog(y13*y23/y123**2)*A30(i1,i3,i2)
         A31hat1 = 0d0
         A31hat2 = 0d0
         calE30x = 4d0*calE30 
     .        + 1d0/3d0*dlog(y13/y123)
     .        + 1d0/3d0*dlog(y14/y123)
     .        + 1d0/3d0*dlog(y23/y123)
     .        + 1d0/3d0*dlog(y24/y123)
         wtsub = var*
     .        ( 0.5d0)*(A30(i1,i3,i2)*A31hat1
     .        + ( A31hat2 + 1d0/2d0*calE30x*A30(i1,i3,i2)
     .        - 2d0*betaf*dlog(y123)*A30(i1,i3,i2) 
     .        )* T(s12,s13,s23) )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
         if(idebug.eq.1)write(*,*)" VS1bcNFoN 3 ",wtsub
      endif

c     1-4-2 antenna.
      call pmap4to3old(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         A31hat1 = 1d0/6d0*dlog(s13*s23)*T(s12,s13,s23)
         A31hat2 = 1d0/6d0*dlog(y14*y24/y124**2)*A30(i1,i4,i2)
         A31hat1 = 0d0
         A31hat2 = 0d0
         calE30x = 4d0*calE30 
     .        + 1d0/3d0*dlog(y13/y124)
     .        + 1d0/3d0*dlog(y14/y124)
     .        + 1d0/3d0*dlog(y23/y124)
     .        + 1d0/3d0*dlog(y24/y124)
         wtsub = var*
     .        ( 0.5d0)*(A30(i1,i4,i2)*A31hat1
     .        + ( A31hat2 + 1d0/2d0*calE30x*A30(i1,i4,i2)
     .        - 2d0*betaf*dlog(y124)*A30(i1,i4,i2) 
     .        )* T(s12,s13,s23) )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bcNFoN =  wt

      return
      end

************************************************************************

c     Function for NF^2 part, sig3s.
      function VS1bcNF2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/s3/s12,s13,s23
      common/yij4/y(4,4)
      common/plots/plot
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y134=y13+y14+y34
      y234=y23+y24+y34

      betaf=-1d0/3d0    

c     1-3-4 antenna.
      call pmap4to3old(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
      if(ipass.eq.1)then
         ee5=-10d0/9d0+2d0/3d0*dlog(y34/y134) 
         E31hat=ee5*E30(i1,i3,i4)
         A31hat=0.d0
         wtsub = var* 
     .        ( (E31hat-2d0*betaf*dlog(y134)*
     .        E30(i1,i3,i4))*T(s12,s13,s23) 
     .        + E30(i1,i3,i4)*A31hat )     
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
         ee5=-10d0/9d0+2d0/3d0*dlog(y34/y234) 
         E31hat=ee5*E30(i2,i3,i4)
         A31hat=0.d0
         wtsub = var* 
     .        ( (E31hat-2d0*betaf*dlog(y234)*
     .        E30(i2,i3,i4))*T(s12,s13,s23) 
     .        + E30(i2,i3,i4)*A31hat )
         if(plot)then
            call bino(1,wtplot*wtsub,4)
         else
            call distrib(wtdis)
            wtsub = wtsub/wtdis
         endif
         wt=wt+wtsub
      endif

      VS1bcNF2 = wt

      return
      end

c-----------------------------------------------------------------------
