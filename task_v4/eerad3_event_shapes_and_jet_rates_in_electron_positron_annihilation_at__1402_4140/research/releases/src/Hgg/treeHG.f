c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Tree-level matrix elements for Higgs decays to two gluons plus up
c     to two additional partons.

c     Note:
c     All matrix elements are written with respect to the *full*
c     H -> g g squared matrix element (including coupling factors,
c     colour factors, and symmetry factors).
c     For imemode=0, this contribution is divided out.
c     Hence, all symmetry factors are divided by 1/2.
c     For higher multiplicities, only FullXY matrix elements have
c     colour, coupling, and symmetry factors included.

c-----------------------------------------------------------------------
c     H -> 2j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix elment squared for
c     H -> g(i1) g(i2).
      real(8) function FullA2g0H(p,i1,i2)
      implicit none
      integer, intent(in) :: i1, i2
      real(8), intent(in) :: p(1:4,3)
      real(8)             :: s12
c     External.
      real(8), external   :: dot, A2g0H
      
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      FullA2g0H = A2g0H(s12)

      return
      end

************************************************************************

      real(8) function A2g0H(s12)
      implicit none
      real(8), intent(in) :: s12
      real(8)             :: as,ca,cflo,cf,tr,cn
      real(8)             :: yB,cHGG
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/eecplngs/yB,cHGG

      A2g0H = 1d0/2d0*(cn**2-1d0)*(cHGG**2/2d0)*s12**2

      return
      end
      
c-----------------------------------------------------------------------
c     H -> 3j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> g(i1) g(i2) g(i3).
      real(8) function FullA3g0H(p,i1,i2,i3)
      implicit none
      integer, intent(in) :: i1,i2,i3
      real(8), intent(in) :: p(1:4,4)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external   :: A3g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)*cn

      FullA3g0H = 1d0/3d0*fac*(
     .     + A3g0H(p,i1,i2,i3)
     .     + A3g0H(p,i1,i3,i2)
     .     )

      return
      end      

************************************************************************

c     Tree-level amplitude squared for
c     H -> g(i1) g(i2) g(i3).
      real(8) function A3g0H(p,i1,i2,i3)
      implicit none
      real(8), intent(in) :: p(1:4,4)
      integer, intent(in) :: i1,i2,i3
      integer             :: imemode
      real(8)             :: s12,s13,s23
      real(8)             :: born,ant
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external   ::  dot,F30n,A2g0H

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12+s13+s23)

      ant   = F30n(s12,s13,s23)
      A3g0H = ant*born

      return
      end      
      
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> q(i1) g(i3) qbar(i2).
      real(8) function FullB1g0H(p,i1,i3,i2)
      implicit none
      integer, intent(in) :: i1,i2,i3
      real(8), intent(in) :: p(1:4,4)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external   :: dot,B1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)

      FullB1g0H = 2d0*fac*B1g0H(p,i1,i3,i2)

      return
      end

************************************************************************

c     Tree-level amplitude squared for
c     H -> q(i1) g(i3) qbar(i2).
      real(8) function B1g0H(p,i1,i3,i2)
      implicit none
      integer, intent(in) :: i1,i2,i3
      real(8), intent(in) :: p(1:4,4)
      integer             :: imemode
      real(8)             :: s12,s13,s23
      real(8)             :: born,ant
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external   :: dot,G30n,A2g0H

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12+s13+s23)

      ant   = G30n(s23,s13,s12)
      B1g0H = ant*born

      return
      end      
      
c-----------------------------------------------------------------------
c     H -> 4j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> g(i1) g(i2) g(i3) g(i4).
c     Adapted from NNLOJET (src/process/H/libAH.f).
      real(8) function FullA4g0H(p,i1,i2,i3,i4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: p(1:4,5)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external   :: A4g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac  = (4d0*pi*as)**2*cn**2

      FullA4g0H = 1d0/12d0*fac*(
     .     + A4g0H(p,i1,i2,i3,i4)
     .     + A4g0H(p,i1,i2,i4,i3)
     .     + A4g0H(p,i1,i3,i2,i4)
     .     + A4g0H(p,i1,i3,i4,i2)
     .     + A4g0H(p,i1,i4,i2,i3)
     .     + A4g0H(p,i1,i4,i3,i2)
     .     )

      return
      end

************************************************************************

c     Leading-colour H -> g g g g tree-level matrix element squared.
      real(8) function A4g0H(p,i1,i2,i3,i4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: p(4,5)
      integer             :: i, IHEL
      integer             :: perm(4)
      integer             :: permb(4),permc(4),permd(4)
      integer             :: imemode
      real(8)             :: s1234,amp2,born
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zA4g0Hmmmm, zA4g0Hpmmm
      complex(8), external :: zA4g0Hmmpp, zA4g0Hmpmp

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Fill permutations.
      perm(1)  = i1
      perm(2)  = i2
      perm(3)  = i3
      perm(4)  = i4

      permb(1) = i2
      permb(2) = i3
      permb(3) = i4
      permb(4) = i1

      permc(1) = i3
      permc(2) = i4
      permc(3) = i1
      permc(4) = i2

      permd(1) = i4
      permd(2) = i1
      permd(3) = i2
      permd(4) = i3

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,8
         if (i.eq.1) zamp = zA4g0Hmmmm(perm(1))
         if (i.eq.2) zamp = zA4g0Hpmmm(perm(1))
         if (i.eq.3) zamp = zA4g0Hpmmm(permb(1))
         if (i.eq.4) zamp = zA4g0Hpmmm(permc(1))
         if (i.eq.5) zamp = zA4g0Hpmmm(permd(1))
         if (i.eq.6) zamp = zA4g0Hmmpp(perm(1))
         if (i.eq.7) zamp = zA4g0Hmpmp(perm(1))
         if (i.eq.8) zamp = dconjg(zA4g0Hmmpp(permd(1)))
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s1234**2

      A4g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g g g tree-level amplitudes.

      complex(8) function zA4g0Hmmmm(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s43 = s(j4,j3)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      s56=s12+s13+s14+s23+s24+s34

      zA4g0Hmmmm=s56**2/zb12/zb23/zb34/zb41

      return
      end

************************************************************************

      complex(8) function zA4g0Hpmmm(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56, t123, t234, t124, t134
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s43 = s(j4,j3)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      t123 = s12+s13+s23
      t234 = s23+s24+s34
      t124 = s12+s14+s24
      t134 = s13+s14+s34

      s56  = s12+s13+s14+s23+s24+s34

      zA4g0Hpmmm = -s56**2*za24**4/t124/za12/za14/(za21*zb13+za24*zb43)
     .     /(za41*zb13+za42*zb23)
     .     + (za42*zb21+za43*zb31)**3
     .     /t123/(za41*zb13+za42*zb23)/zb12/zb23
     .     - (za23*zb31+za24*zb41)**3
     .     /t134/zb14/zb34/(za21*zb13+za24*zb43)

      return
      end

************************************************************************

      complex(8) function zA4g0Hmmpp(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      integer    :: perma(4), permb(4)
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB
c     Externals.
      complex(8) :: zAphi4g0mmpp

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j3
      permb(2)=j4
      permb(3)=j1
      permb(4)=j2

      zA4g0Hmmpp = zAphi4g0mmpp(perma(1))
     .     + conjg(zAphi4g0mmpp(permb(1)))
      return
      end

************************************************************************

      complex(8) function zA4g0Hmpmp(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      integer    :: perma(4), permb(4)
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56
      complex(8) :: zi
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB
c     Externals.
      complex(8) :: zAphi4g0mpmp

      zi=(0d0,1d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j2
      permb(2)=j3
      permb(3)=j4
      permb(4)=j1

      zA4g0Hmpmp = zAphi4g0mpmp(perma(1))
     .     + conjg(zAphi4g0mpmp(permb(1)))

      return
      end

************************************************************************

      complex(8) function zAphi4g0mmpp(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56
      complex(8) :: zi
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB

      zi=(0d0,1d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      zAphi4g0mmpp=za12**4/za12/za23/za34/za41

      return
      end

************************************************************************

      complex(8) function zAphi4g0mpmp(perm)
      implicit none
      integer, intent(in)    :: perm(4)
      real(8)                :: s(5,5)
      complex(8)             :: zA(5,5), zB(5,5)
      integer    :: j1,j2,j3,j4
      real(8)    :: s12,s13,s14,s23,s24,s34
      real(8)    :: s21,s31,s41,s32,s42,s43
      real(8)    :: s56
      complex(8) :: zi
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
c     Common blocks.
      common/kin5/s,zA,zB

      zi=(0d0,1d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      zAphi4g0mpmp=za13**4/za12/za23/za34/za41

      return
      end

c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> q(i1) g(i3) g(i4) qbar(i2).
c     Adapted from NNLOJET (src/process/H/libBH.f).
      real(8) function FullB2g0H(p,iq1,i3,i4,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4
      real(8), intent(in) :: p(1:4,5)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: B2g0H,Bt2g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac  = (4d0*pi*as)**2*cn

      FullB2g0H = fac*(
     .     + B2g0H(p,iq1,i3,i4,iqbar2)
     .     + B2g0H(p,iq1,i4,i3,iqbar2)
     .     - 1d0/cn**2*Bt2g0H(p,iq1,i3,i4,iqbar2)
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to H -> g g q qbar.
      real(8) function B2g0H(p,iq1,i3,i4,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4
      real(8), intent(in) :: p(1:4,5)
      integer             :: i,IHEL,NHEL(4,8)
      integer             :: perm(4)
      integer             :: imemode
      real(8)             :: s1234,amp2,born
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zB2g0Hmppp,zB2g0Hmmmp
      complex(8), external :: zB2g0Hmpmp,zB2g0Hmmpp
      complex(8), external :: zB2g0Hpmmm,zB2g0Hpppm
      complex(8), external :: zB2g0Hpmpm,zB2g0Hppmm
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 4) / -1, 1, 1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 4) / -1,-1, 1, 1/
      DATA (NHEL(IHEL,   3),IHEL=1, 4) / -1, 1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 4) / -1,-1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(iq1,iqbar2)+s(iq1,i3)+s(iq1,i4)
     .     +s(iqbar2,i3)+s(iqbar2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Fill permutations.
      perm(1) = iq1
      perm(2) = i3
      perm(3) = i4
      perm(4) = iqbar2

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,8
         zamp = 0d0
         if (i.eq.1) zamp = +zB2g0Hmppp(perm(1))
         if (i.eq.2) zamp = +zB2g0Hmmmp(perm(1))
         if (i.eq.3) zamp = +zB2g0Hmpmp(perm(1))
         if (i.eq.4) zamp = +zB2g0Hmmpp(perm(1))
         if (i.eq.5) zamp = +zB2g0Hpmmm(perm(1))
         if (i.eq.6) zamp = +zB2g0Hpppm(perm(1))
         if (i.eq.7) zamp = +zB2g0Hpmpm(perm(1))
         if (i.eq.8) zamp = +zB2g0Hppmm(perm(1))
         amp2 = amp2 + zamp*conjg(zamp)
      enddo
      amp2 = amp2/2d0/s1234**2

      B2g0H = amp2*born

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> g g q qbar.
      real(8) function Bt2g0H(p,iq1,i3,i4,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4
      real(8), intent(in) :: p(1:4,5)
      integer             :: i,j,ii,numplus,IHEL,NHEL(4,8)
      integer             :: perma(4),permb(4)
      integer             :: imemode
      real(8)             :: s1234,amp2,born
      real(8)             :: s(5,5)
      real(8)             :: as,ca,cflo,cf,tr,cn
      complex(8)          :: zA(5,5),zB(5,5)
      complex(8)          :: zamp
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zB2g0Hmppp,zB2g0Hmmmp,zB2g0HMHV
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 4) / -1, 1, 1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 4) / -1,-1, 1, 1/
      DATA (NHEL(IHEL,   3),IHEL=1, 4) / -1, 1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 4) / -1,-1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(iq1,iqbar2)+s(iq1,i3)+s(iq1,i4)
     .     +s(iqbar2,i3)+s(iqbar2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Fill permutations.
      perma(1) = iq1
      perma(2) = i3
      perma(3) = i4
      perma(4) = iqbar2

      permb(1) = iq1
      permb(2) = i4
      permb(3) = i3
      permb(4) = iqbar2

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,4
         numplus = 0
         do j=1,4
            if (NHEL(j,i).eq.1) numplus = numplus+1
         enddo
         zamp = 0d0
         if (numplus.eq.3)then
            zamp = zB2g0Hmppp(PERMA(1))+zB2g0Hmppp(PERMB(1))
         endif
         if (numplus.eq.1) then
            zamp = zB2g0Hmmmp(PERMA(1))+zB2g0Hmmmp(PERMB(1))
         endif
         if (numplus.eq.2) then
            ii=0
            if (i.eq.2)then
               ii = 3
            endif
            if (i.eq.3)then
               ii = 2
            endif
            zamp = zB2g0HMHV(PERMA(1),NHEL(1,i))
     .           + zB2g0HMHV(PERMB(1),NHEL(1,ii))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s1234**2

      Bt2g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g q qbar amplitudes.

      complex(8) function zB2g0Hmppp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      t123=s12+s13+s23
      t234=s23+s34+s24
      t134=s13+s34+s14
      t124=s12+s24+s14

      s56=s12+s13+s14+s23+s24+s34

      zB2g0Hmppp=-zb42**3*s56**2/t124/zb41/(za31*zb12+za34*zb42)/
     .            (za31*zb14+za32*zb24)
     .           -(za12*zb24+za13*zb34)**2/(za31*zb14+za32*zb24)/
     .            za21/za32
     .           -(za13*zb32+za14*zb42)**2*(za41*zb12+za43*zb32)/
     .            t134/(za31*zb12+za34*zb42)/za41/za43

      return
      end

************************************************************************

      complex(8) function zB2g0HMHV(PERM,HEL)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer hel(4),perm(4)
      integer p(2),m(2)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8) :: zamm21,zamp22,zbmp11,zbpp21
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)    

      l=0
      k=0
      do i=1,4
        if(HEL(i).eq.-1) then
          l=l+1
          m(l)=perm(i)
        endif
        if(HEL(i).eq.1) then
          k=k+1
          p(k)=perm(i)
        endif
      enddo

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      zamm21 = zA(m(2),m(1))
      zamp22 = zA(m(2),p(2))
      zbmp11 = zB(m(1),p(1))
      zbpp21 = zB(p(2),p(1))

      zB2g0HMHV=
     .   zamm21**3*zamp22/za12/za23
     .  /za34/za41
     .  -zbmp11*zbpp21**3/zb21/zb32
     .  /zb43/zb14

      return
      end

************************************************************************

      complex(8) function zB2g0Hmmmp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8) :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      t123=s12+s13+s23
      t234=s23+s34+s24
      t134=s13+s34+s14
      t124=s12+s24+s14

      s56=s12+s13+s14+s23+s24+s34

      zB2g0Hmmmp=(za31*zb14+za32*zb24)**2*(za32*zb21+za34*zb41)/zb12
     .            /zb14/t124/(za31*zb12+za34*zb42)
     .           +s56**2*za13**3/za14/t134/(za13*zb32+za14*zb42)
     .            /(za31*zb12+za34*zb42)
     .     +(za12*zb24+za13*zb34)**2/zb23/zb34/(za13*zb32+za14*zb42)

      return
      end

************************************************************************

      complex(8) function zAphiq2gqmmpp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      zAphiq2gqmmpp=-za12**2*za24/za23/za34/za41

      return
      end

************************************************************************

      complex(8) function zAcphiq2gqmmpp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)
          
      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      zAcphiq2gqmmpp=zb13*zb34**2/zb12/zb23/zb41

      return
      end

************************************************************************

      complex(8) function zB2g0Hmmpp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)

      zB2g0Hmmpp = zAcphiq2gqmmpp(perm(1))+zAphiq2gqmmpp(perm(1))

      return
      end

************************************************************************

      complex(8) function zAphiq2gqmpmp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      zAphiq2gqmpmp = -za13**3/za12/za23/za41

      return
      end

************************************************************************

      complex(8) function zAcphiq2gqmpmp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zA(j1,j2)
      za13 =zA(j1,j3)
      za14 =zA(j1,j4)
      za23 =zA(j2,j3)
      za24 =zA(j2,j4)
      za34 =zA(j3,j4)

      za21 =zA(j2,j1)
      za31 =zA(j3,j1)
      za41 =zA(j4,j1)
      za32 =zA(j3,j2)
      za42 =zA(j4,j2)
      za43 =zA(j4,j3)

      zb12 =zB(j1,j2)
      zb13 =zB(j1,j3)
      zb14 =zB(j1,j4)
      zb23 =zB(j2,j3)
      zb24 =zB(j2,j4)
      zb34 =zB(j3,j4)

      zb21 =zB(j2,j1)
      zb31 =zB(j3,j1)
      zb41 =zB(j4,j1)
      zb32 =zB(j3,j2)
      zb42 =zB(j4,j2)
      zb43 =zB(j4,j3)

      zAcphiq2gqmpmp=zb24**3/zb23/zb34/zb41

      return
      end

************************************************************************

      complex(8) function zB2g0Hmpmp(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)

      zB2g0Hmpmp=zAphiq2gqmpmp(perm(1))+zAcphiq2gqmpmp(perm(1))

      return
      end

************************************************************************

      complex(8) function zAcphiq2gqpmpm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      zAcphiq2gqpmpm=zb24**3/zb23/zb34/zb41

      return
      end

************************************************************************

      complex(8) function zAcphiq2gqppmm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      zAcphiq2gqppmm=zb13*zb34**2/zb12/zb23/zb41

      return
      end

************************************************************************

      complex(8) function zAphiq2gqpmpm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      zAphiq2gqpmpm=-za13**3/za12/za23/za41

      return
      end

************************************************************************

      complex(8) function zAphiq2gqppmm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      zAphiq2gqppmm=-za12**2*za24/za23/za34/za41

      return
      end

************************************************************************

      complex(8) function zB2g0Hpmmm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)
      
      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      t123=s12+s13+s23
      t234=s23+s34+s24
      t134=s13+s34+s14
      t124=s12+s24+s14

      s56=s12+s13+s14+s23+s24+s34

      zB2g0Hpmmm = -zb42**3*s56**2/t124/zb41/(za31*zb12+za34*zb42)/
     .     (za31*zb14+za32*zb24)
     .     -(za12*zb24+za13*zb34)**2/(za31*zb14+za32*zb24)/
     .     za21/za32
     .     -(za13*zb32+za14*zb42)**2*(za41*zb12+za43*zb32)/
     .     t134/(za31*zb12+za34*zb42)/za41/za43

      return
      end

************************************************************************

      complex(8) function zB2g0Hpmpm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)

      zB2g0Hpmpm=zAphiq2gqpmpm(perm(1))+zAcphiq2gqpmpm(perm(1))

      return
      end

************************************************************************

      complex(8) function zB2g0Hppmm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)

      zB2g0Hppmm=zAcphiq2gqppmm(perm(1))+zAphiq2gqppmm(perm(1))

      return
      end

************************************************************************

      complex(8) function zB2g0Hpppm(PERM)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer :: perm(4)
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      s12 =s(j1,j2)
      s13 =s(j1,j3)
      s14 =s(j1,j4)
      s23 =s(j2,j3)
      s24 =s(j2,j4)
      s34 =s(j3,j4)

      s21 =s(j2,j1)
      s31 =s(j3,j1)
      s41 =s(j4,j1)
      s32 =s(j3,j2)
      s42 =s(j4,j2)
      s43 =s(j4,j3)

      za12 =zB(j1,j2)
      za13 =zB(j1,j3)
      za14 =zB(j1,j4)
      za23 =zB(j2,j3)
      za24 =zB(j2,j4)
      za34 =zB(j3,j4)

      za21 =zB(j2,j1)
      za31 =zB(j3,j1)
      za41 =zB(j4,j1)
      za32 =zB(j3,j2)
      za42 =zB(j4,j2)
      za43 =zB(j4,j3)

      zb12 =zA(j1,j2)
      zb13 =zA(j1,j3)
      zb14 =zA(j1,j4)
      zb23 =zA(j2,j3)
      zb24 =zA(j2,j4)
      zb34 =zA(j3,j4)

      zb21 =zA(j2,j1)
      zb31 =zA(j3,j1)
      zb41 =zA(j4,j1)
      zb32 =zA(j3,j2)
      zb42 =zA(j4,j2)
      zb43 =zA(j4,j3)

      t123=s12+s13+s23
      t234=s23+s34+s24
      t134=s13+s34+s14
      t124=s12+s24+s14

      s56=s12+s13+s14+s23+s24+s34

      zB2g0Hpppm=(za31*zb14+za32*zb24)**2*(za32*zb21+za34*zb41)/zb12
     .     /zb14/t124/(za31*zb12+za34*zb42)
     .     +s56**2*za13**3/za14/t134/(za13*zb32+za14*zb42)
     .     /(za31*zb12+za34*zb42)
     .     +(za12*zb24+za13*zb34)**2/zb23/zb34/(za13*zb32+za14*zb42)
      return
      end

c-----------------------------------------------------------------------
c     H -> q qbar Q Qbar (different flavours).

c     Full matrix element squared for
c     H -> q(i1) Qbar(i4) Q(i3) qbar(i2).
      real(8) function FullC0g0H(p,iq1,iQbar4,iQ3,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4
      real(8), intent(in) :: p(1:4,5)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: C0g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**2

      FullC0g0H = 2d0*fac*C0g0H(p,iq1,iQbar4,iQ3,iqbar2)

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> q(i1) Qbar(i4) Q(i3) qbar(i2).
      real(8) function C0g0H(p,iq1,iQbar4,iQ3,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4
      real(8), intent(in) :: p(1:4,5)
      integer             :: i,IHEL
      integer             :: imemode
      integer             :: nhel(4,2),perm(4)
      real(8)             :: s1234,born,amp2
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zC0g0HMHV
c     Data.
      DATA (nhel(IHEL,   1),IHEL=1, 4) / -1,-1, 1, 1/
      DATA (nhel(IHEL,   2),IHEL=1, 4) / -1, 1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)
     .     +s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iQ3,iQbar4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Fill permutations.
      perm(1) = iq1
      perm(2) = iQbar4
      perm(3) = iQ3
      perm(4) = iqbar2

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,2
         zamp = zC0g0HMHV(perm(1),nhel(1,i))
         amp2 = amp2+2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s1234**2

      C0g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     H -> q qbar q qbar (same-flavour).

c     Full matrix element squared for
c     H -> q(i1) Qbar(i4) Q(i3) qbar(i2).
      real(8) function FullD0g0H(p,iq1,iQbar4,iQ3,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4
      real(8), intent(in) :: p(4,5)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: C0g0H,D0g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac = (4d0*pi*as)**2

      FullD0g0H = 1d0/2d0*fac*(
     .     + C0g0H(p,iq1,iQbar4,iQ3,iqbar2)
     .     + C0g0H(p,iq1,iqbar2,iQ3,iQbar4)
     .     - 1d0/cn*D0g0H(p,iq1,iQbar4,iQ3,iqbar2)
     .     )

      return
      end

************************************************************************

      real(8) function D0g0H(p,iq1,iQbar4,iQ3,iqbar2)
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4
      real(8), intent(in) :: p(4,5)
      integer             :: i, IHEL
      integer             :: imemode
      integer             :: nhel(4,1),perma(4)
      real(8)             :: s1234,born,amp2
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      complex(8)          :: zamp,zampa,zampb
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zD0g0HMHVA,zD0g0HMHVB
c     Data.
      DATA (nhel(IHEL,   1),IHEL=1, 4) /  1,-1, 1,-1/

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)
     .     +s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iQ3,iQbar4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Fill permutations.
      perma(1) = iq1
      perma(2) = iQbar4
      perma(3) = iQ3
      perma(4) = iqbar2

c     Calculate amplitude squared.
      amp2  = 0d0
      zampa = zD0g0HMHVA(perma(1),nhel(1,1))
      zampb = zD0g0HMHVB(perma(1),nhel(1,1))
      zamp  = -2d0*real(zampa*dconjg(zampb))
      amp2  = amp2+2d0*zamp
      amp2 = amp2/2d0/s1234**2

      D0g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> q qbar Q Qbar tree-level amplitudes.

      complex(8) function zC0g0HMHV(perm,HEL)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer hel(4),perm(4)
      integer p(2),m(2),ipset
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8) :: zamm12,zbpp12
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      l=0
      k=0
      do i=1,4
         if (HEL(i).eq.-1)then
            l=l+1
            m(l)=perm(i)
         endif
         if (HEL(i).eq.1)then
            k=k+1
            p(k)=perm(i)
         endif
      enddo

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s43 = s(j4,j3)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      zamm12=zA(m(1),m(2))
      zbpp12=zB(p(1),p(2))

      zC0g0HMHV = zamm12**2/za23/za14+zbpp12**2/zb23/zb14

      return
      end

************************************************************************

      complex(8) function zD0g0HMHVA(perm,HEL)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer hel(4),perm(4)
      integer p(2),m(2),ipset
      common /npars/npars,nspec,n
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8) :: zamm12,zbpp12
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      l=0
      k=0
      do i=1,4
         if (HEL(i).eq.-1)then
            l=l+1
            m(l)=perm(i)
         endif
         if (HEL(i).eq.1)then
            k=k+1
            p(k)=perm(i)
         endif
      enddo

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s43 = s(j4,j3)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      zamm12 = zA(m(1),m(2))
      zbpp12 = zB(p(1),p(2))

      zD0g0HMHVA = zamm12**2/za23/za14+zbpp12**2/zb23/zb14

      return
      end

************************************************************************

      complex(8) function zD0g0HMHVB(perm,HEL)
      implicit double precision (a-h,o-y)
      implicit complex(8) (z)
      integer hel(4),perm(4)
      integer p(2),m(2),ipset
      real(8):: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex(8) :: za12,za13,za14,za23,za24,za34
      complex(8) :: za21,za31,za41,za32,za42,za43
      complex(8) :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8) :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8) :: zamm12,zbpp12
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      l=0
      k=0
      do i=1,4
         if (HEL(i).eq.-1)then
            l=l+1
            m(l)=perm(i)
         endif
         if (HEL(i).eq.1)then
            k=k+1
            p(k)=perm(i)
         endif
      enddo

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s43 = s(j4,j3)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za34 = zA(j3,j4)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za43 = zA(j4,j3)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb34 = zB(j3,j4)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb43 = zB(j4,j3)

      zamm12 = zA(m(1),m(2))
      zbpp12 = zB(p(1),p(2))

      zD0g0HMHVB = zamm12**2/za12/za43+zbpp12**2/zb12/zb43

      return
      end

c-----------------------------------------------------------------------
c     H -> 5j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> g(i1) g(i2) g(i3) g(i4) g(i5).
c     Adapted from NNLOJET (src/process/H/libAH.f).
      real(8) function FullA5g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external   :: A5g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*cn**3

      FullA5g0H = 1d0/60d0*fac*(
     .     + A5g0H(p,i1,i2,i3,i4,i5)
     .     + A5g0H(p,i1,i2,i3,i5,i4)
     .     + A5g0H(p,i1,i2,i4,i3,i5)
     .     + A5g0H(p,i1,i2,i4,i5,i3)
     .     + A5g0H(p,i1,i2,i5,i3,i4)
     .     + A5g0H(p,i1,i2,i5,i4,i3)
     .     + A5g0H(p,i1,i3,i2,i4,i5)
     .     + A5g0H(p,i1,i3,i2,i5,i4)
     .     + A5g0H(p,i1,i4,i2,i3,i5)
     .     + A5g0H(p,i1,i4,i2,i5,i3)
     .     + A5g0H(p,i1,i5,i2,i3,i4)
     .     + A5g0H(p,i1,i5,i2,i4,i3)
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution for
c     H -> g(i1) g(i2) g(i3) g(i4) g(i5).
c     Note:
c     A5g0H(p,i1,i2,i3,i4,i5)
c     = A5g0H(p,i1,i2,i3,i4,i5)+A5g0H(p,i1,i5,i4,i3,i2).
      real(8) function A5g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,j,IHEL,numplus
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zamp,zA(6,6),zB(6,6)
      integer             :: NHEL(5,16),perm(5)
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zAh5gallminus, zAh5gNNMHV, zAh5gNMHV
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1,-1,-1,-1,-1 /
      DATA (NHEL(IHEL,   2),IHEL=1, 5) /  1,-1,-1,-1,-1 /
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1, 1,-1,-1,-1 /
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1, 1,-1,-1 /
      DATA (NHEL(IHEL,   5),IHEL=1, 5) / -1,-1,-1, 1,-1 /
      DATA (NHEL(IHEL,   6),IHEL=1, 5) / -1,-1,-1,-1, 1 /
      DATA (NHEL(IHEL,   7),IHEL=1, 5) /  1, 1,-1,-1,-1 /
      DATA (NHEL(IHEL,   8),IHEL=1, 5) / -1, 1, 1,-1,-1 /
      DATA (NHEL(IHEL,   9),IHEL=1, 5) / -1,-1, 1, 1,-1 /
      DATA (NHEL(IHEL,  10),IHEL=1, 5) / -1,-1,-1, 1, 1 /
      DATA (NHEL(IHEL,  11),IHEL=1, 5) /  1,-1,-1,-1, 1 /
      DATA (NHEL(IHEL,  12),IHEL=1, 5) /  1,-1, 1,-1,-1 /
      DATA (NHEL(IHEL,  13),IHEL=1, 5) / -1, 1,-1, 1,-1 /
      DATA (NHEL(IHEL,  14),IHEL=1, 5) / -1,-1, 1,-1, 1 /
      DATA (NHEL(IHEL,  15),IHEL=1, 5) /  1,-1,-1, 1,-1 /
      DATA (NHEL(IHEL,  16),IHEL=1, 5) / -1, 1,-1,-1, 1 /

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)
     .     + s(i4,i5)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutation.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i3
      perm(4) = i4
      perm(5) = i5

      amp2 = 0d0
      do i=1,16
         numplus = 0
         do j=1,5
            if (NHEL(j,i).eq.1) numplus = numplus+1
         enddo
         if (numplus.eq.0)
     .        zamp = zAh5gallminus(s,zA,zB,perm(1),NHEL(1,i))
         if (numplus.eq.1)
     .        zamp = zAh5gNNMHV(s,zA,zB,perm(1),NHEL(1,i))
         if (numplus.eq.2)
     .        zamp = zAh5gNMHV(s,zA,zB,perm(1),NHEL(1,i))
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/s12345**2

      A5g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g g g g tree-level amplitudes.

      complex(8) function zAh5gallminus(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: perm(5), hel(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

      zAh5gallminus = -s12345**2/zb12/zb23/zb34/zb45/zb51

      return
      end

************************************************************************

      complex(8) function zAh5gNNMHV(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: perm(5), hel(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: permaux(5),helaux(5)
      integer                :: permgood(5),helgood(5)
      integer                :: i,k,l,aux1,aux2,aux3(5),aux4(5)
c     Externals.
      complex(8), external   :: zAh5gpmmmmh

      do i=1,5
         helaux(i)=hel(i)
      enddo

      do i=1,5
         permaux(i)=perm(i)
      enddo

c     Perform cyclic permutations of the helicity configuration
c     until it finds the right configuration: +----.
      do i=1,5
         if( helaux(1) .eq. 1 ) then
            do k=1,5
               helgood(k)=helaux(k)
            enddo
            do l=1,5
               permgood(l)=permaux(l)
            enddo
         endif

c     Do the cyclic permutation.
         aux1=helaux(1)
         aux2=permaux(1)
         do k=1,4
            helaux(k)=helaux(k+1)
            permaux(k)=permaux(k+1)
         enddo
         helaux(5)=aux1
         permaux(5)=aux2
      enddo

      zAh5gNNMHV = zAh5gpmmmmh(s,zA,zB,permgood)

      return
      end

************************************************************************

      complex(8) function zAh5gpmmmmh(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345, t123,t145,t125,t234,t1235,t1234,t1245,t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

c     A.
      zAh5gpmmmmh = s12345**2*za23*(za52*zb21+za53*zb31)**4
     .     /zb12/s23/t123/t1235/(za51*zb14+za52*zb24+za53*zb34)
     .     /(za51*zb13+za52*zb23)
     .     /(t123*zb41+zb45*za52*zb21+zb45*za53*zb31)
c     B.      
     .     + s12345**2*za25**4/zb34/za21/za51/t125/(za21*zb14+za25*zb54)
     .     /(za51*zb13+za52*zb23)
c     C.
     .     - (za52*zb21+za53*zb31+za54*zb41)**3/t1234/zb12/zb23/zb34
     .     /(za51*zb14+za52*zb24+za53*zb34)
c     D(1).
     .     - s12345**2*za45*(za24*zb41+za25*zb51)**4/s45/t145/t1245/zb15
     .     /(za21*zb13+za24*zb43+za25*zb53)/(za21*zb14+za25*zb54)
     .     /(zb13*t145+zb23*(zb14*za42+zb15*za52))
c     D(2).
     .     - za45*(zb14*za42*zb21 + zb14*za43*zb31
     .     + zb15*za52*zb21 + zb15*za53*zb31)**3
     .     /s45/zb12/zb23/zb15/(zb13*t145+zb23*(zb14*za42+zb15*za52))
     .     /(t123*zb41+zb45*za52*zb21+zb45*za53*zb31)
*     D(3).
     .     + za45*(za23*zb31+za24*zb41+za25*zb51)**3/s45/t1345/zb15/zb43
     .     /(za21*zb13+za24*zb43+za25*zb53)

      return
      end

************************************************************************

      complex(8) function zAh5gNMHV(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: perm(5), hel(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: permaux(5), helaux(5)
      integer                :: permgood(5), helgood(5)
      integer                :: i,j,k,l,aux1,aux2,aux3(5),aux4(5)
      complex(8)             :: zamp3
c     Externals.
      complex(8), external   :: zAcphi5gMHVbar
      complex(8), external   :: zAphi5gppmmm, zAphi5gpmpmm

      zamp3 = zAcphi5gMHVbar(s,zA,zB,perm,hel)

      do i=1,5
         helaux(i) = hel(i)
      enddo
      do i=1,5
         permaux(i) = perm(i)
      enddo

c     Perform cyclic permutations of the helicity configuration
c     until it finds the right configuration: ++---;+-+--.
      j = 0
      do i=1,5
         if (helaux(1).eq.1.and.helaux(2).eq.1)then
            j=1
            do k=1,5
               helgood(k)=helaux(k)
            enddo
            do l=1,5
               permgood(l)=permaux(l)
            enddo
         endif

         if (helaux(1).eq.1.and.helaux(2).eq.-1.and.helaux(3).eq.1)then
            j=2
            do k=1,5
               helgood(k)=helaux(k)
            enddo
            do l=1,5
               permgood(l)=permaux(l)
            enddo
         endif

c     Do the cyclic permutation.
         aux1 = helaux(1)
         aux2 = permaux(1)
         do k=1,4
            helaux(k)  = helaux(k+1)
            permaux(k) = permaux(k+1)
         enddo
         helaux(5)  = aux1
         permaux(5) = aux2
      enddo

      if (j.eq.1)then
         zAh5gNMHV = zAphi5gppmmm(s,zA,zB,permgood) + zamp3
      endif
      if (j.eq.2)then
         zAh5gNMHV = zAphi5gpmpmm(s,zA,zB,permgood) + zamp3
      endif

      return
      end

************************************************************************

      complex(8) function zAcphi5gMHVbar(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: perm(5), hel(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      integer    :: i,l,p(2)
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54
      complex(8) :: zbpp

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      l = 0
      do i=1,5
         if (hel(i).eq.1)then
            l = l+1
            p(l) = perm(i)
         endif
      enddo

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      zbpp = zB(p(1),p(2))

      zAcphi5gMHVbar = -zbpp**4/zb12/zb23/zb34/zb45/zb51

      return
      end

************************************************************************

      complex(8) function zAphi5gppmmm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345, t123,t145,t125,t234,t1235,t1234,t1245,t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

c     A(1).
      zAphi5gppmmm = zb12*za35**4*s12345**2/s12/t1235
     .     /(za31*zb14+za32*zb24+za35*zb54)
     .     /(za51*zb14+za52*zb24+za53*zb34)/za23/za15
c     A(2).
     .     + zb12*(za51*zb13*za35 + za51*zb14*za45
     .     + za52*zb23*za35 + za52*zb24*za45)**3
     .     /s12/zb34/za51/(za51*zb14+za52*zb24+za53*zb34)
     .     /(za51*zb13+za52*zb23)/(za25*t234+za15*(za23*zb31+za24*zb41))
c     A(3).
     .     + zb12*(t125*za53+(za51*zb14+za52*zb24)*za43)**3
     .     /s12/t125/t1245/za51
     .     /(za31*zb14+za32*zb24+za35*zb54)/(za21*zb14+za25*zb54)
c     B.
     .     - za45**3*zb21**3*za32/s23/t123/(za42*zb21+za43*zb31)
     .     /(za51*zb13+za52*zb23)
c     C.
     .     + za45*(za34*zb41+za35*zb51)**3
     .     /za23/s45/zb15/(za21*zb14+za25*zb54)/t145
c     D.
     .     - za34**3*(za52*zb21+za53*zb31+za54*zb41)**3
     .     /za23/t234/t1234/(za42*zb21+za43*zb31)
     .     /(za25*t234+za15*(za23*zb31+za24*zb41))

      return
      end

************************************************************************

      complex(8) function zAphi5gpmpmm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: t123, t145, t125, t234, t345
      real(8)    :: s12345, t1235, t1234, t1245, t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

c     A(1).
      zAphi5gpmpmm = s12345**2*za24**4*zb12*za25**4/za15/s12/za34/za32
     .     /(za25*t234+(za23*zb31+za24*zb41)*za15)
     .     /(t125*za42+za43*(za21*zb13+za25*zb53))
     .     /(za23*zb31*za12 + za23*zb35*za52
     .     + za24*zb41*za12 + za24*zb45*za52)
c     A(2).
     .     - zb12*(za21*zb13+za24*zb43+za25*zb53)**3*za25**4
     .     /za15/zb34/s12/(za21*zb14+za25*zb54)
     .     /(za23*zb31*za12 + za23*zb35*za52
     .     + za24*zb41*za12 + za24*zb45*za52)
     .     /(za25*t345-za12*(za53*zb31+za54*zb41))
c     A(3).
     .     - (za41*zb13+za42*zb23 + za45*zb53)**3*za25**4*zb21
     .     /s12/t1235/t125/za51/(za51*zb13+za52*zb23)
     .     /(t125*za42+za43*(za21*zb13+za25*zb53))
c     B.
     .     + za45**3*(za23*zb31+za24*zb41+za25*zb51)**3
     .     /t345/t1345/za34/(za34*zb41+za35*zb51)
     .     /(za54*zb41*za12+za53*zb31*za12+t345*za52)
c     C.
     .     + za45**3*za23*zb31**4/s23/t123/zb21
     .     /(za42*zb21+za43*zb31)/(za51*zb13+za52*zb23)
c     D.
     .     + za45*(za24*zb41+za25*zb51)**4/s45/t145/za23/zb15
     .     /(za34*zb41+za35*zb51)/(za21*zb14+za25*zb54)
c     E.
     .     + za24**4*(za52*zb21+za53*zb31+za54*zb41)**3
     .     /t1234/t234/za23/za34
     .     /(za42*zb21+za43*zb31)
     .     /(za52*t234+za51*(za23*zb31+za24*zb41))

      return
      end

c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
c     Adapted from NNLOJET (src/process/H/libBH.f).
      real(8) function FullB3g0H(p,iq1,i3,i4,i5,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: B3g0H,Bt3g0H,Btt3g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*cn**2

      FullB3g0H = 1d0/3d0*fac*(
     .     + B3g0H(p,iq1,i3,i4,i5,iqbar2)
     .     + B3g0H(p,iq1,i3,i5,i4,iqbar2)
     .     + B3g0H(p,iq1,i4,i3,i5,iqbar2)
     .     + B3g0H(p,iq1,i4,i5,i3,iqbar2)
     .     + B3g0H(p,iq1,i5,i3,i4,iqbar2)
     .     + B3g0H(p,iq1,i5,i4,i3,iqbar2)

     .     - 1d0/cn**2*(
     .     + Bt3g0H(p,iq1,i3,i4,i5,iqbar2)
     .     + Bt3g0H(p,iq1,i3,i5,i4,iqbar2)
     .     + Bt3g0H(p,iq1,i4,i3,i5,iqbar2)
     .     + Bt3g0H(p,iq1,i4,i5,i3,iqbar2)
     .     + Bt3g0H(p,iq1,i5,i3,i4,iqbar2)
     .     + Bt3g0H(p,iq1,i5,i4,i3,iqbar2)
     .     )
     .     + 1d0/cn**2*Btt3g0H(p,iq1,i3,i4,i5,iqbar2)

     .     + 1d0/cn**4*Btt3g0H(p,iq1,i3,i4,i5,iqbar2)
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
      real(8) function B3g0H(p,iq1,i3,i4,i5,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: i,IHEL,NHEL(5,16),perma(5),permb(5)
      integer             :: imemode
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6),zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zB3g0Hmmmmp, zB3g0Hmmmpp
      complex(8), external :: zB3g0Hmpmmp, zB3g0Hmmpmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1,-1,-1,-1, 1 /
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1,-1,-1, 1 /
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1 /
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1,-1, 1, 1 /
      DATA (NHEL(IHEL,   5),IHEL=1, 5) / -1,-1, 1, 1, 1 /
      DATA (NHEL(IHEL,   6),IHEL=1, 5) / -1, 1,-1, 1, 1 /
      DATA (NHEL(IHEL,   7),IHEL=1, 5) / -1, 1, 1,-1, 1 /
      DATA (NHEL(IHEL,   8),IHEL=1, 5) / -1, 1, 1, 1, 1 /

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,i3)+s(iq1,i4)+s(iq1,i5)
     .     + s(iqbar2,i3)+s(iqbar2,i4)+s(iqbar2,i5)
     .     + s(i3,i4)+s(i3,i5)
     .     + s(i4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      perma(1) = iq1
      perma(2) = i3
      perma(3) = i4
      perma(4) = i5
      perma(5) = iqbar2

      permb(1) = iqbar2
      permb(2) = i5
      permb(3) = i4
      permb(4) = i3
      permb(5) = iq1

c     Calculate squared amplitude.
      amp2 = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp = zB3g0Hmmmmp(s,zA,zB,perma(1),NHEL(1,i))
         endif
         if (i.eq.2)then
            zamp = zB3g0Hmpmmp(s,zA,zB,perma(1),NHEL(1,i))
         endif
         if (i.eq.3)then
            zamp = zB3g0Hmmpmp(s,zA,zB,perma(1),NHEL(1,i))
         endif
         if (i.eq.4)then
            zamp = zB3g0Hmmmpp(s,zA,zB,perma(1),NHEL(1,i))
         endif
         if (i.eq.5)then
            zamp = zB3g0Hmmmpp(s,zA,zB,permb(1),NHEL(1,i))
         endif
         if (i.eq.6)then
            zamp = zB3g0Hmmpmp(s,zA,zB,permb(1),NHEL(1,i))
         endif
         if (i.eq.7)then
            zamp = zB3g0Hmpmmp(s,zA,zB,permb(1),NHEL(1,i))
         endif
         if (i.eq.8)then
            zamp = zB3g0Hmmmmp(s,zA,zB,permb(1),NHEL(1,i))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      B3g0H = amp2*born

      return
      end

************************************************************************

c     Sub-leading colour contribution to
c     H -> q(i1) g(i3) g(i4) g(i5) qbar(i2).
c     (one photon like: the last gluon is the photon like).
      real(8) function Bt3g0H(p,iq1,i3,i4,i5,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: i,IHEL,NHEL(5,16)
      integer             :: perma1(5),perma2(5),perma3(5)
      integer             :: permb1(5),permb2(5),permb3(5)
      integer             :: imemode
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zB3g0Hmmmmp, zB3g0Hmmmpp
      complex(8), external :: zB3g0Hmpmmp, zB3g0Hmmpmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1,-1,-1,-1, 1 /
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1,-1,-1, 1 /
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1 /
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1,-1, 1, 1 /
      DATA (NHEL(IHEL,   5),IHEL=1, 5) / -1,-1, 1, 1, 1 /
      DATA (NHEL(IHEL,   6),IHEL=1, 5) / -1, 1,-1, 1, 1 /
      DATA (NHEL(IHEL,   7),IHEL=1, 5) / -1, 1, 1,-1, 1 /
      DATA (NHEL(IHEL,   8),IHEL=1, 5) / -1, 1, 1, 1, 1 /

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,i3)+s(iq1,i4)+s(iq1,i5)
     .     + s(iqbar2,i3)+s(iqbar2,i4)+s(iqbar2,i5)
     .     + s(i3,i4)+s(i3,i5)
     .     + s(i4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      perma1(1) = iq1
      perma1(2) = i3
      perma1(3) = i4
      perma1(4) = i5
      perma1(5) = iqbar2

      perma2(1) = iq1
      perma2(2) = i4
      perma2(3) = i3
      perma2(4) = i5
      perma2(5) = iqbar2

      perma3(1) = iq1
      perma3(2) = i4
      perma3(3) = i5
      perma3(4) = i3
      perma3(5) = iqbar2

      permb1(1) = iqbar2
      permb1(2) = i5
      permb1(3) = i4
      permb1(4) = i3
      permb1(5) = iq1

      permb2(1) = iqbar2
      permb2(2) = i5
      permb2(3) = i3
      permb2(4) = i4
      permb2(5) = iq1

      permb3(1) = iqbar2
      permb3(2) = i3
      permb3(3) = i5
      permb3(4) = i4
      permb3(5) = iq1

c     Calculate squared amplitude.
      amp2 = 0d0
      do i=1,8
         if(i.eq.1) then
            zamp = zB3g0Hmmmmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma3(1),NHEL(1,i))
         endif
         if(i.eq.2) then
            zamp = zB3g0Hmpmmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma3(1),NHEL(1,i))
         endif
         if(i.eq.3) then
            zamp = zB3g0Hmmpmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma3(1),NHEL(1,i))
         endif
         if(i.eq.4) then
            zamp = zB3g0Hmmmpp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma3(1),NHEL(1,i))
         endif
         if(i.eq.5) then
            zamp = zB3g0Hmmmpp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb3(1),NHEL(1,i))
         endif
         if(i.eq.6) then
            zamp = zB3g0Hmmpmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb3(1),NHEL(1,i))
         endif
         if(i.eq.7) then
            zamp = zB3g0Hmpmmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb3(1),NHEL(1,i))
         endif
         if(i.eq.8) then
            zamp = zB3g0Hmmmmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb3(1),NHEL(1,i))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      Bt3g0H = amp2*born

      return
      end

************************************************************************

c     Sub-sub-leading colour contribution to H -> g g g q qbar.
      real(8) function Btt3g0H(p,iq1,i3,i4,i5,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,i3,i4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: i,IHEL,NHEL(5,16)
      integer             :: perma1(5),perma2(5),perma3(5)
      integer             :: perma4(5),perma5(5),perma6(5)
      integer             :: permb1(5),permb2(5),permb3(5)
      integer             :: permb4(5),permb5(5),permb6(5)
      integer             :: imemode
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
c     Externals.
      real(8), external    :: A2g0H
      complex(8), external :: zB3g0Hmmmmp,zB3g0Hmmmpp
      complex(8), external :: zB3g0Hmpmmp,zB3g0Hmmpmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1,-1,-1,-1, 1 /
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1,-1,-1, 1 /
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1 /
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1,-1, 1, 1 /
      DATA (NHEL(IHEL,   5),IHEL=1, 5) / -1,-1, 1, 1, 1 /
      DATA (NHEL(IHEL,   6),IHEL=1, 5) / -1, 1,-1, 1, 1 /
      DATA (NHEL(IHEL,   7),IHEL=1, 5) / -1, 1, 1,-1, 1 /
      DATA (NHEL(IHEL,   8),IHEL=1, 5) / -1, 1, 1, 1, 1 /

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,i3)+s(iq1,i4)+s(iq1,i5)
     .     + s(iqbar2,i3)+s(iqbar2,i4)+s(iqbar2,i5)
     .     + s(i3,i4)+s(i3,i5)
     .     + s(i4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      perma1(1) = iq1
      perma1(2) = i3
      perma1(3) = i4
      perma1(4) = i5
      perma1(5) = iqbar2

      permb1(1) = iqbar2
      permb1(2) = i5
      permb1(3) = i4
      permb1(4) = i3
      permb1(5) = iq1

      perma2(1) = iq1
      perma2(2) = i3
      perma2(3) = i5
      perma2(4) = i4
      perma2(5) = iqbar2

      permb2(1) = iqbar2
      permb2(2) = i4
      permb2(3) = i5
      permb2(4) = i3
      permb2(5) = iq1

      perma3(1) = iq1
      perma3(2) = i4
      perma3(3) = i3
      perma3(4) = i5
      perma3(5) = iqbar2

      permb3(1) = iqbar2
      permb3(2) = i5
      permb3(3) = i3
      permb3(4) = i4
      permb3(5) = iq1

      perma4(1) = iq1
      perma4(2) = i4
      perma4(3) = i5
      perma4(4) = i3
      perma4(5) = iqbar2

      permb4(1) = iqbar2
      permb4(2) = i3
      permb4(3) = i5
      permb4(4) = i4
      permb4(5) = iq1

      perma5(1) = iq1
      perma5(2) = i5
      perma5(3) = i3
      perma5(4) = i4
      perma5(5) = iqbar2

      permb5(1) = iqbar2
      permb5(2) = i4
      permb5(3) = i3
      permb5(4) = i5
      permb5(5) = iq1

      perma6(1) = iq1
      perma6(2) = i5
      perma6(3) = i4
      perma6(4) = i3
      perma6(5) = iqbar2

      permb6(1) = iqbar2
      permb6(2) = i3
      permb6(3) = i4
      permb6(4) = i5
      permb6(5) = iq1

      amp2 = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp = zB3g0Hmmmmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma3(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma4(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma5(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,perma6(1),NHEL(1,i))
         endif
         if (i.eq.2)then
            zamp = zB3g0Hmpmmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma3(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma4(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma5(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma6(1),NHEL(1,i))
         endif
         if (i.eq.3)then
            zamp = zB3g0Hmmpmp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma3(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma4(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma5(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma6(1),NHEL(1,i))
         endif
         if(i.eq.4) then
            zamp = zB3g0Hmmmpp(s,zA,zB,perma1(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma2(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,perma3(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,perma4(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma5(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,perma6(1),NHEL(1,i))
         endif
         if (i.eq.5)then
            zamp = zB3g0Hmmmpp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb3(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb4(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb5(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb6(1),NHEL(1,i))
         endif
         if (i.eq.6)then
            zamp = zB3g0Hmmpmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb3(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb4(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb5(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb6(1),NHEL(1,i))
         endif
         if (i.eq.7)then
            zamp = zB3g0Hmpmmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmpmmp(s,zA,zB,permb3(1),NHEL(1,i))
     .           + zB3g0Hmmpmp(s,zA,zB,permb4(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb5(1),NHEL(1,i))
     .           + zB3g0Hmmmpp(s,zA,zB,permb6(1),NHEL(1,i))
         endif
         if (i.eq.8)then
            zamp = zB3g0Hmmmmp(s,zA,zB,permb1(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb2(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb3(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb4(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb5(1),NHEL(1,i))
     .           + zB3g0Hmmmmp(s,zA,zB,permb6(1),NHEL(1,i))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      Btt3g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g g q qbar tree-level amplitudes.

      complex(8) function zB3g0Hmmmmp(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: hel(5), perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345
      real(8)    :: t123, t125, t145, t234, t345
      real(8)    :: t1234, t1235, t1245, t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

      zB3g0Hmmmmp =
c     A.
     .     - s12345**2*za12*(za41*zb15+za42*zb25)**3
     .     *(za42*zb21+za45*zb51)
     .     /s12/t125/t1245/zb15/(za41*zb13+za42*zb23+za45*zb53)
     .     /(za41*zb12+za45*zb52)/((zb51*za14+zb52*za24)*zb43+t125*zb53)
c     B(1).
     .     + za34*(zb53*za31*zb15 + zb53*za32*zb25
     .     + zb54*za41*zb15 + zb54*za42*zb25)**2
     .     *(t345*zb15+zb12*(za23*zb35+za24*zb45))/s34/zb12/zb15/zb45
     .     /(zb25*t345+zb21*(za13*zb35+za14*zb45))
     .     /(t125*zb35+zb34*(za41*zb15+za42*zb25))
c     B(2).
     .     - s12345**2*za34*(za13*zb35+za14*zb45)**3/t1345/s34
     .     /(za13*zb32+za14*zb42+za15*zb52)
     .     /zb45/(zb25*t345+zb21*(za13*zb35+za14*zb45))
     .     /(za14*zb43+za15*zb53)
c     B(3).
     .     - (za12*zb25+za13*zb35+za14*zb45)**2*za34/s34/zb32/zb45
     .     /(za13*zb32+za14*zb42+za15*zb52)
c     C.
     .     +s12345**2*za14**3*zb15/s15/t145/zb23
     .     /(za41*zb12+za45*zb52)/(za14*zb43+za15*zb53)
c     D.
     .     +(za41*zb15+za42*zb25+za43*zb35)**2
     .     *(za42*zb21+za43*zb31+za45*zb51)
     .     /zb12/zb23/zb51/t1235/(za41*zb13+za42*zb23+za45*zb53)

      return
      end

************************************************************************

      complex(8) function zB3g0Hmpmmp(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: hel(5), perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345
      real(8)    :: t123, t125, t145, t234, t345
      real(8)    :: t1234, t1235, t1245, t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

      zB3g0Hmpmmp =
c     A.
     .     - za34*(za13*zb35+za14*zb45)**3/za12/s34/zb45
     .     /(za23*zb35+za24*zb45)/(za14*zb43+za15*zb53)
c     B.
     .     - za34**3*zb25**3/zb15/t125
     .     /(za31*zb15+za32*zb25)/(za41*zb12+za45*zb52)
c     C(1).
     .     + s12345**2*za13**4*za14**3*zb15/s15/za23/za21
     .     /(t145*za13+za23*(za14*zb42+za15*zb52))
     .     /(za12*zb24*za41 + za12*zb25*za51
     .     + za13*zb34*za41 + za13*zb35*za51)
     .     /(t123*za14-za45*(za12*zb25+za13*zb35))
c     C(2).
     .     - zb51*za14**3*(za13*zb32+za14*zb42+za15*zb52)**3/s15/zb23
     .     /(za12*zb24*za41 + za12*zb25*za51
     .     + za13*zb34*za41 + za13*zb35*za51)
     .     /(za14*zb43+za15*zb53)/(za14*t234+za15*(za42*zb25+za43*zb35))
c     C(3).
     .     - (za31*zb12+za34*zb42+za35*zb52)**3*zb15*za41**3/t145/s15
     .     /(za41*zb12+za45*zb52)
     .     /(t145*za31+za32*(zb24*za41+zb25*za51))/t1245
c     D.
     .     + za34**3*(za12*zb25+za13*zb35+za14*zb45)**2/za23/t234
     .     /(za23*zb35+za24*zb45)/(za41*t234+za51*(za42*zb25+za43*zb35))
c     E.
     .     - za13**3*(za41*zb15+za42*zb25+za43*zb35)**2
     .     *(t123*za34+za54*(za31*zb15+za32*zb25))
     .     /za12/za23/t123/t1235/(za31*zb15+za32*zb25)
     .     /(t123*za14+za54*(za12*zb25+za13*zb35))
c     cphi part.
     .     + zb25**3/zb23/zb34/zb45/zb15

      return
      end

************************************************************************

      complex(8) function zB3g0Hmmpmp(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: hel(5), perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345
      real(8)    :: t123, t125, t145, t234, t345
      real(8)    :: t1234, t1235, t1245, t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

      zB3g0Hmmpmp =
c     A.
     .     - za12**2*za34*zb35**3*(za24*zb43+za25*zb53)/s34/t345/zb45
     .     /(za14*zb43+za15*zb53)/(za23*zb35+za24*zb45)
c     B.
     .     -za12*(za41*zb15+za42*zb25)**3*(za42*zb21+za45*zb51)/s12
     .     /t125/za34/zb15/(za31*zb15+za32*zb25)/(za41*zb12+za45*zb52)
c     C(1).
     .     -s12345**2*za24**4*za14**3*zb15/za23/za34/s15
     .     /(t145*za42+za32*(za41*zb13+za45*zb53))
     .     /(za42*zb21*za14 + za42*zb25*za54
     .     + za43*zb31*za14 + za43*zb35*za54)
     .     /(t234*za14+za15*(za42*zb25+za43*zb35))
c     C(2).
     .     + (za21*zb13+za24*zb43+za25*zb53)**3*za14**3
     .     *zb15/t145/s15/t1345
     .     /(za14*zb43+za15*zb53)/(t145*za42+za32*(za41*zb13+za45*zb53))
c     C(3).
     .     - (za41*zb13+za42*zb23+za45*zb53)**3*za14**3*zb15/s15/zb23
     .     /(za41*zb12+za45*zb52)
     .     /(za42*zb21*za14 + za42*zb25*za54
     .     + za43*zb31*za14 + za43*zb35*za54)
     .     /(t123*za14-za45*(za12*zb25+za13*zb35))
c     D.
     .     + za24**4*(za12*zb25+za13*zb35+za14*zb45)**2
     .     /t234/za23/za34/(za23*zb35+za24*zb45)
     .     /(t234*za41+za51*(za42*zb25+za43*zb35))
c     E.
     .     - za12**2*(za41*zb15+za42*zb25+za43*zb35)**2
     .     *(t123*za24+za54*(za21*zb15+za23*zb35))
     .     /za23/t123/t1235/(za31*zb15+za32*zb25)
     .     /(t123*za14+za54*(za12*zb25+za13*zb35))
c     cphi part.
     .     + zb35**3*zb31/zb12/zb23/zb34/zb45/zb51

      return
      end

************************************************************************

      complex(8) function zB3g0Hmmmpp(s,zA,zB,perm,hel)
      implicit none
      integer, intent(in)    :: hel(5), perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12345
      real(8)    :: t123, t125, t145, t234, t345
      real(8)    :: t1234, t1235, t1245, t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+s25+s34+s35+s45

c     A.      
      zB3g0Hmmmpp =
     .     + za15*za23**3*zb54**2*zb14/s15/t145
     .     /(za21*zb14+za25*zb54)/(za34*zb41+za35*zb51)
c     B.      
     .     - za23*(za12*zb24+za13*zb34)**2*(za52*zb24+za53*zb34)
     .     /za51/s23/zb34/t234/(za53*zb32+za54*zb42)
c     C.
     .     + za12**2*za25
     .     *(za31*zb14+za32*zb24+za35*zb54)**3/za51/t1245/t125
     .     /(za21*zb14+za25*zb54)/(za53*t125+za43*(za51*zb14+za52*zb24))
c     D(1).
     .     + zb45*za35*(za32*zb21+za34*zb41+za35*zb51)*(za31*zb14*za43
     .     + za31*zb15*za53 + za32*zb24*za43 + za32*zb25*za53)**2
     .     /zb12/za34/s45
     .     /(za31*zb12+za34*zb42+za35*zb52)/(za34*zb41+za35*zb51)
     .     /(t125*za35+za34*(za51*zb14+za52*zb24))
c     D(2).
     .     - s12345**2*zb45*za13**3*za35/za15/za34/s45/t1345
     .     /(za13*zb32+za14*zb42+za15*zb52)
     .     /(za31*zb12+za34*zb42+za35*zb52)
c     cphi part.
     .     + zb45*za35*(t345*za13+za12*(zb24*za43+zb25*za53))**2
     .     /za34/t345/s45/(za13*zb32+za14*zb42+za15*zb52)
     .     /(za53*zb32+za54*zb42)
     .     + zb45**2*zb41/zb12/zb23/zb34/zb51

      return
      end

c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> q(i1) qbar(i2) Q(i3) Qbar(i4) g(i5) (different flavours).
c     Adapted from NNLOJET (src/process/H/libCDH.f).
      real(8) function FullC1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: C1g0Ha,C1g0Hb,Ct1g0Ha,Ct1g0Hb,Ctt1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*cn

      FullC1g0H = 2d0*fac*(
     .     + C1g0Ha(p,iq1,i5,iQbar4,iQ3,iqbar2)
     .     + C1g0Hb(p,iq1,iQbar4,iQ3,i5,iqbar2)
     .     + 1d0/cn**2*(
     .     + Ct1g0Ha(p,iq1,i5,iqbar2,iQ3,iQbar4)
     .     + Ct1g0Hb(p,iq1,iqbar2,iQ3,i5,iQbar4)
     .     - 2d0*Ctt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
     .     )
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to H -> q g Qbar Q qbar
c     in A1 order.
      real(8) function C1g0Ha(p,iq1,i5,iQbar4,iQ3,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,IHEL,NHEL(5,16),perm(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6),zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Ha1mppmp, zC1g0Ha1mpmpp
      complex(8), external :: zC1g0Ha1mmpmp, zC1g0Ha1mmmpp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1, 1,-1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1,-1, 1, 1/
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1,-1, 1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutation.
      perm(1) = iq1
      perm(2) = i5
      perm(3) = iQbar4
      perm(4) = iQ3
      perm(5) = iqbar2

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,4
         if (i.eq.1)then
            zamp = zC1g0Ha1mppmp(s,zA,zB,perm(1))
         endif
         if (i.eq.2)then
            zamp = zC1g0Ha1mpmpp(s,zA,zB,perm(1))
         endif
         if (i.eq.3)then
            zamp = zC1g0Ha1mmpmp(s,zA,zB,perm(1))
         endif
         if (i.eq.4)then
            zamp = zC1g0Ha1mmmpp(s,zA,zB,perm(1))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      C1g0Ha = born*amp2

      return
      end

************************************************************************

c     Leading-colour contribution to H -> q g Qbar Q qbar
c     in A2 order.
      real(8) function C1g0Hb(p,iq1,iQbar4,iQ3,i5,iqbar2)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,IHEL,NHEL(5,16),perm(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6),zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Ha2mpmpp, zC1g0Ha2mmppp
      complex(8), external :: zC1g0Ha2mpmmp, zC1g0Ha2mmpmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1,-1, 1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1,-1, 1, 1, 1/
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1, 1,-1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1, 1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutation.
      perm(1) = iq1
      perm(2) = iQbar4
      perm(3) = iQ3
      perm(4) = i5
      perm(5) = iqbar2

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,4
         if (i.eq.1)then
            zamp = zC1g0Ha2mpmpp(s,zA,zB,perm(1))
         endif
         if (i.eq.2)then
            zamp = zC1g0Ha2mmppp(s,zA,zB,perm(1))
         endif
         if (i.eq.3)then
            zamp = zC1g0Ha2mpmmp(s,zA,zB,perm(1))
         endif
         if (i.eq.4)then
            zamp = zC1g0Ha2mmpmp(s,zA,zB,perm(1))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      C1g0Hb = born*amp2

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> q g Qbar Q qbar
c     in B1 order.
      real(8) function Ct1g0Ha(p,iq1,i5,iqbar2,iQ3,iQbar4)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,IHEL,NHEL(5,16),perm(5),perma(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Hb1mppmp, zC1g0Hb1mpppm
      complex(8), external :: zC1g0Hb1mmpmp, zC1g0Hb1mmppm
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1, 1,-1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1, 1, 1,-1/
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1, 1, 1,-1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutation.
      perm(1) = iq1
      perm(2) = i5
      perm(3) = iqbar2
      perm(4) = iQ3
      perm(5) = iQbar4

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,4
         if (i.eq.1)then
            zamp = zC1g0Hb1mppmp(s,zA,zB,perm(1))
         endif
         if (i.eq.2)then
            zamp = zC1g0Hb1mpppm(s,zA,zB,perm(1))
         endif
         if (i.eq.3)then
            zamp = zC1g0Hb1mmpmp(s,zA,zB,perm(1))
         endif
         if (i.eq.4)then
            zamp = zC1g0Hb1mmppm(s,zA,zB,perm(1))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      Ct1g0Ha = born*amp2

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> q g Qbar Q qbar
c     in B2 order.
      real(8) function Ct1g0Hb(p,iq1,iqbar2,iQ3,i5,iQbar4)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,IHEL,NHEL(5,16),perm(5),perma(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Hb2mpmpp, zC1g0Hb2mpppm
      complex(8), external :: zC1g0Hb2mpmmp, zC1g0Hb2mppmm
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1,-1, 1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1, 1, 1,-1/
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1, 1,-1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1, 1, 1,-1,-1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutation.
      perm(1) = iq1
      perm(2) = iqbar2
      perm(3) = iQ3
      perm(4) = i5
      perm(5) = iQbar4

      amp2 = 0d0
      do i=1,4
         if (i.eq.1)then
            zamp = zC1g0Hb2mpmpp(s,zA,zB,perm(1))
         endif
         if (i.eq.2)then
            zamp = zC1g0Hb2mpppm(s,zA,zB,perm(1))
         endif
         if (i.eq.3)then
            zamp = zC1g0Hb2mpmmp(s,zA,zB,perm(1))
         endif
         if (i.eq.4)then
            zamp = zC1g0Hb2mppmm(s,zA,zB,perm(1))
         endif
         amp2 = amp2 + 2d0*zamp*dconjg(zamp)
      enddo
      amp2 = amp2/2d0/s12345**2

      Ct1g0Hb = born*amp2

      return
      end

************************************************************************

c     Colour-mixing part of H -> q g Qbar Q qbar.
c     (as (A1+A2)(B1+B2)^* + (B1+B2)(A1+A2)^*.)
      real(8) function Ctt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: imemode
      integer             :: i,IHEL,NHEL(5,16)
      integer             :: perma1(5),perma2(5),permb1(5),permb2(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6)
      complex(8)          :: zA(6,6),zB(6,6)
      complex(8)          :: zamp
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Hb1mppmp, zC1g0Hb2mpmpp
      complex(8), external :: zC1g0Hb1mpppm, zC1g0Hb2mpppm
      complex(8), external :: zC1g0Hb1mmpmp, zC1g0Hb2mpmmp
      complex(8), external :: zC1g0Hb1mmppm, zC1g0Hb2mppmm
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1, 1,-1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1, 1,-1, 1, 1/
      DATA (NHEL(IHEL,   3),IHEL=1, 5) / -1,-1, 1,-1, 1/
      DATA (NHEL(IHEL,   4),IHEL=1, 5) / -1,-1,-1, 1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      permb1(1) = iq1
      permb1(2) = i5
      permb1(3) = iqbar2
      permb1(4) = iQ3
      permb1(5) = iQbar4

      permb2(1) = iq1
      permb2(2) = iqbar2
      permb2(3) = iQ3
      permb2(4) = i5
      permb2(5) = iQbar4

c     Here 4d0*zamp= 2d0*2d0*zamp, the first 2d0 is for double-real
c     part of (A1+A2)*(B1+B2)^\dagger,  which equals to
c     (A1+A2)*(B1+B2)^\dagger+(B1+B2)*(A1+A2)^\dagger.
c     This could also be seen as two times the |A1+A2|^2
c     as A1+A2=B1+B2.
      amp2 = 0d0
      do i=1,4
         if (i.eq.1)then
            zamp = zC1g0Hb1mppmp(s,zA,zB,permb1(1))
     .           - zC1g0Hb2mpmpp(s,zA,zB,permb2(1))
         endif
         if (i.eq.2)then
            zamp = zC1g0Hb1mpppm(s,zA,zB,permb1(1))
     .           - zC1g0Hb2mpppm(s,zA,zB,permb2(1))
         endif
         if (i.eq.3)then
            zamp = zC1g0Hb1mmpmp(s,zA,zB,permb1(1))
     .           - zC1g0Hb2mpmmp(s,zA,zB,permb2(1))
         endif
         if (i.eq.4)then
            zamp = zC1g0Hb1mmppm(s,zA,zB,permb1(1))
     .           - zC1g0Hb2mppmm(s,zA,zB,permb2(1))
         endif
c     The second 2d0 is for the other opposite helicity.         
         amp2 = amp2 + 4d0*zamp*conjg(zamp)
      enddo
c     Additional factor of 1/2 here so that full SLC is given by
c     Ct1g0Ha+Ct1g0Hb-2*Ctt1g0H.
      amp2 = amp2/2d0/s12345**2/2d0

      Ctt1g0H = born*amp2

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g q qbar Q Qbar tree-level amplitudes.

      complex(8) function zC1g0Ha1mppmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: t123,t124,t134,t145,t125,t234,t345
      real(8)    :: t1235,t1234,t1245,t1345
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      real(8)    :: s12345
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t124  = s12+s14+s24
      t134  = s13+s14+s34
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+S25+s34+s35+s45

      zC1g0Ha1mppmp =
c     A.
     .     - (za42*zb25+za43*zb35)**2*(za32*zb25+za34*zb45)
     .     /za23/za34/zb15/t234/(za23*zb35+za24*zb45)
c     B.
     .     + zb23**2*za14**2*zb15*(za14*zb42+za15*zb52)
     .     /t145/s15/(za41*zb12+za45*zb52)/(za14*zb43+za15*zb53)
c     C(1).
     .     - (za13*zb32+za14*zb42+za15*zb52)**2*za34*zb35**2
     .     *(zb23*t345-zb12*(za14*zb43+za15*zb53))
     .     /s34/t1345/t345/(za14*zb43+za15*zb53)
     .     /(zb25*t345-zb12*(za13*zb35+za14*zb45))
c     C(2).
     .     + s12345**2*zb25**3*za34*zb35**3/zb51/s34
     .     /(zb35*t125+zb34*(za41*zb15+za42*zb25))
     .     /(zb53*za31*zb15 + zb53*za32*zb25
     .     + zb54*za41*zb15 + zb54*za42*zb25)
     .     /(zb25*t345-zb12*(za13*zb35+za14*zb45))
c     C(3).
     .     - (za12*zb25+za13*zb35+za14*zb45)**2*za34*zb35**2
     .     /za12/s34/(za23*zb35+za24*zb45)/(zb53*za31*zb15
     .     + zb53*za32*zb25 + zb54*za41*zb15 + zb54*za42*zb25)
c     D.
     .     + zb25**3*(za41*zb13+za42*zb23+za45*zb53)**2
     .     /zb15/t125/(za41*zb12+za45*zb52)
     .     /(zb43*(za41*zb15+za42*zb25)+t125*zb53)
c     phi part.
     .     + za31*za14**2/za12/za23/za34/za51

      return
      end

************************************************************************

      complex(8) function zC1g0Ha1mpmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      real(8)    :: s12345
      real(8)    :: t123,t124,t134,t145,t125,t234,t345
      real(8)    :: t1235,t1234,t1245,t1345
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t124  = s12+s14+s24
      t134  = s13+s14+s34
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+S25+s34+s35+s45

      zC1g0Ha1mpmpp =
c     A(1).
     .     - (za31*zb12+za34*zb42+za35*zb52)**2
     .     *(za41*zb12+za43*zb32+za45*zb52)*za15*zb25**3
     .     /za34/s15/(za41*zb12+za45*zb52)
     .     /(zb25*t345+zb21*(za13*zb35+za14*zb45))
     .     /(zb21*za13*zb32 + zb21*za14*zb42
     .     + zb25*za53*zb32 + zb25*za54*zb42)
c     A(2).
     .     + s12345**2*zb24**3*zb25**3*za15/zb43/s15
     .     /(t125*zb24+(zb21*za13+zb25*za53)*zb34)
     .     /(zb25*t234+zb15*(za13*zb32+za14*zb42))
     .     /(zb21*za13*zb32 + zb21*za14*zb42
     .     + zb25*za53*zb32 + zb25*za54*zb42)
c     A(3).
     .     + (za31*zb14+za32*zb24+za35*zb54)**2*za15*zb25**3
     .     /s15/t125/(za31*zb15+za32*zb25)
     .     /(t125*zb24+(zb21*za13+zb25*za53)*zb34)
c     B.
     .     + za34*zb42**3*(za12*zb25+za13*zb35+za14*zb45)**2
     .     /s34/t234/(za12*zb24+za13*zb34)
     .     /(zb15*(za13*zb32+za14*zb42)+t234*zb25)
c     C.
     .     + zb45**2*(za13*zb32+za14*zb42+za15*zb52)**2
     .     *(zb32*t345+zb12*(za14*zb43+za15*zb53))
     .     /zb34/t345/t1345/(za14*zb43+za15*zb53)
     .     /(zb52*t345+zb12*(za13*zb35+za14*zb45))
c     D.
     .     - (za14*zb42+za15*zb52)**3/za15/t145
     .     /(za14*zb43+za15*zb53)/(za41*zb12+za45*zb52)
c     E.
     .     + zb45**2*za13**3*zb23/za12/s23
     .     /(za12*zb24+za13*zb34)/(za31*zb15+za32*zb25)
c     cphi part.
     .     + za13**3/za12/za23/za34/za15

      return
      end

************************************************************************

      complex(8) function zC1g0Ha1mmpmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mppmp

      perma(1) = perm(3)
      perma(2) = perm(2)
      perma(3) = perm(1)
      perma(4) = perm(5)
      perma(5) = perm(4)

c     Related to zC1g0Ha1mppmp amplitude by new symmetry
c     in two quark pairs.
c     For two separated quark lines in the colour decomposed
c     factor, we could swap the overall line order.
      zC1g0Ha1mmpmp = -conjg(zC1g0Ha1mppmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha1mmmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      real(8)    :: s12345
      real(8)    :: t123,t145,t125,t234,t345
      real(8)    :: t1235,t1234,t1245,t1345
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      s12345 = s12+s13+s14+s15+s23+s24+S25+s34+s35+s45

      zC1g0Ha1mmmpp =
c     A(1).
     .     - za13**2*zb34*(za31*zb15+za32*zb25+za34*zb45)**2
     .     *(za32*zb21*za13 + za32*zb24*za43
     .     + za35*zb51*za13 + za35*zb54*za43)/s34
     .     /(za31*zb12+za34*zb42)/(za31*zb15+za34*zb45)
     .     /(za31*zb12+za34*zb42+za35*zb52)
     .     /(za13*t125-za34*(za12*zb24+za15*zb54))
c     A(2).
     .     + s12345**2*za13**3*zb34/za51/s34/t1345
     .     /(za13*zb32+za14*zb42+za15*zb52)
     .     /(za31*zb12+za34*zb42+za35*zb52)
c     A(3).
     .     + (za12*zb25+za13*zb35+za14*zb45)**2
     .     *za13**2*zb34/s34
     .     /(za13*zb32+za14*zb42+za15*zb52)
     .     /(za13*zb32+za14*zb42)/(za13*zb35+za14*zb45)
c     B.
     .     + za12**2*za25*(za31*zb14+za32*zb24+za35*zb54)**2
     .     *(za12*zb24+za15*zb54)/za15/t125/(za21*zb14+za25*zb54)
     .     /(za51*zb14+za52*zb24)/(za34*(za12*zb24+za15*zb54)+t125*za31)
c     C.
     .     - za23*(za12*zb24+za13*zb34)**2*(za12*zb23+za14*zb43)
     .     /za15/zb34/s23/t234/(za13*zb32+za14*zb42)
c     D.
     .     - za23**2*za15*zb45**2*(za21*zb15+za24*zb45)
     .     /s15/(za21*zb14+za25*zb54)/(za31*zb15+za34*zb45)/t145
c     E.
     .     + za12*(za31*zb14+za32*zb24)**2/s12/(za31*zb12+za34*zb42)
     .     /(za51*zb14+za52*zb24)
c     F.
     .     - za12**2*zb45**2/t345/zb34/(za13*zb35+za14*zb45)
c     cphi part.
     .     - zb13*zb45**2/zb12/zb23/zb34/zb15

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mpmmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mppmp

      perma(1) = perm(5)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(2)
      perma(5) = perm(1)

      zC1g0Ha2mpmmp = dconjg(zC1g0Ha1mppmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mmpmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mpmpp

      perma(1) = perm(5)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(2)
      perma(5) = perm(1)

      zi = (0d0,1d0)

      zC1g0Ha2mmpmp = -dconjg(zi*zC1g0Ha1mpmpp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mpmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mmpmp

      perma(1) = perm(5)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(2)
      perma(5) = perm(1)

      zC1g0Ha2mpmpp = dconjg(zC1g0Ha1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mmppp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mmmpp

      perma(1) = perm(5)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(2)
      perma(5) = perm(1)

      zi = (0d0,1d0)

      zC1g0Ha2mmppp = -dconjg(zi*zC1g0Ha1mmmpp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mmpmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer    :: j1,j2,j3,j4,j5
      real(8)    :: s12,s13,s14,s15,s23,s24,s25,s34,s35,s45
      real(8)    :: s21,s31,s41,s51,s32,s42,s52,s43,s53,s54
      real(8)    :: s12345
      real(8)    :: t123,t145,t125,t234,t345
      real(8)    :: t1235,t1234,t1245,t1345
      complex(8) :: za12,za13,za14,za15,za23,za24,za25,za34,za35,za45
      complex(8) :: za21,za31,za41,za51,za32,za42,za52,za43,za53,za54
      complex(8) :: zb12,zb13,zb14,zb15,zb23,zb24,zb25,zb34,zb35,zb45
      complex(8) :: zb21,zb31,zb41,zb51,zb32,zb42,zb52,zb43,zb53,zb54

      j1 = perm(1)
      j2 = perm(2)
      j3 = perm(3)
      j4 = perm(4)
      j5 = perm(5)

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s15 = s(j1,j5)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s25 = s(j2,j5)
      s34 = s(j3,j4)
      s35 = s(j3,j5)
      s45 = s(j4,j5)

      s21 = s(j2,j1)
      s31 = s(j3,j1)
      s41 = s(j4,j1)
      s51 = s(j5,j1)
      s32 = s(j3,j2)
      s42 = s(j4,j2)
      s52 = s(j5,j2)
      s43 = s(j4,j3)
      s53 = s(j5,j3)
      s54 = s(j5,j4)

      za12 = zA(j1,j2)
      za13 = zA(j1,j3)
      za14 = zA(j1,j4)
      za15 = zA(j1,j5)
      za23 = zA(j2,j3)
      za24 = zA(j2,j4)
      za25 = zA(j2,j5)
      za34 = zA(j3,j4)
      za35 = zA(j3,j5)
      za45 = zA(j4,j5)

      za21 = zA(j2,j1)
      za31 = zA(j3,j1)
      za41 = zA(j4,j1)
      za51 = zA(j5,j1)
      za32 = zA(j3,j2)
      za42 = zA(j4,j2)
      za52 = zA(j5,j2)
      za43 = zA(j4,j3)
      za53 = zA(j5,j3)
      za54 = zA(j5,j4)

      zb12 = zB(j1,j2)
      zb13 = zB(j1,j3)
      zb14 = zB(j1,j4)
      zb15 = zB(j1,j5)
      zb23 = zB(j2,j3)
      zb24 = zB(j2,j4)
      zb25 = zB(j2,j5)
      zb34 = zB(j3,j4)
      zb35 = zB(j3,j5)
      zb45 = zB(j4,j5)

      zb21 = zB(j2,j1)
      zb31 = zB(j3,j1)
      zb41 = zB(j4,j1)
      zb51 = zB(j5,j1)
      zb32 = zB(j3,j2)
      zb42 = zB(j4,j2)
      zb52 = zB(j5,j2)
      zb43 = zB(j4,j3)
      zb53 = zB(j5,j3)
      zb54 = zB(j5,j4)

      t123  = s12+s13+s23
      t145  = s14+s45+s15
      t125  = s12+s25+s15
      t234  = s23+s34+s24
      t345  = s34+s45+s35
      t1235 = s12+s13+s15+s23+s25+s35
      t1234 = s12+s13+s14+s23+s24+s34
      t1245 = s12+s14+s15+s24+s25+s45
      t1345 = s13+s14+s15+s34+s35+s45

      zC1g0Hb1mmpmp =
c     A.
     .     + za14**2*(za21*zb13+za24*zb43+za25*zb53)**2/za45/t145/t1345
     .     /(za14*zb43+za15*zb53)
c     B.
     .     - za12**2*za45*zb35**2/s45/t345/(za14*zb43+za15*zb53)
c     C.
     .     + za12*(za41*zb13+za42*zb23)**2/za45/zb23/s12/t123
c     Cphi part.
     .     - zb35**2/zb12/zb23/zb54

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mppmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1)=perm(3)
      perma(2)=perm(2)
      perma(3)=perm(1)
      perma(4)=perm(5)
      perma(5)=perm(4)

      zC1g0Hb1mppmp = -dconjg(zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mpppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(3)
      perma(2) = perm(2)
      perma(3) = perm(1)
      perma(4) = perm(4)
      perma(5) = perm(5)

      zi = (0d0,1d0)

      zC1g0Hb1mpppm = dconjg(zi*zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mmppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1)=perm(1)
      perma(2)=perm(2)
      perma(3)=perm(3)
      perma(4)=perm(5)
      perma(5)=perm(4)

      zi = (0d0,1d0)

      zC1g0Hb1mmppm = zi*zC1g0Hb1mmpmp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mpmmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6), zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(3)
      perma(2) = perm(4)
      perma(3) = perm(5)
      perma(4) = perm(1)
      perma(5) = perm(2)

      zi = (0d0,1d0)

      zC1g0Hb2mpmmp = -zC1g0Hb1mmpmp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mppmm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(5)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(1)
      perma(5) = perm(2)

      zi = (0d0,1d0)

      zC1g0Hb2mppmm = zi*zC1g0Hb1mmpmp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mpppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1)=perm(3)
      perma(2)=perm(4)
      perma(3)=perm(5)
      perma(4)=perm(2)
      perma(5)=perm(1)

      zi = (0d0,1d0)

      zC1g0Hb2mpppm = dconjg(zi*zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mpmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1)=perm(5)
      perma(2)=perm(4)
      perma(3)=perm(3)
      perma(4)=perm(2)
      perma(5)=perm(1)

      zC1g0Hb2mpmpp = dconjg(zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mppmm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mpmpp

      perma(1) = perm(2)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(5)
      perma(5) = perm(1)

      zi = (0d0,1d0)

      zC1g0Ha2mppmm = -conjg(zi*zC1g0Ha1mpmpp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Ha1mpppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mpmpp

      perma(1) = perm(1)
      perma(2) = perm(2)
      perma(3) = perm(5)
      perma(4) = perm(4)
      perma(5) = perm(3)

      zi = (0d0,1d0)

      zC1g0Ha1mpppm = zi*zC1g0Ha1mpmpp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Ha1mmppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mmmpp

      perma(1) = perm(1)
      perma(2) = perm(2)
      perma(3) = perm(5)
      perma(4) = perm(4)
      perma(5) = perm(3)

      zi = (0d0,1d0)

      zC1g0Ha1mmppm = zi*zC1g0Ha1mmmpp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Ha2mpppm(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Ha1mmmpp

      perma(1) = perm(2)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(5)
      perma(5) = perm(1)

      zi = (0d0,1d0)

      zC1g0Ha2mpppm = -conjg(zi*zC1g0Ha1mmmpp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mmmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(1)
      perma(2) = perm(2)
      perma(3) = perm(5)
      perma(4) = perm(3)
      perma(5) = perm(4)

      zi = (0d0,1d0)

      zC1g0Hb1mmmpp = zi*zC1g0Hb1mmpmp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Hb1mpmpp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(5)
      perma(2) = perm(2)
      perma(3) = perm(1)
      perma(4) = perm(4)
      perma(5) = perm(3)

      zi = (0d0,1d0)

      zC1g0Hb1mpmpp = conjg(zi*zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mmpmp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(2)
      perma(2) = perm(4)
      perma(3) = perm(3)
      perma(4) = perm(1)
      perma(5) = perm(5)

      zi = (0d0,1d0)

      zC1g0Hb2mmpmp = -zi*zC1g0Hb1mmpmp(s,zA,zB,perma)

      return
      end

************************************************************************

      complex(8) function zC1g0Hb2mmppp(s,zA,zB,perm)
      implicit none
      integer, intent(in)    :: perm(5)
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: zA(6,6),zB(6,6)
      integer                :: perma(5)
      complex(8)             :: zi
c     Externals.
      complex(8), external :: zC1g0Hb1mmpmp

      perma(1) = perm(3)
      perma(2) = perm(4)
      perma(3) = perm(2)
      perma(4) = perm(5)
      perma(5) = perm(1)

      zi = (0d0,1d0)

      zC1g0Hb2mmppp = -conjg(zi*zC1g0Hb1mmpmp(s,zA,zB,perma))

      return
      end

c-----------------------------------------------------------------------

c     H -> q g qb q qb (identical flavours).
c     Adapted from NNLOJET (src/process/H/libCDH.f).
      real(8) function FullD1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: C1g0Ha,C1g0Hb,Ct1g0Ha,Ct1g0Hb,Ctt1g0H
      real(8), external   :: D1g0H,Dt1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*cn

      FullD1g0H = 1d0/2d0*fac*(
     .     + C1g0Ha(p,iq1,i5,iQbar4,iQ3,iqbar2)
     .     + C1g0Ha(p,iq1,i5,iqbar2,iQ3,iQbar4)
     .     + C1g0Hb(p,iq1,iQbar4,iQ3,i5,iqbar2)
     .     + C1g0Hb(p,iq1,iqbar2,iQ3,i5,iQbar4)

     .     + 1d0/cn**2*(
     .     + Ct1g0Ha(p,iq1,i5,iqbar2,iQ3,iQbar4)
     .     + Ct1g0Ha(p,iq1,i5,iQbar4,iQ3,iqbar2)
     .     + Ct1g0Hb(p,iq1,iqbar2,iQ3,i5,iQbar4)
     .     + Ct1g0Hb(p,iq1,iQbar4,iQ3,i5,iqbar2)
     .     - 2d0*Ctt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
     .     - 2d0*Ctt1g0H(p,iq1,iQbar4,iQ3,iqbar2,i5)
     .     )

     .     - 1d0/cn*(
     .     + D1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
     .     - Dt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
     .     )

     .     + 1d0/cn**3*Dt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
     .     )

      return
      end

************************************************************************

      real(8) function D1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: i,imemode,IHEL,NHEL(5,2)
      integer             :: perma1(5),perma2(5)
      integer             :: permb1(5),permb2(5)
      integer             :: permbb1(5),permbb2(5)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6),zamp
      complex(8)          :: zA(6,6),zB(6,6)
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Ha1mppmp,zC1g0Hb1mppmp
      complex(8), external :: zC1g0Ha2mpmpp,zC1g0Hb2mpmpp
      complex(8), external :: zC1g0Ha1mmpmp,zC1g0Hb1mmpmp
      complex(8), external :: zC1g0Ha2mpmmp,zC1g0Hb2mpmmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1, 1,-1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1,-1, 1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      perma1(1) = iq1
      perma1(2) = i5
      perma1(3) = iQbar4
      perma1(4) = iQ3
      perma1(5) = iqbar2

      perma2(1) = iq1
      perma2(2) = iQbar4
      perma2(3) = iQ3
      perma2(4) = i5
      perma2(5) = iqbar2

      permb1(1) = iq1
      permb1(2) = i5
      permb1(3) = iqbar2
      permb1(4) = iQ3
      permb1(5) = iQbar4

      permb2(1) = iq1
      permb2(2) = iqbar2
      permb2(3) = iQ3
      permb2(4) = i5
      permb2(5) = iQbar4

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,2
         if (i.eq.1)then
            zamp = -real(
     .           + zC1g0Ha1mppmp(s,zA,zB,perma1(1))
     .           *conjg(zC1g0Hb1mppmp(s,zA,zB,perma1(1)))
     .           + zC1g0Ha2mpmpp(s,zA,zB,perma2(1))
     .           *conjg(zC1g0Hb2mpmpp(s,zA,zB,perma2(1)))
     .           + zC1g0Hb1mppmp(s,zA,zB,permb1(1))
     .           *conjg(zC1g0Ha1mppmp(s,zA,zB,permb1(1)))
     .           + zC1g0Hb2mpmpp(s,zA,zB,permb2(1))
     .           *conjg(zC1g0Ha2mpmpp(s,zA,zB,permb2(1)))
     .           )
         endif
         if(i.eq.2) then
            zamp = -real(
     .           + zC1g0Ha1mmpmp(s,zA,zB,perma1(1))
     .           *conjg(zC1g0Hb1mmpmp(s,zA,zB,perma1(1)))
     .           + zC1g0Ha2mpmmp(s,zA,zB,perma2(1))
     .           *conjg(zC1g0Hb2mpmmp(s,zA,zB,perma2(1)))
     .           + zC1g0Hb1mmpmp(s,zA,zB,permb1(1))
     .           *conjg(zC1g0Ha1mmpmp(s,zA,zB,permb1(1)))
     .           + zC1g0Hb2mpmmp(s,zA,zB,permb2(1))
     .           *conjg(zC1g0Ha2mpmmp(s,zA,zB,permb2(1)))
     .           )
         endif
         amp2 = amp2 + 4d0*zamp
      enddo
      amp2 = amp2/2d0/s12345**2

      D1g0H = amp2*born

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> q g qbar q qbar.
c     Colour-mixing part for (A1+A2)(B1+B2)^*+(B1+B2)(A1+A2)^*.
      real(8) function Dt1g0H(p,iq1,iqbar2,iQ3,iQbar4,i5)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,i5
      real(8), intent(in) :: p(1:4,6)
      integer             :: i,imemode,IHEL,NHEL(5,2)
      integer             :: perma1(7),perma2(7)
      integer             :: permaa1(7),permaa2(7)
      real(8)             :: s12345,amp2,born
      real(8)             :: s(6,6),zamp
      complex(8)          :: zA(6,6),zB(6,6)
c     Common blocks.
      common/memode/imemode
c     Externals.      
      real(8), external    :: A2g0H
      complex(8), external :: zC1g0Ha1mppmp, zC1g0Ha2mpmpp
      complex(8), external :: zC1g0Ha1mmpmp, zC1g0Ha2mpmmp
c     Data.
      DATA (NHEL(IHEL,   1),IHEL=1, 5) / -1, 1, 1,-1, 1/
      DATA (NHEL(IHEL,   2),IHEL=1, 5) / -1,-1, 1,-1, 1/

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(iq1,iqbar2)+s(iq1,iQ3)+s(iq1,iQbar4)+s(iq1,i5)
     .     + s(iqbar2,iQ3)+s(iqbar2,iQbar4)+s(iqbar2,i5)
     .     + s(iQ3,iQbar4)+s(iQ3,i5)
     .     + s(iQbar4,i5)

c     Calculate Born.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s12345)

c     Set permutations.
      perma1(1) = iq1
      perma1(2) = i5
      perma1(3) = iQbar4
      perma1(4) = iQ3
      perma1(5) = iqbar2

      perma2(1) = iq1
      perma2(2) = iQbar4
      perma2(3) = iQ3
      perma2(4) = i5
      perma2(5) = iqbar2

      permaa1(1) = iq1
      permaa1(2) = i5
      permaa1(3) = iqbar2
      permaa1(4) = iQ3
      permaa1(5) = iQbar4

      permaa2(1) = iq1
      permaa2(2) = iqbar2
      permaa2(3) = iQ3
      permaa2(4) = i5
      permaa2(5) = iQbar4

c     Calculate amplitude squared.
      amp2 = 0d0
      do i=1,2
         if (i.eq.1)then
            zamp = real(
     .           (zC1g0Ha1mppmp(s,zA,zB,perma1(1))
     .           - zC1g0Ha2mpmpp(s,zA,zB,perma2(1)))
     .           *dconjg(zC1g0Ha1mppmp(s,zA,zB,permaa1(1))
     .           - zC1g0Ha2mpmpp(s,zA,zB,permaa2(1)))
     .           )
         endif
         if (i.eq.2)then
            zamp = real(
     .           (zC1g0Ha1mmpmp(s,zA,zB,perma1(1))
     .           - zC1g0Ha2mpmmp(s,zA,zB,perma2(1)))
     .           *dconjg(zC1g0Ha1mmpmp(s,zA,zB,permaa1(1))
     .           - zC1g0Ha2mpmmp(s,zA,zB,permaa2(1)))
     .           )
         endif
         amp2 = amp2 + 4d0*zamp
      enddo
      amp2 = -amp2/2d0/s12345**2

      Dt1g0H = amp2*born

      return
      end

c-----------------------------------------------------------------------
