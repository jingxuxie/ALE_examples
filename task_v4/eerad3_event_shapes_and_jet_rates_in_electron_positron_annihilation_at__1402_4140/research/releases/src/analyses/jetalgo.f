c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains subroutines implementing jet-clustering
c     algorithms.

c-----------------------------------------------------------------------
c     Jet-transition parameters in different algorithms.
c     Jet algorithms:
c       jetalg = 1: JADE
c       jetalg = 2: DURHAM
c       jetalg = 3: GENEVA
c     Recombination schemes:
c       jetcom = 1: E scheme
c       jetcom = 2: E0 scheme
c       jetcom = 3: P scheme
c       jetcom = 4: P0 scheme
c-----------------------------------------------------------------------

      subroutine getjet(y45,y34,y23,npar,jetalg,jetcom)
      implicit real(8)(a-h,o-z)
      common/pcut/ppar(4,5) 
      dimension pjet(4,5)
      integer :: iclus(3),jclus(3)
      dimension pseq(0:3,4,5)
c     Common blocks.
      common/cuts/ycutJ,ycutD,ycutG,
     .     Acut,Bcut,Ccut,Dcut,Fcut,Tcut,Scut,
     .     em2hcut,em2lcut
      common/clusterseq/pseq,nj,nclus,iclus,jclus

c     Initialise and calculate visible energy.
      nclus=0
      nj=-1
      y45=0d0
      y34=0d0
      y23=0d0
      evis=0d0
      do i=1,npar
         do j=1,4
            pjet(j,i)=ppar(j,i)
            pseq(0,j,i)=ppar(j,i)
         enddo
         evis=evis+pjet(4,i)
      enddo

c     Clustering 5->4.
      if (npar.ge.5)then
         y45=1d0
         do i=1,npar-1
            do j=i+1,npar
               if(pjet(4,i).gt.0d0.and.pjet(4,j).gt.0d0)then
c     Here, vij=1-cos(thetaij).
                  vij=v(pjet(1,i),pjet(1,j))
                  ei=pjet(4,i)
                  ej=pjet(4,j)
                  emin=dmin1(ei,ej)
                  if (jetalg.eq.1) ytemp=2d0*ei*ej*vij/evis**2
                  if (jetalg.eq.2) ytemp=2d0*emin**2*vij/evis**2
                  if (jetalg.eq.3) ytemp=8d0*ei*ej*vij/9d0/(ei+ej)**2/evis**2
                  if (ytemp.lt.y45)then
                     y45=ytemp
                     ii=i
                     jj=j
                  endif
               endif
            enddo
         enddo
         call jetco(pjet(1,ii),pjet(1,jj),evis,jetcom)
         if (nj.lt.0 .and. y45.gt.ycutD)then
            nj=5
         else
            nclus=nclus+1
            iclus(nclus)=ii
            jclus(nclus)=jj
            do i=1,npar
               pseq(nclus,1,i)=pjet(1,i)
               pseq(nclus,2,i)=pjet(2,i)
               pseq(nclus,3,i)=pjet(3,i)
               pseq(nclus,4,i)=pjet(4,i)
            enddo
         endif
      endif

c     Clustering 4->3.
      if (npar.ge.4) then
         y34=1d0
         do i=1,npar-1
            do j=i+1,npar
               if(pjet(4,i).gt.0d0.and.pjet(4,j).gt.0d0)then
c     Here, vij=1-cos(thetaij).
                  vij=v(pjet(1,i),pjet(1,j))
                  ei=pjet(4,i)
                  ej=pjet(4,j)
                  emin=dmin1(ei,ej)
                  if (jetalg.eq.1) ytemp=2d0*ei*ej*vij/evis**2
                  if (jetalg.eq.2) ytemp=2d0*emin**2*vij/evis**2
                  if (jetalg.eq.3) ytemp=8d0*ei*ej*vij/9d0/(ei+ej)**2 
                  if (ytemp.lt.y34)then
                     y34=ytemp
                     ii=i
                     jj=j
                  endif
               endif
            enddo
         enddo
         call jetco(pjet(1,ii),pjet(1,jj),evis,jetcom)
         if (nj.lt.0 .and. y34.gt.ycutD)then
            nj=4
         else
            nclus=nclus+1
            iclus(nclus)=ii
            jclus(nclus)=jj
            do i=1,npar
               pseq(nclus,1,i)=pjet(1,i)
               pseq(nclus,2,i)=pjet(2,i)
               pseq(nclus,3,i)=pjet(3,i)
               pseq(nclus,4,i)=pjet(4,i)
            enddo
         endif
      endif

c     Clustering 3->2.
      y23=1d0
      do i=1,npar-1
         do j=i+1,npar
            if(pjet(4,i).gt.0d0.and.pjet(4,j).gt.0d0)then
c     Here, vij=1-cos(thetaij).
               vij=v(pjet(1,i),pjet(1,j))
               ei=pjet(4,i)
               ej=pjet(4,j)
               emin=dmin1(ei,ej)
               if(jetalg.eq.1) ytemp=2d0*ei*ej*vij/evis**2
               if(jetalg.eq.2) ytemp=2d0*emin**2*vij/evis**2
               if(jetalg.eq.3) ytemp=8d0*ei*ej*vij/9d0/(ei+ej)**2 
               if (ytemp.lt.y23)then
                  y23=ytemp
                  ii=i
                  jj=j
               endif
            endif
         enddo
      enddo
      call jetco(pjet(1,ii),pjet(1,jj),evis,jetcom)
      if (nj.lt.0 .and. y23.gt.ycutD)then
         nj=3
      else
         nj=2
         nclus=nclus+1
         iclus(nclus)=ii
         jclus(nclus)=jj
         do i=1,npar
            pseq(nclus,1,i)=pjet(1,i)
            pseq(nclus,2,i)=pjet(2,i)
            pseq(nclus,3,i)=pjet(3,i)
            pseq(nclus,4,i)=pjet(4,i)
         enddo
      endif

      return
      end

************************************************************************

      function v(a,b)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4)
      pa=sqrt(a(1)**2+a(2)**2+a(3)**2)
      pb=sqrt(b(1)**2+b(2)**2+b(3)**2)
      ea=a(4)
      eb=b(4)
      v  = (dot(a(1),b(1))-ea*eb+pa*pb)/pa/pb
      return
      end

************************************************************************

c     Jet recombination schemes.
      subroutine jetco(a,b,evis,jetcom)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4)
c     E scheme.
      if(jetcom.eq.1)then
         do i=1,4
            a(i) = a(i)+b(i)
         enddo
c     E0 scheme.
      elseif(jetcom.eq.2)then
         pij = dsqrt((a(1)+b(1))**2
     .        +(a(2)+b(2))**2
     .        +(a(3)+b(3))**2)
         fact = (a(4)+b(4))/pij
         do i=1,3
            a(i) = fact*(a(i)+b(i))
         enddo
         a(4) = a(4)+b(4)
c     P scheme.
      elseif(jetcom.eq.3)then
         do i=1,3
            a(i)=a(i)+b(i)
         enddo
         a(4) = dsqrt(a(1)**2+a(2)**2+a(3)**2)
*     P0 scheme.
      elseif(jetcom.eq.4)then
         evis=evis-a(4)-b(4)
         do  i=1,3
            a(i)=a(i)+b(i)
         enddo
         a(4)=dsqrt(a(1)**2+a(2)**2+a(3)**2)
         evis=evis+a(4)
      endif
      b(4) = -1d0

      return
      end

c-----------------------------------------------------------------------
