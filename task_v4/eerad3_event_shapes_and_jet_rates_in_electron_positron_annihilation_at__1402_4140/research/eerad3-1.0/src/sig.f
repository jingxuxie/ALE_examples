c---- cross sections in three-parton, four-parton and five-parton channel
c---- construction of cross sections is described in Section 4 of arXiv:0710:0346
c---- these routines supply the integrands for the vegas integrations in the main program

************************************************************************
*
      function sig3a(x,wgt)
      implicit real*8(a-h,o-z)
      logical plot 
      dimension x(10)
      common /plots/plot
      common /s3/s12,s13,s23
      common /pcut/ppar(4,5)
      common/eventmom3p/pevt3(4,3,1)
      common/eventinv3p/sevt3(3,3,1),ievt3(1)
      parameter(psconv3=3968.80341507837698d0) ! 128*pi^3
      sig3a=0d0
      call phase3ee(x,wtps,ifail)
      if(ifail.eq.1)return
      call fillcommon3pee
      do i=1,3
         do j=1,4
            ppar(j,i) = pevt3(j,i,1)
         enddo
      enddo
      call ecuts(3,var,ipass)
      if(ipass.eq.0)return
      s12 = sevt3(1,2,1)
      s13 = sevt3(1,3,1)
      s23 = sevt3(2,3,1)
      sig3a=psconv3*sig3(s12,s13,s23)
      sig3a=sig3a*wtps*var

      if(plot)then
         call bino(1,sig3a*wgt,3)
      else
         call distrib(wtdis)
         sig3a=sig3a/wtdis
      endif
      return
      end
*
************************************************************************
*
      function sig4a(x,wgt)
      implicit real*8(a-h,o-z)
      logical plot 
      dimension x(10)
      parameter(i1=1,i2=2,i3=3,i4=4,i5=5)
      common /plots/plot
      common /yij4/y(4,4)
      common /pcut/ppar(4,5)
      common /pmom/p(4,5) 
      common/eventmom4p/pevt4(4,4,12)
      common/eventinv4p/sevt4(4,4,12),ievt4(12)
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/nloop,icol,njets
      parameter(psconv4=626728.314440256416d0) ! 2048*pi^5
      sig4asum = 0d0
      sig4a = 0d0
      call phase4ee(x,wtps,ifail)
      wtps = wtps*psconv4
      if (iang.eq.1) wtps=wtps/2d0
      if(ifail.eq.1)return
      call fillcommon4pee
      if (iang.eq.0) ievtmax = 6
      if (iang.eq.1) ievtmax = 12
      do ievt=1,ievtmax
         sig4w = 0d0
         sig3sw = 0d0
         if (ievt4(ievt).eq.1) then
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
               wtplot = wtps*wgt
               sig4w=sig4(i1,i2,i3,i4,wtplot,var)
               sig4w=sig4w*wtps*var
               if (njets.eq.3) then
                  sig3sw=sig3s(i1,i2,i3,i4,wtplot) 
                  sig3sw=sig3sw*wtps
               endif
               sig4w=sig4w-sig3sw
            endif
         endif
         sig4asum = sig4asum + sig4w
      enddo
      sig4a = sig4asum
      return
      end
*
************************************************************************
*
      function sig5a(x,wgt)
      implicit real*8(a-h,o-z)
      dimension x(10)
      logical plot 
      common /plots/plot
      common /phase/ips 
      common /yij5/y(5,5)
      common /pcut/ppar(4,5)
      common /pmom/p(4,5) 
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/nloop,icol,njets
      common/invarang5/sijang5(5,5,4),iacc(4)
      common/eventmom5ap/pevt5a(4,5,120)
      common/eventinv5ap/sevt5a(5,5,120),ievt5a(120)
      common/eventmom5bp/pevt5b(4,5,60)
      common/eventinv5bp/sevt5b(5,5,60),ievt5b(60)
      parameter(i1=1,i2=2,i3=3,i4=4,i5=5)
      parameter(psconv5=2.4742242121947481d7) ! 8192*pi^7
      sig5asum = 0d0
      sig5a=0d0
      if (ips.eq.1) then
         call phase5aee(x,wtps,ifail)
         if(ifail.eq.1)return
         wtps = wtps*psconv5
         call fillcommon5apee
         if (iang.eq.0) ievtmax = 30
         if (iang.eq.1) ievtmax = 120
      elseif (ips.eq.2) then
         call phase5bee(x,wtps,ifail)
         if(ifail.eq.1)return
         wtps = wtps*psconv5
         call fillcommon5bpee
         if (iang.eq.0) ievtmax = 15
         if (iang.eq.1) ievtmax = 60
      endif
      if (iang.eq.1) wtps=wtps/4d0
      do ievt=1,ievtmax
         sig5w=0d0
         sig4sw=0d0
         sig3dsw=0d0
         if (ips.eq.1) ievt5 = ievt5a(ievt)
         if (ips.eq.2) ievt5 = ievt5b(ievt)
         if (ievt5.eq.1) then
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
            if (ipass.ne.0) then
               wtplot=wtps*wgt
               sig5w=sig5(i1,i2,i3,i4,i5,wtplot,var)
               sig5w=sig5w*wtps*var 
               sig4sw=sig4s(i1,i2,i3,i4,i5,wtplot) 
               sig4sw=sig4sw*wtps  
               if (njets.eq.3) then
                  sig3dsw=sig3ds(i1,i2,i3,i4,i5,wtplot)  
                  sig3dsw=sig3dsw*wtps 
               endif
               sig5w=sig5w-sig4sw-sig3dsw
            endif
         endif
         sig5asum = sig5asum + sig5w
      enddo
      sig5a = sig5asum
      return
      end
*
************************************************************************
************************************************************************
*
      function T(s12,s13,s23)
      implicit real*8(a-h,o-z)
      s123=s12+s13+s23
      y12=s12/s123
      y13=s13/s123
      y23=s23/s123

      T=y13/y23+y23/y13+2d0*y12/y13/y23
      return
      end
*
************************************************************************
*
      function sig3(s12,s13,s23) 
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      parameter(zeta2=1.64493406684822644d0)
      parameter(zeta3=1.20205690315959429d0)
      common /qcd/as,ca,cflo,cf,tr,cn 
      common /tcuts/ymin,y0
      common/inphys/nloop,icol,njets
      sig3=0d0
      one=1d0
      if(nloop.eq.-1)one=0d0
      if(nloop.eq.0)then
        sig3=cflo*(as/2d0/pi)*T(s12,s13,s23)
      elseif(abs(nloop).eq.1)then
      ee0=0d0
      ff0=0d0
      ee1=0d0
      ee2=0d0
      ff2=0d0
* N terms
      if(icol.eq.0.or.icol.eq.1)then
c integral of q-g-g antenna (d30, contained in A40s)      
c use (6.11) and d30 as antenna 
        ee0 = 34d0/3d0
c        ee0 = 31d0/6d0
c ff0=A_3^1 (5.13)-4*T
c A31 is defined in aversubnew.f 
c add A_2^1*T according to (9.26)
         ff0=A31(s12,s13,s23)-4d0*T(s12,s13,s23)
*        
      endif
*      
* -1/N terms
      if(icol.eq.0.or.icol.eq.2)then
c integral of q-g-qbar antenna (5.8)      
        ee2 = 19d0/4d0 
c tildeA31=1/2*(FCF+8*T)
c has been ff2=FCF/2 originally
        ff2 = tilda31(s12,s13,s23)-4d0*T(s12,s13,s23)
      endif
*      
* nf terms
c nf=2*tr  
c ff1 comes from (5.17) 
c ee1 corresponds to integral of E30 (6.17) contained in B40s
c ff1 from quark loop is renorm. factor times tree
      if(icol.eq.0.or.icol.eq.3)then
	 ee1 =  -1.d0
         ff1 = 1d0/6d0*dlog(s13*s23)
      endif
        sig3 =cflo*(as/2d0/pi)*
     .   (T(s12,s13,s23)*(one 
     .    +(as/2d0/pi)*(cn*ee0+2d0*tr*(ee1+ff1)-1d0/cn*ee2))
     .    +(as/2d0/pi)*(cn*ff0-1d0/cn*ff2)) 
      elseif(abs(nloop).eq.2)then
      if(nloop.eq.-2)then
        ee0=0d0
        ff0=0d0
        ee1=0d0
        ee2=0d0
        ff2=0d0
	ee4=0d0
	ee4x=0d0
	one=0d0
       finite20 = 0d0
       finite11 = 0d0
       finiteR  = 0d0
      endif
      
      call tjme20(s13,s23,A20a,B20a,C20a,D20a,E20a,F20a,G20a)
      call tjme20(s23,s13,A20b,B20b,C20b,D20b,E20b,F20b,G20b)
      call tjme11(s13,s23,A11a,B11a,C11a,D11a,E11a,F11a)
      call tjme11(s23,s13,A11b,B11b,C11b,D11b,E11b,F11b)

      call tjmeRR(s13,s23,ARa,BRa,CRa,DRa,ERa,FRa)
      call tjmeRR(s23,s13,ARb,BRb,CRb,DRb,ERb,FRb)

      A20 = A20a+A20b
      B20 = B20a+B20b
      C20 = C20a+C20b
      D20 = D20a+D20b
      E20 = E20a+E20b
      F20 = F20a+F20b
      G20 = G20a+G20b
      A11 = A11a+A11b
      B11 = B11a+B11b
      C11 = C11a+C11b
      D11 = D11a+D11b
      E11 = E11a+E11b
      F11 = F11a+F11b
      AR = ARa+ARb
      BR = BRa+BRb
      CR = CRa+CRb
      DR = DRa+DRb
      ER = ERa+ERb
      FR = FRa+FRb
*      finite20 = 
*     $ (9.*A20+B20+1./9.*C20+15.*D20+5./3.*E20+25.*F20-5./33.*G20)/4.
*      finite11 = 
*     $ (9.*A11+B11+1./9.*C11+15.*D11+5./3.*E11+25.*F11)/4.
*      finiteR = 
*     $ (9.*AR+BR+1./9.*CR+15.*DR+5./3.*ER+25.*FR)/4.
c N^2 terms
      if(icol.eq.0.or.icol.eq.1)then
       finite20 = finite20+A20*cn**2
       finite11 = finite11+A11*cn**2
       finiteR  = finiteR+AR*cn**2
       endif
c N^0 terms
      if(icol.eq.0.or.icol.eq.2)then
       finite20 = finite20+B20
       finite11 = finite11+B11
       finiteR  = finiteR+BR 
       endif
c 1/N^2 terms
      if(icol.eq.0.or.icol.eq.3)then
       finite20 = finite20+1.d0/cn**2*C20
       finite11 = finite11+1.d0/cn**2*C11
       finiteR  = finiteR+1.d0/cn**2*CR
       endif
* N*nf terms
      if(icol.eq.0.or.icol.eq.4)then
       finite20 = finite20+D20*2d0*tr*cn
       finite11 = finite11+D11*2d0*tr*cn
       finiteR  = finiteR+DR*2d0*tr*cn
       endif
* nf/N terms
      if(icol.eq.0.or.icol.eq.5)then
       finite20 = finite20+E20*2d0*tr/cn
       finite11 = finite11+E11*2d0*tr/cn
       finiteR  = finiteR+ER*2d0*tr/cn
       endif
* nf^2 terms
c tr=TR*NF=1/2*NF, in hep-ph/0112081 coeff is NF^2, 
c therefore factor 4
      if(icol.eq.0.or.icol.eq.6)then
       finite20 = finite20+4d0*tr**2*F20
       finite11 = finite11+4d0*tr**2*F11
       finiteR  = finiteR+4d0*tr**2*FR
       endif
* nfZ*(4/N-N) terms
       if(icol.eq.0.or.icol.eq.7)then
c       finite20 = finite20+G20
       endif
      
       
        sig3 =cflo*(as/2d0/pi)*
     .   (T(s12,s13,s23)*(one 
     .    +(as/2d0/pi)*(cn*ee0+2d0*tr*ee1-1/cn*ee2))
     .    +(as/2d0/pi)*(cn*ff0-1/cn*ff2)
     .    +(as/2d0/pi)**2*(finite20+finite11+finiteR)/4d0 )

      endif
      return
      end
*************************************************************************
*
*************************************************************************
* sig4
*
* nloop = 1: four-parton tree-level matrix elements
* nloop = 2: four-parton one-loop matrix elements plus VS1a-terms
*************************************************************************
      function sig4(i1,i2,i3,i4,wtplot,var4) 
      implicit real*8(a-h,l,o-z)
      parameter(pi=3.141592653589793238d0)
      parameter(zeta2=1.64493406684822644d0)
      parameter(zeta3=1.20205690315959429d0)
      parameter(zeta4=1.08232323371113819d0)
      logical iprint
      logical plot 
      common /plots/plot
      common/inphys/nloop,icol,njets
      common /qcd/as,ca,cflo,cf,tr,cn 
      common /tcuts/ymin,y0
      common /ps/n1,n2,n3,n4
      common /yij4/y(4,4)
      common /print/iprint

      s12=y(i1,i2)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s23=y(i2,i3)
      s24=y(i2,i4)
      s34=y(i3,i4)

      one=1d0
      s1234=s12+s13+s14+s23+s24+s34
      

      if(nloop.lt.0)one=0d0
      if(abs(nloop).eq.1)then
        treeA34=0d0
        treeAslc=0d0
        treeBpole=0d0
        treeBfin=0d0
        treeA40=0d0
        treeA40b=0d0
        treeA40til=0d0
        treeC40=0d0
        treeB40=0d0
* N terms
	if(icol.eq.0.or.icol.eq.1)then
c A40 is as in (5.27)
	   treeA40=A40(s12,s13,s14,s23,s24,s34)
           treeA40a=treeA40
	   treeA40b=A40(s12,s14,s13,s24,s23,s34)
	endif
* 1/N terms
	if(icol.eq.0.or.icol.eq.2)then
	   treeA40til=A40tilde(s12,s13,s14,s23,s24,s34)
	   treeC40=C40(s12,s13,s14,s23,s24,s34)
	endif
* nf terms
	if(icol.eq.0.or.icol.eq.3)then
	   treeB40=B40(s12,s13,s14,s23,s24,s34)
	endif
c N-part: factor 1/2 statistical times factor 2 for 3<->4 
c => no factor for N-part
c A40tilde-part gets statistical factor 1/2
c NF=2*tr
c C40 contains by def only 2-3-4, for 1-3-4 multiply by 2 
c ( see (9.12) )
c as Bpole was 2*B40, Aslc=2*A40tilde, Bfin=-2*C40
c


        sig4=cflo*(as/2d0/pi)**2/4d0*( 
     .         2d0*cn*treeA40   
     .        -1d0/cn*treeA40til    
     .        +4d0*tr*treeB40         
     .        -4d0/cn*treeC40  ) 
c      
      elseif(abs(nloop).eq.2)then

         calA30 = 19d0/4d0
         calD30 = 34d0/3d0
         calE30 = -1d0
         calF30 = 73d0/4d0
         calG30 = -7d0/6d0

        call setup(s12,s13,s14,s23,s24,s34)
        ee0=0d0
        ff0=0d0
        ee1a=0d0
        ee1b=0d0
        ff1=0d0
        ee2a=0d0
        ee2b=0d0
        ee2x=0d0
        ee4=0d0
        ee4x=0d0
	ee4n=0d0
        ff2=0d0
        ff4=0d0
        ff2x=0d0
        ff4x=0d0
        ee2y=0d0
        ee3a=0d0
        ee3b=0d0
        ee5=0d0
        ff3=0d0
        treeA40=0d0
        treeA40a=0d0
        treeA40b=0d0
        treeA40tilde=0d0
        treeB40=0d0
        treeC40=0d0
!
* N^2, N^0, N*nf terms
       if(icol.eq.0.or.icol.eq.1.or.icol.eq.2.or.icol.eq.4)then
         treeA40=A40(s12,s13,s14,s23,s24,s34)
         treeA40a=treeA40
         treeA40b=A40(s12,s14,s13,s24,s23,s34)
       endif

* N^0, 1/N^2, nf/N terms
       if(icol.eq.0.or.icol.eq.2.or.icol.eq.3
     .    .or.icol.eq.5)then
         treeA40tilde=A40tilde(s12,s13,s14,s23,s24,s34)
	 treeC40=1d0/2d0*(
     .         C40(s12,s13,s14,s23,s24,s34)
     .       + C40(s34,s24,s23,s14,s13,s12) )
       endif

* N*nf, nf/N, nf^2 terms
       if(icol.eq.0.or.icol.eq.4.or.icol.eq.5.or.icol.eq.6)then
         treeB40=B40(s12,s13,s14,s23,s24,s34)
       endif

**************************************************************************
* N^2 terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.1)then
c (6.11) and (7.11)	 
         ee0=calD30+calF30/3d0
         ff0= (fLA34(n1,n2,n3,n4)+fLA34(n1,n2,n4,n3))/2d0
     #        + (-5d0/3d0*(dlog(s13)+dlog(s24)) 
     #        -11d0/6d0*dlog(s34) )*treeA40a
     #        + (-5d0/3d0*(dlog(s14)+dlog(s23)) 
     #        -11d0/6d0*dlog(s34) )*treeA40b

c log terms to account for different subtraction of poles in virtual
c (see (14) of hep-ph/9706297)	
c factor 2 because A34=2*A40
      endif
**************************************************************************
* N^0 terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.2)then
**** terms with fLB34 only work already !
         ee2a=calD30             ! times -2*A40t
         ee2x=2d0*calA30             ! times -4*C40   OK
         ee2b=calA30             ! times -A40a-A40b   ! fLB34
c from (N^2+1)/N  contribution split into 2 parts   
         ee4n=calA30             ! times A40t
        ff2=
     #      fLA(n1,n2,n3,n4)
     #       +fLB34(n1,n2,n3,n4)
     #       +fLB34(n1,n2,n4,n3)
     #	     -fLC(n1,n2,n3,n4)
c correct for (15,16,18) of hep-ph/9706297    
     #   -3d0/2d0*dlog(s12)*2d0*treeA40a     !fLB34
     #   -3d0/2d0*dlog(s12)*2d0*treeA40b     !fLB34
     #  -5d0/3d0*(dlog(s13)+dlog(s24)
     #           +dlog(s23)+dlog(s14))*2d0*treeA40tilde  ! fLA/fLC 
     #  +3d0/2d0*dlog(s12)*2d0*treeA40tilde     ! fLA/fLC
	ff2x=fuc14(n1,n2,n3,n4)-fua14(n1,n2,n3,n4)
c correct for  (12) and (14) of  hep-ph/9609474
c Bfin= -2d0*treeC40    
     #  -(3d0/2d0*dlog(s13)+3d0/2d0*dlog(s24)+
     #     2d0/3d0*dlog(s34)-31d0/9d0)*(-2d0*treeC40)	   
      endif
**************************************************************************
* 1/N^2 terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.3)then
           ee4 = calA30
           ee4x= 2d0*calA30
           ff4=fLB(n1,n2,n3,n4)-3d0*treeA40tilde*log(s12)
           ff4x=fua14(n1,n2,n3,n4)+fub14(n1,n2,n3,n4)
     .          +3d0*(log(s12)+log(s14)+log(s23)
     .          -log(s34)-log(s13)-log(s24))*treeC40
* ee4x from (9.76),(5.8)
c different sign of log(s34) comes from eq.(13) of hep-ph/9609474
c (3*Log(s34)*Bfin must be added)	
	
      endif
**************************************************************************
* NF*N terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.4)then
         ee1a=2d0*calA30
         ee1b=2d0*calG30
         ff1=
c - qqgg terms
     #        fLNF(n1,n2,n3,n4)
     #        + 1d0/6d0*(4d0*dlog(s34))*2d0*treeA40
c - qqqq terms        
     #        + 0.5d0*(fuc12(n2,n1,n3,n4)+ fuc12(n1,n2,n3,n4))
     #        -(2d0/3d0*dlog(s34)-31d0/9d0+3d0/4d0*dlog(s14)
     #        +3d0/4d0*dlog(s23)+3d0/4d0*dlog(s13)+3d0/4d0*dlog(s24))
     #        *2d0*treeB40
      endif
**************************************************************************
* nf/N terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.5)then
           ee3b=calE30
           ee2y=-10d0/9d0+2d0/3d0*dlog(s34)
c   log(s34) term according to (14) of hep-ph/9609474     	
           ee3a=19d0/2d0 
           ff3=0.5d0*( 2d0*fua12(n2,n1,n3,n4)+fub12(n2,n1,n3,n4)
     #          +2d0*fua12(n1,n2,n3,n4)+fub12(n1,n2,n3,n4) )
     #          + (3d0/2d0*dlog(s34)-3d0/2d0*dlog(s12))*2d0*treeB40
     #          + (1d0/6d0*(dlog(s14)+dlog(s23)
     #          + dlog(s13)+dlog(s24)) )*treeA40tilde
        endif
**************************************************************************
* NF^2 terms
**************************************************************************
      if(icol.eq.0.or.icol.eq.6)then
         ee5=-10d0/9d0+2d0/3d0*dlog(s34) 
      endif

c	
      sig4=0d0
      sig4=cflo*(as/2d0/pi)**2/4d0
     .     *(2d0*cn*treeA40                 ! NF*N: twice one ordering
     .     *(one+(as/2d0/pi)*(2d0*tr*ee1b)) 
     .      +1d0*cn*(treeA40a+treeA40b)     ! N^2, N^0: both orderings 
     .     *(one+(as/2d0/pi)*(cn*ee0
     .                       -1d0/cn*ee2b))
     .     -1d0/cn*treeA40tilde  
     .     *(one+(as/2d0/pi)*(2d0*cn*ee2a
     .                       -cn*ee4n
     .                       +4d0*tr*ee3b
     .                       -1d0/cn*ee4))     
     .     +4d0*tr*treeB40        
     .     *(one+(as/2d0/pi)*(cn*ee1a
     .                       -1d0/cn*ee3a 
     .                       +2d0*tr*ee5))
     .     -4d0/cn*treeC40     
     .     *(one+(as/2d0/pi)*(cn*ee2x
     .                       -1d0/cn*ee4x
     .                       +2d0*tr*ee2y)) 
     .     +(as/2d0/pi)/2d0
     .      *(       2d0*cn**2*ff0
     .              -ff2+4d0*ff2x 
     .              +1d0/cn**2*(ff4-4d0*ff4x)
     .              +4d0*cn*tr*ff1
     .              -4d0*tr/cn*ff3  ))
       endif

      if(plot)then
         call bino(1,sig4*wtplot*var4,4)
      else
         call distrib(wtdis)
         sig4=sig4/wtdis
      endif

      return
      end
*
*************************************************************************
*

************************************************************************
*
      function sig3s(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      logical plot 
      parameter(pi=3.141592653589793238d0)
      common /qcd/as,ca,cflo,cf,tr,cn 
      common /tcuts/ymin,y0
      common /plots/plot
      common/inphys/nloop,icol,njets
      common /yij4/y(4,4)

      s12=y(i1,i2)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s23=y(i2,i3)
      s24=y(i2,i4)
      s34=y(i3,i4)

      if(abs(nloop).eq.1)then
      fac=-cflo*(as/2d0/pi)**2/4d0
      wt1=2d0*cn*wtplot*fac 
      wt2=-1/cn*wtplot*fac 
      wt3=4d0*tr*wtplot*fac
      treeA40s=0d0
      treeA40tils=0d0
      treeB40s=0d0
* N terms
      if(icol.eq.0.or.icol.eq.1)then
	 treeA40s=A40s(i1,i2,i3,i4,wt1)
      endif
* -1/N terms
      if(icol.eq.0.or.icol.eq.2)then
	 treeA40tils=A40tildes(i1,i2,i3,i4,wt2)
      endif
* nf terms (nf=2*tr)
      if(icol.eq.0.or.icol.eq.3)then
        treeB40s=B40s(i1,i2,i3,i4,wt3)
      endif
c 
      sig3s=cflo*(as/2d0/pi)**2/4d0
     .          *(2d0*cn*treeA40s
     .          -1d0/cn*treeA40tils
     .          +4d0*tr*treeB40s ) 
c     
      elseif(abs(nloop).eq.2)then
      
      fac=-cflo*(as/2d0/pi)**3/4d0
      wt1=cn**2*wtplot*fac
      wt2=wtplot*fac
      wt3=1d0/cn**2*wtplot*fac
      wt4=4d0*cn*tr*wtplot*fac
      wt5=-4d0/cn*tr*wtplot*fac
      wt6=4d0*tr**2*wtplot*fac
      oneA=0d0
      oneB=0d0
      oneC=0d0
      oneD=0d0
      oneE=0d0
      oneF=0d0
      
* N^2 terms
      if(icol.eq.0.or.icol.eq.1)then
      oneA=VS1bcN2(i1,i2,i3,i4,wt1)
      endif
* N^0 terms
      if(icol.eq.0.or.icol.eq.2)then
      oneB=VS1bcN0(i1,i2,i3,i4,wt2)
      endif
* 1/N^2 terms
      if(icol.eq.0.or.icol.eq.3)then
      oneC=VS1bc1oN2(i1,i2,i3,i4,wt3)
      endif
* NF*N terms
      if(icol.eq.0.or.icol.eq.4)then
      oneD=VS1bcNFN(i1,i2,i3,i4,wt4)
      endif
* nf/N terms
      if(icol.eq.0.or.icol.eq.5)then
      oneE = VS1bcNFoN(i1,i2,i3,i4,wt5)
      endif
* NF^2 terms
      if(icol.eq.0.or.icol.eq.6)then
      oneF=VS1bcNF2(i1,i2,i3,i4,wt6)
      endif
      
*      
c use 4*cf^2 = N^2-2+1/N^2     
      sig3s=cflo*(as/2d0/pi)**3/4d0
     .          *( cn**2*oneA
     .             +1d0*oneB
     .             +1d0/cn**2*oneC 
     .             +4d0*cn*tr*oneD
     .             -4d0/cn*tr*oneE
     .             +4d0*tr**2*oneF)
      endif
      
      return
      end
*
************************************************************************
*
      function sig5(i1,i2,i3,i4,i5,wtplot,var5)
      implicit real*8(a-h,o-z)
      logical plot 
      parameter(pi=3.141592653589793238d0)
      common /qcd/as,ca,cflo,cf,tr,cn 
      common/inphys/nloop,icol,njets
      common /tcuts/ymin,y0
      common /plots/plot
      common /yij5/y(5,5)
 
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

      tt0=0d0
      tt1=0d0
      tt2=0d0
      tt4=0d0
      tt2x=0d0
      tt2y=0d0
      tt3=0d0
      tt4split=0d0
      tt2ysplit=0d0
* N^2  terms
      if(icol.eq.0.or.icol.eq.1)then
        tt0=1d0/2d0*(A345(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
     #             + A345(y12,y15,y14,y13,y25,y24,y23,y45,y35,y34))
c        tt0=A345(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c        tt0=1d0/6d0*(A345(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c     #             + A345(y12,y15,y14,y13,y25,y24,y23,y45,y35,y34)
c     #             + A345(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35)
c     #             + A345(y12,y15,y13,y14,y25,y23,y24,y35,y45,y34)
c     #             + A345(y12,y13,y15,y14,y23,y25,y24,y35,y34,y45)
c     #             + A345(y12,y14,y15,y13,y24,y25,y23,y45,y34,y35))

		
      endif
* N^0  terms 
      if(icol.eq.0.or.icol.eq.2)then
        tt2=(A345p(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
     #	    +A345p(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35))/2d0
c        tt2= A345p(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
	
        tt2x= +AB12354(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)  
     .        +AB14352(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)  
     .        +AB15234(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
     .        +AB15432(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
c
c tt4split and tt2ysplit are equal to tt4 and tt2y, but also 
c included here since (N^2+1)/N^2 has been split into contributions
c to N^0 and 1/N^2 colour factors
       tt4split =A345q(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c include 1<->2 and 3<->4, but do not change overall factor
c as compared to eerad       
       tt2ysplit=(AAAA(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
     #           +AAAA(y12,y24,y23,y25,y14,y13,y15,y34,y45,y35))/2d0	
      endif
* 1/N^2 terms
      if(icol.eq.0.or.icol.eq.3)then
        tt4 =A345q(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
        tt2y= AAAA(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
      endif
* N*nf terms
      if(icol.eq.0.or.icol.eq.4)then
c        tt1=  A14352(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)  
c     .      + A15432(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c        tt1=( A14352(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)  
c     .      + A15432(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c     .      + A14352(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35)  
c     .      + A15432(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35) )/2d0
        tt1=( A14352(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)  
     .      + A15432(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
     .      + A14352(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35)  
     .      + A15432(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35)
     .      + A14352(y12,y23,y24,y25,y13,y14,y15,y34,y35,y45)  
     .      + A15432(y12,y23,y24,y25,y13,y14,y15,y34,y35,y45)
     .      + A14352(y12,y24,y23,y25,y14,y13,y15,y34,y45,y35)  
     .      + A15432(y12,y24,y23,y25,y14,y13,y15,y34,y45,y35) )/4d0
      endif
* nf/N terms
c symmetrize 3<->4
      if(icol.eq.0.or.icol.eq.5)then
        tt3=   B12354(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
     .        +B15234(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c symmetrize 1<->2, 3<->4 
c        tt3=
c     .	(
c     .       +B12354(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
c     .       +B15234(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c     .       +B12354(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35)
c     .       +B15234(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35))/4d0
c     . +(
c     .       +B12354(y12,y23,y24,y25,y13,y14,y15,y34,y35,y45) 
c     .       +B15234(y12,y23,y24,y25,y13,y14,y15,y34,y35,y45)
c     .       +B12354(y12,y24,y23,y25,y14,y13,y15,y34,y45,y35)
c     .       +B15234(y12,y24,y23,y25,y14,y13,y15,y34,y45,y35))/4d0
c symmetrize 3<->4 
c        tt3=(  B12354(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45) 
c     .        +B15234(y12,y13,y14,y15,y23,y24,y25,y34,y35,y45)
c     .        +B12354(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35) 
c     .        +B15234(y12,y14,y13,y15,y24,y23,y25,y34,y45,y35))/2d0     
      endif
      sig5=cflo*(as/2d0/pi)**3/4d0/6d0
     .   *(6d0*cn**2*tt0
     .    -6d0*tt2 
     .    + tt4split
     .    +1d0/cn**2*tt4)
     .    +cflo*(as/2d0/pi)**3/4d0/2d0
     .   *(4d0*cn*tr*tt1
     .    +4d0*tt2x 
     .    -4d0*tt2ysplit
     .    -4d0/cn*tr*tt3
     .    -4d0/cn**2*tt2y)

      if(plot)then
         call bino(1,sig5*wtplot*var5,5)
      else
         call distrib(wtdis)
         sig5=sig5/wtdis
      endif
      return
      end
*
************************************************************************
*
      function sig4s(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      logical plot 
      common /qcd/as,ca,cflo,cf,tr,cn 
      common /tcuts/ymin,y0
      common /plots/plot
      common/inphys/nloop,icol,njets
      common /yij5/y(5,5)
      parameter(pi=3.141592653589793238d0)

c     minus sign in fac to account for overall minus in sig5a       
      fac=-cflo*(as/2d0/pi)**3/4d0
      wt1=6d0*cn**2*wtplot*fac/6d0
      wt2=4d0*cn*tr*wtplot*fac/2d0
      wt3=-6d0*wtplot*fac/6d0
      wt4=1d0/cn**2*wtplot*fac/6d0
      wt5=-4d0*wtplot*fac/2d0
      wt6=-4d0/cn*tr*wtplot*fac/2d0
      wt7=-4d0/cn**2*wtplot*fac/2d0
      wt8=wtplot*fac/6d0
      tt0=0d0
      tt1=0d0
      tt2=0d0
      tt4=0d0
      tt2x=0d0
      tt2y=0d0
      tt3=0d0
      tt4split=0d0
      tt2xy=0d0
* N^2  terms
      if(icol.eq.0.or.icol.eq.1)then
       tt0=
     #	 ( A345s(i1,i2,i3,i4,i5,wt1) 
     #	 + A345s(i1,i2,i5,i4,i3,wt1) )
c       tt0= 2d0*A345s(i1,i2,i3,i4,i5,2d0*wt1) 
c       tt0=
c     #	 ( A345s(i1,i2,i3,i4,i5,wt1/3d0) 
c     #	 + A345s(i1,i2,i5,i4,i3,wt1/3d0) 
c     #	 + A345s(i1,i2,i3,i5,i4,wt1/3d0) 
c     #	 + A345s(i1,i2,i4,i5,i3,wt1/3d0) 
c     #	 + A345s(i1,i2,i4,i3,i5,wt1/3d0) 
c     #	 + A345s(i1,i2,i5,i3,i4,wt1/3d0) )/3d0
      endif
* N^0  terms
c combining AB...s and AAAAs, only 1-5-3 and 4-5-2 antennas of AAAAs
c remain, they are now defined as ACs and included as tt2xy
      if(icol.eq.0.or.icol.eq.2)then
        tt2=A345ps(i1,i2,i3,i4,i5,wt3) 
        tt2xy= ACs(i1,i2,i3,i4,i5,wt5)  
c tt4split is equal to tt4, but has to be 
c included here since (N^2+1)/N^2 has been split into 
c contributions to N^0 and 1/N^2 colour factors
        tt4split=A345qs(i1,i2,i3,i4,i5,wt8) 
      endif
* 1/N^2  terms
      if(icol.eq.0.or.icol.eq.3)then
        tt4=A345qs(i1,i2,i3,i4,i5,wt4)
        tt2y=AAAAs(i1,i2,i3,i4,i5,wt7) 
      endif
* N*nf terms
      if(icol.eq.0.or.icol.eq.4)then
c        tt1=A14352s(i1,i2,i3,i4,i5,wt2)  
c     .     +A15432s(i1,i2,i3,i4,i5,wt2) 

c symmetrise 3<->4
c        tt1= ( A14352s(i1,i2,i3,i4,i5,wt2/2d0)  
c     .        +A15432s(i1,i2,i3,i4,i5,wt2/2d0) 
c     .        +A14352s(i1,i2,i4,i3,i5,wt2/2d0)  
c     .        +A15432s(i1,i2,i4,i3,i5,wt2/2d0) )/2d0 
c symmetrise 1<->2, 3<->4
        tt1= ( A14352s(i1,i2,i3,i4,i5,wt2/4d0)  
     .        +A15432s(i1,i2,i3,i4,i5,wt2/4d0) 
     .        +A14352s(i1,i2,i4,i3,i5,wt2/4d0)  
     .        +A15432s(i1,i2,i4,i3,i5,wt2/4d0) 
     .        +A14352s(i2,i1,i3,i4,i5,wt2/4d0)  
     .        +A15432s(i2,i1,i3,i4,i5,wt2/4d0) 
     .        +A14352s(i2,i1,i4,i3,i5,wt2/4d0)  
     .        +A15432s(i2,i1,i4,i3,i5,wt2/4d0) )/4d0 
      endif
* nf/N terms
      if(icol.eq.0.or.icol.eq.5)then
        tt3= 
     #	     B50cs(i1,i2,i3,i4,i5,wt6) 
     #	    +B50ds(i1,i2,i3,i4,i5,wt6) 
     #	    +B50es(i1,i2,i3,i4,i5,wt6) 
      endif

      sig4s=cflo*(as/2d0/pi)**3/4d0/6d0
     .   *(6d0*cn**2*tt0
     .    -6d0*tt2 
     .    + tt4split
     .    +1d0/cn**2*tt4)
     .    +cflo*(as/2d0/pi)**3/4d0/2d0
     .   *(4d0*cn*tr*tt1
     .    -4d0*tt2xy 
     .    -4d0/cn*tr*tt3
     .    -4d0/cn**2*tt2y)

      return
      end
*
************************************************************************
*
      function sig3ds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      logical plot 
      parameter(pi=3.141592653589793238d0)
      common /qcd/as,ca,cflo,cf,tr,cn 
      common /tcuts/ymin,y0
      common /plots/plot
      common/inphys/nloop,icol,njets
      common /yij5/y(5,5)

      fac=-cflo*(as/2d0/pi)**3/4d0
      wt1=6d0*cn**2*wtplot*fac/6d0
      wt2=4d0*cn*tr*wtplot*fac/2d0
      wt3=-6d0*wtplot*fac/6d0
      wt4=1d0/cn**2*wtplot*fac/6d0
      wt5=4d0*wtplot*fac/2d0
      wt6=-4d0/cn*tr*wtplot*fac/2d0
      wt7=-4d0/cn**2*wtplot*fac/2d0
      wt8=wtplot*fac/6d0
      wt9=-4d0*wtplot*fac/2d0
      tt0=0d0
      tt1=0d0
      tt2=0d0
      tt3=0d0
      tt4=0d0
      tt2x=0d0
      tt2y=0d0
      tt4split=0d0
      tt2ysplit=0d0

* N^2  terms
      if(icol.eq.0.or.icol.eq.1)then
c        tt0= 
c     &	   ( A345dsA40t(i1,i2,i3,i4,i5,wt1/2d0)
c     &      + A345dsD40(i1,i2,i3,i4,i5,wt1/2d0) )/2d0	 
        tt0= 
     &	   ( A345dsA40t(i1,i2,i3,i4,i5,wt1/4d0)
     &      + A345dsD40(i1,i2,i3,i4,i5,wt1/4d0)	 
     &	    + A345dsA40t(i2,i1,i3,i4,i5,wt1/4d0)
     &      + A345dsD40(i2,i1,i3,i4,i5,wt1/4d0) )/4d0	 
c        tt0= 
c     &	   ( A345dsA40t(i1,i2,i3,i4,i5,wt1/6d0)
c     &      + A345dsD40(i1,i2,i3,i4,i5,wt1/6d0)
c     &	    +A345dsA40t(i1,i2,i3,i5,i4,wt1/6d0)
c     &      + A345dsD40(i1,i2,i3,i5,i4,wt1/6d0)
c     &	    +A345dsA40t(i1,i2,i4,i3,i5,wt1/6d0)
c     &      + A345dsD40(i1,i2,i4,i3,i5,wt1/6d0) )/6d0
      endif
*     N^0  terms
      if(icol.eq.0.or.icol.eq.2)then
           tt2 = ( AN0a(i1,i2,i3,i4,i5,wt3/2d0)
     #	        +  AN0a(i1,i2,i4,i3,i5,wt3/2d0) )/2d0 
     #          +( AN0b(i1,i2,i3,i4,i5,wt3/3d0) 
     #          +  AN0b(i1,i2,i4,i3,i5,wt3/3d0) )/3d0 
c for AN0c factor 1/2 is already included in overall prefactor
c cflo*(as/2d0/pi)**3/4d0/2d0     
          tt2x =   AN0c(i1,i2,i3,i4,i5,wt5)
     #	         + AN0c(i1,i2,i4,i3,i5,wt5) 
       tt4split=  A34Qds(i1,i2,i3,i4,i5,wt8) 
       tt2ysplit=-( AAAAds(i1,i2,i3,i4,i5,-wt9/2d0)  
     #          +   AAAAds(i2,i1,i4,i3,i5,-wt9/2d0) )/2d0	    
      endif
* 1/N^2  terms
      if(icol.eq.0.or.icol.eq.3)then
        tt4=A345qds(i1,i2,i3,i4,i5,wt4) 
        tt2y=AAAAds(i1,i2,i3,i4,i5,wt7) 
      endif
* N*nf terms
      if(icol.eq.0.or.icol.eq.4)then
c symmerise 1<->2, 3<->4
        tt1= 1d0/2d0*(
     #      +B50ads(i1,i2,i3,i4,i5,wt2/2d0)
     #	    +B50ads(i2,i1,i4,i3,i5,wt2/2d0)
     #      +B50ads(i1,i2,i4,i3,i5,wt2/2d0)
     #	    +B50ads(i2,i1,i3,i4,i5,wt2/2d0) )
c symmerise 3<->4
c        tt1= 
c     #      +B50ads(i1,i2,i3,i4,i5,wt2)
c     #	    +B50ads(i2,i1,i4,i3,i5,wt2)

      endif
* nf/N terms
      if(icol.eq.0.or.icol.eq.5)then
        tt3= 
     #      +B50cds(i1,i2,i3,i4,i5,wt6)
     #	    +B50dds(i1,i2,i3,i4,i5,wt6)
     #      +B50eds(i1,i2,i3,i4,i5,wt6)
      endif
c
      sig3ds=cflo*(as/2d0/pi)**3/4d0/6d0
     .   *(6d0*cn**2*tt0
     .    -6d0*tt2 
     .    + tt4split
     .    +1d0/cn**2*tt4)
     .    +cflo*(as/2d0/pi)**3/4d0/2d0
     .   *(4d0*cn*tr*tt1
     .    +4d0*tt2x 
     .    -4d0*tt2ysplit
     .    -4d0/cn*tr*tt3
     .    -4d0/cn**2*tt2y)

      return
      end
********************************************
