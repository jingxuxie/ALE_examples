c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Antenna functions.
c     Equation numbers refer to hep-ph/0505111.
c
c     Note: all antenna functions available in two forms.
c     a) using invariants
c     b) using indices referring to specific common blocks
c     Using option a) should always be preferred!

c-----------------------------------------------------------------------
c     Three-parton tree-level antenna functions using invariants.
c-----------------------------------------------------------------------

c     Antenna function for q-g-qb.
      real(8) function A30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123 = s12+s13+s23
      A30n = 1d0/s123*(s13/s23+s23/s13+2d0*s12*s123/s13/s23)
      return
      end

************************************************************************

c     Sub-antenna function for q-g-g.
      real(8) function sd30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123  = s12+s13+s23
      sd30n = 1d0/s123**2*(
     .     + 2d0*s123**2*s12/s13/s23
     .     + (s12*s23+s23**2)/s13
     .     + s13*s12/s23+5d0/2d0*s123+s23/2d0
     .     )
      return
      end

************************************************************************

c     D30(1,3,4) = sd30(1,3,4)+sd30(1,4,3).
      real(8) function D30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
c     Externals.
      real(8), external   :: sd30n
c     D30 as in (6.12).
      D30n = sd30n(s12,s13,s23)+sd30n(s13,s12,s23)
      return
      end

************************************************************************

c     Antenna function for x-q-qbar.
      real(8) function E30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123 = s12+s13+s23
c     E30 as in (6.14).
      E30n = 1d0/s123**2*(s13+s12+(s13**2+s12**2)/s23)
      return
      end

************************************************************************

c     Sub-antenna function for g-g-g.
      real(8) function sf30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123  = s13+s12+s23
      sf30n = 1d0/s123**2*(
     .     2d0*s123**2*s12/s13/s23
     .     + s12*s23/s13
     .     + s12*s13/s23
     .     + 8d0/3d0*s123)
      return
      end

************************************************************************

c     F30(1,2,3) = sf30(1,3,2)+sf30(3,2,1)+sf30(2,1,3).
      real(8) function F30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123 = s12+s13+s23
c     F30 as in (7.8).
      F30n = 2d0/s123**2*(s123**2*s12/s13/s23 + s123**2*s13/s12/s23
     .     + s123**2*s23/s12/s13 + s12*s13/s23 + s12*s23/s13
     .     + s13*s23/s12 + 4d0*s123)
      return
      end

************************************************************************

c     Antenna function for g-q-qbar.
      real(8) function G30n(s12,s13,s23)
      implicit none
      real(8), intent(in) :: s12,s13,s23
      real(8)             :: s123
      s123 = s12+s13+s23
c     G30 as in (7.14).      
      G30n = 1d0/s123**2*(s13**2+s12**2)/s23
      return
      end

c-----------------------------------------------------------------------
c     Three-parton tree-level antenna functions using invariants.
c
c     Legacy version only used in Zqq process.
c     Usage should be replaced by X30n functions above.
c-----------------------------------------------------------------------

c     A30(ia,iu,ib) depending on invariants instead of i's
c     includes proper normalisation, don't use T(w12,..)/x12 any longer.
      function A30y5map(sab,sau,sub)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      A30y5map=sa30y5map(sab,sau,sub)+sa30y5map(sab,sub,sau)
      return
      end

************************************************************************

c     Small sa30(ia,iu,ib) depending on redefined momenta.
      function sa30y5map(sab,sau,sub)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      saub=sab+sau+sub
      sa30y5map=1d0/saub
     .     *( sub/sau+2d0*sab*saub/sau/(sau+sub) ) 
      return
      end

************************************************************************

c     g-g-q antenna with reversed arguments of d30.
      function D30y5map(s14,s13,s34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
      D30y5map=sd30y5map(s14,s13,s34)+sd30y5map(s13,s14,s34)
      return
      end

************************************************************************

c     If dependence on invariants of pmap is needed.
      function sd30y5map(y14,y13,y34)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      y134=y13+y14+y34
      sd30y5map=1d0/y134**2*( 2d0*y134**2*y14/y13/y34
     &     + (y14*y34+y34**2)/y13
     &     +  y13*y14/y34+5d0/2d0*y134+y34/2d0 )
      return
      end

************************************************************************

c     If dependence on invariants of pmap is needed:
      function E30y5map(s13,s14,s34)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      s134=s13+s14+s34
      E30y5map=1d0/s134**2*( (s13**2+s14**2)/s34+s13+s14 )
      return
      end

************************************************************************

c     Q30 = d30(1,3,4) - A30(1,3,4).
      function Q30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      y134 = y13+y14+y34
      Q30y5map= 1/y134**2* 
     .     (3d0/2d0*y13 -y13**2/y34 +2d0*y34 +5d0/2d0*y14)
      return
      end

************************************************************************

c     R30 = d30(1,3,4) - A30(1,3,4) - d30(1,4,3) + A30(1,4,3).
      function R30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      y134 = y13+y14+y34
      R30y5map= Q30y5map(y13,y14,y34) - Q30y5map(y14,y13,y34)
      return
      end

************************************************************************

      function S30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      y134 = y13+y14+y34
      S30y5map= 1/y134**2*(5d0*y134-y34) 
      return
      end

c-----------------------------------------------------------------------
c     Three-parton tree-level antenna functions using yij4.
c
c     Common block yij4 is filled in phase4.
c-----------------------------------------------------------------------

c     Antenna function for q-g-qb.
      function A30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yub+yab
      A30=1d0/yaub 
     .     *(yau/yub+yub/yau+2d0*yab*yaub/yau/yub) 
      return
      end

************************************************************************

c     Sub-antenna function for q-g-g.
      function sd30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sd30=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .               + (yab*yub+yub**2)/yau
     .               +  yau*yab/yub+5d0/2d0*yaub+yub/2d0 )
      return
      end

************************************************************************

c     D30(1,3,4)=sd30(1,3,4)+sd30(1,4,3).
      function D30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      external sd30
c     D30 as in (6.12).
      D30=sd30(ia,iu,ib)+sd30(ia,ib,iu)
      return
      end

************************************************************************

c     Antenna function for x-q-qbar.
      function E30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
c     E30 as in (6.14).
      E30=1d0/yaub**2*( (yau**2+yab**2)/yub+yau+yab )
      return
      end

************************************************************************

c     Sub-antenna function for g-g-g.
      function sf30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sf30=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .     + yab*yub/yau
     .     + yab*yau/yub
     .     + 8d0/3d0*yaub )
      return
      end

************************************************************************

c     Antenna function for g-q-qbar.
      function G30(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
c     G30 as in (7.14).
      G30=1d0/yaub**2*(yau**2+yab**2)/yub 
      return
      end

c-----------------------------------------------------------------------
c     Three-parton tree-level antenna functions using yij5.
c
c     Common block yij5 is filled in phase5.
c-----------------------------------------------------------------------

      function A30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yub+yab
      A30y5=1d0/yaub 
     .     *(yau/yub+yub/yau+2d0*yab*yaub/yau/yub) 
      return
      end

************************************************************************

c     A30(ia,iu,ib)=sa30(ia,iu,ib)+sa30(ib,iu,ia) (5.9).
      function sa30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yub+yab
      sa30y5=1d0/yaub 
     .     *( yub/yau+2d0*yab*yaub/yau/(yau+yub) ) 
      return
      end

************************************************************************

c     D30(1,3,4)=sd30(1,3,4)+sd30(1,4,3) (6.12) q-g-g antenna.
      function sd30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sd30y5=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .     + (yab*yub+yub**2)/yau
     .     +  yau*yab/yub+5d0/2d0*yaub+yub/2d0 )
      return
      end

************************************************************************

c     x-q-qbar antenna (6.14).
      function E30y5(i1,i3,i4)
      implicit real*8(a-h,o-z)
      common/tcuts/ymin,y0
      common/yij5/y(5,5)
      y13=y(i1,i3)
      y34=y(i3,i4)
      y14=y(i1,i4)
      y134=y13+y14+y34
      E30y5=1d0/y134**2*( (y13**2+y14**2)/y34+y13+y14 )
      return
      end

************************************************************************

c     g-g-g antenna:
c     F30(1,2,3)=sf30(1,3,2)+sf30(3,2,1)+sf30(2,1,3) (7.12).
c     22.06.06: 2/3*s123 -> 8/3*s123 corrected.
      function sf30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sf30y5=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .     + yab*yub/yau
     .     + yab*yau/yub
     .     + 8d0/3d0*yaub )
      return
      end

************************************************************************

c     g-q-qbar antenna: (7.14).
      function G30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      G30y5=1d0/yaub**2*(yau**2+yab**2)/yub 
      return
      end

c-----------------------------------------------------------------------
c     Integrated three-parton tree-level antenna functions.
c-----------------------------------------------------------------------

      real(8) function A30int(sij,renscale2,ipole)
      implicit none
      real(8), intent(in) :: sij,renscale2
      integer, intent(in) :: ipole
      real(8)             :: dlogs,e2,e1,e0,pi
      integer             :: ischeme
      parameter(pi=3.141592653589793238d0)

      dlogs = log(renscale2/sij)

      ischeme = 0
      e2 = 1
      e1 = 3d0/2d0
      e0 = 19d0/4d0 - 7d0/12d0*pi**2
      if (ischeme.eq.0) e0 = e0 + pi**2/12d0*e2

      A30int = 0d0
      select case (ipole)
      case(-2)
         A30int = e2
      case(-1)
         A30int = e1 + e2*dlogs
      case(0)
         A30int = e0 + e1*dlogs + e2*dlogs**2/2d0
      end select

      return
      end

************************************************************************

      real(8) function D30int(sij,renscale2,ipole)
      implicit none
      real(8), intent(in) :: sij,renscale2
      integer, intent(in) :: ipole
      real(8)             :: dlogs,e2,e1,e0,pi
      integer             :: ischeme
      parameter(pi=3.141592653589793238d0)

      dlogs = log(renscale2/sij)

      ischeme = 0
      e2 = 2d0
      e1 = 10d0/3d0
      e0 = 34d0/3d0 - 7d0/6d0*pi**2
      if (ischeme.eq.0) e0 = e0 + pi**2/12d0*e2

      D30int = 0d0
      select case (ipole)
      case(-2)
         D30int = e2
      case(-1)
         D30int = e1 + e2*dlogs
      case(0)
         D30int = e0 + e1*dlogs + e2*dlogs**2/2d0
      end select

      return
      end

************************************************************************

      real(8) function E30int(sij,renscale2,ipole)
      implicit none
      real(8), intent(in) :: sij,renscale2
      integer, intent(in) :: ipole
      real(8)             :: dlogs,e2,e1,e0,pi
      integer             :: ischeme
      parameter(pi=3.141592653589793238d0)

      dlogs = log(renscale2/sij)

      ischeme = 0
      e2 = 0d0
      e1 = -1d0/3d0
      e0 = -1d0
      if (ischeme.eq.0) e0 = e0 + pi**2/12d0*e2

      E30int = 0d0
      select case (ipole)
      case(-2)
         E30int = e2
      case(-1)
         E30int = e1 + e2*dlogs
      case(0)
         E30int = e0 + e1*dlogs + e2*dlogs**2/2d0
      end select

      return
      end

************************************************************************

      real(8) function F30int(sij,renscale2,ipole)
      implicit none
      real(8), intent(in) :: sij,renscale2
      integer, intent(in) :: ipole
      real(8)             :: dlogs,e2,e1,e0,pi
      integer             :: ischeme
      parameter(pi=3.141592653589793238d0)

      dlogs = log(renscale2/sij)

      ischeme = 0
      e2 = 3d0
      e1 = 11d0/2d0
      e0 = 73d0/4d0 - 7d0/4d0*pi**2
      if (ischeme.eq.0) e0 = e0 + pi**2/12d0*e2

      F30int = 0d0
      select case (ipole)
      case(-2)
         F30int = e2
      case(-1)
         F30int = e1 + e2*dlogs
      case(0)
         F30int = e0 + e1*dlogs + e2*dlogs**2/2d0
      end select

      return
      end

************************************************************************

      real(8) function G30int(sij,renscale2,ipole)
      implicit none
      real(8), intent(in) :: sij,renscale2
      integer, intent(in) :: ipole
      real(8)             :: dlogs,e2,e1,e0,pi
      integer             :: ischeme
      parameter(pi=3.141592653589793238d0)

      dlogs = log(renscale2/sij)

      ischeme = 0
      e2 = 0d0
      e1 = -1d0/3d0
      e0 = -7d0/6d0
      if (ischeme.eq.0) e0 = e0 + pi**2/12d0*e2

      G30int = 0d0
      select case (ipole)
      case(-2)
         G30int = e2
      case(-1)
         G30int = e1 + e2*dlogs
      case(0)
         G30int = e0 + e1*dlogs + e2*dlogs**2/2d0
      end select

      return
      end

c-----------------------------------------------------------------------
c     Three-parton one-loop antenna functions.
c-----------------------------------------------------------------------

c     Leading-colour antenna function for q-g-qb.
      function A31(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123=s12+s13+s23
c     A31 as in (5.13): A31=(FCA+FCF/2)/s123.
c     FCF,FCA are defined at the end of this file.
      A31=FCA(s12,s13,s23)+FCF(s12,s13,s23)/2d0
      A31=A31/s123
      return
      end

************************************************************************

c     Subleading colour antenna function for q-g-qb.
      function A31t(s12,s13,s23)
      implicit real*8(a-h,o-z)
      A31t = tilda31(s12,s13,s23)
      return
      end

************************************************************************

      function tilda31(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)

      s123=s12+s13+s23
      y12=s12/s123
      y13=s13/s123
      y23=s23/s123

      omy12=1d0-y12
      omy13=1d0-y13
      omy23=1d0-y23

      r1213=log(y12)*log(y13)-log(y12)*log(omy12)-log(y13)*log(omy13)
     .     +pi**2/6d0-rli2(y12)-rli2(y13)
      r1223=log(y12)*log(y23)-log(y12)*log(omy12)-log(y23)*log(omy23)
     .     +pi**2/6d0-rli2(y12)-rli2(y23)

c     A31t as in (5.15): tildeA31=1/2*(FCF+8*T)/s123.
      tilda31 =
     .     +(y12/(y12+y13)+y12/(y12+y23)+(y12+y23)/y13+(y12+y13)/y23)
     .     +log(y13)*((4d0*y12**2+2d0*y12*y13
     .     +4d0*y12*y23+y13*y23)/(y12+y23)**2)
     .     +log(y23)*((4d0*y12**2+2d0*y12*y23
     .     +4d0*y12*y13+y13*y23)/(y12+y13)**2)
     .     -2d0*((y12**2+(y12+y13)**2)/y13/y23*r1223
     .     +(y12**2+(y12+y23)**2)/y13/y23*r1213
     .     +(y13**2+y23**2)/y13/y23/(y13+y23)
     .     -2d0*log(y12)*(y12**2/(y13+y23)**2+2d0*y12/(y13+y23)) )

c     Correction such that finite piece remains after I1 extracted.
      tilda31=(tilda31-3d0*log(y12)*T(y12,y13,y23))/2d0/s123
c     1/s123 to have normalisation of (3.3).
      return
      end

************************************************************************

c     Quark-loop antenna function for q-g-qb.
      function A31hat(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123=s12+s13+s23
      y13=s13/s123
      y23=s23/s123
c     A31hat as in (5.17).
      A31hat=1d0/6d0*(dlog(y13)+dlog(y23))*T(s12,s13,s23)/s123
      return
      end

************************************************************************

c     x-g-g antenna: (6.19).
      function sd31(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sd30e=sd30(ia,iu,ib)
      sd31= -( Rli(yau/yaub,yub/yaub) + Rli(yab/yaub,yub/yaub)
     .     + Rli(yau/yaub,yab/yaub) 
     .     + 5d0/3d0*dlog(yau/yaub) 
     .     + 5d0/3d0*dlog(yab/yaub) 
     .     + 11d0/6d0*dlog(yub/yaub) )*sd30e
     .     + 1d0/6d0/yub
      return
      end

************************************************************************

c     x-q-qbar antenna: (6.29).
      function E31(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      E30e=E30(ia,iu,ib)
      E31= -( Rli(yau/yaub,yub/yaub) + Rli(yab/yaub,yub/yaub) 
     .     + 3d0/2d0*dlog(yau/yaub) 
     .     + 3d0/2d0*dlog(yab/yaub) 
     .     + 13d0/6d0*dlog(yub/yaub) 
     .     - 40d0/9d0)*E30e
     .     + Rli(yau/yaub,yub/yaub)*yau/yaub**2
     .     + Rli(yab/yaub,yub/yaub)*yab/yaub**2
      return
      end

************************************************************************

c     x-q-qbar: (6.31).
      function E31t(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common/yij4/y(4,4)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      E30e=E30(ia,iu,ib)
      E31t=-4d0*E30e
      return
      end

************************************************************************
      
c     Antenna function for g-g-g.
      function F31_(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123 = s12+s13+s23
      y12 = s12/s123
      y13 = s13/s123
      y23 = s23/s123
      R1213 = log(y12)*log(y13) - log(y12)*log(1d0-y12)
     .     - log(y13)*log(1d0-y13) + pi**2/6d0 - rli2(y12) - rli2(y13)
      R1323 = log(y13)*log(y23) - log(y13)*log(1d0-y13)
     .     - log(y23)*log(1d0-y23) + pi**2/6d0 - rli2(y13) - rli2(y23)
      R1223 = log(y12)*log(y23) - log(y12)*log(1d0-y12)
     .     - log(y23)*log(1d0-y23) + pi**2/6d0 - rli2(y12) - rli2(y23)
c     F31 as in (7.19).
      F31_ = -(R1213 + R1323 + R1223 + 11d0/6d0*log(y12)
     .     + 11d0/6d0*log(y13) + 11d0/6d0*log(y23))*F30n(s12,s13,s23)
      return
      end

************************************************************************

c     Quark-loop antenna function for g-g-g.
      function F31hat(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123 = s12+s13+s23
      y12 = s12/s123
      y13 = s13/s123
      y23 = s23/s123
c     F31hat as in (7.21).
      F31hat = 1d0/3d0*((log(y12) + log(y13) + log(y23))
     .     *F30n(s12,s13,s23)
     .     - 1d0/s12 - 1d0/s13 - 1d0/s23 - 1d0/s123)
      return
      end

************************************************************************

c     Antenna function for g-q-qb.
      function G31(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123 = s12+s13+s23
      y12 = s12/s123
      y13 = s13/s123
      y23 = s23/s123
      R1223 = log(y12)*log(y23) - log(y12)*log(1d0-y12)
     .     - log(y23)*log(1d0-y23) + pi**2/6d0 - rli2(y12) - rli2(y23)
      R1323 = log(y13)*log(y23) - log(y13)*log(1d0-y13)
     .     - log(y23)*log(1d0-y23) + pi**2/6d0 - rli2(y13) - rli2(y23)
c     G31 as in (7.29).
      G31 = -(R1223 + R1323 + 5d0/3d0*log(y12) + 5d0/3d0*log(y13)
     .     + 13d0/6d0*log(y23) - 40d0/9d0)*G30n(s12,s13,s23)
     .     - (s12+s13)/2d0/s123**2

      return
      end

************************************************************************

      function G31tilde(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123 = s12+s13+s23
      y12 = s12/s123
      y13 = s13/s123
      y23 = s23/s123
      R1213 = log(y12)*log(y13) - log(y12)*log(1d0-y12)
     .     - log(y13)*log(1d0-y13) + pi**2/6d0 - rli2(y12) - rli2(y13)
c     G31tilde as in (7.31).
      G31tilde = -(4d0 + R1213)*G30n(s12,s13,s23) + (s12+s13)/2/s123**2
      return
      end

************************************************************************

      function G31hat(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      s123 = s12+s13+s23
      y12 = s12/s123
      y13 = s13/s123
      y23 = s23/s123
c     G31hat as in (7.33).
      G31hat = (-10d0/9d0 + 2d0/3d0*log(y23) + 1d0/6d0*log(y12)
     .     + 1d0/6d0*log(y13))*G30n(s12,s13,s23)
      return
      end

c-----------------------------------------------------------------------
c     Four-parton tree-level antenna functions using invariants.
c-----------------------------------------------------------------------
      
c     Leading-colour antenna function for q-g-g-qb.
      real(8) function A40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s134=s13+s14+s34
      s234=s23+s24+s34
      s1234=s134+s234-s34+s12

      wt=0d0
      wt =
     &  + s134**(-2) * ( 2*s12*s13*s14**2*s24 + s12*s13*s24*s34**2 +
     &    s12*s24*s34**3 + 2*s13*s14**2*s23*s24 + 2*s13*s14**2*s24**2
     &     + s13*s23*s24*s34**2 + s13*s24**2*s34**2 + s23*s24*s34**3 +
     &    s24**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 4*s12*s13*s14*s24*s34 - 4*
     &    s12*s13*s14*s24**2 - 3*s12*s13*s14*s34**2 + 6*s12*s13*s24*
     &    s34**2 + 3*s12*s13*s34**3 + 6*s12*s24*s34**3 + 3*s12*s24**2*
     &    s34**2 + 3*s12*s34**4 - 8*s12**2*s13*s24*s34 - 4*s12**2*s13*
     &    s34**2 - 4*s12**2*s24*s34**2 - 4*s12**2*s34**3 + 2*s12**3*
     &    s34**2 + 3*s13*s14*s24*s34**2 + 4*s13*s14*s24**2*s34 + s13*
     &    s14*s34**3 - 2*s13*s14**2*s24*s34 - s13*s14**2*s34**2 - 3*s13
     &    *s24*s34**3 - 3*s13*s24**2*s34**2 - 2*s13*s24**3*s34 - s13*
     &    s34**4 - 3*s24*s34**4 - 3*s24**2*s34**3 - s24**3*s34**2 -
     &    s34**5 )
      wt = wt + s134**(-1) * ( 2*s12*s13*s14*s34 + 2*s12*s13*s23*s34 -
     &    8*s12*s13*s24*s34 - 4*s12*s13*s34**2 + 3*s12*s23*s34**2 - 6*
     &    s12*s24*s34**2 - 3*s12*s34**3 + 2*s12**2*s13*s34 + 4*s12**2*
     &    s34**2 + 2*s13*s14*s23*s34 - 2*s13*s14*s24*s34 - 4*s13*s14*
     &    s24**2 - s13*s14*s34**2 + 2*s13*s14**2*s24 + s13*s14**2*s34
     &     - 3*s13*s23*s24*s34 - s13*s23*s34**2 + s13*s23**2*s34 + s13*
     &    s24*s34**2 - s13*s24**2*s34 + s13*s34**3 - 3*s23*s24*s34**2
     &     - s23*s34**3 + s23**2*s34**2 + 2*s24*s34**3 - s24**2*s34**2
     &     + s34**4 )
      wt = wt + s234**(-2) * ( 3*s12*s13*s24*s34**2 + 4*s12*s13*s24**2*
     &    s34 + 2*s12*s13*s24**3 + s12*s13*s34**3 + 3*s13*s14*s24*
     &    s34**2 + 4*s13*s14*s24**2*s34 + 2*s13*s14*s24**3 + s13*s14*
     &    s34**3 + 3*s13**2*s24*s34**2 + 4*s13**2*s24**2*s34 + 2*s13**2
     &    *s24**3 + s13**2*s34**3 )
      wt = wt + s234**(-1) * (  - 8*s12*s13*s24*s34 - 3*s12*s13*s34**2
     &     + 2*s12*s14*s24*s34 + 3*s12*s14*s34**2 - 6*s12*s24*s34**2 -
     &    2*s12*s24**2*s34 - 3*s12*s34**3 + 2*s12**2*s24*s34 + 4*s12**2
     &    *s34**2 - 5*s13*s14*s24*s34 - 4*s13*s14*s24**2 - 2*s13*s14*
     &    s34**2 + 2*s13*s24**2*s34 + 2*s13*s24**3 - 3*s13**2*s24*s34
     &     - 2*s13**2*s34**2 - 3*s14*s24*s34**2 - 2*s14*s24**2*s34 -
     &    s14*s34**3 + s14**2*s24*s34 + s14**2*s34**2 + 3*s24*s34**3 +
     &    3*s24**2*s34**2 + s24**3*s34 + s34**4 )
      wt = wt + 4*s12*s13*s34 + 2*s12*s14*s34 + 2*s12*s23*s34 + 6*s12*
     &    s24*s34 + 6*s12*s34**2 + 2*s12**2*s34 + 3*s13*s14*s34 - 2*s13
     &    *s24*s34 + 2*s13**2*s34 + 2*s14*s24*s34 + 3*s14*s34**2 +
     &    s14**2*s34 + 4*s23*s24*s34 + 3*s23*s34**2 + s23**2*s34 - 2*
     &    s24*s34**2 + s24**2*s34

      A40=wt/s34**2/s13/s24
        
      return
      end

************************************************************************

c     Sub-leading colour antenna function for q-g-g-qb.
c     A40tilde is equal to Aslc/2, equal to A40tsub of ana/A40.sub
c     sum over small atildes (5.28) already contained in A40tilde.
c     NOTE: A40tilde is NOT normalized to s1234!!
c     for 4 parton this dose not matter as s1234=1.
c     for 5 parton use always Aqppq(i1,i3,i4,i2).
      real(8) function A40tilde(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s134=s13+s14+s34
      s234=s23+s24+s34
      wt=0d0

      wt = wt +   ( s13**3*s24**2 + s13**3*s24
     +    *s12 - s13**2*s14*s24**2 + s13**2*s14*s24*s12 - s13**2*
     +    s23*s24**2 - s13**2*s23*s24*s12 + s13**2*s24**3 + 4*
     +    s13**2*s24**2*s12 + 4*s13**2*s24*s12**2 - s13*s14**2*
     +    s23**2 + s13*s14**2*s23*s12 - s13*s14*s23**2*s12 - 4*s13
     +    *s14*s23*s24*s12 + 4*s13*s14*s23*s12**2 - s13*s14*
     +    s24**2*s12 + 4*s13*s14*s24*s12**2 + s13*s23*s24**2*s12
     +     + 4*s13*s23*s24*s12**2 + 4*s13*s23*s12**3 + s13*s24**3
     +    *s12 + 4*s13*s24**2*s12**2 + 4*s13*s24*s12**3 + s14**3*
     +    s23**2 + s14**3*s23*s12 + s14**2*s23**3 - s14**2*s23**2*
     +    s24 + 4*s14**2*s23**2*s12 - s14**2*s23*s24*s12 + 4*
     +    s14**2*s23*s12**2 + s14*s23**3*s12 + s14*s23**2*s24*
     +    s12 + 4*s14*s23**2*s12**2 + 4*s14*s23*s24*s12**2 + 4*
     +    s14*s23*s12**3 + 4*s14*s24*s12**3 )/s134/s234

      wt = wt +  (  - 2*s13**2*s23*s24 - 2*s13**2*s23*
     +    s12 + s13**2*s24**2 + s13**2*s24*s12 - 2*s13*s14*s23**2
     +     - 2*s13*s14*s23*s24 - 2*s13*s14*s24**2 + 2*s13*s23**2*
     +    s12 + 2*s13*s23*s24*s12 + 4*s13*s23*s12**2 + 2*s13*
     +    s24**3 + 5*s13*s24**2*s12 + 4*s13*s24*s12**2 + s14**2*
     +    s23**2 - 2*s14**2*s23*s24 + s14**2*s23*s12 - 2*s14**2*
     +    s24*s12 + 2*s14*s23**3 + 5*s14*s23**2*s12 + 2*s14*s23*
     +    s24*s12 + 4*s14*s23*s12**2 + 2*s14*s24**2*s12 + 4*s14*
     +    s24*s12**2 )/s134

      wt = wt + s23*s24 * (  - 2*s13**2*s23 - 2*s13**2*
     +    s24 - 2*s13**2*s12 - 2*s14**2*s23 - 2*s14**2*s24 - 2*
     +    s14**2*s12 )/s134**2

      wt = wt +  ( 2*s13**3*s24 - 2*s13**2*s23*s24 + 2*
     +    s13**2*s23*s12 + s13**2*s24**2 + 5*s13**2*s24*s12 - 2*
     +    s13*s14*s23**2 - 2*s13*s14*s23*s24 + 2*s13*s14*s23*s12
     +     - 2*s13*s14*s24**2 + 2*s13*s14*s24*s12 - 2*s13*s23**2*
     +    s12 + 4*s13*s23*s12**2 + s13*s24**2*s12 + 4*s13*s24*
     +    s12**2 + 2*s14**3*s23 + s14**2*s23**2 - 2*s14**2*s23*s24
     +     + 5*s14**2*s23*s12 + 2*s14**2*s24*s12 + s14*s23**2*s12
     +     + 4*s14*s23*s12**2 - 2*s14*s24**2*s12 + 4*s14*s24*
     +    s12**2 )/s234

      wt = wt + s13*s14 * (  - 2*s13*s23**2 - 2*s13*
     +    s24**2 - 2*s14*s23**2 - 2*s14*s24**2 - 2*s23**2*s12 - 2*
     +    s24**2*s12 )/s234**2

      wt = wt + 4*s13**2*s24 + 2*s13**2*s12 + 4*s13*s14*s12 + 4*s13*
     +    s23*s12 + 4*s13*s24**2 + 6*s13*s24*s12 + 2*s13*s24*s34
     +     + 4*s13*s12**2 + 4*s14**2*s23 + 2*s14**2*s12 + 4*s14*
     +    s23**2 + 6*s14*s23*s12 + 2*s14*s23*s34 + 4*s14*s24*s12
     +     + 4*s14*s12**2 + 2*s23**2*s12 + 4*s23*s24*s12 + 4*s23
     +    *s12**2 + 2*s24**2*s12 + 4*s24*s12**2 + 4*s12**3
  

      A40tilde=wt/s13/s14/s23/s24/2d0 

      return
      end

************************************************************************

c     Antenna function for q-q'-qb'-qb.
c     B40below = B40 of (5.37)*s1234
      real(8) function B40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s134=s13+s14+s34
      s234=s23+s24+s34
      wt=0d0
      wt = wt +  ( 2*s12**2*s34 - 2*s12*s13*s24
     +     + s12*s13*s34 - 2*s12*s14*s23 + s12*s14*s34 + 
     +     s12*s23*s34 + 
     +    s12*s24*s34 + 2*s12*s34**2 - s13**2*s24 + 
     +    s13*s14*s23 + s13*
     +    s14*s24 + s13*s23*s24 - s13*s24**2 - 
     +    s14**2*s23 - s14*s23**2
     +     + s14*s23*s24 )/s134/s234

      wt = wt +  ( 2*s12*s13*s14 + s12*s13*s34 + s12*s14*
     +    s34 - s13**2*s24 + s13*s14*s23 + s13*s14*s24 + 
     +   s13*s23*s34 - 
     +    s14**2*s23 + s14*s24*s34 )/s134**2

      wt = wt +  ( 2*s12*s23*s24 + s12*s23*s34 + s12*s24*
     +    s34 + s13*s23*s24 + s13*s23*s34 - s13*s24**2 - 
     +    s14*s23**2 + 
     +    s14*s23*s24 + s14*s24*s34 )/s234**2

      B40 = wt/s34**2
    
      return
      end

************************************************************************

c     Same-flavour antenna function for q-q-qb-qb.
c     C40 IS normalised to 1/s1234^2, in contrast to
c     A40,B40,A40tilde.
c     For 4-parton this does not matter since s1234=1.
c     For 5-parton always use X40i(i1,i2,i3,i4).
      real(8) function C40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s134=s13+s14+s34
      s123=s23+s12+s13
      s124=s12+s14+s24
      s234=s23+s24+s34
      
      s1234=s12+s13+s14+s23+s24+s34
      y12=s12/s1234
      y13=s13/s1234
      y14=s14/s1234
      y23=s23/s1234
      y24=s24/s1234
      y34=s34/s1234
      y134=y13+y14+y34
      y123=y23+y12+y13
      y124=y12+y14+y24
      y234=y23+y24+y34
      
      wt=0d0
      wt = wt + y23**(-1)*y34**(-1)*y123**(-1)*y134**(-1) * 
     .     ( 2*y12*y13
     .     *y14 + 2*y12*y13*y34 + 2*y13*y14*y23 + 2*y13*y23*y34 )
      
      wt = wt + y23**(-1)*y34**(-1)*y123**(-1)*y234**(-1) * 
     .     ( y12**2*
     .     y34 - y12*y13*y24 - y12*y14*y23 + y12*y14*y34 + 
     .     y12*y23*y34
     .     + y12*y34**2 + y13*y14*y24 - y13*y23*y24 - y13*y24*y34 - 
     .     y14**2*y23 - y14*y23**2 - y14*y23*y34 )

      wt = wt + y23**(-1)*y34**(-1)*y134**(-1)*y234**(-1) * 
     .     (  - y12**2
     .     *y34 + y12*y13*y24 + y12*y14*y23 - y12*y14*y34 - 
     .     y12*y23*y34
     .     - y12*y34**2 - y13*y14*y24 - y13*y23*y24 - y13*y24*y34 + 
     .     y14**2*y23 + y14*y23**2 + y14*y23*y34 )

      wt = wt + y23**(-1)*y34**(-1)*y234**(-2) * 
     .     (  - 2*y12*y23*y24 - 2
     .     *y12*y24*y34 + 2*y13*y24**2 - 2*y14*y23*y24 - 
     .     2*y14*y24*y34 )

      C40 = -wt/2.d0/s1234**2

      return
      end

************************************************************************

c     Antenna function for q-g-g-g.
      real(8) function D40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s134=s13+s14+s34
      s123=s23+s12+s13
      s124=s12+s14+s24
      s234=s23+s24+s34
      
      s1234=s12+s13+s14+s23+s24+s34
      y12=s12/s1234
      y13=s13/s1234
      y14=s14/s1234
      y23=s23/s1234
      y24=s24/s1234
      y34=s34/s1234
      y134=y13+y14+y34
      y123=y23+y12+y13
      y124=y12+y14+y24
      y234=y23+y24+y34
      
      wt = 0d0
      
      wt =
     &     + s123**(-2)*(4*s12*s13**2*s14*s24*s34**3 + 2*s12*s13**2*s14
     &     *s24**2*s34**2 + 2*s12*s13**2*s14*s34**4 + 4*s12*s13**2*
     &     s14**2*s24*s34**2 + 4*s12*s13**2*s14**2*s34**3 + 2*s12*s13**2
     &     *s14**3*s34**2 + 2*s12*s14*s23**2*s24*s34**3 + s12*s14*s23**2
     &     *s24**2*s34**2 + s12*s14*s23**2*s34**4 + 2*s12*s14**2*s23**2*
     &     s24*s34**2 + 2*s12*s14**2*s23**2*s34**3 + s12*s14**3*s23**2*
     &     s34**2 + 2*s14*s23**3*s24*s34**3 + s14*s23**3*s24**2*s34**2
     &     + s14*s23**3*s34**4 + 2*s14**2*s23**3*s24*s34**2 + 2*s14**2*
     &     s23**3*s34**3 + s14**3*s23**3*s34**2 )
      wt = wt + s123**(-1)*s124**(-1) * ( 6*s12*s14*s23*s24*s34**4 + 9*
     &     s12*s14*s23*s24**2*s34**3 + 4*s12*s14*s23*s24**3*s34**2 + s12
     &     *s14*s23*s34**5 - 9*s12*s14*s23**2*s24*s34**3 - 9*s12*s14*
     &     s23**2*s24**2*s34**2 + 6*s12*s14*s23**3*s24*s34**2 - s12*s14*
     &     s23**4*s34**2 + 9*s12*s14**2*s23*s24*s34**3 + 6*s12*s14**2*
     &     s23*s24**2*s34**2 + 3*s12*s14**2*s23*s34**4 - 9*s12*s14**2*
     &     s23**2*s24*s34**2 + 3*s12*s14**2*s23**3*s34**2 + 5*s12*s14**3
     &     *s23*s24*s34**2 + 3*s12*s14**3*s23*s34**3 - 3*s12*s14**3*
     &     s23**2*s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s24*s34**5
     &     + 3*s12*s23*s24**2*s34**4 + 3*s12*s23*s24**3*s34**3 + s12*
     &     s23*s24**4*s34**2 - 3*s12*s23**2*s24*s34**4 - 6*s12*s23**2*
     &     s24**2*s34**3 - 3*s12*s23**2*s24**3*s34**2 + 3*s12*s23**3*s24
     &     *s34**3 + 3*s12*s23**3*s24**2*s34**2 - s12*s23**4*s24*s34**2
     &     )
      wt = wt + s123**(-1)*s134**(-1) * ( 12*s12*s14*s23*s24*s34**4 + 9
     &     *s12*s14*s23*s24**2*s34**3 + 2*s12*s14*s23*s24**3*s34**2 + 5*
     &     s12*s14*s23*s34**5 - 6*s12*s14*s23**2*s24*s34**3 - 8*s12*s14*
     &     s23**2*s34**4 + 3*s12*s14*s23**3*s34**3 + 18*s12*s14**2*s23*
     &     s24*s34**3 + 9*s12*s14**2*s23*s24**2*s34**2 + s12*s14**2*s23*
     &     s24**3*s34 + 10*s12*s14**2*s23*s34**4 - 3*s12*s14**2*s23**2*
     &     s24*s34**2 - 12*s12*s14**2*s23**2*s34**3 + 3*s12*s14**2*
     &     s23**3*s34**2 + 12*s12*s14**3*s23*s24*s34**2 + 3*s12*s14**3*
     &     s23*s24**2*s34 + 11*s12*s14**3*s23*s34**3 - 8*s12*s14**3*
     &     s23**2*s34**2 + s12*s14**3*s23**3*s34 + 3*s12*s14**4*s23*s24*
     &     s34 + 7*s12*s14**4*s23*s34**2 - 2*s12*s14**4*s23**2*s34 + 2*
     &     s12*s14**5*s23*s34 + 3*s12*s23*s24*s34**5 + 3*s12*s23*s24**2*
     &     s34**4 + s12*s23*s24**3*s34**3 + s12*s23*s34**6 - 3*s12*
     &     s23**2*s24*s34**4 - 2*s12*s23**2*s34**5 + s12*s23**3*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 + 2*s14*s23**2*s24**3*s34**2 + 
     &     3*s14**2*s23**2*s24*s34**3 )
      wt = wt + s123**(-1)*s134**(-1) * ( 6*s14**2*s23**2*s24**2*s34**2
     &     + s14**2*s23**2*s24**3*s34 + 6*s14**3*s23**2*s24*s34**2 + 3*
     &     s14**3*s23**2*s24**2*s34 + s14**3*s23**2*s34**3 + 3*s14**4*
     &     s23**2*s24*s34 + 2*s14**4*s23**2*s34**2 + s14**5*s23**2*s34
     &     + s23**2*s24**3*s34**3 )
      wt = wt + s123**(-1)*s234**(-1) * (  - 5*s12*s13*s14*s23**2*s24*
     &     s34**2 - 2*s12*s13*s14*s23**2*s24**2*s34 - 3*s12*s13*s14*
     &     s23**2*s34**3 - 2*s12*s13*s14**2*s23*s34**3 - 4*s12*s13*
     &     s14**2*s23**2*s24*s34 - 10*s12*s13*s14**2*s23**2*s34**2 - 4*
     &     s12*s13*s14**3*s23*s34**2 - 6*s12*s13*s14**3*s23**2*s34 - 4*
     &     s12*s13*s14**3*s34**3 + s12*s13**2*s14*s23**2*s24*s34 + 3*s12
     &     *s13**2*s14*s23**2*s34**2 - 8*s12*s13**2*s14**2*s23*s34**2 - 
     &     4*s12*s13**2*s14**2*s23**2*s34 - 2*s12*s13**3*s14*s23**2*s34
     &     + s12*s14*s23**2*s24*s34**3 - s12*s14*s23**2*s24**2*s34**2
     &     - s12*s14*s23**2*s24**3*s34 + s12*s14*s23**2*s34**4 - 2*s12*
     &     s14**2*s23*s34**4 + s12*s14**2*s23**2*s24*s34**2 - 4*s12*
     &     s14**2*s23**2*s24**2*s34 + 2*s12*s14**2*s23**2*s34**3 - 6*s12
     &     *s14**3*s23**2*s24*s34 + 6*s12*s14**3*s23**2*s34**2 - 8*s12*
     &     s14**4*s23*s34**2 - 4*s12*s14**4*s23**2*s34 + s14*s23**2*s24*
     &     s34**4 + 3*s14*s23**2*s24**2*s34**3 + 3*s14*s23**2*s24**3*
     &     s34**2 )
      wt = wt + s123**(-1)*s234**(-1) * ( s14*s23**2*s24**4*s34 + 6*
     &     s14**2*s23**2*s24*s34**3 + 9*s14**2*s23**2*s24**2*s34**2 + 5*
     &     s14**2*s23**2*s24**3*s34 + s14**2*s23**2*s34**4 + 9*s14**3*
     &     s23**2*s24*s34**2 + 9*s14**3*s23**2*s24**2*s34 + 3*s14**3*
     &     s23**2*s34**3 + 7*s14**4*s23**2*s24*s34 + 3*s14**4*s23**2*
     &     s34**2 + 2*s14**5*s23**2*s34 )
      wt = wt + s123**(-1) * ( 5*s12*s13*s14*s23*s24*s34**2 - 3*s12*s13
     &     *s14*s23*s34**3 + s12*s13*s14*s23**2*s24*s34 - 3*s12*s13*s14*
     &     s23**2*s34**2 - 4*s12*s13*s14*s24*s34**3 - 4*s12*s13*s14*
     &     s34**4 + 2*s12*s13*s14**2*s23*s24*s34 + 2*s12*s13*s14**2*s23*
     &     s34**2 - 2*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &     s34**3 + 4*s12*s13*s14**3*s23*s34 + s12*s13*s23*s24**2*s34**2
     &     - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s34**3 + s12*s13**2*
     &     s14*s23*s24*s34 - 7*s12*s13**2*s14*s23*s34**2 + 4*s12*s13**2*
     &     s14*s24*s34**2 + 4*s12*s13**2*s14*s34**3 + 2*s12*s13**2*
     &     s14**2*s23*s34 + 4*s12*s13**2*s14**2*s34**2 - 2*s12*s13**2*
     &     s23*s24*s34**2 - 2*s12*s13**2*s23*s34**3 + 2*s12*s13**3*s14*
     &     s23*s34 - 19*s12*s14*s23*s24*s34**3 - 11*s12*s14*s23*s24**2*
     &     s34**2 - 10*s12*s14*s23*s34**4 + 11*s12*s14*s23**2*s24*s34**2
     &     + s12*s14*s23**2*s24**2*s34 + 9*s12*s14*s23**2*s34**3 - 3*
     &     s12*s14*s23**3*s34**2 - 21*s12*s14**2*s23*s24*s34**2 - 18*s12
     &     *s14**2*s23*s34**3 )
      wt = wt + s123**(-1) * ( 2*s12*s14**2*s23**2*s24*s34 + 12*s12*
     &     s14**2*s23**2*s34**2 - s12*s14**2*s23**3*s34 + s12*s14**3*s23
     &     *s24*s34 - 21*s12*s14**3*s23*s34**2 + 3*s12*s14**3*s23**2*s34
     &     - 6*s12*s23*s24*s34**4 - 6*s12*s23*s24**2*s34**3 - 2*s12*s23
     &     *s24**3*s34**2 - 2*s12*s23*s34**5 + 6*s12*s23**2*s24*s34**3
     &     + 2*s12*s23**2*s24**2*s34**2 + 2*s12*s23**2*s34**4 - s12*
     &     s23**3*s24*s34**2 - s12*s23**3*s34**3 - 5*s14*s23**2*s24*
     &     s34**3 - 7*s14*s23**2*s24**2*s34**2 - s14*s23**2*s24**3*s34
     &     - 2*s14*s23**2*s34**4 + 4*s14*s23**3*s24*s34**2 + s14*s23**3
     &     *s24**2*s34 + 3*s14*s23**3*s34**3 - 13*s14**2*s23**2*s24*
     &     s34**2 - 4*s14**2*s23**2*s24**2*s34 - 6*s14**2*s23**2*s34**3
     &     + 2*s14**2*s23**3*s24*s34 + 4*s14**2*s23**3*s34**2 - 5*
     &     s14**3*s23**2*s24*s34 - 7*s14**3*s23**2*s34**2 + s14**3*
     &     s23**3*s34 - 2*s14**4*s23**2*s34 - s23**2*s24**3*s34**2 )
      wt = wt + s124**(-2) * ( 4*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*
     &     s14*s23**3*s34**2 + 2*s12*s13*s23**2*s24*s34**3 + 2*s12*s13*
     &     s23**3*s24*s34**2 + 2*s12*s13**2*s14*s23**2*s34**2 + s12*
     &     s13**2*s23**2*s24*s34**2 + 2*s12*s14*s23**2*s34**4 + 4*s12*
     &     s14*s23**3*s34**3 + 2*s12*s14*s23**4*s34**2 + s12*s23**2*s24*
     &     s34**4 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s24*s34**2 + 2*
     &     s13*s14*s23**2*s24*s34**3 + 2*s13*s14*s23**3*s24*s34**2 + 
     &     s13**2*s14*s23**2*s24*s34**2 + s14*s23**2*s24*s34**4 + 2*s14*
     &     s23**3*s24*s34**3 + s14*s23**4*s24*s34**2 )
      wt = wt + s124**(-1)*s134**(-1) * ( 3*s12*s14*s23**2*s24*s34**3
     &     - 3*s12*s14*s23**2*s24**2*s34**2 + s12*s14*s23**2*s24**3*s34
     &     - s12*s14*s23**2*s34**4 - 9*s12*s14*s23**3*s24*s34**2 + 3*
     &     s12*s14*s23**3*s24**2*s34 + 3*s12*s14*s23**4*s24*s34 + s12*
     &     s14*s23**5*s34 + 3*s12*s14**2*s23**2*s24*s34**2 - 2*s12*
     &     s14**2*s23**2*s24**2*s34 - 3*s12*s14**2*s23**2*s34**3 - 3*s12
     &     *s14**2*s23**3*s24*s34 - 3*s12*s14**2*s23**4*s34 - s12*s14**3
     &     *s23**2*s24*s34 - 3*s12*s14**3*s23**2*s34**2 + 3*s12*s14**3*
     &     s23**3*s34 - 2*s12*s14**4*s23**2*s34 - s14*s23**2*s24*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 - 3*s14*s23**2*s24**3*s34**2 + 
     &     s14*s23**2*s24**4*s34 + 3*s14*s23**3*s24*s34**3 - 6*s14*
     &     s23**3*s24**2*s34**2 + 3*s14*s23**3*s24**3*s34 - 3*s14*s23**4
     &     *s24*s34**2 + 3*s14*s23**4*s24**2*s34 + s14*s23**5*s24*s34 )
      wt = wt + s124**(-1)*s234**(-1) * (  - 8*s12*s13*s14*s23*s34**4
     &     + 10*s12*s13*s14*s23**2*s24*s34**2 - 4*s12*s13*s14*s23**2*
     &     s24**2*s34 - 8*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*s14**2*
     &     s23*s34**3 + 4*s12*s13*s14**2*s23**2*s24*s34 + 4*s12*s13*
     &     s14**2*s23**2*s34**2 + 5*s12*s13*s23*s34**5 - 4*s12*s13*
     &     s23**2*s24*s34**3 + 4*s12*s13*s23**2*s24**2*s34**2 - s12*s13*
     &     s23**2*s24**3*s34 + 5*s12*s13*s23**2*s34**4 - 6*s12*s13**2*
     &     s14*s23*s34**3 + 6*s12*s13**2*s14*s23**2*s24*s34 - 2*s12*
     &     s13**2*s14*s23**2*s34**2 + 9*s12*s13**2*s23*s34**4 - 6*s12*
     &     s13**2*s23**2*s24*s34**2 + 3*s12*s13**2*s23**2*s24**2*s34 + 9
     &     *s12*s13**2*s23**2*s34**3 + 7*s12*s13**3*s23*s34**3 - 3*s12*
     &     s13**3*s23**2*s24*s34 + 7*s12*s13**3*s23**2*s34**2 + 2*s12*
     &     s13**4*s23*s34**2 + 2*s12*s13**4*s23**2*s34 - 3*s12*s14*s23*
     &     s34**5 + 3*s12*s14*s23**2*s24*s34**3 - 3*s12*s14*s23**2*
     &     s24**2*s34**2 + 2*s12*s14*s23**2*s24**3*s34 - 3*s12*s14*
     &     s23**2*s34**4 )
      wt = wt + s124**(-1)*s234**(-1) * ( 3*s12*s14**2*s23*s34**4 - 3*
     &     s12*s14**2*s23**2*s24*s34**2 + s12*s14**2*s23**2*s24**2*s34
     &     + 3*s12*s14**2*s23**2*s34**3 - 2*s12*s14**3*s23*s34**3 + 2*
     &     s12*s14**3*s23**2*s24*s34 - 2*s12*s14**3*s23**2*s34**2 + s12*
     &     s23*s34**6 - s12*s23**2*s24*s34**4 + s12*s23**2*s24**2*s34**3
     &     - s12*s23**2*s24**3*s34**2 + s12*s23**2*s34**5 + s13*s14*s23
     &     *s34**5 - 2*s13*s14*s23**2*s24*s34**3 - s13*s14*s23**2*s24**2
     &     *s34**2 - 5*s13*s14*s23**2*s24**3*s34 + s13*s14*s23**2*s34**4
     &     + 3*s13**2*s14*s23*s34**4 + 9*s13**2*s14*s23**2*s24**2*s34
     &     + 3*s13**2*s14*s23**2*s34**3 + 3*s13**3*s14*s23*s34**3 - 7*
     &     s13**3*s14*s23**2*s24*s34 + 3*s13**3*s14*s23**2*s34**2 + 2*
     &     s13**4*s14*s23*s34**2 + 2*s13**4*s14*s23**2*s34 + s14*s23**2*
     &     s24**4*s34 )
      wt = wt + s124**(-1) * ( s12*s13*s14*s23*s24*s34**2 + 9*s12*s13*
     &     s14*s23*s34**3 + 5*s12*s13*s14*s23**2*s24*s34 + 4*s12*s13*s14
     &     *s23**2*s34**2 + s12*s13*s14*s23**3*s34 - 4*s12*s13*s14**2*
     &     s23**2*s34 + 5*s12*s13*s23*s24*s34**3 + s12*s13*s23*s24**2*
     &     s34**2 - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s24*s34**2 + 
     &     s12*s13*s23**2*s24**2*s34 + 2*s12*s13*s23**2*s34**3 - s12*s13
     &     *s23**3*s24*s34 + s12*s13*s23**4*s34 + 4*s12*s13**2*s14*s23*
     &     s34**2 - 2*s12*s13**2*s14*s23**2*s34 + 2*s12*s13**2*s23*s24*
     &     s34**2 - 2*s12*s13**2*s23*s34**3 - 3*s12*s13**2*s23**2*s24*
     &     s34 + 6*s12*s13**2*s23**2*s34**2 + 3*s12*s13**2*s23**3*s34 - 
     &     s12*s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 + 5*s12*s14*
     &     s23*s24*s34**3 + 3*s12*s14*s23*s24**2*s34**2 + 6*s12*s14*s23*
     &     s34**4 - 4*s12*s14*s23**2*s24*s34**2 + 7*s12*s14*s23**2*
     &     s34**3 + 4*s12*s14*s23**3*s24*s34 + 7*s12*s14*s23**3*s34**2
     &     + 3*s12*s14*s23**4*s34 + 3*s12*s14**2*s23*s24*s34**2 + s12*
     &     s14**2*s23*s34**3 )
      wt = wt + s124**(-1) * (  - 4*s12*s14**2*s23**3*s34 + 2*s12*
     &     s14**3*s23*s34**2 + 4*s12*s23*s24*s34**4 + 3*s12*s23*s24**2*
     &     s34**3 + s12*s23*s24**3*s34**2 - s12*s23**2*s24*s34**3 - s12*
     &     s23**2*s24**2*s34**2 + 3*s12*s23**3*s24*s34**2 - 2*s12*s23**3
     &     *s34**3 - s12*s23**4*s34**2 - s13*s14*s23**2*s24*s34**2 + 6*
     &     s13*s14*s23**2*s24**2*s34 + 2*s13*s14*s23**3*s34**2 + 4*s13*
     &     s14*s23**4*s34 - 7*s13**2*s14*s23**2*s24*s34 + 6*s13**2*s14*
     &     s23**2*s34**2 + 7*s13**2*s14*s23**3*s34 + s13**3*s14*s23*
     &     s34**2 + 6*s13**3*s14*s23**2*s34 + 3*s14*s23**2*s24*s34**3 - 
     &     s14*s23**2*s24**2*s34**2 - s14*s23**2*s34**4 - s14*s23**3*s24
     &     *s34**2 + 4*s14*s23**3*s24**2*s34 - 2*s14*s23**3*s34**3 + 3*
     &     s14*s23**4*s24*s34 + s14*s23**5*s34 )
      wt = wt + s134**(-2) * ( 3*s12*s14*s23**2*s24**2*s34**2 + 6*s12*
     &     s14*s23**3*s24*s34**2 + 3*s12*s14*s23**4*s34**2 + 4*s12*
     &     s14**2*s23**2*s24**2*s34 + 8*s12*s14**2*s23**3*s24*s34 + 4*
     &     s12*s14**2*s23**4*s34 + 2*s12*s14**3*s23**2*s24**2 + 4*s12*
     &     s14**3*s23**3*s24 + 2*s12*s14**3*s23**4 + s12*s23**2*s24**2*
     &     s34**3 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s34**3 + 6*
     &     s12**2*s14*s23**2*s24*s34**2 + 6*s12**2*s14*s23**3*s34**2 + 8
     &     *s12**2*s14**2*s23**2*s24*s34 + 8*s12**2*s14**2*s23**3*s34 + 
     &     4*s12**2*s14**3*s23**2*s24 + 4*s12**2*s14**3*s23**3 + 2*
     &     s12**2*s23**2*s24*s34**3 + 2*s12**2*s23**3*s34**3 + 3*s12**3*
     &     s14*s23**2*s34**2 + 4*s12**3*s14**2*s23**2*s34 + 2*s12**3*
     &     s14**3*s23**2 + s12**3*s23**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * ( 4*s12*s14*s23*s34**5 + 3*s12*
     &     s14*s23**2*s34**4 + 6*s12*s14**2*s23*s34**4 + 3*s12*s14**2*
     &     s23**2*s34**3 + 5*s12*s14**3*s23*s34**3 + 2*s12*s14**3*s23**2
     &     *s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s34**6 + s12*
     &     s23**2*s34**5 - 12*s12**2*s14*s23*s34**4 - 3*s12**2*s14*
     &     s23**2*s24*s34**2 - 2*s12**2*s14*s23**2*s24**2*s34 - 12*
     &     s12**2*s14*s23**2*s34**3 - 12*s12**2*s14**2*s23*s34**3 - 2*
     &     s12**2*s14**2*s23**2*s24*s34 - 12*s12**2*s14**2*s23**2*s34**2
     &     - 4*s12**2*s14**3*s23*s34**2 - 8*s12**2*s14**3*s23**2*s34 - 
     &     5*s12**2*s23*s34**5 + s12**2*s23**2*s24*s34**3 - s12**2*
     &     s23**2*s24**2*s34**2 - 4*s12**2*s23**2*s34**4 + 12*s12**3*s14
     &     *s23*s34**3 - 4*s12**3*s14*s23**2*s24*s34 + 12*s12**3*s14*
     &     s23**2*s34**2 + 6*s12**3*s14**2*s23*s34**2 - 4*s12**3*s14**2*
     &     s23**2*s24 + 9*s12**3*s23*s34**4 - 3*s12**3*s23**2*s24*s34**2
     &     + 6*s12**3*s23**2*s34**3 - 4*s12**4*s14*s23*s34**2 - 8*
     &     s12**4*s14*s23**2*s34 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 7*s12**4*s23*s34**3 - 4*
     &     s12**4*s23**2*s34**2 + 2*s12**5*s23*s34**2 )
      wt = wt + s134**(-1) * ( 12*s12*s14*s23*s24*s34**3 + 6*s12*s14*
     &     s23*s24**2*s34**2 + s12*s14*s23*s24**3*s34 + 7*s12*s14*s23**2
     &     *s24*s34**2 - 6*s12*s14*s23**2*s24**2*s34 - 5*s12*s14*s23**2*
     &     s34**3 - 8*s12*s14*s23**3*s24*s34 + 14*s12*s14*s23**3*s34**2
     &     - 3*s12*s14*s23**4*s34 + 12*s12*s14**2*s23*s24*s34**2 + 3*
     &     s12*s14**2*s23*s24**2*s34 + 8*s12*s14**2*s23**2*s24*s34 - 4*
     &     s12*s14**2*s23**2*s24**2 - 8*s12*s14**2*s23**2*s34**2 - 4*s12
     &     *s14**2*s23**3*s24 + 11*s12*s14**2*s23**3*s34 + 4*s12*s14**3*
     &     s23*s24*s34 + 4*s12*s14**3*s23**2*s24 - 4*s12*s14**3*s23**2*
     &     s34 + 4*s12*s14**3*s23**3 + 4*s12*s23*s24*s34**4 + 3*s12*s23*
     &     s24**2*s34**3 + s12*s23*s24**3*s34**2 + 3*s12*s23**2*s24*
     &     s34**3 - 2*s12*s23**2*s24**2*s34**2 - s12*s23**2*s34**4 - 4*
     &     s12*s23**3*s24*s34**2 + 3*s12*s23**3*s34**3 - 2*s12*s23**4*
     &     s34**2 + 2*s12**2*s14*s23*s24*s34**2 + 3*s12**2*s14*s23*
     &     s24**2*s34 + 14*s12**2*s14*s23*s34**3 - 15*s12**2*s14*s23**2*
     &     s24*s34 )
      wt = wt + s134**(-1) * ( 14*s12**2*s14*s23**2*s34**2 - 11*s12**2*
     &     s14*s23**3*s34 + s12**2*s14**2*s23*s24*s34 + 13*s12**2*s14**2
     &     *s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 + 9*s12**2*s14**2*
     &     s23**2*s34 + 4*s12**2*s14**3*s23*s34 + 4*s12**2*s14**3*s23**2
     &     + 4*s12**2*s23*s24**2*s34**2 + 6*s12**2*s23*s34**4 - 5*
     &     s12**2*s23**2*s24*s34**2 + 3*s12**2*s23**2*s34**3 - 5*s12**2*
     &     s23**3*s34**2 + 4*s12**3*s14*s23*s24*s34 - 6*s12**3*s14*s23*
     &     s34**2 - 14*s12**3*s14*s23**2*s34 - 2*s12**3*s14**2*s23*s34
     &     + 7*s12**3*s23*s24*s34**2 - 7*s12**3*s23*s34**3 - 3*s12**3*
     &     s23**2*s34**2 + 2*s12**4*s14*s23*s34 + 6*s12**4*s23*s34**2 - 
     &     3*s14*s23**2*s24*s34**3 + 4*s14*s23**2*s24**2*s34**2 - s14*
     &     s23**2*s24**3*s34 + 6*s14*s23**3*s24*s34**2 - 3*s14*s23**3*
     &     s24**2*s34 - s14*s23**3*s34**3 - 3*s14*s23**4*s24*s34 + 2*s14
     &     *s23**4*s34**2 - s14*s23**5*s34 - s14**2*s23**2*s24*s34**2 + 
     &     2*s14**2*s23**2*s24**2*s34 + 3*s14**2*s23**3*s24*s34 - 2*
     &     s14**2*s23**3*s34**2 )
      wt = wt + s134**(-1) * ( 2*s14**2*s23**4*s34 + s14**3*s23**2*s24*
     &     s34 + s14**3*s23**2*s34**2 - s14**3*s23**3*s34 + s14**4*
     &     s23**2*s34 )
      wt = wt + s234**(-2) * ( 8*s12*s13*s14**2*s23*s34**3 + 4*s12*s13*
     &     s14**2*s23**2*s24**2 + 8*s12*s13*s14**2*s23**2*s34**2 + 4*s12
     &     *s13*s14**2*s34**4 + 4*s12*s13**2*s14*s23*s34**3 + 2*s12*
     &     s13**2*s14*s23**2*s24**2 + 4*s12*s13**2*s14*s23**2*s34**2 + 2
     &     *s12*s13**2*s14*s34**4 + 4*s12*s14**3*s23*s34**3 + 2*s12*
     &     s14**3*s23**2*s24**2 + 4*s12*s14**3*s23**2*s34**2 + 2*s12*
     &     s14**3*s34**4 + 8*s12**2*s13*s14*s23*s34**3 + 4*s12**2*s13*
     &     s14*s23**2*s24**2 + 8*s12**2*s13*s14*s23**2*s34**2 + 4*s12**2
     &     *s13*s14*s34**4 + 8*s12**2*s14**2*s23*s34**3 + 4*s12**2*
     &     s14**2*s23**2*s24**2 + 8*s12**2*s14**2*s23**2*s34**2 + 4*
     &     s12**2*s14**2*s34**4 + 4*s12**3*s14*s23*s34**3 + 2*s12**3*s14
     &     *s23**2*s24**2 + 4*s12**3*s14*s23**2*s34**2 + 2*s12**3*s14*
     &     s34**4 )
      wt = wt + s234**(-1) * ( 5*s12*s13*s14*s23*s34**3 + 4*s12*s13*s14
     &     *s23**2*s24**2 + 4*s12*s13*s14*s23**2*s34**2 + 4*s12*s13*s14*
     &     s34**4 - 10*s12*s13*s14**2*s23*s34**2 - 4*s12*s13*s14**2*
     &     s23**2*s24 - 4*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &     s34**3 + 6*s12*s13*s23*s34**4 - 4*s12*s13*s23**2*s24*s34**2
     &     + s12*s13*s23**2*s24**2*s34 + 5*s12*s13*s23**2*s34**3 - 8*
     &     s12*s13**2*s14*s23*s34**2 - 2*s12*s13**2*s14*s23**2*s34 - 4*
     &     s12*s13**2*s14*s34**3 + 7*s12*s13**2*s23*s34**3 - 3*s12*
     &     s13**2*s23**2*s24*s34 + 5*s12*s13**2*s23**2*s34**2 + 6*s12*
     &     s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 - 5*s12*s14*s23*
     &     s34**4 + 3*s12*s14*s23**2*s24*s34**2 - s12*s14*s23**2*s24**2*
     &     s34 - 3*s12*s14*s23**2*s34**3 + 8*s12*s14**2*s23*s34**3 - 3*
     &     s12*s14**2*s23**2*s24*s34 + 4*s12*s14**2*s23**2*s24**2 + 15*
     &     s12*s14**2*s23**2*s34**2 + 4*s12*s14**2*s34**4 - 16*s12*
     &     s14**3*s23*s34**2 - 4*s12*s14**3*s23**2*s24 - 6*s12*s14**3*
     &     s23**2*s34 )
      wt = wt + s234**(-1) * (  - s12*s23**2*s24*s34**3 + s12*s23**2*
     &     s24**2*s34**2 - 12*s12**2*s13*s14*s23*s34**2 - 12*s12**2*s13*
     &     s14*s23**2*s34 - 4*s12**2*s13*s14*s34**3 - s12**2*s13*s23**2*
     &     s24*s34 + s12**2*s13*s23**2*s34**2 + 10*s12**2*s13**2*s23*
     &     s34**2 + 6*s12**2*s13**2*s23**2*s34 + 17*s12**2*s14*s23*
     &     s34**3 + s12**2*s14*s23**2*s24*s34 + 4*s12**2*s14*s23**2*
     &     s24**2 + 19*s12**2*s14*s23**2*s34**2 + 4*s12**2*s14*s34**4 - 
     &     10*s12**2*s14**2*s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 - 6*
     &     s12**2*s14**2*s23**2*s34 + 6*s12**2*s23*s34**4 - 2*s12**2*
     &     s23**2*s24*s34**2 + s12**2*s23**2*s24**2*s34 + 5*s12**2*
     &     s23**2*s34**3 + 10*s12**3*s13*s23*s34**2 + 4*s12**3*s13*
     &     s23**2*s34 - 12*s12**3*s14*s23*s34**2 - 14*s12**3*s14*s23**2*
     &     s34 - 7*s12**3*s23*s34**3 + 2*s12**3*s23**2*s24*s34 - 4*
     &     s12**3*s23**2*s34**2 + 6*s12**4*s23*s34**2 + 2*s12**4*s23**2*
     &     s34 + s13*s14*s23*s34**4 + 2*s13*s14*s23**2*s24*s34**2 + 6*
     &     s13*s14*s23**2*s24**2*s34 )
      wt = wt + s234**(-1) * ( 2*s13*s14*s23**2*s34**3 + s13*s14**2*s23
     &     *s34**3 + 2*s13*s14**2*s23**2*s34**2 + 4*s13*s14**3*s23*
     &     s34**2 + 10*s13*s14**3*s23**2*s34 + 3*s13**2*s14*s23*s34**3
     &     - 7*s13**2*s14*s23**2*s24*s34 + s13**2*s14*s23**2*s34**2 + 6
     &     *s13**2*s14**2*s23*s34**2 + 10*s13**2*s14**2*s23**2*s34 + 4*
     &     s13**3*s14*s23*s34**2 + 6*s13**3*s14*s23**2*s34 + s14*s23**2*
     &     s24*s34**3 + 2*s14*s23**2*s24**2*s34**2 + s14**2*s23*s34**4
     &     + 4*s14**2*s23**2*s24*s34**2 + 6*s14**2*s23**2*s24**2*s34 + 
     &     2*s14**2*s23**2*s34**3 - 2*s14**3*s23*s34**3 + 7*s14**3*
     &     s23**2*s24*s34 + s14**3*s23**2*s34**2 + 2*s14**4*s23*s34**2
     &     + 6*s14**4*s23**2*s34 )
      wt = wt + 22*s12*s13*s14*s23*s24*s34 + 14*s12*s13*s14*s23*s34**2
     &     + 12*s12*s13*s14*s23**2*s34 - 8*s12*s13*s14*s34**3 + 14*s12*
     &     s13*s14**2*s23*s34 + 14*s12*s13*s23*s24*s34**2 + 6*s12*s13*
     &     s23*s24**2*s34 + 4*s12*s13*s23*s34**3 + 15*s12*s13*s23**2*s24
     &     *s34 + 15*s12*s13*s23**2*s34**2 + 12*s12*s13*s23**3*s34 + 14*
     &     s12*s13**2*s14*s23*s34 + 2*s12*s13**2*s14*s34**2 + 9*s12*
     &     s13**2*s23*s24*s34 + 11*s12*s13**2*s23*s34**2 + 18*s12*s13**2
     &     *s23**2*s34 + 4*s12*s13**3*s23*s34 + s12*s14*s23*s24*s34**2
     &     + 9*s12*s14*s23*s24**2*s34 + 5*s12*s14*s23*s34**3 + 6*s12*
     &     s14*s23**2*s24*s34 + 2*s12*s14*s23**2*s24**2 + 16*s12*s14*
     &     s23**2*s34**2 - 3*s12*s14*s23**3*s34 + 2*s12*s14*s34**4 + 14*
     &     s12*s14**2*s23*s24*s34 - 8*s12*s14**2*s23*s34**2 - 8*s12*
     &     s14**2*s23**2*s24 + 11*s12*s14**2*s23**2*s34 + 8*s12*s14**3*
     &     s23*s34 + 2*s12*s14**3*s23**2 - s12*s23*s24*s34**3 + s12*s23*
     &     s24**2*s34**2 + s12*s23*s24**3*s34 + 2*s12*s23**2*s24*s34**2
     &     + 5*s12*s23**2*s24**2*s34
      wt = wt + 2*s12*s23**2*s34**3 + 5*s12*s23**3*s24*s34 - 2*s12*
     &     s23**3*s34**2 + 2*s12*s23**4*s34 + 18*s12**2*s13*s14*s23*s34
     &     + 9*s12**2*s13*s23*s24*s34 + 17*s12**2*s13*s23*s34**2 + 18*
     &     s12**2*s13*s23**2*s34 + 6*s12**2*s13**2*s23*s34 + 17*s12**2*
     &     s14*s23*s24*s34 - 9*s12**2*s14*s23*s34**2 - 8*s12**2*s14*
     &     s23**2*s34 + 8*s12**2*s14**2*s23*s34 + 8*s12**2*s23*s24*
     &     s34**2 + 3*s12**2*s23*s24**2*s34 - 3*s12**2*s23*s34**3 + 11*
     &     s12**2*s23**2*s24*s34 + 3*s12**2*s23**2*s34**2 + 6*s12**2*
     &     s23**3*s34 + 4*s12**3*s13*s23*s34 + 10*s12**3*s14*s23*s34 + 4
     &     *s12**3*s23*s24*s34 + 12*s12**3*s23*s34**2 + 8*s12**3*s23**2*
     &     s34 + 2*s12**4*s23*s34 + 16*s13*s14*s23*s24*s34**2 + 6*s13*
     &     s14*s23*s24**2*s34 + 11*s13*s14*s23*s34**3 + 6*s13*s14*s23**2
     &     *s24*s34 + 14*s13*s14*s23**2*s34**2 + 8*s13*s14*s23**3*s34 + 
     &     9*s13*s14**2*s23*s24*s34 + 17*s13*s14**2*s23*s34**2 + 17*s13*
     &     s14**2*s23**2*s34 + 4*s13*s14**3*s23*s34 + 3*s13*s23*s24*
     &     s34**3
      wt = wt + 3*s13*s23*s24**2*s34**2 + s13*s23*s24**3*s34 + s13*s23*
     &     s34**4 + 6*s13*s23**2*s24*s34**2 + 3*s13*s23**2*s24**2*s34 + 
     &     3*s13*s23**2*s34**3 + 3*s13*s23**3*s24*s34 + 3*s13*s23**3*
     &     s34**2 + s13*s23**4*s34 + 9*s13**2*s14*s23*s24*s34 + 15*
     &     s13**2*s14*s23*s34**2 + 18*s13**2*s14*s23**2*s34 + 6*s13**2*
     &     s14**2*s23*s34 + 6*s13**2*s23*s24*s34**2 + 3*s13**2*s23*
     &     s24**2*s34 + 3*s13**2*s23*s34**3 + 6*s13**2*s23**2*s24*s34 + 
     &     6*s13**2*s23**2*s34**2 + 3*s13**2*s23**3*s34 + 4*s13**3*s14*
     &     s23*s34 + 3*s13**3*s23*s24*s34 + 4*s13**3*s23*s34**2 + 4*
     &     s13**3*s23**2*s34 + 2*s13**4*s23*s34 + 5*s14*s23*s24*s34**3
     &     + 5*s14*s23*s24**2*s34**2 + s14*s23*s24**3*s34 + 2*s14*s23*
     &     s34**4 + 3*s14*s23**2*s24*s34**2 + 2*s14*s23**2*s24**2*s34 - 
     &     2*s14*s23**2*s34**3 - s14*s23**3*s24*s34 + 2*s14*s23**3*
     &     s34**2 - s14*s23**4*s34 + 12*s14**2*s23*s24*s34**2 + 3*s14**2
     &     *s23*s24**2*s34 + 5*s14**2*s23*s34**3 + 4*s14**2*s23**2*s24*
     &     s34
      wt = wt + 2*s14**2*s23**2*s34**2 + 5*s14**2*s23**3*s34 + 4*s14**3
     &     *s23*s24*s34 + 10*s14**3*s23*s34**2 + 5*s14**3*s23**2*s34 + 2
     &     *s14**4*s23*s34

      D40 = wt/s34**2/s14/s23**2/s12

      return
      end

************************************************************************

c     A-type subantenna for q-g-g-g.
      function D40a(s13,s14,s15,s34,s35,s45)
      implicit double precision (a-h,o-z)
      real(8), intent(in) :: s13,s14,s15,s34,s35,s45

      s134  = s13+s14+s34
      s135  = s13+s15+s35
      s145  = s14+s15+s45
      s345  = s34+s35+s45
      s1345 = s13+s14+s15+s34+s35+s45

      s134t = s134
      s135t = s135
      s145t = s145
      s345t = s345

c     1,3,4 antenna (3 soft).
      call DAK(s13,s34,s14,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s13t5 =   x*s15+  y*s35+  z*s45
      s34t5 = omx*s15+omy*s35+omz*s45

c     3,4,5 antenna (4 soft).
      call DAK(s34,s45,s35,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s34t1 =   x*s13+  y*s14+  z*s15
      s45t1 = omx*s13+omy*s14+omz*s15

c     4,5,1 antenna (5 soft).
      call DAK(s45,s15,s14,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s45t3 =   x*s34+  y*s35+  z*s13
      s15t3 = omx*s34+omy*s35+omz*s13

      D40A =
     &  + s134**(-2)*S13**(-1) * (  - s14*s45**2 - 2.D0*s14*s35*s45 -
     &    s14*s35**2 - 2.D0*s14*s15*s45 - 2.D0*s14*s15*s35 - s14*s15**2
     &     )
      D40A = D40A + s134**(-2)*S34**(-2) * ( 2.D0*s13**2*s45**2 + 4.D0*
     &    s13**2*s35*s45 + 2.D0*s13**2*s35**2 + 4.D0*s13**2*s15*s45 + 4.
     &    D0*s13**2*s15*s35 + 2.D0*s13**2*s15**2 )
      D40A = D40A + s134**(-2)*S34**(-1) * ( 4.D0*s13*s45**2 + 8.D0*s13
     &    *s35*s45 + 4.D0*s13*s35**2 + 8.D0*s13*s15*s45 + 8.D0*s13*s15*
     &    s35 + 4.D0*s13*s15**2 )
      D40A = D40A + s134**(-2) * ( 2.D0*s45**2 + 4.D0*s35*s45 + 2.D0*
     &    s35**2 + 4.D0*s15*s45 + 4.D0*s15*s35 + 2.D0*s15**2 )
      D40A = D40A + s134**(-1)*s135**(-1)*S34**(-1) * ( 1.D0/2.D0*
     &    s15**(-1)*s35*s45**3 + 3.D0/2.D0*s15**(-1)*s35**2*s45**2 + 3.D
     &    0/2.D0*s15**(-1)*s35**3*s45 + 1.D0/2.D0*s15**(-1)*s35**4 + 1.D
     &    0/2.D0*s45**3 + 3.D0*s35*s45**2 + 9.D0/2.D0*s35**2*s45 + 2.D0
     &    *s35**3 + 3.D0/2.D0*s15*s45**2 + 9.D0/2.D0*s15*s35*s45 + 3.D0
     &    *s15*s35**2 + 3.D0/2.D0*s15**2*s45 + 5.D0/2.D0*s15**2*s35 +
     &    s15**3 )
      D40A = D40A + s134**(-1)*s135**(-1) * (  - 3.D0/2.D0*s15**(-1)*
     &    s35*s45**2 - 3.D0*s15**(-1)*s35**2*s45 - 3.D0/2.D0*s15**(-1)*
     &    s35**3 - 9.D0/2.D0*s35*s45 - 9.D0/2.D0*s35**2 - 9.D0/2.D0*s15
     &    *s35 - 3.D0/2.D0*s15**2 - 3.D0/2.D0*s14*s15**(-1)*s35*s45 - 3.
     &    D0/2.D0*s14*s15**(-1)*s35**2 - 3.D0*s14*s35 - 3.D0/2.D0*s14*
     &    s15 - 1.D0/2.D0*s14**2*s15**(-1)*s35 - 1.D0/2.D0*s14**2 - 3.D0
     &    /2.D0*s13*s15**(-1)*s35*s45 - 3.D0/2.D0*s13*s15**(-1)*s35**2
     &     - 3.D0*s13*s35 - 3.D0/2.D0*s13*s15 - s13*s14*s15**(-1)*s35
     &     - s13*s14 - 1.D0/2.D0*s13**2*s15**(-1)*s35 - 1.D0/2.D0*
     &    s13**2 )
      D40A = D40A + s134**(-1)*s145**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/
     &    2.D0*s15*s35**3 - 3.D0/2.D0*s14*s15*s35**2 + 3.D0/2.D0*s14**2
     &    *s15*s35 - 1.D0/2.D0*s14**3*s15 )
      D40A = D40A + s134**(-1)*s145**(-1)*S13**(-1) * ( 1.D0/2.D0*
     &    s35**3 - 1.D0/2.D0*s14*s15**(-1)*s35**3 - 3.D0/2.D0*s14*
     &    s35**2 + 1.D0/2.D0*s14**2*s45 + 1.D0/2.D0*s14**3 )
      D40A = D40A + s134**(-1)*s145**(-1)*S34**(-1)*S45**(-1) * ( 1.D0/
     &    2.D0*s13*s35**3 + 3.D0/2.D0*s13**2*s35**2 + 1.D0/2.D0*s13**3*
     &    s35 )
      D40A = D40A + s134**(-1)*s145**(-1)*S34**(-1) * (  - 1.D0/2.D0*
     &    s14*s15**(-1)*s45**3 - 3.D0/2.D0*s14*s15**(-1)*s35*s45**2 - 3.
     &    D0/2.D0*s14*s15**(-1)*s35**2*s45 - 1.D0/2.D0*s14*s15**(-1)*
     &    s35**3 + 1.D0/2.D0*s13*s45**2 + 3.D0/2.D0*s13*s35*s45 + 3.D0/
     &    2.D0*s13*s35**2 + s13**2*s45 + 3.D0/2.D0*s13**2*s35 - 1.D0/2.D
     &    0*s13**3 )
      D40A = D40A + s134**(-1)*s145**(-1)*S45**(-1) * ( 1.D0/2.D0*
     &    s35**3 + 3.D0/2.D0*s15*s35**2 - 1.D0/2.D0*s14*s15*s35 - 1.D0/
     &    2.D0*s14**2*s15 + 3.D0/2.D0*s13*s35**2 + 1.D0/2.D0*s13*s15*
     &    s35 + 1.D0/2.D0*s13*s14*s15 + 1.D0/2.D0*s13**2*s35 )
      D40A = D40A + s134**(-1)*s145**(-1) * ( 1.D0/2.D0*s45**2 + 3.D0/2.
     &    D0*s35*s45 + 3.D0*s35**2 + 1.D0/2.D0*s14*s15**(-1)*s45**2 + 3.
     &    D0/2.D0*s14*s15**(-1)*s35*s45 - 1.D0/2.D0*s14*s45 - 1.D0/2.D0
     &    *s14*s35 - 3.D0/2.D0*s14**2 + s13*s45 + 2.D0*s13*s35 + 1.D0/2.
     &    D0*s13*s14*s15**(-1)*s45 + 3.D0/2.D0*s13*s14 - 1.D0/2.D0*
     &    s13**2 )
      D40A = D40A + s134**(-1)*s345**(-1)*S13**(-1)*S45**(-1) * ( 2.D0*
     &    s15**4 + 13.D0/2.D0*s14*s15**3 + 8.D0*s14**2*s15**2 + 9.D0/2.D
     &    0*s14**3*s15 + s14**4 )
      D40A = D40A + s134**(-1)*s345**(-1)*S13**(-1) * (  - s15*s45**2
     &     - 2.D0*s15*s34*s45 - s15*s34**2 + 3.D0*s15**2*s45 + 3.D0*
     &    s15**2*s34 - 4.D0*s15**3 - 1.D0/2.D0*s14*s45**2 - s14*s34*s45
     &     - 1.D0/2.D0*s14*s34**2 + 5.D0/2.D0*s14*s15*s45 + 5.D0/2.D0*
     &    s14*s15*s34 - 13.D0/2.D0*s14*s15**2 + 1.D0/2.D0*s14**2*s45 +
     &    1.D0/2.D0*s14**2*s34 - 4.D0*s14**2*s15 - s14**3 )
      D40A = D40A + s134**(-1)*s345**(-1)*S34**(-2) * ( 4.D0*s13*s15**2
     &    *s45 )
      D40A = D40A + s134**(-1)*s345**(-1)*S34**(-1) * (  - 2.D0*s15*
     &    s45**2 + 4.D0*s15**2*s45 - 8.D0*s15**3 - 8.D0*s13*s15*s45 + 4.
     &    D0*s13*s15**2 - 2.D0*s13**2*s15 )
      D40A = D40A + s134**(-1)*s345**(-1)*S45**(-1) * ( 5.D0/2.D0*
     &    s15**3 + 6.D0*s14*s15**2 + 4.D0*s14**2*s15 + 1.D0/2.D0*s14**3
     &     + s13*s15**2 + 3.D0/2.D0*s13*s14*s15 - 1.D0/2.D0*s13*s14**2
     &     + s13**2*s15 )
      D40A = D40A + s134**(-1)*s345**(-1) * ( 3.D0/2.D0*s45**2 + 3.D0*
     &    s34*s45 + 3.D0/2.D0*s34**2 - 6.D0*s15*s45 - 4.D0*s15*s34 + 10.
     &    D0*s15**2 - s14*s45 - s14*s34 + s14*s15 + 5.D0/2.D0*s13*s45
     &     + 5.D0/2.D0*s13*s34 - 15.D0/2.D0*s13*s15 + s13**2 )
      D40A = D40A + s134**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/2.D0*s35**3
     &     + 4.D0*s15*s35**2 + 7.D0*s15**2*s35 + 6.D0*s15**3 + 1.D0/2.D0
     &    *s14*s35**2 + 2.D0*s14*s15*s35 + 7.D0*s14*s15**2 + s14**2*s35
     &     + 5.D0*s14**2*s15 + s14**3 )
      D40A = D40A + s134**(-1)*S13**(-1) * (  - s45**2 - 2.D0*s35*s45
     &     - s35**2 - 2.D0*s15*s45 - 4.D0*s15*s35 + s15*s34 - 5.D0*
     &    s15**2 - 3.D0/2.D0*s14*s45 - 5.D0/2.D0*s14*s35 + 1.D0/2.D0*
     &    s14*s34 - 9.D0/2.D0*s14*s15 - s14**2 )
      D40A = D40A + s134**(-1)*S34**(-2) * (  - 4.D0*s13*s35*s45 - 4.D0
     &    *s13*s35**2 - 8.D0*s13*s15*s35 - 4.D0*s13*s15**2 + 4.D0*
     &    s13**2*s45 + 4.D0*s13**2*s35 + 4.D0*s13**2*s15 )
      D40A = D40A + s134**(-1)*S34**(-1)*S45**(-1) * ( s35**3 + 3.D0*
     &    s15*s35**2 + 4.D0*s15**2*s35 + 2.D0*s15**3 + 1.D0/2.D0*s13*
     &    s35**2 - 3.D0/2.D0*s13*s15*s35 - 2.D0*s13*s15**2 + 3.D0/2.D0*
     &    s13**2*s35 + s13**2*s15 )
      D40A = D40A + s134**(-1)*S34**(-1) * (  - 1.D0/2.D0*s15**(-1)*
     &    s45**3 - 3.D0/2.D0*s15**(-1)*s35*s45**2 - 3.D0/2.D0*s15**(-1)
     &    *s35**2*s45 - 1.D0/2.D0*s15**(-1)*s35**3 - 9.D0/2.D0*s45**2
     &     - 11.D0*s35*s45 - 15.D0/2.D0*s35**2 - 21.D0/2.D0*s15*s45 -
     &    37.D0/2.D0*s15*s35 - 19.D0*s15**2 + 7.D0*s13*s45 + 23.D0/2.D0
     &    *s13*s35 + 13.D0*s13*s15 - 3.D0/2.D0*s13**2 )
      D40A = D40A + s134**(-1)*S45**(-1) * (  - s35**2 - 3.D0/2.D0*s15*
     &    s35 - s15**2 - s14*s35 + 1.D0/2.D0*s14*s15 - 1.D0/2.D0*s14**2
     &     + s13*s35 + 3.D0/2.D0*s13*s15 )
      D40A = D40A + s134**(-1) * ( 1.D0/2.D0*s15**(-1)*s45**2 +
     &    s15**(-1)*s35*s45 + s15**(-1)*s35**2 + 4.D0*s45 + 17.D0/2.D0*
     &    s35 - 3.D0/2.D0*s34 + 21.D0/2.D0*s15 + 1.D0/2.D0*s14*
     &    s15**(-1)*s45 + s14*s15**(-1)*s35 + 9.D0/2.D0*s14 - 1.D0/2.D0
     &    *s13*s15**(-1)*s45 + 1.D0/2.D0*s13*s15**(-1)*s35 - 7.D0/2.D0*
     &    s13 )
      D40A = D40A + s135**(-2)*S13**(-1) * (  - 1.D0/2.D0*s35**2*s45 -
     &    1.D0/2.D0*s34*s35**2 - 1.D0/2.D0*s15*s35*s45 - 1.D0/2.D0*s15*
     &    s34*s35 - 1.D0/2.D0*s14*s35**2 - 1.D0/2.D0*s14*s15*s35 )
      D40A = D40A + s135**(-2) * (  - 1.D0/2.D0*s15**(-1)*s35**2*s45 -
     &    1.D0/2.D0*s15**(-1)*s34*s35**2 - 2.D0*s35*s45 - 2.D0*s34*s35
     &     - s15*s45 - s15*s34 - 1.D0/2.D0*s14*s15**(-1)*s35**2 - 2.D0*
     &    s14*s35 - s14*s15 - 1.D0/2.D0*s13*s15**(-1)*s35*s45 - 1.D0/2.D
     &    0*s13*s15**(-1)*s34*s35 - s13*s45 - s13*s34 - 1.D0/2.D0*s13*
     &    s14*s15**(-1)*s35 - s13*s14 )
      D40A = D40A + s135**(-1)*s145**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/
     &    2.D0*s35**4 + 3.D0/2.D0*s34*s35**3 + 3.D0/2.D0*s34**2*s35**2
     &     + 1.D0/2.D0*s34**3*s35 )
      D40A = D40A + s135**(-1)*s145**(-1)*S13**(-1) * (  - 1.D0/2.D0*
     &    s35*s45**2 + 3.D0/2.D0*s35**2*s45 - 3.D0/2.D0*s35**3 + 3.D0/2.
     &    D0*s34*s35*s45 - 3.D0*s34*s35**2 - 3.D0/2.D0*s34**2*s35 )
      D40A = D40A + s135**(-1)*s145**(-1)*S45**(-1) * ( 1.D0/2.D0*
     &    s35**3 + 3.D0/2.D0*s34*s35**2 + 3.D0/2.D0*s34**2*s35 + 1.D0/2.
     &    D0*s34**3 - s15*s35**2 - 3.D0/2.D0*s15*s34*s35 - 3.D0/2.D0*
     &    s15*s34**2 + 1.D0/2.D0*s14*s15*s35 - 3.D0/2.D0*s14*s15*s34 -
     &    s14**2*s15 )
      D40A = D40A + s135**(-1)*s145**(-1) * ( 1.D0/2.D0*s45**2 - 1.D0/2.
     &    D0*s35*s45 - 3.D0/2.D0*s35**2 + 3.D0/2.D0*s34*s45 - 9.D0/2.D0
     &    *s34*s35 + 3.D0/2.D0*s14*s45 - 2.D0*s14*s35 + 3.D0/2.D0*s14*
     &    s34 + 1.D0/2.D0*s14**2 )
      D40A = D40A + s135**(-1)*s345**(-1)*S13**(-1)*S34**(-1) * ( 1.D0/
     &    2.D0*s14*s45**3 + 3.D0/2.D0*s14**2*s45**2 + 3.D0/2.D0*s14**3*
     &    s45 - s14**3*s15 )
      D40A = D40A + s135**(-1)*s345**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/
     &    2.D0*s34**4 - 1.D0/2.D0*s15*s34**3 + 2.D0*s14*s34**3 - 3.D0/2.
     &    D0*s14*s15*s34**2 + 3.D0*s14**2*s34**2 - 2.D0*s14**2*s15*s34
     &     + 3.D0/2.D0*s14**3*s34 - s14**3*s15 )
      D40A = D40A + s135**(-1)*s345**(-1)*S13**(-1) * ( 1.D0/2.D0*
     &    s45**3 + 2.D0*s34*s45**2 + 3.D0*s34**2*s45 + 2.D0*s34**3 - 1.D
     &    0/2.D0*s15*s34**2 + 7.D0/2.D0*s14*s45**2 + 15.D0/2.D0*s14*s34
     &    *s45 + 13.D0/2.D0*s14*s34**2 - 3.D0/2.D0*s14*s15*s34 + 6.D0*
     &    s14**2*s45 + 15.D0/2.D0*s14**2*s34 - 2.D0*s14**2*s15 + 3.D0*
     &    s14**3 )
      D40A = D40A + s135**(-1)*s345**(-1)*S34**(-1) * ( 1.D0/2.D0*
     &    s15**(-1)*s45**4 - 2.D0*s45**3 + 5.D0/2.D0*s15*s45**2 - 3.D0/
     &    2.D0*s15**2*s45 + 2.D0*s14*s15**(-1)*s45**3 - 9.D0/2.D0*s14*
     &    s45**2 + 3.D0*s14*s15*s45 + 3.D0*s14**2*s15**(-1)*s45**2 - 7.D
     &    0/2.D0*s14**2*s45 + 3.D0/2.D0*s14**3*s15**(-1)*s45 - 2.D0*
     &    s14**3 - 1.D0/2.D0*s13*s15**(-1)*s45**3 + s13*s45**2 - 1.D0/2.
     &    D0*s13*s15*s45 - 3.D0/2.D0*s13*s14*s15**(-1)*s45**2 + 3.D0/2.D
     &    0*s13*s14*s45 - 2.D0*s13*s14**2*s15**(-1)*s45 - s13*s14**3*
     &    s15**(-1) )
      D40A = D40A + s135**(-1)*s345**(-1)*S45**(-1) * (  - 3.D0/2.D0*
     &    s34**3 + s15*s34**2 - 1.D0/2.D0*s15**2*s34 + 1.D0/2.D0*s14*
     &    s15**(-1)*s34**3 - 3.D0*s14*s34**2 + 3.D0/2.D0*s14**2*
     &    s15**(-1)*s34**2 - 7.D0/2.D0*s14**2*s34 + 3.D0/2.D0*s14**3*
     &    s15**(-1)*s34 - 2.D0*s14**3 + 1.D0/2.D0*s13*s34**2 + 1.D0/2.D0
     &    *s13*s15*s34 + 3.D0/2.D0*s13*s14*s34 - s13*s14**3*s15**(-1) )
      D40A = D40A + s135**(-1)*s345**(-1) * ( 2.D0*s15**(-1)*s45**3 + 3.
     &    D0*s15**(-1)*s34*s45**2 + 2.D0*s15**(-1)*s34**2*s45 + 1.D0/2.D
     &    0*s15**(-1)*s34**3 - 6.D0*s45**2 - 15.D0/2.D0*s34*s45 - 5.D0*
     &    s34**2 + 4.D0*s15*s45 + 5.D0/2.D0*s15*s34 - 2.D0*s15**2 + 13.D
     &    0/2.D0*s14*s15**(-1)*s45**2 + 15.D0/2.D0*s14*s15**(-1)*s34*
     &    s45 + 7.D0/2.D0*s14*s15**(-1)*s34**2 - 12.D0*s14*s45 - 21.D0/
     &    2.D0*s14*s34 + s14*s15 + 15.D0/2.D0*s14**2*s15**(-1)*s45 + 6.D
     &    0*s14**2*s15**(-1)*s34 - 7.D0*s14**2 + 3.D0*s14**3*s15**(-1)
     &     - 1.D0/2.D0*s13*s15**(-1)*s45**2 + 1.D0/2.D0*s13*s45 - 3.D0/
     &    2.D0*s13*s14*s15**(-1)*s45 + s13*s14 - 2.D0*s13*s14**2*
     &    s15**(-1) )
      D40A = D40A + s135**(-1)*S13**(-1)*S34**(-1) * (  - 1.D0/2.D0*s14
     &    *s45**2 - s14*s35*s45 - 1.D0/2.D0*s14*s35**2 - 1.D0/2.D0*s14*
     &    s15*s45 - 1.D0/2.D0*s14*s15*s35 - 3.D0/2.D0*s14**2*s45 - 3.D0/
     &    2.D0*s14**2*s35 - s14**2*s15 - 3.D0/2.D0*s14**3 )
      D40A = D40A + s135**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/2.D0*s35**3
     &     + 3.D0/2.D0*s34*s35**2 + 2.D0*s34**2*s35 - 1.D0/2.D0*s34**3
     &     + 1.D0/2.D0*s14*s35**2 + 5.D0/2.D0*s14*s34*s35 - 2.D0*s14*
     &    s34**2 + s14**2*s35 - 3.D0*s14**2*s34 - 3.D0/2.D0*s14**3 )
      D40A = D40A + s135**(-1)*S13**(-1) * (  - 1.D0/2.D0*s45**2 + 2.D0
     &    *s35*s45 - 3.D0/2.D0*s35**2 - 3.D0/2.D0*s34*s45 + 1.D0/2.D0*
     &    s34*s35 - 3.D0/2.D0*s34**2 + 1.D0/2.D0*s15*s45 - 1.D0/2.D0*
     &    s15*s35 + 1.D0/2.D0*s15*s34 - 3.D0*s14*s45 + 1.D0/2.D0*s14*
     &    s35 - 9.D0/2.D0*s14*s34 - 9.D0/2.D0*s14**2 )
      D40A = D40A + s135**(-1)*S34**(-1) * (  - 1.D0/2.D0*s15**(-1)*
     &    s45**3 + 2.D0*s15**(-1)*s35*s45**2 + 3.D0/2.D0*s15**(-1)*
     &    s35**2*s45 + 1.D0/2.D0*s15**(-1)*s35**3 + 4.D0*s45**2 + 5.D0/
     &    2.D0*s35*s45 + 3.D0/2.D0*s35**2 + 3.D0/2.D0*s15*s35 + s15**2
     &     - 2.D0*s14*s15**(-1)*s45**2 + 5.D0/2.D0*s14*s15**(-1)*s35*
     &    s45 + 1.D0/2.D0*s14*s15**(-1)*s35**2 + 5.D0*s14*s45 - 1.D0/2.D
     &    0*s14*s35 - 1.D0/2.D0*s14*s15 - 3.D0*s14**2*s15**(-1)*s45 +
     &    s14**2*s15**(-1)*s35 + 1.D0/2.D0*s14**2 - 3.D0/2.D0*s14**3*
     &    s15**(-1) - 1.D0/2.D0*s13*s14 )
      D40A = D40A + s135**(-1)*S45**(-1) * ( s35**2 + 3.D0/2.D0*s34*s35
     &     + 7.D0/2.D0*s34**2 - 1.D0/2.D0*s14*s15**(-1)*s35**2 - s14*
     &    s15**(-1)*s34*s35 - 1.D0/2.D0*s14*s15**(-1)*s34**2 - 1.D0/2.D0
     &    *s14*s35 + 7.D0/2.D0*s14*s34 + 1.D0/2.D0*s14*s15 - 3.D0/2.D0*
     &    s14**2*s15**(-1)*s35 - 3.D0/2.D0*s14**2*s15**(-1)*s34 + 1.D0/
     &    2.D0*s14**2 - 3.D0/2.D0*s14**3*s15**(-1) + 1.D0/2.D0*s13*s34
     &     - 1.D0/2.D0*s13*s14*s15**(-1)*s35 - 1.D0/2.D0*s13*s14*
     &    s15**(-1)*s34 - 1.D0/2.D0*s13*s14 - s13*s14**2*s15**(-1) )
      D40A = D40A + s135**(-1) * (  - 3.D0/2.D0*s15**(-1)*s45**2 + 2.D0
     &    *s15**(-1)*s35*s45 - 3.D0/2.D0*s15**(-1)*s34*s45 + 3.D0/2.D0*
     &    s15**(-1)*s34*s35 - 1.D0/2.D0*s15**(-1)*s34**2 + 15.D0/2.D0*
     &    s45 - s35 + 6.D0*s34 - 3.D0/2.D0*s15 - 9.D0/2.D0*s14*
     &    s15**(-1)*s45 + s14*s15**(-1)*s35 - 3.D0*s14*s15**(-1)*s34 +
     &    17.D0/2.D0*s14 - 9.D0/2.D0*s14**2*s15**(-1) + 1.D0/2.D0*s13*
     &    s15**(-1)*s45 + 1.D0/2.D0*s13*s15**(-1)*s34 )
      D40A = D40A + s145**(-1)*s345**(-1)*S34**(-1) * ( 1.D0/2.D0*
     &    s14**2*s45 - 1.D0/2.D0*s13*s15**(-1)*s45**3 + 1.D0/2.D0*s13*
     &    s45**2 + s13*s14*s45 + s13**2*s15**(-1)*s45**2 - 1.D0/2.D0*
     &    s13**3*s15**(-1)*s45 )
      D40A = D40A + s145**(-1)*s345**(-1) * (  - s15**(-1)*s45**3 - 3.D0
     &    /2.D0*s15**(-1)*s34*s45**2 - 1.D0/2.D0*s15**(-1)*s34**2*s45
     &     - s45**2 - s34*s45 + 3.D0/2.D0*s13*s15**(-1)*s45**2 + 3.D0/2.
     &    D0*s13*s15**(-1)*s34*s45 + 4.D0*s13*s45 + 5.D0/2.D0*s13*s34
     &     + 3.D0/2.D0*s13*s14 - 1.D0/2.D0*s13**2*s15**(-1)*s45 - 3.D0/
     &    2.D0*s13**2 )
      D40A = D40A + s145**(-1)*S13**(-1)*S45**(-1) * (  - 1.D0/2.D0*
     &    s35**3 - 3.D0/2.D0*s34*s35**2 - 3.D0/2.D0*s34**2*s35 - 1.D0/2.
     &    D0*s34**3 + 3.D0/2.D0*s15*s35**2 + 3.D0/2.D0*s15*s34*s35 + 1.D
     &    0/2.D0*s15*s34**2 - 3.D0/2.D0*s14*s15*s35 - 1.D0/2.D0*s14*s15
     &    *s34 + 1.D0/2.D0*s14**2*s15 )
      D40A = D40A + s145**(-1)*S13**(-1) * (  - 1.D0/2.D0*s35*s45 + 5.D0
     &    /2.D0*s35**2 + 1.D0/2.D0*s34*s45 + 5.D0/2.D0*s34*s35 + s34**2
     &     - 1.D0/2.D0*s14*s45 + 1.D0/2.D0*s14*s35 + s14*s34 - 1.D0/2.D0
     &    *s14**2 )
      D40A = D40A + s145**(-1)*S34**(-1)*S45**(-1) * (  - 1.D0/2.D0*
     &    s35**3 + s15*s35**2 - 3.D0/2.D0*s13*s35**2 + 2.D0*s13*s15*s35
     &     - 1.D0/2.D0*s13**2*s35 )
      D40A = D40A + s145**(-1)*S34**(-1) * (  - 1.D0/2.D0*s45**2 - 3.D0/
     &    2.D0*s35*s45 - 1.D0/2.D0*s35**2 - 1.D0/2.D0*s14*s15**(-1)*
     &    s45**2 - 3.D0/2.D0*s14*s15**(-1)*s35*s45 - 2.D0*s14*s15**(-1)
     &    *s35**2 - 1.D0/2.D0*s14**2 + 1.D0/2.D0*s13*s15**(-1)*s45**2
     &     - 1.D0/2.D0*s13*s15**(-1)*s35*s45 - s13*s45 + s13*s35 - 1.D0/
     &    2.D0*s13*s14*s15**(-1)*s45 - 5.D0/2.D0*s13*s14*s15**(-1)*s35
     &     - 1.D0/2.D0*s13*s14 - s13**2*s15**(-1)*s45 + 3.D0/2.D0*
     &    s13**2 - s13**2*s14*s15**(-1) )
      D40A = D40A + s145**(-1)*S45**(-1) * (  - 1.D0/2.D0*s15*s15t3 +
     &    s15*s35 - 5.D0/2.D0*s15*s34 - s14*s15 - 2.D0*s13*s15 )
      D40A = D40A + s145**(-1) * ( s15**(-1)*s45**2 - s15**(-1)*s35*s45
     &     + 1.D0/2.D0*s15**(-1)*s34*s45 + 1.D0/2.D0*s15t3 + 5.D0/2.D0*
     &    s45 + 7.D0/2.D0*s35 + 11.D0/2.D0*s34 + 1.D0/2.D0*s14*
     &    s15**(-1)*s15t3 + 1.D0/2.D0*s14*s15**(-1)*s35 + s14*s15**(-1)
     &    *s34 + 3.D0*s14 - 2.D0*s13*s15**(-1)*s45 + 2.D0*s13 + 1.D0/2.D
     &    0*s13*s14*s15**(-1) )
      D40A = D40A + s345**(-3)*S34**(-1) * (  - 2.D0*s45**2*s34t1*s45t1
     &     + 2.D0*s15*s45**2*s34t1 + 2.D0*s14*s45**2*s34t1 + 2.D0*s13*
     &    s45**2*s34t1 )
      D40A = D40A + s345**(-3) * (  - 2.D0*s45*s34t1*s45t1 + 2.D0*s15*
     &    s45*s34t1 + 2.D0*s14*s45*s34t1 + 2.D0*s13*s45*s34t1 )
      D40A = D40A + s345**(-2)*S34**(-2) * ( 2.D0*s15**2*s45**2 + 4.D0*
     &    s14*s15*s45**2 + 2.D0*s14**2*s45**2 + 4.D0*s13*s15*s45**2 + 4.
     &    D0*s13*s14*s45**2 + 2.D0*s13**2*s45**2 )
      D40A = D40A + s345**(-2)*S34**(-1) * ( 2.D0*s45*s34t1*s45t1 + 2.D0
     &    *s45**2*s34t1 + 1.D0/2.D0*s15*s45*s45t1 - 5.D0/2.D0*s15*s45*
     &    s34t1 - 5.D0*s15*s45**2 + 7.D0/2.D0*s15**2*s45 + 1.D0/2.D0*
     &    s14*s45*s45t1 - 5.D0/2.D0*s14*s45*s34t1 - 5.D0*s14*s45**2 + 7.
     &    D0*s14*s15*s45 + 7.D0/2.D0*s14**2*s45 + 1.D0/2.D0*s13*s45*
     &    s45t1 - 5.D0/2.D0*s13*s45*s34t1 - 5.D0*s13*s45**2 + 7.D0*s13*
     &    s15*s45 + 7.D0*s13*s14*s45 + 7.D0/2.D0*s13**2*s45 )
      D40A = D40A + s345**(-2)*S45**(-1) * ( 1.D0/2.D0*s15*s34*s45t1 -
     &    1.D0/2.D0*s15*s34*s34t1 + 1.D0/2.D0*s15**2*s34 + 1.D0/2.D0*
     &    s14*s34*s45t1 - 1.D0/2.D0*s14*s34*s34t1 + s14*s15*s34 + 1.D0/
     &    2.D0*s14**2*s34 + 1.D0/2.D0*s13*s34*s45t1 - 1.D0/2.D0*s13*s34
     &    *s34t1 + s13*s15*s34 + s13*s14*s34 + 1.D0/2.D0*s13**2*s34 )
      D40A = D40A + s345**(-2) * ( s34t1*s45t1 + 2.D0*s45*s34t1 - s15*
     &    s34t1 - 5.D0*s15*s45 + 3.D0*s15**2 - s14*s34t1 - 5.D0*s14*s45
     &     + 6.D0*s14*s15 + 3.D0*s14**2 - s13*s34t1 - 5.D0*s13*s45 + 6.D
     &    0*s13*s15 + 6.D0*s13*s14 + 3.D0*s13**2 )
      D40A = D40A + s345**(-1)*S13**(-1)*S34**(-1) * ( s15*s45**2 - 2.D0
     &    *s15**2*s45 + 2.D0*s15**3 + s14*s45**2 - 3.D0/2.D0*s14*s15*
     &    s45 + 4.D0*s14*s15**2 + s14**2*s45 + 3.D0*s14**2*s15 + 2.D0*
     &    s14**3 )
      D40A = D40A + s345**(-1)*S13**(-1)*S45**(-1) * ( 1.D0/2.D0*s34**3
     &     - 1.D0/2.D0*s15**3 + 2.D0*s14*s34**2 + 1.D0/2.D0*s14*s15*s34
     &     - s14*s15**2 + 3.D0*s14**2*s34 - 1.D0/2.D0*s14**2*s15 +
     &    s14**3 )
      D40A = D40A + s345**(-1)*S13**(-1) * ( 1.D0/2.D0*s45**2 + 3.D0/2.D
     &    0*s34*s45 + 3.D0/2.D0*s34**2 + 5.D0/2.D0*s15*s45 + 2.D0*s15*
     &    s34 - 3.D0/2.D0*s15**2 + 4.D0*s14*s45 + 5.D0*s14*s34 + 4.D0*
     &    s14**2 )
      D40A = D40A + s345**(-1)*S34**(-2) * ( 4.D0*s15*s45**2 - 4.D0*
     &    s15**2*s45 + 4.D0*s14*s45**2 - 8.D0*s14*s15*s45 - 4.D0*s14**2
     &    *s45 + 4.D0*s13*s45**2 - 4.D0*s13*s14*s45 )
      D40A = D40A + s345**(-1)*S34**(-1) * ( 1.D0/2.D0*s15**(-1)*s45**3
     &     - s34t1*s45t1 + 1.D0/2.D0*s45*s45t1 - 5.D0/2.D0*s45*s34t1 -
     &    2.D0*s45**2*s34t1**(-1)*s45t1 - 9.D0*s45**2 - s15*s45t1 + 2.D0
     &    *s15*s34t1 + 18.D0*s15*s45 + 2.D0*s15*s45**2*s34t1**(-1) - 17.
     &    D0*s15**2 + 2.D0*s14*s15**(-1)*s45**2 - s14*s45t1 + 2.D0*s14*
     &    s34t1 + 25.D0/2.D0*s14*s45 + 2.D0*s14*s45**2*s34t1**(-1) - 15.
     &    D0*s14*s15 + 3.D0*s14**2*s15**(-1)*s45 - 5.D0*s14**2 + s14**3
     &    *s15**(-1) + 1.D0/2.D0*s13*s15**(-1)*s45**2 - s13*s45t1 + 2.D0
     &    *s13*s34t1 + 19.D0/2.D0*s13*s45 + 2.D0*s13*s45**2*s34t1**(-1)
     &     - 8.D0*s13*s15 - 7.D0*s13*s14 - s13**2*s15**(-1)*s45 - 3.D0*
     &    s13**2 )
      D40A = D40A + s345**(-1)*S45**(-1) * ( 1.D0/2.D0*s34*s45t1 - 1.D0/
     &    2.D0*s34*s34t1 - 3.D0/2.D0*s34**2 - s15*s45t1 + s15*s34t1 +
     &    s15*s34 - 4.D0*s15**2 - s14*s45t1 + s14*s34t1 + 2.D0*s14*s34
     &     - 9.D0/2.D0*s14*s15 + 3.D0*s14**2*s15**(-1)*s34 - 1.D0/2.D0*
     &    s14**2 + s14**3*s15**(-1) - s13*s45t1 + s13*s34t1 + 1.D0/2.D0
     &    *s13*s34 - 5.D0*s13*s15 + 5.D0/2.D0*s13*s14*s15**(-1)*s34 - 2.
     &    D0*s13*s14 - s13**2 )
      D40A = D40A + s345**(-1) * ( 5.D0/2.D0*s15**(-1)*s45**2 + 3.D0*
     &    s15**(-1)*s34*s45 + s15**(-1)*s34**2 - s34t1 - 2.D0*s45*
     &    s34t1**(-1)*s45t1 - 23.D0/2.D0*s45 - 4.D0*s34 + 14.D0*s15 + 2.
     &    D0*s15*s45*s34t1**(-1) + 7.D0/2.D0*s14*s15**(-1)*s45 + 3.D0/2.
     &    D0*s14*s15**(-1)*s34 + 11.D0*s14 + 2.D0*s14*s45*s34t1**(-1)
     &     + 6.D0*s14**2*s15**(-1) - 1.D0/2.D0*s13*s15**(-1)*s45 - s13*
     &    s15**(-1)*s34 + 11.D0/2.D0*s13 + 2.D0*s13*s45*s34t1**(-1) + 5.
     &    D0*s13*s14*s15**(-1) + 2.D0*s13**2*s15**(-1) )
      D40A = D40A + S13**(-1)*S34**(-1)*S45**(-1) * ( s35**3 + 3.D0*s15
     &    *s35**2 + 4.D0*s15**2*s35 + 2.D0*s15**3 + 1.D0/2.D0*s14*
     &    s15**(-1)*s35**3 + 7.D0/2.D0*s14*s35**2 + 13.D0/2.D0*s14*s15*
     &    s35 + 4.D0*s14*s15**2 + 3.D0/2.D0*s14**2*s15**(-1)*s35**2 + 4.
     &    D0*s14**2*s35 + 3.D0*s14**2*s15 + 1.D0/2.D0*s14**3*s15**(-1)*
     &    s35 + s14**3 )
      D40A = D40A + S13**(-1)*S34**(-1) * ( 2.D0*s45**2 + 5.D0*s35*s45
     &     + 5.D0*s35**2 + 5.D0*s15*s45 + 12.D0*s15*s35 + 10.D0*s15**2
     &     + s14*s15**(-1)*s35*s45 + 3.D0/2.D0*s14*s15**(-1)*s35**2 +
     &    11.D0/2.D0*s14*s45 + 11.D0*s14*s35 + 29.D0/2.D0*s14*s15 + 2.D0
     &    *s14**2*s15**(-1)*s35 + 5.D0*s14**2 - 2.D0*s14**3*s34t5**(-1)
     &     )
      D40A = D40A + S13**(-1)*S45**(-1) * ( 5.D0/2.D0*s35**2 + 1.D0/2.D0
     &    *s34*s35 - 3.D0/2.D0*s34**2 + 9.D0*s15*s35 + 3.D0/2.D0*s15*
     &    s34 + 7.D0*s15**2 + 3.D0/2.D0*s14*s15**(-1)*s35**2 + s14*
     &    s15**(-1)*s34*s35 + 13.D0/2.D0*s14*s35 + 13.D0/2.D0*s14*s15
     &     + 2.D0*s14**2*s15**(-1)*s35 + 3.D0*s14**2 )
      D40A = D40A + S13**(-1) * ( s45 + 11.D0/2.D0*s35 - 3.D0/2.D0*s34
     &     - s34**2*s34t5**(-1) + 4.D0*s15 + 2.D0*s14*s15**(-1)*s35 + 5.
     &    D0/2.D0*s14 - 3.D0*s14*s34*s34t5**(-1) - 4.D0*s14**2*
     &    s34t5**(-1) )
      D40A = D40A + S34**(-2) * ( 2.D0*s35**2 - 4.D0*s15*s45 + 4.D0*s15
     &    *s35 + 2.D0*s15**2 - 4.D0*s14*s45 + 4.D0*s14*s35 + 4.D0*s14*
     &    s15 + 2.D0*s14**2 - 4.D0*s13*s45 - 4.D0*s13*s35 - 4.D0*s13*
     &    s15 )
      D40A = D40A + S34**(-1)*S45**(-1) * ( s35*s45t1 - s35*s34t1 +
     &    s35**2*s34t1**(-1)*s45t1 + 9.D0/2.D0*s35**2 - s35**2*s34t1*
     &    s45t1**(-1) + s15*s45t1 - s15*s34t1 + 27.D0/2.D0*s15*s35 -
     &    s15*s35**2*s34t1**(-1) + s15*s35**2*s45t1**(-1) + 9.D0*s15**2
     &     + 5.D0/2.D0*s14*s15**(-1)*s35**2 + s14*s45t1 - s14*s34t1 +
     &    21.D0/2.D0*s14*s35 - s14*s35**2*s34t1**(-1) + s14*s35**2*
     &    s45t1**(-1) + 11.D0*s14*s15 + 3.D0*s14**2*s15**(-1)*s35 + 4.D0
     &    *s14**2 + s13*s45t1 - s13*s34t1 + 5.D0/2.D0*s13*s35 - s13*
     &    s35**2*s34t1**(-1) + s13*s35**2*s45t1**(-1) + 5.D0*s13*s15 +
     &    5.D0/2.D0*s13*s14*s15**(-1)*s35 + 4.D0*s13*s14 + s13**2 )
      D40A = D40A + S34**(-1) * (  - 2.D0*s15**(-1)*s45**2 - s15**(-1)*
     &    s35*s45 + s34t1 + 3.D0/2.D0*s45*s34t1**(-1)*s45t1 + 2.D0*s45
     &     - 1.D0/2.D0*s45*s34t1*s45t1**(-1) - 11.D0/2.D0*s35 - s35*
     &    s34t1*s45t1**(-1) - 17.D0*s15 - 3.D0/2.D0*s15*s45*s34t1**(-1)
     &     + 1.D0/2.D0*s15*s45*s45t1**(-1) + s15*s35*s45t1**(-1) - 3.D0
     &    *s14*s15**(-1)*s45 + 3.D0/2.D0*s14*s15**(-1)*s35 - 9.D0/2.D0*
     &    s14 - 3.D0/2.D0*s14*s45*s34t1**(-1) + 1.D0/2.D0*s14*s45*
     &    s45t1**(-1) + s14*s35*s45t1**(-1) - s14**2*s15**(-1) - 4.D0*
     &    s14**2*s34t5**(-1) - 3.D0*s13*s15**(-1)*s45 - 1.D0/2.D0*s13*
     &    s15**(-1)*s35 - 5.D0/2.D0*s13 - 3.D0/2.D0*s13*s45*s34t1**(-1)
     &     + 1.D0/2.D0*s13*s45*s45t1**(-1) + s13*s35*s45t1**(-1) - 5.D0/
     &    2.D0*s13*s14*s15**(-1) - 3.D0*s13*s14*s34t5**(-1) - s13**2*
     &    s15**(-1) - s13**2*s34t5**(-1) )
      D40A = D40A + S45**(-1) * ( s35*s34t1**(-1)*s45t1 + 5.D0*s35 -
     &    s35*s34t1*s45t1**(-1) + 1.D0/2.D0*s34*s34t1**(-1)*s45t1 + 3.D0
     &    *s34 - 1.D0/2.D0*s34*s34t1*s45t1**(-1) + 5.D0/2.D0*s15 - s15*
     &    s35*s34t1**(-1) + s15*s35*s45t1**(-1) - 1.D0/2.D0*s15*s34*
     &    s34t1**(-1) + 1.D0/2.D0*s15*s34*s45t1**(-1) - s14*s15**(-1)*
     &    s15t3 + s14*s15**(-1)*s35 + 1.D0/2.D0*s14*s15**(-1)*s34 + 3.D0
     &    *s14 - s14*s35*s34t1**(-1) + s14*s35*s45t1**(-1) - 1.D0/2.D0*
     &    s14*s34*s34t1**(-1) + 1.D0/2.D0*s14*s34*s45t1**(-1) - 2.D0*
     &    s14**2*s15**(-1) + 5.D0/2.D0*s13 - s13*s35*s34t1**(-1) + s13*
     &    s35*s45t1**(-1) - 1.D0/2.D0*s13*s34*s34t1**(-1) + 1.D0/2.D0*
     &    s13*s34*s45t1**(-1) - 3.D0/2.D0*s13*s14*s15**(-1) )
      D40A = D40A + 21.D0/2.D0 - 1.D0/2.D0*s15**(-1)*s15t3 - 9.D0/2.D0*
     &    s15**(-1)*s45 - 5.D0/2.D0*s15**(-1)*s34 - s34*s34t5**(-1) - 3.
     &    D0/2.D0*s14*s15**(-1) - 4.D0*s14*s34t5**(-1) + s13*s15**(-1)
     &     - s13*s34t5**(-1)

      D40a = D40a/s1345**2

      return
      end

************************************************************************

c     C-type subantenna for q-g-g-g.
      function D40c(s13,s14,s15,s34,s35,s45)
      implicit double precision (a-h,o-z)
      real(8), intent(in) :: s13,s14,s15,s34,s35,s45

      s134  = s13+s14+s34
      s135  = s13+s15+s35
      s145  = s14+s15+s45
      s345  = s34+s35+s45
      s1345 = s13+s14+s15+s34+s35+s45

      s134t = s134
      s135t = s135
      s145t = s145
      s345t = s345


c     1,3,4 antenna (3 soft).
      call DAK(s13,s34,s14,x,y,z)
      omx = 1d0-x
      omy = 1d0-y
      omz = 1d0-z
      s13t5 =   x*s15+  y*s35+  z*s45
      s34t5 = omx*s15+omy*s35+omz*s45

c     3,4,5 antenna (4 soft).
      call DAK(s34,s45,s35,x,y,z)
      omx = 1d0-x
      omy = 1d0-y
      omz = 1d0-z
      s34t1 =   x*s13+  y*s14+  z*s15
      s45t1 = omx*s13+omy*s14+omz*s15

c     4,5,1 antenna (5 soft).
      call DAK(s45,s15,s14,x,y,z)
      omx = 1d0-x
      omy = 1d0-y
      omz = 1d0-z
      s45t3 =   x*s34+  y*s35+  z*s13
      s15t3 = omx*s34+omy*s35+omz*s13

      D40C =
     &  + s134**(-1)*s145**(-1)*S34**(-1)*S45**(-1) * ( s13**3*s35 +
     &    s13**4 )
      D40C = D40C + s134**(-1)*s145**(-1)*S45**(-1) * (  - s14*s15*s35
     &     + s14**2*s15 + s13*s15*s35 - s13*s14*s15 + s13**2*s35 +
     &    s13**2*s15 + s13**3 )
      D40C = D40C + s134**(-1)*s145**(-1) * (  - s14*s35 + s14**2 + s13
     &    *s35 - s13*s14 + s13**2 )
      D40C = D40C + s134**(-1)*s345**(-1)*S34**(-1) * (  - s13*s15**2 )
      D40C = D40C + s134**(-1)*s345**(-1)*S45**(-1) * ( 1.D0/2.D0*
     &    s15**3 + 1.D0/2.D0*s14*s15**2 + 1.D0/2.D0*s14**2*s15 + 1.D0/2.
     &    D0*s14**3 + 1.D0/2.D0*s13*s15**2 + 1.D0/2.D0*s13*s14**2 )
      D40C = D40C + s134**(-1)*s345**(-1) * ( 1.D0/2.D0*s15*s45 + 1.D0/
     &    2.D0*s15*s34 + 1.D0/2.D0*s14*s45 + 1.D0/2.D0*s14*s34 - 1.D0/2.
     &    D0*s14*s15 - 1.D0/2.D0*s14**2 + 1.D0/2.D0*s13*s45 + 1.D0/2.D0
     &    *s13*s34 + 3.D0/2.D0*s13*s15 + 1.D0/2.D0*s13**2 )
      D40C = D40C + s134**(-1)*S13**(-1) * (  - 1.D0/2.D0*s14*s13t5 - 2.
     &    D0*s14*s45 - 2.D0*s14*s35 - 2.D0*s14*s15 )
      D40C = D40C + s134**(-1)*S34**(-1)*S45**(-1) * ( 1.D0/2.D0*s13*
     &    s15*s35 + 1.D0/2.D0*s13*s15**2 + 1.D0/2.D0*s13**2*s35 + 1.D0/
     &    2.D0*s13**2*s15 + s13**3 )
      D40C = D40C + s134**(-1)*S34**(-1) * (  - 3.D0/2.D0*s13*s45 + s13
     &    *s45**2*s34t5**(-1) - 3.D0/2.D0*s13*s35 + 2.D0*s13*s35*s45*
     &    s34t5**(-1) + s13*s35**2*s34t5**(-1) - 2.D0*s13*s15 + 2.D0*
     &    s13*s15*s45*s34t5**(-1) + 2.D0*s13*s15*s35*s34t5**(-1) + s13*
     &    s15**2*s34t5**(-1) + 1.D0/2.D0*s13**2 )
      D40C = D40C + s134**(-1)*S45**(-1) * ( 1.D0/2.D0*s15*s35 + s15**2
     &     + 1.D0/2.D0*s14*s35 - 1.D0/2.D0*s14*s15 + 1.D0/2.D0*s14**2
     &     - 1.D0/2.D0*s13*s35 + 1.D0/2.D0*s13*s15 )
      D40C = D40C + s134**(-1) * (  - 1.D0/2.D0*s13t5 - 2.D0*s45 - 5.D0/
     &    2.D0*s35 - 2.D0*s15 - 3.D0/2.D0*s14 + 1.D0/2.D0*s13 )
      D40C = D40C + s135**(-2)*S13**(-1) * ( s35*s45**2 + s35**2*s45 +
     &    2.D0*s34*s35*s45 + s34*s35**2 + s34**2*s35 + s15*s35*s45 +
     &    s15*s34*s35 + 2.D0*s14*s35*s45 + s14*s35**2 + 2.D0*s14*s34*
     &    s35 + s14*s15*s35 + s14**2*s35 )
      D40C = D40C + s135**(-2) * ( s45**2 + 2.D0*s35*s45 + 2.D0*s34*s45
     &     + 2.D0*s34*s35 + s34**2 + s15*s45 + s15*s34 + 2.D0*s14*s45
     &     + 2.D0*s14*s35 + 2.D0*s14*s34 + s14*s15 + s14**2 + s13*s45
     &     + s13*s34 + s13*s14 )
      D40C = D40C + s135**(-1)*s345**(-1)*(s13+s34)**(-1)*S13**(-1)
     &  * ( 2.D0*s14**3*s15 + 2.D0*s14**4 )
      D40C = D40C + s135**(-1)*s345**(-1)*(s13+s34)**(-1) * ( 2.D0*
     &    s14**3 )
      D40C = D40C + s135**(-1)*s345**(-1)*(s15+s45)**(-1)*S45**(-1)
     &  * ( 2.D0*s14**4 + 2.D0*s13*s14**3 )
      D40C = D40C + s135**(-1)*s345**(-1)*(s15+s45)**(-1) * (  - 2.D0*
     &    s14**3 )
      D40C = D40C + s135**(-1)*s345**(-1)*S13**(-1)*S45**(-1) * ( s15*
     &    s34**3 + s14*s34**3 + 3.D0*s14*s15*s34**2 + 3.D0*s14**2*
     &    s34**2 + 4.D0*s14**2*s15*s34 + 4.D0*s14**3*s34 + 2.D0*s14**3*
     &    s15 + 2.D0*s14**4 )
      D40C = D40C + s135**(-1)*s345**(-1)*S13**(-1) * ( s15*s34**2 +
     &    s14*s34**2 + 3.D0*s14*s15*s34 + 3.D0*s14**2*s34 + 4.D0*s14**2
     &    *s15 + 4.D0*s14**3 )
      D40C = D40C + s135**(-1)*s345**(-1)*S45**(-1) * ( s34**3 - s15*
     &    s34**2 - s15**2*s34 + 2.D0*s14*s34**2 - 4.D0*s14*s15*s34 +
     &    s14**2*s34 + 4.D0*s14**3 - s13*s34**2 - s13*s15*s34 - 3.D0*
     &    s13*s14*s34 )
      D40C = D40C + s135**(-1)*s345**(-1) * ( s34**2 + s15*s45 - s15**2
     &     + s14*s45 + 3.D0*s14*s34 - 2.D0*s14*s15 + 3.D0*s14**2 + s13*
     &    s45 - s13*s15 - s13*s14 )
      D40C = D40C + s135**(-1)*(s13+s34)**(-1)*S13**(-1) * ( s14*s45**2
     &     + 2.D0*s14*s35*s45 + s14*s35**2 + s14*s15*s45 + s14*s15*s35
     &     + 3.D0*s14**2*s45 + 3.D0*s14**2*s35 + 2.D0*s14**2*s15 + 4.D0
     &    *s14**3 )
      D40C = D40C + s135**(-1)*(s15+s45)**(-1)*S45**(-1) * ( s14*s35**2
     &     + 2.D0*s14*s34*s35 + s14*s34**2 + 3.D0*s14**2*s35 + 3.D0*
     &    s14**2*s34 + 4.D0*s14**3 + s13*s14*s35 + s13*s14*s34 + 2.D0*
     &    s13*s14**2 )
      D40C = D40C + s135**(-1)*S13**(-1)*S45**(-1) * ( s34**3 + 3.D0*
     &    s14*s34**2 + 4.D0*s14**2*s34 + 2.D0*s14**3 )
      D40C = D40C + s135**(-1)*S13**(-1) * (  - s45**2 + s35**2 - 2.D0*
     &    s34*s45 - s15*s45 + s15*s35 - s15*s34 + 2.D0*s14*s35 + 2.D0*
     &    s14*s34 + 6.D0*s14**2 )
      D40C = D40C + s135**(-1)*S45**(-1) * (  - s34*s35 - 2.D0*s34**2
     &     - 2.D0*s15*s34 + 2.D0*s14*s35 - 2.D0*s14*s34 + s14*s15 + 3.D0
     &    *s14**2 - s13*s34 + s13*s14 )
      D40C = D40C + s135**(-1) * ( s35 - 2.D0*s34 - s15 )
      D40C = D40C + s145**(-1)*s345**(-1)*S34**(-1) * (  - s14*s45**2
     &     - 5.D0/2.D0*s14**2*s45 - 2.D0*s14**3 - s13*s45**2 - 2.D0*s13
     &    *s14*s45 - 7.D0/2.D0*s13*s14**2 - 1.D0/2.D0*s13**2*s45 - 3.D0
     &    *s13**2*s14 - 1.D0/2.D0*s13**3 )
      D40C = D40C + s145**(-1)*s345**(-1)*S45**(-1) * ( 10.D0*s13*s15*
     &    s34 + 6.D0*s13*s14*s15 + s13**2*s15 )
      D40C = D40C + s145**(-1)*s345**(-1) * ( s45**2 - 1.D0/2.D0*s34*
     &    s45 - 2.D0*s34**2 + 3.D0*s14*s45 + 4.D0*s14*s34 - 7.D0*s13*
     &    s45 + 9.D0/2.D0*s13*s34 - 8.D0*s13*s14 + s13**2 )
      D40C = D40C + s145**(-1)*S13**(-1)*S45**(-1) * (  - s15*s35**2 +
     &    s15*s34**2 + 2.D0*s14*s15*s35 + 2.D0*s14*s15*s34 )
      D40C = D40C + s145**(-1)*S13**(-1) * (  - s35**2 - s34*s45 + s34*
     &    s35 + s14*s35 - s14*s34 )
      D40C = D40C + s145**(-1)*S34**(-1)*S45**(-1) * (  - 1.D0/2.D0*s14
     &    *s15*s35 - 2.D0*s14**2*s15 - 3.D0/2.D0*s13*s15*s35 - 3.D0/2.D0
     &    *s13*s14*s15 - s13**2*s35 - 3.D0/2.D0*s13**2*s15 - s13**3 )
      D40C = D40C + s145**(-1)*S34**(-1) * ( s14*s45 - 1.D0/2.D0*s14*
     &    s35 + 1.D0/2.D0*s14**2 - 3.D0/2.D0*s13*s35 - 5.D0/2.D0*s13*
     &    s14 - 2.D0*s13**2 )
      D40C = D40C + s145**(-1)*S45**(-1) * ( 1.D0/2.D0*s15*s15t3 - 5.D0/
     &    2.D0*s15*s35 - s15*s35**2*s45t3**(-1) + 19.D0/2.D0*s15*s34 -
     &    2.D0*s15*s34*s35*s45t3**(-1) - s15*s34**2*s45t3**(-1) + 9.D0/
     &    2.D0*s14*s15 - s13*s15 - 2.D0*s13*s15*s35*s45t3**(-1) - 2.D0*
     &    s13*s15*s34*s45t3**(-1) - s13**2*s15*s45t3**(-1) )
      D40C = D40C + s145**(-1) * (  - 3.D0*s45 - 7.D0/2.D0*s35 + 4.D0*
     &    s34 - 11.D0/2.D0*s14 - 2.D0*s13 )
      D40C = D40C + s345**(-3)*S45**(-1) * ( 2.D0*s34**2*s34t1*s45t1 -
     &    2.D0*s15*s34**2*s45t1 - 2.D0*s14*s34**2*s45t1 - 2.D0*s13*
     &    s34**2*s45t1 )
      D40C = D40C + s345**(-3) * ( 2.D0*s34*s34t1*s45t1 - 2.D0*s15*s34*
     &    s45t1 - 2.D0*s14*s34*s45t1 - 2.D0*s13*s34*s45t1 )
      D40C = D40C + s345**(-2)*S45**(-1) * (  - 2.D0*s34*s34t1*s45t1 -
     &    2.D0*s34**2*s45t1 + 2.D0*s15*s34*s45t1 + 5.D0*s15*s34**2 + 2.D
     &    0*s14*s34*s45t1 + 5.D0*s14*s34**2 + 2.D0*s13*s34*s45t1 + 5.D0
     &    *s13*s34**2 )
      D40C = D40C + s345**(-2) * (  - s34t1*s45t1 - 2.D0*s34*s45t1 +
     &    s15*s45t1 + 5.D0*s15*s34 + s14*s45t1 + 5.D0*s14*s34 + s13*
     &    s45t1 + 5.D0*s13*s34 )
      D40C = D40C + s345**(-1)*(s13+s34)**(-1)*S13**(-1) * (  - s14*s15
     &    *s45 + s14*s15**2 - s14**2*s45 + 3.D0*s14**2*s15 + 2.D0*
     &    s14**3 )
      D40C = D40C + s345**(-1)*(s13+s34)**(-1) * (  - s14*s45 - s14*s34
     &     + 2.D0*s14*s15 + 3.D0*s14**2 )
      D40C = D40C + s345**(-1)*(s15+s45)**(-1)*S45**(-1) * (  - s14**2*
     &    s34 + 2.D0*s14**3 - s13*s14*s34 + 3.D0*s13*s14**2 + s13**2*
     &    s14 )
      D40C = D40C + s345**(-1)*(s15+s45)**(-1) * ( s14*s45 + s14*s34 -
     &    3.D0*s14**2 - 2.D0*s13*s14 )
      D40C = D40C + s345**(-1)*S13**(-1)*S34**(-1) * ( s14*s15*s45 -
     &    s14*s15**2 - s14**3 )
      D40C = D40C + s345**(-1)*S13**(-1)*S45**(-1) * ( s15*s34**2 + 2.D0
     &    *s15**2*s34 + s14*s34**2 + 4.D0*s14*s15*s34 + 3.D0*s14*s15**2
     &     + 2.D0*s14**2*s34 + 6.D0*s14**2*s15 + 3.D0*s14**3 )
      D40C = D40C + s345**(-1)*S13**(-1) * ( s14*s15 - s14**2 )
      D40C = D40C + s345**(-1)*S34**(-1) * ( 1.D0/2.D0*s15*s45 + 3.D0/2.
     &    D0*s15**2 + 1.D0/2.D0*s14*s45 + s14*s15 - 2.D0*s14**2 + 1.D0/
     &    2.D0*s13*s45 + 3.D0/2.D0*s13*s15 - 3.D0/2.D0*s13*s14 + 1.D0/2.
     &    D0*s13**2 )
      D40C = D40C + s345**(-1)*S45**(-1) * ( s34t1*s45t1 + 2.D0*s34*
     &    s45t1 + 9.D0*s34**2 + 2.D0*s34**2*s34t1*s45t1**(-1) - s15*
     &    s45t1 + 1.D0/2.D0*s15*s34 - 2.D0*s15*s34**2*s45t1**(-1) -
     &    s15**2 - s14*s45t1 - 17.D0/2.D0*s14*s34 - 2.D0*s14*s34**2*
     &    s45t1**(-1) + 9.D0/2.D0*s14*s15 + 3.D0/2.D0*s14**2 - s13*
     &    s45t1 - 21.D0/2.D0*s13*s34 - 2.D0*s13*s34**2*s45t1**(-1) - 3.D
     &    0/2.D0*s13*s15 - 4.D0*s13*s14 - 3.D0/2.D0*s13**2 )
      D40C = D40C + s345**(-1) * ( s45t1 - s45 + 13.D0/2.D0*s34 + 2.D0*
     &    s34*s34t1*s45t1**(-1) + 2.D0*s15 - 2.D0*s15*s34*s45t1**(-1)
     &     - 6.D0*s14 - 2.D0*s14*s34*s45t1**(-1) + 4.D0*s13 - 2.D0*s13*
     &    s34*s45t1**(-1) )
      D40C = D40C + (s34+s45)**(-1)*(s13+s34)**(-1)*(s15+s45)**(-1)*
     & S45**(-1) * ( 2.D0*s14**3*s35 + 2.D0*s14**4 + 2.D0*s13*s14**3 )
      D40C = D40C + (s34+s45)**(-1)*(s13+s34)**(-1)*(s15+s45)**(-1)
     &  * (  - 2.D0*s14**3 )
      D40C = D40C + (s34+s45)**(-1)*(s13+s34)**(-1)*S45**(-1) * ( s14*
     &    s15*s35 + s14*s15**2 + 2.D0*s14**2*s35 + 3.D0*s14**2*s15 + 4.D
     &    0*s14**3 + s13*s14*s15 + 2.D0*s13*s14**2 )
      D40C = D40C + (s34+s45)**(-1)*(s15+s45)**(-1)*S45**(-1) * ( 2.D0*
     &    s14**2*s35 + 2.D0*s14**3 + s13*s14*s35 + 3.D0*s13*s14**2 +
     &    s13**2*s14 )
      D40C = D40C + (s34+s45)**(-1)*(s15+s45)**(-1) * (  - 2.D0*s14**2
     &     - s13*s14 )
      D40C = D40C + (s34+s45)**(-1)*S45**(-1) * ( 2.D0*s14*s35 + 2.D0*
     &    s14*s15 + 4.D0*s14**2 + 3.D0*s13*s14 )
      D40C = D40C + (s13+s15)**(-1)*(s13+s34)**(-1)*(s15+s45)**(-1)*
     & S13**(-1) * ( 2.D0*s14**3*s45 + 2.D0*s14**3*s35 + 2.D0*s14**3*
     &    s15 + 2.D0*s14**4 )
      D40C = D40C + (s13+s15)**(-1)*(s13+s34)**(-1)*S13**(-1) * ( s14*
     &    s45**2 + s14*s35*s45 + s14*s15*s45 + 3.D0*s14**2*s45 + 2.D0*
     &    s14**2*s35 + 2.D0*s14**2*s15 + 2.D0*s14**3 )
      D40C = D40C + (s13+s15)**(-1)*(s15+s45)**(-1)*S13**(-1) * ( s14*
     &    s34*s45 + s14*s34*s35 + s14*s34**2 + s14*s15*s34 + 2.D0*
     &    s14**2*s45 + 2.D0*s14**2*s35 + 3.D0*s14**2*s34 + 2.D0*s14**2*
     &    s15 + 4.D0*s14**3 )
      D40C = D40C + (s13+s15)**(-1)*(s15+s45)**(-1) * ( s14*s34 + 2.D0*
     &    s14**2 )
      D40C = D40C + (s13+s15)**(-1)*S13**(-1) * ( 3.D0*s14*s45 + 2.D0*
     &    s14*s35 + 2.D0*s14*s34 + 2.D0*s14*s15 + 4.D0*s14**2 )
      D40C = D40C + (s13+s15)**(-1) * ( 2.D0*s14 )
      D40C = D40C + (s13+s34)**(-1)*(s15+s45)**(-1)*S13**(-1)*S45**(-1)
     &  * ( 2.D0*s14**3*s35 + 2.D0*s14**4 )
      D40C = D40C + (s13+s34)**(-1)*(s15+s45)**(-1)*S45**(-1) * ( 2.D0*
     &    s14**3 )
      D40C = D40C + (s13+s34)**(-1)*S13**(-1)*S45**(-1) * ( s14*s15*s35
     &     + s14*s15**2 + 2.D0*s14**2*s35 + 3.D0*s14**2*s15 + 4.D0*
     &    s14**3 )
      D40C = D40C + (s13+s34)**(-1)*S13**(-1) * ( s14*s13t5 + 6.D0*s14*
     &    s45 - 2.D0*s14*s45**2*s34t5**(-1) + 7.D0*s14*s35 - 4.D0*s14*
     &    s35*s45*s34t5**(-1) - 2.D0*s14*s35**2*s34t5**(-1) + 9.D0*s14*
     &    s15 - 4.D0*s14*s15*s45*s34t5**(-1) - 4.D0*s14*s15*s35*
     &    s34t5**(-1) - 2.D0*s14*s15**2*s34t5**(-1) + 10.D0*s14**2 )
      D40C = D40C + (s13+s34)**(-1)*S45**(-1) * ( s14*s15 + 2.D0*s14**2
     &     )
      D40C = D40C + (s13+s34)**(-1) * ( s14 )
      D40C = D40C + (s15+s45)**(-1)*S13**(-1)*S45**(-1) * ( s14*s34*s35
     &     + s14*s34**2 + 2.D0*s14**2*s35 + 3.D0*s14**2*s34 + 4.D0*
     &    s14**3 )
      D40C = D40C + (s15+s45)**(-1)*S45**(-1) * ( s14*s15t3 + 7.D0*s14*
     &    s35 - 2.D0*s14*s35**2*s45t3**(-1) + 7.D0*s14*s34 - 4.D0*s14*
     &    s34*s35*s45t3**(-1) - 2.D0*s14*s34**2*s45t3**(-1) + 12.D0*
     &    s14**2 + 9.D0*s13*s14 - 4.D0*s13*s14*s35*s45t3**(-1) - 4.D0*
     &    s13*s14*s34*s45t3**(-1) - 2.D0*s13**2*s14*s45t3**(-1) )
      D40C = D40C + (s15+s45)**(-1) * (  - s14 )
      D40C = D40C + S13**(-1)*S34**(-1)*S45**(-1) * (  - s14*s15*s35 -
     &    s14*s15**2 - s14**3 )
      D40C = D40C + S13**(-1)*S34**(-1) * (  - 2.D0*s14*s45 + 2.D0*s14*
     &    s45**2*s34t5**(-1) - 3.D0*s14*s35 + 4.D0*s14*s35*s45*
     &    s34t5**(-1) + 2.D0*s14*s35**2*s34t5**(-1) - 5.D0*s14*s15 + 4.D
     &    0*s14*s15*s45*s34t5**(-1) + 4.D0*s14*s15*s35*s34t5**(-1) + 2.D
     &    0*s14*s15**2*s34t5**(-1) + 2.D0*s14**3*s34t5**(-1) )
      D40C = D40C + S13**(-1)*S45**(-1) * ( s35**2 + 2.D0*s34*s35 + 2.D0
     &    *s34**2 + 4.D0*s15*s34 + 3.D0*s14*s35 + 6.D0*s14*s34 + 8.D0*
     &    s14*s15 + 8.D0*s14**2 )
      D40C = D40C + S13**(-1) * ( 1.D0/2.D0*s13t5 + s45 + s35 + 9.D0/2.D
     &    0*s34 + s34**2*s34t5**(-1) + s15 + 8.D0*s14 + 3.D0*s14*s34*
     &    s34t5**(-1) + 4.D0*s14**2*s34t5**(-1) )
      D40C = D40C + S34**(-1)*S45**(-1) * (  - 1.D0/2.D0*s15*s35 - 1.D0/
     &    2.D0*s15**2 - s14*s15 + s14**2 + s13*s35 - 1.D0/2.D0*s13*s15
     &     + s13*s14 + 1.D0/2.D0*s13**2 )
      D40C = D40C + S34**(-1) * ( s45 + 1.D0/2.D0*s35 + 3.D0/2.D0*s15
     &     - 1.D0/2.D0*s14 + 4.D0*s14**2*s34t5**(-1) + 1.D0/2.D0*s13 +
     &    3.D0*s13*s14*s34t5**(-1) + s13**2*s34t5**(-1) )
      D40C = D40C + S45**(-1) * (  - s45t1 + 9.D0/2.D0*s35 + s35*s34t1*
     &    s45t1**(-1) - 9.D0*s34 - s34*s34t1*s45t1**(-1) - s15*s35*
     &    s45t1**(-1) + s15*s34*s45t1**(-1) + 10.D0*s14 - s14*s35*
     &    s45t1**(-1) + s14*s34*s45t1**(-1) + s13 - s13*s35*s45t1**(-1)
     &     + s13*s34*s45t1**(-1) )
      D40C = D40C + s34*s34t5**(-1) + 4.D0*s14*s34t5**(-1) + s13*
     &    s34t5**(-1)

      D40c = D40c/s1345**2
      return
      end

************************************************************************

c     Antenna function for g-g-g-g.
      real(8) function F40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34

      s1234=s12+s13+s14+s23+s24+s34
      
      f40 = + s123**(-2)*s1234**(-2)*s12**(-2) * (
     &     + 2.d0*s23**2*s34**2
     &     + 4.d0*s23**2*s24*s34
     &     + 2.d0*s23**2*s24**2
     &     + 4.d0*s14*s23**2*s34
     &     + 4.d0*s14*s23**2*s24
     &     + 2.d0*s14**2*s23**2
     &     )
      f40 = f40 + s123**(-2)*s1234**(-2)*s12**(-1) * (
     &     + 4.d0*s23*s34**2
     &     + 8.d0*s23*s24*s34
     &     + 4.d0*s23*s24**2
     &     + 8.d0*s14*s23*s34
     &     + 8.d0*s14*s23*s24
     &     + 4.d0*s14**2*s23
     &     )
      f40 = f40 + s123**(-2)*s1234**(-2)*s23**(-2) * (
     &     + 2.d0*s13**2*s34**2
     &     + 4.d0*s13**2*s24*s34
     &     + 2.d0*s13**2*s24**2
     &     + 4.d0*s13**2*s14*s34
     &     + 4.d0*s13**2*s14*s24
     &     + 2.d0*s13**2*s14**2
     &     )
      f40 = f40 + s123**(-2)*s1234**(-2) * (
     &     + 4.d0*s34**2
     &     + 8.d0*s24*s34
     &     + 4.d0*s24**2
     &     + 8.d0*s14*s34
     &     + 8.d0*s14*s24
     &     + 4.d0*s14**2
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2)*s12**(-2) * (
     &     - 4.d0*s23*s24*s34**2
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2)*s12**(-1) * (
     &     - 8.d0*s34**3
     &     - 4.d0*s24*s34**2
     &     - 8.d0*s24**2*s34
     &     - 8.d0*s23*s24*s34
     &     - 8.d0*s23**2*s34
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2)*s14**(-1)*s23**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     + 8.d0*s24*s34**3
     &     + 12.d0*s24**2*s34**2
     &     + 8.d0*s24**3*s34
     &     + 2.d0*s24**4
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 4.d0*s34**3
     &     - 12.d0*s24*s34**2
     &     - 12.d0*s24**2*s34
     &     - 4.d0*s24**3
     &     + 6.d0*s23*s34**2
     &     + 12.d0*s23*s24*s34
     &     + 6.d0*s23*s24**2
     &     - 4.d0*s23**2*s34
     &     - 4.d0*s23**2*s24
     &     + 2.d0*s23**3
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 4.d0*s34**3
     &     + 12.d0*s24*s34**2
     &     + 12.d0*s24**2*s34
     &     + 4.d0*s24**3
     &     + 6.d0*s14*s34**2
     &     + 12.d0*s14*s24*s34
     &     + 6.d0*s14*s24**2
     &     + 4.d0*s14**2*s34
     &     + 4.d0*s14**2*s24
     &     + 2.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s124**(-1)*s1234**(-2) * (
     &     - 24.d0*s24*s34
     &     - 12.d0*s24**2
     &     + 12.d0*s23*s24
     &     - 4.d0*s23**2
     &     - 12.d0*s14*s24
     &     + 6.d0*s14*s23
     &     - 4.d0*s14**2
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s12**(-1)*s14**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     + 4.d0*s24*s34**3
     &     + 6.d0*s24**2*s34**2
     &     + 4.d0*s24**3*s34
     &     + 2.d0*s24**4
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s12**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     + 8.d0*s14*s24**3
     &     + 12.d0*s14**2*s24**2
     &     + 8.d0*s14**3*s24
     &     + 2.d0*s14**4
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 6.d0*s34**3
     &     + 16.d0*s24*s34**2
     &     + 18.d0*s24**2*s34
     &     + 12.d0*s24**3
     &     + 10.d0*s14*s34**2
     &     + 24.d0*s14*s24*s34
     &     + 24.d0*s14*s24**2
     &     + 10.d0*s14**2*s34
     &     + 20.d0*s14**2*s24
     &     + 6.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s14**(-1)*s23**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     + 8.d0*s24*s34**3
     &     + 12.d0*s24**2*s34**2
     &     + 8.d0*s24**3*s34
     &     + 2.d0*s24**4
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 4.d0*s34**3
     &     - 8.d0*s24*s34**2
     &     - 6.d0*s24**2*s34
     &     + 2.d0*s23*s34**2
     &     + 4.d0*s23*s24*s34
     &     - 2.d0*s23**2*s34
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s23**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     + 4.d0*s14*s24**3
     &     + 6.d0*s14**2*s24**2
     &     + 4.d0*s14**3*s24
     &     + 2.d0*s14**4
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 6.d0*s34**3
     &     + 20.d0*s24*s34**2
     &     + 24.d0*s24**2*s34
     &     + 12.d0*s24**3
     &     + 10.d0*s14*s34**2
     &     + 24.d0*s14*s24*s34
     &     + 18.d0*s14*s24**2
     &     + 10.d0*s14**2*s34
     &     + 16.d0*s14**2*s24
     &     + 6.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2)*s34**(-1) * (
     &     - 6.d0*s14*s24**2
     &     - 4.d0*s14*s23*s24
     &     - 2.d0*s14*s23**2
     &     - 4.d0*s14**2*s24
     &     + 2.d0*s14**2*s23
     &     - 4.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s134**(-1)*s1234**(-2) * (
     &     - 16.d0*s34**2
     &     - 28.d0*s24*s34
     &     - 8.d0*s24**2
     &     + 6.d0*s23*s34
     &     - 4.d0*s23**2
     &     - 24.d0*s14*s34
     &     - 24.d0*s14*s24
     &     + 6.d0*s14*s23
     &     - 16.d0*s14**2
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2)*s12**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     + 8.d0*s14*s24**3
     &     + 12.d0*s14**2*s24**2
     &     + 8.d0*s14**3*s24
     &     + 2.d0*s14**4
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 2.d0*s34**3
     &     + 4.d0*s24*s34**2
     &     + 6.d0*s24**2*s34
     &     + 4.d0*s24**3
     &     + 4.d0*s14*s34**2
     &     + 12.d0*s14*s24*s34
     &     + 12.d0*s14*s24**2
     &     + 6.d0*s14**2*s34
     &     + 12.d0*s14**2*s24
     &     + 4.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2)*s23**(-2) * (
     &     - 4.d0*s13*s14**2*s34
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     - 8.d0*s14*s34**2
     &     - 8.d0*s14**3
     &     - 8.d0*s13*s14*s34
     &     - 4.d0*s13*s14**2
     &     - 8.d0*s13**2*s14
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     - 4.d0*s14*s24**2
     &     - 6.d0*s14**2*s24
     &     - 4.d0*s14**3
     &     - 4.d0*s13*s24**2
     &     - 4.d0*s13*s14*s24
     &     - 6.d0*s13*s14**2
     &     + 2.d0*s13**2*s24
     &     - 4.d0*s13**2*s14
     &     - 2.d0*s13**3
     &     )
      f40 = f40 + s123**(-1)*s234**(-1)*s1234**(-2) * (
     &     - 4.d0*s14*s34
     &     + 4.d0*s14*s24
     &     + 6.d0*s14**2
     &     - 4.d0*s13*s34
     &     - 8.d0*s13*s24
     &     - 16.d0*s13*s14
     &     + 2.d0*s13**2
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s12**(-2) * (
     &     - 8.d0*s23*s24*s34
     &     - 4.d0*s23*s24**2
     &     + 4.d0*s23**2*s34
     &     + 4.d0*s23**2*s24
     &     - 4.d0*s14*s23*s24
     &     + 4.d0*s14*s23**2
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s12**(-1)*s14**(-1) * (
     &     - 4.d0*s23*s34**2
     &     + 2.d0*s23**2*s34
     &     - 2.d0*s23**3
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     - 4.d0*s24**3
     &     - 2.d0*s23*s24**2
     &     - 2.d0*s23**2*s24
     &     - 10.d0*s14*s24**2
     &     - 2.d0*s14*s23**2
     &     - 10.d0*s14**2*s24
     &     + 2.d0*s14**2*s23
     &     - 4.d0*s14**3
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s12**(-1) * (
     &     - 20.d0*s34**2
     &     - 26.d0*s24*s34
     &     - 22.d0*s24**2
     &     + 12.d0*s23*s34
     &     - 6.d0*s23**2
     &     - 24.d0*s14*s34
     &     - 28.d0*s14*s24
     &     + 14.d0*s14*s23
     &     - 16.d0*s14**2
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     - 4.d0*s34**3
     &     - 10.d0*s24*s34**2
     &     - 10.d0*s24**2*s34
     &     - 4.d0*s24**3
     &     - 2.d0*s13*s34**2
     &     + 2.d0*s13*s24**2
     &     - 2.d0*s13**2*s34
     &     - 2.d0*s13**2*s24
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s14**(-1) * (
     &     + 6.d0*s34**2
     &     + 16.d0*s24*s34
     &     + 6.d0*s24**2
     &     - 4.d0*s23*s34
     &     - 4.d0*s23*s24
     &     - 2.d0*s13*s34
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s23**(-2) * (
     &     - 4.d0*s13*s34**2
     &     - 4.d0*s13*s24*s34
     &     - 8.d0*s13*s14*s34
     &     + 4.d0*s13**2*s34
     &     + 4.d0*s13**2*s24
     &     + 4.d0*s13**2*s14
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s23**(-1)*s34**(-1) * (
     &     + 4.d0*s13*s14**2
     &     + 2.d0*s13**2*s14
     &     + 2.d0*s13**3
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s23**(-1) * (
     &     - 16.d0*s34**2
     &     - 24.d0*s24*s34
     &     - 18.d0*s24**2
     &     - 16.d0*s14*s34
     &     - 26.d0*s14*s24
     &     - 20.d0*s14**2
     &     - 6.d0*s13*s34
     &     + 8.d0*s13*s24
     &     + 4.d0*s13*s14
     &     - 6.d0*s13**2
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 4.d0*s14*s24
     &     - 4.d0*s14*s23
     &     + 6.d0*s14**2
     &     + 4.d0*s13*s24
     &     - 2.d0*s13*s14
     &     )
      f40 = f40 + s123**(-1)*s1234**(-2) * (
     &     + 26.d0*s34
     &     + 28.d0*s24
     &     - 12.d0*s23
     &     + 28.d0*s14
     &     )
      f40 = f40 + s124**(-2)*s1234**(-2)*s12**(-2) * (
     &     + 2.d0*s24**2*s34**2
     &     + 4.d0*s23*s24**2*s34
     &     + 2.d0*s23**2*s24**2
     &     + 4.d0*s13*s24**2*s34
     &     + 4.d0*s13*s23*s24**2
     &     + 2.d0*s13**2*s24**2
     &     )
      f40 = f40 + s124**(-2)*s1234**(-2)*s14**(-2) * (
     &     + 2.d0*s24**2*s34**2
     &     + 4.d0*s23*s24**2*s34
     &     + 2.d0*s23**2*s24**2
     &     + 4.d0*s13*s24**2*s34
     &     + 4.d0*s13*s23*s24**2
     &     + 2.d0*s13**2*s24**2
     &     )
      f40 = f40 + s124**(-2)*s1234**(-2) * (
     &     + 2.d0*s34**2
     &     + 4.d0*s23*s34
     &     + 2.d0*s23**2
     &     + 4.d0*s13*s34
     &     + 4.d0*s13*s23
     &     + 2.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2)*s12**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     + 8.d0*s23*s24**3
     &     + 12.d0*s23**2*s24**2
     &     + 8.d0*s23**3*s24
     &     + 2.d0*s23**4
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 2.d0*s34**3
     &     - 4.d0*s24*s34**2
     &     + 6.d0*s24**2*s34
     &     - 4.d0*s24**3
     &     - 4.d0*s23*s34**2
     &     + 12.d0*s23*s24*s34
     &     - 12.d0*s23*s24**2
     &     + 6.d0*s23**2*s34
     &     - 12.d0*s23**2*s24
     &     - 4.d0*s23**3
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2)*s14**(-2) * (
     &     - 4.d0*s23**2*s24*s34
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 8.d0*s23*s34**2
     &     - 8.d0*s23*s24*s34
     &     - 8.d0*s23*s24**2
     &     - 4.d0*s23**2*s24
     &     - 8.d0*s23**3
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 4.d0*s23*s24**2
     &     + 6.d0*s23**2*s24
     &     + 4.d0*s23**3
     &     - 4.d0*s14*s24**2
     &     - 4.d0*s14*s23*s24
     &     - 6.d0*s14*s23**2
     &     - 2.d0*s14**2*s24
     &     + 4.d0*s14**2*s23
     &     - 2.d0*s14**3
     &     )
      f40 = f40 + s124**(-1)*s134**(-1)*s1234**(-2) * (
     &     - 4.d0*s34**2
     &     + 6.d0*s24*s34
     &     - 4.d0*s24**2
     &     - 24.d0*s23*s24
     &     - 6.d0*s14*s34
     &     + 4.d0*s14*s24
     &     - 4.d0*s14**2
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s12**(-1)*s23**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     + 4.d0*s13*s34**3
     &     + 6.d0*s13**2*s34**2
     &     + 4.d0*s13**3*s34
     &     + 2.d0*s13**4
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s12**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     - 8.d0*s13*s24**3
     &     + 12.d0*s13**2*s24**2
     &     - 8.d0*s13**3*s24
     &     + 2.d0*s13**4
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 2.d0*s34**3
     &     + 4.d0*s24**2*s34
     &     + 2.d0*s24**3
     &     + 4.d0*s13*s34**2
     &     - 8.d0*s13*s24*s34
     &     - 4.d0*s13*s24**2
     &     + 6.d0*s13**2*s34
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s14**(-1)*s23**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     + 8.d0*s13*s34**3
     &     + 12.d0*s13**2*s34**2
     &     + 8.d0*s13**3*s34
     &     + 2.d0*s13**4
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s14**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     - 4.d0*s13*s24**3
     &     + 6.d0*s13**2*s24**2
     &     - 4.d0*s13**3*s24
     &     + 2.d0*s13**4
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s14**(-1) * (
     &     + 2.d0*s34**3
     &     + 4.d0*s24**2*s34
     &     + 2.d0*s24**3
     &     + 8.d0*s13*s34**2
     &     - 4.d0*s13*s24*s34
     &     + 4.d0*s13*s24**2
     &     + 12.d0*s13**2*s34
     &     - 6.d0*s13**2*s24
     &     + 8.d0*s13**3
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     - 4.d0*s34**3
     &     + 2.d0*s14*s34**2
     &     - 2.d0*s14**2*s34
     &     - 8.d0*s13*s34**2
     &     + 4.d0*s13*s14*s34
     &     - 6.d0*s13**2*s34
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 2.d0*s14*s24**2
     &     + 2.d0*s14**2*s24
     &     - 4.d0*s13*s24**2
     &     + 4.d0*s13*s14*s24
     &     + 6.d0*s13**2*s24
     &     )
      f40 = f40 + s124**(-1)*s234**(-1)*s1234**(-2) * (
     &     - 4.d0*s34**2
     &     + 4.d0*s24*s34
     &     - 4.d0*s24**2
     &     + 2.d0*s14*s34
     &     - 2.d0*s14*s24
     &     - 2.d0*s14**2
     &     - 8.d0*s13*s34
     &     + 16.d0*s13*s24
     &     + 4.d0*s13*s14
     &     - 2.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s12**(-2) * (
     &     + 4.d0*s24**2*s34
     &     - 8.d0*s23*s24*s34
     &     + 4.d0*s23*s24**2
     &     - 4.d0*s23**2*s24
     &     + 4.d0*s13*s24**2
     &     - 4.d0*s13*s23*s24
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s12**(-1)*s23**(-1) * (
     &     + 4.d0*s24*s34**2
     &     + 2.d0*s24**2*s34
     &     + 2.d0*s24**3
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 8.d0*s23*s24**2
     &     + 8.d0*s23**2*s24
     &     + 6.d0*s23**3
     &     + 8.d0*s13*s24**2
     &     + 10.d0*s13*s23**2
     &     - 8.d0*s13**2*s24
     &     + 10.d0*s13**2*s23
     &     + 6.d0*s13**3
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s12**(-1) * (
     &     - 16.d0*s34**2
     &     + 4.d0*s24*s34
     &     - 8.d0*s24**2
     &     - 2.d0*s23*s34
     &     - 12.d0*s23*s24
     &     - 12.d0*s23**2
     &     - 10.d0*s13*s34
     &     + 4.d0*s13*s24
     &     - 8.d0*s13*s23
     &     - 4.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s14**(-2) * (
     &     - 4.d0*s24*s34**2
     &     + 4.d0*s24**2*s34
     &     - 8.d0*s23*s24*s34
     &     + 4.d0*s23*s24**2
     &     - 4.d0*s13*s24*s34
     &     + 4.d0*s13*s24**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     + 4.d0*s34**3
     &     + 10.d0*s24*s34**2
     &     + 6.d0*s24**2*s34
     &     + 2.d0*s24**3
     &     + 2.d0*s13*s34**2
     &     + 8.d0*s13*s24*s34
     &     - 2.d0*s13**2*s34
     &     + 4.d0*s13**2*s24
     &     - 2.d0*s13**3
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s14**(-1)*s34**(-1) * (
     &     + 4.d0*s23*s24**2
     &     + 2.d0*s23**2*s24
     &     + 2.d0*s23**3
     &     + 4.d0*s13*s24**2
     &     - 4.d0*s13*s23*s24
     &     + 4.d0*s13*s23**2
     &     - 6.d0*s13**2*s24
     &     + 6.d0*s13**2*s23
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 12.d0*s34**2
     &     - 14.d0*s24*s34
     &     - 8.d0*s24**2
     &     - 2.d0*s23*s34
     &     + 6.d0*s23*s24
     &     - 16.d0*s23**2
     &     - 8.d0*s13*s34
     &     - 10.d0*s13*s23
     &     - 4.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 10.d0*s34**2
     &     + 4.d0*s24*s34
     &     + 4.d0*s24**2
     &     + 2.d0*s14*s34
     &     + 2.d0*s14*s24
     &     + 2.d0*s14**2
     &     + 12.d0*s13*s34
     &     + 4.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 4.d0*s23*s24
     &     + 6.d0*s23**2
     &     - 4.d0*s14*s23
     &     + 4.d0*s13*s24
     &     + 4.d0*s13*s23
     &     - 4.d0*s13*s14
     &     - 2.d0*s13**2
     &     )
      f40 = f40 + s124**(-1)*s1234**(-2) * (
     &     + 10.d0*s34
     &     - 12.d0*s24
     &     + 10.d0*s23
     &     + 4.d0*s13
     &     )
      f40 = f40 + s134**(-2)*s1234**(-2)*s14**(-2) * (
     &     + 2.d0*s24**2*s34**2
     &     + 4.d0*s23*s24*s34**2
     &     + 2.d0*s23**2*s34**2
     &     + 4.d0*s12*s24*s34**2
     &     + 4.d0*s12*s23*s34**2
     &     + 2.d0*s12**2*s34**2
     &     )
      f40 = f40 + s134**(-2)*s1234**(-2)*s14**(-1) * (
     &     + 4.d0*s24**2*s34
     &     + 8.d0*s23*s24*s34
     &     + 4.d0*s23**2*s34
     &     + 8.d0*s12*s24*s34
     &     + 8.d0*s12*s23*s34
     &     + 4.d0*s12**2*s34
     &     )
      f40 = f40 + s134**(-2)*s1234**(-2)*s34**(-2) * (
     &     + 2.d0*s14**2*s24**2
     &     + 4.d0*s14**2*s23*s24
     &     + 2.d0*s14**2*s23**2
     &     + 4.d0*s12*s14**2*s24
     &     + 4.d0*s12*s14**2*s23
     &     + 2.d0*s12**2*s14**2
     &     )
      f40 = f40 + s134**(-2)*s1234**(-2)*s34**(-1) * (
     &     + 4.d0*s14*s24**2
     &     + 8.d0*s14*s23*s24
     &     + 4.d0*s14*s23**2
     &     + 8.d0*s12*s14*s24
     &     + 8.d0*s12*s14*s23
     &     + 4.d0*s12**2*s14
     &     )
      f40 = f40 + s134**(-2)*s1234**(-2) * (
     &     + 6.d0*s24**2
     &     + 12.d0*s23*s24
     &     + 6.d0*s23**2
     &     + 12.d0*s12*s24
     &     + 12.d0*s12*s23
     &     + 6.d0*s12**2
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2)*s14**(-1)*s23**(-1)
     &  * (
     &     + 2.d0*s34**4
     &     - 8.d0*s12*s34**3
     &     + 12.d0*s12**2*s34**2
     &     - 8.d0*s12**3*s34
     &     + 2.d0*s12**4
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 4.d0*s24*s34**2
     &     - 2.d0*s24**2*s34
     &     - 2.d0*s24**3
     &     - 4.d0*s12*s34**2
     &     + 4.d0*s12*s24*s34
     &     - 4.d0*s12*s24**2
     &     + 6.d0*s12**2*s34
     &     - 6.d0*s12**2*s24
     &     - 4.d0*s12**3
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 4.d0*s34**3
     &     + 6.d0*s14*s34**2
     &     + 4.d0*s14**2*s34
     &     + 2.d0*s14**3
     &     - 12.d0*s12*s34**2
     &     - 12.d0*s12*s14*s34
     &     - 4.d0*s12*s14**2
     &     + 12.d0*s12**2*s34
     &     + 6.d0*s12**2*s14
     &     - 4.d0*s12**3
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2)*s34**(-2) * (
     &     - 4.d0*s12**2*s14*s24
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     - 8.d0*s12*s24**2
     &     - 8.d0*s12*s14*s24
     &     - 8.d0*s12*s14**2
     &     - 4.d0*s12**2*s24
     &     - 8.d0*s12**3
     &     )
      f40 = f40 + s134**(-1)*s234**(-1)*s1234**(-2) * (
     &     - 12.d0*s12*s34
     &     - 12.d0*s12*s24
     &     - 12.d0*s12*s14
     &     + 12.d0*s12**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s12**(-1)*s14**(-1) * (
     &     + 4.d0*s24*s34**2
     &     + 6.d0*s24**2*s34
     &     + 4.d0*s24**3
     &     + 4.d0*s23*s34**2
     &     + 4.d0*s23*s24*s34
     &     + 6.d0*s23*s24**2
     &     - 2.d0*s23**2*s34
     &     + 4.d0*s23**2*s24
     &     + 2.d0*s23**3
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 2.d0*s23*s24**2
     &     - 2.d0*s23**2*s24
     &     - 2.d0*s23**3
     &     + 10.d0*s14*s24**2
     &     + 8.d0*s14*s23*s24
     &     + 4.d0*s14*s23**2
     &     + 6.d0*s14**2*s24
     &     + 2.d0*s14**3
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 4.d0*s34**2
     &     + 6.d0*s24*s34
     &     + 16.d0*s24**2
     &     + 20.d0*s23*s24
     &     + 8.d0*s23**2
     &     + 6.d0*s14*s34
     &     + 8.d0*s14*s24
     &     + 4.d0*s14**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s14**(-2) * (
     &     + 4.d0*s24*s34**2
     &     - 4.d0*s24**2*s34
     &     + 4.d0*s23*s34**2
     &     - 8.d0*s23*s24*s34
     &     + 4.d0*s12*s34**2
     &     - 4.d0*s12*s24*s34
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     + 8.d0*s24*s34**2
     &     + 8.d0*s24**2*s34
     &     + 6.d0*s24**3
     &     + 8.d0*s12*s34**2
     &     + 10.d0*s12*s24**2
     &     - 8.d0*s12**2*s34
     &     + 10.d0*s12**2*s24
     &     + 6.d0*s12**3
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s14**(-1) * (
     &     - 4.d0*s34**2
     &     + 4.d0*s24*s34
     &     - 6.d0*s24**2
     &     + 14.d0*s23*s34
     &     - 12.d0*s23*s24
     &     - 14.d0*s23**2
     &     + 12.d0*s12*s34
     &     - 8.d0*s12*s24
     &     - 14.d0*s12*s23
     &     - 6.d0*s12**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s23**(-1)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 6.d0*s14*s24**2
     &     + 4.d0*s14**2*s24
     &     + 6.d0*s12*s24**2
     &     + 4.d0*s12*s14*s24
     &     + 4.d0*s12*s14**2
     &     + 4.d0*s12**2*s24
     &     - 2.d0*s12**2*s14
     &     + 2.d0*s12**3
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 12.d0*s24*s34
     &     + 12.d0*s24**2
     &     + 12.d0*s14*s24
     &     + 12.d0*s12*s34
     &     + 8.d0*s12*s24
     &     + 12.d0*s12*s14
     &     - 4.d0*s12**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s34**(-2) * (
     &     - 4.d0*s14*s24**2
     &     - 4.d0*s14*s23*s24
     &     + 4.d0*s14**2*s24
     &     + 4.d0*s14**2*s23
     &     - 8.d0*s12*s14*s24
     &     + 4.d0*s12*s14**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2)*s34**(-1) * (
     &     - 6.d0*s24**2
     &     - 8.d0*s23*s24
     &     - 6.d0*s23**2
     &     + 8.d0*s14*s24
     &     + 14.d0*s14*s23
     &     - 4.d0*s14**2
     &     - 12.d0*s12*s24
     &     - 14.d0*s12*s23
     &     + 12.d0*s12*s14
     &     - 14.d0*s12**2
     &     )
      f40 = f40 + s134**(-1)*s1234**(-2) * (
     &     - 12.d0*s34
     &     + 8.d0*s24
     &     + 32.d0*s23
     &     - 12.d0*s14
     &     + 28.d0*s12
     &     )
      f40 = f40 + s234**(-2)*s1234**(-2)*s23**(-2) * (
     &     + 2.d0*s14**2*s34**2
     &     + 4.d0*s13*s14*s34**2
     &     + 2.d0*s13**2*s34**2
     &     + 4.d0*s12*s14*s34**2
     &     + 4.d0*s12*s13*s34**2
     &     + 2.d0*s12**2*s34**2
     &     )
      f40 = f40 + s234**(-2)*s1234**(-2)*s23**(-1) * (
     &     + 4.d0*s14**2*s34
     &     + 8.d0*s13*s14*s34
     &     + 4.d0*s13**2*s34
     &     + 8.d0*s12*s14*s34
     &     + 8.d0*s12*s13*s34
     &     + 4.d0*s12**2*s34
     &     )
      f40 = f40 + s234**(-2)*s1234**(-2)*s34**(-2) * (
     &     + 2.d0*s14**2*s24**2
     &     + 4.d0*s13*s14*s24**2
     &     + 2.d0*s13**2*s24**2
     &     + 4.d0*s12*s14*s24**2
     &     + 4.d0*s12*s13*s24**2
     &     + 2.d0*s12**2*s24**2
     &     )
      f40 = f40 + s234**(-2)*s1234**(-2) * (
     &     + 4.d0*s14**2
     &     + 8.d0*s13*s14
     &     + 4.d0*s13**2
     &     + 8.d0*s12*s14
     &     + 8.d0*s12*s13
     &     + 4.d0*s12**2
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s12**(-1)*s23**(-1) * (
     &     + 4.d0*s14*s34**2
     &     - 2.d0*s14**2*s34
     &     + 2.d0*s14**3
     &     + 4.d0*s13*s34**2
     &     + 4.d0*s13*s14*s34
     &     + 4.d0*s13*s14**2
     &     + 6.d0*s13**2*s34
     &     + 6.d0*s13**2*s14
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 8.d0*s14*s24**2
     &     + 8.d0*s14**2*s24
     &     + 6.d0*s14**3
     &     + 8.d0*s13*s24**2
     &     + 10.d0*s13*s14**2
     &     - 8.d0*s13**2*s24
     &     + 10.d0*s13**2*s14
     &     + 6.d0*s13**3
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 8.d0*s14*s34
     &     + 4.d0*s14*s24
     &     + 4.d0*s14**2
     &     + 8.d0*s13*s34
     &     + 4.d0*s13*s24
     &     + 8.d0*s13*s14
     &     + 4.d0*s13**2
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     + 8.d0*s13*s34**2
     &     + 8.d0*s13**2*s34
     &     + 6.d0*s13**3
     &     + 8.d0*s12*s34**2
     &     + 10.d0*s12*s13**2
     &     - 8.d0*s12**2*s34
     &     + 10.d0*s12**2*s13
     &     + 6.d0*s12**3
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s14**(-1)*s34**(-1) * (
     &     + 4.d0*s13*s24**2
     &     - 6.d0*s13**2*s24
     &     + 4.d0*s13**3
     &     + 4.d0*s12*s24**2
     &     - 4.d0*s12*s13*s24
     &     + 6.d0*s12*s13**2
     &     + 2.d0*s12**2*s24
     &     + 4.d0*s12**2*s13
     &     + 2.d0*s12**3
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s14**(-1) * (
     &     + 4.d0*s13*s34
     &     - 4.d0*s13*s24
     &     + 6.d0*s13**2
     &     + 4.d0*s12*s34
     &     - 4.d0*s12*s24
     &     + 4.d0*s12*s13
     &     - 2.d0*s12**2
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s23**(-2) * (
     &     + 4.d0*s14*s34**2
     &     + 4.d0*s13*s34**2
     &     - 8.d0*s13*s14*s34
     &     - 4.d0*s13**2*s34
     &     + 4.d0*s12*s34**2
     &     - 4.d0*s12*s13*s34
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     - 8.d0*s34**2
     &     + 12.d0*s14*s34
     &     - 16.d0*s14**2
     &     + 4.d0*s13*s34
     &     - 10.d0*s13*s14
     &     - 8.d0*s13**2
     &     + 20.d0*s12*s34
     &     - 10.d0*s12*s14
     &     - 12.d0*s12*s13
     &     - 12.d0*s12**2
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s34**(-2) * (
     &     + 4.d0*s14*s24**2
     &     - 4.d0*s14**2*s24
     &     + 4.d0*s13*s24**2
     &     - 4.d0*s13*s14*s24
     &     + 4.d0*s12*s24**2
     &     - 8.d0*s12*s14*s24
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     - 4.d0*s24**2
     &     - 6.d0*s14*s24
     &     - 6.d0*s14**2
     &     - 4.d0*s13*s14
     &     - 2.d0*s13**2
     &     + 4.d0*s12*s24
     &     - 6.d0*s12*s14
     &     - 12.d0*s12*s13
     &     - 14.d0*s12**2
     &     )
      f40 = f40 + s234**(-1)*s1234**(-2) * (
     &     - 4.d0*s34
     &     + 4.d0*s24
     &     + 22.d0*s14
     &     + 4.d0*s13
     &     + 24.d0*s12
     &     )
      f40 = f40 + s1234**(-2)*s12**(-2) * (
     &     + 2.d0*s24**2
     &     - 8.d0*s23*s24
     &     + 2.d0*s23**2
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s14**(-1)*s23**(-1)*s34**(-1)
     &  * (
     &     + 2.d0*s24**4
     &     + 4.d0*s13*s24**3
     &     + 6.d0*s13**2*s24**2
     &     + 4.d0*s13**3*s24
     &     + 2.d0*s13**4
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s14**(-1)*s23**(-1) * (
     &     + 2.d0*s34**3
     &     + 4.d0*s24*s34**2
     &     + 6.d0*s24**2*s34
     &     + 4.d0*s24**3
     &     + 4.d0*s13*s34**2
     &     + 12.d0*s13*s24*s34
     &     + 12.d0*s13*s24**2
     &     + 6.d0*s13**2*s34
     &     + 12.d0*s13**2*s24
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s14**(-1)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 6.d0*s23*s24**2
     &     + 4.d0*s23**2*s24
     &     + 2.d0*s23**3
     &     + 12.d0*s13*s24**2
     &     + 12.d0*s13*s23*s24
     &     + 4.d0*s13*s23**2
     &     + 12.d0*s13**2*s24
     &     + 6.d0*s13**2*s23
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s14**(-1) * (
     &     + 12.d0*s34**2
     &     + 20.d0*s24*s34
     &     + 18.d0*s24**2
     &     + 6.d0*s23*s34
     &     + 20.d0*s23*s24
     &     + 12.d0*s23**2
     &     + 16.d0*s13*s34
     &     + 28.d0*s13*s24
     &     + 16.d0*s13*s23
     &     + 16.d0*s13**2
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s23**(-1)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 6.d0*s14*s24**2
     &     + 4.d0*s14**2*s24
     &     + 2.d0*s14**3
     &     + 12.d0*s13*s24**2
     &     + 12.d0*s13*s14*s24
     &     + 4.d0*s13*s14**2
     &     + 12.d0*s13**2*s24
     &     + 6.d0*s13**2*s14
     &     + 4.d0*s13**3
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s23**(-1) * (
     &     + 8.d0*s34**2
     &     + 14.d0*s24*s34
     &     + 14.d0*s24**2
     &     + 8.d0*s14*s34
     &     + 18.d0*s14*s24
     &     + 10.d0*s14**2
     &     + 20.d0*s13*s34
     &     + 28.d0*s13*s24
     &     + 20.d0*s13*s14
     &     + 18.d0*s13**2
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 12.d0*s24**2
     &     + 8.d0*s23*s24
     &     + 2.d0*s23**2
     &     + 8.d0*s14*s24
     &     + 4.d0*s14*s23
     &     + 2.d0*s14**2
     &     + 16.d0*s13*s24
     &     + 14.d0*s13*s23
     &     + 14.d0*s13*s14
     &     + 18.d0*s13**2
     &     )
      f40 = f40 + s1234**(-2)*s12**(-1) * (
     &     - 8.d0*s34
     &     + 22.d0*s24
     &     + 14.d0*s23
     &     - 4.d0*s14
     &     + 14.d0*s13
     &     )
      f40 = f40 + s1234**(-2)*s14**(-2) * (
     &     + 2.d0*s34**2
     &     - 8.d0*s24*s34
     &     + 2.d0*s24**2
     &     )
      f40 = f40 + s1234**(-2)*s14**(-1)*s23**(-1)*s34**(-1) * (
     &     + 4.d0*s24**3
     &     + 12.d0*s13*s24**2
     &     + 12.d0*s13**2*s24
     &     + 4.d0*s13**3
     &     + 6.d0*s12*s24**2
     &     + 12.d0*s12*s13*s24
     &     + 6.d0*s12*s13**2
     &     + 4.d0*s12**2*s24
     &     + 4.d0*s12**2*s13
     &     + 2.d0*s12**3
     &     )
      f40 = f40 + s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     + 4.d0*s34**2
     &     + 8.d0*s24*s34
     &     + 10.d0*s24**2
     &     + 8.d0*s13*s34
     &     + 26.d0*s13*s24
     &     + 10.d0*s13**2
     &     - 6.d0*s12*s34
     &     + 14.d0*s12*s24
     &     + 14.d0*s12*s13
     &     + 10.d0*s12**2
     &     )
      f40 = f40 + s1234**(-2)*s14**(-1)*s34**(-1) * (
     &     + 14.d0*s24**2
     &     + 14.d0*s23*s24
     &     + 8.d0*s23**2
     &     + 24.d0*s13*s24
     &     + 24.d0*s13*s23
     &     + 24.d0*s13**2
     &     + 14.d0*s12*s24
     &     + 12.d0*s12*s23
     &     + 24.d0*s12*s13
     &     + 8.d0*s12**2
     &     )
      f40 = f40 + s1234**(-2)*s14**(-1) * (
     &     + 14.d0*s34
     &     + 20.d0*s24
     &     - 8.d0*s23
     &     + 18.d0*s13
     &     )
      f40 = f40 + s1234**(-2)*s23**(-2) * (
     &     + 2.d0*s34**2
     &     - 8.d0*s13*s34
     &     + 2.d0*s13**2
     &     )
      f40 = f40 + s1234**(-2)*s23**(-1)*s34**(-1) * (
     &     + 18.d0*s24**2
     &     + 20.d0*s14*s24
     &     + 8.d0*s14**2
     &     + 28.d0*s13*s24
     &     + 14.d0*s13*s14
     &     + 14.d0*s13**2
     &     + 20.d0*s12*s24
     &     + 8.d0*s12*s14
     &     + 18.d0*s12*s13
     &     + 10.d0*s12**2
     &     )
      f40 = f40 + s1234**(-2)*s23**(-1) * (
     &     + 14.d0*s34
     &     + 10.d0*s24
     &     - 8.d0*s14
     &     + 20.d0*s13
     &     - 8.d0*s12
     &     )
      f40 = f40 + s1234**(-2)*s34**(-2) * (
     &     + 2.d0*s24**2
     &     - 8.d0*s14*s24
     &     + 2.d0*s14**2
     &     )
      f40 = f40 + s1234**(-2)*s34**(-1) * (
     &     + 18.d0*s24
     &     + 14.d0*s14
     &     + 18.d0*s13
     &     - 8.d0*s12
     &     )
      f40 = f40 + s1234**(-2) * (
     &     + 42.d0
     &     )
      f40 = f40 + 2d0*s1234**(-2)*s12**(-2)*s34**(-2) * (
     &     (s14*s23-s13*s24)**2)
      f40 = f40 + 2d0*s1234**(-2)*s14**(-2)*s23**(-2) * (
     &     (s13*s24-s12*s34)**2)

      F40 = f40

      return
      end

************************************************************************

c     Sub-antenna function F40a for F40.
c     F40(1,2,3,4) = F40a(1,2,3,4) + F40b(1,2,3,4)
c     + F40a(1,4,3,2) + F40b(1,4,3,2)
c     + F40b(2,3,4,1) + F40a(2,1,4,3)
c     + F40b(4,3,2,1) + F40a(4,1,2,3)
      real(8) function F40a(s12,s13,s14,s23,s24,s34)
      implicit double precision (a-h,o-z)
      real(8), intent(in) :: s12,s13,s14,s23,s24,s34

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s134 = s13+s14+s34
      s234 = s23+s24+s34

      s1234 = s12+s13+s14+s23+s24+s34

      s123t = s123
      s124t = s124
      s134t = s134
      s234t = s234

c     1,2,3 antenna (2 soft).
      call DAK(s12,s23,s13,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s12t4s2 =   x*s14+  y*s24+  z*s34
      s23t4s2 = omx*s14+omy*s24+omz*s34

c     2,3,4 antenna (3 soft).
      call DAK(s23,s34,s24,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s23t1s3 =   x*s12+  y*s13+  z*s14
      s34t1s3 = omx*s12+omy*s13+omz*s14

c     3,4,1 antenna (4 soft).
      call DAK(s34,s14,s13,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s34t2s4 =   x*s23+  y*s24+  z*s12
      s14t2s4 = omx*s23+omy*s24+omz*s12

c     4,1,2 antenna (1 soft).
      call DAK(s14,s12,s24,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s14t3s1 =   x*s34+  y*s13+  z*s23
      s12t3s1 = omx*s34+omy*s13+omz*s23

      F40AFF = + 37.D0/2.D0
     &  - 2.D0*s12**(-2)*s123**(-1)*s124**(-1)*s13*s14*s34**2
     &  + 2.D0*s12**(-2)*s123**(-1)*s13*s34**2
     &  + s12**(-2)*s124**(-2)*s14**2*s34**2
     &  + 2.D0*s12**(-2)*s124**(-2)*s13*s14**2*s34
     &  + s12**(-2)*s124**(-2)*s13**2*s14**2
     &  + 2.D0*s12**(-2)*s124**(-1)*s14**2*s34
     &  - 4.D0*s12**(-2)*s124**(-1)*s13*s14*s34
     &  + 2.D0*s12**(-2)*s124**(-1)*s13*s14**2
     &  - 2.D0*s12**(-2)*s124**(-1)*s13**2*s14
     &  - s12**(-2)*s34**2
     &  - 2.D0*s12**(-2)*s14*s34
     &  + 2.D0*s12**(-2)*s13*s34
     &  - 2.D0*s12**(-2)*s13*s14
     &  + s12**(-2)*s13**2

      F40AFF = F40AFF - 2.D0*s12**(-2)*s24*s123**(-1)*s124**(-1)*s13*
     & s34**2
     &  + 2.D0*s12**(-2)*s24*s124**(-1)*s34**2
     &  + 2.D0*s12**(-2)*s24*s34
     &  + 2.D0*s12**(-2)*s24*s13
     &  - s12**(-2)*s24**2*s124**(-2)*s34**2
     &  + 1.D0/2.D0*s12**(-2)*s24**2*s124**(-2)*s14*s34
     &  - 2.D0*s12**(-2)*s24**2*s124**(-2)*s13*s34
     &  + 1.D0/2.D0*s12**(-2)*s24**2*s124**(-2)*s13*s14
     &  - s12**(-2)*s24**2*s124**(-2)*s13**2
     &  - 5.D0/2.D0*s12**(-2)*s24**2*s124**(-1)*s34
     &  + 1.D0/2.D0*s12**(-2)*s24**2*s124**(-1)*s14
     &  - 5.D0/2.D0*s12**(-2)*s24**2*s124**(-1)*s13
     &  - 1.D0/2.D0*s12**(-2)*s24**2
     &  + 1.D0/2.D0*s12**(-2)*s24**3*s124**(-2)*s34

      F40AFF = F40AFF + 1.D0/2.D0*s12**(-2)*s24**3*s124**(-2)*s13
     &  + 1.D0/2.D0*s12**(-2)*s24**3*s124**(-1)
     &  + 2.D0*s12**(-2)*s23*s124**(-2)*s14**2*s34
     &  + 2.D0*s12**(-2)*s23*s124**(-2)*s13*s14**2
     &  + 2.D0*s12**(-2)*s23*s124**(-1)*s14**2
     &  - 2.D0*s12**(-2)*s23*s124**(-1)*s13*s14
     &  - 2.D0*s12**(-2)*s23*s34
     &  - 2.D0*s12**(-2)*s23*s14
     &  - s12**(-2)*s23*s24*s123**(-1)*s124**(-1)*s14*s34
     &  - s12**(-2)*s23*s24*s123**(-1)*s124**(-1)*s13*s34
     &  + s12**(-2)*s23*s24*s123**(-1)*s34
     &  - s12**(-2)*s23*s24*s123**(-1)*s13
     &  + 5.D0*s12**(-2)*s23*s24*s124**(-1)*s34
     &  - s12**(-2)*s23*s24*s124**(-1)*s14
     &  + 2.D0*s12**(-2)*s23*s24*s124**(-1)*s13

      F40AFF = F40AFF + 4.D0*s12**(-2)*s23*s24
     &  - s12**(-2)*s23*s24**2*s123**(-1)*s124**(-1)*s34
     &  - 2.D0*s12**(-2)*s23*s24**2*s124**(-2)*s34
     &  + 1.D0/2.D0*s12**(-2)*s23*s24**2*s124**(-2)*s14
     &  - 2.D0*s12**(-2)*s23*s24**2*s124**(-2)*s13
     &  - 7.D0/2.D0*s12**(-2)*s23*s24**2*s124**(-1)
     &  + 1.D0/2.D0*s12**(-2)*s23*s24**3*s124**(-2)
     &  + 1.D0/2.D0*s12**(-2)*s23**2*s123**(-2)*s13*s34
     &  + 1.D0/2.D0*s12**(-2)*s23**2*s123**(-2)*s13*s14
     &  - 1.D0/2.D0*s12**(-2)*s23**2*s123**(-1)*s34
     &  - 1.D0/2.D0*s12**(-2)*s23**2*s123**(-1)*s14
     &  + 1.D0/2.D0*s12**(-2)*s23**2*s123**(-1)*s13
     &  + s12**(-2)*s23**2*s124**(-2)*s14**2
     &  - 3.D0/2.D0*s12**(-2)*s23**2
     &  + 1.D0/2.D0*s12**(-2)*s23**2*s24*s123**(-2)*s13

      F40AFF = F40AFF - s12**(-2)*s23**2*s24*s123**(-1)*s124**(-1)*s34
     &  - 3.D0/2.D0*s12**(-2)*s23**2*s24*s123**(-1)
     &  + 2.D0*s12**(-2)*s23**2*s24*s124**(-1)
     &  - s12**(-2)*s23**2*s24**2*s124**(-2)
     &  + 1.D0/2.D0*s12**(-2)*s23**3*s123**(-2)*s34
     &  + 1.D0/2.D0*s12**(-2)*s23**3*s123**(-2)*s14
     &  + 1.D0/2.D0*s12**(-2)*s23**3*s123**(-1)
     &  + 1.D0/2.D0*s12**(-2)*s23**3*s24*s123**(-2)
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s34**4
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s14*
     & s34**3
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s14**3*
     & s34
     &  + 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s14**4
     &  + s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s13*s14**3

      F40AFF = F40AFF + 3.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*
     & s234**(-1)*s13**2*s34**2
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s13**2*
     & s14**2
     &  + s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s13**3*s34
     &  - 1.D0/4.D0*s12**(-1)*s23**(-1)*s124**(-1)*s234**(-1)*s13**3*
     & s14
     &  + 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s34**3
     &  - 5.D0/4.D0*s12**(-1)*s23**(-1)*s124**(-1)*s14*s34**2
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s14**2*s34
     &  - 1.D0/4.D0*s12**(-1)*s23**(-1)*s124**(-1)*s14**3
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s13*s14*s34
     &  + 7.D0/4.D0*s12**(-1)*s23**(-1)*s124**(-1)*s13*s14**2
     &  - 3.D0/2.D0*s12**(-1)*s23**(-1)*s124**(-1)*s13**2*s34
     &  + 3.D0/4.D0*s12**(-1)*s23**(-1)*s124**(-1)*s13**2*s14

      F40AFF = F40AFF - s12**(-1)*s23**(-1)*s124**(-1)*s13**3
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s234**(-1)*s34**3
     &  + 3.D0/4.D0*s12**(-1)*s23**(-1)*s234**(-1)*s14**2*s34
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s234**(-1)*s14**3
     &  + 1.D0/4.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13*s34**2
     &  + 2.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13*s14*s34
     &  + 3.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13*s14**2
     &  + 7.D0/4.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13**2*s34
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13**2*s14
     &  + 5.D0/4.D0*s12**(-1)*s23**(-1)*s234**(-1)*s13**3
     &  - 2.D0*s12**(-1)*s23**(-1)*s23t4s2**(-1)*s13*s123t**2
     &  + 13.D0/4.D0*s12**(-1)*s23**(-1)*s34**2
     &  + 9.D0/2.D0*s12**(-1)*s23**(-1)*s14*s34
     &  + 7.D0*s12**(-1)*s23**(-1)*s14**2
     &  + 2.D0*s12**(-1)*s23**(-1)*s14**3*s34**(-1)

      F40AFF = F40AFF - s12**(-1)*s23**(-1)*s13*s123t
     &  + 67.D0/12.D0*s12**(-1)*s23**(-1)*s13*s34
     &  + 103.D0/12.D0*s12**(-1)*s23**(-1)*s13*s14
     &  + 4.D0*s12**(-1)*s23**(-1)*s13*s14**2*s34**(-1)
     &  + 23.D0/6.D0*s12**(-1)*s23**(-1)*s13**2
     &  + 3.D0*s12**(-1)*s23**(-1)*s13**2*s14*s34**(-1)
     &  + s12**(-1)*s23**(-1)*s13**3*s34**(-1)
     &  + s12**(-1)*s23**(-1)*s23t4s2*s13
     &  - s12**(-1)*s23**(-1)*s23t4s2*s13*s34*s123t**(-1)
     &  - s12**(-1)*s23**(-1)*s23t4s2*s13*s14*s123t**(-1)
     &  - s12**(-1)*s23**(-1)*s23t4s2*s13**2*s123t**(-1)
     &  + s12**(-1)*s23**(-1)*s12t4s2*s13*s34*s123t**(-1)
     &  + s12**(-1)*s23**(-1)*s12t4s2*s13*s14*s123t**(-1)
     &  + s12**(-1)*s23**(-1)*s12t4s2*s13**2*s123t**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s234**(-1)*
     & s34**3

      F40AFF = F40AFF - 1.D0/2.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*
     & s234**(-1)*s14**3
     &  + 1.D0/4.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s234**(-1)*
     & s13**3
     &  - 7.D0/4.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s34**2
     &  - s12**(-1)*s23**(-1)*s24*s124**(-1)*s14*s34
     &  - 1.D0/4.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s14**2
     &  - 3.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s13*s34
     &  - 3.D0/4.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s13*s14
     &  - 3.D0/4.D0*s12**(-1)*s23**(-1)*s24*s124**(-1)*s13**2
     &  - 1.D0/2.D0*s12**(-1)*s23**(-1)*s24*s234**(-1)*s34**2
     &  + s12**(-1)*s23**(-1)*s24*s234**(-1)*s14*s34
     &  + 13.D0/4.D0*s12**(-1)*s23**(-1)*s24*s234**(-1)*s14**2
     &  + 5.D0/4.D0*s12**(-1)*s23**(-1)*s24*s234**(-1)*s13*s34
     &  + 3.D0*s12**(-1)*s23**(-1)*s24*s234**(-1)*s13*s14

      F40AFF = F40AFF + 5.D0/4.D0*s12**(-1)*s23**(-1)*s24*s234**(-1)*
     & s13**2
     &  + 6.D0*s12**(-1)*s23**(-1)*s24*s34
     &  + 17.D0/2.D0*s12**(-1)*s23**(-1)*s24*s14
     &  + 4.D0*s12**(-1)*s23**(-1)*s24*s14**2*s34**(-1)
     &  + 2.D0*s12**(-1)*s23**(-1)*s24*s13*s14**(-1)*s34
     &  + 28.D0/3.D0*s12**(-1)*s23**(-1)*s24*s13
     &  + 15.D0/2.D0*s12**(-1)*s23**(-1)*s24*s13*s14*s34**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s23**(-1)*s24*s13**2*s14**(-1)
     &  + 17.D0/4.D0*s12**(-1)*s23**(-1)*s24*s13**2*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**(-1)*s24*s13**3*s14**(-1)*s34**(-1)
     &  - s12**(-1)*s23**(-1)*s24*s23t4s2*s13*s123t**(-1)
     &  + s12**(-1)*s23**(-1)*s24*s12t4s2*s13*s123t**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*
     & s13**2

      F40AFF = F40AFF - 2.D0*s12**(-1)*s23**(-1)*s24**2*s124**(-1)*s34
     &  - 7.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s124**(-1)*s13
     &  + 3.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s234**(-1)*s34
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s24**2*s234**(-1)*s14
     &  + 5.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s234**(-1)*s13
     &  + 17.D0/4.D0*s12**(-1)*s23**(-1)*s24**2
     &  + 3.D0*s12**(-1)*s23**(-1)*s24**2*s14*s34**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s13*s14**(-1)
     &  + 17.D0/4.D0*s12**(-1)*s23**(-1)*s24**2*s13*s34**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23**(-1)*s24**2*s13**2*s14**(-1)*
     & s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23**(-1)*s24**3*s124**(-1)*s234**(-1)*
     & s13
     &  - s12**(-1)*s23**(-1)*s24**3*s124**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**(-1)*s24**3*s234**(-1)

      F40AFF = F40AFF + s12**(-1)*s23**(-1)*s24**3*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**(-1)*s24**3*s13*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s123**(-2)*s13*s34**2
     &  - s12**(-1)*s123**(-2)*s13*s14*s34
     &  - 1.D0/2.D0*s12**(-1)*s123**(-2)*s13*s14**2
     &  - s12**(-1)*s123**(-2)*s13**2*s34
     &  - s12**(-1)*s123**(-2)*s13**2*s14
     &  - 1.D0/4.D0*s12**(-1)*s123**(-2)*s13**3
     &  + 3.D0/2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s14*s34**2
     &  - 7.D0/2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s14**2*s34
     &  - 2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13*s34**2
     &  - 1.D0/2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13*s14*s34
     &  + 3.D0/2.D0*s12**(-1)*s123**(-1)*s234**(-1)*s14*s34**2
     &  - 3.D0/2.D0*s12**(-1)*s123**(-1)*s234**(-1)*s14**2*s34
     &  + 2.D0*s12**(-1)*s123**(-1)*s234**(-1)*s14**4*s34**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13*
     & s34**2
     &  - s12**(-1)*s123**(-1)*s234**(-1)*s13*s14*s34
     &  - 15.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13*s14**2
     &  + 15.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13*s14**3*
     & s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**2*s34
     &  - 1.D0/2.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**2*s14
     &  + 15.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**2*s14**2*
     & s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**3
     &  + 7.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**3*s14*
     & s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s123**(-1)*s234**(-1)*s13**4*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s123**(-1)*s14**(-1)*s34**3

      F40AFF = F40AFF + 1.D0/2.D0*s12**(-1)*s123**(-1)*s14**(-1)*s34**4
     & *s134**(-1)
     &  - 3.D0*s12**(-1)*s123**(-1)*s34**2
     &  + 3.D0/2.D0*s12**(-1)*s123**(-1)*s34**3*s134**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s123**(-1)*s14*s34
     &  + 5.D0/2.D0*s12**(-1)*s123**(-1)*s14*s34**2*s134**(-1)
     &  - 9.D0/4.D0*s12**(-1)*s123**(-1)*s14**2
     &  + 11.D0/4.D0*s12**(-1)*s123**(-1)*s14**2*s34*s134**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s123**(-1)*s14**3*s34**(-1)
     &  + 7.D0/4.D0*s12**(-1)*s123**(-1)*s14**3*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s123**(-1)*s14**4*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s123**(-1)*s13*s14**(-1)*s34**2
     &  + 1.D0/2.D0*s12**(-1)*s123**(-1)*s13*s34
     &  - 1.D0/4.D0*s12**(-1)*s123**(-1)*s13*s14*s34*s134**(-1)
     &  + 4.D0*s12**(-1)*s123**(-1)*s13*s14**2*s34**(-1)

      F40AFF = F40AFF + s12**(-1)*s123**(-1)*s13*s14**2*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s123**(-1)*s13**2*s14**(-1)*s34
     &  - s12**(-1)*s123**(-1)*s13**2
     &  + 1.D0/4.D0*s12**(-1)*s123**(-1)*s13**2*s34*s134**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s123**(-1)*s13**2*s14*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s123**(-1)*s13**2*s14*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s123**(-1)*s13**3*s34**(-1)
     &  + 7.D0/4.D0*s12**(-1)*s123**(-1)*s13**3*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s123**(-1)*s13**3*s14*s34**(-1)*
     & s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s123**(-1)*s13**4*s34**(-1)*s134**(-1)
     &  + 2.D0*s12**(-1)*s124**(-2)*s14*s34**2
     &  - 1.D0/4.D0*s12**(-1)*s124**(-2)*s14**3
     &  + 4.D0*s12**(-1)*s124**(-2)*s13*s14*s34
     &  + 2.D0*s12**(-1)*s124**(-2)*s13**2*s14

      F40AFF = F40AFF - 13.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*
     & s34**3
     &  - 3.D0/2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s14*s34**2
     &  - 1.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s14**2*s34
     &  - s12**(-1)*s124**(-1)*s234**(-1)*s14**3
     &  + 1.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s14**4*s34**(-1)
     &  - 13.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13*s34**2
     &  + 3.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13*s14**2
     &  + 3.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13*s14**3*
     & s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**2*s14**2*
     & s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3
     &  - 1.D0/4.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3*s14*
     & s34**(-1)

      F40AFF = F40AFF + 11.D0/4.D0*s12**(-1)*s124**(-1)*s34**2
     &  + 9.D0/2.D0*s12**(-1)*s124**(-1)*s14*s34
     &  - 5.D0/2.D0*s12**(-1)*s124**(-1)*s14**2
     &  - 1.D0/4.D0*s12**(-1)*s124**(-1)*s14**2*s34*s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s124**(-1)*s14**3*s34**(-1)
     &  - 7.D0/4.D0*s12**(-1)*s124**(-1)*s14**3*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s124**(-1)*s14**4*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s13*s34
     &  - 5.D0/4.D0*s12**(-1)*s124**(-1)*s13*s34**2*s134**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s13*s14
     &  + 1.D0/4.D0*s12**(-1)*s124**(-1)*s13*s14*s34*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s124**(-1)*s13*s14**2*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s124**(-1)*s13*s14**2*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s124**(-1)*s13*s14**3*s34**(-1)*
     & s134**(-1)

      F40AFF = F40AFF - 7.D0/4.D0*s12**(-1)*s124**(-1)*s13**2*s34*
     & s134**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s124**(-1)*s13**2*s14*s34**(-1)
     &  - s12**(-1)*s124**(-1)*s13**2*s14*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s13**3*s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s124**(-1)*s13**3*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s124**(-1)*s13**4*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s12t3s1*s14
     &  - 2.D0*s12**(-1)*s234**(-1)*s34**2
     &  - 5.D0/2.D0*s12**(-1)*s234**(-1)*s14*s34
     &  + 5.D0*s12**(-1)*s234**(-1)*s14**2
     &  + 2.D0*s12**(-1)*s234**(-1)*s14**3*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s234**(-1)*s13*s34
     &  + 3.D0/2.D0*s12**(-1)*s234**(-1)*s13*s14
     &  + 5.D0/2.D0*s12**(-1)*s234**(-1)*s13*s14**2*s34**(-1)

      F40AFF = F40AFF + 3.D0/2.D0*s12**(-1)*s234**(-1)*s13**2*s14*
     & s34**(-1)
     &  + s12**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s34
     &  + 1.D0/2.D0*s12**(-1)*s34**2*s134**(-1)
     &  + 12.D0*s12**(-1)*s14
     &  + 2.D0*s12**(-1)*s14*s34*s134**(-1)
     &  + 17.D0/4.D0*s12**(-1)*s14**2*s34**(-1)
     &  + 2.D0*s12**(-1)*s14**2*s134**(-1)
     &  + s12**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  - s12**(-1)*s13*s14**(-1)*s34
     &  + 28.D0/3.D0*s12**(-1)*s13
     &  - 5.D0/4.D0*s12**(-1)*s13*s34*s134**(-1)
     &  + 33.D0/4.D0*s12**(-1)*s13*s14*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s13*s14*s134**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s13*s14**2*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s13**2*s14**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s13**2*s14**(-1)*s34*s134**(-1)
     &  + 29.D0/4.D0*s12**(-1)*s13**2*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s13**2*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s13**2*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  - s12**(-1)*s23t4s2*s13*s123t**(-1)
     &  + s12**(-1)*s12t4s2*s13*s123t**(-1)
     &  - s12**(-1)*s24*s123**(-2)*s13*s34
     &  - s12**(-1)*s24*s123**(-2)*s13*s14
     &  - s12**(-1)*s24*s123**(-2)*s13**2
     &  + 3.D0/2.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s34**2

      F40AFF = F40AFF - 3.D0/2.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*
     & s13*s34
     &  + 5.D0/4.D0*s12**(-1)*s24*s123**(-1)*s234**(-1)*s34**2
     &  + 7.D0/4.D0*s12**(-1)*s24*s123**(-1)*s234**(-1)*s14*s34
     &  + 4.D0*s12**(-1)*s24*s123**(-1)*s234**(-1)*s14**3*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24*s123**(-1)*s234**(-1)*s13*s34
     &  - 7.D0/2.D0*s12**(-1)*s24*s123**(-1)*s234**(-1)*s13*s14
     &  - s12**(-1)*s24*s123**(-1)*s234**(-1)*s13**2
     &  - s12**(-1)*s24*s123**(-1)*s14**(-1)*s34**2
     &  + s12**(-1)*s24*s123**(-1)*s14**(-1)*s34**3*s134**(-1)
     &  - 35.D0/4.D0*s12**(-1)*s24*s123**(-1)*s34
     &  + 4.D0*s12**(-1)*s24*s123**(-1)*s34**2*s134**(-1)
     &  - 7.D0*s12**(-1)*s24*s123**(-1)*s14
     &  + 27.D0/4.D0*s12**(-1)*s24*s123**(-1)*s14*s34*s134**(-1)
     &  + s12**(-1)*s24*s123**(-1)*s14**2*s34**(-1)

      F40AFF = F40AFF + 21.D0/4.D0*s12**(-1)*s24*s123**(-1)*s14**2*
     & s134**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s24*s123**(-1)*s14**3*s34**(-1)*
     & s134**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13*s14**(-1)*s34
     &  - 7.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13
     &  - 3.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13*s34*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13*s14*s34**(-1)
     &  + 2.D0*s12**(-1)*s24*s123**(-1)*s13*s14*s134**(-1)
     &  + 13.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13**2*s34**(-1)
     &  - 17.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13**2*s134**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13**2*s14*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24*s123**(-1)*s13**3*s14**(-1)*
     & s134**(-1)

      F40AFF = F40AFF - 3.D0*s12**(-1)*s24*s123**(-1)*s13**3*s34**(-1)*
     & s134**(-1)
     &  + s12**(-1)*s24*s124**(-2)*s14*s34
     &  - 1.D0/4.D0*s12**(-1)*s24*s124**(-2)*s14**2
     &  + s12**(-1)*s24*s124**(-2)*s13*s14
     &  - 5.D0/4.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s34**2
     &  + 1.D0/4.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s14*s34
     &  - 3.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13*s34
     &  - 3.D0/4.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13*s14
     &  - 5.D0/4.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**2
     &  + s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**3*
     & s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24*s124**(-1)*s34
     &  - 5.D0/4.D0*s12**(-1)*s24*s124**(-1)*s34**2*s134**(-1)

      F40AFF = F40AFF - 3.D0/2.D0*s12**(-1)*s24*s124**(-1)*s14
     &  + 1.D0/4.D0*s12**(-1)*s24*s124**(-1)*s14**2*s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24*s124**(-1)*s14**2*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24*s124**(-1)*s14**3*s34**(-1)*
     & s134**(-1)
     &  - 5.D0*s12**(-1)*s24*s124**(-1)*s13
     &  + 1.D0/2.D0*s12**(-1)*s24*s124**(-1)*s13*s14*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s24*s124**(-1)*s13*s14*s134**(-1)
     &  - 11.D0/4.D0*s12**(-1)*s24*s124**(-1)*s13**2*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24*s124**(-1)*s13**2*s134**(-1)
     &  - 9.D0/4.D0*s12**(-1)*s24*s234**(-1)*s34
     &  + 3.D0/4.D0*s12**(-1)*s24*s234**(-1)*s14
     &  + 19.D0/4.D0*s12**(-1)*s24*s234**(-1)*s14**2*s34**(-1)
     &  + 2.D0*s12**(-1)*s24*s234**(-1)*s13
     &  + s12**(-1)*s24*s234**(-1)*s13*s14*s34**(-1)

      F40AFF = F40AFF - 11.D0/4.D0*s12**(-1)*s24*s234**(-1)*s13**2*
     & s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s24*s14**(-1)*s34
     &  + s12**(-1)*s24*s14**(-1)*s34**2*s134**(-1)
     &  + 21.D0/4.D0*s12**(-1)*s24
     &  + s12**(-1)*s24*s34*s134**(-1)
     &  + 35.D0/4.D0*s12**(-1)*s24*s14*s34**(-1)
     &  - s12**(-1)*s24*s14*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s24*s14**2*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s24*s13*s14**(-1)*s34*s134**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s24*s13*s34**(-1)
     &  + 17.D0/4.D0*s12**(-1)*s24*s13*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24*s13*s14*s34**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s24*s13**2*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24*s13**2*s14**(-1)*s134**(-1)

      F40AFF = F40AFF + 17.D0/4.D0*s12**(-1)*s24*s13**2*s34**(-1)*
     & s134**(-1)
     &  + s12**(-1)*s24*s12t3s1*s14**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24**2*s123**(-2)*s13
     &  + 7.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s124**(-1)*s34
     &  - 1.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s124**(-1)*s13
     &  + s12**(-1)*s24**2*s123**(-1)*s234**(-1)*s34
     &  + 7.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s234**(-1)*s14
     &  + 9.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s234**(-1)*s14**2*
     & s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s234**(-1)*s13
     &  - 3.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s14**(-1)*s34
     &  + 3.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s14**(-1)*s34**2*
     & s134**(-1)

      F40AFF = F40AFF - 7.D0/2.D0*s12**(-1)*s24**2*s123**(-1)
     &  + 21.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s34*s134**(-1)
     &  + 21.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s14*s134**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s14**2*s34**(-1)*
     & s134**(-1)
     &  - 7.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s13*s14**(-1)
     &  - 9.D0/2.D0*s12**(-1)*s24**2*s123**(-1)*s13*s34**(-1)
     &  + 19.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s13*s134**(-1)
     &  + s12**(-1)*s24**2*s123**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s13**2*s14**(-1)*
     & s134**(-1)
     &  + 19.D0/4.D0*s12**(-1)*s24**2*s123**(-1)*s13**2*s34**(-1)*
     & s134**(-1)
     &  + s12**(-1)*s24**2*s124**(-2)*s34
     &  - 1.D0/4.D0*s12**(-1)*s24**2*s124**(-2)*s14

      F40AFF = F40AFF + s12**(-1)*s24**2*s124**(-2)*s13
     &  + 7.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s34
     &  + 1.D0/2.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s14
     &  - 5.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13
     &  - 3.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13*s14*
     & s34**(-1)
     &  + 13.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13**2*
     & s34**(-1)
     &  + 11.D0/4.D0*s12**(-1)*s24**2*s124**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s34*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24**2*s124**(-1)*s14*s34**(-1)
     &  + 4.D0*s12**(-1)*s24**2*s124**(-1)*s13*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24**2*s124**(-1)*s13*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24**2*s234**(-1)
     &  + 3.D0*s12**(-1)*s24**2*s234**(-1)*s14*s34**(-1)

      F40AFF = F40AFF + 3.D0*s12**(-1)*s24**2*s234**(-1)*s13*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24**2*s14**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s24**2*s14**(-1)*s34*s134**(-1)
     &  + 35.D0/4.D0*s12**(-1)*s24**2*s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24**2*s134**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s24**2*s13*s14**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s24**2*s13*s14**(-1)*s134**(-1)
     &  - 9.D0/2.D0*s12**(-1)*s24**2*s13*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24**3*s123**(-1)*s124**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s24**3*s123**(-1)*s234**(-1)
     &  + 5.D0/2.D0*s12**(-1)*s24**3*s123**(-1)*s234**(-1)*s14*
     & s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s24**3*s123**(-1)*s14**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24**3*s123**(-1)*s14**(-1)*s34*
     & s134**(-1)

      F40AFF = F40AFF + 1.D0/2.D0*s12**(-1)*s24**3*s123**(-1)*s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24**3*s123**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12**(-1)*s24**3*s123**(-1)*s13*s14**(-1)*
     & s134**(-1)
     &  - 3.D0*s12**(-1)*s24**3*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24**3*s124**(-2)
     &  + 3.D0/4.D0*s12**(-1)*s24**3*s124**(-1)*s234**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s24**3*s124**(-1)*s234**(-1)*s14*
     & s34**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s24**3*s124**(-1)*s234**(-1)*s13*
     & s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24**3*s124**(-1)*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s24**3*s124**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s24**3*s234**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s24**3*s14**(-1)*s134**(-1)

      F40AFF = F40AFF + 2.D0*s12**(-1)*s24**3*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24**4*s123**(-1)*s234**(-1)*s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s24**4*s124**(-1)*s234**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24**4*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23*s123**(-2)*s13**2
     &  - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s124**(-1)*s14*s34
     &  - s12**(-1)*s23*s123**(-1)*s124**(-1)*s13*s34
     &  - s12**(-1)*s23*s123**(-1)*s234**(-1)*s34**2
     &  + 5.D0/2.D0*s12**(-1)*s23*s123**(-1)*s234**(-1)*s14*s34
     &  - 19.D0/4.D0*s12**(-1)*s23*s123**(-1)*s234**(-1)*s14**2
     &  + 5.D0/4.D0*s12**(-1)*s23*s123**(-1)*s234**(-1)*s14**3*
     & s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s123**(-1)*s234**(-1)*s13*s34
     &  - s12**(-1)*s23*s123**(-1)*s234**(-1)*s13*s14**2*s34**(-1)
     &  - s12**(-1)*s23*s123**(-1)*s23t4s2**(-1)*s123t**2

      F40AFF = F40AFF - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s123t
     &  - 13.D0/12.D0*s12**(-1)*s23*s123**(-1)*s34
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s34**2*s134**(-1)
     &  - 55.D0/12.D0*s12**(-1)*s23*s123**(-1)*s14
     &  + 2.D0*s12**(-1)*s23*s123**(-1)*s14**2*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s13*s14**(-1)*s34
     &  - 11.D0/6.D0*s12**(-1)*s23*s123**(-1)*s13
     &  - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s13*s14*s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23*s123**(-1)*s13*s14*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23*s123**(-1)*s13**2*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s123**(-1)*s13**2*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s123**(-1)*s13**3*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s23t4s2
     &  - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s23t4s2*s34*s123t**(-1)

      F40AFF = F40AFF - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s23t4s2*s14*
     & s123t**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s23t4s2*s13*s123t**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s12t4s2*s34*s123t**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s12t4s2*s14*s123t**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s12t4s2*s13*s123t**(-1)
     &  + 4.D0*s12**(-1)*s23*s124**(-2)*s14*s34
     &  + 4.D0*s12**(-1)*s23*s124**(-2)*s13*s14
     &  - 23.D0/4.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s34**2
     &  - 3.D0/2.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s14*s34
     &  + 1.D0/2.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s14**2
     &  - 6.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s13*s34
     &  - 9.D0/4.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s13**2
     &  - 3.D0/4.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s13**3*
     & s34**(-1)

      F40AFF = F40AFF + 23.D0/4.D0*s12**(-1)*s23*s124**(-1)*s34
     &  - 7.D0/4.D0*s12**(-1)*s23*s124**(-1)*s34**2*s134**(-1)
     &  + 3.D0*s12**(-1)*s23*s124**(-1)*s14
     &  + 3.D0/4.D0*s12**(-1)*s23*s124**(-1)*s14*s34*s134**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s23*s124**(-1)*s14**2*s34**(-1)
     &  + 15.D0/4.D0*s12**(-1)*s23*s124**(-1)*s14**2*s134**(-1)
     &  + 7.D0/4.D0*s12**(-1)*s23*s124**(-1)*s14**3*s34**(-1)*
     & s134**(-1)
     &  + 2.D0*s12**(-1)*s23*s124**(-1)*s13
     &  - 3.D0*s12**(-1)*s23*s124**(-1)*s13*s34*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s124**(-1)*s13*s14*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s23*s124**(-1)*s13*s14*s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23*s124**(-1)*s13*s14**2*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s124**(-1)*s13**2*s134**(-1)

      F40AFF = F40AFF + 3.D0/4.D0*s12**(-1)*s23*s124**(-1)*s13**3*
     & s34**(-1)*s134**(-1)
     &  - 2.D0*s12**(-1)*s23*s234**(-1)*s34
     &  - 9.D0/2.D0*s12**(-1)*s23*s234**(-1)*s14
     &  + 9.D0/4.D0*s12**(-1)*s23*s234**(-1)*s14**2*s34**(-1)
     &  - 2.D0*s12**(-1)*s23*s234**(-1)*s13
     &  - 5.D0/4.D0*s12**(-1)*s23*s234**(-1)*s13**2*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s14**(-1)*s34
     &  + s12**(-1)*s23*s14**(-1)*s34**2*s134**(-1)
     &  + s12**(-1)*s23
     &  - s12**(-1)*s23*s34*s134**(-1)
     &  + 11.D0/2.D0*s12**(-1)*s23*s14*s34**(-1)
     &  - 19.D0/4.D0*s12**(-1)*s23*s14*s134**(-1)
     &  - 9.D0/4.D0*s12**(-1)*s23*s14**2*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s13*s14**(-1)*s34*s134**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s23*s13*s34**(-1)
     &  + 5.D0/2.D0*s12**(-1)*s23*s13*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s13*s14*s34**(-1)*s134**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s23*s13**2*s34**(-1)*s134**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s124**(-1)*s34
     &  + s12**(-1)*s23*s24*s123**(-1)*s124**(-1)*s14
     &  + s12**(-1)*s23*s24*s123**(-1)*s124**(-1)*s13
     &  + 3.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s234**(-1)*s34
     &  - 1.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s234**(-1)*s14
     &  - s12**(-1)*s23*s24*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s234**(-1)*s13
     &  - 1.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s14**(-1)*s34
     &  - 61.D0/12.D0*s12**(-1)*s23*s24*s123**(-1)
     &  - s12**(-1)*s23*s24*s123**(-1)*s34*s134**(-1)
     &  - 5.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s14*s34**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s13*
     & s14**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s13*s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s13*s134**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23*s24*s123**(-1)*s13**2*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s23t4s2*s123t**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s12t4s2*s123t**(-1)
     &  + s12**(-1)*s23*s24*s124**(-2)*s14
     &  - 5.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s34
     &  - 7.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s13
     &  + s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  - 3.D0*s12**(-1)*s23*s24*s124**(-1)
     &  + 15.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s34*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s24*s124**(-1)*s14*s34**(-1)

      F40AFF = F40AFF + 3.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s14*
     & s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s14**2*s34**(-1)*
     & s134**(-1)
     &  + s12**(-1)*s23*s24*s124**(-1)*s13*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s24*s124**(-1)*s13*s134**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s23*s24*s234**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23*s24*s234**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s234**(-1)*s13*s34**(-1)
     &  - 5.D0/4.D0*s12**(-1)*s23*s24*s14**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s23*s24*s14**(-1)*s34*s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23*s24*s34**(-1)
     &  + 7.D0/2.D0*s12**(-1)*s23*s24*s134**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s23*s24*s14*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s13*s14**(-1)*s34**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s23*s24*s13*s14**(-1)*
     & s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23*s24*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24**2*s123**(-1)*s124**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s24**2*s123**(-1)*s234**(-1)
     &  - 7.D0/4.D0*s12**(-1)*s23*s24**2*s123**(-1)*s14**(-1)
     &  - 7.D0/2.D0*s12**(-1)*s23*s24**2*s123**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23*s24**2*s123**(-1)*s134**(-1)
     &  + s12**(-1)*s23*s24**2*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  + s12**(-1)*s23*s24**2*s124**(-2)
     &  + 1.D0/4.D0*s12**(-1)*s23*s24**2*s124**(-1)*s234**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23*s24**2*s124**(-1)*s234**(-1)*s13*
     & s34**(-1)
     &  + 3.D0*s12**(-1)*s23*s24**2*s124**(-1)*s34**(-1)
     &  - 7.D0/2.D0*s12**(-1)*s23*s24**2*s124**(-1)*s134**(-1)

      F40AFF = F40AFF - 1.D0/4.D0*s12**(-1)*s23*s24**2*s234**(-1)*
     & s34**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23*s24**2*s14**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23*s24**2*s34**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s23*s24**3*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s23*s24**3*s123**(-1)*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23*s24**3*s124**(-1)*s234**(-1)*
     & s34**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23*s24**3*s124**(-1)*s34**(-1)*
     & s134**(-1)
     &  + s12**(-1)*s23**2*s123**(-2)*s34
     &  + s12**(-1)*s23**2*s123**(-2)*s14
     &  - 1.D0/4.D0*s12**(-1)*s23**2*s123**(-2)*s13

      F40AFF = F40AFF - s12**(-1)*s23**2*s123**(-1)*s124**(-1)*s34
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s124**(-1)*s13
     &  - 5.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s234**(-1)*s34
     &  + 3.D0*s12**(-1)*s23**2*s123**(-1)*s234**(-1)*s14
     &  - 5.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s234**(-1)*s14**2*
     & s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s234**(-1)*s13*s14*
     & s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s14**(-1)*s34
     &  - 1.D0/12.D0*s12**(-1)*s23**2*s123**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s34*s134**(-1)
     &  - 9.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s14*s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s14*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s13*s14**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**(-1)*s23**2*s123**(-1)*s13*
     & s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s23t4s2*s123t**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s12t4s2*s123t**(-1)
     &  + 2.D0*s12**(-1)*s23**2*s124**(-2)*s14
     &  - 9.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s234**(-1)*s34
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s234**(-1)*s14
     &  - 7.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s234**(-1)*s13
     &  - 3.D0/4.D0*s12**(-1)*s23**2*s124**(-1)*s234**(-1)*s13**2*
     & s34**(-1)
     &  + 9.D0/4.D0*s12**(-1)*s23**2*s124**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**2*s124**(-1)*s34*s134**(-1)
     &  + 11.D0/4.D0*s12**(-1)*s23**2*s124**(-1)*s14*s34**(-1)
     &  - 17.D0/4.D0*s12**(-1)*s23**2*s124**(-1)*s14*s134**(-1)
     &  - 5.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s14**2*s34**(-1)*
     & s134**(-1)

      F40AFF = F40AFF + 1.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s13*
     & s134**(-1)
     &  - s12**(-1)*s23**2*s124**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**2*s124**(-1)*s13**2*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**2*s234**(-1)
     &  - 2.D0*s12**(-1)*s23**2*s234**(-1)*s14*s34**(-1)
     &  - s12**(-1)*s23**2*s234**(-1)*s13*s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**2*s14**(-1)
     &  - 15.D0/4.D0*s12**(-1)*s23**2*s34**(-1)
     &  + 4.D0*s12**(-1)*s23**2*s134**(-1)
     &  + 3.D0*s12**(-1)*s23**2*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s13*s14**(-1)*s134**(-1)
     &  + 2.D0*s12**(-1)*s23**2*s13*s34**(-1)*s134**(-1)
     &  + s12**(-1)*s23**2*s24*s123**(-2)

      F40AFF = F40AFF + 1.D0/2.D0*s12**(-1)*s23**2*s24*s123**(-1)*
     & s124**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**2*s24*s123**(-1)*s234**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**2*s24*s123**(-1)*s234**(-1)*s14*
     & s34**(-1)
     &  - s12**(-1)*s23**2*s24*s123**(-1)*s14**(-1)
     &  - 9.D0/4.D0*s12**(-1)*s23**2*s24*s123**(-1)*s34**(-1)
     &  + 2.D0*s12**(-1)*s23**2*s24*s123**(-1)*s134**(-1)
     &  - s12**(-1)*s23**2*s24*s124**(-1)*s234**(-1)
     &  + 11.D0/4.D0*s12**(-1)*s23**2*s24*s124**(-1)*s34**(-1)
     &  - 13.D0/4.D0*s12**(-1)*s23**2*s24*s124**(-1)*s134**(-1)
     &  - s12**(-1)*s23**2*s24*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23**2*s24*s234**(-1)*s34**(-1)
     &  + s12**(-1)*s23**2*s24*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s24*s34**(-1)*s134**(-1)

      F40AFF = F40AFF - 3.D0/2.D0*s12**(-1)*s23**2*s24**2*s123**(-1)*
     & s14**(-1)*s134**(-1)
     &  - 3.D0*s12**(-1)*s23**2*s24**2*s123**(-1)*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12**(-1)*s23**2*s24**2*s124**(-1)*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**3*s123**(-2)
     &  - 1.D0/2.D0*s12**(-1)*s23**3*s123**(-1)*s124**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23**3*s123**(-1)*s234**(-1)
     &  + 7.D0/4.D0*s12**(-1)*s23**3*s123**(-1)*s234**(-1)*s14*
     & s34**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**3*s123**(-1)*s234**(-1)*s13*
     & s34**(-1)
     &  - 3.D0/4.D0*s12**(-1)*s23**3*s123**(-1)*s14**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s23**3*s123**(-1)*s134**(-1)
     &  - 7.D0/4.D0*s12**(-1)*s23**3*s124**(-1)*s234**(-1)

      F40AFF = F40AFF - 3.D0/4.D0*s12**(-1)*s23**3*s124**(-1)*
     & s234**(-1)*s13*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**3*s124**(-1)*s34**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**3*s124**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s12**(-1)*s23**3*s124**(-1)*s14*s34**(-1)*
     & s134**(-1)
     &  + 3.D0/4.D0*s12**(-1)*s23**3*s124**(-1)*s13*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23**3*s234**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**3*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**3*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**3*s24*s123**(-1)*s234**(-1)*
     & s34**(-1)
     &  - s12**(-1)*s23**3*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 2.D0*s12**(-1)*s23**3*s24*s123**(-1)*s34**(-1)*s134**(-1)

      F40AFF = F40AFF + s12**(-1)*s23**3*s24*s124**(-1)*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**4*s123**(-1)*s234**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**4*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**4*s123**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**(-1)*s23**4*s124**(-1)*s234**(-1)*s34**(-1)
     &  - s23**(-2)*s123**(-2)*s13**2*s34**2
     &  - 2.D0*s23**(-2)*s123**(-2)*s13**2*s14*s34
     &  - s23**(-2)*s123**(-2)*s13**2*s14**2
     &  + 1.D0/2.D0*s23**(-2)*s123**(-2)*s13**3*s34
     &  + 1.D0/2.D0*s23**(-2)*s123**(-2)*s13**3*s14
     &  - s23**(-2)*s123**(-1)*s234**(-1)*s13*s14*s34**2
     &  - 2.D0*s23**(-2)*s123**(-1)*s234**(-1)*s13*s14**2*s34
     &  - s23**(-2)*s123**(-1)*s234**(-1)*s13**2*s14*s34
     &  + 2.D0*s23**(-2)*s123**(-1)*s13*s34**2

      F40AFF = F40AFF + 5.D0*s23**(-2)*s123**(-1)*s13*s14*s34
     &  + 4.D0*s23**(-2)*s123**(-1)*s13*s14**2
     &  - 7.D0/2.D0*s23**(-2)*s123**(-1)*s13**2*s34
     &  - 5.D0/2.D0*s23**(-2)*s123**(-1)*s13**2*s14
     &  + 1.D0/2.D0*s23**(-2)*s123**(-1)*s13**3
     &  + 1.D0/2.D0*s23**(-2)*s234**(-2)*s14*s34**3
     &  + s23**(-2)*s234**(-2)*s14**2*s34**2
     &  + 1.D0/2.D0*s23**(-2)*s234**(-2)*s13*s34**3
     &  + 2.D0*s23**(-2)*s234**(-2)*s13*s14*s34**2
     &  + s23**(-2)*s234**(-2)*s13**2*s34**2
     &  + 1.D0/2.D0*s23**(-2)*s234**(-1)*s34**3
     &  + 3.D0/2.D0*s23**(-2)*s234**(-1)*s14*s34**2
     &  + 1.D0/2.D0*s23**(-2)*s234**(-1)*s13*s34**2
     &  - 3.D0*s23**(-2)*s234**(-1)*s13*s14*s34
     &  - 2.D0*s23**(-2)*s234**(-1)*s13**2*s34

      F40AFF = F40AFF - 3.D0/2.D0*s23**(-2)*s34**2
     &  - 4.D0*s23**(-2)*s14*s34
     &  - 2.D0*s23**(-2)*s14**2
     &  + 2.D0*s23**(-2)*s13*s34
     &  + 4.D0*s23**(-2)*s13*s14
     &  + 1.D0/2.D0*s23**(-2)*s13**2
     &  - 2.D0*s23**(-2)*s24*s123**(-2)*s13**2*s34
     &  - 2.D0*s23**(-2)*s24*s123**(-2)*s13**2*s14
     &  + 1.D0/2.D0*s23**(-2)*s24*s123**(-2)*s13**3
     &  - s23**(-2)*s24*s123**(-1)*s234**(-1)*s13*s14*s34
     &  - 4.D0*s23**(-2)*s24*s123**(-1)*s234**(-1)*s13*s14**2
     &  + 2.D0*s23**(-2)*s24*s123**(-1)*s13*s34
     &  - 5.D0/2.D0*s23**(-2)*s24*s123**(-1)*s13**2
     &  + 1.D0/2.D0*s23**(-2)*s24*s234**(-2)*s14*s34**2
     &  + 1.D0/2.D0*s23**(-2)*s24*s234**(-2)*s13*s34**2

      F40AFF = F40AFF + 1.D0/2.D0*s23**(-2)*s24*s234**(-1)*s34**2
     &  + 4.D0*s23**(-2)*s24*s234**(-1)*s14**2
     &  - s23**(-2)*s24*s234**(-1)*s13*s34
     &  + 4.D0*s23**(-2)*s24*s14
     &  + 4.D0*s23**(-2)*s24*s13
     &  - s23**(-2)*s24**2*s123**(-2)*s13**2
     &  + 2.D0*s23**(-2)*s24**2*s234**(-2)*s14*s34
     &  + s23**(-2)*s24**2*s234**(-2)*s14**2
     &  + 2.D0*s23**(-2)*s24**2*s234**(-2)*s13*s34
     &  + 2.D0*s23**(-2)*s24**2*s234**(-2)*s13*s14
     &  + s23**(-2)*s24**2*s234**(-2)*s13**2
     &  + 2.D0*s23**(-2)*s24**2*s234**(-1)*s34
     &  + s23**(-2)*s24**2
     &  + 2.D0*s23**(-2)*s24**3*s234**(-2)*s14
     &  + 2.D0*s23**(-2)*s24**3*s234**(-2)*s13

      F40AFF = F40AFF + 2.D0*s23**(-2)*s24**3*s234**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13**2*s123t**2
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13**2*s34*s123t
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13**2*s14*s123t
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13**3*s123t
     &  - 1.D0/2.D0*s23**(-1)*s123**(-2)*s13*s34**2
     &  - s23**(-1)*s123**(-2)*s13*s14*s34
     &  - 1.D0/2.D0*s23**(-1)*s123**(-2)*s13*s14**2
     &  - 1.D0/4.D0*s23**(-1)*s123**(-2)*s13**2*s123t
     &  - 5.D0/6.D0*s23**(-1)*s123**(-2)*s13**2*s34
     &  - 5.D0/6.D0*s23**(-1)*s123**(-2)*s13**2*s14
     &  - 19.D0/12.D0*s23**(-1)*s123**(-2)*s13**3
     &  + 1.D0/4.D0*s23**(-1)*s123**(-2)*s23t4s2*s13**2
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2*s13**2*s34*s123t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2*s13**2*s14*s123t**(-1)

      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2*s13**3*
     & s123t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s123**(-2)*s23t4s2**2*s13**2*s123t**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s123**(-2)*s12t4s2*s23t4s2**(-1)*s13**2*
     & s123t
     &  - 1.D0/2.D0*s23**(-1)*s123**(-2)*s12t4s2*s23t4s2*s13**2*
     & s123t**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s34**3
     &  + 23.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s14*s34**2
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s124**(-1)*s14**2*s34
     &  + 7.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s14**3
     &  - 5.D0/2.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13*s14**(-1)*
     & s34**3
     &  + 11.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13*s34**2
     &  - 1.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13*s14*s34

      F40AFF = F40AFF - 3.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13**2*
     & s14**(-1)*s34**2
     &  + 5.D0/2.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13**2*s34
     &  - 3.D0/4.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13**2*s14
     &  - 2.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13**3*s14**(-1)*s34
     &  + s23**(-1)*s123**(-1)*s124**(-1)*s13**3
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s124**(-1)*s13**4*s14**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s34**3
     &  - 3.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s14*s34**2
     &  - 9.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s14**2*s34
     &  - 8.D0*s23**(-1)*s123**(-1)*s234**(-1)*s14**3
     &  + 1.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s13*s34**2
     &  - 3.D0*s23**(-1)*s123**(-1)*s234**(-1)*s13*s14*s34
     &  - 13.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s13*s14**2
     &  + 1.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s13**2*s34

      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*
     & s13**2*s14
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s234**(-1)*s13**3
     &  - 5.D0/2.D0*s23**(-1)*s123**(-1)*s14**(-1)*s34**3
     &  + 3.D0/4.D0*s23**(-1)*s123**(-1)*s14**(-1)*s34**4*s134**(-1)
     &  - 37.D0/4.D0*s23**(-1)*s123**(-1)*s34**2
     &  + 9.D0/4.D0*s23**(-1)*s123**(-1)*s34**3*s134**(-1)
     &  - 17.D0/2.D0*s23**(-1)*s123**(-1)*s14*s34
     &  + 3.D0*s23**(-1)*s123**(-1)*s14*s34**2*s134**(-1)
     &  - 21.D0/2.D0*s23**(-1)*s123**(-1)*s14**2
     &  + 9.D0/4.D0*s23**(-1)*s123**(-1)*s14**2*s34*s134**(-1)
     &  + 3.D0/2.D0*s23**(-1)*s123**(-1)*s14**3*s34**(-1)
     &  + 5.D0/4.D0*s23**(-1)*s123**(-1)*s14**3*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s123**(-1)*s14**4*s34**(-1)*s134**(-1)
     &  - 13.D0/4.D0*s23**(-1)*s123**(-1)*s13*s14**(-1)*s34**2

      F40AFF = F40AFF - 9.D0/4.D0*s23**(-1)*s123**(-1)*s13*s34
     &  - s23**(-1)*s123**(-1)*s13*s34**2*s134**(-1)
     &  - 13.D0/4.D0*s23**(-1)*s123**(-1)*s13*s14
     &  - 5.D0/4.D0*s23**(-1)*s123**(-1)*s13*s14*s34*s134**(-1)
     &  + 5.D0/4.D0*s23**(-1)*s123**(-1)*s13*s14**2*s34**(-1)
     &  - 5.D0/4.D0*s23**(-1)*s123**(-1)*s13*s14**2*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s13*s14**3*s34**(-1)*
     & s134**(-1)
     &  - 5.D0/2.D0*s23**(-1)*s123**(-1)*s13**2*s14**(-1)*s34
     &  + 1.D0/4.D0*s23**(-1)*s123**(-1)*s13**2*s34*s134**(-1)
     &  - s23**(-1)*s123**(-1)*s13**2*s14*s34**(-1)
     &  + 3.D0/4.D0*s23**(-1)*s123**(-1)*s13**2*s14*s134**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s123**(-1)*s13**3*s14**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s123**(-1)*s13**3*s14**(-1)*s34*
     & s134**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s23**(-1)*s123**(-1)*s13**3*
     & s134**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s123**(-1)*s13**4*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s14**(-1)*s34**4
     &  - 7.D0/4.D0*s23**(-1)*s124**(-1)*s234**(-1)*s34**3
     &  + 5.D0/4.D0*s23**(-1)*s124**(-1)*s234**(-1)*s14*s34**2
     &  - 5.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s14**2*s34
     &  + 3.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s14**3
     &  + 5.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13*s14**(-1)*
     & s34**3
     &  - 4.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13*s34**2
     &  + 2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13*s14*s34
     &  + 9.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13*s14**2
     &  + 9.D0/2.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13**2*s14**(-1)*
     & s34**2

      F40AFF = F40AFF - 3.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13**2*s34
     &  + 15.D0/4.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13**2*s14
     &  + 3.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13**3*s14**(-1)*s34
     &  - 9.D0/4.D0*s23**(-1)*s124**(-1)*s234**(-1)*s13**3
     &  + 2.D0*s23**(-1)*s124**(-1)*s14**(-1)*s34**3
     &  + 5.D0/4.D0*s23**(-1)*s124**(-1)*s34**2
     &  + 29.D0/4.D0*s23**(-1)*s124**(-1)*s14*s34
     &  + 1.D0/2.D0*s23**(-1)*s124**(-1)*s13*s14**(-1)*s34**2
     &  + 15.D0/4.D0*s23**(-1)*s124**(-1)*s13*s34
     &  + 27.D0/4.D0*s23**(-1)*s124**(-1)*s13*s14
     &  - 5.D0/2.D0*s23**(-1)*s124**(-1)*s13**2*s14**(-1)*s34
     &  + 5.D0/4.D0*s23**(-1)*s124**(-1)*s13**2
     &  - 5.D0/2.D0*s23**(-1)*s124**(-1)*s13**3*s14**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3**(-1)*s34**2*s234t**2
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3**(-1)*s34**3*s234t

      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3**(-1)*
     & s14*s34**2*s234t
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3**(-1)*s13*s34**2*s234t
     &  - 1.D0/4.D0*s23**(-1)*s234**(-2)*s34**2*s234t
     &  - 19.D0/12.D0*s23**(-1)*s234**(-2)*s34**3
     &  - 5.D0/6.D0*s23**(-1)*s234**(-2)*s14*s34**2
     &  + s23**(-1)*s234**(-2)*s14**2*s34
     &  - 5.D0/6.D0*s23**(-1)*s234**(-2)*s13*s34**2
     &  + 2.D0*s23**(-1)*s234**(-2)*s13*s14*s34
     &  + s23**(-1)*s234**(-2)*s13**2*s34
     &  + 1.D0/4.D0*s23**(-1)*s234**(-2)*s23t1s3*s34**2
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3*s34**3*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3*s14*s34**2*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3*s13*s34**2*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-2)*s23t1s3**2*s34**2*s234t**(-1)

      F40AFF = F40AFF - 1.D0/2.D0*s23**(-1)*s234**(-2)*s34t1s3*
     & s23t1s3**(-1)*s34**2*s234t
     &  - 1.D0/2.D0*s23**(-1)*s234**(-2)*s34t1s3*s23t1s3*s34**2*
     & s234t**(-1)
     &  - s23**(-1)*s234**(-1)*s23t1s3**(-1)*s34*s234t**2
     &  - 1.D0/2.D0*s23**(-1)*s234**(-1)*s14**(-1)*s34**3
     &  + s23**(-1)*s234**(-1)*s14**(-1)*s34**4*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s234**(-1)*s34*s234t
     &  - 31.D0/12.D0*s23**(-1)*s234**(-1)*s34**2
     &  + 9.D0/4.D0*s23**(-1)*s234**(-1)*s34**3*s134**(-1)
     &  - 1.D0/12.D0*s23**(-1)*s234**(-1)*s14*s34
     &  + 5.D0/4.D0*s23**(-1)*s234**(-1)*s14*s34**2*s134**(-1)
     &  - 21.D0/2.D0*s23**(-1)*s234**(-1)*s14**2
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s14**2*s34*s134**(-1)
     &  + 3.D0/2.D0*s23**(-1)*s234**(-1)*s14**3*s134**(-1)

      F40AFF = F40AFF + 13.D0/4.D0*s23**(-1)*s234**(-1)*s13*s14**(-1)*
     & s34**2
     &  + 1.D0/4.D0*s23**(-1)*s234**(-1)*s13*s14**(-1)*s34**3*
     & s134**(-1)
     &  - 10.D0/3.D0*s23**(-1)*s234**(-1)*s13*s34
     &  - 3.D0/4.D0*s23**(-1)*s234**(-1)*s13*s34**2*s134**(-1)
     &  - 57.D0/4.D0*s23**(-1)*s234**(-1)*s13*s14
     &  - 7.D0/4.D0*s23**(-1)*s234**(-1)*s13*s14*s34*s134**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s234**(-1)*s13*s14**2*s134**(-1)
     &  + 2.D0*s23**(-1)*s234**(-1)*s13**2*s14**(-1)*s34
     &  - 6.D0*s23**(-1)*s234**(-1)*s13**2
     &  + 1.D0/4.D0*s23**(-1)*s234**(-1)*s13**2*s34*s134**(-1)
     &  + 2.D0*s23**(-1)*s234**(-1)*s13**2*s14*s134**(-1)
     &  + 2.D0*s23**(-1)*s234**(-1)*s13**3*s14**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s234**(-1)*s13**3*s134**(-1)

      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s234**(-1)*s23t1s3*s34
     &  - 1.D0/2.D0*s23**(-1)*s234**(-1)*s23t1s3*s34**2*s234t**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s234**(-1)*s23t1s3*s14*s34*s234t**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s234**(-1)*s23t1s3*s13*s34*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s34t1s3*s34**2*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s34t1s3*s14*s34*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s34t1s3*s13*s34*s234t**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s14**(-1)*s34**2
     &  - 1.D0/4.D0*s23**(-1)*s14**(-1)*s34**3*s134**(-1)
     &  - 9.D0/2.D0*s23**(-1)*s34
     &  - 1.D0/4.D0*s23**(-1)*s34**2*s134**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s14
     &  + 35.D0/4.D0*s23**(-1)*s14**2*s34**(-1)
     &  + s23**(-1)*s14**2*s134**(-1)
     &  - 11.D0/4.D0*s23**(-1)*s13*s14**(-1)*s34

      F40AFF = F40AFF - 1.D0/4.D0*s23**(-1)*s13*s14**(-1)*s34**2*
     & s134**(-1)
     &  + 49.D0/12.D0*s23**(-1)*s13
     &  + 11.D0*s23**(-1)*s13*s14*s34**(-1)
     &  + 5.D0/4.D0*s23**(-1)*s13*s14*s134**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s13**2*s14**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s13**2*s14**(-1)*s34*s134**(-1)
     &  + 21.D0/4.D0*s23**(-1)*s13**2*s34**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s13**2*s14*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s23**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  - s23**(-1)*s23t4s2*s13*s123t**(-1)
     &  + s23**(-1)*s12t4s2*s13*s123t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24*s123**(-2)*s23t4s2**(-1)*s13**2*s123t
     &  - s23**(-1)*s24*s123**(-2)*s13*s34

      F40AFF = F40AFF - s23**(-1)*s24*s123**(-2)*s13*s14
     &  - 5.D0/6.D0*s23**(-1)*s24*s123**(-2)*s13**2
     &  + 1.D0/2.D0*s23**(-1)*s24*s123**(-2)*s23t4s2*s13**2*s123t**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34**3
     &  + 19.D0/2.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s34**2
     &  + 11.D0/2.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s14*s34
     &  + 2.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s14**2
     &  + 7.D0/4.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s13*s34
     &  + 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s13*s14
     &  + 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s124**(-1)*s13**2
     &  - 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s234**(-1)*s34**2
     &  - 4.D0*s23**(-1)*s24*s123**(-1)*s234**(-1)*s14*s34
     &  - 21.D0/2.D0*s23**(-1)*s24*s123**(-1)*s234**(-1)*s14**2
     &  + s23**(-1)*s24*s123**(-1)*s234**(-1)*s13*s34

      F40AFF = F40AFF - 6.D0*s23**(-1)*s24*s123**(-1)*s234**(-1)*s13*
     & s14
     &  - 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s234**(-1)*s13**2
     &  - 13.D0/2.D0*s23**(-1)*s24*s123**(-1)*s14**(-1)*s34**2
     &  + 11.D0/4.D0*s23**(-1)*s24*s123**(-1)*s14**(-1)*s34**3*
     & s134**(-1)
     &  - 75.D0/4.D0*s23**(-1)*s24*s123**(-1)*s34
     &  + 15.D0/2.D0*s23**(-1)*s24*s123**(-1)*s34**2*s134**(-1)
     &  - 18.D0*s23**(-1)*s24*s123**(-1)*s14
     &  + 9.D0*s23**(-1)*s24*s123**(-1)*s14*s34*s134**(-1)
     &  + 3.D0*s23**(-1)*s24*s123**(-1)*s14**2*s34**(-1)
     &  + 21.D0/4.D0*s23**(-1)*s24*s123**(-1)*s14**2*s134**(-1)
     &  + s23**(-1)*s24*s123**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13*s14**(-1)*s34
     &  - 6.D0*s23**(-1)*s24*s123**(-1)*s13

      F40AFF = F40AFF - 7.D0/4.D0*s23**(-1)*s24*s123**(-1)*s13*s34*
     & s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13*s14*s34**(-1)
     &  - 5.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13**2*s14**(-1)
     &  - 3.D0/4.D0*s23**(-1)*s24*s123**(-1)*s13**2*s14**(-1)*s34*
     & s134**(-1)
     &  - 5.D0/4.D0*s23**(-1)*s24*s123**(-1)*s13**2*s34**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24*s123**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s23**(-1)*s24*s123**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24*s123**(-1)*s13**3*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s14*s34
     &  - 5.D0/4.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s14**2
     &  - 3.D0/4.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s13*s34
     &  - 1.D0/2.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s13*s14
     &
      F40AFF = F40AFF + s23**(-1)*s24*s124**(-1)*s234**(-1)*s13**2*
     & s14**(-1)*s34
     &  + 7.D0/4.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s13**2
     &  + 1.D0/2.D0*s23**(-1)*s24*s124**(-1)*s234**(-1)*s13**3*
     & s14**(-1)
     &  + 5.D0/2.D0*s23**(-1)*s24*s124**(-1)*s14**(-1)*s34**2
     &  + 17.D0/4.D0*s23**(-1)*s24*s124**(-1)*s34
     &  + 1.D0/4.D0*s23**(-1)*s24*s124**(-1)*s14
     &  + 11.D0/4.D0*s23**(-1)*s24*s124**(-1)*s13*s14**(-1)*s34
     &  + 3.D0/2.D0*s23**(-1)*s24*s124**(-1)*s13
     &  + s23**(-1)*s24*s124**(-1)*s13**2*s14**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s23t1s3**(-1)*s34**2*s234t
     &  - 19.D0/12.D0*s23**(-1)*s24*s234**(-2)*s34**2
     &  + 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s14*s34
     &  - 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s14**2
     &
      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s13*s34
     &  - s23**(-1)*s24*s234**(-2)*s13*s14
     &  - 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s13**2
     &  + 1.D0/2.D0*s23**(-1)*s24*s234**(-2)*s23t1s3*s34**2*s234t**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s24*s234**(-1)*s14**(-1)*s34**2
     &  + 1.D0/4.D0*s23**(-1)*s24*s234**(-1)*s14**(-1)*s34**3*
     & s134**(-1)
     &  - 31.D0/12.D0*s23**(-1)*s24*s234**(-1)*s34
     &  - 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s34**2*s134**(-1)
     &  - 13.D0/4.D0*s23**(-1)*s24*s234**(-1)*s14
     &  - 5.D0/4.D0*s23**(-1)*s24*s234**(-1)*s14*s34*s134**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s24*s234**(-1)*s14**2*s134**(-1)
     &  + s23**(-1)*s24*s234**(-1)*s13*s14**(-1)*s34
     &  - 21.D0/4.D0*s23**(-1)*s24*s234**(-1)*s13
     &  - 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s13*s34*s134**(-1)
     &
      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s13*s14*
     & s134**(-1)
     &  - 3.D0/2.D0*s23**(-1)*s24*s234**(-1)*s13**2*s14**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24*s234**(-1)*s13**2*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s23t1s3*s34*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s34t1s3*s34*s234t**(-1)
     &  - 2.D0*s23**(-1)*s24*s23t1s3**(-1)*s34**(-1)*s234t**2
     &  - 15.D0/4.D0*s23**(-1)*s24*s14**(-1)*s34
     &  + 3.D0*s23**(-1)*s24*s14**(-1)*s34**2*s134**(-1)
     &  - s23**(-1)*s24*s34**(-1)*s234t
     &  + 29.D0/6.D0*s23**(-1)*s24
     &  + 15.D0/2.D0*s23**(-1)*s24*s34*s134**(-1)
     &  + 151.D0/12.D0*s23**(-1)*s24*s14*s34**(-1)
     &  + 11.D0/2.D0*s23**(-1)*s24*s14*s134**(-1)
     &  + 5.D0/4.D0*s23**(-1)*s24*s14**2*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF + 4.D0*s23**(-1)*s24*s13*s14**(-1)
     &  + s23**(-1)*s24*s13*s14**(-1)*s34*s134**(-1)
     &  + 37.D0/3.D0*s23**(-1)*s24*s13*s34**(-1)
     &  - 3.D0/2.D0*s23**(-1)*s24*s13*s134**(-1)
     &  - 7.D0/4.D0*s23**(-1)*s24*s13*s14*s34**(-1)*s134**(-1)
     &  + 9.D0/4.D0*s23**(-1)*s24*s13**2*s14**(-1)*s34**(-1)
     &  - 3.D0/2.D0*s23**(-1)*s24*s13**2*s14**(-1)*s134**(-1)
     &  - 9.D0/4.D0*s23**(-1)*s24*s13**2*s34**(-1)*s134**(-1)
     &  + s23**(-1)*s24*s23t1s3*s34**(-1)
     &  - s23**(-1)*s24*s23t1s3*s234t**(-1)
     &  - s23**(-1)*s24*s23t1s3*s14*s34**(-1)*s234t**(-1)
     &  - s23**(-1)*s24*s23t1s3*s13*s34**(-1)*s234t**(-1)
     &  + s23**(-1)*s24*s34t1s3*s234t**(-1)
     &  + s23**(-1)*s24*s34t1s3*s14*s34**(-1)*s234t**(-1)
     &  + s23**(-1)*s24*s34t1s3*s13*s34**(-1)*s234t**(-1)
     &
      F40AFF = F40AFF - 1.D0/2.D0*s23**(-1)*s24**2*s123**(-2)*s13
     &  + 15.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34**2
     &  + 35.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s124**(-1)*s34
     &  + 5.D0/2.D0*s23**(-1)*s24**2*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s124**(-1)*s13
     &  - 2.D0*s23**(-1)*s24**2*s123**(-1)*s234**(-1)*s34
     &  - 9.D0/2.D0*s23**(-1)*s24**2*s123**(-1)*s234**(-1)*s14
     &  - 2.D0*s23**(-1)*s24**2*s123**(-1)*s234**(-1)*s13
     &  - 13.D0/2.D0*s23**(-1)*s24**2*s123**(-1)*s14**(-1)*s34
     &  + 15.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s14**(-1)*s34**2*
     & s134**(-1)
     &  - 45.D0/4.D0*s23**(-1)*s24**2*s123**(-1)
     &  + 33.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s34*s134**(-1)
     &  + 3.D0/2.D0*s23**(-1)*s24**2*s123**(-1)*s14*s34**(-1)
     &
      F40AFF = F40AFF + 6.D0*s23**(-1)*s24**2*s123**(-1)*s14*s134**(-1)
     &  + 3.D0/2.D0*s23**(-1)*s24**2*s123**(-1)*s14**2*s34**(-1)*
     & s134**(-1)
     &  + 11.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s13*s14**(-1)
     &  + s23**(-1)*s24**2*s123**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s13*s34**(-1)
     &  - 5.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s13*s134**(-1)
     &  - 17.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s13**2*s14**(-1)*
     & s134**(-1)
     &  - 3.D0/4.D0*s23**(-1)*s24**2*s123**(-1)*s13**2*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s34
     &  + 3.D0/4.D0*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s14
     &  - 3.D0/4.D0*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s13*
     & s14**(-1)*s34
     &
      F40AFF = F40AFF - 2.D0*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s13
     &  + 1.D0/4.D0*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s13**2*
     & s14**(-1)
     &  + 9.D0/4.D0*s23**(-1)*s24**2*s124**(-1)*s14**(-1)*s34
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s124**(-1)
     &  + 3.D0/4.D0*s23**(-1)*s24**2*s124**(-1)*s13*s14**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3**(-1)*s234t**2
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3**(-1)*s34*s234t
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3**(-1)*s14*s234t
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3**(-1)*s13*s234t
     &  - 1.D0/4.D0*s23**(-1)*s24**2*s234**(-2)*s234t
     &  - 19.D0/12.D0*s23**(-1)*s24**2*s234**(-2)*s34
     &  + 2.D0/3.D0*s23**(-1)*s24**2*s234**(-2)*s14
     &  + 2.D0/3.D0*s23**(-1)*s24**2*s234**(-2)*s13
     &  + 1.D0/4.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3
     &
      F40AFF = F40AFF + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3*
     & s34*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3*s14*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3*s13*s234t**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s23t1s3**2*s234t**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s34t1s3*s23t1s3**(-1)*
     & s234t
     &  - 1.D0/2.D0*s23**(-1)*s24**2*s234**(-2)*s34t1s3*s23t1s3*
     & s234t**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s24**2*s234**(-1)*s14**(-1)*s34
     &  + 1.D0/4.D0*s23**(-1)*s24**2*s234**(-1)
     &  - 3.D0/4.D0*s23**(-1)*s24**2*s234**(-1)*s14*s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24**2*s234**(-1)*s13*s14**(-1)
     &  - 13.D0/4.D0*s23**(-1)*s24**2*s14**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s24**2*s14**(-1)*s34*s134**(-1)
     &
      F40AFF = F40AFF + 35.D0/6.D0*s23**(-1)*s24**2*s34**(-1)
     &  + 9.D0/2.D0*s23**(-1)*s24**2*s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24**2*s14*s34**(-1)*s134**(-1)
     &  + 9.D0/4.D0*s23**(-1)*s24**2*s13*s14**(-1)*s34**(-1)
     &  + 15.D0/4.D0*s23**(-1)*s24**2*s13*s14**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s23**(-1)*s24**2*s13*s34**(-1)*s134**(-1)
     &  - s23**(-1)*s24**2*s23t1s3*s34**(-1)*s234t**(-1)
     &  + s23**(-1)*s24**2*s34t1s3*s34**(-1)*s234t**(-1)
     &  + 11.D0/4.D0*s23**(-1)*s24**3*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34
     &  + 3.D0*s23**(-1)*s24**3*s123**(-1)*s124**(-1)
     &  - 2.D0*s23**(-1)*s24**3*s123**(-1)*s234**(-1)
     &  - 5.D0/2.D0*s23**(-1)*s24**3*s123**(-1)*s14**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s24**3*s123**(-1)*s14**(-1)*s34*
     & s134**(-1)
     &
      F40AFF = F40AFF + s23**(-1)*s24**3*s123**(-1)*s34**(-1)
     &  + 7.D0/4.D0*s23**(-1)*s24**3*s123**(-1)*s134**(-1)
     &  + 4.D0*s23**(-1)*s24**3*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24**3*s123**(-1)*s13*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24**3*s124**(-1)*s234**(-1)*s14**(-1)*
     & s34
     &  + s23**(-1)*s24**3*s124**(-1)*s234**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24**3*s124**(-1)*s234**(-1)*s13*
     & s14**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**3*s124**(-1)*s14**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24**3*s234**(-2)*s23t1s3**(-1)*s234t
     &  - 19.D0/12.D0*s23**(-1)*s24**3*s234**(-2)
     &  + 1.D0/2.D0*s23**(-1)*s24**3*s234**(-2)*s23t1s3*s234t**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24**3*s234**(-1)*s14**(-1)
     &
      F40AFF = F40AFF + 3.D0/4.D0*s23**(-1)*s24**3*s234**(-1)*
     & s134**(-1)
     &  - 5.D0/2.D0*s23**(-1)*s24**3*s14**(-1)*s134**(-1)
     &  - 3.D0/4.D0*s23**(-1)*s24**3*s34**(-1)*s134**(-1)
     &  + 3.D0/4.D0*s23**(-1)*s24**4*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 1.D0/4.D0*s23**(-1)*s24**4*s124**(-1)*s234**(-1)*s14**(-1)
     &  - 1.D0/4.D0*s23**(-1)*s24**4*s234**(-1)*s14**(-1)*s134**(-1)
     &  - s123**(-2)*s23t4s2**(-1)*s13*s123t**2
     &  + s123**(-2)*s23t4s2**(-1)*s13*s34*s123t
     &  + s123**(-2)*s23t4s2**(-1)*s13*s14*s123t
     &  + 3.D0/2.D0*s123**(-2)*s23t4s2**(-1)*s13**2*s123t
     &  + 3.D0*s123**(-2)*s34**2
     &  + 6.D0*s123**(-2)*s14*s34
     &  + 3.D0*s123**(-2)*s14**2
     &  - 1.D0/2.D0*s123**(-2)*s13*s123t
     &
      F40AFF = F40AFF - 1.D0/2.D0*s123**(-2)*s13*s34
     &  - 1.D0/2.D0*s123**(-2)*s13*s14
     &  - 13.D0/3.D0*s123**(-2)*s13**2
     &  + s123**(-2)*s23t4s2*s13*s34*s123t**(-1)
     &  + s123**(-2)*s23t4s2*s13*s14*s123t**(-1)
     &  + 3.D0/2.D0*s123**(-2)*s23t4s2*s13**2*s123t**(-1)
     &  - s123**(-2)*s12t4s2*s23t4s2**(-1)*s13*s123t
     &  - s123**(-2)*s12t4s2*s23t4s2*s13*s123t**(-1)
     &  - 5.D0/2.D0*s123**(-1)*s124**(-1)*s14**(-1)*s34**3
     &  + 1.D0/2.D0*s123**(-1)*s124**(-1)*s34**2
     &  - 19.D0/2.D0*s123**(-1)*s124**(-1)*s14*s34
     &  - 7.D0/4.D0*s123**(-1)*s124**(-1)*s14**2
     &  - 7.D0/2.D0*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34**2
     &  - 5.D0/4.D0*s123**(-1)*s124**(-1)*s13*s34
     &  - s123**(-1)*s124**(-1)*s13*s14
     &
      F40AFF = F40AFF - 7.D0/2.D0*s123**(-1)*s124**(-1)*s13**2*
     & s14**(-1)*s34
     &  + 5.D0/4.D0*s123**(-1)*s124**(-1)*s13**2
     &  - s123**(-1)*s124**(-1)*s13**3*s14**(-1)
     &  - s123**(-1)*s234**(-1)*s34**2
     &  + 1.D0/4.D0*s123**(-1)*s234**(-1)*s14*s34
     &  - 13.D0/2.D0*s123**(-1)*s234**(-1)*s14**2
     &  - 1.D0/4.D0*s123**(-1)*s234**(-1)*s14**3*s34**(-1)
     &  - 9.D0/4.D0*s123**(-1)*s234**(-1)*s13*s34
     &  - 1.D0/4.D0*s123**(-1)*s234**(-1)*s13*s14
     &  + 3.D0/2.D0*s123**(-1)*s234**(-1)*s13*s14**2*s34**(-1)
     &  + 2.D0*s123**(-1)*s234**(-1)*s13**2
     &  + 11.D0/4.D0*s123**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  + 5.D0/4.D0*s123**(-1)*s14**(-1)*s34**2
     &  - 3.D0/2.D0*s123**(-1)*s14**(-1)*s34**3*s134**(-1)
     &
      F40AFF = F40AFF + 11.D0*s123**(-1)*s34
     &  - 6.D0*s123**(-1)*s34**2*s134**(-1)
     &  + 3.D0*s123**(-1)*s14
     &  - 21.D0/2.D0*s123**(-1)*s14*s34*s134**(-1)
     &  + 9.D0/4.D0*s123**(-1)*s14**2*s34**(-1)
     &  - 31.D0/4.D0*s123**(-1)*s14**2*s134**(-1)
     &  - 5.D0/4.D0*s123**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  - s123**(-1)*s13*s14**(-1)*s34
     &  + 7.D0/4.D0*s123**(-1)*s13
     &  + 7.D0/4.D0*s123**(-1)*s13*s34*s134**(-1)
     &  - 7.D0/4.D0*s123**(-1)*s13*s14*s34**(-1)
     &  - 5.D0/4.D0*s123**(-1)*s13*s14*s134**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s13**2*s14**(-1)
     &  + 1.D0/4.D0*s123**(-1)*s13**2*s14**(-1)*s34*s134**(-1)
     &  - s123**(-1)*s13**2*s34**(-1)
     &
      F40AFF = F40AFF + 5.D0/2.D0*s123**(-1)*s13**2*s134**(-1)
     &  + 1.D0/2.D0*s123**(-1)*s13**2*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  + s123**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s124**(-2)*s34**2
     &  + 3.D0/4.D0*s124**(-2)*s14*s34
     &  - 1.D0/4.D0*s124**(-2)*s14**2
     &  + s124**(-2)*s13*s34
     &  + 3.D0/4.D0*s124**(-2)*s13*s14
     &  + 1.D0/2.D0*s124**(-2)*s13**2
     &  + 1.D0/4.D0*s124**(-1)*s234**(-1)*s14**(-1)*s34**3
     &  - 5.D0/4.D0*s124**(-1)*s234**(-1)*s34**2
     &  + 1.D0/2.D0*s124**(-1)*s234**(-1)*s14*s34
     &  - 9.D0/2.D0*s124**(-1)*s234**(-1)*s14**2
     &  - 1.D0/4.D0*s124**(-1)*s234**(-1)*s14**3*s34**(-1)
     &
      F40AFF = F40AFF + 7.D0/4.D0*s124**(-1)*s234**(-1)*s13*s14**(-1)*
     & s34**2
     &  - 17.D0/4.D0*s124**(-1)*s234**(-1)*s13*s34
     &  + s124**(-1)*s234**(-1)*s13*s14
     &  + 15.D0/4.D0*s124**(-1)*s234**(-1)*s13**2*s14**(-1)*s34
     &  - 3.D0/2.D0*s124**(-1)*s234**(-1)*s13**2
     &  + 3.D0/4.D0*s124**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  + 9.D0/4.D0*s124**(-1)*s234**(-1)*s13**3*s14**(-1)
     &  - 5.D0/4.D0*s124**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 3.D0/4.D0*s124**(-1)*s14**(-1)*s34**2
     &  + 13.D0/4.D0*s124**(-1)*s34
     &  - 1.D0/2.D0*s124**(-1)*s34**2*s134**(-1)
     &  - 11.D0/2.D0*s124**(-1)*s14
     &  - 3.D0*s124**(-1)*s14*s34*s134**(-1)
     &  + 7.D0/4.D0*s124**(-1)*s14**2*s34**(-1)
     &
      F40AFF = F40AFF - 23.D0/4.D0*s124**(-1)*s14**2*s134**(-1)
     &  - 3.D0*s124**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  + 13.D0/4.D0*s124**(-1)*s13*s14**(-1)*s34
     &  - 5.D0/2.D0*s124**(-1)*s13
     &  + 3.D0*s124**(-1)*s13*s34*s134**(-1)
     &  - 5.D0*s124**(-1)*s13*s14*s34**(-1)
     &  + 7.D0/4.D0*s124**(-1)*s13*s14*s134**(-1)
     &  - 3.D0/4.D0*s124**(-1)*s13*s14**2*s34**(-1)*s134**(-1)
     &  + 11.D0/4.D0*s124**(-1)*s13**2*s14**(-1)
     &  - 1.D0/2.D0*s124**(-1)*s13**2*s14**(-1)*s34*s134**(-1)
     &  - 5.D0/2.D0*s124**(-1)*s13**2*s34**(-1)
     &  + 3.D0/4.D0*s124**(-1)*s13**3*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s124**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  - 3.D0/4.D0*s124**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  - s234**(-2)*s23t1s3**(-1)*s34*s234t**2
     &
      F40AFF = F40AFF + 3.D0/2.D0*s234**(-2)*s23t1s3**(-1)*s34**2*s234t
     &  + s234**(-2)*s23t1s3**(-1)*s14*s34*s234t
     &  + s234**(-2)*s23t1s3**(-1)*s13*s34*s234t
     &  - 1.D0/2.D0*s234**(-2)*s34*s234t
     &  - 49.D0/12.D0*s234**(-2)*s34**2
     &  - 7.D0/4.D0*s234**(-2)*s14*s34
     &  + s234**(-2)*s14**2
     &  - 7.D0/4.D0*s234**(-2)*s13*s34
     &  + 2.D0*s234**(-2)*s13*s14
     &  + s234**(-2)*s13**2
     &  + 3.D0/2.D0*s234**(-2)*s23t1s3*s34**2*s234t**(-1)
     &  + s234**(-2)*s23t1s3*s14*s34*s234t**(-1)
     &  + s234**(-2)*s23t1s3*s13*s34*s234t**(-1)
     &  - s234**(-2)*s34t1s3*s23t1s3**(-1)*s34*s234t
     &  - s234**(-2)*s34t1s3*s23t1s3*s34*s234t**(-1)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s234**(-1)*s14**(-1)*s34**2
     &  + 7.D0/4.D0*s234**(-1)*s14**(-1)*s34**3*s134**(-1)
     &  - 7.D0/3.D0*s234**(-1)*s34
     &  + 11.D0/4.D0*s234**(-1)*s34**2*s134**(-1)
     &  + 17.D0/4.D0*s234**(-1)*s14
     &  - 5.D0/4.D0*s234**(-1)*s14*s34*s134**(-1)
     &  - 9.D0/4.D0*s234**(-1)*s14**2*s34**(-1)
     &  - 15.D0/4.D0*s234**(-1)*s14**2*s134**(-1)
     &  - 1.D0/2.D0*s234**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  + 7.D0/2.D0*s234**(-1)*s13*s14**(-1)*s34
     &  + 5.D0/4.D0*s234**(-1)*s13*s14**(-1)*s34**2*s134**(-1)
     &  - 1.D0/2.D0*s234**(-1)*s13
     &  - 7.D0/4.D0*s234**(-1)*s13*s34*s134**(-1)
     &  - 17.D0/4.D0*s234**(-1)*s13*s14*s34**(-1)
     &  - 13.D0/2.D0*s234**(-1)*s13*s14*s134**(-1)
     &
      F40AFF = F40AFF - 1.D0/2.D0*s234**(-1)*s13*s14**2*s34**(-1)*
     & s134**(-1)
     &  + 5.D0/4.D0*s234**(-1)*s13**2*s14**(-1)
     &  - 1.D0/4.D0*s234**(-1)*s13**2*s34**(-1)
     &  - 19.D0/4.D0*s234**(-1)*s13**2*s134**(-1)
     &  + s234**(-1)*s13**3*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s234**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s234**(-1)*s23t1s3*s34*s234t**(-1)
     &  + 1.D0/2.D0*s234**(-1)*s34t1s3*s34*s234t**(-1)
     &  + 1.D0/2.D0*s14**(-2)*s34**2
     &  + 13.D0/2.D0*s14**(-1)*s34
     &  - 7.D0/2.D0*s14**(-1)*s34**2*s134**(-1)
     &  - 1.D0/4.D0*s14**(-1)*s34**3*s134**(-2)
     &  - 7.D0*s34*s134**(-1)
     &  - 1.D0/4.D0*s34**2*s134**(-2)
     &
      F40AFF = F40AFF + 17.D0/2.D0*s14*s34**(-1)
     &  - 5.D0*s14*s134**(-1)
     &  - 1.D0/2.D0*s14**2*s34**(-2)
     &  + 1.D0/4.D0*s14**2*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s14**2*s134**(-2)
     &  + 1.D0/2.D0*s14**3*s34**(-2)*s134**(-1)
     &  - 1.D0/4.D0*s14**3*s34**(-1)*s134**(-2)
     &  + 1.D0/4.D0*s13*s14**(-1)
     &  - 11.D0/4.D0*s13*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/4.D0*s13*s14**(-1)*s34**2*s134**(-2)
     &  + 11.D0/2.D0*s13*s34**(-1)
     &  - 1.D0/4.D0*s13*s134**(-1)
     &  + 1.D0/2.D0*s13*s14**2*s34**(-2)*s134**(-1)
     &  - 1.D0/4.D0*s13*s14**2*s34**(-1)*s134**(-2)
     &  - s13**2*s14**(-2)
     &
      F40AFF = F40AFF + 1.D0/2.D0*s13**2*s14**(-2)*s34*s134**(-1)
     &  + 2.D0*s13**2*s14**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s13**2*s14**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s13**2*s14**(-1)*s34*s134**(-2)
     &  + 5.D0/2.D0*s13**2*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s13**2*s134**(-2)
     &  - 1.D0/4.D0*s13**2*s14*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s13**3*s14**(-2)*s134**(-1)
     &  - 1.D0/4.D0*s13**3*s14**(-1)*s134**(-2)
     &  - 1.D0/4.D0*s13**3*s34**(-1)*s134**(-2)
     &  + ((s14*s23-s13*s24)/s12/s34)**2
     &  + 1.D0/2.D0*s34t2s4*s14**(-1)*s34*s134**(-1)
     &  + 1.D0/2.D0*s34t2s4*s14*s34**(-1)*s134**(-1)
     &  + s34t2s4*s13*s14**(-1)*s34**(-1)
     &  + s24*s123**(-2)*s23t4s2**(-1)*s13*s123t
     &
      F40AFF = F40AFF + 6.D0*s24*s123**(-2)*s34
     &  + 6.D0*s24*s123**(-2)*s14
     &  - 1.D0/2.D0*s24*s123**(-2)*s13
     &  + s24*s123**(-2)*s23t4s2*s13*s123t**(-1)
     &  - 11.D0/4.D0*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  - 5.D0*s24*s123**(-1)*s124**(-1)*s34
     &  - 11.D0/2.D0*s24*s123**(-1)*s124**(-1)*s14
     &  + 5.D0/4.D0*s24*s123**(-1)*s124**(-1)*s13
     &  + 3.D0*s24*s123**(-1)*s234**(-1)*s34
     &  - 7.D0/4.D0*s24*s123**(-1)*s234**(-1)*s14
     &  - 15.D0/4.D0*s24*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - 7.D0/2.D0*s24*s123**(-1)*s234**(-1)*s13
     &  - 5.D0/4.D0*s24*s123**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &  + 3.D0/4.D0*s24*s123**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  + 19.D0/4.D0*s24*s123**(-1)*s14**(-1)*s34
     &
      F40AFF = F40AFF - 11.D0/4.D0*s24*s123**(-1)*s14**(-1)*s34**2*
     & s134**(-1)
     &  + 3.D0/2.D0*s24*s123**(-1)
     &  - 21.D0/2.D0*s24*s123**(-1)*s34*s134**(-1)
     &  - 17.D0/4.D0*s24*s123**(-1)*s14*s34**(-1)
     &  - 15.D0/4.D0*s24*s123**(-1)*s14*s134**(-1)
     &  + s24*s123**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  - 7.D0/4.D0*s24*s123**(-1)*s13*s14**(-1)
     &  - 3.D0/4.D0*s24*s123**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 2.D0*s24*s123**(-1)*s13*s34**(-1)
     &  - 3.D0*s24*s123**(-1)*s13*s134**(-1)
     &  - 3.D0/4.D0*s24*s123**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 2.D0*s24*s123**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  - 5.D0/2.D0*s24*s123**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + s24*s124**(-2)*s34
     &
      F40AFF = F40AFF + s24*s124**(-2)*s13
     &  - 1.D0/2.D0*s24*s124**(-1)*s234**(-1)*s14**(-1)*s34**2
     &  + 11.D0/4.D0*s24*s124**(-1)*s234**(-1)*s34
     &  - 1.D0/4.D0*s24*s124**(-1)*s234**(-1)*s14
     &  + 3.D0/4.D0*s24*s124**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - 3.D0*s24*s124**(-1)*s234**(-1)*s13*s14**(-1)*s34
     &  + s24*s124**(-1)*s234**(-1)*s13
     &  + s24*s124**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &  - 11.D0/4.D0*s24*s124**(-1)*s234**(-1)*s13**2*s14**(-1)
     &  + 13.D0/4.D0*s24*s124**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  - 9.D0/4.D0*s24*s124**(-1)*s234**(-1)*s13**3*s14**(-1)*
     & s34**(-1)
     &  - s24*s124**(-1)*s14**(-2)*s34**2
     &  - 11.D0/4.D0*s24*s124**(-1)*s14**(-1)*s34
     &  - 13.D0/4.D0*s24*s124**(-1)
     &
      F40AFF = F40AFF + 9.D0/4.D0*s24*s124**(-1)*s34*s134**(-1)
     &  + 3.D0/4.D0*s24*s124**(-1)*s14*s34**(-1)
     &  + s24*s124**(-1)*s14*s134**(-1)
     &  - 3.D0/2.D0*s24*s124**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  - s24*s124**(-1)*s13*s14**(-2)*s34
     &  - 3.D0/4.D0*s24*s124**(-1)*s13*s14**(-1)
     &  + 9.D0/4.D0*s24*s124**(-1)*s13*s34**(-1)
     &  + 2.D0*s24*s124**(-1)*s13*s134**(-1)
     &  - 11.D0/4.D0*s24*s124**(-1)*s13**2*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s24*s124**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  - s24*s234**(-2)*s23t1s3**(-1)*s234t**2
     &  + 2.D0*s24*s234**(-2)*s23t1s3**(-1)*s34*s234t
     &  + s24*s234**(-2)*s23t1s3**(-1)*s14*s234t
     &  + s24*s234**(-2)*s23t1s3**(-1)*s13*s234t
     &  - 1.D0/2.D0*s24*s234**(-2)*s234t
     &
      F40AFF = F40AFF - 5.D0*s24*s234**(-2)*s34
     &  - 5.D0/2.D0*s24*s234**(-2)*s14
     &  - 1.D0/2.D0*s24*s234**(-2)*s14**2*s34**(-1)
     &  - 5.D0/2.D0*s24*s234**(-2)*s13
     &  - s24*s234**(-2)*s13*s14*s34**(-1)
     &  - 1.D0/2.D0*s24*s234**(-2)*s13**2*s34**(-1)
     &  + 2.D0*s24*s234**(-2)*s23t1s3*s34*s234t**(-1)
     &  + s24*s234**(-2)*s23t1s3*s14*s234t**(-1)
     &  + s24*s234**(-2)*s23t1s3*s13*s234t**(-1)
     &  - s24*s234**(-2)*s34t1s3*s23t1s3**(-1)*s234t
     &  - s24*s234**(-2)*s34t1s3*s23t1s3*s234t**(-1)
     &  - 7.D0/4.D0*s24*s234**(-1)*s14**(-1)*s34
     &  + 1.D0/2.D0*s24*s234**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  + 3.D0/4.D0*s24*s234**(-1)
     &  + 7.D0/4.D0*s24*s234**(-1)*s34*s134**(-1)
     &
      F40AFF = F40AFF - 13.D0/4.D0*s24*s234**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s24*s234**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s24*s234**(-1)*s13*s14**(-1)
     &  + 1.D0/4.D0*s24*s234**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  - 7.D0/2.D0*s24*s234**(-1)*s13*s34**(-1)
     &  + 5.D0/4.D0*s24*s234**(-1)*s13*s134**(-1)
     &  + s24*s234**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  - 11.D0/4.D0*s24*s234**(-1)*s13**2*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s24*s234**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  - 2.D0*s24*s14**(-2)*s34
     &  + s24*s14**(-2)*s34**2*s134**(-1)
     &  + 3.D0*s24*s14**(-1)
     &  + 1.D0/4.D0*s24*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/2.D0*s24*s14**(-1)*s34**2*s134**(-2)
     &  + 97.D0/12.D0*s24*s34**(-1)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s24*s134**(-1)
     &  + 1.D0/4.D0*s24*s34*s134**(-2)
     &  - 3.D0/4.D0*s24*s14*s34**(-1)*s134**(-1)
     &  + 7.D0/4.D0*s24*s14*s134**(-2)
     &  + 1.D0/2.D0*s24*s14**2*s34**(-2)*s134**(-1)
     &  + 3.D0/2.D0*s24*s14**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s24*s14**3*s34**(-2)*s134**(-2)
     &  - s24*s13*s14**(-1)*s34**(-1)
     &  - 3.D0/2.D0*s24*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s24*s13*s14**(-1)*s34*s134**(-2)
     &  + 2.D0*s24*s13*s34**(-2)
     &  - 21.D0/4.D0*s24*s13*s34**(-1)*s134**(-1)
     &  + s24*s13*s134**(-2)
     &  - s24*s13*s14*s34**(-2)*s134**(-1)
     &  + 2.D0*s24*s13*s14*s34**(-1)*s134**(-2)
     &
      F40AFF = F40AFF + 1.D0/2.D0*s24*s13*s14**2*s34**(-2)*s134**(-2)
     &  - 3.D0/2.D0*s24*s13**2*s14**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s24*s13**2*s14**(-2)*s34*s134**(-2)
     &  - 2.D0*s24*s13**2*s34**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s24*s13**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s24*s13**3*s14**(-2)*s134**(-2)
     &  - s24*s23t1s3*s34**(-1)*s234t**(-1)
     &  + s24*s34t1s3*s34**(-1)*s234t**(-1)
     &  + 3.D0*s24**2*s123**(-2)
     &  - 9.D0/2.D0*s24**2*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  - 29.D0/4.D0*s24**2*s123**(-1)*s124**(-1)
     &  + s24**2*s123**(-1)*s234**(-1)
     &  - 1.D0/2.D0*s24**2*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 3.D0/2.D0*s24**2*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &  + 5.D0/2.D0*s24**2*s123**(-1)*s14**(-1)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s24**2*s123**(-1)*s14**(-1)*s34*
     & s134**(-1)
     &  - 17.D0/4.D0*s24**2*s123**(-1)*s34**(-1)
     &  - 3.D0*s24**2*s123**(-1)*s134**(-1)
     &  - 17.D0/4.D0*s24**2*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 7.D0/4.D0*s24**2*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s24**2*s124**(-2)*s14**(-2)*s34**2
     &  - 1.D0/2.D0*s24**2*s124**(-2)*s14**(-1)*s34
     &  - 1.D0/2.D0*s24**2*s124**(-2)
     &  + s24**2*s124**(-2)*s13*s14**(-2)*s34
     &  - 1.D0/2.D0*s24**2*s124**(-2)*s13*s14**(-1)
     &  + 1.D0/2.D0*s24**2*s124**(-2)*s13**2*s14**(-2)
     &  + 5.D0/4.D0*s24**2*s124**(-1)*s234**(-1)*s14**(-1)*s34
     &  + 3.D0/2.D0*s24**2*s124**(-1)*s234**(-1)
     &  + 3.D0/4.D0*s24**2*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &
      F40AFF = F40AFF + 3.D0/4.D0*s24**2*s124**(-1)*s234**(-1)*s13*
     & s14**(-1)
     &  - 3.D0*s24**2*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  + 9.D0/4.D0*s24**2*s124**(-1)*s234**(-1)*s13**2*s14**(-1)*
     & s34**(-1)
     &  + s24**2*s124**(-1)*s14**(-2)*s34
     &  - 11.D0/4.D0*s24**2*s124**(-1)*s14**(-1)
     &  - s24**2*s124**(-1)*s34**(-1)
     &  - 3.D0/2.D0*s24**2*s124**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s24**2*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &  + s24**2*s124**(-1)*s13*s14**(-2)
     &  + s24**2*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s24**2*s234**(-2)*s23t1s3**(-1)*s234t
     &  - 13.D0/3.D0*s24**2*s234**(-2)
     &  - 1.D0/2.D0*s24**2*s234**(-2)*s14*s34**(-1)
     &
      F40AFF = F40AFF - 1.D0/2.D0*s24**2*s234**(-2)*s13*s34**(-1)
     &  + 3.D0/2.D0*s24**2*s234**(-2)*s23t1s3*s234t**(-1)
     &  - s24**2*s234**(-1)*s14**(-1)
     &  - 1.D0/2.D0*s24**2*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 1.D0/4.D0*s24**2*s234**(-1)*s34**(-1)
     &  + 7.D0/4.D0*s24**2*s234**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s24**2*s234**(-1)*s14*s34**(-2)
     &  + 1.D0/2.D0*s24**2*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s24**2*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s24**2*s234**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s24**2*s234**(-1)*s13*s34**(-2)
     &  - 1.D0/2.D0*s24**2*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s24**2*s14**(-2)
     &  - s24**2*s14**(-2)*s34*s134**(-1)
     &  + 1.D0/2.D0*s24**2*s14**(-2)*s34**2*s134**(-2)
     &
      F40AFF = F40AFF - 1.D0/4.D0*s24**2*s14**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s24**2*s14**(-1)*s134**(-1)
     &  + s24**2*s14**(-1)*s34*s134**(-2)
     &  + 1.D0/2.D0*s24**2*s34**(-2)
     &  + 1.D0/4.D0*s24**2*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s24**2*s134**(-2)
     &  - 2.D0*s24**2*s14*s34**(-2)*s134**(-1)
     &  + 2.D0*s24**2*s14*s34**(-1)*s134**(-2)
     &  + s24**2*s14**2*s34**(-2)*s134**(-2)
     &  - 1.D0/2.D0*s24**2*s13**2*s14**(-2)*s134**(-2)
     &  - s24**2*s13**2*s34**(-2)*s134**(-2)
     &  - 7.D0/4.D0*s24**3*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 1.D0/2.D0*s24**3*s123**(-1)*s234**(-1)*s34**(-1)
     &  + 5.D0/4.D0*s24**3*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 7.D0/4.D0*s24**3*s123**(-1)*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - 1.D0/4.D0*s24**3*s124**(-2)*s14**(-1)
     &  + 3.D0/4.D0*s24**3*s124**(-1)*s234**(-1)*s14**(-1)
     &  + 2.D0*s24**3*s124**(-1)*s234**(-1)*s34**(-1)
     &  - 5.D0/4.D0*s24**3*s124**(-1)*s234**(-1)*s13*s14**(-1)*
     & s34**(-1)
     &  - 1.D0/2.D0*s24**3*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s24**3*s234**(-2)*s34**(-1)
     &  + 1.D0/2.D0*s24**3*s234**(-2)*s14*s34**(-2)
     &  + 1.D0/2.D0*s24**3*s234**(-2)*s13*s34**(-2)
     &  - 1.D0/4.D0*s24**3*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 5.D0/4.D0*s24**3*s234**(-1)*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s24**3*s234**(-1)*s34**(-2)
     &  - 1.D0/2.D0*s24**3*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s24**4*s124**(-1)*s234**(-1)*s14**(-1)*s34**(-1)
     &  + s23*s123**(-2)*s23t4s2**(-1)*s13*s123t
     &
      F40AFF = F40AFF + 13.D0/4.D0*s23*s123**(-2)*s34
     &  + 13.D0/4.D0*s23*s123**(-2)*s14
     &  - 5.D0/2.D0*s23*s123**(-2)*s13
     &  + s23*s123**(-2)*s23t4s2*s13*s123t**(-1)
     &  - 1.D0/2.D0*s23*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  - 3.D0/4.D0*s23*s123**(-1)*s124**(-1)*s34
     &  + 9.D0/4.D0*s23*s123**(-1)*s124**(-1)*s14
     &  - 9.D0/4.D0*s23*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34
     &  + 1.D0/2.D0*s23*s123**(-1)*s124**(-1)*s13
     &  - 3.D0/4.D0*s23*s123**(-1)*s124**(-1)*s13**2*s14**(-1)
     &  - 7.D0/4.D0*s23*s123**(-1)*s234**(-1)*s34
     &  + 9.D0/2.D0*s23*s123**(-1)*s234**(-1)*s14
     &  - 7.D0/4.D0*s23*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - 3.D0/2.D0*s23*s123**(-1)*s234**(-1)*s13
     &  + 5.D0/2.D0*s23*s123**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &
      F40AFF = F40AFF - 1.D0/4.D0*s23*s123**(-1)*s234**(-1)*s13**2*
     & s34**(-1)
     &  - 13.D0/4.D0*s23*s123**(-1)*s14**(-1)*s34
     &  + 3.D0/4.D0*s23*s123**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  - 7.D0/3.D0*s23*s123**(-1)
     &  + 3.D0/2.D0*s23*s123**(-1)*s34*s134**(-1)
     &  - 7.D0/2.D0*s23*s123**(-1)*s14*s34**(-1)
     &  + 3.D0/2.D0*s23*s123**(-1)*s14*s134**(-1)
     &  + 3.D0/4.D0*s23*s123**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s23*s123**(-1)*s13*s14**(-1)
     &  + s23*s123**(-1)*s13*s34**(-1)
     &  + 1.D0/4.D0*s23*s123**(-1)*s13*s134**(-1)
     &  + 1.D0/4.D0*s23*s123**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s23*s123**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23*s123**(-1)*s23t4s2*s123t**(-1)
     &
      F40AFF = F40AFF + 1.D0/2.D0*s23*s123**(-1)*s12t4s2*s123t**(-1)
     &  + s23*s124**(-2)*s34
     &  + 3.D0/4.D0*s23*s124**(-2)*s14
     &  + s23*s124**(-2)*s13
     &  - 1.D0/4.D0*s23*s124**(-1)*s234**(-1)*s14**(-1)*s34**2
     &  + 3.D0/2.D0*s23*s124**(-1)*s234**(-1)*s34
     &  + 3.D0/2.D0*s23*s124**(-1)*s234**(-1)*s14
     &  - 3.D0/4.D0*s23*s124**(-1)*s234**(-1)*s13*s14**(-1)*s34
     &  - 1.D0/2.D0*s23*s124**(-1)*s234**(-1)*s13
     &  - 3.D0/4.D0*s23*s124**(-1)*s234**(-1)*s13**2*s14**(-1)
     &  - 3.D0/4.D0*s23*s124**(-1)*s234**(-1)*s13**3*s14**(-1)*
     & s34**(-1)
     &  + 11.D0/4.D0*s23*s124**(-1)*s14**(-1)*s34
     &  - 2.D0*s23*s124**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  - 3.D0/4.D0*s23*s124**(-1)
     &
      F40AFF = F40AFF + 3.D0/2.D0*s23*s124**(-1)*s34*s134**(-1)
     &  - 31.D0/4.D0*s23*s124**(-1)*s14*s34**(-1)
     &  + 6.D0*s23*s124**(-1)*s14*s134**(-1)
     &  + 25.D0/4.D0*s23*s124**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s23*s124**(-1)*s13*s14**(-1)
     &  - s23*s124**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 1.D0/4.D0*s23*s124**(-1)*s13*s34**(-1)
     &  + 3.D0/2.D0*s23*s124**(-1)*s13*s134**(-1)
     &  + 3.D0/2.D0*s23*s124**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + s23*s124**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s23*s124**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + s23*s234**(-2)*s23t1s3**(-1)*s34*s234t
     &  - 5.D0/2.D0*s23*s234**(-2)*s34
     &  + 1.D0/4.D0*s23*s234**(-2)*s14
     &  + 1.D0/4.D0*s23*s234**(-2)*s13
     &
      F40AFF = F40AFF + s23*s234**(-2)*s23t1s3*s34*s234t**(-1)
     &  - s23*s234**(-1)*s23t1s3**(-1)*s34**(-1)*s234t**2
     &  - 5.D0/2.D0*s23*s234**(-1)*s14**(-1)*s34
     &  + 11.D0/4.D0*s23*s234**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)*s34**(-1)*s234t
     &  - 11.D0/6.D0*s23*s234**(-1)
     &  + 4.D0*s23*s234**(-1)*s34*s134**(-1)
     &  - 19.D0/12.D0*s23*s234**(-1)*s14*s34**(-1)
     &  + 3.D0/4.D0*s23*s234**(-1)*s14*s134**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s23*s234**(-1)*s13*s14**(-1)
     &  + 3.D0/2.D0*s23*s234**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 2.D0/3.D0*s23*s234**(-1)*s13*s34**(-1)
     &  + 5.D0/2.D0*s23*s234**(-1)*s13*s134**(-1)
     &  + 1.D0/4.D0*s23*s234**(-1)*s13**2*s14**(-1)*s34**(-1)
     &
      F40AFF = F40AFF + 3.D0/4.D0*s23*s234**(-1)*s13**2*s14**(-1)*
     & s134**(-1)
     &  + 1.D0/2.D0*s23*s234**(-1)*s23t1s3*s34**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)*s23t1s3*s234t**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)*s23t1s3*s14*s34**(-1)*s234t**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)*s23t1s3*s13*s34**(-1)*s234t**(-1)
     &  + 1.D0/2.D0*s23*s234**(-1)*s34t1s3*s234t**(-1)
     &  + 1.D0/2.D0*s23*s234**(-1)*s34t1s3*s14*s34**(-1)*s234t**(-1)
     &  + 1.D0/2.D0*s23*s234**(-1)*s34t1s3*s13*s34**(-1)*s234t**(-1)
     &  + s23*s14**(-2)*s34**2*s134**(-1)
     &  + 19.D0/4.D0*s23*s14**(-1)
     &  + 1.D0/2.D0*s23*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/2.D0*s23*s14**(-1)*s34**2*s134**(-2)
     &  + 7.D0/2.D0*s23*s34**(-1)
     &  + 2.D0*s23*s134**(-1)
     &
      F40AFF = F40AFF + 1.D0/4.D0*s23*s34*s134**(-2)
     &  - 2.D0*s23*s14*s34**(-2)
     &  - s23*s14*s34**(-1)*s134**(-1)
     &  + 7.D0/4.D0*s23*s14*s134**(-2)
     &  + 3.D0/2.D0*s23*s14**2*s34**(-2)*s134**(-1)
     &  + 3.D0/2.D0*s23*s14**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s23*s14**3*s34**(-2)*s134**(-2)
     &  - 1.D0/4.D0*s23*s13*s14**(-1)*s34**(-1)
     &  - 2.D0*s23*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23*s13*s14**(-1)*s34*s134**(-2)
     &  + 2.D0*s23*s13*s34**(-2)
     &  - 5.D0/4.D0*s23*s13*s34**(-1)*s134**(-1)
     &  + s23*s13*s134**(-2)
     &  + 2.D0*s23*s13*s14*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s23*s13*s14**2*s34**(-2)*s134**(-2)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s23*s13**2*s14**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s23*s13**2*s14**(-2)*s34*s134**(-2)
     &  - 2.D0*s23*s13**2*s34**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s23*s13**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s23*s13**3*s14**(-2)*s134**(-2)
     &  + 13.D0/4.D0*s23*s24*s123**(-2)
     &  + 3.D0*s23*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + 13.D0/2.D0*s23*s24*s123**(-1)*s124**(-1)
     &  + 3.D0/4.D0*s23*s24*s123**(-1)*s234**(-1)
     &  + 9.D0/4.D0*s23*s24*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 1.D0/4.D0*s23*s24*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 15.D0/4.D0*s23*s24*s123**(-1)*s14**(-1)
     &  + s23*s24*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &  - s23*s24*s123**(-1)*s34**(-1)
     &  + 7.D0/4.D0*s23*s24*s123**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - s23*s24*s123**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23*s24*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s23*s24*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  + s23*s24*s124**(-2)
     &  - 1.D0/4.D0*s23*s24*s124**(-1)*s234**(-1)*s14**(-1)*s34
     &  + 7.D0/4.D0*s23*s24*s124**(-1)*s234**(-1)
     &  - 1.D0/4.D0*s23*s24*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 3.D0/4.D0*s23*s24*s124**(-1)*s234**(-1)*s13*s14**(-1)
     &  - 3.D0/4.D0*s23*s24*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 2.D0*s23*s24*s124**(-1)*s14**(-2)*s34
     &  + 1.D0/2.D0*s23*s24*s124**(-1)*s14**(-1)
     &  - 2.D0*s23*s24*s124**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 3.D0/2.D0*s23*s24*s124**(-1)*s34**(-1)
     &  - 7.D0*s23*s24*s124**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23*s24*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - 5.D0/4.D0*s23*s24*s124**(-1)*s13*s14**(-1)*
     & s34**(-1)
     &  - s23*s24*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  + s23*s24*s234**(-2)*s23t1s3**(-1)*s234t
     &  - 5.D0/2.D0*s23*s24*s234**(-2)
     &  - s23*s24*s234**(-2)*s14*s34**(-1)
     &  - s23*s24*s234**(-2)*s13*s34**(-1)
     &  + s23*s24*s234**(-2)*s23t1s3*s234t**(-1)
     &  - 11.D0/4.D0*s23*s24*s234**(-1)*s14**(-1)
     &  + 7.D0/4.D0*s23*s24*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  - 4.D0/3.D0*s23*s24*s234**(-1)*s34**(-1)
     &  + 9.D0/2.D0*s23*s24*s234**(-1)*s134**(-1)
     &  - s23*s24*s234**(-1)*s14*s34**(-2)
     &  + s23*s24*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s23*s24*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - 1.D0/2.D0*s23*s24*s234**(-1)*s23t1s3*s34**(-1)*
     & s234t**(-1)
     &  + 1.D0/2.D0*s23*s24*s234**(-1)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - 2.D0*s23*s24*s14**(-2)*s34*s134**(-1)
     &  + s23*s24*s14**(-2)*s34**2*s134**(-2)
     &  - s23*s24*s14**(-1)*s34**(-1)
     &  + 3.D0*s23*s24*s14**(-1)*s134**(-1)
     &  + 2.D0*s23*s24*s14**(-1)*s34*s134**(-2)
     &  + 5.D0/4.D0*s23*s24*s34**(-1)*s134**(-1)
     &  + 3.D0*s23*s24*s134**(-2)
     &  - 2.D0*s23*s24*s14*s34**(-2)*s134**(-1)
     &  + 4.D0*s23*s24*s14*s34**(-1)*s134**(-2)
     &  + 2.D0*s23*s24*s14**2*s34**(-2)*s134**(-2)
     &  + 2.D0*s23*s24*s13*s34**(-2)*s134**(-1)
     &  - s23*s24*s13**2*s14**(-2)*s134**(-2)
     &
      F40AFF = F40AFF - 2.D0*s23*s24*s13**2*s34**(-2)*s134**(-2)
     &  + 9.D0/4.D0*s23*s24**2*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 3.D0*s23*s24**2*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 15.D0/4.D0*s23*s24**2*s123**(-1)*s34**(-1)*s134**(-1)
     &  + s23*s24**2*s124**(-2)*s14**(-2)*s34
     &  - 1.D0/2.D0*s23*s24**2*s124**(-2)*s14**(-1)
     &  + s23*s24**2*s124**(-2)*s13*s14**(-2)
     &  + 1.D0/4.D0*s23*s24**2*s124**(-1)*s234**(-1)*s14**(-1)
     &  + 1.D0/4.D0*s23*s24**2*s124**(-1)*s234**(-1)*s34**(-1)
     &  + s23*s24**2*s124**(-1)*s14**(-2)
     &  + s23*s24**2*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 2.D0*s23*s24**2*s124**(-1)*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23*s24**2*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23*s24**2*s234**(-2)*s34**(-1)
     &  + 1.D0/2.D0*s23*s24**2*s234**(-2)*s14*s34**(-2)
     &
      F40AFF = F40AFF + 1.D0/2.D0*s23*s24**2*s234**(-2)*s13*s34**(-2)
     &  + 1.D0/4.D0*s23*s24**2*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 7.D0/4.D0*s23*s24**2*s234**(-1)*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23*s24**2*s234**(-1)*s34**(-2)
     &  - 1.D0/2.D0*s23*s24**2*s234**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23**2*s123**(-2)
     &  - 3.D0/4.D0*s23**2*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  - 7.D0/4.D0*s23**2*s123**(-1)*s124**(-1)
     &  - 11.D0/4.D0*s23**2*s123**(-1)*s234**(-1)
     &  + 5.D0/2.D0*s23**2*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 7.D0/4.D0*s23**2*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &  - s23**2*s123**(-1)*s14**(-1)
     &  - 1.D0/2.D0*s23**2*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &  + s23**2*s123**(-1)*s34**(-1)
     &  + 5.D0/4.D0*s23**2*s123**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - s23**2*s123**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23**2*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**2*s124**(-2)
     &  + 2.D0*s23**2*s124**(-1)*s234**(-1)
     &  + 3.D0/4.D0*s23**2*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  + 7.D0/4.D0*s23**2*s124**(-1)*s14**(-1)
     &  - 2.D0*s23**2*s124**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 19.D0/4.D0*s23**2*s124**(-1)*s34**(-1)
     &  - 7.D0*s23**2*s124**(-1)*s134**(-1)
     &  - 23.D0/4.D0*s23**2*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &  - s23**2*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 7.D0/4.D0*s23**2*s124**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23**2*s234**(-2)
     &  - 1.D0/2.D0*s23**2*s234**(-2)*s14*s34**(-1)
     &  - 1.D0/2.D0*s23**2*s234**(-2)*s13*s34**(-1)
     &
      F40AFF = F40AFF - 5.D0/2.D0*s23**2*s234**(-1)*s14**(-1)
     &  + 2.D0*s23**2*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/3.D0*s23**2*s234**(-1)*s34**(-1)
     &  + 9.D0/4.D0*s23**2*s234**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**2*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/4.D0*s23**2*s234**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23**2*s234**(-1)*s23t1s3*s34**(-1)*s234t**(-1)
     &  + 1.D0/2.D0*s23**2*s234**(-1)*s34t1s3*s34**(-1)*s234t**(-1)
     &  + 1.D0/2.D0*s23**2*s14**(-2)*s34**2*s134**(-2)
     &  - 1.D0/2.D0*s23**2*s14**(-1)*s34**(-1)
     &  + 13.D0/4.D0*s23**2*s14**(-1)*s134**(-1)
     &  + s23**2*s14**(-1)*s34*s134**(-2)
     &  - s23**2*s34**(-2)
     &  + 13.D0/4.D0*s23**2*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s23**2*s134**(-2)
     &
      F40AFF = F40AFF + 2.D0*s23**2*s14*s34**(-1)*s134**(-2)
     &  + s23**2*s14**2*s34**(-2)*s134**(-2)
     &  + 2.D0*s23**2*s13*s34**(-2)*s134**(-1)
     &  - 1.D0/2.D0*s23**2*s13**2*s14**(-2)*s134**(-2)
     &  - s23**2*s13**2*s34**(-2)*s134**(-2)
     &  - s23**2*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 3.D0/2.D0*s23**2*s24*s123**(-1)*s234**(-1)*s34**(-1)
     &  - 13.D0/4.D0*s23**2*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 13.D0/4.D0*s23**2*s24*s123**(-1)*s34**(-1)*s134**(-1)
     &  - s23**2*s24*s124**(-1)*s14**(-2)*s34*s134**(-1)
     &  + s23**2*s24*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 3.D0*s23**2*s24*s124**(-1)*s14**(-1)*s134**(-1)
     &  - s23**2*s24*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23**2*s24*s234**(-2)*s34**(-1)
     &  - 1.D0/2.D0*s23**2*s24*s234**(-1)*s14**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - 3.D0/4.D0*s23**2*s24*s234**(-1)*s14**(-1)*
     & s134**(-1)
     &  + 1.D0/2.D0*s23**2*s24**2*s124**(-2)*s14**(-2)
     &  + 1.D0/4.D0*s23**3*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 2.D0*s23**3*s123**(-1)*s234**(-1)*s34**(-1)
     &  - 7.D0/4.D0*s23**3*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s23**3*s123**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**3*s124**(-1)*s234**(-1)*s34**(-1)
     &  + s23**3*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s23**3*s234**(-2)*s34**(-1)
     &  - 1.D0/2.D0*s23**3*s234**(-1)*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12*s23**(-2)*s123**(-2)*s13**2*s34
     &  + 1.D0/2.D0*s12*s23**(-2)*s123**(-2)*s13**2*s14
     &  - s12*s23**(-2)*s123**(-1)*s234**(-1)*s13*s14*s34
     &  - s12*s23**(-2)*s123**(-1)*s13*s34
     &
      F40AFF = F40AFF + 1.D0/2.D0*s12*s23**(-2)*s123**(-1)*s13**2
     &  + 1.D0/2.D0*s12*s23**(-2)*s234**(-2)*s34**3
     &  + 2.D0*s12*s23**(-2)*s234**(-2)*s14*s34**2
     &  + 2.D0*s12*s23**(-2)*s234**(-2)*s13*s34**2
     &  + 3.D0/2.D0*s12*s23**(-2)*s234**(-1)*s34**2
     &  - 2.D0*s12*s23**(-2)*s234**(-1)*s13*s34
     &  - 4.D0*s12*s23**(-2)*s34
     &  - 4.D0*s12*s23**(-2)*s14
     &  + 1.D0/2.D0*s12*s23**(-2)*s24*s123**(-2)*s13**2
     &  - 4.D0*s12*s23**(-2)*s24*s123**(-1)*s234**(-1)*s14*s34
     &  - 6.D0*s12*s23**(-2)*s24*s123**(-1)*s234**(-1)*s14**2
     &  - 4.D0*s12*s23**(-2)*s24*s123**(-1)*s234**(-1)*s13*s14
     &  - 6.D0*s12*s23**(-2)*s24*s123**(-1)*s34
     &  - 8.D0*s12*s23**(-2)*s24*s123**(-1)*s14
     &  - 4.D0*s12*s23**(-2)*s24*s123**(-1)*s13
     &
      F40AFF = F40AFF + 1.D0/2.D0*s12*s23**(-2)*s24*s234**(-2)*s34**2
     &  - 4.D0*s12*s23**(-2)*s24*s234**(-1)*s34
     &  - 2.D0*s12*s23**(-2)*s24*s234**(-1)*s13
     &  - 4.D0*s12*s23**(-2)*s24**2*s123**(-1)*s234**(-1)*s14
     &  - 6.D0*s12*s23**(-2)*s24**2*s123**(-1)
     &  + 2.D0*s12*s23**(-2)*s24**2*s234**(-2)*s34
     &  + 2.D0*s12*s23**(-2)*s24**2*s234**(-2)*s14
     &  + 2.D0*s12*s23**(-2)*s24**2*s234**(-2)*s13
     &  - 4.D0*s12*s23**(-2)*s24**2*s234**(-1)
     &  + 2.D0*s12*s23**(-2)*s24**3*s234**(-2)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13**2*s123t
     &  + 5.D0*s12*s23**(-1)*s123**(-2)*s34**2
     &  + 10.D0*s12*s23**(-1)*s123**(-2)*s14*s34
     &  + 5.D0*s12*s23**(-1)*s123**(-2)*s14**2
     &  + 7.D0/2.D0*s12*s23**(-1)*s123**(-2)*s13*s34
     &
      F40AFF = F40AFF + 7.D0/2.D0*s12*s23**(-1)*s123**(-2)*s13*s14
     &  - 19.D0/12.D0*s12*s23**(-1)*s123**(-2)*s13**2
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-2)*s23t4s2*s13**2*s123t**(-1)
     &  - 5.D0/4.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34**3
     &  + 21.D0/4.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s34**2
     &  - 29.D0/4.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s14*s34
     &  + 7.D0/4.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s14**2
     &  + s12*s23**(-1)*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34**2
     &  - 3.D0/4.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s13*s34
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s124**(-1)*s13*s14
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s234**(-1)*s34**2
     &  - s12*s23**(-1)*s123**(-1)*s234**(-1)*s14*s34
     &  - 9.D0/2.D0*s12*s23**(-1)*s123**(-1)*s234**(-1)*s14**2
     &  + s12*s23**(-1)*s123**(-1)*s234**(-1)*s13*s34
     &
      F40AFF = F40AFF - s12*s23**(-1)*s123**(-1)*s234**(-1)*s13*s14
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s234**(-1)*s13**2
     &  - s12*s23**(-1)*s123**(-1)*s23t4s2**(-1)*s123t**2
     &  - 9.D0/4.D0*s12*s23**(-1)*s123**(-1)*s14**(-1)*s34**2
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s123t
     &  + 49.D0/6.D0*s12*s23**(-1)*s123**(-1)*s34
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s34**2*s134**(-1)
     &  + 5.D0/12.D0*s12*s23**(-1)*s123**(-1)*s14
     &  - 3.D0/2.D0*s12*s23**(-1)*s123**(-1)*s14*s34*s134**(-1)
     &  - 5.D0/4.D0*s12*s23**(-1)*s123**(-1)*s14**2*s34**(-1)
     &  - 5.D0/2.D0*s12*s23**(-1)*s123**(-1)*s14**2*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s14**3*s34**(-1)*
     & s134**(-1)
     &  + s12*s23**(-1)*s123**(-1)*s13*s14**(-1)*s34
     &  - 1.D0/12.D0*s12*s23**(-1)*s123**(-1)*s13
     &
      F40AFF = F40AFF - 2.D0*s12*s23**(-1)*s123**(-1)*s13*s14*s34**(-1)
     &  + 1.D0/4.D0*s12*s23**(-1)*s123**(-1)*s13*s14*s134**(-1)
     &  - 1.D0/4.D0*s12*s23**(-1)*s123**(-1)*s13**2*s14**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s13**2*s134**(-1)
     &  + 1.D0/4.D0*s12*s23**(-1)*s123**(-1)*s13**3*s14**(-1)*
     & s134**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s23t4s2
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s23t4s2*s34*s123t**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s23t4s2*s14*s123t**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s23t4s2*s13*s123t**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s12t4s2*s34*s123t**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s12t4s2*s14*s123t**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s12t4s2*s13*s123t**(-1)
     &  - 1.D0/4.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*s34**2
     &  - 3.D0/2.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*s14*s34
     &
      F40AFF = F40AFF + 5.D0/2.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*
     & s14**2
     &  + 27.D0/4.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*s13*s14
     &  + 3.D0/4.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*s13**2
     &  - 2.D0*s12*s23**(-1)*s124**(-1)*s234**(-1)*s13**3*s14**(-1)
     &  - 3.D0*s12*s23**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  + 8.D0*s12*s23**(-1)*s124**(-1)*s34
     &  - 5.D0/4.D0*s12*s23**(-1)*s124**(-1)*s14
     &  - 7.D0/4.D0*s12*s23**(-1)*s124**(-1)*s13*s14**(-1)*s34
     &  + 11.D0/2.D0*s12*s23**(-1)*s124**(-1)*s13
     &  - 2.D0*s12*s23**(-1)*s124**(-1)*s13**2*s14**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s234**(-2)*s23t1s3**(-1)*s34**2*s234t
     &  - 5.D0/6.D0*s12*s23**(-1)*s234**(-2)*s34**2
     &  + 2.D0*s12*s23**(-1)*s234**(-2)*s14*s34
     &  + 2.D0*s12*s23**(-1)*s234**(-2)*s13*s34
     &
      F40AFF = F40AFF + 1.D0/2.D0*s12*s23**(-1)*s234**(-2)*s23t1s3*
     & s34**2*s234t**(-1)
     &  + 17.D0/4.D0*s12*s23**(-1)*s234**(-1)*s14**(-1)*s34**2
     &  - 15.D0/4.D0*s12*s23**(-1)*s234**(-1)*s14**(-1)*s34**3*
     & s134**(-1)
     &  + 17.D0/3.D0*s12*s23**(-1)*s234**(-1)*s34
     &  - 8.D0*s12*s23**(-1)*s234**(-1)*s34**2*s134**(-1)
     &  - 13.D0/2.D0*s12*s23**(-1)*s234**(-1)*s14
     &  - 13.D0/2.D0*s12*s23**(-1)*s234**(-1)*s14*s34*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s14**2*s134**(-1)
     &  - 7.D0/4.D0*s12*s23**(-1)*s234**(-1)*s13*s14**(-1)*s34
     &  - 3.D0/4.D0*s12*s23**(-1)*s234**(-1)*s13*s14**(-1)*s34**2*
     & s134**(-1)
     &  - 25.D0/2.D0*s12*s23**(-1)*s234**(-1)*s13
     &  + 7.D0/4.D0*s12*s23**(-1)*s234**(-1)*s13*s34*s134**(-1)
     &
      F40AFF = F40AFF + 19.D0/4.D0*s12*s23**(-1)*s234**(-1)*s13*s14*
     & s134**(-1)
     &  + 2.D0*s12*s23**(-1)*s234**(-1)*s13**2*s14**(-1)
     &  + 19.D0/4.D0*s12*s23**(-1)*s234**(-1)*s13**2*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s13**3*s14**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s23t1s3*s34*s234t**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s34t1s3*s34*s234t**(-1)
     &  - 10.D0*s12*s23**(-1)*s14**(-1)*s34
     &  + 4.D0*s12*s23**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  - 3.D0*s12*s23**(-1)
     &  + 9.D0*s12*s23**(-1)*s34*s134**(-1)
     &  + 11.D0/2.D0*s12*s23**(-1)*s14*s34**(-1)
     &  + 6.D0*s12*s23**(-1)*s14*s134**(-1)
     &  + s12*s23**(-1)*s14**2*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - 1.D0/4.D0*s12*s23**(-1)*s13*s14**(-1)
     &  + s12*s23**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 13.D0/2.D0*s12*s23**(-1)*s13*s34**(-1)
     &  + 5.D0/4.D0*s12*s23**(-1)*s13*s134**(-1)
     &  - 2.D0*s12*s23**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  - 5.D0/2.D0*s12*s23**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + 10.D0*s12*s23**(-1)*s24*s123**(-2)*s34
     &  + 10.D0*s12*s23**(-1)*s24*s123**(-2)*s14
     &  + 7.D0/2.D0*s12*s23**(-1)*s24*s123**(-2)*s13
     &  + s12*s23**(-1)*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s123**(-1)*s124**(-1)*s34
     &  - 3.D0/4.D0*s12*s23**(-1)*s24*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/4.D0*s12*s23**(-1)*s24*s123**(-1)*s124**(-1)*s13
     &  + 4.D0*s12*s23**(-1)*s24*s123**(-1)*s234**(-1)*s34
     &
      F40AFF = F40AFF - 5.D0*s12*s23**(-1)*s24*s123**(-1)*s234**(-1)*
     & s14
     &  + 4.D0*s12*s23**(-1)*s24*s123**(-1)*s234**(-1)*s13
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s123**(-1)*s14**(-1)*s34
     &  - 67.D0/12.D0*s12*s23**(-1)*s24*s123**(-1)
     &  - 3.D0/2.D0*s12*s23**(-1)*s24*s123**(-1)*s14*s34**(-1)
     &  + 2.D0*s12*s23**(-1)*s24*s123**(-1)*s14*s134**(-1)
     &  + s12*s23**(-1)*s24*s123**(-1)*s13*s14**(-1)
     &  - 7.D0/4.D0*s12*s23**(-1)*s24*s123**(-1)*s13*s34**(-1)
     &  - 3.D0/4.D0*s12*s23**(-1)*s24*s123**(-1)*s13*s134**(-1)
     &  - 3.D0/4.D0*s12*s23**(-1)*s24*s123**(-1)*s13**2*s14**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s123**(-1)*s23t4s2*s123t**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24*s123**(-1)*s12t4s2*s123t**(-1)
     &  - 5.D0/4.D0*s12*s23**(-1)*s24*s124**(-1)*s234**(-1)*s14
     &
      F40AFF = F40AFF + 1.D0/4.D0*s12*s23**(-1)*s24*s124**(-1)*
     & s234**(-1)*s13
     &  + s12*s23**(-1)*s24*s124**(-1)*s234**(-1)*s13**2*s14**(-1)
     &  + s12*s23**(-1)*s24*s124**(-1)*s14**(-1)*s34
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s124**(-1)
     &  + s12*s23**(-1)*s24*s124**(-1)*s13*s14**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24*s234**(-2)*s34
     &  - s12*s23**(-1)*s24*s234**(-2)*s14
     &  - s12*s23**(-1)*s24*s234**(-2)*s13
     &  + s12*s23**(-1)*s24*s234**(-1)*s14**(-1)*s34
     &  - 3.D0/4.D0*s12*s23**(-1)*s24*s234**(-1)*s14**(-1)*s34**2*
     & s134**(-1)
     &  - 6.D0*s12*s23**(-1)*s24*s234**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24*s234**(-1)*s14*s134**(-1)
     &  - 7.D0/4.D0*s12*s23**(-1)*s24*s234**(-1)*s13*s14**(-1)
     &
      F40AFF = F40AFF + 3.D0/2.D0*s12*s23**(-1)*s24*s234**(-1)*s13*
     & s134**(-1)
     &  - 13.D0/4.D0*s12*s23**(-1)*s24*s14**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s14**(-1)*s34*s134**(-1)
     &  + 79.D0/12.D0*s12*s23**(-1)*s24*s34**(-1)
     &  + 7.D0/2.D0*s12*s23**(-1)*s24*s134**(-1)
     &  - s12*s23**(-1)*s24*s14*s34**(-1)*s134**(-1)
     &  + 2.D0*s12*s23**(-1)*s24*s13*s14**(-1)*s34**(-1)
     &  + 2.D0*s12*s23**(-1)*s24*s13*s14**(-1)*s134**(-1)
     &  - 7.D0/2.D0*s12*s23**(-1)*s24*s13*s34**(-1)*s134**(-1)
     &  - s12*s23**(-1)*s24*s23t1s3*s34**(-1)*s234t**(-1)
     &  + s12*s23**(-1)*s24*s34t1s3*s34**(-1)*s234t**(-1)
     &  + 5.D0*s12*s23**(-1)*s24**2*s123**(-2)
     &  - 1.D0/4.D0*s12*s23**(-1)*s24**2*s123**(-1)*s124**(-1)
     &  + 2.D0*s12*s23**(-1)*s24**2*s123**(-1)*s234**(-1)
     &
      F40AFF = F40AFF + 7.D0/4.D0*s12*s23**(-1)*s24**2*s123**(-1)*
     & s14**(-1)
     &  + 1.D0/4.D0*s12*s23**(-1)*s24**2*s123**(-1)*s34**(-1)
     &  - 3.D0*s12*s23**(-1)*s24**2*s123**(-1)*s134**(-1)
     &  + s12*s23**(-1)*s24**2*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s12*s23**(-1)*s24**2*s124**(-1)*s234**(-1)
     &  - 3.D0/4.D0*s12*s23**(-1)*s24**2*s124**(-1)*s234**(-1)*s13*
     & s14**(-1)
     &  - 1.D0/4.D0*s12*s23**(-1)*s24**2*s124**(-1)*s14**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24**2*s234**(-2)*s23t1s3**(-1)*s234t
     &  + 2.D0/3.D0*s12*s23**(-1)*s24**2*s234**(-2)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24**2*s234**(-2)*s23t1s3*s234t**(-1)
     &  - 3.D0/4.D0*s12*s23**(-1)*s24**2*s234**(-1)*s14**(-1)
     &  + 3.D0/2.D0*s12*s23**(-1)*s24**2*s234**(-1)*s134**(-1)
     &  - 3.D0*s12*s23**(-1)*s24**2*s14**(-1)*s134**(-1)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s12*s23**(-1)*s24**2*s34**(-1)*
     & s134**(-1)
     &  + 11.D0/4.D0*s12*s23**(-1)*s24**3*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  + 3.D0/4.D0*s12*s23**(-1)*s24**3*s123**(-1)*s34**(-1)*
     & s134**(-1)
     &  + 1.D0/4.D0*s12*s23**(-1)*s24**3*s124**(-1)*s234**(-1)*
     & s14**(-1)
     &  - 3.D0/4.D0*s12*s23**(-1)*s24**3*s234**(-1)*s14**(-1)*
     & s134**(-1)
     &  - s12*s123**(-2)*s23t4s2**(-1)*s123t**2
     &  + s12*s123**(-2)*s23t4s2**(-1)*s34*s123t
     &  + s12*s123**(-2)*s23t4s2**(-1)*s14*s123t
     &  + 2.D0*s12*s123**(-2)*s23t4s2**(-1)*s13*s123t
     &  - 1.D0/2.D0*s12*s123**(-2)*s123t
     &
      F40AFF = F40AFF + 13.D0/4.D0*s12*s123**(-2)*s34
     &  + 13.D0/4.D0*s12*s123**(-2)*s14
     &  - 5.D0*s12*s123**(-2)*s13
     &  + s12*s123**(-2)*s23t4s2*s34*s123t**(-1)
     &  + s12*s123**(-2)*s23t4s2*s14*s123t**(-1)
     &  + 2.D0*s12*s123**(-2)*s23t4s2*s13*s123t**(-1)
     &  - s12*s123**(-2)*s12t4s2*s23t4s2**(-1)*s123t
     &  - s12*s123**(-2)*s12t4s2*s23t4s2*s123t**(-1)
     &  + 5.D0/4.D0*s12*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  - 27.D0/4.D0*s12*s123**(-1)*s124**(-1)*s34
     &  + 7.D0/4.D0*s12*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/4.D0*s12*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34
     &  + 1.D0/2.D0*s12*s123**(-1)*s124**(-1)*s13**2*s14**(-1)
     &  - 3.D0*s12*s123**(-1)*s234**(-1)*s34
     &  - 5.D0/4.D0*s12*s123**(-1)*s234**(-1)*s14
     &
      F40AFF = F40AFF + 3.D0/4.D0*s12*s123**(-1)*s234**(-1)*s14**2*
     & s34**(-1)
     &  + s12*s123**(-1)*s234**(-1)*s13
     &  + 5.D0/2.D0*s12*s123**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &  - 1.D0/2.D0*s12*s123**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  + 7.D0/4.D0*s12*s123**(-1)*s14**(-1)*s34
     &  - 5.D0/6.D0*s12*s123**(-1)
     &  - 7.D0/4.D0*s12*s123**(-1)*s14*s34**(-1)
     &  - 3.D0/4.D0*s12*s123**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12*s123**(-1)*s13*s14**(-1)
     &  - 1.D0/4.D0*s12*s123**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 1.D0/4.D0*s12*s123**(-1)*s13*s34**(-1)
     &  + 13.D0/4.D0*s12*s123**(-1)*s13*s134**(-1)
     &  + 1.D0/4.D0*s12*s123**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s12*s123**(-1)*s13**2*s14**(-1)*s134**(-1)
     &
      F40AFF = F40AFF + 3.D0/4.D0*s12*s123**(-1)*s13**2*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12*s123**(-1)*s23t4s2*s123t**(-1)
     &  + 1.D0/2.D0*s12*s123**(-1)*s12t4s2*s123t**(-1)
     &  - s12*s124**(-2)*s14**(-1)*s34**2
     &  + 5.D0/4.D0*s12*s124**(-2)*s34
     &  - 2.D0*s12*s124**(-2)*s13*s14**(-1)*s34
     &  + 5.D0/4.D0*s12*s124**(-2)*s13
     &  - s12*s124**(-2)*s13**2*s14**(-1)
     &  - 3.D0/2.D0*s12*s124**(-1)*s234**(-1)*s34
     &  - 9.D0/2.D0*s12*s124**(-1)*s234**(-1)*s14
     &  - 2.D0*s12*s124**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - 5.D0/4.D0*s12*s124**(-1)*s234**(-1)*s13
     &  - 3.D0*s12*s124**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &  + 3.D0/2.D0*s12*s124**(-1)*s234**(-1)*s13**2*s14**(-1)
     &
      F40AFF = F40AFF - 3.D0/2.D0*s12*s124**(-1)*s234**(-1)*s13**2*
     & s34**(-1)
     &  - s12*s124**(-1)*s234**(-1)*s13**3*s14**(-1)*s34**(-1)
     &  - 23.D0/4.D0*s12*s124**(-1)*s14**(-1)*s34
     &  - 1.D0/2.D0*s12*s124**(-1)
     &  - 3.D0/2.D0*s12*s124**(-1)*s34*s134**(-1)
     &  + 7.D0/4.D0*s12*s124**(-1)*s14*s34**(-1)
     &  - 9.D0/2.D0*s12*s124**(-1)*s14*s134**(-1)
     &  - 3.D0*s12*s124**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + s12*s124**(-1)*s13*s14**(-2)*s34
     &  - 11.D0/2.D0*s12*s124**(-1)*s13*s14**(-1)
     &  + s12*s124**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  - 19.D0/4.D0*s12*s124**(-1)*s13*s34**(-1)
     &  + 7.D0/4.D0*s12*s124**(-1)*s13*s134**(-1)
     &  - 3.D0/4.D0*s12*s124**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF + s12*s124**(-1)*s13**2*s14**(-2)
     &  - 9.D0/4.D0*s12*s124**(-1)*s13**2*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12*s124**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  + 3.D0/4.D0*s12*s124**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12*s124**(-1)*s12t3s1*s14**(-1)
     &  + s12*s234**(-2)*s23t1s3**(-1)*s34*s234t
     &  - 7.D0/4.D0*s12*s234**(-2)*s34
     &  + 2.D0*s12*s234**(-2)*s14
     &  + 2.D0*s12*s234**(-2)*s13
     &  + s12*s234**(-2)*s23t1s3*s34*s234t**(-1)
     &  + 19.D0/4.D0*s12*s234**(-1)*s14**(-1)*s34
     &  - 15.D0/4.D0*s12*s234**(-1)*s14**(-1)*s34**2*s134**(-1)
     &  + 47.D0/4.D0*s12*s234**(-1)
     &  - 39.D0/4.D0*s12*s234**(-1)*s34*s134**(-1)
     &  + 3.D0/2.D0*s12*s234**(-1)*s14*s34**(-1)
     &
      F40AFF = F40AFF - 10.D0*s12*s234**(-1)*s14*s134**(-1)
     &  - 7.D0/2.D0*s12*s234**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + s12*s234**(-1)*s13*s14**(-1)
     &  - 9.D0/4.D0*s12*s234**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  - 3.D0*s12*s234**(-1)*s13*s34**(-1)
     &  - 3.D0/2.D0*s12*s234**(-1)*s13*s134**(-1)
     &  + s12*s234**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12*s234**(-1)*s13**2*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12*s234**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  + 9.D0/2.D0*s12*s234**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + s12*s14**(-2)*s34**2*s134**(-1)
     &  - 5.D0*s12*s14**(-1)
     &  + 19.D0/4.D0*s12*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/2.D0*s12*s14**(-1)*s34**2*s134**(-2)
     &  - 7.D0/4.D0*s12*s34**(-1)
     &
      F40AFF = F40AFF + 21.D0/2.D0*s12*s134**(-1)
     &  + 1.D0/4.D0*s12*s34*s134**(-2)
     &  - 2.D0*s12*s14*s34**(-2)
     &  + 4.D0*s12*s14*s34**(-1)*s134**(-1)
     &  + 7.D0/4.D0*s12*s14*s134**(-2)
     &  + 3.D0/2.D0*s12*s14**2*s34**(-2)*s134**(-1)
     &  + 3.D0/2.D0*s12*s14**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s12*s14**3*s34**(-2)*s134**(-2)
     &  + 4.D0*s12*s13*s14**(-2)
     &  - s12*s13*s14**(-2)*s34*s134**(-1)
     &  + 1.D0/4.D0*s12*s13*s14**(-1)*s34**(-1)
     &  + 2.D0*s12*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s13*s14**(-1)*s34*s134**(-2)
     &  + 2.D0*s12*s13*s34**(-2)
     &  + 3.D0/4.D0*s12*s13*s34**(-1)*s134**(-1)
     &
      F40AFF = F40AFF + s12*s13*s134**(-2)
     &  + 2.D0*s12*s13*s14*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s12*s13*s14**2*s34**(-2)*s134**(-2)
     &  - 5.D0/2.D0*s12*s13**2*s14**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s12*s13**2*s14**(-2)*s34*s134**(-2)
     &  - 2.D0*s12*s13**2*s34**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s12*s13**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s12*s13**3*s14**(-2)*s134**(-2)
     &  + s12*s24*s123**(-2)*s23t4s2**(-1)*s123t
     &  + 13.D0/4.D0*s12*s24*s123**(-2)
     &  + s12*s24*s123**(-2)*s23t4s2*s123t**(-1)
     &  - 3.D0/2.D0*s12*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + 7.D0/4.D0*s12*s24*s123**(-1)*s234**(-1)
     &  + 5.D0/4.D0*s12*s24*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s12*s24*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &
      F40AFF = F40AFF + 3.D0/2.D0*s12*s24*s123**(-1)*s14**(-1)
     &  + 3.D0/4.D0*s12*s24*s123**(-1)*s34**(-1)
     &  - 9.D0/2.D0*s12*s24*s123**(-1)*s134**(-1)
     &  - s12*s24*s123**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 4.D0*s12*s24*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s12*s24*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12*s24*s124**(-2)*s14**(-1)*s34
     &  + 1.D0/2.D0*s12*s24*s124**(-2)*s13*s14**(-1)
     &  - 1.D0/4.D0*s12*s24*s124**(-1)*s234**(-1)*s14**(-1)*s34
     &  + 1.D0/4.D0*s12*s24*s124**(-1)*s234**(-1)
     &  - 1.D0/4.D0*s12*s24*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 3.D0/4.D0*s12*s24*s124**(-1)*s234**(-1)*s13*s14**(-1)
     &  - 1.D0/4.D0*s12*s24*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 5.D0/4.D0*s12*s24*s124**(-1)*s14**(-1)
     &  + 1.D0/4.D0*s12*s24*s124**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - s12*s24*s124**(-1)*s134**(-1)
     &  - 3.D0/4.D0*s12*s24*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &  - s12*s24*s124**(-1)*s13*s14**(-2)
     &  - 3.D0/4.D0*s12*s24*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + s12*s24*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  + s12*s24*s234**(-2)*s23t1s3**(-1)*s234t
     &  - 5.D0/2.D0*s12*s24*s234**(-2)
     &  - s12*s24*s234**(-2)*s14*s34**(-1)
     &  - s12*s24*s234**(-2)*s13*s34**(-1)
     &  + s12*s24*s234**(-2)*s23t1s3*s234t**(-1)
     &  + 1.D0/2.D0*s12*s24*s234**(-1)*s14**(-1)
     &  - 3.D0/2.D0*s12*s24*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 3.D0/2.D0*s12*s24*s234**(-1)*s34**(-1)
     &  - 7.D0/4.D0*s12*s24*s234**(-1)*s134**(-1)
     &  + s12*s24*s234**(-1)*s14*s34**(-2)
     &
      F40AFF = F40AFF - 5.D0/2.D0*s12*s24*s234**(-1)*s14*s34**(-1)*
     & s134**(-1)
     &  - s12*s24*s234**(-1)*s14**2*s34**(-2)*s134**(-1)
     &  - 5.D0/4.D0*s12*s24*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/4.D0*s12*s24*s234**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s12*s24*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  - s12*s24*s234**(-1)*s13*s14*s34**(-2)*s134**(-1)
     &  - s12*s24*s14**(-2)*s34*s134**(-1)
     &  + s12*s24*s14**(-2)*s34**2*s134**(-2)
     &  - s12*s24*s14**(-1)*s34**(-1)
     &  + 4.D0*s12*s24*s14**(-1)*s134**(-1)
     &  + 2.D0*s12*s24*s14**(-1)*s34*s134**(-2)
     &  + 2.D0*s12*s24*s34**(-2)
     &  - 9.D0/4.D0*s12*s24*s34**(-1)*s134**(-1)
     &  + 3.D0*s12*s24*s134**(-2)
     &
      F40AFF = F40AFF - 3.D0*s12*s24*s14*s34**(-2)*s134**(-1)
     &  + 4.D0*s12*s24*s14*s34**(-1)*s134**(-2)
     &  + 2.D0*s12*s24*s14**2*s34**(-2)*s134**(-2)
     &  + s12*s24*s13*s14**(-2)*s134**(-1)
     &  - s12*s24*s13**2*s14**(-2)*s134**(-2)
     &  - 2.D0*s12*s24*s13**2*s34**(-2)*s134**(-2)
     &  - 3.D0/4.D0*s12*s24**2*s123**(-1)*s234**(-1)*s34**(-1)
     &  + 9.D0/4.D0*s12*s24**2*s123**(-1)*s14**(-1)*s134**(-1)
     &  + 3.D0/4.D0*s12*s24**2*s123**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12*s24**2*s124**(-2)*s14**(-1)
     &  + 1.D0/4.D0*s12*s24**2*s124**(-1)*s234**(-1)*s14**(-1)
     &  + 1.D0/4.D0*s12*s24**2*s124**(-1)*s234**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12*s24**2*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s24**2*s234**(-2)*s34**(-1)
     &  + 3.D0/2.D0*s12*s24**2*s234**(-1)*s14**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - 7.D0/2.D0*s12*s24**2*s234**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12*s24**2*s234**(-1)*s34**(-2)
     &  - s12*s24**2*s234**(-1)*s34**(-1)*s134**(-1)
     &  - s12*s24**2*s234**(-1)*s14*s34**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s12*s24**3*s234**(-2)*s34**(-2)
     &  + s12*s23*s123**(-2)*s23t4s2**(-1)*s123t
     &  - 5.D0/2.D0*s12*s23*s123**(-2)
     &  + s12*s23*s123**(-2)*s23t4s2*s123t**(-1)
     &  + 3.D0/2.D0*s12*s23*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + s12*s23*s123**(-1)*s124**(-1)
     &  + 3.D0/4.D0*s12*s23*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  - 19.D0/4.D0*s12*s23*s123**(-1)*s234**(-1)
     &  + 7.D0/4.D0*s12*s23*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 9.D0/4.D0*s12*s23*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &
      F40AFF = F40AFF - 5.D0/4.D0*s12*s23*s123**(-1)*s14**(-1)
     &  + 7.D0/4.D0*s12*s23*s123**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s12*s23*s123**(-1)*s134**(-1)
     &  - 3.D0/2.D0*s12*s23*s123**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12*s23*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12*s23*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 2.D0*s12*s23*s124**(-2)*s14**(-1)*s34
     &  + 5.D0/4.D0*s12*s23*s124**(-2)
     &  - 2.D0*s12*s23*s124**(-2)*s13*s14**(-1)
     &  - s12*s23*s124**(-1)*s234**(-1)*s13*s14**(-1)
     &  - 13.D0/2.D0*s12*s23*s124**(-1)*s14**(-1)
     &  - 19.D0/4.D0*s12*s23*s124**(-1)*s34**(-1)
     &  + 4.D0*s12*s23*s124**(-1)*s134**(-1)
     &  + 9.D0/2.D0*s12*s23*s124**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 3.D0*s12*s23*s124**(-1)*s13*s14**(-2)
     &
      F40AFF = F40AFF - s12*s23*s124**(-1)*s13*s14**(-2)*s34*s134**(-1)
     &  - 5.D0/4.D0*s12*s23*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s12*s23*s124**(-1)*s13*s34**(-1)*s134**(-1)
     &  - s12*s23*s124**(-1)*s13**2*s14**(-2)*s134**(-1)
     &  + 1.D0/4.D0*s12*s23*s234**(-2)
     &  + 3.D0/2.D0*s12*s23*s234**(-1)*s14**(-1)
     &  - 9.D0/4.D0*s12*s23*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 29.D0/12.D0*s12*s23*s234**(-1)*s34**(-1)
     &  - 13.D0/4.D0*s12*s23*s234**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s23*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s12*s23*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12*s23*s234**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s23*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12*s23*s234**(-1)*s23t1s3*s34**(-1)*s234t**(-1)
     &  + 1.D0/2.D0*s12*s23*s234**(-1)*s34t1s3*s34**(-1)*s234t**(-1)
     &
      F40AFF = F40AFF + s12*s23*s14**(-2)*s34**2*s134**(-2)
     &  + s12*s23*s14**(-1)*s34**(-1)
     &  + 5.D0/4.D0*s12*s23*s14**(-1)*s134**(-1)
     &  + 2.D0*s12*s23*s14**(-1)*s34*s134**(-2)
     &  - 2.D0*s12*s23*s34**(-2)
     &  + 5.D0/4.D0*s12*s23*s34**(-1)*s134**(-1)
     &  + 3.D0*s12*s23*s134**(-2)
     &  + 4.D0*s12*s23*s14*s34**(-1)*s134**(-2)
     &  + 2.D0*s12*s23*s14**2*s34**(-2)*s134**(-2)
     &  + 3.D0*s12*s23*s13*s14**(-2)*s134**(-1)
     &  + 4.D0*s12*s23*s13*s34**(-2)*s134**(-1)
     &  - s12*s23*s13**2*s14**(-2)*s134**(-2)
     &  - 2.D0*s12*s23*s13**2*s34**(-2)*s134**(-2)
     &  + 3.D0/4.D0*s12*s23*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 2.D0*s12*s23*s24*s123**(-1)*s234**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - 9.D0/2.D0*s12*s23*s24*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 9.D0/4.D0*s12*s23*s24*s123**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12*s23*s24*s124**(-2)*s14**(-1)
     &  - 1.D0/2.D0*s12*s23*s24*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12*s23*s24*s124**(-1)*s34**(-1)*s134**(-1)
     &  - s12*s23*s24*s124**(-1)*s13*s14**(-2)*s134**(-1)
     &  - s12*s23*s24*s234**(-2)*s34**(-1)
     &  + 3.D0/2.D0*s12*s23*s24*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 9.D0/2.D0*s12*s23*s24*s234**(-1)*s14**(-1)*s134**(-1)
     &  - 2.D0*s12*s23*s24*s234**(-1)*s34**(-1)*s134**(-1)
     &  - s12*s23*s24*s234**(-1)*s14*s34**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s12*s23*s24**2*s234**(-2)*s34**(-2)
     &  - 1.D0/4.D0*s12*s23**2*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 7.D0/2.D0*s12*s23**2*s123**(-1)*s234**(-1)*s34**(-1)
     &
      F40AFF = F40AFF - 11.D0/4.D0*s12*s23**2*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 9.D0/4.D0*s12*s23**2*s123**(-1)*s34**(-1)*s134**(-1)
     &  - s12*s23**2*s124**(-2)*s14**(-1)
     &  + 1.D0/2.D0*s12*s23**2*s124**(-1)*s234**(-1)*s14**(-1)
     &  - 1.D0/4.D0*s12*s23**2*s124**(-1)*s234**(-1)*s34**(-1)
     &  + s12*s23**2*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 2.D0*s12*s23**2*s124**(-1)*s14**(-1)*s134**(-1)
     &  - 5.D0/2.D0*s12*s23**2*s124**(-1)*s34**(-1)*s134**(-1)
     &  + s12*s23**2*s124**(-1)*s13*s14**(-2)*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**2*s234**(-2)*s34**(-1)
     &  + 1.D0/2.D0*s12*s23**2*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 7.D0/4.D0*s12*s23**2*s234**(-1)*s14**(-1)*s134**(-1)
     &  - s12*s23**2*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 3.D0*s12**2*s23**(-2)*s123**(-2)*s34**2
     &
      F40AFF = F40AFF + 6.D0*s12**2*s23**(-2)*s123**(-2)*s14*s34
     &  + 3.D0*s12**2*s23**(-2)*s123**(-2)*s14**2
     &  + 2.D0*s12**2*s23**(-2)*s123**(-2)*s13*s34
     &  + 2.D0*s12**2*s23**(-2)*s123**(-2)*s13*s14
     &  + 4.D0*s12**2*s23**(-2)*s123**(-1)*s34
     &  + 4.D0*s12**2*s23**(-2)*s123**(-1)*s14
     &  + 2.D0*s12**2*s23**(-2)*s123**(-1)*s13
     &  + s12**2*s23**(-2)*s234**(-2)*s34**2
     &  - s12**2*s23**(-2)
     &  + 6.D0*s12**2*s23**(-2)*s24*s123**(-2)*s34
     &  + 6.D0*s12**2*s23**(-2)*s24*s123**(-2)*s14
     &  + 2.D0*s12**2*s23**(-2)*s24*s123**(-2)*s13
     &  - 4.D0*s12**2*s23**(-2)*s24*s123**(-1)*s234**(-1)*s14
     &  - 2.D0*s12**2*s23**(-2)*s24*s234**(-1)
     &  + 3.D0*s12**2*s23**(-2)*s24**2*s123**(-2)
     &
      F40AFF = F40AFF + s12**2*s23**(-2)*s24**2*s234**(-2)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s123t**2
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s34*s123t
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s14*s123t
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s13*s123t
     &  - 1.D0/4.D0*s12**2*s23**(-1)*s123**(-2)*s123t
     &  + 11.D0/3.D0*s12**2*s23**(-1)*s123**(-2)*s34
     &  + 11.D0/3.D0*s12**2*s23**(-1)*s123**(-2)*s14
     &  - 19.D0/12.D0*s12**2*s23**(-1)*s123**(-2)*s13
     &  + 1.D0/4.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2*s34*s123t**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2*s14*s123t**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2*s13*s123t**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s23t4s2**2*s123t**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s12t4s2*s23t4s2**(-1)*
     & s123t
     &
      F40AFF = F40AFF - 1.D0/2.D0*s12**2*s23**(-1)*s123**(-2)*s12t4s2*
     & s23t4s2*s123t**(-1)
     &  + 5.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34**2
     &  - 13.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s124**(-1)*s34
     &  + 5.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s124**(-1)*s14
     &  - 3.D0/4.D0*s12**2*s23**(-1)*s123**(-1)*s124**(-1)*s13*
     & s14**(-1)*s34
     &  - 2.D0*s12**2*s23**(-1)*s123**(-1)*s234**(-1)*s34
     &  - 7.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s234**(-1)*s14
     &  - 2.D0*s12**2*s23**(-1)*s123**(-1)*s234**(-1)*s13
     &  + 2.D0*s12**2*s23**(-1)*s123**(-1)*s14**(-1)*s34
     &  + 2.D0/3.D0*s12**2*s23**(-1)*s123**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s14*s34**(-1)
     &  + 5.D0/4.D0*s12**2*s23**(-1)*s123**(-1)*s14*s134**(-1)
     &
      F40AFF = F40AFF - 1.D0/4.D0*s12**2*s23**(-1)*s123**(-1)*s13*
     & s14**(-1)
     &  + 1.D0/4.D0*s12**2*s23**(-1)*s123**(-1)*s13*s34**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s23t4s2*s123t**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s123**(-1)*s12t4s2*s123t**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s124**(-1)*s234**(-1)*s34
     &  + 11.D0/4.D0*s12**2*s23**(-1)*s124**(-1)*s234**(-1)*s14
     &  + 11.D0/4.D0*s12**2*s23**(-1)*s124**(-1)*s234**(-1)*s13
     &  - 3.D0/2.D0*s12**2*s23**(-1)*s124**(-1)*s234**(-1)*s13**2*
     & s14**(-1)
     &  + 9.D0/4.D0*s12**2*s23**(-1)*s124**(-1)*s14**(-1)*s34
     &  - s12**2*s23**(-1)*s124**(-1)
     &  + 1.D0/4.D0*s12**2*s23**(-1)*s124**(-1)*s13*s14**(-1)
     &  + s12**2*s23**(-1)*s234**(-2)*s34
     &  - 5.D0*s12**2*s23**(-1)*s234**(-1)*s14**(-1)*s34
     &
      F40AFF = F40AFF + 11.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*
     & s14**(-1)*s34**2*s134**(-1)
     &  - 27.D0/4.D0*s12**2*s23**(-1)*s234**(-1)
     &  + 33.D0/4.D0*s12**2*s23**(-1)*s234**(-1)*s34*s134**(-1)
     &  + 5.D0*s12**2*s23**(-1)*s234**(-1)*s14*s134**(-1)
     &  + 2.D0*s12**2*s23**(-1)*s234**(-1)*s13*s14**(-1)
     &  + s12**2*s23**(-1)*s234**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + 7.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*s13*s134**(-1)
     &  - 3.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*s13**2*s14**(-1)*
     & s134**(-1)
     &  + 7.D0/4.D0*s12**2*s23**(-1)*s14**(-1)
     &  - 17.D0/4.D0*s12**2*s23**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 5.D0/2.D0*s12**2*s23**(-1)*s34**(-1)
     &  - s12**2*s23**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12**2*s23**(-1)*s14*s34**(-1)*s134**(-1)

      F40AFF = F40AFF - 5.D0/4.D0*s12**2*s23**(-1)*s13*s14**(-1)*
     & s134**(-1)
     &  - 7.D0/4.D0*s12**2*s23**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s24*s123**(-2)*s23t4s2**(-1)*s123t
     &  + 11.D0/3.D0*s12**2*s23**(-1)*s24*s123**(-2)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s24*s123**(-2)*s23t4s2*s123t**(-1)
     &  - 3.D0/4.D0*s12**2*s23**(-1)*s24*s123**(-1)*s124**(-1)*
     & s14**(-1)*s34
     &  - 1.D0/4.D0*s12**2*s23**(-1)*s24*s123**(-1)*s124**(-1)
     &  + 2.D0*s12**2*s23**(-1)*s24*s123**(-1)*s234**(-1)
     &  + 2.D0*s12**2*s23**(-1)*s24*s123**(-1)*s14**(-1)
     &  - 1.D0/4.D0*s12**2*s23**(-1)*s24*s123**(-1)*s34**(-1)
     &  - 13.D0/4.D0*s12**2*s23**(-1)*s24*s123**(-1)*s134**(-1)
     &  - 1.D0/4.D0*s12**2*s23**(-1)*s24*s124**(-1)*s234**(-1)
     &  - 1.D0/4.D0*s12**2*s23**(-1)*s24*s124**(-1)*s14**(-1)

      F40AFF = F40AFF - 1.D0/2.D0*s12**2*s23**(-1)*s24*s234**(-2)
     &  - 3.D0/2.D0*s12**2*s23**(-1)*s24*s234**(-1)*s14**(-1)
     &  + s12**2*s23**(-1)*s24*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 5.D0/4.D0*s12**2*s23**(-1)*s24*s234**(-1)*s134**(-1)
     &  - s12**2*s23**(-1)*s24*s14**(-1)*s134**(-1)
     &  + 15.D0/4.D0*s12**2*s23**(-1)*s24**2*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  + 3.D0/2.D0*s12**2*s23**(-1)*s24**2*s123**(-1)*s34**(-1)*
     & s134**(-1)
     &  - 3.D0/4.D0*s12**2*s23**(-1)*s24**2*s234**(-1)*s14**(-1)*
     & s134**(-1)
     &  + 3.D0/2.D0*s12**2*s123**(-2)*s23t4s2**(-1)*s123t
     &  - 49.D0/12.D0*s12**2*s123**(-2)
     &  + 3.D0/2.D0*s12**2*s123**(-2)*s23t4s2*s123t**(-1)
     &  - 5.D0/4.D0*s12**2*s123**(-1)*s124**(-1)*s14**(-1)*s34

      F40AFF = F40AFF + 11.D0/4.D0*s12**2*s123**(-1)*s124**(-1)
     &  + s12**2*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  - 4.D0*s12**2*s123**(-1)*s234**(-1)
     &  + 1.D0/2.D0*s12**2*s123**(-1)*s234**(-1)*s14*s34**(-1)
     &  - 3.D0/2.D0*s12**2*s123**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 3.D0/4.D0*s12**2*s123**(-1)*s14**(-1)
     &  + 1.D0/2.D0*s12**2*s123**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**2*s123**(-1)*s134**(-1)
     &  - s12**2*s123**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12**2*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 5.D0/4.D0*s12**2*s123**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s124**(-2)*s14**(-2)*s34**2
     &  + s12**2*s124**(-2)*s14**(-1)*s34
     &  - 1.D0/4.D0*s12**2*s124**(-2)
     &  - s12**2*s124**(-2)*s13*s14**(-2)*s34

      F40AFF = F40AFF + s12**2*s124**(-2)*s13*s14**(-1)
     &  - 1.D0/2.D0*s12**2*s124**(-2)*s13**2*s14**(-2)
     &  - 1.D0/4.D0*s12**2*s124**(-1)*s234**(-1)*s14**(-1)*s34
     &  - 7.D0/4.D0*s12**2*s124**(-1)*s234**(-1)
     &  - 11.D0/4.D0*s12**2*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s12**2*s124**(-1)*s234**(-1)*s13*s14**(-1)
     &  - 13.D0/4.D0*s12**2*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 3.D0/2.D0*s12**2*s124**(-1)*s234**(-1)*s13**2*s14**(-1)*
     & s34**(-1)
     &  - 3.D0/2.D0*s12**2*s124**(-1)*s14**(-2)*s34
     &  + 5.D0/4.D0*s12**2*s124**(-1)*s14**(-1)
     &  - 1.D0/2.D0*s12**2*s124**(-1)*s14**(-1)*s34*s134**(-1)
     &  + s12**2*s124**(-1)*s34**(-1)
     &  - 5.D0/2.D0*s12**2*s124**(-1)*s134**(-1)
     &  - 9.D0/4.D0*s12**2*s124**(-1)*s14*s34**(-1)*s134**(-1)

      F40AFF = F40AFF - 5.D0/2.D0*s12**2*s124**(-1)*s13*s14**(-2)
     &  - 3.D0/2.D0*s12**2*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**2*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s124**(-1)*s13*s34**(-1)*s134**(-1)
     &  + s12**2*s234**(-2)
     &  - 2.D0*s12**2*s234**(-1)*s14**(-1)
     &  + 11.D0/4.D0*s12**2*s234**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s234**(-1)*s34**(-1)
     &  + 7.D0/2.D0*s12**2*s234**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12**2*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + s12**2*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 7.D0/4.D0*s12**2*s234**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12**2*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  - s12**2*s14**(-2)
     &  + 1.D0/2.D0*s12**2*s14**(-2)*s34**2*s134**(-2)

      F40AFF = F40AFF - 3.D0/4.D0*s12**2*s14**(-1)*s34**(-1)
     &  + 11.D0/4.D0*s12**2*s14**(-1)*s134**(-1)
     &  + s12**2*s14**(-1)*s34*s134**(-2)
     &  - s12**2*s34**(-2)
     &  + 9.D0/4.D0*s12**2*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12**2*s134**(-2)
     &  + 2.D0*s12**2*s14*s34**(-1)*s134**(-2)
     &  + s12**2*s14**2*s34**(-2)*s134**(-2)
     &  + s12**2*s13*s14**(-2)*s134**(-1)
     &  + 2.D0*s12**2*s13*s34**(-2)*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s13**2*s14**(-2)*s134**(-2)
     &  - s12**2*s13**2*s34**(-2)*s134**(-2)
     &  + 3.D0/4.D0*s12**2*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 1.D0/2.D0*s12**2*s24*s123**(-1)*s234**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**2*s24*s123**(-1)*s14**(-1)*s134**(-1)

      F40AFF = F40AFF - s12**2*s24*s123**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s24*s124**(-2)*s14**(-2)*s34
     &  - 1.D0/4.D0*s12**2*s24*s124**(-2)*s14**(-1)
     &  + 1.D0/2.D0*s12**2*s24*s124**(-2)*s13*s14**(-2)
     &  + 1.D0/2.D0*s12**2*s24*s124**(-1)*s14**(-2)
     &  + 1.D0/4.D0*s12**2*s24*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**2*s24*s124**(-1)*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s24*s124**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s24*s234**(-2)*s34**(-1)
     &  - 2.D0*s12**2*s24*s234**(-1)*s14**(-1)*s134**(-1)
     &  + 2.D0*s12**2*s24*s234**(-1)*s34**(-2)
     &  - 2.D0*s12**2*s24*s234**(-1)*s34**(-1)*s134**(-1)
     &  - 2.D0*s12**2*s24*s234**(-1)*s14*s34**(-2)*s134**(-1)
     &  - 2.D0*s12**2*s24*s234**(-1)*s13*s34**(-2)*s134**(-1)
     &  - 11.D0/4.D0*s12**2*s23*s123**(-1)*s234**(-1)*s34**(-1)

      F40AFF = F40AFF - 5.D0/2.D0*s12**2*s23*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 3.D0*s12**2*s23*s123**(-1)*s34**(-1)*s134**(-1)
     &  - s12**2*s23*s124**(-2)*s14**(-2)*s34
     &  + s12**2*s23*s124**(-2)*s14**(-1)
     &  - s12**2*s23*s124**(-2)*s13*s14**(-2)
     &  - 1.D0/4.D0*s12**2*s23*s124**(-1)*s234**(-1)*s14**(-1)
     &  - 3.D0/2.D0*s12**2*s23*s124**(-1)*s14**(-2)
     &  - 3.D0/2.D0*s12**2*s23*s124**(-1)*s14**(-1)*s34**(-1)
     &  + 2.D0*s12**2*s23*s124**(-1)*s14**(-1)*s134**(-1)
     &  + 5.D0/4.D0*s12**2*s23*s124**(-1)*s34**(-1)*s134**(-1)
     &  - s12**2*s23*s124**(-1)*s13*s14**(-2)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s23*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 5.D0/4.D0*s12**2*s23*s234**(-1)*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s23*s24*s124**(-2)*s14**(-2)

      F40AFF = F40AFF - 1.D0/2.D0*s12**2*s23**2*s124**(-2)*s14**(-2)
     &  + 2.D0*s12**3*s23**(-2)*s123**(-2)*s34
     &  + 2.D0*s12**3*s23**(-2)*s123**(-2)*s14
     &  + 2.D0*s12**3*s23**(-2)*s123**(-1)
     &  + 2.D0*s12**3*s23**(-2)*s24*s123**(-2)
     &  + 1.D0/2.D0*s12**3*s23**(-1)*s123**(-2)*s23t4s2**(-1)*s123t
     &  - 19.D0/12.D0*s12**3*s23**(-1)*s123**(-2)
     &  + 1.D0/2.D0*s12**3*s23**(-1)*s123**(-2)*s23t4s2*s123t**(-1)
     &  - 7.D0/4.D0*s12**3*s23**(-1)*s123**(-1)*s124**(-1)*s14**(-1)*
     & s34
     &  + 2.D0*s12**3*s23**(-1)*s123**(-1)*s124**(-1)
     &  + 1.D0/4.D0*s12**3*s23**(-1)*s123**(-1)*s124**(-1)*s13*
     & s14**(-1)
     &  - 2.D0*s12**3*s23**(-1)*s123**(-1)*s234**(-1)
     &  - 1.D0/4.D0*s12**3*s23**(-1)*s123**(-1)*s14**(-1)

      F40AFF = F40AFF + 1.D0/4.D0*s12**3*s23**(-1)*s123**(-1)*s34**(-1)
     &  - 3.D0/2.D0*s12**3*s23**(-1)*s123**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**3*s23**(-1)*s123**(-1)*s14*s34**(-1)*
     & s134**(-1)
     &  - 1.D0/2.D0*s12**3*s23**(-1)*s123**(-1)*s13*s34**(-1)*
     & s134**(-1)
     &  + 5.D0/4.D0*s12**3*s23**(-1)*s124**(-1)*s234**(-1)
     &  - 1.D0/2.D0*s12**3*s23**(-1)*s124**(-1)*s234**(-1)*s13*
     & s14**(-1)
     &  - 1.D0/2.D0*s12**3*s23**(-1)*s124**(-1)*s14**(-1)
     &  + 2.D0*s12**3*s23**(-1)*s234**(-1)*s14**(-1)
     &  - 13.D0/4.D0*s12**3*s23**(-1)*s234**(-1)*s14**(-1)*s34*
     & s134**(-1)
     &  - 2.D0*s12**3*s23**(-1)*s234**(-1)*s134**(-1)
     &  - 2.D0*s12**3*s23**(-1)*s234**(-1)*s13*s14**(-1)*s134**(-1)

      F40AFF = F40AFF + 1.D0/2.D0*s12**3*s23**(-1)*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**3*s23**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s12**3*s23**(-1)*s24*s123**(-1)*s124**(-1)*
     & s14**(-1)
     &  + 7.D0/4.D0*s12**3*s23**(-1)*s24*s123**(-1)*s14**(-1)*
     & s134**(-1)
     &  - 3.D0/4.D0*s12**3*s23**(-1)*s24*s234**(-1)*s14**(-1)*
     & s134**(-1)
     &  + s12**3*s123**(-1)*s124**(-1)*s14**(-1)
     &  - 5.D0/4.D0*s12**3*s123**(-1)*s234**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12**3*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 2.D0*s12**3*s123**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**3*s124**(-2)*s14**(-2)*s34
     &  - 1.D0/4.D0*s12**3*s124**(-2)*s14**(-1)
     &  + 1.D0/2.D0*s12**3*s124**(-2)*s13*s14**(-2)

      F40AFF = F40AFF + 1.D0/4.D0*s12**3*s124**(-1)*s234**(-1)*
     & s14**(-1)
     &  - 7.D0/4.D0*s12**3*s124**(-1)*s234**(-1)*s34**(-1)
     &  - s12**3*s124**(-1)*s234**(-1)*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**3*s124**(-1)*s14**(-2)
     &  + 1.D0/4.D0*s12**3*s124**(-1)*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**3*s124**(-1)*s14**(-1)*s134**(-1)
     &  - 3.D0/4.D0*s12**3*s124**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**3*s234**(-1)*s14**(-1)*s34**(-1)
     &  - 3.D0/4.D0*s12**3*s234**(-1)*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**3*s23*s124**(-2)*s14**(-2)
     &  + 1.D0/2.D0*s12**4*s23**(-1)*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 1.D0/4.D0*s12**4*s23**(-1)*s123**(-1)*s14**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**4*s23**(-1)*s123**(-1)*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s12**4*s124**(-1)*s234**(-1)*s14**(-1)*s34**(-1)

      F40a = s1234**(-2)*F40AFF

      return
      end
************************************************************************

c     Sub-antenna function F40b for F40.
c     F40(1,2,3,4) = F40a(1,2,3,4) + F40b(1,2,3,4)
c     + F40a(1,4,3,2) + F40b(1,4,3,2)
c     + F40b(2,3,4,1) + F40a(2,1,4,3)
c     + F40b(4,3,2,1) + F40a(4,1,2,3)
      real(8) function F40b(s12,s13,s14,s23,s24,s34)
      implicit double precision (a-h,o-z)
      real(8), intent(in) :: s12,s13,s14,s23,s24,s34

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s134 = s13+s14+s34
      s234 = s23+s24+s34

      s1234 = s12+s13+s14+s23+s24+s34

      s123t = s123
      s124t = s124
      s134t = s134
      s234t = s234

c     1,2,3 antenna (2 soft).
      call DAK(s12,s23,s13,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s12t4s2 =   x*s14+  y*s24+  z*s34
      s23t4s2 = omx*s14+omy*s24+omz*s34

c     2,3,4 antenna (3 soft).
      call DAK(s23,s34,s24,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s23t1s3 =   x*s12+  y*s13+  z*s14
      s34t1s3 = omx*s12+omy*s13+omz*s14

c     3,4,1 antenna (4 soft).
      call DAK(s34,s14,s13,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s34t2s4 =   x*s23+  y*s24+  z*s12
      s14t2s4 = omx*s23+omy*s24+omz*s12

c     4,1,2 antenna (1 soft).
      call DAK(s14,s12,s24,x,y,z)
      omx=1d0-x
      omy=1d0-y
      omz=1d0-z
      s14t3s1 =   x*s34+  y*s13+  z*s23
      s12t3s1 = omx*s34+omy*s13+omz*s23

      F40BFF = - 8.D0
     &  - 2.D0*s12**(-2)*s123**(-2)*s13**3*s34
     &  - 2.D0*s12**(-2)*s123**(-2)*s13**3*s14
     &  + 4.D0*s12**(-2)*s123**(-1)*s124**(-1)*s13*s14*s34**2
     &  + 4.D0*s12**(-2)*s123**(-1)*s124**(-1)*s13*s14**2*s34
     &  + 4.D0*s12**(-2)*s123**(-1)*s124**(-1)*s13**2*s14*s34
     &  - 4.D0*s12**(-2)*s123**(-1)*s13*s34**2
     &  - 4.D0*s12**(-2)*s123**(-1)*s13*s14*s34
     &  + 2.D0*s12**(-2)*s123**(-1)*s13**2*s34
     &  + 6.D0*s12**(-2)*s123**(-1)*s13**2*s14
     &  - 2.D0*s12**(-2)*s123**(-1)*s13**3
     &  - 2.D0*s12**(-2)*s124**(-2)*s14**2*s34**2
     &  - 2.D0*s12**(-2)*s124**(-2)*s14**3*s34
     &  - 4.D0*s12**(-2)*s124**(-2)*s13*s14**2*s34
     &  - 2.D0*s12**(-2)*s124**(-2)*s13*s14**3
     &
      F40BFF = F40BFF - 2.D0*s12**(-2)*s124**(-2)*s13**2*s14**2
     &  - 2.D0*s12**(-2)*s124**(-1)*s14**2*s34
     &  - 2.D0*s12**(-2)*s124**(-1)*s14**3
     &  + 4.D0*s12**(-2)*s124**(-1)*s13*s14*s34
     &  + 2.D0*s12**(-2)*s124**(-1)*s13*s14**2
     &  + 4.D0*s12**(-2)*s124**(-1)*s13**2*s14
     &  + 2.D0*s12**(-2)*s34**2
     &  + 4.D0*s12**(-2)*s14*s34
     &  + 2.D0*s12**(-2)*s14**2
     &  - 4.D0*s12**(-2)*s13*s34
     &  - 4.D0*s12**(-2)*s13*s14
     &  - 2.D0*s12**(-2)*s24*s123**(-2)*s13**3
     &  + 4.D0*s12**(-2)*s24*s123**(-1)*s124**(-1)*s13*s34**2
     &  + 4.D0*s12**(-2)*s24*s123**(-1)*s124**(-1)*s13*s14*s34
     &  + 2.D0*s12**(-2)*s24*s123**(-1)*s13**2
     &
      F40BFF = F40BFF - 2.D0*s12**(-2)*s24*s124**(-2)*s14**2*s34
     &  - 2.D0*s12**(-2)*s24*s124**(-2)*s13*s14**2
     &  - 4.D0*s12**(-2)*s24*s124**(-1)*s34**2
     &  - 2.D0*s12**(-2)*s24*s124**(-1)*s14**2
     &  + 4.D0*s12**(-2)*s24*s124**(-1)*s13*s14
     &  - 4.D0*s12**(-2)*s24*s34
     &  - 4.D0*s12**(-2)*s24*s13
     &  + 2.D0*s12**(-2)*s24**2*s124**(-2)*s34**2
     &  + 4.D0*s12**(-2)*s24**2*s124**(-2)*s13*s34
     &  + 2.D0*s12**(-2)*s24**2*s124**(-2)*s13**2
     &  + 4.D0*s12**(-2)*s24**2*s124**(-1)*s34
     &  + 4.D0*s12**(-2)*s24**2*s124**(-1)*s13
     &  - 2.D0*s12**(-2)*s23*s123**(-2)*s13**2*s34
     &  - 2.D0*s12**(-2)*s23*s123**(-2)*s13**2*s14
     &  + 4.D0*s12**(-2)*s23*s123**(-1)*s124**(-1)*s13*s14*s34
     &
      F40BFF = F40BFF + 4.D0*s12**(-2)*s23*s123**(-1)*s13*s14
     &  - 2.D0*s12**(-2)*s23*s123**(-1)*s13**2
     &  - 4.D0*s12**(-2)*s23*s124**(-2)*s14**2*s34
     &  - 2.D0*s12**(-2)*s23*s124**(-2)*s14**3
     &  - 4.D0*s12**(-2)*s23*s124**(-2)*s13*s14**2
     &  - 2.D0*s12**(-2)*s23*s124**(-1)*s14**2
     &  + 4.D0*s12**(-2)*s23*s124**(-1)*s13*s14
     &  + 4.D0*s12**(-2)*s23*s34
     &  + 4.D0*s12**(-2)*s23*s14
     &  - 2.D0*s12**(-2)*s23*s24*s123**(-2)*s13**2
     &  - 2.D0*s12**(-2)*s23*s24*s124**(-2)*s14**2
     &  - 8.D0*s12**(-2)*s23*s24*s124**(-1)*s34
     &  - 4.D0*s12**(-2)*s23*s24*s124**(-1)*s13
     &  - 4.D0*s12**(-2)*s23*s24
     &  + 4.D0*s12**(-2)*s23*s24**2*s124**(-2)*s34
     &
      F40BFF = F40BFF + 4.D0*s12**(-2)*s23*s24**2*s124**(-2)*s13
     &  + 4.D0*s12**(-2)*s23*s24**2*s124**(-1)
     &  - 2.D0*s12**(-2)*s23**2*s124**(-2)*s14**2
     &  + 2.D0*s12**(-2)*s23**2
     &  - 4.D0*s12**(-2)*s23**2*s24*s124**(-1)
     &  + 2.D0*s12**(-2)*s23**2*s24**2*s124**(-2)
     &  - s12**(-1)*s23**(-1)*s234**(-1)*s13*s14**2
     &  - s12**(-1)*s23**(-1)*s234**(-1)*s13**3
     &  + 2.D0*s12**(-1)*s23**(-1)*s23t4s2**(-1)*s13*s123t**2
     &  + 2.D0*s12**(-1)*s23**(-1)*s13*s123t
     &  - 2.D0*s12**(-1)*s23**(-1)*s13*s14
     &  - s12**(-1)*s23**(-1)*s13*s14**2*s34**(-1)
     &  - 2.D0*s12**(-1)*s23**(-1)*s13**2
     &  - s12**(-1)*s23**(-1)*s13**3*s34**(-1)
     &  + 2.D0*s12**(-1)*s23**(-1)*s12t4s2*s13
     &
      F40BFF = F40BFF + 2.D0*s12**(-1)*s23**(-1)*s12t4s2**2*
     & s23t4s2**(-1)*s13
     &  - s12**(-1)*s23**(-1)*s24*s234**(-1)*s13*s14
     &  - s12**(-1)*s23**(-1)*s24*s13
     &  - s12**(-1)*s23**(-1)*s24*s13*s14*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s123**(-2)*s13**2*s123t
     &  - 25.D0/6.D0*s12**(-1)*s123**(-2)*s13**2*s34
     &  - 25.D0/6.D0*s12**(-1)*s123**(-2)*s13**2*s14
     &  - 1.D0/6.D0*s12**(-1)*s123**(-2)*s13**3
     &  + 1.D0/4.D0*s12**(-1)*s123**(-2)*s12t4s2*s13**2
     &  + 4.D0*s12**(-1)*s123**(-1)*s124**(-1)*s14*s34**2
     &  + 4.D0*s12**(-1)*s123**(-1)*s124**(-1)*s14**2*s34
     &  + 2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s14**3
     &  + 4.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13*s34**2
     &  + 4.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13*s14*s34
     &
      F40BFF = F40BFF - 2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13*s14**2
     &  - 4.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13**2*s34
     &  - 2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13**2*s14
     &  + 2.D0*s12**(-1)*s123**(-1)*s124**(-1)*s13**3
     &  - 4.D0*s12**(-1)*s123**(-1)*s34**2
     &  - 4.D0*s12**(-1)*s123**(-1)*s14*s34
     &  - 2.D0*s12**(-1)*s123**(-1)*s14**2
     &  + s12**(-1)*s123**(-1)*s13*s14**(-1)*s34**2
     &  + 3.D0*s12**(-1)*s123**(-1)*s13*s34
     &  + 4.D0*s12**(-1)*s123**(-1)*s13*s14
     &  - s12**(-1)*s123**(-1)*s13*s14**2*s34**(-1)
     &  + 2.D0*s12**(-1)*s123**(-1)*s13**2*s14**(-1)*s34
     &  - 9.D0*s12**(-1)*s123**(-1)*s13**2
     &  - 2.D0*s12**(-1)*s123**(-1)*s13**2*s14*s34**(-1)
     &  + 2.D0*s12**(-1)*s123**(-1)*s13**3*s14**(-1)
     &
      F40BFF = F40BFF + s12**(-1)*s124**(-2)*s12t3s1**(-1)*s14**2*
     & s124t**2
     &  - s12**(-1)*s124**(-2)*s12t3s1**(-1)*s14**2*s34*s124t
     &  - s12**(-1)*s124**(-2)*s12t3s1**(-1)*s14**3*s124t
     &  - s12**(-1)*s124**(-2)*s12t3s1**(-1)*s13*s14**2*s124t
     &  - 2.D0*s12**(-1)*s124**(-2)*s14*s34**2
     &  + 1.D0/2.D0*s12**(-1)*s124**(-2)*s14**2*s124t
     &  - 3.D0/2.D0*s12**(-1)*s124**(-2)*s14**2*s34
     &  + 5.D0/2.D0*s12**(-1)*s124**(-2)*s14**3
     &  - 4.D0*s12**(-1)*s124**(-2)*s13*s14*s34
     &  - 3.D0/2.D0*s12**(-1)*s124**(-2)*s13*s14**2
     &  - 2.D0*s12**(-1)*s124**(-2)*s13**2*s14
     &  - s12**(-1)*s124**(-2)*s12t3s1*s14**2*s34*s124t**(-1)
     &  - s12**(-1)*s124**(-2)*s12t3s1*s14**3*s124t**(-1)
     &  - s12**(-1)*s124**(-2)*s12t3s1*s13*s14**2*s124t**(-1)
     &
      F40BFF = F40BFF + s12**(-1)*s124**(-2)*s14t3s1*s12t3s1**(-1)*
     & s14**2*s124t
     &  + s12**(-1)*s124**(-2)*s14t3s1*s12t3s1*s14**2*s124t**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3*s34*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3*s14*s34**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**3*s14*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**4*s34**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s234**(-1)*s13**4*(s12+s23)**(-1)
     &  - 7.D0/2.D0*s12**(-1)*s124**(-1)*s34**2
     &  + 3.D0/2.D0*s12**(-1)*s124**(-1)*s14*s34
     &  - 2.D0*s12**(-1)*s124**(-1)*s14**2
     &  + 3.D0*s12**(-1)*s124**(-1)*s13*s34
     &
      F40BFF = F40BFF + s12**(-1)*s124**(-1)*s13*s34**2*(s12+s23)**(-1)
     &  + 11.D0/2.D0*s12**(-1)*s124**(-1)*s13*s14
     &  + s12**(-1)*s124**(-1)*s13*s14*s34*(s12+s23)**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s124**(-1)*s13**2
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s13**2*s34*s134**(-1)
     &  + 3.D0*s12**(-1)*s124**(-1)*s13**2*s34*(s12+s23)**(-1)
     &  + 4.D0*s12**(-1)*s124**(-1)*s13**2*s14*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s13**2*s14*s134**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s13**2*s14*(s12+s23)**(-1)
     &  + 3.D0*s12**(-1)*s124**(-1)*s13**3*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s124**(-1)*s13**3*s134**(-1)
     &  + 2.D0*s12**(-1)*s124**(-1)*s13**3*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s234**(-1)*s14*s34
     &  - s12**(-1)*s234**(-1)*s14**2
     &  - 2.D0*s12**(-1)*s234**(-1)*s13*s34
     &
      F40BFF = F40BFF + s12**(-1)*s234**(-1)*s13*s14*s34*
     & (s12+s23)**(-1)
     &  + 3.D0*s12**(-1)*s234**(-1)*s13*s14**2*s34**(-1)
     &  + s12**(-1)*s234**(-1)*s13*s14**2*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s234**(-1)*s13**2
     &  + 2.D0*s12**(-1)*s234**(-1)*s13**2*s34*(s12+s23)**(-1)
     &  + 6.D0*s12**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  + 3.D0*s12**(-1)*s234**(-1)*s13**2*s14*(s12+s23)**(-1)
     &  + 3.D0*s12**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 2.D0*s12**(-1)*s234**(-1)*s13**3*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s12t4s2**(-1)*s23t4s2*s13*(s12+s23)**(-1)*
     & s123t
     &  - 2.D0*s12**(-1)*s12t4s2**(-1)*s23t4s2*s13*s34*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s12t4s2**(-1)*s23t4s2*s13*s14*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s12t4s2**(-1)*s23t4s2*s13**2*(s12+s23)**(-1)
     &
      F40BFF = F40BFF - 1.D0/2.D0*s12**(-1)*s14**(-1)*s34**2
     &  - 15.D0/2.D0*s12**(-1)*s34
     &  + s12**(-1)*s14**2*s34**(-1)
     &  - s12**(-1)*s13*s14**(-1)*s34
     &  + 1.D0/2.D0*s12**(-1)*s13
     &  + 16.D0/3.D0*s12**(-1)*s13*s34*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13*s34*(s12+s14)**(-1)
     &  + s12**(-1)*s13*s34**2*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 7.D0*s12**(-1)*s13*s14*s34**(-1)
     &  + 19.D0/3.D0*s12**(-1)*s13*s14*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13*s14*(s12+s14)**(-1)
     &  + s12**(-1)*s13*s14*s34*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + s12**(-1)*s13*s14**2*s34**(-1)*(s12+s23)**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s13**2*s14**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s13**2*s14**(-1)*s34*s134**(-1)
     &
      F40BFF = F40BFF - 2.D0*s12**(-1)*s13**2*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s12**(-1)*s13**2*(s14+s34)**(-1)
     &  + 22.D0/3.D0*s12**(-1)*s13**2*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13**2*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**2*s34*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 3.D0*s12**(-1)*s13**2*s34*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**2*s14*s34**(-1)*(s14+s34)**(-1)
     &  + 3.D0*s12**(-1)*s13**2*s14*s34**(-1)*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13**2*s14*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**2*s14*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  - s12**(-1)*s13**3*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s13**3*s14**(-1)*s134**(-1)
     &  + 2.D0*s12**(-1)*s13**3*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*s34**(-1)*(s12+s23)**(-1)
     &
      F40BFF = F40BFF + 2.D0*s12**(-1)*s13**3*(s14+s34)**(-1)*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*s34*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*s14*s34**(-1)*(s14+s34)**(-1)*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13**3*s14*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s13**4*s34**(-1)*(s14+s34)**(-1)*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s13**4*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s12t4s2*s23t4s2**(-1)*s13*(s12+s23)**(-1)*
     & s123t
     &
      F40BFF = F40BFF - 2.D0*s12**(-1)*s12t4s2*s23t4s2**(-1)*s13*s34*
     & (s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s12t4s2*s23t4s2**(-1)*s13*s14*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s12t4s2*s23t4s2**(-1)*s13**2*(s12+s23)**(-1)
     &  - 25.D0/6.D0*s12**(-1)*s24*s123**(-2)*s13**2
     &  + 4.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s34**2
     &  + 2.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s14*s34
     &  + 2.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s14**2
     &  + 4.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s13*s34
     &  - 4.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s13*s14
     &  + 2.D0*s12**(-1)*s24*s123**(-1)*s124**(-1)*s13**2
     &  + 2.D0*s12**(-1)*s24*s123**(-1)*s34
     &  + s12**(-1)*s24*s123**(-1)*s13*s14**(-1)*s34
     &  + 8.D0*s12**(-1)*s24*s123**(-1)*s13
     &  + s12**(-1)*s24*s123**(-1)*s13**2*s14**(-1)
     &
      F40BFF = F40BFF - 2.D0*s12**(-1)*s24*s123**(-1)*s13**2*s34**(-1)
     &  - s12**(-1)*s24*s124**(-2)*s12t3s1**(-1)*s14**2*s124t
     &  + 2.D0*s12**(-1)*s24*s124**(-2)*s34**2
     &  + 5.D0/2.D0*s12**(-1)*s24*s124**(-2)*s14**2
     &  + 4.D0*s12**(-1)*s24*s124**(-2)*s13*s34
     &  + 2.D0*s12**(-1)*s24*s124**(-2)*s13**2
     &  - s12**(-1)*s24*s124**(-2)*s12t3s1*s14**2*s124t**(-1)
     &  + 3.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13*s34
     &  + 3.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13*s14
     &  - s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**2
     &  - 4.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  - 2.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 2.D0*s12**(-1)*s24*s124**(-1)*s234**(-1)*s13**3*
     & (s12+s23)**(-1)
     &  + 3.D0*s12**(-1)*s24*s124**(-1)*s34
     &
      F40BFF = F40BFF + 3.D0/2.D0*s12**(-1)*s24*s124**(-1)*s14
     &  + 4.D0*s12**(-1)*s24*s124**(-1)*s13
     &  + 2.D0*s12**(-1)*s24*s124**(-1)*s13*s34*(s12+s23)**(-1)
     &  - 3.D0*s12**(-1)*s24*s124**(-1)*s13*s14*s34**(-1)
     &  + s12**(-1)*s24*s124**(-1)*s13*s14*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s24*s124**(-1)*s13**2*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s24*s124**(-1)*s13**2*s134**(-1)
     &  + 3.D0*s12**(-1)*s24*s124**(-1)*s13**2*(s12+s23)**(-1)
     &  + s12**(-1)*s24*s234**(-1)*s34
     &  - 2.D0*s12**(-1)*s24*s234**(-1)*s14
     &  - s12**(-1)*s24*s234**(-1)*s14**2*s34**(-1)
     &  - 4.D0*s12**(-1)*s24*s234**(-1)*s13
     &  + s12**(-1)*s24*s234**(-1)*s13*s34*(s12+s23)**(-1)
     &  - s12**(-1)*s24*s234**(-1)*s13*s14*s34**(-1)
     &  + 2.D0*s12**(-1)*s24*s234**(-1)*s13*s14*(s12+s23)**(-1)
     &
      F40BFF = F40BFF + 2.D0*s12**(-1)*s24*s234**(-1)*s13**2*s34**(-1)
     &  + 3.D0*s12**(-1)*s24*s234**(-1)*s13**2*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s24*s12t4s2**(-1)*s23t4s2*s13*(s12+s23)**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24*s14**(-1)*s34
     &  - 8.D0*s12**(-1)*s24
     &  - s12**(-1)*s24*s14*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24*s13*s14**(-1)
     &  + 8.D0*s12**(-1)*s24*s13*s34**(-1)
     &  - s12**(-1)*s24*s13*s134**(-1)
     &  + 16.D0/3.D0*s12**(-1)*s24*s13*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13*(s12+s14)**(-1)
     &  + s12**(-1)*s24*s13*s34*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + s12**(-1)*s24*s13*s14*s34**(-1)*(s12+s23)**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s24*s13**2*s14**(-1)*s134**(-1)
     &  - 2.D0*s12**(-1)*s24*s13**2*s34**(-1)*s134**(-1)
     &
      F40BFF = F40BFF + 2.D0*s12**(-1)*s24*s13**2*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13**2*s34**(-1)*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13**2*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13**2*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13**3*s34**(-1)*(s14+s34)**(-1)*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s24*s13**3*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s12+s14)**(-1)
     &  - 2.D0*s12**(-1)*s24*s12t4s2*s23t4s2**(-1)*s13*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s24**2*s123**(-1)*s124**(-1)*s34
     &  + s12**(-1)*s24**2*s123**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s24**2*s124**(-2)*s12t3s1**(-1)*s124t**2
     &  - s12**(-1)*s24**2*s124**(-2)*s12t3s1**(-1)*s34*s124t
     &  - s12**(-1)*s24**2*s124**(-2)*s12t3s1**(-1)*s14*s124t
     &
      F40BFF = F40BFF - s12**(-1)*s24**2*s124**(-2)*s12t3s1**(-1)*s13*
     & s124t
     &  + 1.D0/2.D0*s12**(-1)*s24**2*s124**(-2)*s124t
     &  + 9.D0/2.D0*s12**(-1)*s24**2*s124**(-2)*s34
     &  + 5.D0/2.D0*s12**(-1)*s24**2*s124**(-2)*s14
     &  + 9.D0/2.D0*s12**(-1)*s24**2*s124**(-2)*s13
     &  - s12**(-1)*s24**2*s124**(-2)*s12t3s1*s34*s124t**(-1)
     &  - s12**(-1)*s24**2*s124**(-2)*s12t3s1*s14*s124t**(-1)
     &  - s12**(-1)*s24**2*s124**(-2)*s12t3s1*s13*s124t**(-1)
     &  + s12**(-1)*s24**2*s124**(-2)*s14t3s1*s12t3s1**(-1)*s124t
     &  + s12**(-1)*s24**2*s124**(-2)*s14t3s1*s12t3s1*s124t**(-1)
     &  - s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s34
     &  - s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s14
     &  + 5.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13
     &  + 3.D0*s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &
      F40BFF = F40BFF - s12**(-1)*s24**2*s124**(-1)*s234**(-1)*s13**2*
     & s34**(-1)
     &  + 5.D0/2.D0*s12**(-1)*s24**2*s124**(-1)
     &  + s12**(-1)*s24**2*s124**(-1)*s14*s34**(-1)
     &  - 2.D0*s12**(-1)*s24**2*s124**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s24**2*s124**(-1)*s13*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s24**2*s234**(-1)
     &  - 2.D0*s12**(-1)*s24**2*s234**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s24**2*s234**(-1)*s13*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s24**2*s34**(-1)
     &  + s12**(-1)*s24**2*s13*s34**(-1)*s134**(-1)
     &  - s12**(-1)*s24**3*s124**(-2)*s12t3s1**(-1)*s124t
     &  + 5.D0/2.D0*s12**(-1)*s24**3*s124**(-2)
     &  - s12**(-1)*s24**3*s124**(-2)*s12t3s1*s124t**(-1)
     &  - 2.D0*s12**(-1)*s24**3*s124**(-1)*s234**(-1)
     &
      F40BFF = F40BFF - s12**(-1)*s24**3*s124**(-1)*s234**(-1)*s14*
     & s34**(-1)
     &  + 2.D0*s12**(-1)*s24**3*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s24**3*s124**(-1)*s34**(-1)
     &  + s12**(-1)*s24**3*s234**(-1)*s34**(-1)
     &  - s12**(-1)*s24**4*s124**(-1)*s234**(-1)*s34**(-1)
     &  - 2.D0*s12**(-1)*s23*s123**(-2)*s13*s34
     &  - 2.D0*s12**(-1)*s23*s123**(-2)*s13*s14
     &  - 1.D0/6.D0*s12**(-1)*s23*s123**(-2)*s13**2
     &  + s12**(-1)*s23*s123**(-1)*s124**(-1)*s34**2
     &  + s12**(-1)*s23*s123**(-1)*s124**(-1)*s14*s34
     &  + 2.D0*s12**(-1)*s23*s123**(-1)*s124**(-1)*s14**2
     &  + s12**(-1)*s23*s123**(-1)*s124**(-1)*s13*s34
     &  - 4.D0*s12**(-1)*s23*s123**(-1)*s124**(-1)*s13*s14
     &  + 2.D0*s12**(-1)*s23*s123**(-1)*s124**(-1)*s13**2
     &
      F40BFF = F40BFF + s12**(-1)*s23*s123**(-1)*s12t4s2**(-1)*s23t4s2*
     & s123t
     &  - s12**(-1)*s23*s123**(-1)*s12t4s2**(-1)*s23t4s2*s34
     &  - s12**(-1)*s23*s123**(-1)*s12t4s2**(-1)*s23t4s2*s14
     &  - s12**(-1)*s23*s123**(-1)*s12t4s2**(-1)*s23t4s2*s13
     &  + s12**(-1)*s23*s123**(-1)*s23t4s2**(-1)*s123t**2
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s14**(-1)*s34**2
     &  + s12**(-1)*s23*s123**(-1)*s123t
     &  + 14.D0/3.D0*s12**(-1)*s23*s123**(-1)*s34
     &  + 19.D0/6.D0*s12**(-1)*s23*s123**(-1)*s14
     &  + 1.D0/2.D0*s12**(-1)*s23*s123**(-1)*s13*s14**(-1)*s34
     &  + 13.D0/6.D0*s12**(-1)*s23*s123**(-1)*s13
     &  + s12**(-1)*s23*s123**(-1)*s12t4s2*s23t4s2**(-1)*s123t
     &  - s12**(-1)*s23*s123**(-1)*s12t4s2*s23t4s2**(-1)*s34
     &  - s12**(-1)*s23*s123**(-1)*s12t4s2*s23t4s2**(-1)*s14
     &
      F40BFF = F40BFF - s12**(-1)*s23*s123**(-1)*s12t4s2*s23t4s2**(-1)*
     & s13
     &  + s12**(-1)*s23*s123**(-1)*s12t4s2
     &  + s12**(-1)*s23*s123**(-1)*s12t4s2**2*s23t4s2**(-1)
     &  - s12**(-1)*s23*s124**(-2)*s12t3s1**(-1)*s14**2*s124t
     &  - 4.D0*s12**(-1)*s23*s124**(-2)*s14*s34
     &  - 3.D0/2.D0*s12**(-1)*s23*s124**(-2)*s14**2
     &  - 4.D0*s12**(-1)*s23*s124**(-2)*s13*s14
     &  - s12**(-1)*s23*s124**(-2)*s12t3s1*s14**2*s124t**(-1)
     &  + 2.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 2.D0*s12**(-1)*s23*s124**(-1)*s234**(-1)*s13**3*
     & (s12+s23)**(-1)
     &  - 9.D0/2.D0*s12**(-1)*s23*s124**(-1)*s34
     &  + 9.D0/2.D0*s12**(-1)*s23*s124**(-1)*s13
     &  + s12**(-1)*s23*s124**(-1)*s13*s34*(s12+s23)**(-1)
     &
      F40BFF = F40BFF + 3.D0*s12**(-1)*s23*s124**(-1)*s13*s14*s34**(-1)
     &  + 6.D0*s12**(-1)*s23*s124**(-1)*s13**2*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s124**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s12**(-1)*s23*s124**(-1)*s13**2*(s12+s23)**(-1)
     &  - s12**(-1)*s23*s234**(-1)*s34
     &  - 3.D0*s12**(-1)*s23*s234**(-1)*s14
     &  + s12**(-1)*s23*s234**(-1)*s14**2*s34**(-1)
     &  - 3.D0*s12**(-1)*s23*s234**(-1)*s13
     &  + 3.D0*s12**(-1)*s23*s234**(-1)*s13*s14*s34**(-1)
     &  + s12**(-1)*s23*s234**(-1)*s13*s14*(s12+s23)**(-1)
     &  + 4.D0*s12**(-1)*s23*s234**(-1)*s13**2*s34**(-1)
     &  + 2.D0*s12**(-1)*s23*s234**(-1)*s13**2*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s23*s12t4s2**(-1)*s23t4s2*s13*(s12+s23)**(-1)
     &  - s12**(-1)*s23*s14**(-1)*s34
     &  - 5.D0/2.D0*s12**(-1)*s23
     &
      F40BFF = F40BFF + 4.D0*s12**(-1)*s23*s14*s34**(-1)
     &  + s12**(-1)*s23*s14*s134**(-1)
     &  - s12**(-1)*s23*s13*s14**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s13*s14**(-1)*s34*s134**(-1)
     &  + 7.D0*s12**(-1)*s23*s13*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s23*s13*s134**(-1)
     &  + s12**(-1)*s23*s13*(s14+s34)**(-1)
     &  + 16.D0/3.D0*s12**(-1)*s23*s13*(s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s23*s13*(s12+s14)**(-1)
     &  + s12**(-1)*s23*s13*s34*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + s12**(-1)*s23*s13*s34*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + s12**(-1)*s23*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &  + s12**(-1)*s23*s13*s14*s34**(-1)*(s12+s23)**(-1)
     &  + s12**(-1)*s23*s13*s14*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  - 2.D0*s12**(-1)*s23*s13**2*s34**(-1)*s134**(-1)
     &
      F40BFF = F40BFF + 3.D0*s12**(-1)*s23*s13**2*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 2.D0*s12**(-1)*s23*s13**2*s34**(-1)*(s12+s23)**(-1)
     &  + 3.D0*s12**(-1)*s23*s13**2*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s23*s13**2*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s12**(-1)*s23*s13**3*s34**(-1)*(s14+s34)**(-1)*
     & (s12+s23)**(-1)
     &  + 2.D0*s12**(-1)*s23*s13**3*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s12+s14)**(-1)
     &  - 2.D0*s12**(-1)*s23*s12t4s2*s23t4s2**(-1)*s13*(s12+s23)**(-1)
     &  - 2.D0*s12**(-1)*s23*s24*s123**(-2)*s13
     &  - s12**(-1)*s23*s24*s123**(-1)*s124**(-1)*s34
     &  - s12**(-1)*s23*s24*s123**(-1)*s12t4s2**(-1)*s23t4s2
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s123**(-1)*s14**(-1)*s34
     &  + 19.D0/6.D0*s12**(-1)*s23*s24*s123**(-1)
     &
      F40BFF = F40BFF - s12**(-1)*s23*s24*s123**(-1)*s12t4s2*
     & s23t4s2**(-1)
     &  + 4.D0*s12**(-1)*s23*s24*s124**(-2)*s34
     &  + 4.D0*s12**(-1)*s23*s24*s124**(-2)*s13
     &  + s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s34
     &  + s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s14
     &  + 4.D0*s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s13
     &  - 4.D0*s12**(-1)*s23*s24*s124**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  - 3.D0/2.D0*s12**(-1)*s23*s24*s124**(-1)
     &  - s12**(-1)*s23*s24*s124**(-1)*s14*s34**(-1)
     &  - s12**(-1)*s23*s24*s124**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s23*s24*s124**(-1)*s13*(s12+s23)**(-1)
     &  - s12**(-1)*s23*s24*s234**(-1)*s14*s34**(-1)
     &  - 3.D0*s12**(-1)*s23*s24*s234**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s23*s24*s234**(-1)*s13*(s12+s23)**(-1)
     &
      F40BFF = F40BFF - 1.D0/2.D0*s12**(-1)*s23*s24*s14**(-1)
     &  - s12**(-1)*s23*s24*s34**(-1)
     &  + s12**(-1)*s23*s24*s134**(-1)
     &  - s12**(-1)*s23*s24*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23*s24*s13*s14**(-1)*s134**(-1)
     &  + s12**(-1)*s23*s24*s13*s34**(-1)*(s14+s34)**(-1)
     &  + s12**(-1)*s23*s24*s13*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  - s12**(-1)*s23*s24**2*s124**(-2)*s12t3s1**(-1)*s124t
     &  + 9.D0/2.D0*s12**(-1)*s23*s24**2*s124**(-2)
     &  - s12**(-1)*s23*s24**2*s124**(-2)*s12t3s1*s124t**(-1)
     &  + 3.D0*s12**(-1)*s23*s24**2*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  + s12**(-1)*s23*s24**2*s234**(-1)*s34**(-1)
     &  - s12**(-1)*s23*s24**3*s124**(-1)*s234**(-1)*s34**(-1)
     &  + 1.D0/4.D0*s12**(-1)*s23**2*s123**(-2)*s123t
     &  - 1.D0/6.D0*s12**(-1)*s23**2*s123**(-2)*s34
     &
      F40BFF = F40BFF - 1.D0/6.D0*s12**(-1)*s23**2*s123**(-2)*s14
     &  - 1.D0/6.D0*s12**(-1)*s23**2*s123**(-2)*s13
     &  + 1.D0/4.D0*s12**(-1)*s23**2*s123**(-2)*s12t4s2
     &  - s12**(-1)*s23**2*s123**(-1)*s124**(-1)*s34
     &  - s12**(-1)*s23**2*s123**(-1)*s12t4s2**(-1)*s23t4s2
     &  + s12**(-1)*s23**2*s123**(-1)*s14**(-1)*s34
     &  + 8.D0/3.D0*s12**(-1)*s23**2*s123**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s123**(-1)*s13*s14**(-1)
     &  - s12**(-1)*s23**2*s123**(-1)*s12t4s2*s23t4s2**(-1)
     &  - 2.D0*s12**(-1)*s23**2*s124**(-2)*s14
     &  - 3.D0*s12**(-1)*s23**2*s124**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s34*s134**(-1)
     &  + s12**(-1)*s23**2*s124**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s14*s134**(-1)
     &  + 3.D0*s12**(-1)*s23**2*s124**(-1)*s13*s34**(-1)
     &
      F40BFF = F40BFF + 1.D0/2.D0*s12**(-1)*s23**2*s124**(-1)*s13*
     & s134**(-1)
     &  - s12**(-1)*s23**2*s234**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s14**(-1)
     &  - s12**(-1)*s23**2*s14**(-1)*s34*s134**(-1)
     &  + s12**(-1)*s23**2*s34**(-1)
     &  - 2.D0*s12**(-1)*s23**2*s134**(-1)
     &  - s12**(-1)*s23**2*s13*s14**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**(-1)*s23**2*s13*s14**(-1)*s134**(-1)
     &  - s12**(-1)*s23**2*s13*s34**(-1)*s134**(-1)
     &  + s12**(-1)*s23**2*s13*s34**(-1)*(s14+s34)**(-1)
     &  + s12**(-1)*s23**2*s13*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  - 1.D0/6.D0*s12**(-1)*s23**2*s24*s123**(-2)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s24*s123**(-1)*s14**(-1)
     &  + 2.D0*s12**(-1)*s23**2*s24*s124**(-2)
     &
      F40BFF = F40BFF + s12**(-1)*s23**2*s24*s124**(-1)*s234**(-1)
     &  - s12**(-1)*s23**2*s24*s124**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**2*s24*s124**(-1)*s134**(-1)
     &  - s12**(-1)*s23**2*s24*s14**(-1)*s134**(-1)
     &  - 1.D0/6.D0*s12**(-1)*s23**3*s123**(-2)
     &  + 1.D0/2.D0*s12**(-1)*s23**3*s123**(-1)*s14**(-1)
     &  + s12**(-1)*s23**3*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &  + s12**(-1)*s23**3*s123**(-1)*s134**(-1)
     &  + s12**(-1)*s23**3*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**(-1)*s23**3*s124**(-1)*s134**(-1)
     &  - s12**(-1)*s23**3*s14**(-1)*s134**(-1)
     &  + s12**(-1)*s23**3*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  + s12**(-1)*s23**4*s123**(-1)*s14**(-1)*s134**(-1)
     &  + s23**(-1)*s123**(-1)*s234**(-1)*s13*s14*s34
     &  + s23**(-1)*s123**(-1)*s234**(-1)*s13*s14**2
     &
      F40BFF = F40BFF + s23**(-1)*s123**(-1)*s234**(-1)*s13**2*s14
     &  - s23**(-1)*s123**(-1)*s34**2
     &  + s23**(-1)*s123**(-1)*s34**3*s134**(-1)
     &  - 3.D0*s23**(-1)*s123**(-1)*s14*s34
     &  + 4.D0*s23**(-1)*s123**(-1)*s14*s34**2*s134**(-1)
     &  - 3.D0*s23**(-1)*s123**(-1)*s14**2
     &  + 6.D0*s23**(-1)*s123**(-1)*s14**2*s34*s134**(-1)
     &  - s23**(-1)*s123**(-1)*s14**3*s34**(-1)
     &  + 4.D0*s23**(-1)*s123**(-1)*s14**3*s134**(-1)
     &  + s23**(-1)*s123**(-1)*s14**4*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s123**(-1)*s13*s34
     &  + s23**(-1)*s123**(-1)*s13*s34**2*s134**(-1)
     &  + 3.D0*s23**(-1)*s123**(-1)*s13*s14*s34*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s13*s14**2*s34**(-1)
     &  + 3.D0*s23**(-1)*s123**(-1)*s13*s14**2*s134**(-1)
     &
      F40BFF = F40BFF + s23**(-1)*s123**(-1)*s13*s14**3*s34**(-1)*
     & s134**(-1)
     &  + s23**(-1)*s123**(-1)*s13**2
     &  - 1.D0/2.D0*s23**(-1)*s123**(-1)*s13**3*s34**(-1)
     &  - s23**(-1)*s234**(-2)*s14*s34**2
     &  - s23**(-1)*s234**(-2)*s14**2*s34
     &  - s23**(-1)*s234**(-2)*s13*s34**2
     &  - 2.D0*s23**(-1)*s234**(-2)*s13*s14*s34
     &  - s23**(-1)*s234**(-2)*s13**2*s34
     &  - s23**(-1)*s234**(-1)*s34**2
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s34**3*s134**(-1)
     &  - s23**(-1)*s234**(-1)*s14*s34
     &  + 3.D0/2.D0*s23**(-1)*s234**(-1)*s14*s34**2*s134**(-1)
     &  + s23**(-1)*s234**(-1)*s14**2
     &  + 3.D0/2.D0*s23**(-1)*s234**(-1)*s14**2*s34*s134**(-1)
     &
      F40BFF = F40BFF + 1.D0/2.D0*s23**(-1)*s234**(-1)*s14**3*
     & s134**(-1)
     &  + s23**(-1)*s234**(-1)*s13*s34
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s13*s34**2*s134**(-1)
     &  + 2.D0*s23**(-1)*s234**(-1)*s13*s14
     &  + s23**(-1)*s234**(-1)*s13*s14*s34*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s234**(-1)*s13*s14**2*s134**(-1)
     &  - 2.D0*s23**(-1)*s234**(-1)*s13**2
     &  + s23**(-1)*s234**(-1)*s13**2*s14*s134**(-1)
     &  - s23**(-1)*s234**(-1)*s13**3*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s34
     &  + 1.D0/2.D0*s23**(-1)*s34**2*s134**(-1)
     &  + s23**(-1)*s14
     &  + 3.D0/2.D0*s23**(-1)*s14*s34*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s14**2*s34**(-1)
     &
      F40BFF = F40BFF + 3.D0/2.D0*s23**(-1)*s14**2*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  - 3.D0*s23**(-1)*s13
     &  + 1.D0/2.D0*s23**(-1)*s13*s34*s134**(-1)
     &  - s23**(-1)*s13*s14*s34**(-1)
     &  + s23**(-1)*s13*s14*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s13*s14**2*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s13**2*s34**(-1)
     &  + s23**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s23**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  + s23**(-1)*s24*s123**(-1)*s234**(-1)*s13*s14
     &  - s23**(-1)*s24*s123**(-1)*s34
     &  + s23**(-1)*s24*s123**(-1)*s34**2*s134**(-1)
     &  - 2.D0*s23**(-1)*s24*s123**(-1)*s14
     &  + 3.D0*s23**(-1)*s24*s123**(-1)*s14*s34*s134**(-1)
     &
      F40BFF = F40BFF - s23**(-1)*s24*s123**(-1)*s14**2*s34**(-1)
     &  + 3.D0*s23**(-1)*s24*s123**(-1)*s14**2*s134**(-1)
     &  + s23**(-1)*s24*s123**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13
     &  + 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13*s14*s34**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s123**(-1)*s13**2*s34**(-1)
     &  - s23**(-1)*s24*s234**(-2)*s14*s34
     &  - s23**(-1)*s24*s234**(-2)*s14**2
     &  - s23**(-1)*s24*s234**(-2)*s13*s34
     &  - 2.D0*s23**(-1)*s24*s234**(-2)*s13*s14
     &  - s23**(-1)*s24*s234**(-2)*s13**2
     &  - s23**(-1)*s24*s234**(-1)*s34
     &  + 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s34**2*s134**(-1)
     &  - 2.D0*s23**(-1)*s24*s234**(-1)*s14
     &  + s23**(-1)*s24*s234**(-1)*s14*s34*s134**(-1)
     &
      F40BFF = F40BFF + 1.D0/2.D0*s23**(-1)*s24*s234**(-1)*s14**2*
     & s134**(-1)
     &  + s23**(-1)*s24*s234**(-1)*s13
     &  - s23**(-1)*s24*s234**(-1)*s13*s14*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24
     &  + 1.D0/2.D0*s23**(-1)*s24*s34*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s14*s34**(-1)
     &  + s23**(-1)*s24*s14*s134**(-1)
     &  + 1.D0/2.D0*s23**(-1)*s24*s14**2*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s23**(-1)*s24*s13*s34**(-1)
     &  + s23**(-1)*s24*s13**2*s34**(-1)*s134**(-1)
     &  - 3.D0*s123**(-2)*s13*s34
     &  - 3.D0*s123**(-2)*s13*s14
     &  - 1.D0/6.D0*s123**(-2)*s13**2
     &  - 1.D0/2.D0*s123**(-1)*s124**(-1)*s14**(-1)*s34**3
     &
      F40BFF = F40BFF + 11.D0/2.D0*s123**(-1)*s124**(-1)*s34**2
     &  + 2.D0*s123**(-1)*s124**(-1)*s14*s34
     &  + 2.D0*s123**(-1)*s124**(-1)*s14**2
     &  - 5.D0/2.D0*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34**2
     &  - 2.D0*s123**(-1)*s124**(-1)*s13*s34
     &  - 4.D0*s123**(-1)*s124**(-1)*s13*s14
     &  - 3.D0*s123**(-1)*s124**(-1)*s13**2*s14**(-1)*s34
     &  + 3.D0*s123**(-1)*s124**(-1)*s13**2
     &  - s123**(-1)*s124**(-1)*s13**3*s14**(-1)
     &  + 1.D0/2.D0*s123**(-1)*s234**(-1)*s34**2
     &  + 3.D0/2.D0*s123**(-1)*s234**(-1)*s14*s34
     &  + 3.D0/2.D0*s123**(-1)*s234**(-1)*s14**2
     &  + 1.D0/2.D0*s123**(-1)*s234**(-1)*s14**3*s34**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s234**(-1)*s13*s34
     &  + s123**(-1)*s234**(-1)*s13*s14
     &
      F40BFF = F40BFF + 1.D0/2.D0*s123**(-1)*s234**(-1)*s13*s14**2*
     & s34**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s234**(-1)*s13**2
     &  + 1.D0/2.D0*s123**(-1)*s234**(-1)*s13**2*s14*s34**(-1)
     &  + 1.D0/2.D0*s123**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s14**(-1)*s34**2
     &  + 3.D0/2.D0*s123**(-1)*s34
     &  + s123**(-1)*s34**2*s134**(-1)
     &  - 3.D0*s123**(-1)*s14
     &  + 3.D0*s123**(-1)*s14*s34*s134**(-1)
     &  - 2.D0*s123**(-1)*s14**2*s34**(-1)
     &  + 3.D0*s123**(-1)*s14**2*s134**(-1)
     &  + s123**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s13*s14**(-1)*s34
     &  - 9.D0/2.D0*s123**(-1)*s13
     &
      F40BFF = F40BFF - 3.D0/2.D0*s123**(-1)*s13*s14*s34**(-1)
     &  + s123**(-1)*s13**2*s14**(-1)
     &  - 1.D0/2.D0*s123**(-1)*s13**2*s34**(-1)
     &  + s124**(-2)*s12t3s1**(-1)*s14*s124t**2
     &  - s124**(-2)*s12t3s1**(-1)*s14*s34*s124t
     &  - 2.D0*s124**(-2)*s12t3s1**(-1)*s14**2*s124t
     &  - s124**(-2)*s12t3s1**(-1)*s13*s14*s124t
     &  - s124**(-2)*s34**2
     &  + 1.D0/2.D0*s124**(-2)*s14*s124t
     &  - 1.D0/2.D0*s124**(-2)*s14*s34
     &  + 5.D0*s124**(-2)*s14**2
     &  - 2.D0*s124**(-2)*s13*s34
     &  - 1.D0/2.D0*s124**(-2)*s13*s14
     &  - s124**(-2)*s13**2
     &  - s124**(-2)*s12t3s1*s14*s34*s124t**(-1)
     &
      F40BFF = F40BFF - 2.D0*s124**(-2)*s12t3s1*s14**2*s124t**(-1)
     &  - s124**(-2)*s12t3s1*s13*s14*s124t**(-1)
     &  + s124**(-2)*s14t3s1*s12t3s1**(-1)*s14*s124t
     &  + s124**(-2)*s14t3s1*s12t3s1*s14*s124t**(-1)
     &  + 2.D0*s124**(-1)*s234**(-1)*s13*s34
     &  + 2.D0*s124**(-1)*s234**(-1)*s13*s14
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**2
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**3*s34**(-1)
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**3*(s14+s34)**(-1)
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**3*(s12+s23)**(-1)
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**3*s14*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 2.D0*s124**(-1)*s234**(-1)*s13**4*s34**(-1)*(s14+s34)**(-1)
     &  + s124**(-1)*s14**(-1)*s34**2
     &  + 3.D0*s124**(-1)*s34
     &
      F40BFF = F40BFF + 1.D0/2.D0*s124**(-1)*s14
     &  + 3.D0*s124**(-1)*s13
     &  - s124**(-1)*s13*s34*s134**(-1)
     &  + s124**(-1)*s13*s34*(s12+s23)**(-1)
     &  - 2.D0*s124**(-1)*s13*s14*s34**(-1)
     &  - s124**(-1)*s13*s14*s134**(-1)
     &  - 2.D0*s124**(-1)*s13**2*s14**(-1)
     &  + 2.D0*s124**(-1)*s13**2*s34**(-1)
     &  - 1.D0/2.D0*s124**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s124**(-1)*s13**2*(s14+s34)**(-1)
     &  + 2.D0*s124**(-1)*s13**2*(s12+s23)**(-1)
     &  + 2.D0*s124**(-1)*s13**2*s14*s34**(-1)*(s14+s34)**(-1)
     &  - s124**(-1)*s13**3*s14**(-1)*s34**(-1)
     &  + 2.D0*s124**(-1)*s13**3*s34**(-1)*(s14+s34)**(-1)
     &  - 2.D0*s234**(-2)*s14*s34
     &
      F40BFF = F40BFF - s234**(-2)*s14**2
     &  - 2.D0*s234**(-2)*s13*s34
     &  - 2.D0*s234**(-2)*s13*s14
     &  - s234**(-2)*s13**2
     &  - 1.D0/2.D0*s234**(-1)*s34
     &  + s234**(-1)*s34**2*s134**(-1)
     &  - 3.D0/2.D0*s234**(-1)*s14
     &  + 5.D0/2.D0*s234**(-1)*s14*s34*s134**(-1)
     &  - 3.D0*s234**(-1)*s14**2*s34**(-1)
     &  + 5.D0/2.D0*s234**(-1)*s14**2*s134**(-1)
     &  + 3.D0*s234**(-1)*s13
     &  + 1.D0/2.D0*s234**(-1)*s13*s34*s134**(-1)
     &  + 9.D0/2.D0*s234**(-1)*s13*s14*s34**(-1)
     &  + s234**(-1)*s13*s14*(s12+s23)**(-1)
     &  - 1.D0/2.D0*s234**(-1)*s13**2*s34**(-1)
     &
      F40BFF = F40BFF + 3.D0*s234**(-1)*s13**2*s134**(-1)
     &  + 2.D0*s234**(-1)*s13**2*(s14+s34)**(-1)
     &  + 2.D0*s234**(-1)*s13**2*(s12+s23)**(-1)
     &  + 2.D0*s234**(-1)*s13**2*s14*s34**(-1)*s134**(-1)
     &  + 2.D0*s234**(-1)*s13**2*s14*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s234**(-1)*s13**3*s34**(-1)*s134**(-1)
     &  + 2.D0*s234**(-1)*s13**3*s34**(-1)*(s14+s34)**(-1)
     &  - 2.D0*s12t4s2**(-1)*s23t4s2*s13*(s12+s23)**(-1)
     &  + s14t2s4**(-1)*s14**(-1)*s34*s134**(-1)*s134t**2
     &  + s14t2s4**(-1)*s14*s34**(-1)*s134**(-1)*s134t**2
     &  + 2.D0*s14t2s4**(-1)*s13*s14**(-1)*s34**(-1)*s134t**2
     &  + s14t2s4**(-1)*s34t2s4*s14*s34**(-1)*s134**(-1)*s134t
     &  - s14t2s4**(-1)*s34t2s4*s14*s134**(-1)
     &  - s14t2s4**(-1)*s34t2s4*s14**2*s34**(-1)*s134**(-1)
     &  + 2.D0*s14t2s4**(-1)*s34t2s4*s13*s34**(-1)*(s14+s34)**(-1)*
     & s134t
     &
      F40BFF = F40BFF - 2.D0*s14t2s4**(-1)*s34t2s4*s13*(s14+s34)**(-1)
     &  - s14t2s4**(-1)*s34t2s4*s13*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s14t2s4**(-1)*s34t2s4*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &  - 2.D0*s14t2s4**(-1)*s34t2s4*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  + s14t2s4**(-1)*s34t2s4**2*s14**(-1)*s34*s134**(-1)
     &  + s14t2s4**(-1)*s34t2s4**2*s14*s34**(-1)*s134**(-1)
     &  + 2.D0*s14t2s4**(-1)*s34t2s4**2*s13*s14**(-1)*s34**(-1)
     &  + s14**(-1)*s34*s134**(-1)*s134t
     &  - s14**(-1)*s34
     &  + 1.D0/2.D0*s34*s134**(-1)
     &  + s14*s34**(-1)*s134**(-1)*s134t
     &  - 7.D0/2.D0*s14*s34**(-1)
     &  + 37.D0/6.D0*s14*s134**(-1)
     &  + 2.D0*s14**2*s34**(-2)
     &  + 1.D0/4.D0*s14**2*s34**(-1)*s134**(-2)*s134t
     &
      F40BFF = F40BFF + 8.D0/3.D0*s14**2*s34**(-1)*s134**(-1)
     &  - 1.D0/6.D0*s14**2*s134**(-2)
     &  - 1.D0/6.D0*s14**3*s34**(-1)*s134**(-2)
     &  + 2.D0*s13*s14**(-1)*s34**(-1)*s134t
     &  - 3.D0*s13*s14**(-1)
     &  + 3.D0/2.D0*s13*s14**(-1)*s34*s134**(-1)
     &  - 1.D0/2.D0*s13*s34**(-1)
     &  - 9.D0/2.D0*s13*s134**(-1)
     &  + 16.D0/3.D0*s13*(s14+s34)**(-1)
     &  + 16.D0/3.D0*s13*(s12+s23)**(-1)
     &  + 2.D0*s13*(s12+s14)**(-1)
     &  + 2.D0*s13*(s23+s34)**(-1)
     &  + s13*s34*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 13.D0/6.D0*s13*s14*s34**(-1)*s134**(-1)
     &  + 16.D0/3.D0*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &
      F40BFF = F40BFF + s13*s14*s34**(-1)*(s12+s23)**(-1)
     &  + 2.D0*s13*s14*s34**(-1)*(s23+s34)**(-1)
     &  + s13*s14*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 1.D0/6.D0*s13*s14**2*s34**(-1)*s134**(-2)
     &  + s13*s14**2*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s13**2*s14**(-1)*s34**(-1)
     &  + s13**2*s14**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s13**2*s34**(-1)*s134**(-2)*s134t
     &  - 9.D0*s13**2*s34**(-1)*s134**(-1)
     &  + 22.D0/3.D0*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s13**2*s34**(-1)*(s12+s23)**(-1)
     &  + 2.D0*s13**2*s34**(-1)*(s23+s34)**(-1)
     &  - 1.D0/6.D0*s13**2*s134**(-2)
     &  + 2.D0*s13**2*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s13**2*(s14+s34)**(-1)*(s23+s34)**(-1)
     &
      F40BFF = F40BFF + 2.D0*s13**2*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s13**2*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s13**2*s14*s34**(-2)*s134**(-1)
     &  - 1.D0/6.D0*s13**2*s14*s34**(-1)*s134**(-2)
     &  + 2.D0*s13**2*s14*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 3.D0*s13**2*s14*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s13**3*s34**(-2)*s134**(-1)
     &  - 1.D0/6.D0*s13**3*s34**(-1)*s134**(-2)
     &  + 2.D0*s13**3*s34**(-1)*(s14+s34)**(-1)*(s12+s23)**(-1)
     &  + 2.D0*s13**3*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s13**3*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s13**3*(s14+s34)**(-1)*(s12+s23)**(-1)*(s12+s14)**(-1)
     &  + 2.D0*s13**3*(s14+s34)**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s13**3*s14*s34**(-1)*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s23+s34)**(-1)
     &
      F40BFF = F40BFF + 2.D0*s13**4*s34**(-1)*(s14+s34)**(-1)*
     & (s12+s23)**(-1)*(s23+s34)**(-1)
     &  + s34t2s4*s14**(-1)*s34*s134**(-1)
     &  + s34t2s4*s14*s34**(-1)*s134**(-1)
     &  + 1.D0/4.D0*s34t2s4*s14**2*s34**(-1)*s134**(-2)
     &  + 2.D0*s34t2s4*s13*s14**(-1)*s34**(-1)
     &  + 1.D0/4.D0*s34t2s4*s13**2*s34**(-1)*s134**(-2)
     &  + s14t2s4*s34t2s4**(-1)*s14*s34**(-1)*s134**(-1)*s134t
     &  - s14t2s4*s34t2s4**(-1)*s14*s134**(-1)
     &  - s14t2s4*s34t2s4**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + 2.D0*s14t2s4*s34t2s4**(-1)*s13*s34**(-1)*(s14+s34)**(-1)*
     & s134t
     &  - 2.D0*s14t2s4*s34t2s4**(-1)*s13*(s14+s34)**(-1)
     &  - s14t2s4*s34t2s4**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s14t2s4*s34t2s4**(-1)*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &
      F40BFF = F40BFF - 2.D0*s14t2s4*s34t2s4**(-1)*s13**2*s34**(-1)*
     & (s14+s34)**(-1)
     &  - 2.D0*s12t4s2*s23t4s2**(-1)*s13*(s12+s23)**(-1)
     &  - 3.D0*s24*s123**(-2)*s13
     &  + 1.D0/2.D0*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  - 1.D0/2.D0*s24*s123**(-1)*s124**(-1)*s34
     &  - 1.D0/2.D0*s24*s123**(-1)*s124**(-1)*s14
     &  - 1.D0/2.D0*s24*s123**(-1)*s124**(-1)*s13
     &  + 1.D0/2.D0*s24*s123**(-1)*s234**(-1)*s34
     &  + s24*s123**(-1)*s234**(-1)*s14
     &  + 1.D0/2.D0*s24*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - s24*s123**(-1)*s234**(-1)*s13
     &  + 1.D0/2.D0*s24*s123**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  + 1.D0/2.D0*s24*s123**(-1)*s14**(-1)*s34
     &  + 4.D0*s24*s123**(-1)
     &
      F40BFF = F40BFF + s24*s123**(-1)*s14*s34**(-1)
     &  - s24*s123**(-1)*s13*s34**(-1)
     &  + s24*s124**(-2)*s12t3s1**(-1)*s124t**2
     &  - s24*s124**(-2)*s12t3s1**(-1)*s34*s124t
     &  - 2.D0*s24*s124**(-2)*s12t3s1**(-1)*s14*s124t
     &  - s24*s124**(-2)*s12t3s1**(-1)*s13*s124t
     &  - s24*s124**(-2)*s14**(-1)*s34**2
     &  + 1.D0/2.D0*s24*s124**(-2)*s124t
     &  + 7.D0/2.D0*s24*s124**(-2)*s34
     &  + 5.D0*s24*s124**(-2)*s14
     &  - 2.D0*s24*s124**(-2)*s13*s14**(-1)*s34
     &  + 7.D0/2.D0*s24*s124**(-2)*s13
     &  - s24*s124**(-2)*s13**2*s14**(-1)
     &  - s24*s124**(-2)*s12t3s1*s34*s124t**(-1)
     &  - 2.D0*s24*s124**(-2)*s12t3s1*s14*s124t**(-1)
     &
      F40BFF = F40BFF - s24*s124**(-2)*s12t3s1*s13*s124t**(-1)
     &  + s24*s124**(-2)*s14t3s1*s12t3s1**(-1)*s124t
     &  + s24*s124**(-2)*s14t3s1*s12t3s1*s124t**(-1)
     &  - 2.D0*s24*s124**(-1)*s234**(-1)*s34
     &  - 2.D0*s24*s124**(-1)*s234**(-1)*s14
     &  + 6.D0*s24*s124**(-1)*s234**(-1)*s13
     &  + 3.D0*s24*s124**(-1)*s234**(-1)*s13*s14*s34**(-1)
     &  - s24*s124**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  + 2.D0*s24*s124**(-1)*s234**(-1)*s13**3*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 4.D0*s24*s124**(-1)
     &  + 2.D0*s24*s124**(-1)*s14*s34**(-1)
     &  + s24*s124**(-1)*s13*s14**(-1)
     &  - 3.D0*s24*s124**(-1)*s13*s34**(-1)
     &  - s24*s124**(-1)*s13*s134**(-1)
     &
      F40BFF = F40BFF + s24*s124**(-1)*s13*(s14+s34)**(-1)
     &  + s24*s124**(-1)*s13*(s12+s23)**(-1)
     &  + s24*s124**(-1)*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &  + 3.D0*s24*s124**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  + s24*s234**(-2)*s34t1s3**(-1)*s234t**2
     &  - s24*s234**(-2)*s34t1s3**(-1)*s34*s234t
     &  - s24*s234**(-2)*s34t1s3**(-1)*s14*s234t
     &  - s24*s234**(-2)*s34t1s3**(-1)*s13*s234t
     &  + s24*s234**(-2)*s34t1s3**(-1)*s23t1s3*s234t
     &  + 1.D0/2.D0*s24*s234**(-2)*s234t
     &  + 5.D0/2.D0*s24*s234**(-2)*s34
     &  + 7.D0/2.D0*s24*s234**(-2)*s14
     &  + 2.D0*s24*s234**(-2)*s14**2*s34**(-1)
     &  + 7.D0/2.D0*s24*s234**(-2)*s13
     &  + 4.D0*s24*s234**(-2)*s13*s14*s34**(-1)
     &
      F40BFF = F40BFF + 2.D0*s24*s234**(-2)*s13**2*s34**(-1)
     &  - s24*s234**(-2)*s34t1s3*s34*s234t**(-1)
     &  - s24*s234**(-2)*s34t1s3*s14*s234t**(-1)
     &  - s24*s234**(-2)*s34t1s3*s13*s234t**(-1)
     &  + s24*s234**(-2)*s34t1s3*s23t1s3*s234t**(-1)
     &  + 4.D0*s24*s234**(-1)
     &  - 1.D0/2.D0*s24*s234**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s24*s234**(-1)*s14*s134**(-1)
     &  - 4.D0*s24*s234**(-1)*s14**2*s34**(-2)
     &  + 5.D0*s24*s234**(-1)*s13*s34**(-1)
     &  - 1.D0/2.D0*s24*s234**(-1)*s13*s134**(-1)
     &  + s24*s234**(-1)*s13*(s14+s34)**(-1)
     &  + s24*s234**(-1)*s13*(s12+s23)**(-1)
     &  - 4.D0*s24*s234**(-1)*s13*s14*s34**(-2)
     &  + s24*s234**(-1)*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &
      F40BFF = F40BFF + 2.D0*s24*s234**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + 3.D0*s24*s234**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  - s24*s14t2s4**(-1)*s34t2s4*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s24*s14t2s4**(-1)*s34t2s4*s13*s34**(-1)*(s14+s34)**(-1)
     &  - 1.D0/2.D0*s24*s14**(-1)
     &  - 9.D0*s24*s34**(-1)
     &  + 4.D0*s24*s134**(-1)
     &  - s24*s34*s134**(-2)
     &  - 4.D0*s24*s14*s34**(-2)
     &  + 19.D0/6.D0*s24*s14*s34**(-1)*s134**(-1)
     &  - s24*s14*s134**(-2)
     &  - 1.D0/6.D0*s24*s14**2*s34**(-1)*s134**(-2)
     &  - s24*s13*s14**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s24*s13*s14**(-1)*s134**(-1)
     &  - 4.D0*s24*s13*s34**(-2)
     &
      F40BFF = F40BFF + 8.D0*s24*s13*s34**(-1)*s134**(-1)
     &  + 16.D0/3.D0*s24*s13*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s24*s13*s34**(-1)*(s23+s34)**(-1)
     &  - 3.D0*s24*s13*s134**(-2)
     &  - 2.D0*s24*s13*s14*s34**(-1)*s134**(-2)
     &  + s24*s13*s14*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s24*s13**2*s34**(-2)*s134**(-1)
     &  - 25.D0/6.D0*s24*s13**2*s34**(-1)*s134**(-2)
     &  + 2.D0*s24*s13**2*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s24*s13**2*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s24*s13**2*s14*s34**(-2)*s134**(-2)
     &  - 2.D0*s24*s13**3*s34**(-2)*s134**(-2)
     &  + 2.D0*s24*s13**3*s34**(-1)*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s23+s34)**(-1)
     &  - s24*s14t2s4*s34t2s4**(-1)*s14*s34**(-1)*s134**(-1)
     &
      F40BFF = F40BFF - 2.D0*s24*s14t2s4*s34t2s4**(-1)*s13*s34**(-1)*
     & (s14+s34)**(-1)
     &  - 1.D0/2.D0*s24**2*s123**(-1)*s124**(-1)
     &  - 2.D0*s24**2*s124**(-2)*s12t3s1**(-1)*s124t
     &  + 5.D0*s24**2*s124**(-2)
     &  - 2.D0*s24**2*s124**(-2)*s12t3s1*s124t**(-1)
     &  - 5.D0*s24**2*s124**(-1)*s234**(-1)
     &  - 2.D0*s24**2*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &  + 4.D0*s24**2*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  + 3.D0*s24**2*s124**(-1)*s34**(-1)
     &  + s24**2*s124**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  + s24**2*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t**2
     &  - 2.D0*s24**2*s234**(-2)*s34t1s3**(-1)*s234t
     &  - s24**2*s234**(-2)*s34t1s3**(-1)*s14*s34**(-1)*s234t
     &  - s24**2*s234**(-2)*s34t1s3**(-1)*s13*s34**(-1)*s234t
     &
      F40BFF = F40BFF + s24**2*s234**(-2)*s34t1s3**(-1)*s23t1s3*
     & s34**(-1)*s234t
     &  + 1.D0/2.D0*s24**2*s234**(-2)*s34**(-1)*s234t
     &  + 5.D0*s24**2*s234**(-2)
     &  + 9.D0/2.D0*s24**2*s234**(-2)*s14*s34**(-1)
     &  + 2.D0*s24**2*s234**(-2)*s14**2*s34**(-2)
     &  + 9.D0/2.D0*s24**2*s234**(-2)*s13*s34**(-1)
     &  + 4.D0*s24**2*s234**(-2)*s13*s14*s34**(-2)
     &  + 2.D0*s24**2*s234**(-2)*s13**2*s34**(-2)
     &  - 2.D0*s24**2*s234**(-2)*s34t1s3*s234t**(-1)
     &  - s24**2*s234**(-2)*s34t1s3*s14*s34**(-1)*s234t**(-1)
     &  - s24**2*s234**(-2)*s34t1s3*s13*s34**(-1)*s234t**(-1)
     &  + s24**2*s234**(-2)*s34t1s3*s23t1s3*s34**(-1)*s234t**(-1)
     &  + 7.D0/2.D0*s24**2*s234**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s24**2*s234**(-1)*s134**(-1)
     &
      F40BFF = F40BFF + 4.D0*s24**2*s234**(-1)*s14*s34**(-2)
     &  + 4.D0*s24**2*s234**(-1)*s13*s34**(-2)
     &  + s24**2*s234**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - 3.D0*s24**3*s124**(-1)*s234**(-1)*s34**(-1)
     &  - s24**3*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  + 5.D0/2.D0*s24**3*s234**(-2)*s34**(-1)
     &  - s24**3*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - s23*s123**(-2)*s34
     &  - s23*s123**(-2)*s14
     &  + 1.D0/2.D0*s23*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  + 3.D0*s23*s123**(-1)*s124**(-1)*s34
     &  + s23*s123**(-1)*s124**(-1)*s14
     &  + s23*s123**(-1)*s124**(-1)*s13*s14**(-1)*s34
     &  + s23*s123**(-1)*s124**(-1)*s13**2*s14**(-1)
     &  + 1.D0/2.D0*s23*s123**(-1)*s234**(-1)*s34
     &
      F40BFF = F40BFF + s23*s123**(-1)*s234**(-1)*s14
     &  + 1.D0/2.D0*s23*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - s23*s123**(-1)*s234**(-1)*s13
     &  + 1.D0/2.D0*s23*s123**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  - s23*s123**(-1)*s12t4s2**(-1)*s23t4s2
     &  + 3.D0*s23*s123**(-1)*s14**(-1)*s34
     &  + 37.D0/6.D0*s23*s123**(-1)
     &  + s23*s123**(-1)*s14*s34**(-1)
     &  + s23*s123**(-1)*s13*s14**(-1)
     &  - s23*s123**(-1)*s12t4s2*s23t4s2**(-1)
     &  - s23*s124**(-2)*s12t3s1**(-1)*s14*s124t
     &  - 2.D0*s23*s124**(-2)*s34
     &  - 1.D0/2.D0*s23*s124**(-2)*s14
     &  - 2.D0*s23*s124**(-2)*s13
     &  - s23*s124**(-2)*s12t3s1*s14*s124t**(-1)
     &
      F40BFF = F40BFF + 2.D0*s23*s124**(-1)*s234**(-1)*s13
     &  + 2.D0*s23*s124**(-1)*s234**(-1)*s13**3*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 3.D0*s23*s124**(-1)*s14**(-1)*s34
     &  - 3.D0/2.D0*s23*s124**(-1)
     &  + s23*s124**(-1)*s34*s134**(-1)
     &  - 2.D0*s23*s124**(-1)*s14*s34**(-1)
     &  + s23*s124**(-1)*s14*s134**(-1)
     &  + 2.D0*s23*s124**(-1)*s13*s14**(-1)
     &  + s23*s124**(-1)*s13*s14**(-1)*s34*s134**(-1)
     &  + s23*s124**(-1)*s13*s134**(-1)
     &  + s23*s124**(-1)*s13*(s14+s34)**(-1)
     &  + s23*s124**(-1)*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &  + s23*s124**(-1)*s13**2*s14**(-1)*s134**(-1)
     &  + 3.D0*s23*s124**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &
      F40BFF = F40BFF + s23*s234**(-2)*s34t1s3**(-1)*s234t**2
     &  - s23*s234**(-2)*s34t1s3**(-1)*s34*s234t
     &  - s23*s234**(-2)*s34t1s3**(-1)*s14*s234t
     &  - s23*s234**(-2)*s34t1s3**(-1)*s13*s234t
     &  + s23*s234**(-2)*s34t1s3**(-1)*s23t1s3*s234t
     &  + 1.D0/2.D0*s23*s234**(-2)*s234t
     &  + 5.D0/2.D0*s23*s234**(-2)*s34
     &  - 1.D0/2.D0*s23*s234**(-2)*s14
     &  - 2.D0*s23*s234**(-2)*s14**2*s34**(-1)
     &  - 1.D0/2.D0*s23*s234**(-2)*s13
     &  - 4.D0*s23*s234**(-2)*s13*s14*s34**(-1)
     &  - 2.D0*s23*s234**(-2)*s13**2*s34**(-1)
     &  - s23*s234**(-2)*s34t1s3*s34*s234t**(-1)
     &  - s23*s234**(-2)*s34t1s3*s14*s234t**(-1)
     &  - s23*s234**(-2)*s34t1s3*s13*s234t**(-1)
     &
      F40BFF = F40BFF + s23*s234**(-2)*s34t1s3*s23t1s3*s234t**(-1)
     &  - 1.D0/2.D0*s23*s234**(-1)
     &  + 1.D0/2.D0*s23*s234**(-1)*s34*s134**(-1)
     &  + s23*s234**(-1)*s14*s134**(-1)
     &  + 11.D0/2.D0*s23*s234**(-1)*s13*s34**(-1)
     &  - 4.D0*s23*s234**(-1)*s13*s134**(-1)
     &  + 4.D0*s23*s234**(-1)*s13*s14*s34**(-2)
     &  - 4.D0*s23*s234**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + 4.D0*s23*s234**(-1)*s13**2*s34**(-2)
     &  - 2.D0*s23*s234**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + 2.D0*s23*s234**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  - s23*s14t2s4**(-1)*s34t2s4*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s23*s14t2s4**(-1)*s34t2s4*s13*s34**(-1)*(s14+s34)**(-1)
     &  + s23*s14**(-1)
     &  - 2.D0*s23*s14**(-1)*s34*s134**(-1)
     &
      F40BFF = F40BFF - s23*s34**(-1)
     &  - 3.D0*s23*s134**(-1)
     &  - s23*s34*s134**(-2)
     &  + 4.D0*s23*s14*s34**(-2)
     &  + 19.D0/6.D0*s23*s14*s34**(-1)*s134**(-1)
     &  - s23*s14*s134**(-2)
     &  - 1.D0/6.D0*s23*s14**2*s34**(-1)*s134**(-2)
     &  - 2.D0*s23*s13*s14**(-1)*s34**(-1)
     &  - 4.D0*s23*s13*s34**(-2)
     &  + 4.D0*s23*s13*s34**(-1)*s134**(-1)
     &  + 19.D0/3.D0*s23*s13*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s23*s13*s34**(-1)*(s23+s34)**(-1)
     &  - 3.D0*s23*s13*s134**(-2)
     &  + s23*s13*(s14+s34)**(-1)*(s12+s14)**(-1)
     &  + 4.D0*s23*s13*s14*s34**(-2)*s134**(-1)
     &
      F40BFF = F40BFF - 2.D0*s23*s13*s14*s34**(-1)*s134**(-2)
     &  + s23*s13*s14*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  + 6.D0*s23*s13**2*s34**(-2)*s134**(-1)
     &  - 25.D0/6.D0*s23*s13**2*s34**(-1)*s134**(-2)
     &  + 2.D0*s23*s13**2*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s23*s13**2*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s23*s13**2*s14*s34**(-2)*s134**(-2)
     &  - 2.D0*s23*s13**3*s34**(-2)*s134**(-2)
     &  + 2.D0*s23*s13**3*s34**(-1)*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s23+s34)**(-1)
     &  - s23*s14t2s4*s34t2s4**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s23*s14t2s4*s34t2s4**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s23*s24*s123**(-2)
     &  - s23*s24*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + 1.D0/2.D0*s23*s24*s123**(-1)*s124**(-1)
     &
      F40BFF = F40BFF - s23*s24*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  + s23*s24*s123**(-1)*s14**(-1)
     &  - s23*s24*s124**(-2)*s12t3s1**(-1)*s124t
     &  - 2.D0*s23*s24*s124**(-2)*s14**(-1)*s34
     &  + 7.D0/2.D0*s23*s24*s124**(-2)
     &  - 2.D0*s23*s24*s124**(-2)*s13*s14**(-1)
     &  - s23*s24*s124**(-2)*s12t3s1*s124t**(-1)
     &  - s23*s24*s124**(-1)*s234**(-1)
     &  + 3.D0*s23*s24*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  - 2.D0*s23*s24*s124**(-1)*s14**(-1)
     &  - s23*s24*s124**(-1)*s34**(-1)
     &  + s23*s24*s124**(-1)*s134**(-1)
     &  - s23*s24*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + s23*s24*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  + 2.D0*s23*s24*s124**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &
      F40BFF = F40BFF - 2.D0*s23*s24*s234**(-2)*s34t1s3**(-1)*s234t
     &  + 5.D0*s23*s24*s234**(-2)
     &  - 2.D0*s23*s24*s234**(-2)*s34t1s3*s234t**(-1)
     &  + 5.D0/2.D0*s23*s24*s234**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s23*s24*s234**(-1)*s134**(-1)
     &  + 4.D0*s23*s24*s234**(-1)*s13*s34**(-2)
     &  - 4.D0*s23*s24*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  + s23*s24*s234**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - 2.D0*s23*s24*s14**(-1)*s134**(-1)
     &  - 2.D0*s23*s24**2*s124**(-1)*s234**(-1)*s34**(-1)
     &  - s23*s24**2*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  + 5.D0/2.D0*s23*s24**2*s234**(-2)*s34**(-1)
     &  - s23*s24**2*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - 1.D0/6.D0*s23**2*s123**(-2)
     &  + 1.D0/2.D0*s23**2*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &
      F40BFF = F40BFF + 5.D0/2.D0*s23**2*s123**(-1)*s124**(-1)
     &  + 1.D0/2.D0*s23**2*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  + 3.D0/2.D0*s23**2*s123**(-1)*s14**(-1)
     &  + 3.D0*s23**2*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 3.D0*s23**2*s123**(-1)*s134**(-1)
     &  + 3.D0*s23**2*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - s23**2*s124**(-2)
     &  + s23**2*s124**(-1)*s14**(-1)
     &  - s23**2*s124**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s23**2*s124**(-1)*s134**(-1)
     &  - s23**2*s124**(-1)*s13*s14**(-1)*s34**(-1)
     &  + s23**2*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  + s23**2*s124**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  + s23**2*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t**2
     &  - 2.D0*s23**2*s234**(-2)*s34t1s3**(-1)*s234t
     &
      F40BFF = F40BFF - s23**2*s234**(-2)*s34t1s3**(-1)*s14*s34**(-1)*
     & s234t
     &  - s23**2*s234**(-2)*s34t1s3**(-1)*s13*s34**(-1)*s234t
     &  + s23**2*s234**(-2)*s34t1s3**(-1)*s23t1s3*s34**(-1)*s234t
     &  + 1.D0/2.D0*s23**2*s234**(-2)*s34**(-1)*s234t
     &  + 5.D0*s23**2*s234**(-2)
     &  - 3.D0/2.D0*s23**2*s234**(-2)*s14*s34**(-1)
     &  - 2.D0*s23**2*s234**(-2)*s14**2*s34**(-2)
     &  - 3.D0/2.D0*s23**2*s234**(-2)*s13*s34**(-1)
     &  - 4.D0*s23**2*s234**(-2)*s13*s14*s34**(-2)
     &  - 2.D0*s23**2*s234**(-2)*s13**2*s34**(-2)
     &  - 2.D0*s23**2*s234**(-2)*s34t1s3*s234t**(-1)
     &  - s23**2*s234**(-2)*s34t1s3*s14*s34**(-1)*s234t**(-1)
     &  - s23**2*s234**(-2)*s34t1s3*s13*s34**(-1)*s234t**(-1)
     &  + s23**2*s234**(-2)*s34t1s3*s23t1s3*s34**(-1)*s234t**(-1)
     &
      F40BFF = F40BFF - 2.D0*s23**2*s234**(-1)*s34**(-1)
     &  + 2.D0*s23**2*s234**(-1)*s134**(-1)
     &  - 2.D0*s23**2*s234**(-1)*s14*s34**(-2)
     &  + 2.D0*s23**2*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 2.D0*s23**2*s234**(-1)*s13*s34**(-2)
     &  - 2.D0*s23**2*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  - 3.D0*s23**2*s14**(-1)*s134**(-1)
     &  + 2.D0*s23**2*s34**(-2)
     &  - 2.D0*s23**2*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**2*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 3.D0*s23**2*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s23**2*s24*s124**(-2)*s14**(-1)
     &  - s23**2*s24*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  + 5.D0/2.D0*s23**2*s24*s234**(-2)*s34**(-1)
     &  - 2.D0*s23**2*s24*s234**(-2)*s14*s34**(-2)
     &
      F40BFF = F40BFF - 2.D0*s23**2*s24*s234**(-2)*s13*s34**(-2)
     &  - s23**2*s24*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - 2.D0*s23**2*s24*s234**(-1)*s34**(-2)
     &  + 2.D0*s23**2*s24*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s23**3*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 4.D0*s23**3*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s23**3*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  + 5.D0/2.D0*s23**3*s234**(-2)*s34**(-1)
     &  - 2.D0*s23**3*s234**(-2)*s14*s34**(-2)
     &  - 2.D0*s23**3*s234**(-2)*s13*s34**(-2)
     &  - s23**3*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - 2.D0*s23**3*s234**(-1)*s34**(-2)
     &  + 2.D0*s23**3*s234**(-1)*s34**(-1)*s134**(-1)
     &  + s12*s23**(-1)*s123**(-1)*s234**(-1)*s13*s14
     &  + s12*s23**(-1)*s123**(-1)*s23t4s2**(-1)*s123t**2
     &
      F40BFF = F40BFF + s12*s23**(-1)*s123**(-1)*s123t
     &  - s12*s23**(-1)*s123**(-1)*s34
     &  + s12*s23**(-1)*s123**(-1)*s34**2*s134**(-1)
     &  - 2.D0*s12*s23**(-1)*s123**(-1)*s14
     &  + 3.D0*s12*s23**(-1)*s123**(-1)*s14*s34*s134**(-1)
     &  - s12*s23**(-1)*s123**(-1)*s14**2*s34**(-1)
     &  + 3.D0*s12*s23**(-1)*s123**(-1)*s14**2*s134**(-1)
     &  + s12*s23**(-1)*s123**(-1)*s14**3*s34**(-1)*s134**(-1)
     &  + 3.D0/2.D0*s12*s23**(-1)*s123**(-1)*s13
     &  + 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s13*s14*s34**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s123**(-1)*s13**2*s34**(-1)
     &  + s12*s23**(-1)*s123**(-1)*s12t4s2
     &  + s12*s23**(-1)*s123**(-1)*s12t4s2**2*s23t4s2**(-1)
     &  - s12*s23**(-1)*s234**(-2)*s34**2
     &  - 2.D0*s12*s23**(-1)*s234**(-2)*s14*s34
     &
      F40BFF = F40BFF - 2.D0*s12*s23**(-1)*s234**(-2)*s13*s34
     &  + 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s34**2*s134**(-1)
     &  + 3.D0*s12*s23**(-1)*s234**(-1)*s14
     &  + s12*s23**(-1)*s234**(-1)*s14*s34*s134**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s234**(-1)*s14**2*s134**(-1)
     &  + s12*s23**(-1)*s234**(-1)*s13*s14*s134**(-1)
     &  - 3.D0*s12*s23**(-1)*s234**(-1)*s13**2*s134**(-1)
     &  - s12*s23**(-1)
     &  + s12*s23**(-1)*s34*s134**(-1)
     &  - s12*s23**(-1)*s14*s34**(-1)
     &  + 3.D0*s12*s23**(-1)*s14*s134**(-1)
     &  + s12*s23**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  - s12*s23**(-1)*s13*s34**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s13*s134**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &
      F40BFF = F40BFF + 2.D0*s12*s23**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  - s12*s23**(-1)*s24*s234**(-2)*s34
     &  - 2.D0*s12*s23**(-1)*s24*s234**(-2)*s14
     &  - 2.D0*s12*s23**(-1)*s24*s234**(-2)*s13
     &  - s12*s23**(-1)*s24*s234**(-1)*s14*s134**(-1)
     &  - 1.D0/2.D0*s12*s23**(-1)*s24*s34**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24*s134**(-1)
     &  + 1.D0/2.D0*s12*s23**(-1)*s24*s14*s34**(-1)*s134**(-1)
     &  + s12*s23**(-1)*s24*s13*s34**(-1)*s134**(-1)
     &  - s12*s123**(-2)*s34
     &  - s12*s123**(-2)*s14
     &  + 1.D0/2.D0*s12*s123**(-1)*s124**(-1)*s14**(-1)*s34**2
     &  + 1.D0/2.D0*s12*s123**(-1)*s124**(-1)*s34
     &  + 1.D0/2.D0*s12*s123**(-1)*s124**(-1)*s14
     &  + 1.D0/2.D0*s12*s123**(-1)*s124**(-1)*s13
     &
      F40BFF = F40BFF + 1.D0/2.D0*s12*s123**(-1)*s234**(-1)*s34
     &  + s12*s123**(-1)*s234**(-1)*s14
     &  + 1.D0/2.D0*s12*s123**(-1)*s234**(-1)*s14**2*s34**(-1)
     &  - s12*s123**(-1)*s234**(-1)*s13
     &  + 1.D0/2.D0*s12*s123**(-1)*s234**(-1)*s13**2*s34**(-1)
     &  + s12*s123**(-1)*s14**(-1)*s34
     &  + 1.D0/2.D0*s12*s123**(-1)
     &  + 1.D0/2.D0*s12*s123**(-1)*s13*s14**(-1)
     &  - s12*s124**(-2)*s12t3s1**(-1)*s14*s124t
     &  - s12*s124**(-2)*s14**(-1)*s34**2
     &  - 2.D0*s12*s124**(-2)*s34
     &  + 5.D0/2.D0*s12*s124**(-2)*s14
     &  - 2.D0*s12*s124**(-2)*s13*s14**(-1)*s34
     &  - 2.D0*s12*s124**(-2)*s13
     &  - s12*s124**(-2)*s13**2*s14**(-1)
     &
      F40BFF = F40BFF - s12*s124**(-2)*s12t3s1*s14*s124t**(-1)
     &  + 2.D0*s12*s124**(-1)*s234**(-1)*s13
     &  + 2.D0*s12*s124**(-1)*s234**(-1)*s13**3*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 1.D0/2.D0*s12*s124**(-1)
     &  + 1.D0/2.D0*s12*s124**(-1)*s34*s134**(-1)
     &  + s12*s124**(-1)*s14*s34**(-1)
     &  + 1.D0/2.D0*s12*s124**(-1)*s14*s134**(-1)
     &  + s12*s124**(-1)*s13*s14**(-1)
     &  - s12*s124**(-1)*s13*s34**(-1)
     &  - 1.D0/2.D0*s12*s124**(-1)*s13*s134**(-1)
     &  + 2.D0*s12*s124**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  - 2.D0*s12*s234**(-2)*s34
     &  - 2.D0*s12*s234**(-2)*s14
     &  - 2.D0*s12*s234**(-2)*s13
     &
      F40BFF = F40BFF + 3.D0*s12*s234**(-1)
     &  + 1.D0/2.D0*s12*s234**(-1)*s34*s134**(-1)
     &  - 9.D0/2.D0*s12*s234**(-1)*s14*s34**(-1)
     &  + 3.D0*s12*s234**(-1)*s14*s134**(-1)
     &  - s12*s234**(-1)*s14**2*s34**(-1)*s134**(-1)
     &  + 3.D0*s12*s234**(-1)*s13*s34**(-1)
     &  - 2.D0*s12*s234**(-1)*s13*s134**(-1)
     &  + s12*s234**(-1)*s13*(s14+s34)**(-1)
     &  + s12*s234**(-1)*s13*s14*s34**(-1)*s134**(-1)
     &  + s12*s234**(-1)*s13*s14*s34**(-1)*(s14+s34)**(-1)
     &  - 4.D0*s12*s234**(-1)*s13**2*s34**(-1)*s134**(-1)
     &  + 3.D0*s12*s234**(-1)*s13**2*s34**(-1)*(s14+s34)**(-1)
     &  - s12*s14t2s4**(-1)*s34t2s4*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s12*s14t2s4**(-1)*s34t2s4*s13*s34**(-1)*(s14+s34)**(-1)
     &  + 1.D0/2.D0*s12*s14**(-1)
     &
      F40BFF = F40BFF - s12*s14**(-1)*s34*s134**(-1)
     &  - 17.D0/2.D0*s12*s34**(-1)
     &  + 3.D0/2.D0*s12*s134**(-1)
     &  - s12*s34*s134**(-2)
     &  + 4.D0*s12*s14*s34**(-2)
     &  + 14.D0/3.D0*s12*s14*s34**(-1)*s134**(-1)
     &  - s12*s14*s134**(-2)
     &  - 1.D0/6.D0*s12*s14**2*s34**(-1)*s134**(-2)
     &  + 1.D0/2.D0*s12*s13*s14**(-1)*s134**(-1)
     &  - 4.D0*s12*s13*s34**(-2)
     &  + 3.D0*s12*s13*s34**(-1)*s134**(-1)
     &  + 16.D0/3.D0*s12*s13*s34**(-1)*(s14+s34)**(-1)
     &  + 2.D0*s12*s13*s34**(-1)*(s23+s34)**(-1)
     &  - 3.D0*s12*s13*s134**(-2)
     &  + s12*s13*(s14+s34)**(-1)*(s23+s34)**(-1)
     &
      F40BFF = F40BFF - 2.D0*s12*s13*s14*s34**(-1)*s134**(-2)
     &  + s12*s13*s14*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + s12*s13*s14*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s12*s13**2*s34**(-2)*s134**(-1)
     &  - 25.D0/6.D0*s12*s13**2*s34**(-1)*s134**(-2)
     &  + 3.D0*s12*s13**2*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 2.D0*s12*s13**2*s34**(-1)*(s12+s23)**(-1)*(s23+s34)**(-1)
     &  - 2.D0*s12*s13**2*s14*s34**(-2)*s134**(-2)
     &  - 2.D0*s12*s13**3*s34**(-2)*s134**(-2)
     &  + 2.D0*s12*s13**3*s34**(-1)*(s14+s34)**(-1)*(s12+s23)**(-1)*
     & (s23+s34)**(-1)
     &  - s12*s14t2s4*s34t2s4**(-1)*s14*s34**(-1)*s134**(-1)
     &  - 2.D0*s12*s14t2s4*s34t2s4**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s12*s24*s123**(-2)
     &  + 1.D0/2.D0*s12*s24*s123**(-1)*s14**(-1)
     &
      F40BFF = F40BFF - s12*s24*s124**(-2)*s12t3s1**(-1)*s124t
     &  - s12*s24*s124**(-2)*s14**(-1)*s34
     &  + 5.D0/2.D0*s12*s24*s124**(-2)
     &  - s12*s24*s124**(-2)*s13*s14**(-1)
     &  - s12*s24*s124**(-2)*s12t3s1*s124t**(-1)
     &  - 3.D0*s12*s24*s124**(-1)*s234**(-1)
     &  - s12*s24*s124**(-1)*s234**(-1)*s14*s34**(-1)
     &  + 2.D0*s12*s24*s124**(-1)*s234**(-1)*s13*s34**(-1)
     &  - s12*s24*s124**(-1)*s14**(-1)
     &  + 3.D0*s12*s24*s124**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12*s24*s124**(-1)*s134**(-1)
     &  + s12*s24*s124**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s12*s24*s234**(-2)*s34t1s3**(-1)*s234t
     &  + 7.D0/2.D0*s12*s24*s234**(-2)
     &  + 4.D0*s12*s24*s234**(-2)*s14*s34**(-1)
     &
      F40BFF = F40BFF + 4.D0*s12*s24*s234**(-2)*s13*s34**(-1)
     &  - s12*s24*s234**(-2)*s34t1s3*s234t**(-1)
     &  + 4.D0*s12*s24*s234**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12*s24*s234**(-1)*s134**(-1)
     &  - 8.D0*s12*s24*s234**(-1)*s14*s34**(-2)
     &  - s12*s24*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 4.D0*s12*s24*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  + 2.D0*s12*s24*s234**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s12*s24*s14**(-1)*s134**(-1)
     &  - 4.D0*s12*s24*s34**(-2)
     &  + 2.D0*s12*s24*s34**(-1)*s134**(-1)
     &  + s12*s24*s13*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  - 3.D0*s12*s24**2*s124**(-1)*s234**(-1)*s34**(-1)
     &  - s12*s24**2*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  + 9.D0/2.D0*s12*s24**2*s234**(-2)*s34**(-1)
     &
      F40BFF = F40BFF + 4.D0*s12*s24**2*s234**(-2)*s14*s34**(-2)
     &  + 4.D0*s12*s24**2*s234**(-2)*s13*s34**(-2)
     &  - s12*s24**2*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  + 4.D0*s12*s24**2*s234**(-1)*s34**(-2)
     &  - 2.D0*s12*s24**2*s234**(-1)*s34**(-1)*s134**(-1)
     &  + s12*s23*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + 5.D0/2.D0*s12*s23*s123**(-1)*s124**(-1)
     &  + s12*s23*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  + 3.D0/2.D0*s12*s23*s123**(-1)*s14**(-1)
     &  + 3.D0*s12*s23*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &  + 3.D0*s12*s23*s123**(-1)*s134**(-1)
     &  + 3.D0*s12*s23*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - 2.D0*s12*s23*s124**(-2)*s14**(-1)*s34
     &  - 2.D0*s12*s23*s124**(-2)
     &  - 2.D0*s12*s23*s124**(-2)*s13*s14**(-1)
     &
      F40BFF = F40BFF - s12*s23*s124**(-1)*s14**(-1)
     &  - s12*s23*s124**(-1)*s34**(-1)
     &  + 3.D0/2.D0*s12*s23*s124**(-1)*s134**(-1)
     &  + s12*s23*s124**(-1)*s13*s14**(-1)*s134**(-1)
     &  + s12*s23*s124**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s12*s23*s234**(-2)*s34t1s3**(-1)*s234t
     &  - 1.D0/2.D0*s12*s23*s234**(-2)
     &  - 4.D0*s12*s23*s234**(-2)*s14*s34**(-1)
     &  - 4.D0*s12*s23*s234**(-2)*s13*s34**(-1)
     &  - s12*s23*s234**(-2)*s34t1s3*s234t**(-1)
     &  + 3.D0/2.D0*s12*s23*s234**(-1)*s34**(-1)
     &  + 2.D0*s12*s23*s234**(-1)*s134**(-1)
     &  + s12*s23*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 4.D0*s12*s23*s234**(-1)*s13*s34**(-2)
     &  + 4.D0*s12*s23*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &
      F40BFF = F40BFF + s12*s23*s234**(-1)*s13*s34**(-1)*
     & (s14+s34)**(-1)
     &  + 4.D0*s12*s23*s234**(-1)*s13*s14*s34**(-2)*s134**(-1)
     &  + 4.D0*s12*s23*s234**(-1)*s13**2*s34**(-2)*s134**(-1)
     &  - 3.D0*s12*s23*s14**(-1)*s134**(-1)
     &  + 4.D0*s12*s23*s34**(-2)
     &  - 4.D0*s12*s23*s34**(-1)*s134**(-1)
     &  - 4.D0*s12*s23*s13*s34**(-2)*s134**(-1)
     &  + s12*s23*s13*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + s12*s23*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 3.D0*s12*s23*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s12*s23*s24*s124**(-2)*s14**(-1)
     &  - s12*s23*s24*s124**(-1)*s234**(-1)*s34**(-1)
     &  + 2.D0*s12*s23*s24*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 4.D0*s12*s23*s24*s234**(-1)*s13*s34**(-2)*s134**(-1)
     &
      F40BFF = F40BFF + 3.D0/2.D0*s12*s23**2*s123**(-1)*s124**(-1)*
     & s14**(-1)
     &  + 6.D0*s12*s23**2*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s12*s23**2*s124**(-2)*s14**(-1)
     &  - s12*s23**2*s234**(-2)*s34t1s3**(-1)*s34**(-1)*s234t
     &  - 3.D0/2.D0*s12*s23**2*s234**(-2)*s34**(-1)
     &  - 4.D0*s12*s23**2*s234**(-2)*s14*s34**(-2)
     &  - 4.D0*s12*s23**2*s234**(-2)*s13*s34**(-2)
     &  - s12*s23**2*s234**(-2)*s34t1s3*s34**(-1)*s234t**(-1)
     &  - 2.D0*s12*s23**2*s234**(-1)*s34**(-2)
     &  + 4.D0*s12*s23**2*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 4.D0*s12*s23**2*s234**(-1)*s13*s34**(-2)*s134**(-1)
     &  - 2.D0*s12*s23**2*s24*s234**(-2)*s34**(-2)
     &  - 2.D0*s12*s23**3*s234**(-2)*s34**(-2)
     &  - s12**2*s23**(-1)*s234**(-2)*s34
     &
      F40BFF = F40BFF + s12**2*s23**(-1)*s234**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*s34*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*s14*s134**(-1)
     &  - 5.D0/2.D0*s12**2*s23**(-1)*s234**(-1)*s13*s134**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s34**(-1)
     &  - 1.D0/2.D0*s12**2*s23**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s14*s34**(-1)*s134**(-1)
     &  + s12**2*s23**(-1)*s13*s34**(-1)*s134**(-1)
     &  - s12**2*s23**(-1)*s24*s234**(-2)
     &  + 1.D0/2.D0*s12**2*s23**(-1)*s24*s234**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**2*s123**(-1)*s124**(-1)*s14**(-1)*s34
     &  + s12**2*s123**(-1)*s124**(-1)
     &  + 1.D0/2.D0*s12**2*s123**(-1)*s124**(-1)*s13*s14**(-1)
     &  + 1.D0/2.D0*s12**2*s123**(-1)*s14**(-1)
     &  + s12**2*s123**(-1)*s14**(-1)*s34*s134**(-1)
     &
      F40BFF = F40BFF + s12**2*s123**(-1)*s134**(-1)
     &  + s12**2*s123**(-1)*s13*s14**(-1)*s134**(-1)
     &  - s12**2*s124**(-2)*s14**(-1)*s34
     &  - s12**2*s124**(-2)*s13*s14**(-1)
     &  - s12**2*s124**(-1)*s14**(-1)
     &  + s12**2*s124**(-1)*s34**(-1)
     &  + 1.D0/2.D0*s12**2*s124**(-1)*s134**(-1)
     &  - s12**2*s234**(-2)
     &  - 7.D0/2.D0*s12**2*s234**(-1)*s34**(-1)
     &  + 11.D0/2.D0*s12**2*s234**(-1)*s134**(-1)
     &  + s12**2*s234**(-1)*s14*s34**(-1)*s134**(-1)
     &  + 4.D0*s12**2*s234**(-1)*s13*s34**(-1)*s134**(-1)
     &  + s12**2*s234**(-1)*s13*s34**(-1)*(s14+s34)**(-1)
     &  - s12**2*s14**(-1)*s134**(-1)
     &  + 2.D0*s12**2*s34**(-2)
     &
      F40BFF = F40BFF - 4.D0*s12**2*s34**(-1)*s134**(-1)
     &  - 4.D0*s12**2*s13*s34**(-2)*s134**(-1)
     &  + s12**2*s13*s34**(-1)*(s14+s34)**(-1)*(s23+s34)**(-1)
     &  + 1.D0/2.D0*s12**2*s24*s123**(-1)*s124**(-1)*s14**(-1)
     &  + s12**2*s24*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s12**2*s24*s124**(-1)*s234**(-1)*s34**(-1)
     &  + 2.D0*s12**2*s24*s234**(-2)*s34**(-1)
     &  - 4.D0*s12**2*s24*s234**(-1)*s34**(-2)
     &  + 4.D0*s12**2*s24*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 4.D0*s12**2*s24*s234**(-1)*s13*s34**(-2)*s134**(-1)
     &  + 2.D0*s12**2*s24**2*s234**(-2)*s34**(-2)
     &  + 3.D0/2.D0*s12**2*s23*s123**(-1)*s124**(-1)*s14**(-1)
     &  + 4.D0*s12**2*s23*s123**(-1)*s14**(-1)*s134**(-1)
     &  - s12**2*s23*s124**(-2)*s14**(-1)
     &  - 2.D0*s12**2*s23*s234**(-2)*s34**(-1)
     &
      F40BFF = F40BFF + 4.D0*s12**2*s23*s234**(-1)*s34**(-1)*s134**(-1)
     &  + 4.D0*s12**2*s23*s234**(-1)*s13*s34**(-2)*s134**(-1)
     &  - 2.D0*s12**2*s23**2*s234**(-2)*s34**(-2)
     &  - 1.D0/2.D0*s12**3*s23**(-1)*s234**(-1)*s134**(-1)
     &  + 1.D0/2.D0*s12**3*s123**(-1)*s124**(-1)*s14**(-1)
     &  + s12**3*s123**(-1)*s14**(-1)*s134**(-1)

      F40b = s1234**(-2)*F40BFF

      return
      end

************************************************************************

c     Leading-colour antenna function for g-q-qb-g.
      function G40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34

      s1234=s12+s13+s14+s23+s24+s34

      g40 =  + s134**(-2)*s1234**(-2)*s13**(-1) * (
     &     - 2.d0*s24**2*s34
     &     - 4.d0*s23*s24*s34
     &     - 2.d0*s23**2*s34
     &     - 4.d0*s12*s24*s34
     &     - 4.d0*s12*s23*s34
     &     - 2.d0*s12**2*s34
     &     )
      g40 = g40 + s134**(-2)*s1234**(-2)*s34**(-2) * (
     &     - 2.d0*s14**2*s24**2
     &     - 4.d0*s14**2*s23*s24
     &     - 2.d0*s14**2*s23**2
     &     - 2.d0*s13**2*s24**2
     &     - 4.d0*s13**2*s23*s24
     &     - 2.d0*s13**2*s23**2
     &     - 4.d0*s12*s14**2*s24
     &     - 4.d0*s12*s14**2*s23
     &     - 4.d0*s12*s13**2*s24
     &     - 4.d0*s12*s13**2*s23
     &     - 2.d0*s12**2*s14**2
     &     - 2.d0*s12**2*s13**2
     &     )
      g40 = g40 + s134**(-2)*s1234**(-2)*s34**(-1) * (
     &     - 4.d0*s13*s24**2
     &     - 8.d0*s13*s23*s24
     &     - 4.d0*s13*s23**2
     &     - 8.d0*s12*s13*s24
     &     - 8.d0*s12*s13*s23
     &     - 4.d0*s12**2*s13
     &     )
      g40 = g40 + s134**(-2)*s1234**(-2) * (
     &     - 4.d0*s24**2
     &     - 8.d0*s23*s24
     &     - 4.d0*s23**2
     &     - 8.d0*s12*s24
     &     - 8.d0*s12*s23
     &     - 4.d0*s12**2
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s13**(-1) * (
     &     - s34**3
     &     - 3.d0*s24*s34**2
     &     - 4.d0*s24**2*s34
     &     - 2.d0*s24**3
     &     + s23*s34**2
     &     + 2.d0*s23**2*s34
     &     + 2.d0*s23**3
     &     + 4.d0*s12*s34**2
     &     + 6.d0*s12*s24*s34
     &     + 4.d0*s12*s24**2
     &     + 2.d0*s12*s23*s34
     &     + 4.d0*s12*s23**2
     &     - 3.d0*s12**2*s34
     &     - 3.d0*s12**2*s24
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s13**(-1) * (
     &     + 3.d0*s12**2*s23
     &     + 2.d0*s12**3
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s24**(-1) * (
     &     - s34**3
     &     + s14*s34**2
     &     + 2.d0*s14**2*s34
     &     + 2.d0*s14**3
     &     - 3.d0*s13*s34**2
     &     - 4.d0*s13**2*s34
     &     - 2.d0*s13**3
     &     + 4.d0*s12*s34**2
     &     + 2.d0*s12*s14*s34
     &     + 4.d0*s12*s14**2
     &     + 6.d0*s12*s13*s34
     &     + 4.d0*s12*s13**2
     &     - 3.d0*s12**2*s34
     &     + 3.d0*s12**2*s14
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s24**(-1) * (
     &     - 3.d0*s12**2*s13
     &     + 2.d0*s12**3
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s34**(-2) * (
     &     + 4.d0*s12**2*s14*s24
     &     + 4.d0*s12**2*s13*s23
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 8.d0*s12*s24**2
     &     + 8.d0*s12*s23**2
     &     + 8.d0*s12*s14*s24
     &     + 8.d0*s12*s14**2
     &     + 8.d0*s12*s13*s23
     &     + 8.d0*s12*s13**2
     &     + 4.d0*s12**2*s23
     &     + 4.d0*s12**2*s14
     &     + 4.d0*s12**3
     &     )
      g40 = g40 + s134**(-1)*s234**(-1)*s1234**(-2) * (
     &     + 12.d0*s12*s34
     &     + 12.d0*s12*s24
     &     + 12.d0*s12*s23
     &     + 12.d0*s12*s14
     &     + 12.d0*s12*s13
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s12**(-1)*s13**(-1) * (
     &     + 2.d0*s23*s34**2
     &     - 4.d0*s23*s24*s34
     &     + 2.d0*s23*s24**2
     &     + 2.d0*s23**3
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 2.d0*s24**3
     &     + 2.d0*s23*s24**2
     &     + 2.d0*s23**2*s24
     &     + 2.d0*s23**3
     &     + 2.d0*s14*s24**2
     &     - 2.d0*s14*s23**2
     &     + 2.d0*s14**2*s24
     &     + 2.d0*s14**2*s23
     &     - 2.d0*s13*s24**2
     &     + 2.d0*s13*s23**2
     &     + 2.d0*s13**2*s24
     &     + 2.d0*s13**2*s23
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 2.d0*s24*s34
     &     - 2.d0*s24**2
     &     + 4.d0*s23*s34
     &     - 8.d0*s23*s24
     &     + 2.d0*s23**2
     &     + 2.d0*s14*s24
     &     + 2.d0*s13*s24
     &     + 4.d0*s13*s23
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s13**(-1) * (
     &     + 3.d0*s34**2
     &     - 2.d0*s24*s34
     &     + 2.d0*s24**2
     &     - 4.d0*s23*s34
     &     + 2.d0*s23*s24
     &     + 10.d0*s23**2
     &     - 6.d0*s12*s34
     &     - 4.d0*s12*s24
     &     + 12.d0*s12*s23
     &     + 5.d0*s12**2
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s24**(-1)*s34**(-1) * (
     &     - 2.d0*s14**3
     &     + 2.d0*s13**3
     &     - 2.d0*s12*s14**2
     &     - 2.d0*s12*s13**2
     &     - s12**2*s14
     &     + s12**2*s13
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s24**(-1) * (
     &     + s34**2
     &     - s14*s34
     &     - 2.d0*s14**2
     &     + 3.d0*s13*s34
     &     + 4.d0*s13**2
     &     - 2.d0*s12*s34
     &     - 4.d0*s12*s13
     &     + s12**2
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s34**(-2) * (
     &     + 4.d0*s14*s24**2
     &     + 4.d0*s14*s23*s24
     &     - 4.d0*s14**2*s24
     &     - 4.d0*s14**2*s23
     &     + 4.d0*s13*s23*s24
     &     + 4.d0*s13*s23**2
     &     - 4.d0*s13**2*s24
     &     - 4.d0*s13**2*s23
     &     + 8.d0*s12*s14*s24
     &     - 4.d0*s12*s14**2
     &     + 8.d0*s12*s13*s23
     &     - 4.d0*s12*s13**2
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 8.d0*s24**2
     &     + 4.d0*s23*s24
     &     + 16.d0*s23**2
     &     + 6.d0*s14*s24
     &     - 8.d0*s14*s23
     &     + 6.d0*s14**2
     &     - 14.d0*s13*s24
     &     + 6.d0*s13**2
     &     + 4.d0*s12*s24
     &     + 16.d0*s12*s23
     &     - 4.d0*s12*s14
     &     - 12.d0*s12*s13
     &     + 10.d0*s12**2
     &     )
      g40 = g40 + s134**(-1)*s1234**(-2) * (
     &     + 8.d0*s34
     &     - 14.d0*s24
     &     - 4.d0*s23
     &     + 4.d0*s14
     &     + 8.d0*s13
     &     - 16.d0*s12
     &     )
      g40 = g40 + s234**(-2)*s1234**(-2)*s24**(-1) * (
     &     - 2.d0*s14**2*s34
     &     - 4.d0*s13*s14*s34
     &     - 2.d0*s13**2*s34
     &     - 4.d0*s12*s14*s34
     &     - 4.d0*s12*s13*s34
     &     - 2.d0*s12**2*s34
     &     )
      g40 = g40 + s234**(-2)*s1234**(-2)*s34**(-2) * (
     &     - 2.d0*s14**2*s24**2
     &     - 2.d0*s14**2*s23**2
     &     - 4.d0*s13*s14*s24**2
     &     - 4.d0*s13*s14*s23**2
     &     - 2.d0*s13**2*s24**2
     &     - 2.d0*s13**2*s23**2
     &     - 4.d0*s12*s14*s24**2
     &     - 4.d0*s12*s14*s23**2
     &     - 4.d0*s12*s13*s24**2
     &     - 4.d0*s12*s13*s23**2
     &     - 2.d0*s12**2*s24**2
     &     - 2.d0*s12**2*s23**2
     &     )
      g40 = g40 + s234**(-2)*s1234**(-2)*s34**(-1) * (
     &     - 4.d0*s14**2*s24
     &     - 8.d0*s13*s14*s24
     &     - 4.d0*s13**2*s24
     &     - 8.d0*s12*s14*s24
     &     - 8.d0*s12*s13*s24
     &     - 4.d0*s12**2*s24
     &     )
      g40 = g40 + s234**(-2)*s1234**(-2) * (
     &     - 4.d0*s14**2
     &     - 8.d0*s13*s14
     &     - 4.d0*s13**2
     &     - 8.d0*s12*s14
     &     - 8.d0*s12*s13
     &     - 4.d0*s12**2
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s12**(-1)*s24**(-1) * (
     &     + 2.d0*s14*s34**2
     &     + 2.d0*s14**3
     &     - 4.d0*s13*s14*s34
     &     + 2.d0*s13**2*s14
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 2.d0*s14*s24**2
     &     + 2.d0*s14*s23**2
     &     + 2.d0*s14**2*s24
     &     - 2.d0*s14**2*s23
     &     + 2.d0*s14**3
     &     + 2.d0*s13*s24**2
     &     + 2.d0*s13*s23**2
     &     + 2.d0*s13*s14**2
     &     - 2.d0*s13**2*s24
     &     + 2.d0*s13**2*s23
     &     + 2.d0*s13**2*s14
     &     + 2.d0*s13**3
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s12**(-1) * (
     &     + 4.d0*s14*s34
     &     + 4.d0*s14*s24
     &     + 2.d0*s14**2
     &     + 2.d0*s13*s34
     &     + 2.d0*s13*s24
     &     + 2.d0*s13*s23
     &     - 8.d0*s13*s14
     &     - 2.d0*s13**2
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s13**(-1)*s34**(-1) * (
     &     + 2.d0*s24**3
     &     - 2.d0*s23**3
     &     - 2.d0*s12*s24**2
     &     - 2.d0*s12*s23**2
     &     + s12**2*s24
     &     - s12**2*s23
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s13**(-1) * (
     &     + s34**2
     &     + 3.d0*s24*s34
     &     + 4.d0*s24**2
     &     - s23*s34
     &     - 2.d0*s23**2
     &     - 2.d0*s12*s34
     &     - 4.d0*s12*s24
     &     + s12**2
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s24**(-1) * (
     &     + 3.d0*s34**2
     &     - 4.d0*s14*s34
     &     + 10.d0*s14**2
     &     - 2.d0*s13*s34
     &     + 2.d0*s13*s14
     &     + 2.d0*s13**2
     &     - 6.d0*s12*s34
     &     + 12.d0*s12*s14
     &     - 4.d0*s12*s13
     &     + 5.d0*s12**2
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s34**(-2) * (
     &     - 4.d0*s14*s24**2
     &     - 4.d0*s14*s23**2
     &     + 4.d0*s14**2*s24
     &     - 4.d0*s13*s24**2
     &     - 4.d0*s13*s23**2
     &     + 4.d0*s13*s14*s24
     &     + 4.d0*s13*s14*s23
     &     + 4.d0*s13**2*s23
     &     - 4.d0*s12*s24**2
     &     - 4.d0*s12*s23**2
     &     + 8.d0*s12*s14*s24
     &     + 8.d0*s12*s13*s23
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2)*s34**(-1) * (
     &     + 6.d0*s24**2
     &     + 6.d0*s23**2
     &     - 8.d0*s14*s23
     &     + 16.d0*s14**2
     &     - 14.d0*s13*s24
     &     + 6.d0*s13*s23
     &     + 4.d0*s13*s14
     &     + 8.d0*s13**2
     &     - 12.d0*s12*s24
     &     - 4.d0*s12*s23
     &     + 16.d0*s12*s14
     &     + 4.d0*s12*s13
     &     + 10.d0*s12**2
     &     )
      g40 = g40 + s234**(-1)*s1234**(-2) * (
     &     + 8.d0*s34
     &     + 8.d0*s24
     &     + 4.d0*s23
     &     - 4.d0*s14
     &     - 14.d0*s13
     &     - 16.d0*s12
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1)*s13**(-1)*s34**(-1) * (
     &     + 2.d0*s23*s24**2
     &     + 2.d0*s23**3
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1)*s13**(-1) * (
     &     - 2.d0*s23*s34
     &     + 4.d0*s23*s24
     &     + 2.d0*s14*s23
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1)*s24**(-1)*s34**(-1) * (
     &     + 2.d0*s14**3
     &     + 2.d0*s13**2*s14
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1)*s24**(-1) * (
     &     - 2.d0*s14*s34
     &     + 2.d0*s14*s23
     &     + 4.d0*s13*s14
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + 6.d0*s24**2
     &     + 4.d0*s23*s24
     &     + 6.d0*s23**2
     &     + 8.d0*s14*s24
     &     + 6.d0*s14**2
     &     + 8.d0*s13*s24
     &     + 8.d0*s13*s23
     &     + 4.d0*s13*s14
     &     + 6.d0*s13**2
     &     )
      g40 = g40 + s1234**(-2)*s12**(-1) * (
     &     - 2.d0*s24
     &     - 2.d0*s23
     &     - 2.d0*s14
     &     - 2.d0*s13
     &     )
      g40 = g40 + s1234**(-2)*s13**(-1)*s24**(-1) * (
     &     - 2.d0*s14*s23
     &     + 2.d0*s12*s34
     &     )
      g40 = g40 + s1234**(-2)*s13**(-1)*s34**(-1) * (
     &     - 2.d0*s24**2
     &     + 2.d0*s23*s24
     &     - 2.d0*s23**2
     &     + 2.d0*s12*s24
     &     - 2.d0*s12*s23
     &     - s12**2
     &     )
      g40 = g40 + s1234**(-2)*s13**(-1) * (
     &     - 3.d0*s34
     &     - 2.d0*s24
     &     + 4.d0*s23
     &     + 2.d0*s12
     &     )
      g40 = g40 + s1234**(-2)*s24**(-1)*s34**(-1) * (
     &     - 2.d0*s14**2
     &     + 2.d0*s13*s14
     &     - 2.d0*s13**2
     &     - 2.d0*s12*s14
     &     + 2.d0*s12*s13
     &     - s12**2
     &     )
      g40 = g40 + s1234**(-2)*s24**(-1) * (
     &     - 3.d0*s34
     &     + 4.d0*s14
     &     - 2.d0*s13
     &     + 2.d0*s12
     &     )
      g40 = g40 + s1234**(-2)*s34**(-2) * (
     &     - 2.d0*s24**2
     &     - 2.d0*s23**2
     &     + 8.d0*s14*s24
     &     - 2.d0*s14**2
     &     + 8.d0*s13*s23
     &     - 2.d0*s13**2
     &     )
      g40 = g40 + s1234**(-2)*s34**(-1) * (
     &     + 8.d0*s24
     &     + 14.d0*s23
     &     + 14.d0*s14
     &     + 8.d0*s13
     &     + 24.d0*s12
     &     )
      g40 = g40 + s1234**(-2) * (
     &     - 18.d0
     &     )
      g40 = g40 - 4d0*(s13*s24-s14*s23)**2/s12**2/s34**2/s1234**2

      G40 = g40/2d0

      return
      end

************************************************************************

c     Subleading-colour antenna function for g-q-qb-g.
      function G40tilde(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s134 = s13+s14+s34
      s234 = s23+s24+s34

      s1234 = s12+s13+s14+s23+s24+s34

      g40t = + s134**(-2)*s1234**(-2)*s13**(-1) * (
     &     - s24**2*s34
     &     - 2.d0*s23*s24*s34
     &     - s23**2*s34
     &     - 2.d0*s12*s24*s34
     &     - 2.d0*s12*s23*s34
     &     - s12**2*s34
     &     )
      g40t = g40t + s134**(-2)*s1234**(-2)*s14**(-1) * (
     &     - s24**2*s34
     &     - 2.d0*s23*s24*s34
     &     - s23**2*s34
     &     - 2.d0*s12*s24*s34
     &     - 2.d0*s12*s23*s34
     &     - s12**2*s34
     &     )
      g40t = g40t + s134**(-2)*s1234**(-2) * (
     &     - 2.d0*s24**2
     &     - 4.d0*s23*s24
     &     - 2.d0*s23**2
     &     - 4.d0*s12*s24
     &     - 4.d0*s12*s23
     &     - 2.d0*s12**2
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s13**(-1)*
     & s23**(-1) * (
     &     - s12*s34**3
     &     - s12**3*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s13**(-1) * (
     &     - s34**3
     &     - 2.d0*s24*s34**2
     &     - 2.d0*s24**2*s34
     &     + 2.d0*s12*s34**2
     &     + 4.d0*s12*s24*s34
     &     - 3.d0*s12**2*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s14**(-1)*
     & s24**(-1) * (
     &     - s12*s34**3
     &     - s12**3*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s14**(-1) * (
     &     - s34**3
     &     - 2.d0*s24*s34**2
     &     - 2.d0*s24**2*s34
     &     - 2.d0*s12*s34**2
     &     - 4.d0*s12*s24*s34
     &     - 3.d0*s12**2*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     - s34**3
     &     - 2.d0*s14*s34**2
     &     - 2.d0*s14**2*s34
     &     + 2.d0*s12*s34**2
     &     + 4.d0*s12*s14*s34
     &     - 3.d0*s12**2*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2)*s24**(-1) * (
     &     - s34**3
     &     - 2.d0*s14*s34**2
     &     - 2.d0*s14**2*s34
     &     - 2.d0*s12*s34**2
     &     - 4.d0*s12*s14*s34
     &     - 3.d0*s12**2*s34
     &     )
      g40t = g40t + s134**(-1)*s234**(-1)*s1234**(-2) * (
     &     - 8.d0*s12*s34
     &     - 4.d0*s12**2
     &     )
      g40t = g40t + s134**(-1)*s1234**(-2)*s13**(-1) * (
     &     + 2.d0*s24*s34
     &     - s24**2
     &     - 2.d0*s23*s34
     &     + s23**2
     &     - 4.d0*s12*s34
     &     - 2.d0*s12*s24
     &     - s12**2
     &     )
      g40t = g40t + s134**(-1)*s1234**(-2)*s14**(-1) * (
     &     + s24**2
     &     - s23**2
     &     - 2.d0*s12*s23
     &     - s12**2
     &     )
      g40t = g40t + s134**(-1)*s1234**(-2)*s23**(-1) * (
     &     + s34**2
     &     + 2.d0*s14*s34
     &     + 2.d0*s14**2
     &     - 2.d0*s12*s34
     &     - 2.d0*s12*s14
     &     + s12**2
     &     )
      g40t = g40t + s134**(-1)*s1234**(-2)*s24**(-1) * (
     &     + s34**2
     &     + 2.d0*s14*s34
     &     + 2.d0*s14**2
     &     + 2.d0*s12*s14
     &     + s12**2
     &     )
      g40t = g40t + s134**(-1)*s1234**(-2) * (
     &     - 2.d0*s34
     &     - 2.d0*s24
     &     - 2.d0*s23
     &     - 4.d0*s12
     &     )
      g40t = g40t + s234**(-2)*s1234**(-2)*s23**(-1) * (
     &     - s14**2*s34
     &     - 2.d0*s13*s14*s34
     &     - s13**2*s34
     &     - 2.d0*s12*s14*s34
     &     - 2.d0*s12*s13*s34
     &     - s12**2*s34
     &     )
      g40t = g40t + s234**(-2)*s1234**(-2)*s24**(-1) * (
     &     - s14**2*s34
     &     - 2.d0*s13*s14*s34
     &     - s13**2*s34
     &     - 2.d0*s12*s14*s34
     &     - 2.d0*s12*s13*s34
     &     - s12**2*s34
     &     )
      g40t = g40t + s234**(-2)*s1234**(-2) * (
     &     - 2.d0*s14**2
     &     - 4.d0*s13*s14
     &     - 2.d0*s13**2
     &     - 4.d0*s12*s14
     &     - 4.d0*s12*s13
     &     - 2.d0*s12**2
     &     )
      g40t = g40t + s234**(-1)*s1234**(-2)*s13**(-1) * (
     &     + s34**2
     &     + 2.d0*s24*s34
     &     + 2.d0*s24**2
     &     - 2.d0*s12*s34
     &     - 2.d0*s12*s24
     &     + s12**2
     &     )
      g40t = g40t + s234**(-1)*s1234**(-2)*s14**(-1) * (
     &     + s34**2
     &     + 2.d0*s24*s34
     &     + 2.d0*s24**2
     &     + 2.d0*s12*s24
     &     + s12**2
     &     )
      g40t = g40t + s234**(-1)*s1234**(-2)*s23**(-1) * (
     &     + 2.d0*s14*s34
     &     - s14**2
     &     - 2.d0*s13*s34
     &     + s13**2
     &     - 4.d0*s12*s34
     &     - 2.d0*s12*s14
     &     - s12**2
     &     )
      g40t = g40t + s234**(-1)*s1234**(-2)*s24**(-1) * (
     &     + s14**2
     &     - s13**2
     &     - 2.d0*s12*s13
     &     - s12**2
     &     )
      g40t = g40t + s234**(-1)*s1234**(-2) * (
     &     - 2.d0*s34
     &     - 2.d0*s14
     &     - 2.d0*s13
     &     - 4.d0*s12
     &     )
      g40t = g40t + s1234**(-2)*s13**(-1)*s14**(-1) * (
     &     + 2.d0*s24**2
     &     + 2.d0*s23**2
     &     + 2.d0*s12*s24
     &     + 2.d0*s12*s23
     &     + 2.d0*s12**2
     &     )
      g40t = g40t + s1234**(-2)*s13**(-1)*s24**(-1) * (
     &     - s14*s23
     &     + s12*s34
     &     )
      g40t = g40t + s1234**(-2)*s13**(-1) * (
     &     - 2.d0*s24
     &     + 2.d0*s23
     &     + 2.d0*s12
     &     )
      g40t = g40t + s1234**(-2)*s14**(-1)*s23**(-1) * (
     &     - s13*s24
     &     + s12*s34
     &     )
      g40t = g40t + s1234**(-2)*s23**(-1)*s24**(-1) * (
     &     + 2.d0*s14**2
     &     + 2.d0*s13**2
     &     + 2.d0*s12*s14
     &     + 2.d0*s12*s13
     &     + 2.d0*s12**2
     &     )
      g40t = g40t + s1234**(-2)*s23**(-1) * (
     &     - 2.d0*s14
     &     + 2.d0*s13
     &     + 2.d0*s12
     &     )
      g40t = g40t + s1234**(-2) * (
     &     - 2.d0
     &     )

      G40tilde = g40t

      return
      end

************************************************************************

c     Antenna function for q-qb-q'-qb' (double splitting).
      function H40(s12,s13,s14,s23,s24,s34)
      implicit real(8)(a-h,o-z)
      
      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34

      s1234=s12+s13+s14+s23+s24+s34

      h40 = + s1234**(-2)*s12**(-1)*s34**(-1) * (
     &     + s24**2
     &     + s23**2
     &     - 2.d0*s14*s23
     &     + s14**2
     &     - 2.d0*s13*s24
     &     + s13**2
     &     )
      h40 = h40 + s1234**(-2) * (
     &     + 2.d0
     &     )

      h40 =  h40 + 2d0*((s14*s23-s13*s24)/(s12*s34))**(2)/s1234**(2)

      H40 = h40

      return
      end

c-----------------------------------------------------------------------
c     Four-parton tree-level antenna functions using yij5
c
c     Common block yij5 is filled in phase5.
c-----------------------------------------------------------------------

c     Same as A40, but using yij5 common block.
c     Normalised to s1234.
      function A40i(i1,i3,i4,i2)
      implicit real(8)(a-h,o-z)
      common/yij5/y(5,5)

      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)

      s134=s13+s14+s34
      s234=s23+s24+s34
      s1234=s134+s234-s34+s12

      wt=0d0

      wt =
     &     + s134**(-2) * ( 2*s12*s13*s14**2*s24 + s12*s13*s24*s34**2 +
     &     s12*s24*s34**3 + 2*s13*s14**2*s23*s24 + 2*s13*s14**2*s24**2
     &     + s13*s23*s24*s34**2 + s13*s24**2*s34**2 + s23*s24*s34**3 +
     &     s24**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 4*s12*s13*s14*s24*s34 - 4*
     &     s12*s13*s14*s24**2 - 3*s12*s13*s14*s34**2 + 6*s12*s13*s24*
     &     s34**2 + 3*s12*s13*s34**3 + 6*s12*s24*s34**3 + 3*s12*s24**2*
     &     s34**2 + 3*s12*s34**4 - 8*s12**2*s13*s24*s34 - 4*s12**2*s13*
     &     s34**2 - 4*s12**2*s24*s34**2 - 4*s12**2*s34**3 + 2*s12**3*
     &     s34**2 + 3*s13*s14*s24*s34**2 + 4*s13*s14*s24**2*s34 + s13*
     &     s14*s34**3 - 2*s13*s14**2*s24*s34 - s13*s14**2*s34**2 - 3*s13
     &     *s24*s34**3 - 3*s13*s24**2*s34**2 - 2*s13*s24**3*s34 - s13*
     &     s34**4 - 3*s24*s34**4 - 3*s24**2*s34**3 - s24**3*s34**2 -
     &     s34**5 )
      wt = wt + s134**(-1) * ( 2*s12*s13*s14*s34 + 2*s12*s13*s23*s34 -
     &     8*s12*s13*s24*s34 - 4*s12*s13*s34**2 + 3*s12*s23*s34**2 - 6*
     &     s12*s24*s34**2 - 3*s12*s34**3 + 2*s12**2*s13*s34 + 4*s12**2*
     &     s34**2 + 2*s13*s14*s23*s34 - 2*s13*s14*s24*s34 - 4*s13*s14*
     &     s24**2 - s13*s14*s34**2 + 2*s13*s14**2*s24 + s13*s14**2*s34
     &     - 3*s13*s23*s24*s34 - s13*s23*s34**2 + s13*s23**2*s34 + s13*
     &     s24*s34**2 - s13*s24**2*s34 + s13*s34**3 - 3*s23*s24*s34**2
     &     - s23*s34**3 + s23**2*s34**2 + 2*s24*s34**3 - s24**2*s34**2
     &     + s34**4 )
      wt = wt + s234**(-2) * ( 3*s12*s13*s24*s34**2 + 4*s12*s13*s24**2*
     &     s34 + 2*s12*s13*s24**3 + s12*s13*s34**3 + 3*s13*s14*s24*
     &     s34**2 + 4*s13*s14*s24**2*s34 + 2*s13*s14*s24**3 + s13*s14*
     &     s34**3 + 3*s13**2*s24*s34**2 + 4*s13**2*s24**2*s34 + 2*s13**2
     &     *s24**3 + s13**2*s34**3 )
      wt = wt + s234**(-1) * (  - 8*s12*s13*s24*s34 - 3*s12*s13*s34**2
     &     + 2*s12*s14*s24*s34 + 3*s12*s14*s34**2 - 6*s12*s24*s34**2 -
     &     2*s12*s24**2*s34 - 3*s12*s34**3 + 2*s12**2*s24*s34 + 4*s12**2
     &     *s34**2 - 5*s13*s14*s24*s34 - 4*s13*s14*s24**2 - 2*s13*s14*
     &     s34**2 + 2*s13*s24**2*s34 + 2*s13*s24**3 - 3*s13**2*s24*s34
     &     - 2*s13**2*s34**2 - 3*s14*s24*s34**2 - 2*s14*s24**2*s34 -
     &     s14*s34**3 + s14**2*s24*s34 + s14**2*s34**2 + 3*s24*s34**3 +
     &     3*s24**2*s34**2 + s24**3*s34 + s34**4 )
      wt = wt + 4*s12*s13*s34 + 2*s12*s14*s34 + 2*s12*s23*s34 + 6*s12*
     &     s24*s34 + 6*s12*s34**2 + 2*s12**2*s34 + 3*s13*s14*s34 - 2*s13
     &     *s24*s34 + 2*s13**2*s34 + 2*s14*s24*s34 + 3*s14*s34**2 +
     &     s14**2*s34 + 4*s23*s24*s34 + 3*s23*s34**2 + s23**2*s34 - 2*
     &     s24*s34**2 + s24**2*s34

      A40i=wt/s34**2/s13/s24/s1234
	
      return
      end

************************************************************************

c     Same as B40, but using yij5 common block.
c     Normalised to s1234.
      function B40i(i1,i3,i4,i2)
      implicit real(8)(a-h,o-z)
      common/yij5/y(5,5)

      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s1234=s12+s13+s14+s23+s24+s34
      s134=s13+s14+s34
      s234=s23+s24+s34

      wt=0d0
      wt = wt +  ( 2*s12**2*s34 - 2*s12*s13*s24
     +     + s12*s13*s34 - 2*s12*s14*s23 + s12*s14*s34 + 
     +     s12*s23*s34 + 
     +     s12*s24*s34 + 2*s12*s34**2 - s13**2*s24 + 
     +     s13*s14*s23 + s13*
     +     s14*s24 + s13*s23*s24 - s13*s24**2 - 
     +     s14**2*s23 - s14*s23**2
     +     + s14*s23*s24 )/s134/s234

      wt = wt +  ( 2*s12*s13*s14 + s12*s13*s34 + s12*s14*
     +     s34 - s13**2*s24 + s13*s14*s23 + s13*s14*s24 + 
     +     s13*s23*s34 - 
     +     s14**2*s23 + s14*s24*s34 )/s134**2

      wt = wt +  ( 2*s12*s23*s24 + s12*s23*s34 + s12*s24*
     +     s34 + s13*s23*s24 + s13*s23*s34 - s13*s24**2 - 
     +     s14*s23**2 + 
     +     s14*s23*s24 + s14*s24*s34 )/s234**2

      B40i= wt/s34**2/s1234

      return
      end

************************************************************************

c     Same as D40, but using yij5 common block.
c     Normalised to s1234.
      real(8) function C40i(i1,i3,i4,i2)
      implicit real(8)(a-h,o-z)
      common/yij5/y(5,5)

      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s1234=s12+s13+s14+s23+s24+s34
      s134=s13+s14+s34
      s234=s23+s24+s34
      s123=s23+s12+s13

      wt=0d0
      wt = wt + s23**(-1)*s34**(-1)*s123**(-1)*s134**(-1) * 
     +     ( 2*s12*s13
     +     *s14 + 2*s12*s13*s34 + 2*s13*s14*s23 + 2*s13*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s123**(-1)*s234**(-1) * 
     +     ( s12**2*
     +     s34 - s12*s13*s24 - s12*s14*s23 + s12*s14*s34 + 
     +     s12*s23*s34
     +     + s12*s34**2 + s13*s14*s24 - s13*s23*s24 - s13*s24*s34 - 
     +     s14**2*s23 - s14*s23**2 - s14*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s134**(-1)*s234**(-1) * 
     +     (  - s12**2
     +     *s34 + s12*s13*s24 + s12*s14*s23 - s12*s14*s34 - 
     +     s12*s23*s34
     +     - s12*s34**2 - s13*s14*s24 - s13*s23*s24 - s13*s24*s34 + 
     +     s14**2*s23 + s14*s23**2 + s14*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s234**(-2) * 
     +     (  - 2*s12*s23*s24 - 2
     +     *s12*s24*s34 + 2*s13*s24**2 - 2*s14*s23*s24 - 
     +     2*s14*s24*s34 )

      C40i=-wt/2.d0/s1234

      return
      end

************************************************************************

c     Same as D40, but using yij5 common block.
c     Normalised to s1234.
      real(8) function D40i(i1,i2,i3,i4)
      implicit real(8)(a-h,o-z)
      common/yij5/y(5,5)
      s12=y(i1,i2)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s23=y(i2,i3)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s134=s13+s14+s34
      s123=s23+s12+s13
      s124=s12+s14+s24
      s234=s23+s24+s34
      s1234=s12+s13+s14+s23+s24+s34

      wt=0d0

      wt =
     &     + s123**(-2) * ( 4*s12*s13**2*s14*s24*s34**3
     .     + 2*s12*s13**2*s14
     &     *s24**2*s34**2 + 2*s12*s13**2*s14*s34**4 + 4*s12*s13**2*
     &     s14**2*s24*s34**2 + 4*s12*s13**2*s14**2*s34**3
     .     + 2*s12*s13**2
     &     *s14**3*s34**2 + 2*s12*s14*s23**2*s24*s34**3
     .     + s12*s14*s23**2
     &     *s24**2*s34**2 + s12*s14*s23**2*s34**4
     .     + 2*s12*s14**2*s23**2*
     &     s24*s34**2 + 2*s12*s14**2*s23**2*s34**3
     .     + s12*s14**3*s23**2*
     &     s34**2 + 2*s14*s23**3*s24*s34**3 + s14*s23**3*s24**2*s34**2
     &     + s14*s23**3*s34**4 + 2*s14**2*s23**3*s24*s34**2 + 2*s14**2*
     &     s23**3*s34**3 + s14**3*s23**3*s34**2 )
      wt = wt + s123**(-1)*s124**(-1) * ( 6*s12*s14*s23*s24*s34**4 + 9*
     &     s12*s14*s23*s24**2*s34**3 + 4*s12*s14*s23*s24**3*s34**2 + s12
     &     *s14*s23*s34**5 - 9*s12*s14*s23**2*s24*s34**3 - 9*s12*s14*
     &     s23**2*s24**2*s34**2 + 6*s12*s14*s23**3*s24*s34**2 - s12*s14*
     &     s23**4*s34**2 + 9*s12*s14**2*s23*s24*s34**3 + 6*s12*s14**2*
     &     s23*s24**2*s34**2 + 3*s12*s14**2*s23*s34**4 - 9*s12*s14**2*
     &     s23**2*s24*s34**2 + 3*s12*s14**2*s23**3*s34**2 + 5*s12*s14**3
     &     *s23*s24*s34**2 + 3*s12*s14**3*s23*s34**3 - 3*s12*s14**3*
     &     s23**2*s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s24*s34**5
     &     + 3*s12*s23*s24**2*s34**4 + 3*s12*s23*s24**3*s34**3 + s12*
     &     s23*s24**4*s34**2 - 3*s12*s23**2*s24*s34**4 - 6*s12*s23**2*
     &     s24**2*s34**3 - 3*s12*s23**2*s24**3*s34**2 + 3*s12*s23**3*s24
     &     *s34**3 + 3*s12*s23**3*s24**2*s34**2 - s12*s23**4*s24*s34**2
     &     )
      wt = wt + s123**(-1)*s134**(-1) * ( 12*s12*s14*s23*s24*s34**4 + 9
     &     *s12*s14*s23*s24**2*s34**3 + 2*s12*s14*s23*s24**3*s34**2 + 5*
     &     s12*s14*s23*s34**5 - 6*s12*s14*s23**2*s24*s34**3 - 8*s12*s14*
     &     s23**2*s34**4 + 3*s12*s14*s23**3*s34**3 + 18*s12*s14**2*s23*
     &     s24*s34**3 + 9*s12*s14**2*s23*s24**2*s34**2 + s12*s14**2*s23*
     &     s24**3*s34 + 10*s12*s14**2*s23*s34**4 - 3*s12*s14**2*s23**2*
     &     s24*s34**2 - 12*s12*s14**2*s23**2*s34**3 + 3*s12*s14**2*
     &     s23**3*s34**2 + 12*s12*s14**3*s23*s24*s34**2 + 3*s12*s14**3*
     &     s23*s24**2*s34 + 11*s12*s14**3*s23*s34**3 - 8*s12*s14**3*
     &     s23**2*s34**2 + s12*s14**3*s23**3*s34 + 3*s12*s14**4*s23*s24*
     &     s34 + 7*s12*s14**4*s23*s34**2 - 2*s12*s14**4*s23**2*s34 + 2*
     &     s12*s14**5*s23*s34 + 3*s12*s23*s24*s34**5 + 3*s12*s23*s24**2*
     &     s34**4 + s12*s23*s24**3*s34**3 + s12*s23*s34**6 - 3*s12*
     &     s23**2*s24*s34**4 - 2*s12*s23**2*s34**5 + s12*s23**3*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 + 2*s14*s23**2*s24**3*s34**2 + 
     &     3*s14**2*s23**2*s24*s34**3 )
      wt = wt + s123**(-1)*s134**(-1) * ( 6*s14**2*s23**2*s24**2*s34**2
     &     + s14**2*s23**2*s24**3*s34 + 6*s14**3*s23**2*s24*s34**2 + 3*
     &     s14**3*s23**2*s24**2*s34 + s14**3*s23**2*s34**3 + 3*s14**4*
     &     s23**2*s24*s34 + 2*s14**4*s23**2*s34**2 + s14**5*s23**2*s34
     &     + s23**2*s24**3*s34**3 )
      wt = wt + s123**(-1)*s234**(-1) * (  - 5*s12*s13*s14*s23**2*s24*
     &     s34**2 - 2*s12*s13*s14*s23**2*s24**2*s34 - 3*s12*s13*s14*
     &     s23**2*s34**3 - 2*s12*s13*s14**2*s23*s34**3 - 4*s12*s13*
     &     s14**2*s23**2*s24*s34 - 10*s12*s13*s14**2*s23**2*s34**2 - 4*
     &     s12*s13*s14**3*s23*s34**2 - 6*s12*s13*s14**3*s23**2*s34 - 4*
     &     s12*s13*s14**3*s34**3 + s12*s13**2*s14*s23**2*s24*s34 + 3*s12
     &     *s13**2*s14*s23**2*s34**2 - 8*s12*s13**2*s14**2*s23*s34**2 - 
     &     4*s12*s13**2*s14**2*s23**2*s34 - 2*s12*s13**3*s14*s23**2*s34
     &     + s12*s14*s23**2*s24*s34**3 - s12*s14*s23**2*s24**2*s34**2
     &     - s12*s14*s23**2*s24**3*s34 + s12*s14*s23**2*s34**4 - 2*s12*
     &     s14**2*s23*s34**4 + s12*s14**2*s23**2*s24*s34**2 - 4*s12*
     &     s14**2*s23**2*s24**2*s34 + 2*s12*s14**2*s23**2*s34**3 - 6*s12
     &     *s14**3*s23**2*s24*s34 + 6*s12*s14**3*s23**2*s34**2 - 8*s12*
     &     s14**4*s23*s34**2 - 4*s12*s14**4*s23**2*s34 + s14*s23**2*s24*
     &     s34**4 + 3*s14*s23**2*s24**2*s34**3 + 3*s14*s23**2*s24**3*
     &     s34**2 )
      wt = wt + s123**(-1)*s234**(-1) * ( s14*s23**2*s24**4*s34 + 6*
     &     s14**2*s23**2*s24*s34**3 + 9*s14**2*s23**2*s24**2*s34**2 + 5*
     &     s14**2*s23**2*s24**3*s34 + s14**2*s23**2*s34**4 + 9*s14**3*
     &     s23**2*s24*s34**2 + 9*s14**3*s23**2*s24**2*s34 + 3*s14**3*
     &     s23**2*s34**3 + 7*s14**4*s23**2*s24*s34 + 3*s14**4*s23**2*
     &     s34**2 + 2*s14**5*s23**2*s34 )
      wt = wt + s123**(-1) * ( 5*s12*s13*s14*s23*s24*s34**2 - 3*s12*s13
     &     *s14*s23*s34**3 + s12*s13*s14*s23**2*s24*s34 - 3*s12*s13*s14*
     &     s23**2*s34**2 - 4*s12*s13*s14*s24*s34**3 - 4*s12*s13*s14*
     &     s34**4 + 2*s12*s13*s14**2*s23*s24*s34 + 2*s12*s13*s14**2*s23*
     &     s34**2 - 2*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &     s34**3 + 4*s12*s13*s14**3*s23*s34 + s12*s13*s23*s24**2*s34**2
     &     - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s34**3 + s12*s13**2*
     &     s14*s23*s24*s34 - 7*s12*s13**2*s14*s23*s34**2 + 4*s12*s13**2*
     &     s14*s24*s34**2 + 4*s12*s13**2*s14*s34**3 + 2*s12*s13**2*
     &     s14**2*s23*s34 + 4*s12*s13**2*s14**2*s34**2 - 2*s12*s13**2*
     &     s23*s24*s34**2 - 2*s12*s13**2*s23*s34**3 + 2*s12*s13**3*s14*
     &     s23*s34 - 19*s12*s14*s23*s24*s34**3 - 11*s12*s14*s23*s24**2*
     &     s34**2 - 10*s12*s14*s23*s34**4 + 11*s12*s14*s23**2*s24*s34**2
     &     + s12*s14*s23**2*s24**2*s34 + 9*s12*s14*s23**2*s34**3 - 3*
     &     s12*s14*s23**3*s34**2 - 21*s12*s14**2*s23*s24*s34**2 - 18*s12
     &     *s14**2*s23*s34**3 )
      wt = wt + s123**(-1) * ( 2*s12*s14**2*s23**2*s24*s34 + 12*s12*
     &     s14**2*s23**2*s34**2 - s12*s14**2*s23**3*s34 + s12*s14**3*s23
     &     *s24*s34 - 21*s12*s14**3*s23*s34**2 + 3*s12*s14**3*s23**2*s34
     &     - 6*s12*s23*s24*s34**4 - 6*s12*s23*s24**2*s34**3 - 2*s12*s23
     &     *s24**3*s34**2 - 2*s12*s23*s34**5 + 6*s12*s23**2*s24*s34**3
     &     + 2*s12*s23**2*s24**2*s34**2 + 2*s12*s23**2*s34**4 - s12*
     &     s23**3*s24*s34**2 - s12*s23**3*s34**3 - 5*s14*s23**2*s24*
     &     s34**3 - 7*s14*s23**2*s24**2*s34**2 - s14*s23**2*s24**3*s34
     &     - 2*s14*s23**2*s34**4 + 4*s14*s23**3*s24*s34**2 + s14*s23**3
     &     *s24**2*s34 + 3*s14*s23**3*s34**3 - 13*s14**2*s23**2*s24*
     &     s34**2 - 4*s14**2*s23**2*s24**2*s34 - 6*s14**2*s23**2*s34**3
     &     + 2*s14**2*s23**3*s24*s34 + 4*s14**2*s23**3*s34**2 - 5*
     &     s14**3*s23**2*s24*s34 - 7*s14**3*s23**2*s34**2 + s14**3*
     &     s23**3*s34 - 2*s14**4*s23**2*s34 - s23**2*s24**3*s34**2 )
      wt = wt + s124**(-2) * ( 4*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*
     &     s14*s23**3*s34**2 + 2*s12*s13*s23**2*s24*s34**3 + 2*s12*s13*
     &     s23**3*s24*s34**2 + 2*s12*s13**2*s14*s23**2*s34**2 + s12*
     &     s13**2*s23**2*s24*s34**2 + 2*s12*s14*s23**2*s34**4 + 4*s12*
     &     s14*s23**3*s34**3 + 2*s12*s14*s23**4*s34**2 + s12*s23**2*s24*
     &     s34**4 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s24*s34**2 + 2*
     &     s13*s14*s23**2*s24*s34**3 + 2*s13*s14*s23**3*s24*s34**2 + 
     &     s13**2*s14*s23**2*s24*s34**2 + s14*s23**2*s24*s34**4 + 2*s14*
     &     s23**3*s24*s34**3 + s14*s23**4*s24*s34**2 )
      wt = wt + s124**(-1)*s134**(-1) * ( 3*s12*s14*s23**2*s24*s34**3
     &     - 3*s12*s14*s23**2*s24**2*s34**2 + s12*s14*s23**2*s24**3*s34
     &     - s12*s14*s23**2*s34**4 - 9*s12*s14*s23**3*s24*s34**2 + 3*
     &     s12*s14*s23**3*s24**2*s34 + 3*s12*s14*s23**4*s24*s34 + s12*
     &     s14*s23**5*s34 + 3*s12*s14**2*s23**2*s24*s34**2 - 2*s12*
     &     s14**2*s23**2*s24**2*s34 - 3*s12*s14**2*s23**2*s34**3 - 3*s12
     &     *s14**2*s23**3*s24*s34 - 3*s12*s14**2*s23**4*s34 - s12*s14**3
     &     *s23**2*s24*s34 - 3*s12*s14**3*s23**2*s34**2 + 3*s12*s14**3*
     &     s23**3*s34 - 2*s12*s14**4*s23**2*s34 - s14*s23**2*s24*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 - 3*s14*s23**2*s24**3*s34**2 + 
     &     s14*s23**2*s24**4*s34 + 3*s14*s23**3*s24*s34**3 - 6*s14*
     &     s23**3*s24**2*s34**2 + 3*s14*s23**3*s24**3*s34 - 3*s14*s23**4
     &     *s24*s34**2 + 3*s14*s23**4*s24**2*s34 + s14*s23**5*s24*s34 )
      wt = wt + s124**(-1)*s234**(-1) * (  - 8*s12*s13*s14*s23*s34**4
     &     + 10*s12*s13*s14*s23**2*s24*s34**2 - 4*s12*s13*s14*s23**2*
     &     s24**2*s34 - 8*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*s14**2*
     &     s23*s34**3 + 4*s12*s13*s14**2*s23**2*s24*s34 + 4*s12*s13*
     &     s14**2*s23**2*s34**2 + 5*s12*s13*s23*s34**5 - 4*s12*s13*
     &     s23**2*s24*s34**3 + 4*s12*s13*s23**2*s24**2*s34**2 - s12*s13*
     &     s23**2*s24**3*s34 + 5*s12*s13*s23**2*s34**4 - 6*s12*s13**2*
     &     s14*s23*s34**3 + 6*s12*s13**2*s14*s23**2*s24*s34 - 2*s12*
     &     s13**2*s14*s23**2*s34**2 + 9*s12*s13**2*s23*s34**4 - 6*s12*
     &     s13**2*s23**2*s24*s34**2 + 3*s12*s13**2*s23**2*s24**2*s34 + 9
     &     *s12*s13**2*s23**2*s34**3 + 7*s12*s13**3*s23*s34**3 - 3*s12*
     &     s13**3*s23**2*s24*s34 + 7*s12*s13**3*s23**2*s34**2 + 2*s12*
     &     s13**4*s23*s34**2 + 2*s12*s13**4*s23**2*s34 - 3*s12*s14*s23*
     &     s34**5 + 3*s12*s14*s23**2*s24*s34**3 - 3*s12*s14*s23**2*
     &     s24**2*s34**2 + 2*s12*s14*s23**2*s24**3*s34 - 3*s12*s14*
     &     s23**2*s34**4 )
      wt = wt + s124**(-1)*s234**(-1) * ( 3*s12*s14**2*s23*s34**4 - 3*
     &     s12*s14**2*s23**2*s24*s34**2 + s12*s14**2*s23**2*s24**2*s34
     &     + 3*s12*s14**2*s23**2*s34**3 - 2*s12*s14**3*s23*s34**3 + 2*
     &     s12*s14**3*s23**2*s24*s34 - 2*s12*s14**3*s23**2*s34**2 + s12*
     &     s23*s34**6 - s12*s23**2*s24*s34**4 + s12*s23**2*s24**2*s34**3
     &     - s12*s23**2*s24**3*s34**2 + s12*s23**2*s34**5 + s13*s14*s23
     &     *s34**5 - 2*s13*s14*s23**2*s24*s34**3 - s13*s14*s23**2*s24**2
     &     *s34**2 - 5*s13*s14*s23**2*s24**3*s34 + s13*s14*s23**2*s34**4
     &     + 3*s13**2*s14*s23*s34**4 + 9*s13**2*s14*s23**2*s24**2*s34
     &     + 3*s13**2*s14*s23**2*s34**3 + 3*s13**3*s14*s23*s34**3 - 7*
     &     s13**3*s14*s23**2*s24*s34 + 3*s13**3*s14*s23**2*s34**2 + 2*
     &     s13**4*s14*s23*s34**2 + 2*s13**4*s14*s23**2*s34 + s14*s23**2*
     &     s24**4*s34 )
      wt = wt + s124**(-1) * ( s12*s13*s14*s23*s24*s34**2 + 9*s12*s13*
     &     s14*s23*s34**3 + 5*s12*s13*s14*s23**2*s24*s34 + 4*s12*s13*s14
     &     *s23**2*s34**2 + s12*s13*s14*s23**3*s34 - 4*s12*s13*s14**2*
     &     s23**2*s34 + 5*s12*s13*s23*s24*s34**3 + s12*s13*s23*s24**2*
     &     s34**2 - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s24*s34**2 + 
     &     s12*s13*s23**2*s24**2*s34 + 2*s12*s13*s23**2*s34**3 - s12*s13
     &     *s23**3*s24*s34 + s12*s13*s23**4*s34 + 4*s12*s13**2*s14*s23*
     &     s34**2 - 2*s12*s13**2*s14*s23**2*s34 + 2*s12*s13**2*s23*s24*
     &     s34**2 - 2*s12*s13**2*s23*s34**3 - 3*s12*s13**2*s23**2*s24*
     &     s34 + 6*s12*s13**2*s23**2*s34**2 + 3*s12*s13**2*s23**3*s34 - 
     &     s12*s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 + 5*s12*s14*
     &     s23*s24*s34**3 + 3*s12*s14*s23*s24**2*s34**2 + 6*s12*s14*s23*
     &     s34**4 - 4*s12*s14*s23**2*s24*s34**2 + 7*s12*s14*s23**2*
     &     s34**3 + 4*s12*s14*s23**3*s24*s34 + 7*s12*s14*s23**3*s34**2
     &     + 3*s12*s14*s23**4*s34 + 3*s12*s14**2*s23*s24*s34**2 + s12*
     &     s14**2*s23*s34**3 )
      wt = wt + s124**(-1) * (  - 4*s12*s14**2*s23**3*s34 + 2*s12*
     &     s14**3*s23*s34**2 + 4*s12*s23*s24*s34**4 + 3*s12*s23*s24**2*
     &     s34**3 + s12*s23*s24**3*s34**2 - s12*s23**2*s24*s34**3 - s12*
     &     s23**2*s24**2*s34**2 + 3*s12*s23**3*s24*s34**2 - 2*s12*s23**3
     &     *s34**3 - s12*s23**4*s34**2 - s13*s14*s23**2*s24*s34**2 + 6*
     &     s13*s14*s23**2*s24**2*s34 + 2*s13*s14*s23**3*s34**2 + 4*s13*
     &     s14*s23**4*s34 - 7*s13**2*s14*s23**2*s24*s34 + 6*s13**2*s14*
     &     s23**2*s34**2 + 7*s13**2*s14*s23**3*s34 + s13**3*s14*s23*
     &     s34**2 + 6*s13**3*s14*s23**2*s34 + 3*s14*s23**2*s24*s34**3 - 
     &     s14*s23**2*s24**2*s34**2 - s14*s23**2*s34**4 - s14*s23**3*s24
     &     *s34**2 + 4*s14*s23**3*s24**2*s34 - 2*s14*s23**3*s34**3 + 3*
     &     s14*s23**4*s24*s34 + s14*s23**5*s34 )
      wt = wt + s134**(-2) * ( 3*s12*s14*s23**2*s24**2*s34**2 + 6*s12*
     &     s14*s23**3*s24*s34**2 + 3*s12*s14*s23**4*s34**2 + 4*s12*
     &     s14**2*s23**2*s24**2*s34 + 8*s12*s14**2*s23**3*s24*s34 + 4*
     &     s12*s14**2*s23**4*s34 + 2*s12*s14**3*s23**2*s24**2 + 4*s12*
     &     s14**3*s23**3*s24 + 2*s12*s14**3*s23**4 + s12*s23**2*s24**2*
     &     s34**3 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s34**3 + 6*
     &     s12**2*s14*s23**2*s24*s34**2 + 6*s12**2*s14*s23**3*s34**2 + 8
     &     *s12**2*s14**2*s23**2*s24*s34 + 8*s12**2*s14**2*s23**3*s34 + 
     &     4*s12**2*s14**3*s23**2*s24 + 4*s12**2*s14**3*s23**3 + 2*
     &     s12**2*s23**2*s24*s34**3 + 2*s12**2*s23**3*s34**3 + 3*s12**3*
     &     s14*s23**2*s34**2 + 4*s12**3*s14**2*s23**2*s34 + 2*s12**3*
     &     s14**3*s23**2 + s12**3*s23**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * ( 4*s12*s14*s23*s34**5 + 3*s12*
     &     s14*s23**2*s34**4 + 6*s12*s14**2*s23*s34**4 + 3*s12*s14**2*
     &     s23**2*s34**3 + 5*s12*s14**3*s23*s34**3 + 2*s12*s14**3*s23**2
     &     *s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s34**6 + s12*
     &     s23**2*s34**5 - 12*s12**2*s14*s23*s34**4 - 3*s12**2*s14*
     &     s23**2*s24*s34**2 - 2*s12**2*s14*s23**2*s24**2*s34 - 12*
     &     s12**2*s14*s23**2*s34**3 - 12*s12**2*s14**2*s23*s34**3 - 2*
     &     s12**2*s14**2*s23**2*s24*s34 - 12*s12**2*s14**2*s23**2*s34**2
     &     - 4*s12**2*s14**3*s23*s34**2 - 8*s12**2*s14**3*s23**2*s34 - 
     &     5*s12**2*s23*s34**5 + s12**2*s23**2*s24*s34**3 - s12**2*
     &     s23**2*s24**2*s34**2 - 4*s12**2*s23**2*s34**4 + 12*s12**3*s14
     &     *s23*s34**3 - 4*s12**3*s14*s23**2*s24*s34 + 12*s12**3*s14*
     &     s23**2*s34**2 + 6*s12**3*s14**2*s23*s34**2 - 4*s12**3*s14**2*
     &     s23**2*s24 + 9*s12**3*s23*s34**4 - 3*s12**3*s23**2*s24*s34**2
     &     + 6*s12**3*s23**2*s34**3 - 4*s12**4*s14*s23*s34**2 - 8*
     &     s12**4*s14*s23**2*s34 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 7*s12**4*s23*s34**3 - 4*
     &     s12**4*s23**2*s34**2 + 2*s12**5*s23*s34**2 )
      wt = wt + s134**(-1) * ( 12*s12*s14*s23*s24*s34**3 + 6*s12*s14*
     &     s23*s24**2*s34**2 + s12*s14*s23*s24**3*s34 + 7*s12*s14*s23**2
     &     *s24*s34**2 - 6*s12*s14*s23**2*s24**2*s34 - 5*s12*s14*s23**2*
     &     s34**3 - 8*s12*s14*s23**3*s24*s34 + 14*s12*s14*s23**3*s34**2
     &     - 3*s12*s14*s23**4*s34 + 12*s12*s14**2*s23*s24*s34**2 + 3*
     &     s12*s14**2*s23*s24**2*s34 + 8*s12*s14**2*s23**2*s24*s34 - 4*
     &     s12*s14**2*s23**2*s24**2 - 8*s12*s14**2*s23**2*s34**2 - 4*s12
     &     *s14**2*s23**3*s24 + 11*s12*s14**2*s23**3*s34 + 4*s12*s14**3*
     &     s23*s24*s34 + 4*s12*s14**3*s23**2*s24 - 4*s12*s14**3*s23**2*
     &     s34 + 4*s12*s14**3*s23**3 + 4*s12*s23*s24*s34**4 + 3*s12*s23*
     &     s24**2*s34**3 + s12*s23*s24**3*s34**2 + 3*s12*s23**2*s24*
     &     s34**3 - 2*s12*s23**2*s24**2*s34**2 - s12*s23**2*s34**4 - 4*
     &     s12*s23**3*s24*s34**2 + 3*s12*s23**3*s34**3 - 2*s12*s23**4*
     &     s34**2 + 2*s12**2*s14*s23*s24*s34**2 + 3*s12**2*s14*s23*
     &     s24**2*s34 + 14*s12**2*s14*s23*s34**3 - 15*s12**2*s14*s23**2*
     &     s24*s34 )
      wt = wt + s134**(-1) * ( 14*s12**2*s14*s23**2*s34**2 - 11*s12**2*
     &     s14*s23**3*s34 + s12**2*s14**2*s23*s24*s34 + 13*s12**2*s14**2
     &     *s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 + 9*s12**2*s14**2*
     &     s23**2*s34 + 4*s12**2*s14**3*s23*s34 + 4*s12**2*s14**3*s23**2
     &     + 4*s12**2*s23*s24**2*s34**2 + 6*s12**2*s23*s34**4 - 5*
     &     s12**2*s23**2*s24*s34**2 + 3*s12**2*s23**2*s34**3 - 5*s12**2*
     &     s23**3*s34**2 + 4*s12**3*s14*s23*s24*s34 - 6*s12**3*s14*s23*
     &     s34**2 - 14*s12**3*s14*s23**2*s34 - 2*s12**3*s14**2*s23*s34
     &     + 7*s12**3*s23*s24*s34**2 - 7*s12**3*s23*s34**3 - 3*s12**3*
     &     s23**2*s34**2 + 2*s12**4*s14*s23*s34 + 6*s12**4*s23*s34**2 - 
     &     3*s14*s23**2*s24*s34**3 + 4*s14*s23**2*s24**2*s34**2 - s14*
     &     s23**2*s24**3*s34 + 6*s14*s23**3*s24*s34**2 - 3*s14*s23**3*
     &     s24**2*s34 - s14*s23**3*s34**3 - 3*s14*s23**4*s24*s34 + 2*s14
     &     *s23**4*s34**2 - s14*s23**5*s34 - s14**2*s23**2*s24*s34**2 + 
     &     2*s14**2*s23**2*s24**2*s34 + 3*s14**2*s23**3*s24*s34 - 2*
     &     s14**2*s23**3*s34**2 )
      wt = wt + s134**(-1) * ( 2*s14**2*s23**4*s34 + s14**3*s23**2*s24*
     &     s34 + s14**3*s23**2*s34**2 - s14**3*s23**3*s34 + s14**4*
     &     s23**2*s34 )
      wt = wt + s234**(-2) * ( 8*s12*s13*s14**2*s23*s34**3 + 4*s12*s13*
     &     s14**2*s23**2*s24**2 + 8*s12*s13*s14**2*s23**2*s34**2 + 4*s12
     &     *s13*s14**2*s34**4 + 4*s12*s13**2*s14*s23*s34**3 + 2*s12*
     &     s13**2*s14*s23**2*s24**2 + 4*s12*s13**2*s14*s23**2*s34**2 + 2
     &     *s12*s13**2*s14*s34**4 + 4*s12*s14**3*s23*s34**3 + 2*s12*
     &     s14**3*s23**2*s24**2 + 4*s12*s14**3*s23**2*s34**2 + 2*s12*
     &     s14**3*s34**4 + 8*s12**2*s13*s14*s23*s34**3 + 4*s12**2*s13*
     &     s14*s23**2*s24**2 + 8*s12**2*s13*s14*s23**2*s34**2 + 4*s12**2
     &     *s13*s14*s34**4 + 8*s12**2*s14**2*s23*s34**3 + 4*s12**2*
     &     s14**2*s23**2*s24**2 + 8*s12**2*s14**2*s23**2*s34**2 + 4*
     &     s12**2*s14**2*s34**4 + 4*s12**3*s14*s23*s34**3 + 2*s12**3*s14
     &     *s23**2*s24**2 + 4*s12**3*s14*s23**2*s34**2 + 2*s12**3*s14*
     &     s34**4 )
      wt = wt + s234**(-1) * ( 5*s12*s13*s14*s23*s34**3 + 4*s12*s13*s14
     &     *s23**2*s24**2 + 4*s12*s13*s14*s23**2*s34**2 + 4*s12*s13*s14*
     &     s34**4 - 10*s12*s13*s14**2*s23*s34**2 - 4*s12*s13*s14**2*
     &     s23**2*s24 - 4*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &     s34**3 + 6*s12*s13*s23*s34**4 - 4*s12*s13*s23**2*s24*s34**2
     &     + s12*s13*s23**2*s24**2*s34 + 5*s12*s13*s23**2*s34**3 - 8*
     &     s12*s13**2*s14*s23*s34**2 - 2*s12*s13**2*s14*s23**2*s34 - 4*
     &     s12*s13**2*s14*s34**3 + 7*s12*s13**2*s23*s34**3 - 3*s12*
     &     s13**2*s23**2*s24*s34 + 5*s12*s13**2*s23**2*s34**2 + 6*s12*
     &     s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 - 5*s12*s14*s23*
     &     s34**4 + 3*s12*s14*s23**2*s24*s34**2 - s12*s14*s23**2*s24**2*
     &     s34 - 3*s12*s14*s23**2*s34**3 + 8*s12*s14**2*s23*s34**3 - 3*
     &     s12*s14**2*s23**2*s24*s34 + 4*s12*s14**2*s23**2*s24**2 + 15*
     &     s12*s14**2*s23**2*s34**2 + 4*s12*s14**2*s34**4 - 16*s12*
     &     s14**3*s23*s34**2 - 4*s12*s14**3*s23**2*s24 - 6*s12*s14**3*
     &     s23**2*s34 )
      wt = wt + s234**(-1) * (  - s12*s23**2*s24*s34**3 + s12*s23**2*
     &     s24**2*s34**2 - 12*s12**2*s13*s14*s23*s34**2 - 12*s12**2*s13*
     &     s14*s23**2*s34 - 4*s12**2*s13*s14*s34**3 - s12**2*s13*s23**2*
     &     s24*s34 + s12**2*s13*s23**2*s34**2 + 10*s12**2*s13**2*s23*
     &     s34**2 + 6*s12**2*s13**2*s23**2*s34 + 17*s12**2*s14*s23*
     &     s34**3 + s12**2*s14*s23**2*s24*s34 + 4*s12**2*s14*s23**2*
     &     s24**2 + 19*s12**2*s14*s23**2*s34**2 + 4*s12**2*s14*s34**4 - 
     &     10*s12**2*s14**2*s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 - 6*
     &     s12**2*s14**2*s23**2*s34 + 6*s12**2*s23*s34**4 - 2*s12**2*
     &     s23**2*s24*s34**2 + s12**2*s23**2*s24**2*s34 + 5*s12**2*
     &     s23**2*s34**3 + 10*s12**3*s13*s23*s34**2 + 4*s12**3*s13*
     &     s23**2*s34 - 12*s12**3*s14*s23*s34**2 - 14*s12**3*s14*s23**2*
     &     s34 - 7*s12**3*s23*s34**3 + 2*s12**3*s23**2*s24*s34 - 4*
     &     s12**3*s23**2*s34**2 + 6*s12**4*s23*s34**2 + 2*s12**4*s23**2*
     &     s34 + s13*s14*s23*s34**4 + 2*s13*s14*s23**2*s24*s34**2 + 6*
     &     s13*s14*s23**2*s24**2*s34 )
      wt = wt + s234**(-1) * ( 2*s13*s14*s23**2*s34**3 + s13*s14**2*s23
     &     *s34**3 + 2*s13*s14**2*s23**2*s34**2 + 4*s13*s14**3*s23*
     &     s34**2 + 10*s13*s14**3*s23**2*s34 + 3*s13**2*s14*s23*s34**3
     &     - 7*s13**2*s14*s23**2*s24*s34 + s13**2*s14*s23**2*s34**2 + 6
     &     *s13**2*s14**2*s23*s34**2 + 10*s13**2*s14**2*s23**2*s34 + 4*
     &     s13**3*s14*s23*s34**2 + 6*s13**3*s14*s23**2*s34 + s14*s23**2*
     &     s24*s34**3 + 2*s14*s23**2*s24**2*s34**2 + s14**2*s23*s34**4
     &     + 4*s14**2*s23**2*s24*s34**2 + 6*s14**2*s23**2*s24**2*s34 + 
     &     2*s14**2*s23**2*s34**3 - 2*s14**3*s23*s34**3 + 7*s14**3*
     &     s23**2*s24*s34 + s14**3*s23**2*s34**2 + 2*s14**4*s23*s34**2
     &     + 6*s14**4*s23**2*s34 )
      wt = wt + 22*s12*s13*s14*s23*s24*s34 + 14*s12*s13*s14*s23*s34**2
     &     + 12*s12*s13*s14*s23**2*s34 - 8*s12*s13*s14*s34**3 + 14*s12*
     &     s13*s14**2*s23*s34 + 14*s12*s13*s23*s24*s34**2 + 6*s12*s13*
     &     s23*s24**2*s34 + 4*s12*s13*s23*s34**3 + 15*s12*s13*s23**2*s24
     &     *s34 + 15*s12*s13*s23**2*s34**2 + 12*s12*s13*s23**3*s34 + 14*
     &     s12*s13**2*s14*s23*s34 + 2*s12*s13**2*s14*s34**2 + 9*s12*
     &     s13**2*s23*s24*s34 + 11*s12*s13**2*s23*s34**2 + 18*s12*s13**2
     &     *s23**2*s34 + 4*s12*s13**3*s23*s34 + s12*s14*s23*s24*s34**2
     &     + 9*s12*s14*s23*s24**2*s34 + 5*s12*s14*s23*s34**3 + 6*s12*
     &     s14*s23**2*s24*s34 + 2*s12*s14*s23**2*s24**2 + 16*s12*s14*
     &     s23**2*s34**2 - 3*s12*s14*s23**3*s34 + 2*s12*s14*s34**4 + 14*
     &     s12*s14**2*s23*s24*s34 - 8*s12*s14**2*s23*s34**2 - 8*s12*
     &     s14**2*s23**2*s24 + 11*s12*s14**2*s23**2*s34 + 8*s12*s14**3*
     &     s23*s34 + 2*s12*s14**3*s23**2 - s12*s23*s24*s34**3 + s12*s23*
     &     s24**2*s34**2 + s12*s23*s24**3*s34 + 2*s12*s23**2*s24*s34**2
     &     + 5*s12*s23**2*s24**2*s34
      wt = wt + 2*s12*s23**2*s34**3 + 5*s12*s23**3*s24*s34 - 2*s12*
     &     s23**3*s34**2 + 2*s12*s23**4*s34 + 18*s12**2*s13*s14*s23*s34
     &     + 9*s12**2*s13*s23*s24*s34 + 17*s12**2*s13*s23*s34**2 + 18*
     &     s12**2*s13*s23**2*s34 + 6*s12**2*s13**2*s23*s34 + 17*s12**2*
     &     s14*s23*s24*s34 - 9*s12**2*s14*s23*s34**2 - 8*s12**2*s14*
     &     s23**2*s34 + 8*s12**2*s14**2*s23*s34 + 8*s12**2*s23*s24*
     &     s34**2 + 3*s12**2*s23*s24**2*s34 - 3*s12**2*s23*s34**3 + 11*
     &     s12**2*s23**2*s24*s34 + 3*s12**2*s23**2*s34**2 + 6*s12**2*
     &     s23**3*s34 + 4*s12**3*s13*s23*s34 + 10*s12**3*s14*s23*s34 + 4
     &     *s12**3*s23*s24*s34 + 12*s12**3*s23*s34**2 + 8*s12**3*s23**2*
     &     s34 + 2*s12**4*s23*s34 + 16*s13*s14*s23*s24*s34**2 + 6*s13*
     &     s14*s23*s24**2*s34 + 11*s13*s14*s23*s34**3 + 6*s13*s14*s23**2
     &     *s24*s34 + 14*s13*s14*s23**2*s34**2 + 8*s13*s14*s23**3*s34 + 
     &     9*s13*s14**2*s23*s24*s34 + 17*s13*s14**2*s23*s34**2 + 17*s13*
     &     s14**2*s23**2*s34 + 4*s13*s14**3*s23*s34 + 3*s13*s23*s24*
     &     s34**3
      wt = wt + 3*s13*s23*s24**2*s34**2 + s13*s23*s24**3*s34 + s13*s23*
     &     s34**4 + 6*s13*s23**2*s24*s34**2 + 3*s13*s23**2*s24**2*s34 + 
     &     3*s13*s23**2*s34**3 + 3*s13*s23**3*s24*s34 + 3*s13*s23**3*
     &     s34**2 + s13*s23**4*s34 + 9*s13**2*s14*s23*s24*s34 + 15*
     &     s13**2*s14*s23*s34**2 + 18*s13**2*s14*s23**2*s34 + 6*s13**2*
     &     s14**2*s23*s34 + 6*s13**2*s23*s24*s34**2 + 3*s13**2*s23*
     &     s24**2*s34 + 3*s13**2*s23*s34**3 + 6*s13**2*s23**2*s24*s34 + 
     &     6*s13**2*s23**2*s34**2 + 3*s13**2*s23**3*s34 + 4*s13**3*s14*
     &     s23*s34 + 3*s13**3*s23*s24*s34 + 4*s13**3*s23*s34**2 + 4*
     &     s13**3*s23**2*s34 + 2*s13**4*s23*s34 + 5*s14*s23*s24*s34**3
     &     + 5*s14*s23*s24**2*s34**2 + s14*s23*s24**3*s34 + 2*s14*s23*
     &     s34**4 + 3*s14*s23**2*s24*s34**2 + 2*s14*s23**2*s24**2*s34 - 
     &     2*s14*s23**2*s34**3 - s14*s23**3*s24*s34 + 2*s14*s23**3*
     &     s34**2 - s14*s23**4*s34 + 12*s14**2*s23*s24*s34**2 + 3*s14**2
     &     *s23*s24**2*s34 + 5*s14**2*s23*s34**3 + 4*s14**2*s23**2*s24*
     &     s34
      wt = wt + 2*s14**2*s23**2*s34**2 + 5*s14**2*s23**3*s34 + 4*s14**3
     &     *s23*s24*s34 + 10*s14**3*s23*s34**2 + 5*s14**3*s23**2*s34 + 2
     &     *s14**4*s23*s34

      D40i=wt/s34**2/s14/s23**2/s12/s1234**2

      return
      end

************************************************************************

c     Same as E40, but using yij5 common block.
c     Normalised to s1234.
      real(8) function E40i(i1,i3,i4,i5)
      implicit real(8)(a-h,o-z)
      common/yij5/y(5,5)

      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
      s134=s13+s14+s34
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15

      wt=0d0
      wt = wt
     &     + 4*s13*s14*s34**(-1)*s134*s35 - 4*s13*s14*s34**(-1)*s134*
     &     s35**2*s345**(-1) + s13*s14*s34*s134*s15**(-1)*s35*s45**(-1)
     &     + 2*s13*s14*s34*s134*s15**(-1)*s45**(-1)*s345 - s13*s14*s34*
     &     s134*s15**(-1) + 2*s13*s14*s34*s134*s35*s45**(-1)*s345**(-1)
     &     - s13*s14*s34*s15*s45**(-1) + s13*s14*s34*s35*s45**(-1) + 
     &     s13*s14*s34 + s13*s14*s134*s15**(-1)*s35*s45**(-1)*s345 + s13
     &     *s14*s134*s15**(-1)*s345 - s13*s14**2*s34*s45**(-1) + s13*
     &     s14**2*s134*s15**(-1) + 8*s13*s34**(-1)*s134*s15*s35 - 4*s13*
     &     s34**(-1)*s134*s15*s35**2*s345**(-1) - 4*s13*s34**(-1)*s134*
     &     s15*s345 + 4*s13*s34**(-1)*s134*s35*s345 - 4*s13*s34**(-1)*
     &     s134*s35**2 - 4*s13*s34**(-1)*s134*s45*s345 + s13*s34*s134*
     &     s15**(-1)*s345 + 2*s13*s34*s134*s15*s35*s45**(-1)*s345**(-1)
     &     - 2*s13*s34*s134*s15*s45**(-1) + 2*s13*s34*s134*s35*
     &     s45**(-1) - 2*s13*s34*s134*s45**(-1)*s345 - s13*s34*s15**(-1)
     &     *s45*s345
      wt = wt + s13*s34*s15*s35*s45**(-1) - s13*s34*s15*s45**(-1)*s345
     &     - 3*s13*s34*s15 - 3*s13*s34*s345 + 3*s13*s134*s15**(-1)*s35*
     &     s345 + s13*s134*s15**(-1)*s45*s345 + 6*s13*s134*s15 + 2*s13*
     &     s134*s35 + 3*s13*s134*s345 + s13**2*s14*s34*s134*s15**(-1)*
     &     s45**(-1) + s13**2*s14*s134*s15**(-1)*s45**(-1)*s345 + s13**2
     &     *s14*s134*s15**(-1) + 4*s13**2*s34**(-1)*s134*s35 - 2*s13**2*
     &     s34**(-1)*s134*s35**2*s345**(-1) - 2*s13**2*s34**(-1)*s134*
     &     s345 + s13**2*s34*s134*s35*s45**(-1)*s345**(-1) - s13**2*s34*
     &     s134*s45**(-1) - s13**2*s34 + s13**2*s134*s15**(-1)*s35 + 2*
     &     s13**2*s134*s15**(-1)*s345 + 4*s13**2*s134 + s13**3*s134*
     &     s15**(-1) - 4*s14*s34**(-1)*s134*s15*s35**2*s345**(-1) + 4*
     &     s14*s34**(-1)*s134*s15*s345 + 4*s14*s34**(-1)*s134*s35*s345
     &     - 4*s14*s34**(-1)*s134*s35**2 + 4*s14*s34**(-1)*s134*s45*
     &     s345 + 8*s14*s34**(-1)*s15*s45*s345 - 4*s14*s34**(-1)*s15**2*
     &     s35 + 4*s14*s34**(-1)*s15**2*s345 + 4*s14*s34**(-1)*s35*s45*
     &     s345
      wt = wt + 4*s14*s34**(-1)*s45**2*s345 + s14*s34*s134*s15**(-1)*
     &     s35*s45**(-1)*s345 + 2*s14*s34*s134*s15**(-1)*s345 + 2*s14*
     &     s34*s134*s15*s35*s45**(-1)*s345**(-1) + 3*s14*s34*s134*s15*
     &     s45**(-1) + s14*s34*s134*s35*s45**(-1) + 2*s14*s34*s134*
     &     s45**(-1)*s345 - s14*s34*s134 + s14*s34*s15**(-1)*s35*s345 + 
     &     2*s14*s34*s15**(-1)*s45*s345 + s14*s34*s15*s45**(-1)*s345 + 4
     &     *s14*s34*s15 + 3*s14*s34*s15**2*s45**(-1) + 6*s14*s34*s345 - 
     &     4*s14*s134**(-1)*s15*s35*s345 - 4*s14*s134**(-1)*s15*s45*s345
     &     - 2*s14*s134**(-1)*s15**2*s345 - 4*s14*s134**(-1)*s35*s45*
     &     s345 - 2*s14*s134**(-1)*s35**2*s345 - 2*s14*s134**(-1)*s45**2
     &     *s345 - s14*s134*s15**(-1)*s35*s345 + s14*s134*s15**(-1)*s45*
     &     s345 - 4*s14*s134*s35 + 2*s14*s134*s345 - s14*s15**(-1)*
     &     s35**2*s345 + s14*s15**(-1)*s45**2*s345 - s14*s15*s35*
     &     s45**(-1)*s345 - 2*s14*s15*s35 - s14*s15*s345 - s14*s15**2*
     &     s45**(-1)*s345 - 7*s14*s35*s345 + s14*s45*s345 - 4*s14**2*
     &     s34**(-1)*s134**(-1)*s15*s35*s345
      wt = wt - 4*s14**2*s34**(-1)*s134**(-1)*s15*s45*s345 - 2*s14**2*
     &     s34**(-1)*s134**(-1)*s15**2*s345 - 4*s14**2*s34**(-1)*
     &     s134**(-1)*s35*s45*s345 - 2*s14**2*s34**(-1)*s134**(-1)*
     &     s35**2*s345 - 2*s14**2*s34**(-1)*s134**(-1)*s45**2*s345 - 2*
     &     s14**2*s34**(-1)*s134*s35**2*s345**(-1) - 4*s14**2*s34**(-1)*
     &     s15*s345 - 4*s14**2*s34**(-1)*s35*s345 - 4*s14**2*s34**(-1)*
     &     s45*s345 + 2*s14**2*s34*s134*s15**(-1)*s45**(-1)*s345 + 
     &     s14**2*s34*s134*s35*s45**(-1)*s345**(-1) + 4*s14**2*s34*s134*
     &     s45**(-1) + 3*s14**2*s34*s15*s45**(-1) - s14**2*s34*s45**(-1)
     &     *s345 - s14**2*s34 - s14**2*s134*s15**(-1)*s35 + 4*s14**2*
     &     s134*s15**(-1)*s345 + 6*s14**2*s134 + 2*s14**2*s15**(-1)*s35*
     &     s345 + 2*s14**2*s15**(-1)*s45*s345 - 2*s14**2*s15*s45**(-1)*
     &     s345 + 8*s14**2*s15 - s14**2*s35*s45**(-1)*s345 + 7*s14**2*
     &     s345 + s14**3*s34*s134*s15**(-1)*s45**(-1) + s14**3*s34*
     &     s45**(-1) + s14**3*s134*s15**(-1)*s45**(-1)*s345 + s14**3*
     &     s134*s15**(-1)
      wt = wt - 2*s14**3*s45**(-1)*s345 + 4*s34**(-1)*s134*s15*s35*s345
     &     - 4*s34**(-1)*s134*s15*s35**2 - 4*s34**(-1)*s134*s15*s45*
     &     s345 + 4*s34**(-1)*s134*s15**2*s35 - 2*s34**(-1)*s134*s15**2*
     &     s35**2*s345**(-1) - 2*s34**(-1)*s134*s15**2*s345 - 2*
     &     s34**(-1)*s134*s45**2*s345 - 2*s34*s134**(-1)*s15*s35*s345 - 
     &     2*s34*s134**(-1)*s15*s45*s345 - s34*s134**(-1)*s15**2*s345 - 
     &     2*s34*s134**(-1)*s35*s45*s345 - s34*s134**(-1)*s35**2*s345 - 
     &     s34*s134**(-1)*s45**2*s345 + s34*s134*s15**(-1)*s35*s345 + 
     &     s34*s134*s15**(-1)*s45*s345 + s34*s134*s15*s35*s45**(-1) + 
     &     s34*s134*s15**2*s35*s45**(-1)*s345**(-1) + 2*s34*s134*s345 - 
     &     s34*s15**(-1)*s35*s45*s345 + s34*s15**(-1)*s45**2*s345 + s34*
     &     s15**2*s45**(-1)*s345 - 3*s34*s15**2 + s34*s15**3*s45**(-1)
     &     - 3*s34*s35*s345 + 2*s34*s45*s345 - s34**2*s134*s45**(-1)*
     &     s345 + s134*s15**(-1)*s35*s45*s345 + s134*s15**(-1)*s35**2*
     &     s345 + 6*s134*s15*s345 + 5*s134*s15**2 + 6*s134*s35*s345 + 
     &     s134*s45*s345
      wt = wt + s15*s35*s345 + 2*s15*s35**2 + 7*s15*s45*s345 - 2*s15**2
     &     *s35 + 6*s15**2*s345 + 2*s15**3 + 2*s35*s45*s345 + s35**2*
     &     s345 + 3*s45**2*s345

      E40i=wt/s1345**2/s134/s345/s34

      return
      end

************************************************************************

      function E40G(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
      s134=s13+s14+s34
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15

      call DAK(s34,s45,s35,a,b,c)
      s34t1 = a*s13 + b*s14 + c*s15
      s345t = s345
      s45t1 = s1345 - s345t - s34t1

      E40G= B40i(i1,i3,i4,i5)
      E40G = E40G 
     .     + E30y5map(s35,s45,s34)*Q30y5map(s34t1,s45t1,s345t)

      return
      end


************************************************************************

c     Same as function E40tilde, but depending on i1,..,i4.
      function E40tildi(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      E40tildi = se40tilde(i1,i3,i4,i5)+se40tilde(i1,i4,i3,i5)
      return
      end

************************************************************************

c     Small e40tilde from (6.50).
      function se40tilde(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      s15=y(i1,i5)
      s13=y(i1,i3)
      s35=y(i3,i5)
      s14=y(i1,i4)
      s45=y(i4,i5)
      s34=y(i3,i4)
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15
      
      wt=1/s35/s45*(2*s13*s34+2*s13*s15+2*s13**2+s34*s15+s15**2)
     .     + s35/s45/s345**2*(2*s13*s14+2*s13*s15+s13**2
     .     + 2*s14*s15+s14**2+s15**2)
     .     + 1/s45/s345*(-2*s13*s14-4*s13*s15+s13*s35
     .     - 2*s13**2-2*s14*s15+s14*s35+s15*s35-2*s15**2)

      se40tilde=wt/s1345**2

      return
      end

c-----------------------------------------------------------------------
c     Auxiliary functions.
c-----------------------------------------------------------------------      

      function FCA(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)

      s123=s12+s13+s23
      y12=s12/s123
      y13=s13/s123
      y23=s23/s123
      
      omy12=1d0-y12
      omy13=1d0-y13
      omy23=1d0-y23

      r1213=log(y12)*log(y13)-log(y12)*log(omy12)-log(y13)*log(omy13)
     .    +pi**2/6d0-rli2(y12)-rli2(y13)
      r1223=log(y12)*log(y23)-log(y12)*log(omy12)-log(y23)*log(omy23)
     .    +pi**2/6d0-rli2(y12)-rli2(y23)
      r1323=log(y23)*log(y13)-log(y23)*log(omy23)-log(y13)*log(omy13)
     .    +pi**2/6d0-rli2(y23)-rli2(y13)
      FCA =
     .  +log(y13)*(y13/(y12+y23))
     .  +log(y23)*(y23/(y12+y13))
     .  +((y12**2+(y12+y13)**2)/y13/y23*r1223
     .                  +(y12**2+(y12+y23)**2)/y13/y23*r1213
     .                  +(y13**2+y23**2)/y13/y23/(y13+y23)
     .    -2d0*log(y12)*(y12**2/(y13+y23)**2+2d0*y12/(y13+y23)) )
     .     -T(y12,y13,y23)*r1323
c     Correction such that finite piece remains after I1 extracted.
      FCA = FCA 
     .     - (10d0/6d0*log(y13*y23)-3d0/2d0*log(y12)-4d0)*T(y12,y13,y23)

      return
      end

************************************************************************

      function FCF(s12,s13,s23)
      implicit real(8)(a-h,o-z)
      parameter(pi=3.141592653589793238d0)

      s123=s12+s13+s23
      y12=s12/s123
      y13=s13/s123
      y23=s23/s123

      omy12=1d0-y12
      omy13=1d0-y13
      omy23=1d0-y23

      r1213=log(y12)*log(y13)-log(y12)*log(omy12)-log(y13)*log(omy13)
     .    +pi**2/6d0-rli2(y12)-rli2(y13)
      r1223=log(y12)*log(y23)-log(y12)*log(omy12)-log(y23)*log(omy23)
     .    +pi**2/6d0-rli2(y12)-rli2(y23)
      FCF =
     .  +(y12/(y12+y13)+y12/(y12+y23)+(y12+y23)/y13+(y12+y13)/y23)
     .  +log(y13)*((4d0*y12**2+2d0*y12*y13
     .           +4d0*y12*y23+y13*y23)/(y12+y23)**2)
     .  +log(y23)*((4d0*y12**2+2d0*y12*y23
     .           +4d0*y12*y13+y13*y23)/(y12+y13)**2)
     . -2d0*((y12**2+(y12+y13)**2)/y13/y23*r1223
     .                  +(y12**2+(y12+y23)**2)/y13/y23*r1213
     .                  +(y13**2+y23**2)/y13/y23/(y13+y23)
     .    -2d0*log(y12)*(y12**2/(y13+y23)**2+2d0*y12/(y13+y23)) )
     
c     Correction such that finite piece remains after I1 extracted.
      FCF=FCF-8d0*T(y12,y13,y23)-3d0*log(y12)*T(y12,y13,y23)

      return
      end

************************************************************************

      function Rli(x,y)
      implicit real*8(a-z)
      parameter(pi=3.141592653589793238d0)
      Rli = dlog(x)*dlog(y)-dlog(y)*dlog(1d0-y)-dlog(x)*dlog(1d0-x)
     .     +pi**2/6d0-li2(x)-li2(y)
      return
      end

************************************************************************

c     Rlog function as in (5.11) of hep-ph/0505111.
      function Rlog(y,z)
      implicit none
      real(8), intent(in) :: y,z
      real(8)             :: rli2, Rlog
      real(8), parameter  :: pi=3.141592653589793238d0

      Rlog = log(y)*log(z) - log(y)*log(1d0-z)
     .     - log(z)*log(1d0-y) + pi**2/6d0
     .     - rli2(y) - rli2(z)

      return
      end

************************************************************************

      function softfinite(iI,iK,i1,i2,i3)
      implicit real*8(a-h,o-z)
c     This function also comes with 
c     +1/e * ( log(sIK/sI0/sK0) - log(s23/s12/s13) ).

      dlnorm = dlog(sprod(iI,iK))

      x1 = xsoftnew(iI,iK,iI,iK)
      x1 = 1d0
      x2 = xsoftnew(iI,iK,iI,i1)
      x3 = xsoftnew(iI,iK,i1,iK)
      x4 = xsoftnew(iI,iK,i2,i3)
      x5 = xsoftnew(iI,iK,i1,i3)
      x6 = xsoftnew(iI,iK,i2,i1)

      softfinite = -dlnorm*(dlog(x1/x2/x3 /(x4/x5/x6)))
     .     - rli2(dabs(1d0-x1)) - 0.5d0*dlog(x1)**2 
     .     + rli2(dabs(1d0-x2)) + 0.5d0*dlog(x2)**2 
     .     + rli2(dabs(1d0-x3)) + 0.5d0*dlog(x3)**2 
     .     + rli2(dabs(1d0-x4)) + 0.5d0*dlog(x4)**2 
     .     - rli2(dabs(1d0-x5)) - 0.5d0*dlog(x5)**2 
     .     - rli2(dabs(1d0-x6)) - 0.5d0*dlog(x6)**2

      return
      end

************************************************************************

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
      if (xsoftnew.lt.0d0)then
         print *,''
         print*,slm
         print*,sIK
         print*,sIl
         print*,sKl
         print*,sIm
         print*,sKm
      endif
c     Correct for rounding errors.
      if (xsoftnew.gt.1d0) xsoftnew = 1d0
      if (xsoftnew.lt.0d0) xsoftnew = 0d0
      return
      end

************************************************************************

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

************************************************************************

c     Function to calculate soft eikonal.
      function sant(i1,i2,i3)
      implicit real*8(a-h,o-z)
      dimension pa(1:4),pu(1:4),pb(1:4)
      common/tcuts/ymin,y0
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
               pu(i) = p3(i,i2-20)
            enddo
         else
            do i=1,4
               pu(i) = p4(i,i2-10)
            enddo
         endif
      else
         do i=1,4
            pu(i) = p5(i,i2)
         enddo
      endif

      if (i3.gt.10) then
         if (i3.gt.20) then
            do i=1,4
               pb(i) = p3(i,i3-20)
            enddo
         else
            do i=1,4
               pb(i) = p4(i,i3-10)
            enddo
         endif
      else
         do i=1,4
            pb(i) = p5(i,i3)
         enddo
      endif

      yab = 2d0*dot(pa(1),pb(1))
      yau = 2d0*dot(pa(1),pu(1))
      ybu = 2d0*dot(pb(1),pu(1))
      yaub = yab+yau+ybu

      sant = 2d0*yab/yau/ybu

      return
      end

c-----------------------------------------------------------------------
