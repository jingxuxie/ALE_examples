c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Momentum maps.

c----------------------------------------------------------------------
c     Single-unresolved maps.
c----------------------------------------------------------------------

c     Single-unresolved mapping used in Hbb and Hgg.
c     {i1,i2,i3,i4} -> {(i1,i2),(i2,i3),i4}
      subroutine pmap4to3(i1,i2,i3,i4,j1,j2,j3)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,j1,j2,j3
      integer              :: i
      real(8)              :: a,b,c
      real(8)              :: y(4,4)
      real(8)              :: s12,s13,s23,s(3,3)
      real(8)              :: p(1:4,5),ppar(1:4,5)
      real(8)              :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
c     Common blocks.
      common/yij4/y
      common/s3/s12,s13,s23
      common/pmom/p
      common/pcut/ppar
      common/mapmomenta/p5,p4,p3

      do i=1,4
         p4(i,1) = p(i,i1)
         p4(i,2) = p(i,i2)
         p4(i,3) = p(i,i3)
         p4(i,4) = p(i,i4)
      enddo

      call DAK(y(i1,i2),y(i2,i3),y(i1,i3),a,b,c)

      s(j1,j2) =         y(i1,i2)        +y(i1,i3)        +y(i2,i3)
      s(j1,j3) =       a*y(i1,i4)      +b*y(i2,i4)      +c*y(i3,i4)
      s(j2,j3) = (1d0-a)*y(i1,i4)+(1d0-b)*y(i2,i4)+(1d0-c)*y(i3,i4)
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)

      do i=1,4
         ppar(i,j1) =       a*p(i,i1)      +b*p(i,i2)      +c*p(i,i3)
         ppar(i,j2) = (1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)+(1d0-c)*p(i,i3)
         ppar(i,j3) = p(i,i4)
         p3(i,j1) = ppar(i,j1)
         p3(i,j2) = ppar(i,j2)
         p3(i,j3) = ppar(i,j3)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end

************************************************************************      

c     Old single-unresolved mapping. Used only in Zqq process.
c     {i1,i2,i3,i4} -> {(i1,i2),(i2,i3),i4}
      subroutine pmap4to3old(i1,i2,i3,i4,j1,j2,j3)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,j1,j2,j3
      integer              :: i
      real(8)              :: a,b,c
      real(8)              :: y(4,4)
      real(8)              :: s12,s13,s23,s(3,3)
      real(8)              :: p(1:4,5),ppar(1:4,5)
      real(8)              :: p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
c     Common blocks.
      common/yij4/y
      common/s3/s12,s13,s23
      common/pmom/p
      common/pcut/ppar
      common/mapmomenta/p5,p4,p3

      do i=1,4
         p4(i,1) = p(i,i1)
         p4(i,2) = p(i,i2)
         p4(i,3) = p(i,i3)
         p4(i,4) = p(i,i4)
      enddo

      call DAK(y(i1,i2),y(i2,i3),y(i1,i3),a,b,c)

      s(j1,j2) =         y(i1,i2)        +y(i1,i3)        +y(i2,i3)
      s(j1,j3) =       a*y(i1,i4)      +b*y(i2,i4)      +c*y(i3,i4)
      s(j2,j3) = (1d0-a)*y(i1,i4)+(1d0-b)*y(i2,i4)+(1d0-c)*y(i3,i4)
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)

      do i=1,4
         ppar(i,j1) =       a*p(i,i1)      +b*p(i,i2)      +c*p(i,i3)
         ppar(i,j2) = (1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)+(1d0-c)*p(i,i3)
         ppar(i,j3) = p(i,i4)
         p3(i,1) = ppar(i,j1)
         p3(i,2) = ppar(i,j2)
         p3(i,3) = ppar(i,j3)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end

************************************************************************

c     Single-unresolved mapping
c     {i1,i2,i3,i4,i5} -> {(i1,i2),(i2,i3),i4,i5}
      subroutine pmap5to4(i1,i2,i3,i4,i5,j1,j2,j3,j4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5,j1,j2,j3,j4
      integer             :: i
      real(8)             :: a,b,c
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: y(5,5),s(4,4)
      real(8)             :: p(1:4,5),ppar(1:4,5)
      real(8)             :: p5(1:4,5),p4(1:4,4),p3(1:4,3)
c     Common blocks.
      common/yij5/y
      common/s4/s12,s13,s14,s23,s24,s34
      common/pmom/p
      common/pcut/ppar
      common/mapmomenta/p5,p4,p3

      call DAK(y(i1,i2),y(i2,i3),y(i1,i3),a,b,c)

      s(j1,j2) =         y(i1,i2)        +y(i1,i3)        +y(i2,i3)
      s(j1,j3) =       a*y(i1,i4)      +b*y(i2,i4)      +c*y(i3,i4)
      s(j1,j4) =       a*y(i1,i5)      +b*y(i2,i5)      +c*y(i3,i5)
      s(j2,j3) = (1d0-a)*y(i1,i4)+(1d0-b)*y(i2,i4)+(1d0-c)*y(i3,i4)
      s(j2,j4) = (1d0-a)*y(i1,i5)+(1d0-b)*y(i2,i5)+(1d0-c)*y(i3,i5)
      s(j3,j4) = y(i4,i5)
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j4,j1) = s(j1,j4)
      s(j3,j2) = s(j2,j3)
      s(j4,j2) = s(j2,j4)
      s(j4,j3) = s(j3,j4)

      do i=1,4
         ppar(i,j1) =       a*p(i,i1)      +b*p(i,i2)      +c*p(i,i3)
         ppar(i,j2) = (1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)+(1d0-c)*p(i,i3)
         ppar(i,j3) = p(i,i4)
         ppar(i,j4) = p(i,i5)
         p4(i,j1) = ppar(i,j1)
         p4(i,j2) = ppar(i,j2)
         p4(i,j3) = ppar(i,j3)
         p4(i,j4) = ppar(i,j4)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s14 = s(1,4)
      s23 = s(2,3)
      s24 = s(2,4)
      s34 = s(3,4)

      return
      end

c-----------------------------------------------------------------------
c     Double-unresolved maps
c-----------------------------------------------------------------------

c     Double-unresolved mapping
c     {i1,i2,i3,i4} -> {(i1,i2,i3),(i2,i3,i4)}
      subroutine pmap4to2(i1,i2,i3,i4,j1,j2)
      implicit real*8(a-h,o-z)
      common/yij4/y(4,4)
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      call DAK2(y12,y13,y24,y34,y23,y14,a,b,c,d)

      do i=1,4
         ppar(i,j1) =         a*p(i,i1) +       b*p(i,i2)      
     .                +       c*p(i,i3) +       d*p(i,i4)
         ppar(i,j2) =   (1d0-a)*p(i,i1) + (1d0-b)*p(i,i2)
     .                + (1d0-c)*p(i,i3) + (1d0-d)*p(i,i4)
         p3(i,1) = ppar(i,j1)
         p3(i,2) = ppar(i,j2)
      enddo

      return
      end

************************************************************************

c     Double-unresolved mapping
c     {i1,i2,i3,i4,i5} -> {(i1,i2,i3),(i2,i3,i4),i5}
      subroutine pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      call DAK2(y12,y13,y24,y34,y23,y14,a,b,c,d)

      s(j1,j2)=        y(i1,i2) +y(i1,i3) +y(i1,i4)
     .                +y(i2,i3) +y(i2,i4) +y(i3,i4)
      
      s(j1,j3)=      a*y(i1,i5)      +b*y(i2,i5)      
     .              +c*y(i3,i5)      +d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5)+(1d0-b)*y(i2,i5)
     .        +(1d0-c)*y(i3,i5)+(1d0-d)*y(i4,i5)

      s(j2,j1)=s(j1,j2)
      s(j3,j1)=s(j1,j3)
      s(j3,j2)=s(j2,j3)

      do i=1,4
         ppar(i,j1) =         a*p(i,i1) +       b*p(i,i2)      
     .                +       c*p(i,i3) +       d*p(i,i4)
         ppar(i,j2) =   (1d0-a)*p(i,i1) + (1d0-b)*p(i,i2)
     .                + (1d0-c)*p(i,i3) + (1d0-d)*p(i,i4)
         ppar(i,j3) = p(i,i5)
         p3(i,j1) = ppar(i,j1)
         p3(i,j2) = ppar(i,j2)
         p3(i,j3) = ppar(i,j3)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end

c-----------------------------------------------------------------------
c     Iterated single-unresolved maps.
c-----------------------------------------------------------------------

c     Mapping B
c     {i1, i2, i3, i4, i5}
c     -> {(i1,i2),i3,(i2,i4),i5}
c     -> {((i1,i2),i3),(i3,(i2,i4)),i5}.
      subroutine pmap5to4to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/sa3/y14,y12,y24
      common/sb3/wl1l3,wl1l2,wl2l3
      common/sc3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12=y(i1,i2)
      y14=y(i1,i4)
      y24=y(i2,i4)

c     First i2 unresolved, i1,i4 radiators.
      call DAK(y12,y24,y14,a1,b1,c1)
      wl1l3=         y(i1,i2)         +y(i1,i4)         +y(i2,i4)
      wl1l2=      a1*y(i1,i3)      +b1*y(i2,i3)      +c1*y(i4,i3)
      wl2l3=(1d0-a1)*y(i1,i3)+(1d0-b1)*y(i2,i3)+(1d0-c1)*y(i4,i3)
      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i4)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .        +(1d0-c1)*p(i,i4)
         p4(i,2) = p(i,i3)
         p4(i,4) = p(i,i5)
      enddo

c     Now l2 unresolved, l1,l3 radiators.
      call DAK(wl1l2,wl2l3,wl1l3,a2,b2,c2)
      a=a2*a1+c2*(1d0-a1)
      b=a2*b1+c2*(1d0-b1)
      c=b2
      d=a2*c1+c2*(1d0-c1)
      s(j1,j3)= a*y(i1,i5)+b*y(i2,i5)
     .     +c*y(i3,i5)+d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5) +(1d0-b)*y(i2,i5)
     .     +(1d0-c)*y(i3,i5) + (1d0-d)*y(i4,i5)
      s(j1,j2)= y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      do i=1,4
         ppar(i,j1) =      a*p(i,i1)      +b*p(i,i2)
     .        +c*p(i,i3)      +d*p(i,i4)
         ppar(i,j2) = (1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)
     .        +(1d0-c)*p(i,i3)+(1d0-d)*p(i,i4)
         ppar(i,j3) = p(i,i5)
         p3(i,1) = ppar(i,j1)
         p3(i,2) = ppar(i,j2)
         p3(i,3) = ppar(i,j3)
      enddo

      ysum = y12+y14+y24
      y12 = y12/ysum
      y14 = y14/ysum
      y24 = y24/ysum
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)
      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end

************************************************************************

c     Mapping C
c     {i1,i2,i3,i4,i5}
c     -> {(i1,i2),(i2,i3),i4,i5}
c     -> {((i1,i2),(i2,i3),((i2,i3),i4)),i5}
      subroutine pmap5to4to3C(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/sa3/y12,y13,y23
      common/sb3/wl1l2,wl1l3,wl2l3
      common/sc3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5) 
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12 = y(i1,i2)
      y13 = y(i1,i3)
      y23 = y(i2,i3)
      y34 = y(i3,i4)

c     First i2 unresolved, i1,i3 radiators.
c     Yields combined momenta l1 and l3.
      call DAK(y12,y23,y13,a1,b1,c1)
      wl1l3 =         y(i1,i2)         +y(i1,i3)         +y(i2,i3)
      wl1l2 =      a1*y(i1,i4)      +b1*y(i2,i4)      +c1*y(i3,i4)
      wl2l3 =(1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .        +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo

c     Now l3 unresolved, l1,l2 radiators, l4 untouched.
c     Yields j1,j2,j3 with j3=l4=i5.
      call DAK(wl1l3,wl2l3,wl1l2,a2,b2,c2)
      a = a2*a1+b2*(1d0-a1)
      b = a2*b1+b2*(1d0-b1)
      c = a2*c1+b2*(1d0-c1)
      d = c2
      s(j1,j3) =   a*y(i1,i5)     + b*y(i2,i5)   
     .           + c*y(i3,i5)     + d*y(i4,i5)
      s(j2,j3) = (1d0-a)*y(i1,i5) + (1d0-b)*y(i2,i5)    
     .         + (1d0-c)*y(i3,i5) + (1d0-d)*y(i4,i5)
      s(j1,j2) = y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)

      do i=1,4
         ppar(i,j1) = a*p(i,i1)       + b*p(i,i2)
     .              + c*p(i,i3)       + d*p(i,i4)
         ppar(i,j2) = (1d0-a)*p(i,i1) + (1d0-b)*p(i,i2)
     .              + (1d0-c)*p(i,i3) + (1d0-d)*p(i,i4)
         ppar(i,j3) = p(i,i5)
         p3(i,1) = ppar(i,j1)
         p3(i,2) = ppar(i,j2)
         p3(i,3) = ppar(i,j3)
      enddo
      ysum = y12+y13+y23
      y12  = y12/ysum
      y13  = y13/ysum
      y23  = y23/ysum

      wsum = wl1l3+wl1l2+wl2l3

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end

************************************************************************

c     Mapping D
c     {i1,i2,i3,i4,i5}
c     -> {(i1,i2),(i2,i3),i4,i5}
c     -> {((i2,i3),(i1,i2)),((i1,i2),i4),i5}
c     Corresponds to pmap5to4to3C with l1<->l3.
      subroutine pmap5to4to3D(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/sa3/y12,y13,y23
      common/sb3/wl2l3,wl1l2,wl1l3
      common/sc3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5) 
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12 = y(i1,i2)
      y13 = y(i1,i3)
      y23 = y(i2,i3)

c     First i2 unresolved, i1,i3 radiators.
      call DAK(y12,y23,y13,a1,b1,c1)
      wl1l3=         y(i1,i2)         +y(i1,i3)         +y(i2,i3)
      wl1l2=      a1*y(i1,i4)      +b1*y(i2,i4)      +c1*y(i3,i4)
      wl2l3=(1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .        +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo

c     Now l1 unresolved, l2,l3 radiators.
c     (l2=i4), l4=i5 untouched.
      call DAK(wl1l2,wl1l3,wl2l3,a2,b2,c2)
      a = b2*a1+c2*(1d0-a1)
      b = b2*b1+c2*(1d0-b1)
      c = b2*c1+c2*(1d0-c1)
      d = a2
      s(j1,j3) = a*y(i1,i5)         + b*y(i2,i5)   
     .         + c*y(i3,i5)         + d*y(i4,i5)
      s(j2,j3) = (1d0-a)*y(i1,i5)   + (1d0-b)*y(i2,i5)    
     .         + (1d0-c)*y(i3,i5)   + (1d0-d)*y(i4,i5)
      s(j1,j2) = y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)
      do i=1,4
         ppar(i,j1)= a*p(i,i1)        + b*p(i,i2)
     .             + c*p(i,i3)        + d*p(i,i4)
         ppar(i,j2) = (1d0-a)*p(i,i1) + (1d0-b)*p(i,i2)
     .              + (1d0-c)*p(i,i3) + (1d0-d)*p(i,i4)
         ppar(i,j3) = p(i,i5)
         p3(i,1) = ppar(i,j1)
         p3(i,2) = ppar(i,j2)
         p3(i,3) = ppar(i,j3)
      enddo
      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      ysum = y12+y13+y23
      y12  = y12/ysum
      y13  = y13/ysum
      y23  = y23/ysum

      return
      end

************************************************************************

c     Mapping K
c     {i1, i2, i3, i4, i5}
c     -> {(i1,i2),(i2,i3),i4,i5}
c     -> {(i1,i2),((i2,i3),i4),(i4,i5)}
      subroutine pmap5to4to3K(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/sa3/yij,yik,yjk
      common/sb3/wKm,wKl,wlm
      common/sc3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5) 
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      yij=y(i1,i2)
      yjk=y(i2,i3)
      yik=y(i1,i3)

c     First i2 unresolved, i1,i3 radiators.
      call DAK(yij,yjk,yik,a1,b1,c1)
      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2)
     .        +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo
      wKl = (1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
      wlm = y(i4,i5)
      wKm = (1d0-a1)*y(i1,i5)+(1d0-b1)*y(i2,i5)+(1d0-c1)*y(i3,i5)

c     Now:
c     l2=i4=l unresolved
c     l3=   K hard radiator
c     l4=i5=m hard radiator
c     l1      untouched
      call DAK(wKl,wlm,wKm,a2,b2,c2)
      c12 = -2d0*(-1d0 + a1)*(-1d0 + a2)*a2*(-1d0 + b1)
      c13 = -2d0*(-1d0 + a1)*(-1d0 + a2)*a2*(-1d0 + c1)
      c14 = (-1d0 + a1)*(-b2 + a2*(-1d0 + 2d0*b2))
      c15 = (-1d0 + a1)*(-c2 + a2*(-1d0 + 2d0*c2))
      c23 = -2d0*(-1d0 + a2)*a2*(-1d0 + b1)*(-1d0 + c1)
      c24 = (-1d0 + b1)*(-b2 + a2*(-1d0 + 2d0*b2))
      c25 = (-1d0 + b1)*(-c2 + a2*(-1d0 + 2d0*c2))
      c34 = (-b2 + a2*(-1d0 + 2d0*b2))*(-1d0 + c1)
      c35 = (-1d0 + c1)*(-c2 + a2*(-1d0 + 2d0*c2))
      c45 = b2 + c2 - 2d0*b2*c2
      d12 = a2*(a1 + b1 - 2d0*a1*b1)
      d13 = a2*(a1 + c1 - 2d0*a1*c1)
      d14 = a1*b2
      d15 = a1*c2
      d23 = a2*(b1 + c1 - 2d0*b1*c1)
      d24 = b1*b2
      d25 = b1*c2
      d34 = b2*c1
      d35 = c1*c2
      d45 = 0d0
      e12 = (-1d0 + a2)*(-b1 + a1*(-1d0 + 2d0*b1))
      e13 = (-1d0 + a2)*(-c1 + a1*(-1d0 + 2d0*c1))
      e14 = a1 - a1*b2
      e15 = a1 - a1*c2
      e23 = (-1d0 + a2)*(-c1 + b1*(-1d0 + 2d0*c1))
      e24 = b1 - b1*b2
      e25 = b1 - b1*c2
      e34 = c1 - b2*c1
      e35 = c1 - c1*c2
      e45 = 0d0

      s(j1,j2) = c12*y(i1,i2)+c13*y(i1,i3)+c14*y(i1,i4)+c15*y(i1,i5)
     .     + c23*y(i2,i3)+c24*y(i2,i4)+c25*y(i2,i5)
     .     + c34*y(i3,i4)+c35*y(i3,i5)+c45*y(i4,i5)        
      s(j1,j3) = d12*y(i1,i2)+d13*y(i1,i3)+d14*y(i1,i4)+d15*y(i1,i5)
     .     + d23*y(i2,i3)+d24*y(i2,i4)+d25*y(i2,i5)
     .     + d34*y(i3,i4)+d35*y(i3,i5)+d45*y(i4,i5)   
      s(j2,j3) = e12*y(i1,i2)+e13*y(i1,i3)+e14*y(i1,i4)+e15*y(i1,i5)
     .     + e23*y(i2,i3)+e24*y(i2,i4)+e25*y(i2,i5)
     .     + e34*y(i3,i4)+e35*y(i3,i5)+e45*y(i4,i5) 
      s(j2,j1) = s(j1,j2)
      s(j3,j1) = s(j1,j3)
      s(j3,j2) = s(j2,j3)

      do i=1,4
        ppar(i,j1) = a2*( (1d0-a1)*p(i,i1)+(1d0-b1)*p(i,i2)
     .        + (1d0-c1)*p(i,i3) )
     .        + b2*p(i,i4)+c2*p(i,i5)
        ppar(i,j2) = (1d0-a2)*((1d0-a1)*p(i,i1)+(1d0-b1)*p(i,i2)
     .       + (1d0-c1)*p(i,i3))
     .       + (1d0-b2)*p(i,i4)+(1d0-c2)*p(i,i5)
	ppar(i,j3) = a1*p(i,i1)+b1*p(i,i2)+c1*p(i,i3)
        p3(i,1) = ppar(i,j1)
        p3(i,2) = ppar(i,j2)
        p3(i,3) = ppar(i,j3)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      ysum = yij+yjk+yik
      yij  = yij/ysum
      yjk  = yjk/ysum
      yik  = yik/ysum

      return
      end

c----------------------------------------------------------------------
c     Special subroutines needed above.
c----------------------------------------------------------------------

      subroutine DAK(yau,yub,yab,x,y,z)
      implicit real*8(a-h,o-z)
      y=yub/(yau+yub)
      yaub=yau+yub+yab
      rho=yaub*yab+4d0*y*(1d0-y)*yau*yub 
      rho=sqrt(rho/yaub/yab)
      x=(1d0+rho+yub*(1d0+rho-2d0*y)/(yau+yab))/2d0
      z=(1d0-rho+yau*(1d0-rho-2d0*y)/(yub+yab))/2d0
      return
      end

************************************************************************

      subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)
      implicit real*8(a-h,o-z)
      
      ya12b=ya1+ya2+y1b+y2b+y12+yab

      r1 = (y1b+y12)/(ya1+y1b+y12)
      r2 =       y2b/(ya2+y2b+y12)

      rho2 = 1d0
     .     +(r1-r2)**2/yab**2/ya12b**2*
     .     (yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
     .     -2d0*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b))
     .     +((r1*(1d0-r2)+r2*(1d0-r1))
     .     *2d0*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
     .     +4d0*r1*(1d0-r1)*yab*ya1*y1b
     .     +4d0*r2*(1d0-r2)*yab*ya2*y2b)/yab**2/ya12b
      rho = sqrt(rho2)
      
      
      x = 1d0/2d0/(yab+ya1+ya2)*(
     .     (1d0+rho)*ya12b
     .     -(2d0*y1b+y12)*r1
     .     -(2d0*y2b+y12)*r2
     .     +(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      y = 1d0/2d0/(yab+y1b+y2b)*(
     .     (1d0-rho)*ya12b
     .     -(2d0*ya1+y12)*r1
     .     -(2d0*ya2+y12)*r2
     .     -(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      return
      end
      
c----------------------------------------------------------------------
