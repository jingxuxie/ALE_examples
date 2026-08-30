c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains subroutines calculating event-shape
c     observables.

c-----------------------------------------------------------------------
c     C and D parameters.
c-----------------------------------------------------------------------

      subroutine getCD(Cpar,Dpar,npar)
      implicit real*8(a-h,o-z)
      common/pcut/ppar(4,5)

      t11=theta(1,1,npar)
      t12=theta(1,2,npar)
      t13=theta(1,3,npar)
      t22=theta(2,2,npar)
      t23=theta(2,3,npar)
      t33=theta(3,3,npar)
      Dpar=t11*t22*t33-t11*t23**2-t22*t13**2-t33*t12**2+2d0*t12*t13*t23
      Dpar=27d0*Dpar
      Cpar=-t12**2-t13**2-t23**2+t11*t22+t11*t33+t22*t33
      Cpar=3d0*Cpar

      return
      end

************************************************************************

      function theta(ii,ij,npar)
      implicit real*8(a-h,o-z)
      common/pcut/ppar(4,5)
      top=0d0
      bot=0d0
      do i=1,npar
         top=top+ppar(ii,i)*ppar(ij,i)/ppar(4,i)
         bot=bot+ppar(4,i)
      enddo
      theta=top/bot
      return
      end

c-----------------------------------------------------------------------
c     Sphericity observables.
c-----------------------------------------------------------------------

c     Calculate S, A, and P parameters.
      subroutine getSAP(Spar,Apar,Planar,npar)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common/pcut/ppar(4,5)

      t11=phi(1,1,npar)
      t12=phi(1,2,npar)
      t13=phi(1,3,npar)
      t22=phi(2,2,npar)
      t23=phi(2,3,npar)
      t33=phi(3,3,npar)
      x=t11+t22+t33
      y=t11*t22+t11*t33+t22*t33-t12**2-t13**2-t23**2
      z=t11*t22*t33-t11*t23**2-t22*t13**2-t33*t12**2+2d0*t12*t13*t23
      C=3d0*y/x**2
      D=27d0*z/x**3
      sqrt1mc=sqrt(1d0-C)
      ctheta=(D-3d0*C+2d0)/2d0/(1d0-C)/sqrt1mc
      if (ctheta.gt.1d0) ctheta=1d0
      if (ctheta.lt.-1d0) ctheta=-1d0
      theta=acos(ctheta)
      ct=cos(theta/3d0)
      st=sin(theta/3d0)
      rt3=dsqrt(3d0)
      s1=1d0/3d0+2d0/3d0*sqrt1mc*ct
      s2=1d0/3d0-1d0/3d0*sqrt1mc*(1d0*ct+rt3*st)
      s3=1d0/3d0-1d0/3d0*sqrt1mc*(1d0*ct-rt3*st)
      s1=2d0/3d0*sqrt1mc*cos(theta/3d0)+1d0/3d0      
      s2=2d0/3d0*sqrt1mc*cos((theta+2d0*pi)/3d0)+1d0/3d0
      s3=2d0/3d0*sqrt1mc*cos((theta+4d0*pi)/3d0)+1d0/3d0
      e3=dmin1(s1,s2,s3)
      if(e3.lt.0d0)e3=0d0
      e1=dmax1(s1,s2,s3)
      e2=1d0-e1-e3
      Spar=3d0/2d0*(e2+e3)
      Apar=3d0/2d0*e3
      Planar=e2-e3

      return
      end

************************************************************************

      function phi(ii,ij,npar)
      implicit real*8(a-h,o-z)
      common/pcut/ppar(4,5)
      phi=0d0
      do i=1,npar
        phi=phi+ppar(ii,i)*ppar(ij,i)
      enddo
      return
      end

c-----------------------------------------------------------------------
c     Thrust and friends.
c-----------------------------------------------------------------------

c     Compute thrust T and all observables related to it.
c     (MH, BW, BT, TMinor, TMajor, FCx, etc)
      subroutine getT(Tpar,Tmajor,Tminor,Opar,em2h,em2l,em2d,
     .     bmax,bmin,bsum,bdiff,fc0,fc1,fc2,fc3,bks0,bks1,bks2,bks3,
     .     npar)
      implicit real*8(a-h,o-z)
      common/pcut/ppar(4,5)
      common/Tdata/pp(5,15),ta(3),tmja(3),tmna(3)
      do i=1,15
         do j=1,5
            pp(j,i)=0d0
         enddo
      enddo
      n=0
      do j=1,npar
         n=n+1
         do i=1,4
            pp(i,n)=ppar(i,j)
         enddo
         pp(5,n)=pp(4,n)
      enddo
      if(npar.eq.4)then
         do k=2,npar 
            n=n+1
            do i=1,4
               pp(i,n)=ppar(i,1)+ppar(i,k)
            enddo
            pp(5,n)=sqrt(pp(1,n)**2+pp(2,n)**2+pp(3,n)**2)
         enddo
      elseif(npar.eq.5)then
         do j=1,npar-1
            do k=j+1,npar 
               n=n+1
               do i=1,4
                  pp(i,n)=ppar(i,j)+ppar(i,k)
               enddo
               pp(5,n)=sqrt(pp(1,n)**2+pp(2,n)**2+pp(3,n)**2)
            enddo
         enddo
      endif

c     Find thrust axis and calculate thrust.
      ithrust=0
      Tpar=0d0
      do i=1,15
         t=2d0*pp(5,i)
         if(t.gt.Tpar) then
            Tpar=t
            ithrust=i
         endif
      enddo
c     Thrust axis (unit vector).
      do j=1,3
         ta(j) = 2d0*pp(j,ithrust)/Tpar
      enddo

c     Find major axis (maximizes momentum perp to thrust axis).
      imajor=0
      Tmajor=0d0
      do i=1,15
         if (i.ne.ithrust)then
            tmp = pp(1,i)*ta(1)+pp(2,i)*ta(2)+pp(3,i)*ta(3)
            t   = 2d0*sqrt(abs(pp(5,i)**2-tmp**2))
            if (t.gt.Tmajor)then
               Tmajor = t
               imajor = i
               ppta   = tmp
            endif
         endif
      enddo
      if (Tmajor.gt.0)then
         do i=1,3
            tmja(i) = 2d0*(pp(i,imajor) - ta(i)*ppta)/Tmajor
         enddo

c     Find minor axis.
         tmna(1) = ta(2)*tmja(3)-ta(3)*tmja(2)
         tmna(2) = ta(3)*tmja(1)-ta(1)*tmja(3)
         tmna(3) = ta(1)*tmja(2)-ta(2)*tmja(1)
         Tminor=0d0
         do i=1,npar
            Tminor = Tminor +
     .           abs(pp(1,i)*tmna(1)+pp(2,i)*tmna(2)+pp(3,i)*tmna(3))
         enddo

c     Oblateness.
         Opar = Tmajor-Tminor
      endif

c     Hemisphere masses.
      em2h = pp(4,ithrust)**2-pp(5,ithrust)**2
      em2l = (1d0-pp(4,ithrust))**2-pp(5,ithrust)**2
      if (em2l.gt.em2h)then
         tmp  = em2l
         em2l = em2h
         em2h = tmp
      endif
      em2d = em2h-em2l

c     Hemisphere broadening.
      bplus  = 0d0
      bminus = 0d0
      bot    = 0d0
      do i=1,npar
         bot = bot+pp(4,i)
         if (i.ne.ithrust)then
            tmp1 = pp(1,i)*ta(1)+pp(2,i)*ta(2)+pp(3,i)*ta(3)
            tmp2 = sqrt(abs(pp(4,i)**2-tmp1**2))
            if (tmp1.gt.0d0)then
               bplus = bplus+tmp2 
            elseif (tmp1.lt.0d0)then
               bminus = bminus+tmp2 
            endif
         endif
      enddo
      bplus  = bplus/bot/2d0
      bminus = bminus/bot/2d0
      bmax   = dmax1(bplus,bminus)
      bmin   = dmin1(bplus,bminus)
      bsum   = bmax+bmin 
      bdiff  = bmax-bmin 

c     Fractional energy correlations.
      Etot = 0d0
      FC0  = 0d0
      FC1  = 0d0
      FC2  = 0d0
      FC3  = 0d0
      do i=1,npar
         Etot = Etot + ppar(4,i)
         do j=1,i-1
            qit = pp(1,i)*ta(1)+pp(2,i)*ta(2)+pp(3,i)*ta(3)
            qjt = pp(1,j)*ta(1)+pp(2,j)*ta(2)+pp(3,j)*ta(3)
            if (qit*qjt.le.0) cycle
            pipj = pp(1,i)*pp(1,j)+pp(2,i)*pp(2,j)+pp(3,i)*pp(3,j)
            pixpj = pp(2,i)*pp(3,j)-pp(3,i)*pp(2,j)
     .           + pp(3,i)*pp(1,j)-pp(1,i)*pp(3,j)
     .           + pp(1,i)*pp(2,j)-pp(2,i)*pp(1,j)
            Ei  = pp(4,i)
            Ej  = pp(4,j)
            pi  = dsqrt(pp(1,i)**2+pp(2,i)**2+pp(3,i)**2)
            pj  = dsqrt(pp(1,j)**2+pp(2,j)**2+pp(3,j)**2)
            omcTh = 1d0-dabs(pipj/pi/pj)
            sTh = dabs(pixpj/pi/pj)
            if (omcTh.lt.0d0) cycle
            FC0 = FC0 + 2d0*Ei*Ej*omcTh
            FC1 = FC1 + 2d0*Ei*Ej*sTh**0.5d0*omcTh**0.5d0
            FC2 = FC2 + 2d0*Ei*Ej*sTh
            FC3 = FC3 + 2d0*Ei*Ej*sTh**1.5d0*omcTh**(-0.5d0)
         enddo
      enddo
      FC0 = FC0/Etot**2
      FC1 = FC1/Etot**2
      FC2 = FC2/Etot**2
      FC3 = FC3/Etot**2

c     BKS observables.
      qsum = 0d0
      BKS0 = 0d0
      BKS1 = 0d0
      BKS2 = 0d0
      BKS3 = 0d0
      do i=1,npar
         Ei  = pp(4,i)
         qi  = dsqrt(pp(1,i)**2+pp(2,i)**2+pp(3,i)**2)
         qit = pp(1,i)*ta(1)+pp(2,i)*ta(2)+pp(3,i)*ta(3)
         qixt = pp(2,i)*ta(3)-pp(3,i)*ta(2)
     .        + pp(3,i)*ta(1)-pp(1,i)*ta(3)
     .        + pp(1,i)*ta(2)-pp(2,i)*ta(1)
         omcTh = 1d0-dabs(qit/qi)
         sTh = dabs(qixt/qi)
         qsum = qsum + qi
         if (omcTh.lt.0d0) cycle
         BKS0 = BKS0 + Ei*omcTh
         BKS1 = BKS1 + Ei*sTh**0.5d0*omcTh**0.5d0
         BKS2 = BKS2 + Ei*sTh
         BKS3 = BKS3 + Ei*sTh**1.5d0*omcTh**(-0.5d0)
      enddo
      BKS0 = BKS0/qsum
      BKS1 = BKS1/qsum
      BKS2 = BKS2/qsum
      BKS3 = BKS3/qsum

      return
      end

c-----------------------------------------------------------------------
