c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains subroutines implementing the
c     soft-drop algorithm.

c-----------------------------------------------------------------------

c     Subroutine to calculate soft-drop observables.
c     Note: assumes the following subroutines to be called before:
c     - getT for ungroomed thrust axis
      subroutine getSD(tausd,rhosd,npar,zcut,beta)
      implicit none
      integer, intent(in)  :: npar
      real(8), intent(in)  :: zcut,beta
      real(8), intent(out) :: tausd,rhosd
      integer :: i,j
      integer :: nL,nR
      integer :: nclus,iclus(0:3,2)
      real(8) :: qit
      real(8) :: pphl(4,5),pphr(4,5),pseq(0:4,4,5)
      real(8) :: ppl(4,5),ppr(4,5),pjl(4),pjr(4),tal(3),tar(3)
      real(8) :: psum,psumSD,TL,TR,rhoL,rhoR,tau
      real(8) :: pp(5,15),ta(3),tmja(3),tmna(3)
c     Common blocks.
      common/Tdata/pp,ta,tmja,tmna

c     Initialise observables.
      tausd = 0d0
      rhosd = 0d0

c     Initialise hemispheres.
      pphl(:,:) = 0d0
      pphr(:,:) = 0d0
      nL = 0
      nR = 0
      psum = 0d0
      tau = 0d0
      do i=1,npar
         qit = pp(1,i)*ta(1)+pp(2,i)*ta(2)+pp(3,i)*ta(3)
         if (qit.gt.0d0)then
            nL = nL+1
            pphl(:,nL) = pp(1:4,i)
         else
            nR = nR+1
            pphr(:,nR) = pp(1:4,i)
         endif
         psum = psum
     .        + dsqrt(pp(1,i)**2+pp(2,i)**2+pp(3,i)**2)
         tau = tau + dabs(qit)
      enddo
      tau = 1d0 - tau/psum
c     Sanity check.
      if (nL.eq.0 .or. nR.eq.0)then
         print *, 'getSD: less than two hemispheres found'
         return
      endif

c     Groom jets in left hemisphere.
      call clusterjets(pphl,nL,nclus,iclus,pseq,5,1)
      call groomSD(ppl,nclus,pseq,iclus,zcut,beta)

c     Groom jets in right hemisphere.
      call clusterjets(pphr,nR,nclus,iclus,pseq,5,1)
      call groomSD(ppr,nclus,pseq,iclus,zcut,beta)

c     Calculate soft-drop thrust in both hemispheres.
      tausd  = 0d0
      psumSD = 0d0

      tal(:) = ppl(1:3,1)+ppl(1:3,2)+ppl(1:3,3)+ppl(1:3,4)+ppl(1:3,5)
      tal(:) = tal(:)/dsqrt(tal(1)**2 + tal(2)**2 + tal(3)**2)
      TL = 0d0
      do i=1,npar
         TL = TL
     .        + abs(tal(1)*ppl(1,i)+tal(2)*ppl(2,i)+tal(3)*ppl(3,i))
         psumSD = psumSD
     .        + dsqrt(ppl(1,i)**2+ppl(2,i)**2+ppl(3,i)**2)
      enddo

      tar = ppr(1:3,1)+ppr(1:3,2)+ppr(1:3,3)+ppr(1:3,4)+ppr(1:3,5)
      tar(:) = tar(:)/dsqrt(tar(1)**2 + tar(2)**2 + tar(3)**2)
      TR = 0d0
      do i=1,npar
         TR = TR
     .        + abs(tar(1)*ppr(1,i)+tar(2)*ppr(2,i)+tar(3)*ppr(3,i))
         psumSD = psumSD
     .        + dsqrt(ppr(1,i)**2+ppr(2,i)**2+ppr(3,i)**2)
      enddo

      tausd = psumSD/psum * (1d0 - (TL+TR)/psumSD)

c     Calculate jet masses in both hemispheres.
      rhosd = 0d0

      pjl(:) = ppl(:,1)+ppl(:,2)+ppl(:,3)+ppl(:,4)+ppl(:,5)
      rhoL = (pjl(4)**2-pjl(1)**2-pjl(2)**2-pjl(3)**2)/pjl(4)**2

      pjr(:) = ppr(:,1)+ppr(:,2)+ppr(:,3)+ppr(:,4)+ppr(:,5)
      rhoR = (pjr(4)**2-pjr(1)**2-pjr(2)**2-pjr(3)**2)/pjr(4)**2

      rhosd = dmax1(rhoL,rhoR)
      
      return
      end

************************************************************************

      subroutine clusterjets(ppar,npar,nclus,iclus,pseq,jetalg,jetcom)
      implicit none
      integer, intent(in)  :: npar,jetalg,jetcom
      real(8), intent(in)  :: ppar(4,5)
      integer, intent(out) :: nclus,iclus(0:3,2)
      real(8), intent(out) :: pseq(0:4,4,5)
      integer              :: i,j,ii,jj,nj
      real(8)              :: evis,vij,ei,ej,emin,ytemp,ymin
      real(8)              :: pjet(4,5)
c     Externals.
      real(8), external :: v

c     Initialise and calculate visible energy.
      pseq(:,:,:) = 0d0
      nj=npar
      evis=0d0
      do i=1,npar
         do j=1,4
            pjet(j,i)=ppar(j,i)
            pseq(0,j,i)=ppar(j,i)
         enddo
         evis=evis+pjet(4,i)
      enddo

c     Clustering algorithm.
      nclus = 0
      do while(nj.gt.1)
         ii = -1
         jj = -1
         ymin=4d0
         do i=1,npar-1
            do j=i+1,npar
               if (pjet(4,i).gt.0d0.and.pjet(4,j).gt.0d0)then
c     Here, vij=1-cos(thetaij).
                  vij=v(pjet(1,i),pjet(1,j))
                  ei=pjet(4,i)
                  ej=pjet(4,j)
                  emin=dmin1(ei,ej)
                  if (jetalg.eq.1) ytemp=2d0*ei*ej*vij/evis**2
                  if (jetalg.eq.2) ytemp=2d0*emin**2*vij/evis**2
                  if (jetalg.eq.3) ytemp=8d0*ei*ej*vij/9d0/(ei+ej)**2
                  if (jetalg.eq.5) ytemp=2d0*vij
                  if (ytemp.lt.ymin)then
                     ymin=ytemp
                     ii=i
                     jj=j
                  endif
               endif
            enddo
         enddo
         if (ii.lt.0 .or. jj.lt.0)then
            stop 'clusterjets: no clustering found'
         endif
         call jetco(pjet(1,ii),pjet(1,jj),evis,jetcom)
         pjet(1:3,jj) = 0d0
         nclus = nclus+1
         nj = nj-1

c     Save sequence.
         iclus(nclus-1,1) = ii
         iclus(nclus-1,2) = jj
         pseq(nclus,:,:) = pjet(:,:)
      enddo

      return
      end

************************************************************************

      subroutine groomSD(pp,nclus,pseq,iclus,zcut,beta)
      implicit none
      integer, intent(in)  :: nclus,iclus(0:3,2)
      real(8), intent(in)  :: pseq(0:4,4,5),zcut,beta
      real(8), intent(out) :: pp(4,5)
      logical              :: skip
      integer              :: i,ic,ii,jj,idrop
      real(8)              :: Ei,Ej,omcij,theta,val,sdc
      real(8)              :: ppgr(0:4,4,5)
c     Externals.
      real(8), external    :: v

c     Initialise grooming sequence.
      ppgr(:,:,:) = pseq(:,:,:)
      do ic=0,nclus
         do i=1,5
            if (ppgr(ic,4,i).lt.0d0) ppgr(ic,4,i) = 0d0
         enddo
      enddo

c     Initialise momenta.
      pp(:,:) = ppgr(nclus-1,:,:)
c     Special case: no clustering.
      if (nclus.eq.0) pp(:,:) = ppgr(nclus,:,:)

c     Soft-drop algorithm.
      idrop = 0
      skip = .false.
      do ic=nclus-1,0,-1
         pp(:,:) = ppgr(ic,:,:)
         ii = iclus(ic,1)
         jj = iclus(ic,2)
         Ei = pp(4,ii)
         Ej = pp(4,jj)

c     Delete clusterings in already groomed jets.
         if (Ei.le.0d0 .or. Ej.le.0d0)then
            pp(:,ii) = 0d0
            pp(:,jj) = 0d0
            ppgr(:,:,ii) = 0d0
            ppgr(:,:,jj) = 0d0
            cycle
         endif
         if (skip) cycle

c     Check soft-drop condition and terminate if satisfied.
         omcij = v(pp(1,ii),pp(1,jj))
         theta = acos(1-omcij)
         val = dmin1(Ei,Ej)/(Ei+Ej)
         sdc = zcut*theta**beta
         if (val.gt.sdc)then
            skip = .true.
            cycle
         endif

c     Remove softer jet.
         if (Ei.lt.Ej)then
            idrop = ii
         else
            idrop = jj
         endif
         if (idrop.gt.0)then
            pp(:,idrop) = 0d0
            ppgr(:,:,idrop) = 0d0
         endif
         idrop = 0
      enddo

      return
      end

c-----------------------------------------------------------------------
