* subtraction terms for one-loop real radiation
* equation numbers refer to arXiv:0710.0346
************************************************************************
*
************************************************************************
* function for NF/N part, sig3s
* virtual unresolved subtraction terms of type (b) and (c) 
************************************************************************
      function VS1bcNFoN(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /plots/plot
      common /yij4/y(4,4)
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


* four different antenna functions: 1-3-4, 3-4-2, 1-3-2, 1-4-2

*
* 1-3-4 antenna
*

      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var*
     .  ( 0.5d0)*(E30(i1,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + ( E31t(i1,i3,i4) + 2d0*calA30*E30(i1,i3,i4)
     .             )* T(s12,s13,s23) )
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 2-3-4 antenna
*

      call pmap4to3(i2,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var*
     .  ( 0.5d0)*(E30(i2,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + ( E31t(i2,i3,i4) + 2d0*calA30*E30(i2,i3,i4)
     .             )* T(s12,s13,s23) )
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-2 antenna
*

      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
            A31hat1 = 1d0/6d0*dlog(s13*s23)*T(s12,s13,s23)
            A31hat2 = 1d0/6d0*dlog(y13*y23/y123**2)*A30(i1,i3,i2)
            A31hat1 = 0d0
            A31hat2 = 0d0
            calE30x = 4d0*calE30 
     .              + 1d0/3d0*dlog(y13/y123)
     .              + 1d0/3d0*dlog(y14/y123)
     .              + 1d0/3d0*dlog(y23/y123)
     .              + 1d0/3d0*dlog(y24/y123)
           wtsub = var*
     .  ( 0.5d0)*(A30(i1,i3,i2)*A31hat1
     .           + ( A31hat2 + 1d0/2d0*calE30x*A30(i1,i3,i2)
     .             - 2d0*betaf*dlog(y123)*A30(i1,i3,i2) 
     .             )* T(s12,s13,s23) )
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
           if(idebug.eq.1)write(*,*)" VS1bcNFoN 3 ",wtsub
        endif
*
* 1-4-2 antenna
*

      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
            A31hat1 = 1d0/6d0*dlog(s13*s23)*T(s12,s13,s23)
            A31hat2 = 1d0/6d0*dlog(y14*y24/y124**2)*A30(i1,i4,i2)
            A31hat1 = 0d0
            A31hat2 = 0d0
            calE30x = 4d0*calE30 
     .              + 1d0/3d0*dlog(y13/y124)
     .              + 1d0/3d0*dlog(y14/y124)
     .              + 1d0/3d0*dlog(y23/y124)
     .              + 1d0/3d0*dlog(y24/y124)
           wtsub = var*
     .  ( 0.5d0)*(A30(i1,i4,i2)*A31hat1
     .           + ( A31hat2 + 1d0/2d0*calE30x*A30(i1,i4,i2)
     .             - 2d0*betaf*dlog(y124)*A30(i1,i4,i2) 
     .             )* T(s12,s13,s23) )
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
* function for NF*N part, sig3s
* virtual unresolved subtraction terms of type (b) and (c) 
************************************************************************
      function VS1bcNFN(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /plots/plot
      common /yij4/y(4,4)
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
* two different antenna functions: 1-3-4, 3-4-2

*
* 1-3-4 antenna
*

      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
c first bracket here

           calD30 = 34d0/3d0
           calA30 = 19d0/4d0

           wtsub = var*
     .     0.5d0*(E30(i1,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + (  E31(i1,i3,i4) + 2d0*calA30*E30(i1,i3,i4)
     .               - beta*dlog(y134)*E30(i1,i3,i4) 
     .             )* T(s12,s13,s23) )
c second bracket here
c
c note that we have cancellations between A31hat and D31hat here
c therefore, we keep the explicit logs with the calE30 and calG30
c
           
           A31hat = 0d0
           D31hat = -1d0/3d0/y34
           calE30a = 1d0/3d0*dlog(y13/y134)-1d0
           calE30b = 1d0/3d0*dlog(y24/y134)-1d0
           calG30  = 1d0/3d0*dlog(y34/y134)-7d0/6d0
           wtsub = wtsub+var*
     .            (  sd30(i1,i3,i4)*A31hat 
     .            + (D31hat/2d0
     .               +(2d0*calG30)*sd30(i1,i3,i4)
     .               - 2d0*betaf*dlog(y134)*sd30(i1,i3,i4) 
     .            ) * T(s12,s13,s23) )


           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 3-4-2 antenna
*
      call pmap4to3(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
c first bracket here

           calD30 = 34d0/3d0
           calA30 = 19d0/4d0
           wtsub = var*
     .     0.5d0*( E30(i2,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + (  E31(i2,i3,i4) + 2d0*calA30*E30(i2,i3,i4)
     .               - beta*dlog(y234)*E30(i2,i3,i4) 
     .             )* T(s12,s13,s23) )
c second bracket here
c
c note that we have cancellations between A31hat and D31hat here
c therefore, we keep the explicit logs with the calE30 and calG30
c
           
           A31hat = 0d0
           D31hat = -1d0/3d0/y34
           calE30a = 1d0/3d0*dlog(y13/y234)-1d0
           calE30b = 1d0/3d0*dlog(y24/y234)-1d0
           calG30  = 1d0/3d0*dlog(y34/y234)-7d0/6d0

           wtsub = wtsub+var*
     .            (  sd30(i2,i4,i3)*A31hat 
     .            + (D31hat/2d0 
     .               +(2d0*calG30)*sd30(i2,i4,i3)
     .               - 2d0*betaf*dlog(y234)*sd30(i2,i4,i3) 
     .            ) * T(s12,s13,s23) )


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
* function for N^0 part, sig3s
*
* virtual unresolved subtraction terms of type (b) and (c) 

      function VS1bcN0(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /plots/plot
      common /yij4/y(4,4)
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

* six different antenna functions: 1-3-4, 1-4-3, 3-4-2, 4-3-2, 1-3-2, 1-4-2

*
* 1-3-4 antenna        !fLB34
*
      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var*
     .       (sd30(i1,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + sd30(i1,i3,i4)*calA30*T(s12,s13,s23) )
c -2*calA30 terms match ee2b
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 1-4-3 antenna        !fLB34
*
      call pmap4to3(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var*
     .       (sd30(i1,i4,i3)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + sd30(i1,i4,i3)*calA30*T(s12,s13,s23) )
c -2*calA30 terms match ee2b
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 3-4-2 antenna        !fLB34
*
      call pmap4to3(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var*
     .       (sd30(i2,i4,i3)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + sd30(i2,i4,i3)*calA30*T(s12,s13,s23) )
c -2*calA30 terms match ee2b
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 4-3-2 antenna        !fLB34
*
      call pmap4to3(i4,i3,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var*
     .            (sd30(i2,i3,i4)*(A31t(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + sd30(i2,i3,i4)*calA30*T(s12,s13,s23) )
c -2*calA30 terms match ee2b
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-2 antenna
*
      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var* (
     .          (        A31t(y12,y13,y23)                !fLB34
     .              +    A31(y12,y13,y23)
     .              + (calD30
     .         +1d0/2d0*dlog(y14)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y24)**2
     .         -1d0/2d0*dlog(s23)**2
     .         -1d0/2d0*dlog(y12)**2
     .         +1d0/2d0*dlog(s12)**2
     .        -5d0/3d0*dlog(y14/s13)-5d0/3d0*dlog(y24/s23) 
     .        + 3d0/2d0*dlog(y12/y123)
     .                )*A30(i1,i3,i2)
     .              + (calD30-calA30)*A30(i1,i3,i2)
     .              - beta*dlog(y123)*A30(i1,i3,i2)
     .             )*T(s12,s13,s23) 
     .           + A30(i1,i3,i2)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .                  )
c ---- new soft terms
           zy = softfinite(11,13,23,21,22)
     .         *A30(i1,i3,i2)*T(s12,s13,s23)*var
           wtsub = wtsub+zy
c -2*calD30 terms match ee2a
c  + calA30 terms match ee4n
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 1-4-2 antenna
*
      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -1d0*var* (
     .           (       A31t(y12,y14,y24)               !fLB34
     .              +    A31(y12,y14,y24)
     .              + (calD30
     .         +1d0/2d0*dlog(y13)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y23)**2
     .         -1d0/2d0*dlog(s23)**2
     .         -1d0/2d0*dlog(y12)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -5d0/3d0*dlog(y13/s13)-5d0/3d0*dlog(y23/s23)  
     .        + 3d0/2d0*dlog(y12/y124)
     .                 )*A30(i1,i4,i2)
     .              + (calD30-calA30)*A30(i1,i4,i2)
     .              - beta*dlog(y124)*A30(i1,i4,i2)
     .             )*T(s12,s13,s23) 
     .           + A30(i1,i4,i2)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .                  )
c ---- new soft terms
           zy = softfinite(11,13,23,21,22)
     .         *A30(i1,i4,i2)*T(s12,s13,s23)*var
           wtsub = wtsub+zy
c -2*calD30 terms match ee2a
c  + calA30 terms match ee4n
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
* function for N^2 part, sig3s
*
* virtual unresolved subtraction terms of type (b) and (c) 
*
      function VS1bcN2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /plots/plot
      common /yij4/y(4,4)
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
* six different antenna functions: 1-3-4, 1-4-3, 3-4-2, 4-3-2, 1-3-2, 1-4-2

*
* 1-3-4 antenna
*
      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var* (
     .        sd30(i1,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + calD30*sd30(i1,i3,i4)*T(s12,s13,s23)
     .           + 1d0/3d0*calF30*sd30(i1,i3,i4)*T(s12,s13,s23)
     .           - beta*log(y134)*sd30(i1,i3,i4)*T(s12,s13,s23)
     .           + sd31(i1,i3,i4)*T(s12,s13,s23)
     .                   )
c ---- left-over from terms h,i
           zx= -0.5d0*(
     .          1d0/2d0*dlog(s23)**2
     .         -1d0/2d0*dlog(y24)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y14)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -1d0/2d0*dlog(y12)**2
     .         -5d0/3d0*dlog(s23/y24)+5d0/3d0*dlog(s13/y14)
     .         -3d0/2d0*dlog(s12/y12)
     .         )*sd30(i1,i3,i4)*T(s12,s13,s23)*var
c ---- with this, one is left with 
c           div= -0.5d0*( log(y24*y12/y14) - log(s23*s12/s13))/e
c     .         *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c 
c ---- new soft terms 
           zy = -0.5d0*softfinite(11,13,23,21,22)
     .         *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c ---- comes with 
c           div= -0.5d0*( -log(y24*y12/y14) + log(s23*s12/s13))/e
c     .         *sd30(i1,i3,i4)*T(s12,s13,s23)*var
c    and cancels divergency
           wtsub = wtsub+zx+zy
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-3 antenna
*
      call pmap4to3(i1,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var* (
     .        sd30(i1,i4,i3)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + calD30*sd30(i1,i4,i3)*T(s12,s13,s23)
     .           + 1d0/3d0*calF30*sd30(i1,i4,i3)*T(s12,s13,s23)
     .           - beta*log(y134)*sd30(i1,i4,i3)*T(s12,s13,s23)
     .           + sd31(i1,i4,i3)*T(s12,s13,s23)
     .                   )
c ---- left-over from terms h,i
           zx= -0.5d0*(
     .          1d0/2d0*dlog(s23)**2
     .         -1d0/2d0*dlog(y23)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y13)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -1d0/2d0*dlog(y12)**2
     .         -5d0/3d0*dlog(s23/y23)+5d0/3d0*dlog(s13/y13)
     .         -3d0/2d0*dlog(s12/y12)
     .         )*sd30(i1,i4,i3)*T(s12,s13,s23)*var
c ---- new soft terms 
           zy = -0.5d0*softfinite(11,13,23,21,22)
     .         *sd30(i1,i4,i3)*T(s12,s13,s23)*var
           wtsub = wtsub+zx+zy
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 3-4-2 antenna
*
      call pmap4to3(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var* (
     .        sd30(i2,i4,i3)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + calD30*sd30(i2,i4,i3)*T(s12,s13,s23)
     .           + 1d0/3d0*calF30*sd30(i2,i4,i3)*T(s12,s13,s23)
     .           - beta*log(y234)*sd30(i2,i4,i3)*T(s12,s13,s23)
     .           + sd31(i2,i4,i3)*T(s12,s13,s23)
     .                   )
c ---- left-over from terms h,i
           zx= -0.5d0*(
     .          1d0/2d0*dlog(s13)**2
     .         -1d0/2d0*dlog(y13)**2
     .         -1d0/2d0*dlog(s23)**2
     .         +1d0/2d0*dlog(y23)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -1d0/2d0*dlog(y12)**2
     .         -5d0/3d0*dlog(s13/y13)+5d0/3d0*dlog(s23/y23)
     .         -3d0/2d0*dlog(s12/y12)
     .         )*sd30(i2,i4,i3)*T(s12,s13,s23)*var
c ---- new soft terms 
           zy = -0.5d0*softfinite(11,13,23,21,22)
     .         *sd30(i2,i4,i3)*T(s12,s13,s23)*var
           wtsub = wtsub+zx+zy
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 4-3-2 antenna
*
      call pmap4to3(i4,i3,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = var* (
     .        sd30(i2,i3,i4)*(A31(s12,s13,s23)-4d0*T(s12,s13,s23))
     .           + calD30*sd30(i2,i3,i4)*T(s12,s13,s23)
     .           + 1d0/3d0*calF30*sd30(i2,i3,i4)*T(s12,s13,s23)
     .           - beta*log(y234)*sd30(i2,i3,i4)*T(s12,s13,s23)
     .           + sd31(i2,i3,i4)*T(s12,s13,s23)
     .                   )
c ---- left-over from terms h,i
           zx= -0.5d0*(
     .          1d0/2d0*dlog(s13)**2
     .         -1d0/2d0*dlog(y14)**2
     .         -1d0/2d0*dlog(s23)**2
     .         +1d0/2d0*dlog(y24)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -1d0/2d0*dlog(y12)**2
     .         -5d0/3d0*dlog(s13/y14)+5d0/3d0*dlog(s23/y24)
     .         -3d0/2d0*dlog(s12/y12)
     .         )*sd30(i2,i3,i4)*T(s12,s13,s23)*var
c ---- new soft terms 
           zy = -0.5d0*softfinite(11,13,23,21,22)
     .         *sd30(i2,i3,i4)*T(s12,s13,s23)*var
           wtsub = wtsub+zx+zy
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-2 antenna
*
      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -var*
     .              A31t(y12,y13,y23)*T(s12,s13,s23) 
           zx = -0.5d0*(
     .         +1d0/2d0*dlog(y14)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y24)**2
     .         -1d0/2d0*dlog(s23)**2
     .         +5d0/3d0*dlog(s13/y14)+5d0/3d0*dlog(s23/y24)
     .         -1d0/2d0*dlog(y12)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -3d0/2d0*dlog(s12/y12)
     .               ) *A30(i1,i3,i2)*T(s12,s13,s23)*var
c ---- new soft terms 
           zy = +0.5d0*softfinite(11,13,23,21,22)
     .         *A30(i1,i3,i2)*T(s12,s13,s23)*var
           wtsub = wtsub+zx+zy
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
* 1-4-2 antenna
*
      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
         if(ipass.eq.1)then
           wtsub = -var*
     .              A31t(y12,y14,y24)*T(s12,s13,s23) 
           zx = -0.5d0*(
     .         +1d0/2d0*dlog(y13)**2
     .         -1d0/2d0*dlog(s13)**2
     .         +1d0/2d0*dlog(y23)**2
     .         -1d0/2d0*dlog(s23)**2
     .         +5d0/3d0*dlog(s13/y13)+5d0/3d0*dlog(s23/y23)
     .         -1d0/2d0*dlog(y12)**2
     .         +1d0/2d0*dlog(s12)**2
     .         -3d0/2d0*dlog(s12/y12)
     .           ) *A30(i1,i4,i2)*T(s12,s13,s23)*var
c ---- new soft terms 
           zy = +0.5d0*softfinite(11,13,23,21,22)
     .         *A30(i1,i4,i2)*T(s12,s13,s23)*var
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

c x-g-g: (6.19)
      function sd31(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sd30e=sd30(ia,iu,ib)
      sd31=     -( Rli(yau/yaub,yub/yaub) + Rli(yab/yaub,yub/yaub)
     .            +Rli(yau/yaub,yab/yaub) 
     .             + 5d0/3d0*dlog(yau/yaub) 
     .             + 5d0/3d0*dlog(yab/yaub) 
     .             + 11d0/6d0*dlog(yub/yaub) )*sd30e
     .           +1d0/6d0/yub
      return
      end


c x-q-qbar: (6.29)
      function E31(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      E30e=E30(ia,iu,ib)
      E31=     -( Rli(yau/yaub,yub/yaub) + Rli(yab/yaub,yub/yaub) 
     .             + 3d0/2d0*dlog(yau/yaub) 
     .             + 3d0/2d0*dlog(yab/yaub) 
     .             + 13d0/6d0*dlog(yub/yaub) 
     .             - 40d0/9d0)*E30e
     .           + Rli(yau/yaub,yub/yaub)*yau/yaub**2
     .           + Rli(yab/yaub,yub/yaub)*yab/yaub**2
      return
      end

c x-q-qbar: (6.31)
      function E31t(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      E30e=E30(ia,iu,ib)
      E31t= -4d0*E30e
      return
      end

      function A31t(s12,s13,s23)
      implicit real*8(a-h,o-z)
      A31t = tilda31(s12,s13,s23)
      return
      end

      function Rli(x,y)
      implicit real*8(a-z)
      parameter(pi=3.141592653589793238d0)
      Rli = dlog(x)*dlog(y)-dlog(y)*dlog(1d0-y)-dlog(x)*dlog(1d0-x)
     .    +pi**2/6d0-li2(x)-li2(y)
      return
      end


      function softfinite(iI,iK,i1,i2,i3)
      implicit real*8(a-h,o-z)

c---- this function also comes with 
c---- +1/e * ( log(sIK/sI0/sK0) - log(s23/s12/s13) )
      
      dlnorm = dlog(sprod(iI,iK))

      x1 = xsoftnew(iI,iK,iI,iK)
      x1 = 1d0
      x2 = xsoftnew(iI,iK,iI,i1)
      x3 = xsoftnew(iI,iK,i1,iK)
      x4 = xsoftnew(iI,iK,i2,i3)
      x5 = xsoftnew(iI,iK,i1,i3)
      x6 = xsoftnew(iI,iK,i2,i1)

      softfinite = -dlnorm*(dlog(x1/x2/x3 /(x4/x5/x6)))
     .              - rli2(dabs(1d0-x1)) - 0.5d0*dlog(x1)**2 
     .              + rli2(dabs(1d0-x2)) + 0.5d0*dlog(x2)**2 
     .              + rli2(dabs(1d0-x3)) + 0.5d0*dlog(x3)**2 
     .              + rli2(dabs(1d0-x4)) + 0.5d0*dlog(x4)**2 
     .              - rli2(dabs(1d0-x5)) - 0.5d0*dlog(x5)**2 
     .              - rli2(dabs(1d0-x6)) - 0.5d0*dlog(x6)**2 
      return
      end



      function xsoftnew(iI,iK,il,im)
      implicit real*8(a-h,o-z)
      slm = sprod(il,im)
      sIK = sprod(iI,iK)
      sIl = sprod(iI,il)
      sKl = sprod(iK,il)
      sIm = sprod(iI,im)
      sKm = sprod(iK,im)
      if (iI.eq.il) sIl = 0d0
      if (iK.eq.im) sKm = 0d0
      xsoftnew = slm*sIK/(sIl+sKl)/(sIm+sKm)
c ---- correct for rounding errors
      if (xsoftnew.gt.1d0) xsoftnew = 1d0
      return
      end


      function sprod(i1,i2)
      implicit real*8(a-h,o-z)
      dimension pa(1:4),pb(1:4)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      if (i1.gt.10) then
         if (i1.gt.20) then
            do i=1,4
               pa(i) = p3(i,i1-20)
            enddo
         else
            do i=1,4
               pa(i) = p4(i,i1-10)
            enddo
         endif
      else
         do i=1,4
            pa(i) = p5(i,i1)
         enddo
      endif
      if (i2.gt.10) then
         if (i2.gt.20) then
            do i=1,4
               pb(i) = p3(i,i2-20)
            enddo
         else
            do i=1,4
               pb(i) = p4(i,i2-10)
            enddo
         endif
      else
         do i=1,4
            pb(i) = p5(i,i2)
         enddo
      endif
      pa(4) = dsqrt(pa(1)**2+pa(2)**2+pa(3)**2)
      pb(4) = dsqrt(pb(1)**2+pb(2)**2+pb(3)**2)
      sprod = 2d0*dot(pa(1),pb(1))
      return
      end
