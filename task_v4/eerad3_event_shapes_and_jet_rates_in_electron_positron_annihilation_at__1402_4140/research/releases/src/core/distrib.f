c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     This file contains subroutines to optimise phase-space
c     integration. Events are generated according to the function
c     implemented in the subroutine 'distrib'.
       
c-----------------------------------------------------------------------
c     Optimization of integration for a particular distribution.
c     (Used only for moments.)
c-----------------------------------------------------------------------

      subroutine distrib(wtdis)
      implicit real*8(a-h,o-z)
      common/jetdata/y45,y34,y23
      common/evdata/Cpar,Dpar,Spar,Apar,Planar,Tpar,
     .     Tmajor,Tminor,Opar,em2h,em2l,em2d,
     .     bmax,bmin,bsum,bdiff,
     .     FC0,FC1,FC2,FC3
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      data init/0/

c     Events are generated uniformly relative to the function
c     programmed in distrib. If this function is choosen unity
c     events will be generated according to cross section.
      if(init.eq.0.and.idist.eq.1)then
         if(iaver.eq.0)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' y23D distribution'
         elseif(iaver.eq.1)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' BW '
         elseif(iaver.eq.2)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' C parameter '
         elseif(iaver.eq.3)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' M_H^2'
         elseif(iaver.eq.4)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' 1-T '
         elseif(iaver.eq.5)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' BT parameter '
         elseif(iaver.eq.6)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' y23D '
         elseif(iaver.eq.7)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' y23J '
         elseif(iaver.eq.8)then
            write(*,*)' ***** WARNING ******'
            write(*,*)' Subroutine DISTRIB optimised for',
     .           ' y23D (unweighted) '
         endif
         init=1
      endif
      if(idist.eq.1)then
         wtdis=1d0
      else
         wtdis=1d0
      endif

      return
      end

c-----------------------------------------------------------------------
