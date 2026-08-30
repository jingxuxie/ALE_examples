c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains a library of common and special functions,
c     as well as auxiliary routines.

c-----------------------------------------------------------------------
c     Auxilliary subroutines and functions.
c-----------------------------------------------------------------------

c     Calculate spinor and invariant matrices.
      subroutine fillSpinors(npar,p,zA,zB,s)
      implicit none
      integer, intent(in)                   :: npar
      real(8), intent(in)                   :: p(1:4,npar)
      real(8), dimension(npar,npar)         :: s
      complex(8), dimension(npar,npar)      :: zA,zB
      integer                               :: i,j
      integer, dimension(npar)              :: ss
c     Externals.
      real(8), external                     :: dot
      complex(8), external                  :: calczA

      ss = +1
      do i=1,npar
         zA(i,i) = dcmplx(0d0)
         zB(i,i) = dcmplx(0d0)
         do j=i+1,npar
            zA(i,j) = calczA(npar,p,i,j)
            zA(j,i) = -zA(i,j)
            zB(i,j) = -ss(i)*ss(j)*dconjg(zA(i,j))
            zB(j,i) = -zB(i,j)
            s(i,j)  = zA(i,j)*zB(j,i)
            s(j,i)  = s(i,j)
         end do
      end do

      return
      end

************************************************************************

c     Calculate a single zA spinor.
      complex(8) function calczA(npar,p,ia,ib)
      implicit none
      integer, intent(in)            :: npar,ia,ib
      real(8), intent(in)            :: p(1:4,npar)
      real(8), dimension(4)          :: a,b
      real(8)                        :: at2,at,ap,am, bt2,bt,bp,bm
      complex(8)                     :: zea,zeb
      integer                        :: i1,i2,i3
      integer, parameter             :: iaxis = 2

      select case (iaxis)
      case(1)
c     Lightlike rotation along x direction.
         i1=2
         i2=3
         i3=1
      case(2)
c     Lightlike rotation along y direction.
         i1=3
         i2=1
         i3=2
      case(3)
c     Lightlike rotation along z direction.
         i1=1
         i2=2
         i3=3
      case default
         stop "calczA: invalid axis"
      end select

      a = p(:,ia)
      b = p(:,ib)

      at2 = a(i1)**2 + a(i2)**2
      ap = a(4) + a(i3)
      if (ap < 0.5d0*a(4)) ap = at2 / (a(4) - a(i3))

      bt2 = b(i1)**2 + b(i2)**2
      bp = b(4) + b(i3)
      if (bp < 0.5d0*b(4)) bp  = bt2 / (b(4) - b(i3))

      if ( ap==0d0 .or. bp==0d0 ) then
c     Treat the special case separately.
         if(ap == 0d0) then
            am = a(4) - a(i3)
            zea = sqrt(am*bp) * dcmplx(0d0,1d0)
         else
            zea = dcmplx(a(i2),-a(i1)) * sqrt(bp/ap)
         endif
         if(bp == 0d0) then
            bm = b(4) - b(i3)
            zeb = sqrt(bm*ap) * dcmplx(0d0,1d0)
         else
            zeb = dcmplx(b(i2),-b(i1)) * sqrt(ap/bp)
         endif
         calczA = zea-zeb
      else
         calczA = (dcmplx(a(i2),-a(i1))*bp - dcmplx(b(i2),-b(i1))*ap)
     .        /sqrt(ap*bp)
      end if
c     Global phase to match old eval_zA in NNLOJET.
      calczA = calczA * dcmplx(0d0,+1d0)
c     Cross initial states because we use the convention of all ingoing.
      if (ia==1 .or. ib==1) calczA = calczA * dcmplx(0d0,+1d0)
      if (ia==2 .or. ib==2) calczA = calczA * dcmplx(0d0,+1d0)

      return
      end

c-----------------------------------------------------------------------
c     Common and special functions.
c-----------------------------------------------------------------------

c     Four-vector dot product.
      function dot(a,b)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4)
      dot=a(4)*b(4)-a(1)*b(1)-a(2)*b(2)-a(3)*b(3)
      return
      end

************************************************************************

c     Define Heaviside theta function (=1 for x>0) and (0 for x < 0).
      function htheta(x)
      implicit none
      real*8, intent(in) :: x
      real*8             :: htheta
      htheta = 0.5d0+0.5d0*sign(1d0,x)
      return
      end

************************************************************************

c     MCFM's lnrat function with lnrat(x,y)=log(x-i*ep)-log(y-i*ep).
c     This function is hard-wired for sign of epsilon. We must adjust
c     sign of x and y to get the right sign for epsilon.
      function lnrat(x,y)
      implicit none
      integer, parameter     :: dp = selected_real_kind(15)
      real*8, parameter      :: pi = 3.141592653589793238d0
      complex(dp), parameter :: impi=(0d0,pi)
      complex(dp)            :: lnrat
      real(dp)               :: x,y,htheta
c     Define Heaviside theta function (=1 for x>0) and (0 for x < 0).
      htheta(x)=0.5d0+0.5d0*sign(1d0,x)
      lnrat = cmplx(log(abs(x/y)),0d0,kind=dp)
     .     - impi*(htheta(-x)-htheta(-y))
      return
      end

************************************************************************

c     Real dilogarithm function, valid also for negative x.
      double precision function ddilog(X)
      double precision X,Y,T,S,A,PI3,PI6,ZERO,ONE,HALF,MALF,MONE,MTWO
      double precision C(0:18),H,ALFA,B0,B1,B2

      data ZERO /0.0D0/, ONE /1.0D0/
      data HALF /0.5D0/, MALF /-0.5D0/, MONE /-1.0D0/, MTWO /-2.0D0/
      data PI3 /3.289868133696453D0/, PI6 /1.644934066848226D0/

      data C( 0) / 0.4299669356081370D0/
      data C( 1) / 0.4097598753307711D0/
      data C( 2) /-0.0185884366501460D0/
      data C( 3) / 0.0014575108406227D0/
      data C( 4) /-0.0001430418444234D0/
      data C( 5) / 0.0000158841554188D0/
      data C( 6) /-0.0000019078495939D0/
      data C( 7) / 0.0000002419518085D0/
      data C( 8) /-0.0000000319334127D0/
      data C( 9) / 0.0000000043454506D0/
      data C(10) /-0.0000000006057848D0/
      data C(11) / 0.0000000000861210D0/
      data C(12) /-0.0000000000124433D0/
      data C(13) / 0.0000000000018226D0/
      data C(14) /-0.0000000000002701D0/
      data C(15) / 0.0000000000000404D0/
      data C(16) /-0.0000000000000061D0/
      data C(17) / 0.0000000000000009D0/
      data C(18) /-0.0000000000000001D0/

      if(X .eq. ONE) then
       ddilog=PI6
       return
      else if(X .eq. MONE) then
       ddilog=MALF*PI6
       return
      END if
      T=-X
      if(T .le. MTWO) then
       Y=MONE/(ONE+T)
       S=ONE
       A=-PI3+HALF*(LOG(-T)**2-LOG(ONE+ONE/T)**2)
      else if(T .lt. MONE) then
       Y=MONE-T
       S=MONE
       A=LOG(-T)
       A=-PI6+A*(A+LOG(ONE+ONE/T))
      else if(T .le. MALF) then
       Y=(MONE-T)/T
       S=ONE
       A=LOG(-T)
       A=-PI6+A*(MALF*A+LOG(ONE+T))
      else if(T .lt. ZERO) then
       Y=-T/(ONE+T)
       S=MONE
       A=HALF*LOG(ONE+T)**2
      else if(T .le. ONE) then
       Y=T
       S=ONE
       A=ZERO
      else
       Y=ONE/T
       S=MONE
       A=PI6+HALF*LOG(T)**2
      end if

      H=Y+Y-ONE
      ALFA=H+H
      B1=ZERO
      B2=ZERO
      do 1 I = 18,0,-1
      B0=C(I)+ALFA*B1-B2
      B2=B1
    1 B1=B0
      ddilog=-(S*(B0-H*B2)+A)
      return
      END

************************************************************************

c     Real dilogarithm function for 0 <= x <= 1.
      function rli2(x)
      implicit real*8(a-h,o-z)
      parameter(a1 = -0.250000000000000d0)
      parameter(a2 = -0.111111111111111d0)
      parameter(a3 = -0.010000000000000d0)
      parameter(a4 = -0.0170068027210884d0)
      parameter(a5 = -0.0194444444444444d0)
      parameter(a6 = -0.0206611570247934d0)
      parameter(a7 = -0.0214173006480699d0)
      parameter(a8 = -0.02194886637723d0)
      parameter(a9 = -0.0220893589994137d0)
      parameter(a10 = -0.0229303207720760d0)
      parameter(zeta2 =  1.644934066848226d0)
      if(x.gt.1d0)then
         write(*,*)' argument greater than 1 passed to li2'
         rli2=0d0
         return
      elseif(x.lt.0d0)then
         write(*,*)' argument less than 0 passed to li2'
         rli2=0d0
         return
      elseif(x.eq.1d0)then
         rli2=zeta2
         return
      elseif(x.eq.0d0)then
         rli2=0d0
         return
      elseif(x.gt.0.5d0)then
         y=1d0-x
         z=-log(1d0-y)
         z2=z*z
         rli2=-z*(1d0+a1*z*(1d0+a2*z*(1d0+a3*z2*(1d0+a4*z2*
     .        (1d0+a5*z2*(1d0+a6*z2*(1d0+a7*z2*(1d0+a8*z2*(1d0+a9*z2*
     .        (1d0+a10*z2))))))))))
     .        +zeta2-log(x)*log(1d0-x)
         return
      elseif(x.le.0.5d0)then
         y=x
         z=-log(1d0-y)
         z2=z*z
         rli2=z*(1d0+a1*z*(1d0+a2*z*(1d0+a3*z2*(1d0+a4*z2*
     .        (1d0+a5*z2*(1d0+a6*z2*(1d0+a7*z2*(1d0+a8*z2*(1d0+a9*z2*
     .        (1d0+a10*z2))))))))))
         return
      endif
      rli2=0d0
      return
      end

************************************************************************

c     Complex dilogarithm.
      double complex  function cli2(z)
      implicit none
      double complex ris, z, bsli2_inside,bsli2_outside, wcli2
      double complex zlocal
      double precision zabs, pi, zeta2, border, tiny, arg

      pi=3.1415926535897932385D0
      zeta2=pi**2/6d0

      border = 0.3d0
      tiny = 1d-14
      zabs = abs(z)
      zlocal=z

      if (zabs.gt.1d0+tiny) then
         ris=-wcli2(1d0/z)-zeta2-0.5d0*log(-z)**2
      elseif (zabs.le.border) then
         ris=bsli2_inside(z)
      else
         if (zabs.gt.1d0) then
            arg=atan2(dimag(zlocal),dreal(zlocal))
            zlocal=dcmplx(cos(arg),sin(arg))
         endif
         ris=bsli2_outside(zlocal)
      endif

      cli2=ris
      return
      end

************************************************************************

c     Recursion.
      double complex function wcli2(z)
      implicit none
      double complex z, cli2
      
      wcli2 =  cli2(z)
      
      return
      end

************************************************************************

c     Expansion of dilogarithm in y = - log(1-z) with Bernoulli numbers.
      double  complex function bsli2_inside(z)
      implicit none
      integer i, Nmax
      double complex ris, z, zb
      double precision bern(11)

c     bern(i+1) = BernoulliB(2i)/(2i)!
      data bern /1.D0,0.8333333333333333D-1,-0.1388888888888889D-2
     &,0.3306878306878307D-4,-0.8267195767195767D-6,0.208767569878681D-7
     &,-0.5284190138687493D-9,0.1338253653068468D-10
     &,-0.3389680296322583D-12,0.8586062056277845D-14
     &,-0.2174868698558062D-15/

c     This is half the order we want
c     (beacuse odd bernoulli numbers are zero except
c     BernoulliB(1)=-0.5d0).
      parameter (Nmax=11)

      zb = dcmplx(1d0,0d0)-z
      zb = -log(zb)
      ris = -zb**2/4d0          !accounting for BernoulliB(1) = -0.5d0
      do i=1,Nmax
         ris = ris + zb**(2*i-1)*bern(i)/(2*i-1)
      enddo

      bsli2_inside = ris

      return
      end

************************************************************************

c     Expansion of the dilogarithm in log(z) with Zeta values
c     Used for border < |z| < 1.
      double  complex function bsli2_outside(z)
      implicit none
      integer i, Nmax
      double complex ris, z, zb
      double precision zeta(29),zeta0,zeta2

c     zeta(i) = Zeta(2-2i-1)/(2i+1)! i.e. Zeta(-1)/6, Zeta(-3)/120, Zeta(-5)/7!....
      data zeta /-0.01388888888888889d0,0.00006944444444444444d0
     &,-7.873519778281683d-7,1.148221634332745d-8,-1.897886998897100d-10
     &,3.387301370953521d-12,-6.372636443183180d-14,1.246205991295067d-
     &15,-2.510544460899955d-17,5.178258806090624d-19,-1.088735736830085
     &d-20,2.325744114302087d-22,-5.035195213147390d-24,1.10264992943812
     &2d-25,-2.438658550900734d-27,5.440142678856252d-29,-1.222834013121
     &735d-30,2.767263468967951d-32,-6.300090591832014d-34,1.44208683884
     &1848d-35,-3.317093999159543d-37,7.663913557920658d-39,-1.777871473
     &383066d-40,4.139605898234137d-42,-9.671557036081102d-44,2.26671870
     &1676613d-45,-5.327956311328254d-47,1.255724838956433d-48,-2.967000
     &542247094d-50/
c     This is half the order we want
c     (because even zetaval2 are zero except for 0,2).
      parameter (Nmax=29)
      parameter (zeta0 = 1.644934066848226d0)
      parameter (zeta2 = -0.2500000000000000d0)

      zb = log(z)
      ris = dcmplx(zeta0, 0d0) + zb*(1d0 -log(-zb))
     &     + zb**2*zeta2
      do i=1,Nmax
         ris = ris + zb**(2*i+1)*zeta(i)
      enddo

      bsli2_outside=ris

      return
      end

c-----------------------------------------------------------------------
c     Vegas routines for up to five final-state particles.
c-----------------------------------------------------------------------

c     SUBROUTINE PERFORMS N-DIMENSIONAL MONTE CARLO INTEG'N
c     - BY G.P. LEPAGE   SEPT 1976/(REV)APR 1978
      SUBROUTINE vegas5(ISTAT,FXN,ip,AVGI,SD,CHI2A)
      IMPLICIT REAL*8(A-H,O-Z)
      logical fi
      external FXN
      character ch*3,ctype*3,gridfile*19
      character fname*20,prefix*8,suffix*4
      parameter(ipmx=2)
      COMMON/BVEG5/NDIM(ipmx),NCALL(ipmx),NPRN
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/outfile/fname,prefix,suffix
      DIMENSION XI(ipmx,50,10),D(50,10),DI(50,10),XIN(50)
     1   ,R(50),DT(10),X(10),KG(10),IA(10)
      dimension si(ipmx),si2(ipmx),swgt(ipmx),schi(ipmx),calls(ipmx)
     1   ,DXG(ipmx),DV2G(ipmx),XND(ipmx),XJAC(ipmx)
*ng
      dimension GSI(ipmx),GSI2(ipmx),GSWGT(ipmx) 
*ng
      dimension nd(ipmx),ng(ipmx),npg(ipmx),it(ipmx),mds(ipmx)
     1   ,ndo(ipmx),ndm(ipmx)
      REAL*8 QRAN(10)
      DATA NDMX/50/,ALPH/1.5D0/,ONE/1D0/ 
      ctype='.'//char(iaver+48)
      if(iaver.eq.0)ctype='.A'
      if(ip.eq.1)ch='v5a'
      if(ip.eq.2)ch='v5b'
      gridfile = fname(1:6)//fname(12:20)
      gridfile = trim(gridfile)//ch//trim(ctype)
C
      if(istat.eq.0.or.istat.eq.1.or.istat.eq.2)then
c
c         initialize cumulative variables 
c
        IT(ip)=0
        SI(ip)  =0d0
        SI2(ip) =0d0
        SWGT(ip)=0d0
        SCHI(ip)=0d0
*ng
        GSI(ip)  =0d0
        GSI2(ip) =0d0
        GSWGT(ip)=0d0
*mg
        ND(ip)=NDMX
        NG(ip)=1
        MDS(ip)=1
        IF(MDS(ip).ne.0)then
          NG(ip)=(NCALL(ip)/2d0)**(1d0/NDIM(ip))
          MDS(ip)=1
          IF((2*NG(ip)-NDMX).ge.0)then
            MDS(ip)=-1
            NPG(ip)=NG(ip)/NDMX+1
            ND(ip)=NG(ip)/NPG(ip)
            NG(ip)=NPG(ip)*ND(ip)
          endif
        endif
        K=NG(ip)**NDIM(ip)
        NPG(ip)=NCALL(ip)/K
        IF(NPG(ip).LT.2) NPG(ip)=2
        CALLS(ip)=NPG(ip)*K
        DXG(ip)=ONE/NG(ip)
        DV2G(ip)=(CALLS(ip)*DXG(ip)**NDIM(ip))**2
     .         /NPG(ip)/NPG(ip)/(NPG(ip)-ONE)
        XND(ip)=ND(ip)
        NDM(ip)=ND(ip)-1
        DXG(ip)=DXG(ip)*XND(ip)
        XJAC(ip)=ONE/CALLS(ip)
        IF(NPRN.NE.0.and.istat.ne.0.and.idebug.eq.1)
     .       write(6,200) NDIM(ip),CALLS(ip)

      endif
      if(istat.eq.0)then
C
C   read in grid   
C
         inquire(file=gridfile,EXIST=fi)
         if (.not.fi)then
            write(6,*) ''
            write(6,*) 'Missing vegas grid file: ',gridfile
            write(6,*) ''
            stop
         endif
         open(unit=3,file=gridfile,status='unknown')
         write(6,*)' Reading in vegas grid from ',gridfile 
         do j=1,ndim(ip)
            read(3,*) jj,(xi(ip,i,j),i=1,nd(ip))
         enddo
         close(3)
         NDO(ip)=ND(ip)
         return
      elseif(istat.eq.1)then
C
C   construct uniform grid  
C
        RC=1d0/XND(ip)
        DO  J=1,NDIM(ip)
          XI(ip,1,j)=1d0
          K=0
          XN=0d0
          DR=0d0
          I=0
4         K=K+1
          DR=DR+ONE
          XO=XN
          XN=XI(ip,K,J)
5         IF(RC.GT.DR) GO TO 4
          I=I+1
          DR=DR-RC
          XIN(I)=XN-(XN-XO)*DR
          IF(I.LT.NDM(ip)) GO TO 5
          DO  I=1,NDM(ip)
            XI(ip,I,J)=XIN(I)
          enddo
          XI(ip,ND(ip),J)=ONE
        enddo
        NDO(ip)=ND(ip)
        return
C
      elseif(istat.eq.2)then
C
C   rescale refined grid to new ND value - preserve bin density
C
        if(nd(ip).ne.ndo(ip))then
          RC=NDO(ip)/XND(ip)
          DO  J=1,NDIM(ip)
            K=0
            XN=0d0
            DR=0d0
            I=0
6           K=K+1
            DR=DR+ONE
            XO=XN
            XN=XI(ip,K,J)
7           IF(RC.GT.DR) GO TO 6
            I=I+1
            DR=DR-RC
            XIN(I)=XN-(XN-XO)*DR
            IF(I.LT.NDM(ip)) GO TO 7
            DO  I=1,NDM(ip)
              XI(ip,I,J)=XIN(I)
            enddo
            XI(ip,ND(ip),J)=ONE
          enddo
        endif
C
        return
C
      elseif(istat.eq.3.or.istat.eq.4)then
c
c    main integration loop
c         
        IT(ip)=IT(ip)+1
        TI =0d0
        TSI=0d0
*ng
        GTI =0d0
        GTSI=0d0
*ng
        DO J=1,NDIM(ip)
          KG(J)=1
          DO I=1,ND(ip)
           D (I,J)=0d0
           DI(I,J)=0d0
          enddo
        enddo
C
11      FB=0d0
        F2B=0d0
        K=0
12      K=K+1
        do j=1,ndim(ip)
          qran(j)=rn(1)
        enddo        
        WGT=XJAC(ip)
        DO J=1,NDIM(ip)
          XN=(KG(J)-QRAN(J))*DXG(ip)+ONE
          IA(J)=XN
          IF(IA(J).GT.1)then
            XO=XI(ip,IA(J),J)-XI(ip,IA(J)-1,J)
            RC=XI(ip,IA(J)-1,J)+(XN-IA(J))*XO
          else
            XO=XI(ip,IA(J),J)
            RC=(XN-IA(J))*XO
          endif
          X(J)=RC
          WGT=WGT*XO*XND(ip)
        enddo
C
        F=WGT
        F=F*FXN(X,WGT)
        F2=F*F
        FB=FB+F
        F2B=F2B+F2
        DO J=1,NDIM(ip)
          DI(IA(J),J)=DI(IA(J),J)+F
          IF(MDS(ip).GE.0) D(IA(J),J)=D(IA(J),J)+F2
        enddo
        IF(K.LT.NPG(ip)) GO TO 12
C
*ng

        GTI=GTI+FB
        GTSI=GTSI+F2B
*ng

        F2B=DSQRT(F2B*NPG(ip))
        F2B=(F2B-FB)*(F2B+FB)
        TI=TI+FB
        TSI=TSI+F2B
        IF(MDS(ip).lt.0) then
          DO J=1,NDIM(ip)
            D(IA(J),J)=D(IA(J),J)+F2B
          enddo
        endif
        K=NDIM(ip)
19      KG(K)=MOD(KG(K),NG(ip))+1
        IF(KG(K).NE.1) GO TO 11
        K=K-1
        IF(K.GT.0) GO TO 19
C
C   FINAL RESULTS for THIS ITERATION
C
        TSI=TSI*DV2G(ip)
        TI2=TI*TI
        WGT=TI2/TSI
        SI(ip)=SI(ip)+TI*WGT
        SI2(ip)=SI2(ip)+TI2
        SWGT(ip)=SWGT(ip)+WGT
        SCHI(ip)=SCHI(ip)+TI2*WGT
        AVGI=SI(ip)/SWGT(ip)
        SD=SWGT(ip)*IT(ip)/SI2(ip)
        CHI2A=SD*(SCHI(ip)/SWGT(ip)-AVGI*AVGI)/(IT(ip)-.999d0)
        SD=DSQRT(ONE/SD)
*ng
        GTSI=(GTSI*CALLS(ip)-GTI**2)/CALLS(ip)
        GSI(ip)=GSI(ip)+GTI/GTSI
        GSWGT(ip)=GSWGT(ip)+1d0/GTSI
        GAVGI=GSI(ip)/GSWGT(ip)
        GSD=DSQRT(ONE/GSWGT(ip))
*ng
        IF(NPRN.ne.0) then
           TSI=DSQRT(TSI)
           if (idebug.eq.1) write(6,201) IT(ip),ip,TI,TSI,AVGI,SD,CHI2A
*ng
           GTSI=DSQRT(GTSI)
           if (idebug.eq.1) write(6,201) IT(ip),ip,GTI,GTSI,GAVGI,GSD
           AVGI=GAVGI
           SD=GSD
*ng
        endif
      endif
C
C   REFINE GRID
C
      if(istat.eq.3)then
       DO J=1,NDIM(ip)
         XO=D(1,J)
         XN=D(2,J)
         D(1,J)=(XO+XN)/2d0
         DT(J)=D(1,J)
         DO I=2,NDM(ip)
           D(I,J)=XO+XN
           XO=XN
           XN=D(I+1,J)
           D(I,J)=(D(I,J)+XN)/3d0
           DT(J)=DT(J)+D(I,J)
         enddo
         D(ND(ip),J)=(XN+XO)/2d0
         DT(J)=DT(J)+D(ND(ip),J)
       enddo
C
        DO 28 J=1,NDIM(ip)
        RC=0d0
        DO 24 I=1,ND(ip)
        R(I)=0d0
        IF(D(I,J).LE.0d0) GO TO 24
        XO=DT(J)/D(I,J)
        R(I)=((XO-ONE)/XO/DLOG(XO))**ALPH
24      RC=RC+R(I)
        RC=RC/XND(ip)
        K=0
        XN=0d0
        DR=XN
        I=K
25      K=K+1
        DR=DR+R(K)
        XO=XN
        XN=XI(ip,K,J)
26      IF(RC.GT.DR) GO TO 25
        I=I+1
        DR=DR-RC
        XIN(I)=XN-(XN-XO)*DR/R(K)
        IF(I.LT.NDM(ip)) GO TO 26
        DO 27 I=1,NDM(ip)
27      XI(ip,I,J)=XIN(I)
28      XI(ip,ND(ip),J)=ONE
        open(unit=2,file=gridfile,status='unknown')
        write(6,*) 'Writing vegas grid to ',gridfile 
        do j=1,ndim(ip)
          write(2,*) j,(xi(ip,i,j),i=1,nd(ip))
        enddo
        close(2)
        return
      endif
C
 200  FORMAT(' Input parameters for vegas 5: ndim = ',I2,
     1     ',  nshot = ',F10.0)
 201  FORMAT(i4,'(',i2,') ',g15.7,g13.6,g15.7,g13.6,f7.2)
 202  FORMAT(' DATA for AXIS',I2 / ' ',6X,'X',7X,'  DELT I  ',
     1    2X,' CONV''CE  ',11X,'X',7X,'  DELT I  ',2X,' CONV''CE  '
     2   ,11X,'X',7X,'  DELT I  ',2X,' CONV''CE  ' /
     2    (' ',3G12.4,5X,3G12.4,5X,3G12.4))
      RETURN
      END

************************************************************************

c     SUBROUTINE PERFORMS N-DIMENSIONAL MONTE CARLO INTEG'N
c     - BY G.P. LEPAGE   SEPT 1976/(REV)APR 1978
      SUBROUTINE vegas4a(ISTAT,FXN,ip,AVGI,SD,CHI2A)
      IMPLICIT REAL*8(A-H,O-Z)
      logical fi
      external FXN
      parameter(ipmx=1)
      COMMON/BVEG4/NDIM(ipmx),NCALL(ipmx),NPRN
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/outfile/fname,prefix,suffix
      DIMENSION XI(ipmx,50,10),D(50,10),DI(50,10),XIN(50)
     1   ,R(50),DT(10),X(10),KG(10),IA(10)
      dimension si(ipmx),si2(ipmx),swgt(ipmx),schi(ipmx),calls(ipmx)
     1   ,DXG(ipmx),DV2G(ipmx),XND(ipmx),XJAC(ipmx)
*ng
      dimension GSI(ipmx),GSI2(ipmx),GSWGT(ipmx) 
*ng
      dimension nd(ipmx),ng(ipmx),npg(ipmx),it(ipmx),mds(ipmx)
     1   ,ndo(ipmx),ndm(ipmx)
      REAL*8 QRAN(10)
      DATA NDMX/50/,ALPH/1.5D0/,ONE/1D0/ 
      character ch*3,ctype*3,gridfile*19
      character fname*20,prefix*8,suffix*4
      ctype='.'//char(iaver+48)
      if(iaver.eq.0)ctype='.A'
      if(ip.eq. 1)ch='v4a'
      gridfile = fname(1:6)//fname(12:20)
      gridfile = trim(gridfile)//ch//trim(ctype)

C
      if(istat.eq.0.or.istat.eq.1.or.istat.eq.2)then
c
c         initialize cumulative variables 
c
        IT(ip)=0
        SI(ip)  =0d0
        SI2(ip) =0d0
        SWGT(ip)=0d0
        SCHI(ip)=0d0
*ng
        GSI(ip)  =0d0
        GSI2(ip) =0d0
        GSWGT(ip)=0d0
*mg
        ND(ip)=NDMX
        NG(ip)=1
        MDS(ip)=1
        IF(MDS(ip).ne.0)then
          NG(ip)=(NCALL(ip)/2d0)**(1d0/NDIM(ip))
          MDS(ip)=1
          IF((2*NG(ip)-NDMX).ge.0)then
            MDS(ip)=-1
            NPG(ip)=NG(ip)/NDMX+1
            ND(ip)=NG(ip)/NPG(ip)
            NG(ip)=NPG(ip)*ND(ip)
          endif
        endif
        K=NG(ip)**NDIM(ip)
        NPG(ip)=NCALL(ip)/K
        IF(NPG(ip).LT.2) NPG(ip)=2
        CALLS(ip)=NPG(ip)*K
        DXG(ip)=ONE/NG(ip)
        DV2G(ip)=(CALLS(ip)*DXG(ip)**NDIM(ip))**2
     .         /NPG(ip)/NPG(ip)/(NPG(ip)-ONE)
        XND(ip)=ND(ip)
        NDM(ip)=ND(ip)-1
        DXG(ip)=DXG(ip)*XND(ip)
        XJAC(ip)=ONE/CALLS(ip)
        IF(NPRN.NE.0.and.istat.ne.0.and.idebug.eq.1)
     .       write(6,200) NDIM(ip),CALLS(ip) 

      endif
      if(istat.eq.0)then
C
C   read in grid   
C
         inquire(file=gridfile,EXIST=fi)
         if (.not.fi)then
            write(6,*) ''
            write(6,*) 'Missing vegas grid file: ',gridfile
            write(6,*) ''
            stop
         endif
         open(unit=3,file=gridfile,status='unknown')
         write(6,*)' Reading in vegas grid from ',gridfile 
         do j=1,ndim(ip)
            read(3,*) jj,(xi(ip,i,j),i=1,nd(ip))
         enddo
         close(3)
         NDO(ip)=ND(ip)
         return
      elseif(istat.eq.1)then
C
C   construct uniform grid  
C
        RC=1d0/XND(ip)
        DO  J=1,NDIM(ip)
          XI(ip,1,j)=1d0
          K=0
          XN=0d0
          DR=0d0
          I=0
4         K=K+1
          DR=DR+ONE
          XO=XN
          XN=XI(ip,K,J)
5         IF(RC.GT.DR) GO TO 4
          I=I+1
          DR=DR-RC
          XIN(I)=XN-(XN-XO)*DR
          IF(I.LT.NDM(ip)) GO TO 5
          DO  I=1,NDM(ip)
            XI(ip,I,J)=XIN(I)
          enddo
          XI(ip,ND(ip),J)=ONE
        enddo
        NDO(ip)=ND(ip)
        return
C
      elseif(istat.eq.2)then
C
C   rescale refined grid to new ND value - preserve bin density
C
        if(nd(ip).ne.ndo(ip))then
          RC=NDO(ip)/XND(ip)
          DO  J=1,NDIM(ip)
            K=0
            XN=0d0
            DR=0d0
            I=0
6           K=K+1
            DR=DR+ONE
            XO=XN
            XN=XI(ip,K,J)
7           IF(RC.GT.DR) GO TO 6
            I=I+1
            DR=DR-RC
            XIN(I)=XN-(XN-XO)*DR
            IF(I.LT.NDM(ip)) GO TO 7
            DO  I=1,NDM(ip)
              XI(ip,I,J)=XIN(I)
            enddo
            XI(ip,ND(ip),J)=ONE
          enddo
        endif
        return
C
      elseif(istat.eq.3.or.istat.eq.4)then
c
c    main integration loop
c         
        IT(ip)=IT(ip)+1
        TI =0d0
        TSI=0d0
*ng
        GTI =0d0
        GTSI=0d0
*ng
        DO J=1,NDIM(ip)
          KG(J)=1
          DO I=1,ND(ip)
           D (I,J)=0d0
           DI(I,J)=0d0
          enddo
        enddo
C
11      FB=0d0
        F2B=0d0
        K=0
12      K=K+1
        do j=1,ndim(ip)
          qran(j)=rn(1)
        enddo        
        WGT=XJAC(ip)
        DO J=1,NDIM(ip)
          XN=(KG(J)-QRAN(J))*DXG(ip)+ONE
          IA(J)=XN
          IF(IA(J).GT.1)then
            XO=XI(ip,IA(J),J)-XI(ip,IA(J)-1,J)
            RC=XI(ip,IA(J)-1,J)+(XN-IA(J))*XO
          else
            XO=XI(ip,IA(J),J)
            RC=(XN-IA(J))*XO
          endif
          X(J)=RC
          WGT=WGT*XO*XND(ip)
        enddo
C
        F=WGT
        F=F*FXN(X,WGT)
        F2=F*F
        FB=FB+F
        F2B=F2B+F2
        DO J=1,NDIM(ip)
          DI(IA(J),J)=DI(IA(J),J)+F
          IF(MDS(ip).GE.0) D(IA(J),J)=D(IA(J),J)+F2
        enddo
        IF(K.LT.NPG(ip)) GO TO 12
C
*ng

        GTI=GTI+FB
        GTSI=GTSI+F2B
*ng
        F2B=DSQRT(F2B*NPG(ip))
        F2B=(F2B-FB)*(F2B+FB)
        TI=TI+FB
        TSI=TSI+F2B
        IF(MDS(ip).lt.0) then
          DO J=1,NDIM(ip)
            D(IA(J),J)=D(IA(J),J)+F2B
          enddo
        endif
        K=NDIM(ip)
19      KG(K)=MOD(KG(K),NG(ip))+1
        IF(KG(K).NE.1) GO TO 11
        K=K-1
        IF(K.GT.0) GO TO 19
C
C   FINAL RESULTS for THIS ITERATION
C
        TSI=TSI*DV2G(ip)
        TI2=TI*TI
        WGT=TI2/TSI
        SI(ip)=SI(ip)+TI*WGT
        SI2(ip)=SI2(ip)+TI2
        SWGT(ip)=SWGT(ip)+WGT
        SCHI(ip)=SCHI(ip)+TI2*WGT
        AVGI=SI(ip)/SWGT(ip)
        SD=SWGT(ip)*IT(ip)/SI2(ip)
        CHI2A=SD*(SCHI(ip)/SWGT(ip)-AVGI*AVGI)/(IT(ip)-.999d0)
        SD=DSQRT(ONE/SD)
*ng

        GTSI=(GTSI*CALLS(ip)-GTI**2)/CALLS(ip)
        GSI(ip)=GSI(ip)+GTI/GTSI
        GSWGT(ip)=GSWGT(ip)+1d0/GTSI
        GAVGI=GSI(ip)/GSWGT(ip)
        GSD=DSQRT(ONE/GSWGT(ip))
*ng
C
        IF(NPRN.ne.0) then
           TSI=DSQRT(TSI)
           if (idebug.eq.1) write(6,201) IT(ip),ip,TI,TSI,AVGI,SD,CHI2A
*ng
           GTSI=DSQRT(GTSI)
           if (idebug.eq.1) write(6,201) IT(ip),ip,GTI,GTSI,GAVGI,GSD
           AVGI=GAVGI
           SD=GSD
*ng
        endif
      endif
C
C   REFINE GRID
C
      if(istat.eq.3)then
       DO J=1,NDIM(ip)
         XO=D(1,J)
         XN=D(2,J)
         D(1,J)=(XO+XN)/2d0
         DT(J)=D(1,J)
         DO I=2,NDM(ip)
           D(I,J)=XO+XN
           XO=XN
           XN=D(I+1,J)
           D(I,J)=(D(I,J)+XN)/3d0
           DT(J)=DT(J)+D(I,J)
         enddo
         D(ND(ip),J)=(XN+XO)/2d0
         DT(J)=DT(J)+D(ND(ip),J)
       enddo
C
        DO 28 J=1,NDIM(ip)
        RC=0d0
        DO 24 I=1,ND(ip)
        R(I)=0d0
        IF(D(I,J).LE.0d0) GO TO 24
        XO=DT(J)/D(I,J)
        R(I)=((XO-ONE)/XO/DLOG(XO))**ALPH
24      RC=RC+R(I)
        RC=RC/XND(ip)
        K=0
        XN=0d0
        DR=XN
        I=K
25      K=K+1
        DR=DR+R(K)
        XO=XN
        XN=XI(ip,K,J)
26      IF(RC.GT.DR) GO TO 25
        I=I+1
        DR=DR-RC
        XIN(I)=XN-(XN-XO)*DR/R(K)
        IF(I.LT.NDM(ip)) GO TO 26
        DO 27 I=1,NDM(ip)
27      XI(ip,I,J)=XIN(I)
28      XI(ip,ND(ip),J)=ONE
        open(unit=2,file=gridfile,status='unknown')
        write(6,*) 'Writing vegas grid to ',gridfile 
        do j=1,ndim(ip)
          write(2,*) j,(xi(ip,i,j),i=1,nd(ip))
        enddo
        close(2)
        return
      endif
C
 200  FORMAT(' Input parameters for vegas 4: ndim = ',I2,
     1     ', nshot = ',F10.0)
 201  FORMAT(i4,'(',i2,') ',g15.7,g13.6,g15.7,g13.6,f7.2)
 202  FORMAT(' DATA for AXIS',I2 / ' ',6X,'X',7X,'  DELT I  ',
     1    2X,' CONV''CE  ',11X,'X',7X,'  DELT I  ',2X,' CONV''CE  '
     2   ,11X,'X',7X,'  DELT I  ',2X,' CONV''CE  ' /
     2    (' ',3G12.4,5X,3G12.4,5X,3G12.4))
      RETURN
      END

************************************************************************

c     SUBROUTINE PERFORMS N-DIMENSIONAL MONTE CARLO INTEG'N
c     - BY G.P. LEPAGE   SEPT 1976/(REV)APR 1978
      SUBROUTINE vegas3(ISTAT,FXN,AVGI,SD,CHI2A)
      IMPLICIT REAL*8(A-H,O-Z)
      logical fi
      external FXN
      COMMON/BVEG3/NDIM,NCALL,NPRN
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/outfile/fname,prefix,suffix
      DIMENSION XI(50,10),D(50,10),DI(50,10),XIN(50),R(50),DT(10),X(10)
     1   ,KG(10),IA(10)
      REAL*8 QRAN(10)
      DATA NDMX/50/,ALPH/1.5D0/,ONE/1D0/,MDS/1/
      character ch*3,ctype*3,gridfile*19
      character fname*20,prefix*8,suffix*4
      ctype='.'//char(iaver+48)
      if(iaver.eq.0)ctype='.A'
      ch='v3a'
      gridfile = fname(1:6)//fname(12:20)
      gridfile = trim(gridfile)//ch//trim(ctype)

C     
      if(istat.eq.0.or.istat.eq.1.or.istat.eq.2)then
c
c     initialize cumulative variables 
c
        IT=0
        SI  =0d0
        SI2 =0d0
        SWGT=0d0
        SCHI=0d0
*ng
        GSI   =0d0
        GSI2  =0d0
        GSWGT =0d0
*mg
        ND=NDMX
        NG=1
        IF(MDS.ne.0)then
          NG=(NCALL/2d0)**(1d0/NDIM)
          MDS=1
          IF((2*NG-NDMX).ge.0)then
            MDS=-1
            NPG=NG/NDMX+1
            ND=NG/NPG
            NG=NPG*ND
          endif
        endif
        K=NG**NDIM
        NPG=NCALL/K
        IF(NPG.LT.2) NPG=2
        CALLS=NPG*K
        DXG=ONE/NG
        DV2G=(CALLS*DXG**NDIM)**2/NPG/NPG/(NPG-ONE)
        XND=ND
        NDM=ND-1
        DXG=DXG*XND
        XJAC=ONE/CALLS
        IF(NPRN.NE.0.and.istat.ne.0.and.idebug.eq.1)
     .       write(6,200) NDIM,CALLS 
      endif
      if(istat.eq.0)then
C
C   read in grid   
C
         inquire(file=gridfile,EXIST=fi)
         if (.not.fi)then
            write(6,*) ''
            write(6,*) 'Missing vegas grid file: ',gridfile
            write(6,*) ''
            stop
         endif
         open(unit=3,file=gridfile,status='unknown')
         write(6,*) 'Reading in vegas grid from ',gridfile 
         do j=1,ndim
            read(3,*) jj,(xi(i,j),i=1,nd)
         enddo
         close(3)
         NDO=ND
         return
      elseif(istat.eq.1)then
C
C   construct uniform grid  
C
        RC=1d0/XND
        DO  J=1,NDIM
          xi(1,j)=1d0
          K=0
          XN=0d0
          DR=0d0
          I=0
4         K=K+1
          DR=DR+ONE
          XO=XN
          XN=XI(K,J)
5         IF(RC.GT.DR) GO TO 4
          I=I+1
          DR=DR-RC
          XIN(I)=XN-(XN-XO)*DR
          IF(I.LT.NDM) GO TO 5
          DO  I=1,NDM
            XI(I,J)=XIN(I)
          enddo
          XI(ND,J)=ONE
        enddo
        NDO=ND
        return
C
      elseif(istat.eq.2)then
C
C   rescale refined grid to new ND value - preserve bin density
C

        if(nd.ne.ndo)then
          RC=NDO/XND
          DO  J=1,NDIM
            K=0
            XN=0d0
            DR=0d0
            I=0
6           K=K+1
            DR=DR+ONE
            XO=XN
            XN=XI(K,J)
7           IF(RC.GT.DR) GO TO 6
            I=I+1
            DR=DR-RC
            XIN(I)=XN-(XN-XO)*DR
            IF(I.LT.NDM) GO TO 7
            DO  I=1,NDM
              XI(I,J)=XIN(I)
            enddo
            XI(ND,J)=ONE
          enddo
        endif
        return
C
      elseif(istat.eq.3.or.istat.eq.4)then
c
c    main integration loop
c         
        IT=IT+1
        TI =0d0
        TSI=0d0
*ng
        GTI =0d0
        GTSI=0d0
*ng
        DO J=1,NDIM
          KG(J)=1
          DO I=1,ND
           D (I,J)=0d0
           DI(I,J)=0d0
          enddo
        enddo
C
11      FB=0d0
        F2B=0d0
        K=0
12      K=K+1
        do j=1,ndim
          qran(j)=rn(1)
        enddo        
        WGT=XJAC
        DO J=1,NDIM
          XN=(KG(J)-QRAN(J))*DXG+ONE
          IA(J)=XN
          IF(IA(J).GT.1)then
            XO=XI(IA(J),J)-XI(IA(J)-1,J)
            RC=XI(IA(J)-1,J)+(XN-IA(J))*XO
          else
            XO=XI(IA(J),J)
            RC=(XN-IA(J))*XO
          endif
          X(J)=RC
          WGT=WGT*XO*XND
        enddo
C
        F=WGT
        F=F*FXN(X,WGT)
        F2=F*F
        FB=FB+F
        F2B=F2B+F2
        DO J=1,NDIM
          DI(IA(J),J)=DI(IA(J),J)+F
          IF(MDS.GE.0) D(IA(J),J)=D(IA(J),J)+F2
        enddo
        IF(K.LT.NPG) GO TO 12
C
*ng

        GTI=GTI+FB
        GTSI=GTSI+F2B
*ng
        F2B=DSQRT(F2B*NPG)
        F2B=(F2B-FB)*(F2B+FB)
        TI=TI+FB
        TSI=TSI+F2B
        IF(MDS.lt.0) then
          DO J=1,NDIM
            D(IA(J),J)=D(IA(J),J)+F2B
          enddo
        endif
        K=NDIM
19      KG(K)=MOD(KG(K),NG)+1
        IF(KG(K).NE.1) GO TO 11
        K=K-1
        IF(K.GT.0) GO TO 19
C
C   FINAL RESULTS for THIS ITERATION
C
        TSI=TSI*DV2G
        TI2=TI*TI
        WGT=TI2/TSI
        SI=SI+TI*WGT
        SI2=SI2+TI2
        SWGT=SWGT+WGT
        SCHI=SCHI+TI2*WGT
        AVGI=SI/SWGT
        SD=SWGT*IT/SI2
        CHI2A=SD*(SCHI/SWGT-AVGI*AVGI)/(IT-.999d0)
        SD=DSQRT(ONE/SD)
*ng

        GTSI=(GTSI*CALLS-GTI**2)/CALLS
        GSI=GSI+GTI/GTSI
        GSWGT=GSWGT+1d0/GTSI
        GAVGI=GSI/GSWGT
        GSD=DSQRT(ONE/GSWGT)
*ng
C
        IF(NPRN.ne.0) then
          TSI=DSQRT(TSI)
          if (idebug.eq.1) write(6,201) IT,TI,TSI,AVGI,SD,CHI2A
*ng
          GTSI=DSQRT(GTSI)
          if (idebug.eq.1) write(6,201) IT,GTI,GTSI,GAVGI,GSD
          AVGI=GAVGI
          SD=GSD
*ng
        endif
      endif
C
C   REFINE GRID
C
      if(istat.eq.3)then
       DO J=1,NDIM
         XO=D(1,J)
         XN=D(2,J)
         D(1,J)=(XO+XN)/2d0
         DT(J)=D(1,J)
         DO I=2,NDM
           D(I,J)=XO+XN
           XO=XN
           XN=D(I+1,J)
           D(I,J)=(D(I,J)+XN)/3d0
           DT(J)=DT(J)+D(I,J)
        enddo
        D(ND,J)=(XN+XO)/2d0
      DT(J)=DT(J)+D(ND,J)
      enddo
C
        DO 28 J=1,NDIM
        RC=0d0
        DO 24 I=1,ND
        R(I)=0d0
        IF(D(I,J).LE.0d0) GO TO 24
        XO=DT(J)/D(I,J)
        R(I)=((XO-ONE)/XO/DLOG(XO))**ALPH
24      RC=RC+R(I)
        RC=RC/XND
        K=0
        XN=0d0
        DR=XN
        I=K
25      K=K+1
        DR=DR+R(K)
        XO=XN
        XN=XI(K,J)
26      IF(RC.GT.DR) GO TO 25
        I=I+1
        DR=DR-RC
        XIN(I)=XN-(XN-XO)*DR/R(K)
        IF(I.LT.NDM) GO TO 26
        DO 27 I=1,NDM
27      XI(I,J)=XIN(I)
28      XI(ND,J)=ONE
        open(unit=2,file=gridfile,status='unknown')
        write(6,*) 'Writing vegas grid to ',gridfile 
        do j=1,ndim
          write(2,*) j,(xi(i,j),i=1,nd)
        enddo
        close(2)
        return
      endif
C
 200  FORMAT(' Input parameters for vegas 3: ndim = ',I2,
     1     ', nshot = ', F10.0)
 201  FORMAT(i4,'( 3) ',g15.7,g13.6,g15.7,g13.6,f7.2)
 202  FORMAT(' DATA for AXIS',I2 / ' ',6X,'X',7X,'  DELT I  ',
     1    2X,' CONV''CE  ',11X,'X',7X,'  DELT I  ',2X,' CONV''CE  '
     2   ,11X,'X',7X,'  DELT I  ',2X,' CONV''CE  ' /
     2    (' ',3G12.4,5X,3G12.4,5X,3G12.4))
      RETURN
      END

c-----------------------------------------------------------------------
c     Random-number generator.
c-----------------------------------------------------------------------

c     Top-level function.
      real(8) function rn(idummy)
      implicit none
      integer, intent(in) :: idummy
      real(8)             :: ran
      integer             :: iaver,imom,idist,iang,idebug
      integer             :: i1,i2,init
      common/intech/iaver,imom,idist,iang,idebug
      common/rseeds/i1,i2
      save init
      data init /1/
      if (init.eq.1) then
         init=0
         if (idebug.eq.1) write(6,11) i1,i2
         call rmarin(i1,i2)
      end if
 10   call ranmar(ran)
      if (ran.lt.1d-16) goto 10
      rn=ran

 11   format(" Seeding with (",I4,",",I4,")")

      return
      end

************************************************************************

c     Universal random number generator proposed by marsaglia and zaman
c     in report fsu-scri-87-50
c     in this version rvec is a double precision variable.
      subroutine ranmar(rvec)
      implicit real*8(a-h,o-z)
      common/ raset1 / ranu(97),ranc,rancd,rancm
      common/ raset2 / iranmr,jranmr
      save /raset1/,/raset2/
      uni = ranu(iranmr) - ranu(jranmr)
      if(uni .lt. 0d0) uni = uni + 1d0
      ranu(iranmr) = uni
      iranmr = iranmr - 1
      jranmr = jranmr - 1
      if(iranmr .eq. 0) iranmr = 97
      if(jranmr .eq. 0) jranmr = 97
      ranc = ranc - rancd
      if(ranc .lt. 0d0) ranc = ranc + rancm
      uni = uni - ranc
      if(uni .lt. 0d0) uni = uni + 1d0
      rvec = uni
      end

************************************************************************

c     Initialisation routine for ranmar, must be called before
c     generating any pseudorandom numbers with ranmar.
c     The input values should be in the ranges
c     0<=ij<=31328 ; 0<=kl<=30081.
      subroutine rmarin(ij,kl)
      implicit real*8(a-h,o-z)
      common/ raset1 / ranu(97),ranc,rancd,rancm
      common/ raset2 / iranmr,jranmr
      save /raset1/,/raset2/
c     This shows correspondence between the simplified input seeds ij, kl
c     and the original marsaglia-zaman seeds i,j,k,l.
c     to get the standard values in the marsaglia-zaman paper (i=12,j=34
c     k=56,l=78) put ij=1802, kl=9373.
      i = mod( ij/177 , 177 ) + 2
      j = mod( ij     , 177 ) + 2
      k = mod( kl/169 , 178 ) + 1
      l = mod( kl     , 169 )
      do 300 ii = 1 , 97
        s =  0d0
        t = .5d0
        do 200 jj = 1 , 24
          m = mod( mod(i*j,179)*k , 179 )
          i = j
          j = k
          k = m
          l = mod( 53*l+1 , 169 )
          if(mod(l*m,64) .ge. 32) s = s + t
          t = .5d0*t
  200   continue
        ranu(ii) = s
  300 continue
      ranc  =   362436d0 / 16777216d0
      rancd =  7654321d0 / 16777216d0
      rancm = 16777213d0 / 16777216d0
      iranmr = 97
      jranmr = 33
      end

c-----------------------------------------------------------------------
c     Random-number function taken from Knuth
c     (seminumerical algorithms).
c     method is x(n)=mod(x(n-55)-x(n-24),1/fmodul)
c     No provision yet for control over the seed number.
c
c     ranf  gives one random number between 0 and 1.
c     irn55 generates 55 random numbers between 0 and 1/fmodul.
c     in55  initializes the 55 numbers and warms up the sequence.
c-----------------------------------------------------------------------

      double precision function rnnew(dummy)
      implicit double precision (a-h,o-z)
      parameter (fmodul=1.d-09)
      integer ia(55)
      save ia
      data ncall/0/
      data mcall/55/
      if( ncall.eq.0 ) then
         call in55 ( ia,234612947 )
         ncall = 1
      endif
      if ( mcall.eq.0 ) then
         call irn55(ia)
         mcall=55
      endif
      rnnew=ia(mcall)*fmodul
      mcall=mcall-1
      end

      subroutine in55(ia,ix)
      parameter (modulo=1000000000)
      integer ia(55)
      ia(55)=ix
      j=ix
      k=1
      do 10 i=1,54
         ii=mod(21*i,55)
         ia(ii)=k
         k=j-k
         if(k.lt.0)k=k+modulo
         j=ia(ii)
 10   continue
      do 20 i=1,10
         call irn55(ia)
 20   continue
      end

      subroutine irn55(ia)
      parameter (modulo=1000000000)
      integer ia(55)
      do 10 i=1,24
         j=ia(i)-ia(i+31)
         if(j.lt.0)j=j+modulo
         ia(i)=j
 10   continue
      do 20 i=25,55
         j=ia(i)-ia(i-24)
         if(j.lt.0)j=j+modulo
         ia(i)=j
 20   continue
      end

c-----------------------------------------------------------------------

c     The hist-handlers provide access to the histo-handlers via
c     histogram names.

c-----------------------------------------------------------------------

c     Function to return histogram ID of histogram name.
      integer function idhist(string)
      implicit none
      character*(*)      :: string
      integer, parameter :: nhisto=100
      logical            :: isinit
      integer            :: j,jhist,khist
      character(50)      :: stringhist(nhisto)
c     Common blocks.
      common/histnew/jhist,stringhist
      save/histnew/

      if (string.eq.' ') stop 'idhist: empty histogram name'

      khist = -1
      do j=1,jhist
         if (stringhist(j).eq.' ') khist = j
         if (stringhist(j).eq.string)then
            idhist = j
            return
         endif
      enddo

      if (khist.le.0)then
         if (jhist.eq.nhisto)then
            stop 'idhist: exceeded maximum number of histograms'
         endif

         jhist = jhist+1
         khist = jhist
      endif
      stringhist(khist) = trim(adjustl(string))

      if (stringhist(khist).ne.trim(adjustl(string)))then
         stop 'idhist: histogram name too long'
      endif

c     A negative sign indicates a new histogram.
      idhist = -khist

      return
      end

************************************************************************

c     Book a new histogram with name 'name'.
      integer function bookhist(name,bmin,bmax,nbin)
      implicit none
      character*(*)       :: name
      integer, intent(in) :: nbin
      real(8), intent(in) :: bmin,bmax
      character(19)       :: cname
      integer, external   :: idhist

      bookhist = idhist(name)
      if (bookhist.gt.0)then
         write(6,*) "bookhist: histogram already booked"
         return
      endif
      bookhist = abs(bookhist)
      call histoi(bookhist,bmin,bmax,nbin)

      return
      end

************************************************************************
      
c     Print histogram data.
      subroutine printhistdata()
      implicit none
      integer             :: iwarm,iprod,ihist
      integer, parameter  :: nhisto=100
      character(50)       :: hname
      integer             :: jhist
      integer             :: ibin(nhisto)
      character(50)       :: stringhist(nhisto)
      real(8)             :: bmin,bmax,hmin(nhisto),hwidth(nhisto)
      character(1)        :: star 
      character(9)        :: short
      character(39)       :: sblank
      character(86)       :: starline,sno,slong
c     Common blocks.
      common/ivegas/iwarm,iprod
      common/histnew/jhist,stringhist
      common/hispar/hmin,hwidth,ibin

      if (iprod.ne.1) return

      starline=
     . '************************************************************'//
     . '************************************'
      sblank=' '
      sno=' '
      star='*'

      write(6,*)
      write(6,*) star,starline,star
      write(6,*) star,sno,star
      slong = ' Histograms:'
      write(6,*) star,slong,star
      write(6,*) star,sno,star
      do ihist=1,nhisto
         hname = adjustl(trim(stringhist(ihist)))
         if (hname.ne.'')then
            bmin = hmin(ihist)
            bmax = bmin+hwidth(ihist)*ibin(ihist)
            if (dabs(bmin).lt.1d-15) bmin=0d0
            if (dabs(bmax).lt.1d-15) bmax=0d0
            write(6,10) " * ",hname,
     .           "  min =",bmin,"  max =",bmax,
     .           "  bins =",ibin(ihist)," *"
         endif
      enddo
      write(6,*) star,sno,star
      write(6,*) star,starline,star

 10   format(A3,A40,A7,1pe9.1,A7,1pe9.1,A8,I4,A2)

      return
      end

************************************************************************

c     Fill histogram with name 'name'.
      subroutine fillhist(name,val,wgt)
      implicit none
      integer, parameter  :: nhisto=100
      character*(*)       :: name
      real(8), intent(in) :: val,wgt
      integer             :: idhis,jhist
      character(50)       :: stringhist(nhisto)
      integer, external   :: idhist
      common/histnew/jhist,stringhist

      idhis = findloc(stringhist,name,DIM=1)
      call histoa(idhis,val,wgt)

      return
      end

************************************************************************

c     Print histogram with name 'name' to file.
      subroutine writehist(name)
      implicit none
      character*(*)       :: name
      integer, parameter  :: ioff=10
      integer             :: idhis
      character(20)       :: fname
      character(77)       :: outname
      character(8)        :: prefix
      character(4)        :: suffix
      integer, external   :: idhist
      common/outfile/fname,prefix,suffix

      idhis = abs(idhist(name))
      outname=adjustl(trim(adjustl(prefix))//'/'//trim(fname(1:19))
     .     //trim(adjustl(name))//suffix)
      open(idhis+ioff,file=outname)
      call histowf(idhis,idhis+ioff)
      close(idhis+ioff)

      return
      end

c-----------------------------------------------------------------------
c     The histo-handlers, provides a simple interface between the user 
c     routine 'bino' and general histogram manipulator 'ghiman'.
c
c     'histoi' : sets up histogram 'idhis' with minimum bin
c                value 'bmin', maximum binvalue 'bmax' and
c                number of bins 'nbin'
c     'histoa' : make specific entry in histogram 'idhis' for 
c                value 'val' and weight 'wgt'
c     'histoe' : calculate error request for histogram 'idhis',
c                pipe through
c     'histow' : output request for histogram 'idhis', pipe through
c-----------------------------------------------------------------------

c     Histogram initialization.
      subroutine histoi(idhis,bmin,bmax,nbin)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(0,idhis,nbin,0d0,0d0)
      hmin(idhis)=bmin
      ibin(idhis)=nbin
      hwidth(idhis)=(bmax-bmin)/nbin
      return
      end

c     Histogram entry.
      subroutine histoa(idhis,val,wgt)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      if(val.lt.hmin(idhis))return
      if(idhis.le.100)then
        iloc=1+int((val-hmin(idhis))/hwidth(idhis))
        call ghiman(1,idhis,iloc,wgt,wgt*val)
      endif
      return
      end

c     Event errors request, pipe through with correct 'ghiman' call.
      subroutine histoe(istat,idhis)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(istat,idhis,ibin(idhis),0d0,0d0)
      return
      end

c     Output request, pipe through with correct 'ghiman' call.
      subroutine histow(idhis)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(4,idhis,ibin(idhis),hmin(idhis),hwidth(idhis))
      return
      end

c     Output request, pipe through with correct 'ghiman' call.
      subroutine histow1(idhis)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /hispar/hmin,hwidth,ibin 
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(5,idhis,ibin(idhis),hmin(idhis),hwidth(idhis))
      return
      end

c     Output request, pipe through with correct 'ghiman' call.
c     Write to file, logical unit 'lun'.
      subroutine histowf(idhis,lun)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common/hispar/hmin,hwidth,ibin
      dimension hmin(nhisto),hwidth(nhisto),ibin(nhisto)
      call ghiman(lun,idhis,ibin(idhis),hmin(idhis),hwidth(idhis))
      return
      end

c-----------------------------------------------------------------------
c     General histogram manipulator, has no knowledge about
c     specific histograms.
c
c     Maximum number of histograms is given by the nhisto parameter.
c     Maximum number of bins       is given by the maxbin parameter.
c
c     istat = 0 : set histogram 'idhis' to value 'entry1' from bin 1
c                 to bin 'iloc' and resets sweep counter 'itmx' to zero.
c     istat = 1 : add in histogram 'idhis' weight 'entry1' in 
c                 bin location 'iloc'.
c     istat = 2 : accumulate event errors in histogram 'idhis' from
c                 bin 1 to bin 'iloc' for this sweep and increase
c                 sweepcounter 'itmx' by 1.
c     istat = 3 : calculate standard deviation of the 'itmx' sweeps per
c                 bin in histogram 'idhis' from bin 1 to bin 'iloc'
c                 as monte carlo error estimate.
c     istat = 4 : write final output to screen in histogram 'idhis'
c                 from bin 1 to bin 'iloc' with offset 'entry1' and
c                 binwidth 'entry2'.
c                 Format: 
c                   from bin_number = 1 to 'iloc'  
c                   write 'entry1'+'entry2'*(bin_number - 0.5),
c                     bin_value, bin_error
c                   endfrom
c                 [for istat>10: write final output to file lun=istat]
c     istat = 5 : write final output to screen in histogram 'idhis'
c                 from bin 1 to bin 'iloc' with offset 'entry1' and
c                 binwidth 'entry2'.
c                 Format:
c                   from bin_number = 1 to 'iloc'  
c                   write 'entry1'+'entry2'*(bin_number - 1),
c                     bin_value, bin_error
c                   endfrom
c-----------------------------------------------------------------------

      subroutine ghiman(istat,idhis,iloc,entry1,entry2)
      implicit double precision (a-h,o-z)
      parameter(nhisto=100,maxbin=400)
      common /runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2) 
      dimension bin(nhisto,4,maxbin),xbin(nhisto,4)
      common/bins/w(maxbin),w2(maxbin),nc(maxbin)
      if ((idhis.lt.1).or.(idhis.gt.nhisto)) return
      if ((iloc .lt.1).or.(iloc .gt.maxbin)) return
c     Init histograms.
      if (istat.eq.0) then
         do i=1,iloc
            do j=1,4
               bin(idhis,j,i)=entry1
            enddo
         enddo
         itmx=0
      endif

c     Write event into histogram.
      if (istat.eq.1) then
         if ((iloc.ge.1).and.(iloc.le.maxbin)) then
            bin(idhis,1,iloc)=bin(idhis,1,iloc)+entry1
            bin(idhis,4,iloc)=bin(idhis,4,iloc)+1d0
            xbin(idhis,1)=xbin(idhis,1)+entry2
            xbin(idhis,4)=xbin(idhis,4)+1d0
         endif
      endif

c     Accumulate event errors.
      if (istat.eq.2) then
         do i=1,iloc
            bin(idhis,2,i)=bin(idhis,2,i)+bin(idhis,1,i)**2
            bin(idhis,3,i)=bin(idhis,3,i)+bin(idhis,1,i)
            bin(idhis,1,i)=0d0
            xbin(idhis,2)=xbin(idhis,2)+xbin(idhis,1)**2
            xbin(idhis,3)=xbin(idhis,3)+xbin(idhis,1)
            xbin(idhis,1)=0d0
         enddo
      endif

c     Calculate event errors.
      if (istat.eq.3) then
         do i=1,iloc
            bin(idhis,2,i)=
     .           sqrt((bin(idhis,2,i)/itmax2-(bin(idhis,3,i)/itmax2)**2)
     .           /float(itmax2-1))
         enddo
         xbin(idhis,2)=
     .        sqrt((xbin(idhis,2)/itmax2-(xbin(idhis,3)/itmax2)**2)
     .        /float(itmax2-1))
      endif

c     Output distributions.
      if (istat.eq.4) then
         sum=0d0
         sum2=0d0
         do i=1,iloc
            y=bin(idhis,3,i)/itmax2 
            y2=bin(idhis,2,i)
            sum=sum+y
            sum2=sum2+y2**2
            nn=bin(idhis,4,i)
            if(idhis.le.100)then
               x=entry1+entry2*(dfloat(i)-.5d0)
               write(6,101) x,y/entry2,y2/entry2 
            endif
         enddo
         write(6,102)sum,sqrt(sum2)
         write(6,103)xbin(idhis,3)/itmax2,xbin(idhis,2)
      endif
 101  format(3x,f11.6,1pe12.4,1pe12.4)
 111  format(f11.6,f11.6,1pe12.4,1pe12.4,1pe12.4)
 102  format(' sum ',1pe12.4,1pe12.4)
 103  format(' <y> ',1pe12.4,1pe12.4)
      if (istat.ge.11) then
         sum=0d0
         sum2=0d0
         do i=1,iloc
            y=bin(idhis,3,i)/itmax2 
            y2=bin(idhis,2,i)
            sum=sum+y
            sum2=sum2+y2**2
            nn=bin(idhis,4,i)
            if(idhis.le.100)then
               x=entry1+entry2*(dfloat(i)-.5d0)
               xMin=entry1+entry2*dfloat(i-1)
               xMax=entry1+entry2*dfloat(i)
               write(istat,111)
     .              xMin,xMax,y,y2,dfloat(nn)
            endif
         enddo
      endif
c     Print histogram to screen.
      if (istat.eq.5) then
         sum=0d0
         sum2=0d0
         do i=1,iloc
            y=bin(idhis,3,i)/itmax2
            y2=bin(idhis,2,i)
            sum=sum+y
            sum2=sum2+y2**2
            nn=bin(idhis,4,i)
            x=entry1+entry2*(dfloat(i)-1d0)
            xMin=entry1+entry2*dfloat(i-1)
            xMax=entry1+entry2*dfloat(i)
            w(i)  = y
            w2(i) = y2
            nc(i) = nn
            write(6,111) xMin,xMax,y/entry2,y2/entry2,dfloat(nn)
         enddo
         write(6,102)sum,sqrt(sum2)
         write(6,103)xbin(idhis,3)/itmax2,xbin(idhis,2)
      endif
c     Fill common block 'bins'.
      if (istat.eq.6) then
         sum=0d0
         sum2=0d0
         do i=1,iloc
            y=bin(idhis,3,i)/itmax2
            y2=bin(idhis,2,i)
            sum=sum+y
            sum2=sum2+y2**2
            nn=bin(idhis,4,i)
            x=entry1+entry2*(dfloat(i)-1d0)
            xMin=entry1+entry2*dfloat(i-1)
            xMax=entry1+entry2*dfloat(i)
            w(i)  = y
            w2(i) = y2
            nc(i) = nn
         enddo
      endif

      return
      end

c-----------------------------------------------------------------------
