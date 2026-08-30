c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Tree-level matrix elements for Higgs decays to a b-bbar pair
c     plus up to two additional partons.

c     NOTE: Always one ordering only,
c     *including* coupling factors and colour factors,
c     *excluding* symmetry factors. (will be set in sigHB).

c     Common block 'memode' determines whether to include Born or not:
c     imemode = 0  exclude Born       
c     imemode = 1  include Born 
      
c-----------------------------------------------------------------------
c     H -> 2j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> b(i1) bbar(i2).
      real(8) function FullBy0g0H(p,i1,i2)
      implicit none
      integer, intent(in) :: i1, i2
      real(8), intent(in) :: p(1:4,3)
      real(8)             :: s12
c     External.
      real(8), external   :: dot, By0g0H
      
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      FullBy0g0H = By0g0H(s12)

      return
      end

************************************************************************

c     Tree-level amplitude squared for
c     H -> b(i1) bbar(i2).
c     Note: includes colour and coupling factors!
      real(8) function By0g0H(s12)
      implicit none
      real(8), intent(in) :: s12
      real(8)             :: as,ca,cflo,cf,tr,cn
      real(8)             :: yB, cHGG
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/eecplngs/yB,cHGG      

      By0g0H = yB**2*cn*s12

      return
      end
      
c-----------------------------------------------------------------------
c     H -> 3j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> b(i1) g(i3) bbar(i2).
      real(8) function FullBy1g0H(p,i1,i3,i2)
      implicit none
      real(8), intent(in) :: p(1:4,4)
      integer, intent(in) :: i1,i2,i3
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: By1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac = (4d0*pi*as)*2d0*cf

      FullBy1g0H = fac*By1g0H(p,i1,i3,i2)

      return
      end

************************************************************************

c     Tree-level amplitude squared for
c     H -> b(i1) g(i3) bbar(i2).
      real(8) function By1g0H(p,i1,i3,i2)
      implicit none
      real(8), intent(in) :: p(4,4)
      integer, intent(in) :: i1,i2,i3
      integer             :: imemode
      real(8)             :: s12,s13,s23,s123
      real(8)             :: born,wt
c     External.
      real(8), external   :: dot,By0g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12  = 2d0*dot(p(1,i1),p(1,i2))
      s13  = 2d0*dot(p(1,i1),p(1,i3))
      s23  = 2d0*dot(p(1,i2),p(1,i3))
      s123 = s12+s13+s23

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s123)
      
c     Full matrix element.
      wt = (s23/s13+s13/s23+2d0*s12*s123/s13/s23+2d0)/s123
      By1g0H = wt*born

      return
      end

c-----------------------------------------------------------------------
c     H -> 4j matrix elements.
c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function FullBy2g0H(p,i1,i3,i4,i2)
      implicit none
      real(8), intent(in) :: p(1:4,5)
      integer, intent(in) :: i1,i2,i3,i4
      real(8)             :: s12,s13,s14,s23,s24,s34
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: dot,By2g0H,Bty2g0H
C      real(8), external   :: By2g0HAlt,Bty2g0HAlt
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac = (4d0*pi*as)**2*2d0*cf*cn

c     Implementation in terms of invariants (slightly faster).
      FullBy2g0H = 1d0/2d0*fac*(
     .     + By2g0H(p,i1,i3,i4,i2)
     .     + By2g0H(p,i1,i4,i3,i2)
     .     - 1d0/cn**2*Bty2g0H(p,i1,i3,i4,i2)
     .     )

c     Implementation in terms of helicity amplitudes.
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
C      FullBy2g0H = 1d0/2d0*fac*(
C     .     + By2g0HAlt(p,i1,i3,i4,i2)
C     .     + By2g0HAlt(p,i1,i4,i3,i2)
C     .     - 1d0/cn**2*Bty2g0HAlt(p,i1,i3,i4,i2)
C     .     )

      return
      end      

************************************************************************

c     Tree-level LC contribution to
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function By2g0H(p,i1,i3,i4,i2)
      implicit none
      real(8), intent(in) :: p(4,4)
      integer, intent(in) :: i1,i2,i3,i4
c     Variables.
      integer             :: imemode
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s134,s234,s1234
      real(8)             :: wt,born
c     Externals.
      real(8), external   :: dot,By0g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12   = 2d0*dot(p(1,i1),p(1,i2))
      s13   = 2d0*dot(p(1,i1),p(1,i3))
      s14   = 2d0*dot(p(1,i1),p(1,i4))
      s23   = 2d0*dot(p(1,i2),p(1,i3))
      s24   = 2d0*dot(p(1,i2),p(1,i4))
      s34   = 2d0*dot(p(1,i3),p(1,i4))
      s134  = s13+s14+s34
      s234  = s23+s24+s34
      s1234 = s12+s13+s14+s23+s24+s34

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Leading-colour contribution.
      wt = s134**(-2)*s13**(-1) * (
     .     - 8d0*s24*s34
     .     - 8d0*s23*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s134**(-2)*s34**(-2) * (
     .     - 16d0*s24*s14**2
     .     - 16d0*s23*s14**2
     .     - 16d0*s12*s14**2
     .     )
      wt = wt + s134**(-2) * (
     .     - 8d0*s24
     .     - 8d0*s23
     .     - 8d0*s12
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s13**(-1)*s24**(-1) * (
     .     + 16d0*s34**3
     .     - 48d0*s12*s34**2
     .     + 48d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s13**(-1) * (
     .     + 32d0*s34**2
     .     + 24d0*s24*s34
     .     + 8d0*s24**2
     .     - 64d0*s12*s34
     .     - 24d0*s12*s24
     .     + 32d0*s12**2
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s24**(-1) * (
     .     + 16d0*s34**2
     .     - 8d0*s14*s34
     .     + 8d0*s14**2
     .     - 40d0*s12*s34
     .     + 24d0*s12*s14
     .     + 32d0*s12**2
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s34**(-2) * (
     .     + 32d0*s12*s24*s14
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s34**(-1) * (
     .     + 16d0*s14**2
     .     + 16d0*s24**2
     .     + 32d0*s12*s14
     .     + 64d0*s12**2
     .     )
      wt = wt + s134**(-1)*s234**(-1) * (
     .     + 40d0*s34
     .     + 8d0*s14
     .     + 24d0*s24
     .     - 80d0*s12
     .     )
      wt = wt + s134**(-1)*s13**(-1)*s24**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s23*s34
     .     - 8d0*s23**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s23
     .     - 32d0*s12**2
     .     )
      wt = wt + s134**(-1)*s13**(-1) * (
     .     - 32d0*s34
     .     + 8d0*s24
     .     + 24d0*s23
     .     + 48d0*s12
     .     )
      wt = wt + s134**(-1)*s24**(-1)*s34**(-1) * (
     .     - 8d0*s14**2
     .     - 8d0*s23**2
     .     - 16d0*s12*s14
     .     - 16d0*s12*s23
     .     - 16d0*s12**2
     .     )
      wt = wt + s134**(-1)*s24**(-1) * (
     .     - 16d0*s34
     .     + 8d0*s14
     .     + 8d0*s23
     .     + 32d0*s12
     .     )
      wt = wt + s134**(-1)*s34**(-2) * (
     .     - 16d0*s14**2
     .     + 32d0*s24*s14
     .     )
      wt = wt + s134**(-1)*s34**(-1) * (
     .     + 8d0*s24
     .     + 24d0*s23
     .     + 64d0*s12
     .     )
      wt = wt + s134**(-1) * (
     .     - 40d0
     .     )
      wt = wt + s234**(-2)*s24**(-1) * (
     .     - 8d0*s14*s34
     .     - 8d0*s13*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s234**(-2)*s34**(-2) * (
     .     - 16d0*s24**2*s14
     .     - 16d0*s13*s24**2
     .     - 16d0*s12*s24**2
     .     )
      wt = wt + s234**(-2)*s34**(-1) * (
     .     - 32d0*s24*s14
     .     - 32d0*s13*s24
     .     - 32d0*s12*s24
     .     )
      wt = wt + s234**(-2) * (
     .     - 24d0*s14
     .     - 24d0*s13
     .     - 24d0*s12
     .     )
      wt = wt + s234**(-1)*s13**(-1)*s24**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s14*s34
     .     - 8d0*s14**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s14
     .     - 32d0*s12**2
     .     )
      wt = wt + s234**(-1)*s13**(-1)*s34**(-1) * (
     .     - 8d0*s14**2
     .     - 8d0*s24**2
     .     - 16d0*s12*s14
     .     + 16d0*s12*s24
     .     - 16d0*s12**2
     .     )
      wt = wt + s234**(-1)*s13**(-1) * (
     .     - 32d0*s34
     .     + 8d0*s14
     .     - 24d0*s24
     .     + 48d0*s12
     .     )
      wt = wt + s234**(-1)*s24**(-1) * (
     .     - 16d0*s34
     .     + 16d0*s14
     .     + 16d0*s13
     .     + 24d0*s12
     .     )
      wt = wt + s234**(-1)*s34**(-2) * (
     .     + 32d0*s24*s14
     .     - 16d0*s24**2
     .     )
      wt = wt + s234**(-1)*s34**(-1) * (
     .     + 40d0*s14
     .     - 32d0*s24
     .     + 24d0*s13
     .     + 64d0*s12
     .     )
      wt = wt + s234**(-1) * (
     .     - 48d0
     .     )
      wt = wt + s13**(-1)*s24**(-1)*s34**(-1) * (
     .     - 8d0*s14**2
     .     - 16d0*s23*s14
     .     - 8d0*s23**2
     .     - 16d0*s12*s14
     .     - 16d0*s12*s23
     .     - 16d0*s12**2
     .     )
      wt = wt + s13**(-1)*s24**(-1) * (
     .     + 8d0*s34
     .     - 24d0*s14
     .     - 24d0*s23
     .     - 48d0*s12
     .     )
      wt = wt + s13**(-1)*s34**(-1) * (
     .     - 32d0*s14
     .     - 8d0*s24
     .     - 32d0*s23
     .     - 48d0*s12
     .     )
      wt = wt + s13**(-1) * (
     .     + 16d0
     .     )
      wt = wt + s24**(-1)*s34**(-1) * (
     .     - 24d0*s14
     .     - 32d0*s23
     .     - 16d0*s13
     .     - 32d0*s12
     .     )
      wt = wt + s34**(-1) * (
     .     + 16d0
     .     )
      wt = -wt/8d0/s1234

      By2g0H = wt*born

      return
      end
      
************************************************************************      

c     Tree-level SLC contribution to
c     H -> b(i1) g(i3) g(i4) bbar(i2).
      real(8) function Bty2g0H(p,i1,i3,i4,i2)
      implicit none
      real(8), intent(in) :: p(4,4)
      integer, intent(in) :: i1,i3,i4,i2
c     Variables.
      integer             :: imemode
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s134,s234,s1234
      real(8)             :: wt,born
c     External.
      real(8), external   :: dot,By0g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12   = 2d0*dot(p(1,i1),p(1,i2))
      s13   = 2d0*dot(p(1,i1),p(1,i3))
      s14   = 2d0*dot(p(1,i1),p(1,i4))
      s23   = 2d0*dot(p(1,i2),p(1,i3))
      s24   = 2d0*dot(p(1,i2),p(1,i4))
      s34   = 2d0*dot(p(1,i3),p(1,i4))
      s134  = s13+s14+s34
      s234  = s23+s24+s34
      s1234 = s12+s13+s14+s23+s24+s34

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Subleading-colour contribution.
      wt = s134**(-2)*s13**(-1) * (
     .     - 8d0*s24*s34
     .     - 8d0*s23*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s134**(-2)*s14**(-1) * (
     .     - 8d0*s24*s34
     .     - 8d0*s23*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s134**(-2) * (
     .     - 16d0*s24
     .     - 16d0*s23
     .     - 16d0*s12
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s13**(-1)*s24**(-1) * (
     .     + 16d0*s34**3
     .     - 48d0*s12*s34**2
     .     + 48d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s13**(-1)*s23**(-1) * (
     .     - 8d0*s12*s34**2
     .     + 16d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s13**(-1) * (
     .     + 16d0*s34**2
     .     + 8d0*s24*s34
     .     - 24d0*s12*s34
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s24**(-1)*s14**(-1) * (
     .     - 8d0*s12*s34**2
     .     + 16d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s24**(-1) * (
     .     + 8d0*s34**2
     .     - 8d0*s14*s34
     .     - 24d0*s12*s34
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s14**(-1)*s23**(-1) * (
     .     + 16d0*s34**3
     .     - 48d0*s12*s34**2
     .     + 48d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s14**(-1) * (
     .     + 8d0*s34**2
     .     - 8d0*s24*s34
     .     - 24d0*s12*s34
     .     )
      wt = wt + s134**(-1)*s234**(-1)*s23**(-1) * (
     .     + 16d0*s34**2
     .     + 8d0*s14*s34
     .     - 24d0*s12*s34
     .     )
      wt = wt + s134**(-1)*s234**(-1) * (
     .     - 32d0*s12
     .     )
      wt = wt + s134**(-1)*s13**(-1)*s24**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s23*s34
     .     - 8d0*s23**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s23
     .     - 32d0*s12**2
     .     )
      wt = wt + s134**(-1)*s13**(-1)*s23**(-1) * (
     .     + 8d0*s12*s34
     .     - 8d0*s12*s24
     .     - 16d0*s12**2
     .     )
      wt = wt + s134**(-1)*s13**(-1) * (
     .     - 16d0*s34
     .     + 8d0*s24
     .     + 8d0*s23
     .     )
      wt = wt + s134**(-1)*s24**(-1)*s14**(-1) * (
     .     + 8d0*s12*s34
     .     - 8d0*s12*s23
     .     - 16d0*s12**2
     .     )
      wt = wt + s134**(-1)*s24**(-1) * (
     .     - 8d0*s34
     .     + 8d0*s14
     .     + 16d0*s12
     .     )
      wt = wt + s134**(-1)*s14**(-1)*s23**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s24*s34
     .     - 8d0*s24**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s24
     .     - 32d0*s12**2
     .     )
      wt = wt + s134**(-1)*s14**(-1) * (
     .     - 8d0*s34
     .     + 8d0*s24
     .     + 8d0*s23
     .     )
      wt = wt + s134**(-1)*s23**(-1) * (
     .     - 16d0*s34
     .     - 8d0*s14
     .     + 16d0*s12
     .     )
      wt = wt + s134**(-1) * (
     .     - 16d0
     .     )
      wt = wt + s234**(-2)*s24**(-1) * (
     .     - 8d0*s14*s34
     .     - 8d0*s13*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s234**(-2)*s23**(-1) * (
     .     - 8d0*s14*s34
     .     - 8d0*s13*s34
     .     - 8d0*s12*s34
     .     )
      wt = wt + s234**(-2) * (
     .     - 16d0*s14
     .     - 16d0*s13
     .     - 16d0*s12
     .     )
      wt = wt + s234**(-1)*s13**(-1)*s24**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s14*s34
     .     - 8d0*s14**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s14
     .     - 32d0*s12**2
     .     )
      wt = wt + s234**(-1)*s13**(-1)*s23**(-1) * (
     .     + 8d0*s12*s34
     .     - 8d0*s12*s14
     .     - 16d0*s12**2
     .     )
      wt = wt + s234**(-1)*s13**(-1) * (
     .     - 16d0*s34
     .     - 8d0*s24
     .     + 16d0*s12
     .     )
      wt = wt + s234**(-1)*s24**(-1)*s14**(-1) * (
     .     + 8d0*s12*s34
     .     - 8d0*s12*s13
     .     - 16d0*s12**2
     .     )
      wt = wt + s234**(-1)*s24**(-1) * (
     .     - 8d0*s34
     .     + 8d0*s14
     .     + 8d0*s13
     .     )
      wt = wt + s234**(-1)*s14**(-1)*s23**(-1) * (
     .     - 16d0*s34**2
     .     + 8d0*s13*s34
     .     - 8d0*s13**2
     .     + 40d0*s12*s34
     .     - 24d0*s12*s13
     .     - 32d0*s12**2
     .     )
      wt = wt + s234**(-1)*s14**(-1) * (
     .     - 8d0*s34
     .     + 8d0*s24
     .     + 16d0*s12
     .     )
      wt = wt + s234**(-1)*s23**(-1) * (
     .     - 16d0*s34
     .     + 8d0*s14
     .     + 8d0*s13
     .     )
      wt = wt + s234**(-1) * (
     .     - 16d0
     .     )
      wt = wt + s13**(-1)*s24**(-1)*s14**(-1)*s23**(-1) * (
     .     - 8d0*s12*s34**2
     .     - 16d0*s12**2*s34
     .     - 16d0*s12**3
     .     )
      wt = wt + s13**(-1)*s24**(-1)*s14**(-1) * (
     .     - 16d0*s12*s34
     .     - 8d0*s12*s23
     .     - 16d0*s12**2
     .     )
      wt = wt + s13**(-1)*s24**(-1)*s23**(-1) * (
     .     - 16d0*s12*s34
     .     - 8d0*s12*s14
     .     - 16d0*s12**2
     .     )
      wt = wt + s13**(-1)*s24**(-1) * (
     .     + 16d0*s34
     .     - 8d0*s14
     .     - 8d0*s23
     .     - 48d0*s12
     .     )
      wt = wt + s13**(-1)*s14**(-1)*s23**(-1) * (
     .     - 16d0*s12*s34
     .     - 8d0*s12*s24
     .     - 16d0*s12**2
     .     )
      wt = wt + s13**(-1)*s14**(-1) * (
     .     - 16d0*s12
     .     )
      wt = wt + s13**(-1)*s23**(-1) * (
     .     - 32d0*s12
     .     )
      wt = wt + s13**(-1) * (
     .     + 16d0
     .     )
      wt = wt + s24**(-1)*s14**(-1)*s23**(-1) * (
     .     - 16d0*s12*s34
     .     - 8d0*s12*s13
     .     - 16d0*s12**2
     .     )
      wt = wt + s24**(-1)*s14**(-1) * (
     .     - 32d0*s12
     .     )
      wt = wt + s24**(-1)*s23**(-1) * (
     .     - 16d0*s12
     .     )
      wt = wt + s24**(-1) * (
     .     + 8d0
     .     )
      wt = wt + s14**(-1)*s23**(-1) * (
     .     + 16d0*s34
     .     - 8d0*s24
     .     - 8d0*s13
     .     - 48d0*s12
     .     )
      wt = wt + s14**(-1) * (
     .     + 8d0
     .     )
      wt = wt + s23**(-1) * (
     .     + 16d0
     .     )
      wt = -wt/8d0/s1234

      Bty2g0H = wt*born

      return
      end

************************************************************************

c     Leading-colour contribution to H -> b(i1) bbar(i2) g(i3) g(i4).
      real(8) function By2g0HAlt(p,i1,i3,i4,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      real(8), intent(in)  :: p(1:4,5)
      integer              :: imemode,icol
      integer              :: h1,h2,h3
      real(8)              :: msq,born,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: amps(0:2,2,2,2)
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
c     Common blocks.
      common/memode/imemode

c     Invariants.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
      icol = 1
      amps(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,za,zb)

      amps(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zb,za)

      icol = 2
      amps(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,za,zb)

      amps(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zb,za)

c     Calculate squared matrix element.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + real(amps(1,h1,h2,h3)*conjg(amps(1,h1,h2,h3)))
            enddo
         enddo
      enddo
      msq = msq/s1234/2d0

      By2g0HAlt = msq*born

      return
      end

************************************************************************

c     Subleading-colour contribution to H -> b(i1) bbar(i2) g(i3) g(i4).
      real(8) function Bty2g0HAlt(p,i1,i3,i4,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      real(8), intent(in)  :: p(1:4,5)
      integer              :: imemode,icol
      integer              :: h1,h2,h3
      real(8)              :: msq,born,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: amps(0:2,2,2,2)
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
c     Common blocks.
      common/memode/imemode

c     Invariants.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
      icol = 1
      amps(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,za,zb)
      amps(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,za,zb)

      amps(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zb,za)
      amps(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zb,za)

      icol = 2
      amps(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,za,zb)
      amps(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,za,zb)

      amps(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zb,za)
      amps(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zb,za)

      icol = 0
      amps(icol,:,:,:) = amps(1,:,:,:) + amps(2,:,:,:)

c     Calculate squared matrix element.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + real(amps(0,h1,h2,h3)*conjg(amps(0,h1,h2,h3)))
            enddo
         enddo
      enddo
      msq = msq/s1234/2d0

      Bty2g0HAlt = msq*born

      return
      end

************************************************************************

c     Tree-level amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ----.
      complex(8) function Hbbgg_allm(i1,i2,i3,i4,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4
      real(8), intent(in)    :: s(5,5)
      complex(8), intent(in) :: zA(5,5),zB(5,5)
      real(8)                :: s1234

      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

C     Hbbgg_allm = s1234/(zb(i1,i4)*zb(i2,i3)*zb(i3,i4))
      Hbbgg_allm = s1234/(zb(i1,i3)*zb(i2,i4)*zb(i4,i3))

      return
      end

************************************************************************

c     Tree-level amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), --++.
      complex(8) function Hbbgg_mmpp(i1,i2,i3,i4,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4
      real(8), intent(in)    :: s(5,5)
      complex(8), intent(in) :: zA(5,5),zB(5,5)
   
C     Hbbgg_mmpp = za(i1,i2)**2/(za(i1,i4)*za(i2,i3)*za(i3,i4))
      Hbbgg_mmpp = za(i1,i2)**2/(za(i1,i3)*za(i2,i4)*za(i4,i3))

      return
      end

************************************************************************

c     Tree-level amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ---+.
      complex(8) function Hbbgg_mmmp(i1,i2,i3,i4,s,za,zb)
      implicit none
      integer                :: i1,i2,i3,i4
      real(8), intent(in)    :: s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      real(8)                :: t
      complex(8)             :: zab2

      zab2(i1,i2,i4,i3) = za(i1,i2)*zb(i2,i3)+za(i1,i4)*zb(i4,i3)
      t(i1,i2,i3)       = s(i1,i2)+s(i2,i3)+s(i1,i3)
      
C      Hbbgg_mmmp =
C     .     za(i2,i3)*zb(i4,i2)*zab2(i1,i2,i3,i4)
C     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i2,i3)*zb(i3,i4))
C
C      Hbbgg_mmmp = Hbbgg_mmmp
C     .     + za(i1,i3)**2*zab2(i2,i1,i3,i4)
C     .     /(t(i1,i3,i4)*za(i1,i4)*za(i3,i4)*zb(i3,i4))
C
C      Hbbgg_mmmp = Hbbgg_mmmp
C     .     - za(i1,i3)*zab2(i1,i2,i3,i4)
C     .     /(za(i1,i4)*za(i3,i4)*zb(i2,i3)*zb(i3,i4))

      Hbbgg_mmmp =
     .     za(i2,i4)*zb(i3,i2)*zab2(i1,i2,i4,i3)
     .     /(t(i2,i3,i4)*za(i4,i3)*zb(i2,i4)*zb(i4,i3))

      Hbbgg_mmmp = Hbbgg_mmmp
     .     + za(i1,i4)**2*zab2(i2,i1,i4,i3)
     .     /(t(i1,i3,i4)*za(i1,i3)*za(i4,i3)*zb(i4,i3))

      Hbbgg_mmmp = Hbbgg_mmmp
     .     - za(i1,i4)*zab2(i1,i2,i4,i3)
     .     /(za(i1,i3)*za(i4,i3)*zb(i2,i4)*zb(i4,i3))
      
      return
      end

c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> b(i1) qbar(i4) q(i3) bbar(i2).
      real(8) function FullCy0g0H(p,i1,i4,i3,i2)
      implicit none
      real(8), intent(in) :: p(1:4,5)
      integer, intent(in) :: i1,i2,i3,i4
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external   :: dot
      real(8), external   :: Cy0g0H
C      real(8), external   :: Cy0g0HAlt
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac = (4d0*pi*as)**2*2d0*cf

c     Implementation in terms of invariants (slightly faster).
      FullCy0g0H = fac*Cy0g0H(p,i1,i4,i3,i2)

c     Implementation in terms of helicity amplitudes.
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
C      FullCy0g0H = fac*Cy0g0HAlt(p,i1,i4,i3,i2)

      return
      end      

************************************************************************

c     Tree-level amplitude squared for
c     H -> b(i1) bbar(i2) q(i3) qbar(i4).
      real(8) function Cy0g0H(p,i1,i4,i3,i2)
      implicit none
      real(8), intent(in) :: p(4,4)
      integer, intent(in) :: i1,i2,i3,i4
c     Variables.
      integer             :: imemode
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s134,s234,s1234
      real(8)             :: born,wt
c     External.
      real(8), external   :: dot,By0g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12   = 2d0*dot(p(1,i1),p(1,i2))
      s13   = 2d0*dot(p(1,i1),p(1,i3))
      s14   = 2d0*dot(p(1,i1),p(1,i4))
      s23   = 2d0*dot(p(1,i2),p(1,i3))
      s24   = 2d0*dot(p(1,i2),p(1,i4))
      s34   = 2d0*dot(p(1,i3),p(1,i4))
      s134  = s13+s14+s34
      s234  = s23+s24+s34
      s1234 = s12+s13+s14+s23+s24+s34
      
c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

      wt = s34**(-2)*s134**(-2) * (
     .     + 8d0*s14**2*s23
     .     - 8d0*s13*s14*s24
     .     - 8d0*s13*s14*s23
     .     + 8d0*s13**2*s24
     .     - 16d0*s12*s13*s14
     .     )
      wt = wt + s34**(-2)*s134**(-1)*s234**(-1) * (
     .     - 8d0*s14*s23*s24
     .     + 8d0*s14*s23**2
     .     + 8d0*s14**2*s23
     .     + 8d0*s13*s24**2
     .     - 8d0*s13*s23*s24
     .     - 8d0*s13*s14*s24
     .     - 8d0*s13*s14*s23
     .     + 8d0*s13**2*s24
     .     + 16d0*s12*s14*s23
     .     + 16d0*s12*s13*s24
     .     )
      wt = wt + s34**(-2)*s234**(-2) * (
     .     - 8d0*s14*s23*s24
     .     + 8d0*s14*s23**2
     .     + 8d0*s13*s24**2
     .     - 8d0*s13*s23*s24
     .     - 16d0*s12*s23*s24
     .     )
      wt = wt + s34**(-1)*s134**(-2) * (
     .     - 8d0*s14*s24
     .     - 8d0*s13*s23
     .     - 8d0*s12*s14
     .     - 8d0*s12*s13
     .     )
      wt = wt + s34**(-1)*s134**(-1)*s234**(-1) * (
     .     - 16d0*s14*s24
     .     - 16d0*s13*s23
     .     - 8d0*s12*s24
     .     - 8d0*s12*s23
     .     - 8d0*s12*s14
     .     - 8d0*s12*s13
     .     - 16d0*s12**2
     .     )
      wt = wt + s34**(-1)*s234**(-2) * (
     .     - 8d0*s14*s24
     .     - 8d0*s13*s23
     .     - 8d0*s12*s24
     .     - 8d0*s12*s23
     .     )
      wt = -wt/8d0/s1234

      Cy0g0H = wt*born

      return
      end

************************************************************************

c     H -> b(i1) bbar(i2) q(i3) qbar(i4).
      real(8) function Cy0g0HAlt(p,i1,i4,i3,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      real(8), intent(in)  :: p(1:4,5)
      integer              :: imemode,icol
      integer              :: iint,h1
      real(8)              :: msq,born,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: amps(4,2,2,2)
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQ_mmmp
c     Common blocks.
      common/memode/imemode

c     Invariants.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
c     int = 1 mmpm type diagrams
c     int = 2 mmmp type diagrams
      iint=1
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      iint=2
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)

c     Calculate matrix element squared.
      msq = 0d0
      do h1 = 1,2
         msq = msq
     .        + real(amps(1,h1,1,1)*conjg(amps(1,h1,1,1)))
     .        + real(amps(2,h1,1,1)*conjg(amps(2,h1,1,1)))
      enddo
      msq = msq/2d0/s1234

      Cy0g0HAlt = msq*born

      return
      end

************************************************************************

c     H -> b(i1) bbar(i2) q(i3) qbar(i4) ---+ amplitude.
      complex(8) function HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4
      real(8), intent(in)    :: s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      complex(8)             :: zab2
      real(8)                :: t

      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      t(i1,i2,i3)       = s(i1,i2)+s(i1,i3)+s(i2,i3)

      HbbQQ_mmmp =
     .     + za(i1,i3)*zab2(i2,i1,i3,i4)/(t(i1,i3,i4)*s(i3,i4))
     .     + za(i2,i3)*zab2(i1,i2,i3,i4)/(t(i2,i3,i4)*s(i3,i4))

      return
      end

************************************************************************

c     H -> b(i1) bbar(i2) q(i3) qbar(i4) -+-- amplitude.
      complex(8) function HbbQQ_mpmm(i1,i2,i3,i4,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4
      real(8), intent(in)    :: s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      complex(8)             :: zab2
      real(8)                :: t
      
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      t(i1,i2,i3)       = s(i1,i2)+s(i1,i3)+s(i2,i3)

      HbbQQ_mpmm =
     .     + za(i4,i1)*zab2(i3,i1,i4,i2)/(t(i1,i2,i4)*s(i1,i2))
     .     + za(i3,i1)*zab2(i4,i1,i3,i2)/(t(i1,i2,i3)*s(i1,i2))

      return
      end

c-----------------------------------------------------------------------

c     Full matrix element squared for
c     H -> b(i1) bbar(i2) b(i3) bbar(i4).
      real(8) function FullDy0g0H(p,i1,i4,i3,i2)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: p(1:4,5)
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn
c     External.
      real(8), external :: dot
      real(8), external :: Cy0g0H,Dy0g0H
C      real(8), external :: Cy0g0HAlt,Dy0g0HAlt
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn 

c     Prefactor.
      fac = (4d0*pi*as)**2*2d0*cf

c     Implementation in terms of invariants (slightly faster).
      FullDy0g0H = 1d0/4d0*fac*(
     .     + Cy0g0H(p,i1,i4,i3,i2)
     .     + Cy0g0H(p,i1,i2,i3,i4)
     .     + Cy0g0H(p,i3,i4,i1,i2)
     .     + Cy0g0H(p,i3,i2,i1,i4)
     .     - 1d0/cn*Dy0g0H(p,i1,i2,i3,i4)
     .     )

c     Implementation in terms of helicity amplitudes.
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
C      FullDy0g0H = 1d0/4d0*(
C     .     + Cy0g0HAlt(p,i1,i4,i3,i2)
C     .     + Cy0g0HAlt(p,i1,i2,i3,i4)
C     .     + Cy0g0HAlt(p,i3,i4,i1,i2)
C     .     + Cy0g0HAlt(p,i3,i2,i1,i4)
C     .     + Dy0g0HAlt(p,i1,i4,i3,i2)
C     .     )

      return
      end

************************************************************************

c     Tree-level interference contribution to
c     H -> b(i1) bbar(i4) b(i3) bbar(i2).
      real(8) function Dy0g0H(p,i1,i2,i3,i4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: p(1:4,5)
      real(8)             :: s12,s13,s14,s23,s24,s34
c     External.
      real(8), external   :: dot,Dy0g0Hsub

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s14 = 2d0*dot(p(1,i1),p(1,i4))
      s23 = 2d0*dot(p(1,i2),p(1,i3))
      s24 = 2d0*dot(p(1,i2),p(1,i4))
      s34 = 2d0*dot(p(1,i3),p(1,i4))

      Dy0g0H =
     .     + Dy0g0Hsub(s12,s13,s14,s23,s24,s34) !1234
     .     + Dy0g0Hsub(s12,s24,s23,s14,s13,s34) !2143
     .     + Dy0g0Hsub(s34,s13,s23,s14,s24,s12) !3412
     .     + Dy0g0Hsub(s34,s24,s14,s23,s13,s12) !4321
      
      Dy0g0H = Dy0g0H

      return
      end

************************************************************************

      real(8) function Dy0g0Hsub(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8), intent(in) :: s12,s13,s14,s23,s24,s34
      integer             :: imemode
      real(8)             :: s123,s134,s234,s1234
      real(8)             :: born,wt
c     External.
      real(8), external   :: By0g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s123  = s12+s13+s23      
      s134  = s13+s14+s34
      s234  = s23+s24+s34
      s1234 = s12+s13+s14+s23+s24+s34
      
c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

      wt = -((-8*s12**2 + 8*s12*s14 - 8*s12*s24)/(s123*s134*s23))
     .     - (8*s12**2 + 8*s12*s14 - 8*s12*s24)/(s123*s23*s234)
     .     - (-16*s12*s24 - 16*s14*s24)/(s23*s234**2)
     .     - (-8*s12**2 - 8*s12*s14 - 8*s12*s24
     .     - 16*s14*s24)/(s134*s23*s234)
     .     - (16*s13*s24**2)/(s23*s234**2*s34)
     .     - (-16*s12*s24 - 16*s14*s24)/(s234**2*s34)
     .     - (8*s12*s14 - 8*s14**2 - 8*s14*s24)/(s123*s134*s34)
     .     - (8*s12*s14 + 8*s14**2 - 8*s14*s24)/(s134*s234*s34)
     .     - (-8*s12*s14 - 8*s14**2 - 16*s12*s24
     .     - 8*s14*s24)/(s123*s234*s34) 
     .     - (8*s12*s13*s24 - 8*s13*s14*s24
     .     + 8*s13*s24**2)/(s134*s23*s234*s34)
     .     - (-8*s12*s13*s24 + 8*s13*s14*s24
     .     + 8*s13*s24**2)/(s123*s23*s234*s34)
     .     - (16*s12*s13*s14 + 8*s12*s13*s24 + 8*s13*s14*s24
     .     + 8*s13*s24**2)/(s123*s134*s23*s34)
      wt = wt/8d0/s1234

      Dy0g0Hsub = wt*born

      return
      end

************************************************************************

c     H -> b(i1) b(i3) bbar(i4) bbar(i2).
      real(8) function Dy0g0HAlt(p,i1,i4,i3,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      real(8), intent(in)  :: p(1:4,5)
      integer              :: imemode,icol
      integer              :: iint,h1,h2,h3
      real(8)              :: msq,born,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: amps(4,2,2,2)
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQ_mmmp,HbbQQ_mpmm
c     Common blocks.
      common/memode/imemode

c     Invariants.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
c     int = 1 mmpm type diagrams
c     int = 2 mmmp type diagrams
c     int = 3 mmpm type with 2 and 4 swapped for all diagrams
c     int = 4 mmmp type with 1 and 3 swapped for all diagrams
      iint=1
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amps(iint,1,2,1) = HbbQQ_mpmm(i2,i1,i3,i4,s,zb,za)     
      amps(iint,2,2,1) = HbbQQ_mpmm(i2,i1,i3,i4,s,za,zb)
c     These are i2 <-> i4 swapped.
      amps(iint,1,1,2) = HbbQQ_mmmp(i1,i4,i2,i3,s,zb,za)     
      amps(iint,2,1,2) = HbbQQ_mmmp(i1,i4,i2,i3,s,za,zb)
      amps(iint,1,2,2) = HbbQQ_mpmm(i4,i1,i3,i2,s,zb,za)     
      amps(iint,2,2,2) = HbbQQ_mpmm(i4,i1,i3,i2,s,za,zb)

      iint=2
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      amps(iint,1,2,1) = HbbQQ_mpmm(i1,i2,i3,i4,s,zb,za)     
      amps(iint,2,2,1) = HbbQQ_mpmm(i1,i2,i3,i4,s,za,zb)
c     These are i2 <-> i4 swapped.
      amps(iint,1,1,2) = HbbQQ_mmmp(i1,i4,i3,i2,s,zb,za)     
      amps(iint,2,1,2) = HbbQQ_mmmp(i1,i4,i3,i2,s,za,zb)
      amps(iint,1,2,2) = HbbQQ_mmmp(i3,i2,i1,i4,s,zb,za)     
      amps(iint,2,2,2) = HbbQQ_mmmp(i3,i2,i1,i4,s,za,zb)

      iint=3
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i1,i4,i2,i3,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i1,i4,i2,i3,s,za,zb)
      amps(iint,1,2,1) = HbbQQ_mpmm(i4,i1,i3,i2,s,zb,za)     
      amps(iint,2,2,1) = HbbQQ_mpmm(i4,i1,i3,i2,s,za,zb)
c     These are i2 <-> i4 swapped.
      amps(iint,1,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)     
      amps(iint,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amps(iint,1,2,2) = HbbQQ_mpmm(i2,i1,i3,i4,s,zb,za)     
      amps(iint,2,2,2) = HbbQQ_mpmm(i2,i1,i3,i4,s,za,zb)

      iint=4
c     Regular ordering.
      amps(iint,1,1,1) = HbbQQ_mmmp(i3,i2,i1,i4,s,zb,za)
      amps(iint,2,1,1) = HbbQQ_mmmp(i3,i2,i1,i4,s,za,zb)
      amps(iint,1,2,1) = HbbQQ_mpmm(i3,i2,i1,i4,s,zb,za)     
      amps(iint,2,2,1) = HbbQQ_mpmm(i3,i2,i1,i4,s,za,zb)
c     These are i2 <-> i4 swapped.
      amps(iint,1,1,2) = HbbQQ_mmmp(i3,i4,i1,i2,s,zb,za)     
      amps(iint,2,1,2) = HbbQQ_mmmp(i3,i4,i1,i2,s,za,zb)
      amps(iint,1,2,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)     
      amps(iint,2,2,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + (
     .              + amps(1,h1,h2,h3)*conjg(amps(3,h1,h2,h3))
     .              + amps(3,h1,h2,h3)*conjg(amps(1,h1,h2,h3))
     .              )
     .              + (
     .              + amps(2,h1,h2,h3)*conjg(amps(4,h1,h2,h3))
     .              + amps(4,h1,h2,h3)*conjg(amps(2,h1,h2,h3))
     .              )
            enddo
         enddo
      enddo
      msq = -msq/4d0/s1234

      Dy0g0HAlt = msq*born

      return
      end

c-----------------------------------------------------------------------
c     H -> 5j tree-level matrix elements.
c-----------------------------------------------------------------------

c     Full tree-level matrix element squared for
c     H -> b(i1) g(i3) g(i4) g(i5) bbar(i2).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullBy3g0H(p,i1,i3,i4,i5,i2)
      implicit none
      real(8), intent(in)  :: p(1:4,6)
      integer, intent(in)  :: i1,i2,i3,i4,i5
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Variables.
      real(8)              :: fac
      real(8)              :: as,ca,cflo,cf,tr,cn,nf
c     External.
      real(8), external    :: By3g0H,Bty3g0H,Btty3g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*2d0*cf*cn**2

      FullBy3g0H = 1d0/6d0*fac*(
     .     + By3g0H(p,i1,i3,i4,i5,i2)
     .     + By3g0H(p,i1,i3,i5,i4,i2)
     .     + By3g0H(p,i1,i4,i3,i5,i2)
     .     + By3g0H(p,i1,i4,i5,i3,i2)
     .     + By3g0H(p,i1,i5,i3,i4,i2)
     .     + By3g0H(p,i1,i5,i4,i3,i2)
     .     - 1d0/cn**2*(
     .     + Bty3g0H(p,i1,i3,i4,i5,i2)
     .     + Bty3g0H(p,i1,i3,i5,i4,i2)
     .     + Bty3g0H(p,i1,i4,i3,i5,i2)
     .     + Bty3g0H(p,i1,i4,i5,i3,i2)
     .     + Bty3g0H(p,i1,i5,i3,i4,i2)
     .     + Bty3g0H(p,i1,i5,i4,i3,i2)
     .     - Btty3g0H(p,i1,i3,i4,i5,i2)
     .     )
     .     + 1d0/cn**4*Btty3g0H(p,i1,i3,i4,i5,i2)
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function By3g0H(p,i1,i3,i4,i5,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: icol,h1,h2,h3,h4
      integer              :: j3,j4,j5
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: zA(6,6),zB(6,6)
      complex(8)           :: amp(6,2,2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: amp_Hbb3g_ppppp,amp_Hbb3g_ppppm
      complex(8), external :: amp_Hbb3g_pppmm,amp_Hbb3g_ppmmm
      complex(8), external :: amp_Hbb3g_pppmp,amp_Hbb3g_ppmpm

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)+s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes for a single colour ordering.
      icol = 1
      j3 = i3
      j4 = i4
      j5 = i5
      amp(:,:,:,:,:) = (0d0,0d0)

c     All + amplitudes.
      amp(icol,2,2,2,2) = +amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,za,zb)
      amp(icol,1,1,1,1) = -amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,zb,za)
         
c     MHV-bar amplitudes.
      amp(icol,2,1,1,1) = +amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,za,zb)
      amp(icol,1,2,2,2) = -amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,zb,za)
         
c     NMHV amplitudes.
      amp(icol,2,2,2,1) = +amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,za,zb)
      amp(icol,2,2,1,2) = +amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,za,zb)
      amp(icol,2,1,2,2) = +amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,za,zb)
         
      amp(icol,1,1,1,2) = -amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,zb,za)
      amp(icol,1,1,2,1) = -amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,zb,za)
      amp(icol,1,2,1,1) = -amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,zb,za)
         
c     NNMHV amplitudes.
      amp(icol,2,2,1,1) = +amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,za,zb)
      amp(icol,2,1,1,2) = +amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,za,zb)
      amp(icol,2,1,2,1) = +amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,za,zb)

      amp(icol,1,1,2,2) = -amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,zb,za)
      amp(icol,1,2,2,1) = -amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,zb,za)
      amp(icol,1,2,1,2) = -amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,zb,za)

c     Calculate squared matrix element.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  msq = msq
     .                 + amp(1,h1,h2,h3,h4)*conjg(amp(1,h1,h2,h3,h4))
               enddo
            enddo
         enddo
      enddo
      msq = msq/2d0/s12345

      By3g0H = msq*born

      return
      end

************************************************************************

c     Subleading-colour contribution to squared tree-level
c     matrix element for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
c     Gluon i5 is effectively photon-like.
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function Bty3g0H(p,i1,i3,i4,i5,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Parameters.
      integer, parameter   :: ii1(6)=(/1,1,2,2,3,3/)
      integer, parameter   :: ii2(6)=(/2,3,1,3,1,2/)
      integer, parameter   :: ii3(6)=(/3,2,3,1,2,1/)
c     Local.
      integer              :: imemode
      integer              :: ii(3)
      integer              :: icol,h1,h2,h3,h4
      integer              :: j3,j4,j5
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: zA(6,6),zB(6,6)
      complex(8)           :: amp(6,2,2,2,2),m(6)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: amp_Hbb3g_ppppp,amp_Hbb3g_ppppm
      complex(8), external :: amp_Hbb3g_pppmm,amp_Hbb3g_ppmmm
      complex(8), external :: amp_Hbb3g_pppmp,amp_Hbb3g_ppmpm

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)+s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes for the three colour orderings needed here.
      ii(1) = i3
      ii(2) = i4
      ii(3) = i5
      amp(:,:,:,:,:) = (0d0,0d0)
      do icol=1,6
         if (icol.ne.1 .and. icol.ne.2 .and. icol.ne.5) cycle
         j3 = ii(ii1(icol))
         j4 = ii(ii2(icol))
         j5 = ii(ii3(icol))

c     All + amplitudes.
         amp(icol,2,2,2,2) = +amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,1,1,1,1) = -amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,zb,za)
         
c     MHV-bar amplitudes.
         amp(icol,2,1,1,1) = +amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,1,2,2,2) = -amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,zb,za)
         
c     NMHV amplitudes.
         amp(icol,2,2,2,1) = +amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,2,1,2) = +amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,1,2,2) = +amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,za,zb)

         amp(icol,1,1,1,2) = -amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,1,2,1) = -amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,2,1,1) = -amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,zb,za)

c     NNMHV amplitudes.
         amp(icol,2,2,1,1) = +amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,1,1,2) = +amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,za,zb)
         amp(icol,2,1,2,1) = +amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,za,zb)

         amp(icol,1,1,2,2) = -amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,2,2,1) = -amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,zb,za)
         amp(icol,1,2,1,2) = -amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,zb,za)
      enddo

c     Calculate squared matrix element
c     |A(i1,i3,i4,i5,i2) + A(i1,i3,i5,i4,i2) + A(i1,i5,i3,i4,i2)|^2
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  m(1) = amp(1,h1,h2,h3,h4)
                  m(2) = amp(2,h1,h2,h4,h3)
                  m(5) = amp(5,h1,h4,h2,h3)
                  msq = msq
     .                 +(m(1)+m(2)+m(5))*conjg(m(1)+m(2)+m(5))
               enddo
            enddo
         enddo
      enddo
      msq = msq/2d0/s12345

      Bty3g0H = msq*born

      return
      end

************************************************************************

c     Subsubleading-colour contribution to squared tree-level
c     matrix element for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
c     All gluons are effectively photon-like.
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function Btty3g0H(p,i1,i3,i4,i5,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Parameters.
      integer, parameter   :: ii1(6)=(/1,1,2,2,3,3/)
      integer, parameter   :: ii2(6)=(/2,3,1,3,1,2/)
      integer, parameter   :: ii3(6)=(/3,2,3,1,2,1/)
c     Local.
      integer              :: imemode
      integer              :: ii(3),h(3)
      integer              :: icol,h1,h2,h3,h4,hc2,hc3,hc4
      integer              :: j3,j4,j5
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: zA(6,6),zB(6,6)
      complex(8)           :: amp(6,2,2,2,2),m
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: amp_Hbb3g_ppppp,amp_Hbb3g_ppppm
      complex(8), external :: amp_Hbb3g_pppmm,amp_Hbb3g_ppmmm
      complex(8), external :: amp_Hbb3g_pppmp,amp_Hbb3g_ppmpm

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)+s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes for all six colour orderings.
      ii(1) = i3
      ii(2) = i4
      ii(3) = i5
      amp(:,:,:,:,:) = (0d0,0d0)
      do icol=1,6
         j3 = ii(ii1(icol))
         j4 = ii(ii2(icol))
         j5 = ii(ii3(icol))

c     All + amplitudes.
         amp(icol,2,2,2,2) = +amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,1,1,1,1) = -amp_Hbb3g_ppppp(i1,i2,j3,j4,j5,s,zb,za)
         
c     MHV-bar amplitudes.
         amp(icol,2,1,1,1) = +amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,1,2,2,2) = -amp_Hbb3g_ppmmm(i1,i2,j3,j4,j5,s,zb,za)
         
c     NMHV amplitudes.
         amp(icol,2,2,2,1) = +amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,2,1,2) = +amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,1,2,2) = +amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,za,zb)

         amp(icol,1,1,1,2) = -amp_Hbb3g_ppppm(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,1,2,1) = -amp_Hbb3g_pppmp(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,2,1,1) = -amp_Hbb3g_ppppm(i2,i1,j5,j4,j3,s,zb,za)

c     NNMHV amplitudes.
         amp(icol,2,2,1,1) = +amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,za,zb)
         amp(icol,2,1,1,2) = +amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,za,zb)
         amp(icol,2,1,2,1) = +amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,za,zb)

         amp(icol,1,1,2,2) = -amp_Hbb3g_pppmm(i1,i2,j3,j4,j5,s,zb,za)
         amp(icol,1,2,2,1) = -amp_Hbb3g_pppmm(i2,i1,j5,j4,j3,s,zb,za)
         amp(icol,1,2,1,2) = -amp_Hbb3g_ppmpm(i1,i2,j3,j4,j5,s,zb,za)
      enddo

c     Calculate squared matrix element
c     |A(i1,i3,i4,i5,i2) + A(i1,i3,i5,i4,i2) + A(i1,i4,i3,i5,i2)
c     + A(i1,i4,i5,i3,i2) + A(i1,i5,i3,i4,i2) + A(i1,i5,i4,i3,i2)|^2
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  h(1) = h2
                  h(2) = h3
                  h(3) = h4
                  m = 0d0
                  do icol=1,6
                     hc2 = h(ii1(icol))
                     hc3 = h(ii2(icol))
                     hc4 = h(ii3(icol))
                     m   = m + amp(icol,h1,hc2,hc3,hc4)
                  enddo
                  msq = msq + real(m*conjg(m))
               enddo
            enddo
         enddo
      enddo
      msq = msq/2d0/s12345

      Btty3g0H = msq*born

      return
      end

c-----------------------------------------------------------------------
c     Library of tree-level amplitudes for
c     H -> b(i1) bbar(i2) g(i3) g(i4) g(i5)
c     with b quarks treated as massless.
c     CW Sept 18.

c     All-plus amplitude.
      complex(8) function amp_Hbb3g_ppppp(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      real(8)                :: s12345

      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)+s(i2,i3)+s(i2,i4)
     .     + s(i2,i5)+s(i3,i4)+s(i3,i5)+s(i4,i5)

      amp_Hbb3g_ppppp = s12345/(za(i2,i3)*za(i3,i4)*za(i4,i5)*za(i5,i1))

      return
      end

************************************************************************

c     MHV-bar amplitude for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      complex(8) function amp_Hbb3g_ppmmm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)

      amp_Hbb3g_ppmmm =
     .     zb(i1,i2)**2/(zb(i2,i3)*zb(i3,i4)*zb(i4,i5)*zb(i5,i1))

      return
      end

************************************************************************

c     NMHV amplitudes for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      complex(8) function amp_Hbb3g_ppppm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      complex(8)             :: zab2,zab3
      real(8)                :: t,t4,s12345

      t(i1,i2,i3)          = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4)      = s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4)    = za(i1,i2)*zb(i2,i4) + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5) = za(i1,i2)*zb(i2,i5) + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      s12345               = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      amp_Hbb3g_ppppm = (s12345*zab2(i5,i3,i4,i1)**3)/
     .     (t(i3,i4,i5)*t4(i1,i3,i4,i5)*za(i3,i4)*za(i4,i5)
     .     *zab2(i3,i4,i5,i1)*zab3(i2,i3,i4,i5,i1))
     .     - (za(i2,i5)*zab3(i5,i2,i3,i4,i1)**2)/
     .     (t4(i2,i3,i4,i5)*za(i2,i3)*za(i3,i4)*za(i4,i5)
     .     *zab3(i2,i3,i4,i5,i1))
     .     - (s12345*zb(i4,i1)**3)/
     .     (t(i1,i4,i5)*za(i2,i3)*zab2(i3,i4,i5,i1)*zb(i5,i1)*zb(i5,i4))

      return
      end

************************************************************************

c     NMHV amplitudes for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      complex(8) function amp_Hbb3g_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      complex(8)             :: zab2,zab3
      complex(8)             :: zba2,zba3,zba4
      complex(8)             :: zaa24,zaa22
      real(8)                :: t,t4,s12345

      t(i1,i2,i3)             = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4)         = s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4)       =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5)    =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zba2(i1,i2,i3,i4)       =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)    
      zba3(i1,i2,i3,i4,i5)    =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zba4(i1,i2,i3,i4,i6,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
     .     + zb(i1,i6)*za(i6,i5)

      zaa22(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zba2(i2,i4,i5,i6)
     .     + za(i1,i3)*zba2(i3,i4,i5,i6)
C      zaa23(i1,i2,i3,i4,i5,i6,i7)    =
C     .     + za(i1,i2)*zba3(i2,i4,i5,i6,i7)
C     .     + za(i1,i3)*zba3(i3,i4,i5,i6,i7)      
      zaa24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + za(i1,i2)*zba4(i2,i4,i5,i6,i7,i8)
     .     + za(i1,i3)*zba4(i3,i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      amp_Hbb3g_pppmp = (s12345*za(i1,i4)*zab2(i4,i1,i5,i3)**3)/
     .     (t(i1,i4,i5)*t4(i1,i3,i4,i5)*za(i1,i5)
     .     *za(i4,i5)*zaa24(i4,i1,i5,i1,i3,i4,i5,i2)*zab2(i1,i4,i5,i3))
     .     + (za(i2,i4)*zaa22(i4,i1,i5,i2,i3,i4)*zab2(i4,i2,i3,i5))/
     .     (t(i2,i3,i4)*za(i1,i5)*za(i2,i3)
     .     *za(i3,i4)*za(i4,i5)*zab2(i2,i3,i4,i5))
     .     + (za(i2,i4)*zab2(i4,i2,i3,i5)**2*zab3(i4,i2,i3,i5,i1))/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*za(i2,i3)
     .     *za(i3,i4)*za(i4,i5)*zab2(i2,i3,i4,i5))
     .     + (za(i1,i4)*za(i2,i4)**2
     .     *zaa22(i4,i1,i5,i2,i3,i4)*zb(i5,i1))/
     .     (za(i1,i5)*za(i2,i3)*za(i3,i4)*za(i4,i5)
     .     *zaa24(i4,i1,i5,i1,i3,i4,i5,i2)*
     .     zab2(i2,i3,i4,i5))
     .     + (s12345*zb(i5,i3)**4)/
     .     (t(i3,i4,i5)*zab2(i1,i4,i5,i3)
     .     *zab2(i2,i3,i4,i5)*zb(i4,i3)*zb(i5,i4))

      return
      end

************************************************************************

c     NNMHV amplitudes for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      complex(8) function amp_Hbb3g_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33
      real(8)                :: t,t4,s12345

      t(i1,i2,i3)          = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4)      = s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4)    = za(i1,i2)*zb(i2,i4) + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zab4(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zb(i2,i6)
     .     + za(i1,i3)*zb(i3,i6)
     .     + za(i1,i4)*zb(i4,i6)
     .     + za(i1,i5)*zb(i5,i6)

      zba2(i1,i2,i3,i4) = zb(i1,i2)*za(i2,i4) + zb(i1,i3)*za(i3,i4)
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)

      zbb22(i1,i2,i3,i4,i5,i6) =
     .     + zb(i1,i2)*zab2(i2,i4,i5,i6)
     .     + zb(i1,i3)*zab2(i3,i4,i5,i6)
      zbb23(i1,i2,i3,i4,i5,i6,i7) =
     .     + zb(i1,i2)*zab3(i2,i4,i5,i6,i7)
     .     + zb(i1,i3)*zab3(i3,i4,i5,i6,i7)      
      zbb24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab4(i2,i4,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab4(i3,i4,i5,i6,i7,i8)
      zbb33(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab3(i2,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab3(i3,i5,i6,i7,i8)
     .     + zb(i1,i4)*zab3(i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      amp_Hbb3g_pppmm = (za(i4,i5)**3*zb(i2,i1)**2)/
     .     (t(i3,i4,i5)*za(i3,i4)*zab2(i3,i4,i5,i1)*zab2(i5,i3,i4,i2))
     .     - (zb(i3,i1)**2*zbb24(i1,i4,i5,i1,i3,i4,i5,i2))/
     .     (t4(i1,i3,i4,i5)*zab2(i3,i4,i5,i1)
     .     *zb(i4,i3)*zb(i5,i1)*zb(i5,i4))
     .     + (zab2(i5,i2,i4,i3)*zab3(i5,i2,i3,i4,i1)**2*zb(i3,i2)**2)/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*zab2(i5,i3,i4,i2)
     .     *zb(i4,i3)*zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     - (zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zbb22(i1,i4,i5,i2,i3,i1))/
     .     (zab2(i3,i4,i5,i1)*zb(i4,i3)*zb(i5,i1)
     .     *zb(i5,i4)*zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     - zbb22(i1,i4,i5,i2,i3,i1)**2/
     .     (za(i2,i3)*zab2(i3,i4,i5,i1)*zb(i5,i1)*zb(i5,i4)
     .     *zbb24(i4,i2,i3,i2,i3,i4,i5,i1))

      return
      end

************************************************************************

c     Last NNMHV amplitude for H -> b(i1) bbar(i2) g(i3) g(i4) g(i5).
      complex(8) function amp_Hbb3g_ppmpm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33
      real(8)                :: t,t4,s12345

      t(i1,i2,i3)             = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4)         = s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4) =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zab4(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zb(i2,i6)
     .     + za(i1,i3)*zb(i3,i6)
     .     + za(i1,i4)*zb(i4,i6)
     .     + za(i1,i5)*zb(i5,i6)

      zba2(i1,i2,i3,i4) =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)    
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zbb22(i1,i2,i3,i4,i5,i6) =
     .     + zb(i1,i2)*zab2(i2,i4,i5,i6)
     .     + zb(i1,i3)*zab2(i3,i4,i5,i6)
      zbb23(i1,i2,i3,i4,i5,i6,i7) =
     .     + zb(i1,i2)*zab3(i2,i4,i5,i6,i7)
     .     + zb(i1,i3)*zab3(i3,i4,i5,i6,i7)      
      zbb24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab4(i2,i4,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab4(i3,i4,i5,i6,i7,i8)
      zbb33(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab3(i2,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab3(i3,i5,i6,i7,i8)
     .     + zb(i1,i4)*zab3(i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      amp_Hbb3g_ppmpm = (za(i3,i5)**4*zb(i2,i1)**2)/
     .     (t(i3,i4,i5)*za(i3,i4)*za(i4,i5)
     .     *zab2(i3,i4,i5,i1)*zab2(i5,i3,i4,i2))
     .     + (zab2(i5,i2,i3,i4)*zab3(i5,i2,i3,i4,i1)**2*zb(i4,i2)**3)/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*zab2(i5,i3,i4,i2)
     .     *zb(i3,i2)*zb(i4,i3)*zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     - (zab3(i3,i2,i4,i5,i1)*zb(i4,i1)**3*zb(i4,i2)**2)/
     .     (zab2(i3,i4,i5,i1)*zb(i3,i2)*zb(i4,i3)*zb(i5,i1)*zb(i5,i4)*
     .     zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     - (zab3(i3,i1,i4,i5,i2)*zb(i4,i1)**3
     .     *zbb33(i4,i1,i3,i5,i1,i4,i5,i2))/
     .     (t(i1,i4,i5)*t4(i1,i3,i4,i5)*zab2(i3,i4,i5,i1)
     .     *zb(i3,i2)*zb(i4,i3)*zb(i5,i1)*zb(i5,i4))

      return
      end

c-----------------------------------------------------------------------

c     Full tree-level matrix element squared for
c     H -> b(i1) bbar(i2) q(i3) qbar(i4) g(i5).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullCy1g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Variables.
      real(8)              :: fac
      real(8)              :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external    :: Cy1g0Ha,Cy1g0Hb,Cty1g0Ha,Cty1g0Hb,Ctty1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*2d0*cf*cn

      FullCy1g0H = fac*(
     .     + Cy1g0Ha(p,i1,i5,i4,i3,i2)
     .     + Cy1g0Hb(p,i1,i4,i3,i5,i2)
     .     + 1d0/cn**2*(
     .     + Cty1g0Ha(p,i1,i5,i2,i3,i4)
     .     + Cty1g0Hb(p,i1,i2,i3,i5,i4)
     .     - 2d0*Ctty1g0H(p,i1,i2,i3,i4,i5)
     .     )
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> b(i1) g(i5) qbar(i4) q(i3) bbar(i2) in A1 order.
      real(8) function Cy1g0Ha(p,i1,i5,i4,i3,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: h1,h2,h3
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: amp_c1(2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes corresponding to T(a5,i1,i4)*d_(i3,i2) term.
      amp_c1(:,:,:) = (0d0,0d0)
      
      amp_c1(2,2,2) = +HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,2,1) = +HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,1,1) = +HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,1,2) = +HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
  
      amp_c1(1,1,1) = -HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,1,2) = -HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,2,2) = -HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,2,1) = -HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + conjg(amp_c1(h1,h2,h3))*amp_c1(h1,h2,h3)
            enddo
         enddo
      enddo
      msq = msq/s12345/2d0

      Cy1g0Ha = msq*born

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> b(i1) qbar(i4) q(i3) g(i5) bbar(i2) in A2 order.
      real(8) function Cy1g0Hb(p,i1,i4,i3,i5,i2)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: h1,h2,h3
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: amp_c2(2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes corresponding to T(a5,i3,i2)*d_(i1,i4) term.
      amp_c2(:,:,:) = (0d0,0d0)

      amp_c2(2,1,2) = -HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,1,1) = -HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,1) = -HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,2) = -HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)

      amp_c2(1,2,1) = +HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,2,2) = +HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,2) = +HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,1) = +HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + conjg(amp_c2(h1,h2,h3))*amp_c2(h1,h2,h3)
            enddo
         enddo
      enddo
      msq = msq/s12345/2d0

      Cy1g0Hb = msq*born

      return
      end
      
************************************************************************

c     Subleading-colour contribution to
c     H -> b(i1) g(i5) bbar(i2) q(i3) qbar(i4) in B1 order.
      real(8) function Cty1g0Ha(p,i1,i5,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: h1,h2,h3
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: amp_sc1(2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes corresponding to T(a5,i1,i2)*d_(i3,i4) term.
      amp_sc1(:,:,:) = (0d0,0d0)

      amp_sc1(2,2,2) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,2,1) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,1,2) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,1,1) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)

      amp_sc1(1,1,1) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,1,2) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,2,1) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,2,2) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + conjg(amp_sc1(h1,h2,h3))*amp_sc1(h1,h2,h3)
            enddo
         enddo
      enddo
      msq = msq/s12345/2d0

      Cty1g0Ha = msq*born

      return
      end

************************************************************************

c     Subleading-colour contribution to
c     H -> b(i1) bbar(i2) q(i3) g(i5) qbar(i4) in B2 order.
      real(8) function Cty1g0Hb(p,i1,i2,i3,i5,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: h1,h2,h3
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: amp_sc2(2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes corresponding to T(a5,i3,i4)*d_(i1,i2) term.
      amp_sc2(:,:,:) = (0d0,0d0)

      amp_sc2(2,2,2) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,2,1) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,1,2) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,1,1) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)

      amp_sc2(1,1,1) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,1,2) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,2,1) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,2,2) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + conjg(amp_sc2(h1,h2,h3))*amp_sc2(h1,h2,h3)
            enddo
         enddo
      enddo
      msq = msq/s12345/2d0

      Cty1g0Hb = msq*born

      return
      end

************************************************************************

c     Colour-mixing part of subleading-colour contribution to
c     H -> b(i1) bbar(i2) q(i3) qbar(i4) g(i5),
c     corresponding to 2Re[(A1+A2)(B1+B2)^*].
      real(8) function Ctty1g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: h1,h2,h3
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: amp_c1(2,2,2),amp_c2(2,2,2)
      complex(8)           :: amp_sc1(2,2,2),amp_sc2(2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Calculate amplitudes corresponding to T(a5,i1,i4)*d_(i3,i2) term.
      amp_c1(:,:,:) = (0d0,0d0)
      
      amp_c1(2,2,2) = +HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,2,1) = +HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,1,1) = +HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,1,2) = +HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
  
      amp_c1(1,1,1) = -HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,1,2) = -HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,2,2) = -HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,2,1) = -HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)

c     Calculate amplitudes corresponding to T(a5,i3,i2)*d_(i1,i4) term.
      amp_c2(:,:,:) = (0d0,0d0)

      amp_c2(2,1,2) = -HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,1,1) = -HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,1) = -HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,2) = -HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)

      amp_c2(1,2,1) = +HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,2,2) = +HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,2) = +HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,1) = +HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)

c     Calculate amplitudes corresponding to T(a5,i1,i2)*d_(i3,i4) term.
      amp_sc1(:,:,:) = (0d0,0d0)

      amp_sc1(2,2,2) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,2,1) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,1,2) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,1,1) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)

      amp_sc1(1,1,1) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,1,2) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,2,1) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,2,2) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)

c     Calculate amplitudes corresponding to T(a5,i1,i2)*d_(i3,i4) term.
      amp_sc2(:,:,:) = (0d0,0d0)

      amp_sc2(2,2,2) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,2,1) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,1,2) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,1,1) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)

      amp_sc2(1,1,1) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,1,2) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,2,1) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,2,2) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               msq = msq
     .              + 2d0*Real(
     .              conjg(amp_sc1(h1,h2,h3)+amp_sc2(h1,h2,h3))
     .              * (amp_sc1(h1,h2,h3)+amp_sc2(h1,h2,h3))
     .              )
            enddo
         enddo
      enddo
c     Additional factor of 1/2 to match -2*Ctty1g0H structure.
      msq = msq/s12345/4d0

      Ctty1g0H = msq*born

      return
      end

c-----------------------------------------------------------------------
c     Library of tree-level amplitudes for
c     H -> b(i1) bbar(i2) q(i3) qqbar(i4) g(i5)
c     with b-quarks treated as massless.
c     Written by Ciaran Williams.

      complex(8) function HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      real(8)                :: t,t4,s12345
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3,zba4
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33,zaa22
      
      t(i1,i2,i3) = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4) =
     .     + s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4) =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zba2(i1,i2,i3,i4) =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)    
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zba4(i1,i2,i3,i4,i6,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
     .     + zb(i1,i6)*za(i6,i5)

      zaa22(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zba2(i2,i4,i5,i6)
     .     + za(i1,i3)*zba2(i3,i4,i5,i6)
C     zaa23(i1,i2,i3,i4,i5,i6,i7) =
C     .     + za(i1,i2)*zba3(i2,i4,i5,i6,i7)
C     .     + za(i1,i3)*zba3(i3,i4,i5,i6,i7)      
      zaa24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + za(i1,i2)*zba4(i2,i4,i5,i6,i7,i8)
     .     + za(i1,i3)*zba4(i3,i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)
      
      HbbQQbg_pppmp = (s12345*zab2(i4,i2,i3,i5)**3)/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*za(i3,i4)*
     .     zaa24(i4,i2,i3,i2,i3,i4,i5,i1)*zab2(i2,i3,i4,i5))
     .     + (za(i1,i4)*zab2(i4,i1,i5,i3)*zab3(i4,i1,i3,i5,i2))/
     .     (t4(i1,i3,i4,i5)*za(i1,i5)*za(i3,i4)*za(i4,i5)*
     .     zab2(i1,i4,i5,i3))
     .     + (za(i1,i4)**2*zaa22(i4,i1,i5,i2,i3,i4)*zb(i3,i2))/
     .     (za(i1,i5)*za(i3,i4)*za(i4,i5)*
     .     zaa24(i4,i2,i3,i2,i3,i4,i5,i1)*zab2(i1,i4,i5,i3))
     .     + (s12345*zb(i5,i3)**3)/
     .     (t(i3,i4,i5)*zab2(i1,i4,i5,i3)*zab2(i2,i3,i4,i5)*
     .     zb(i4,i3))

      return
      end
      
************************************************************************

      complex(8) function HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      real(8)                :: t,t4,s12345
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3,zba4
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33,zaa22

      t(i1,i2,i3) = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4) =
     .     + s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4) =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)    
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zab4(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zb(i2,i6)
     .     + za(i1,i3)*zb(i3,i6)
     .     + za(i1,i4)*zb(i4,i6)
     .     + za(i1,i5)*zb(i5,i6)

      zba2(i1,i2,i3,i4) =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zbb22(i1,i2,i3,i4,i5,i6) =
     .     + zb(i1,i2)*zab2(i2,i4,i5,i6)
     .     + zb(i1,i3)*zab2(i3,i4,i5,i6)
      zbb23(i1,i2,i3,i4,i5,i6,i7) =
     .     + zb(i1,i2)*zab3(i2,i4,i5,i6,i7)
     .     + zb(i1,i3)*zab3(i3,i4,i5,i6,i7)      
      zbb24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab4(i2,i4,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab4(i3,i4,i5,i6,i7,i8)
      zbb33(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab3(i2,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab3(i3,i5,i6,i7,i8)
     .     + zb(i1,i4)*zab3(i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      HbbQQbg_pppmm = -((za(i3,i5)*za(i4,i5)**2*zb(i2,i1)**2)/
     .     (t(i3,i4,i5)*za(i3,i4)*zab2(i3,i4,i5,i1)*
     .     zab2(i5,i3,i4,i2)))
     .     - (zb(i3,i1)*zb(i4,i1)*zbb24(i1,i4,i5,i1,i3,i4,i5,i2))/
     .     (t4(i1,i3,i4,i5)*zab2(i3,i4,i5,i1)*zb(i4,i3)*zb(i5,i1)*
     .     zb(i5,i4))
     .     + (zab2(i5,i2,i3,i4)*zab3(i5,i2,i3,i4,i1)**2*zb(i3,i2)**2)/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*zab2(i5,i3,i4,i2)*zb(i4,i3)*
     .     zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     - (zb(i3,i2)*zb(i4,i1)**2*zbb22(i1,i4,i5,i2,i3,i1))/
     .     (zab2(i3,i4,i5,i1)*zb(i4,i3)*zb(i5,i1)*zb(i5,i4)*
     .     zbb24(i4,i2,i3,i2,i3,i4,i5,i1))

      return
      end

************************************************************************

      complex(8) function HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      real(8)                :: t,t4,s12345
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3,zba4
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33,zaa22
   
      t(i1,i2,i3) = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4) =
     .     + s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4) =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)    
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zab4(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zb(i2,i6)
     .     + za(i1,i3)*zb(i3,i6)
     .     + za(i1,i4)*zb(i4,i6)
     .     + za(i1,i5)*zb(i5,i6)

      zba2(i1,i2,i3,i4) =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)    
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zbb22(i1,i2,i3,i4,i5,i6) =
     .     + zb(i1,i2)*zab2(i2,i4,i5,i6)
     .     + zb(i1,i3)*zab2(i3,i4,i5,i6)
      zbb23(i1,i2,i3,i4,i5,i6,i7) =
     .     + zb(i1,i2)*zab3(i2,i4,i5,i6,i7)
     .     + zb(i1,i3)*zab3(i3,i4,i5,i6,i7)      
      zbb24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab4(i2,i4,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab4(i3,i4,i5,i6,i7,i8)
      zbb33(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + zb(i1,i2)*zab3(i2,i5,i6,i7,i8)
     .     + zb(i1,i3)*zab3(i3,i5,i6,i7,i8)
     .     + zb(i1,i4)*zab3(i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)

      HbbQQbg_ppmpm = (za(i3,i5)**3*zb(i2,i1)**2)/
     .     (t(i3,i4,i5)*za(i3,i4)*zab2(i3,i4,i5,i1)*zab2(i5,i3,i4,i2))
     .     + (zab3(i3,i1,i4,i5,i2)*zb(i4,i1)**3)/(t4(i1,i3,i4,i5)
     .     *zab2(i3,i4,i5,i1)*zb(i4,i3)*zb(i5,i1)*zb(i5,i4))
     .     - (zab2(i5,i2,i3,i4)*zab3(i5,i2,i3,i4,i1)**2*zb(i4,i2)**2)/
     .     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*zab2(i5,i3,i4,i2)*zb(i4,i3)*
     .     zbb24(i4,i2,i3,i2,i3,i4,i5,i1))
     .     + (zab3(i3,i2,i4,i5,i1)*zb(i4,i1)**3*zb(i4,i2))/
     .     (zab2(i3,i4,i5,i1)*zb(i4,i3)*zb(i5,i1)*zb(i5,i4)
     .     *zbb24(i4,i2,i3,i2,i3,i4,i5,i1))

      return
      end

************************************************************************

      complex(8) function HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,i5
      real(8), intent(in)    :: s(6,6)
      complex(8), intent(in) :: za(6,6),zb(6,6)
      integer                :: i6,i7,i8
      real(8)                :: t,t4,s12345
      complex(8)             :: zab2,zab3,zab4
      complex(8)             :: zba2,zba3,zba4
      complex(8)             :: zbb24,zbb23,zbb33,zbb22
      complex(8)             :: zaa24,zaa33,zaa22
      
      t(i1,i2,i3) = s(i1,i2) + s(i1,i3) + s(i2,i3)
      t4(i1,i2,i3,i4) =
     .     + s(i1,i2) + s(i1,i3) + s(i1,i4)
     .     + s(i2,i3) + s(i2,i4) + s(i3,i4)
      zab2(i1,i2,i3,i4) =
     .     + za(i1,i2)*zb(i2,i4)
     .     + za(i1,i3)*zb(i3,i4)
      zab3(i1,i2,i3,i4,i5) =
     .     + za(i1,i2)*zb(i2,i5)
     .     + za(i1,i3)*zb(i3,i5)
     .     + za(i1,i4)*zb(i4,i5)
      zba2(i1,i2,i3,i4) =
     .     + zb(i1,i2)*za(i2,i4)
     .     + zb(i1,i3)*za(i3,i4)    
      zba3(i1,i2,i3,i4,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
      zba4(i1,i2,i3,i4,i6,i5) =
     .     + zb(i1,i2)*za(i2,i5)
     .     + zb(i1,i3)*za(i3,i5)
     .     + zb(i1,i4)*za(i4,i5)
     .     + zb(i1,i6)*za(i6,i5)

      zaa22(i1,i2,i3,i4,i5,i6) =
     .     + za(i1,i2)*zba2(i2,i4,i5,i6)
     .     + za(i1,i3)*zba2(i3,i4,i5,i6)
C     zaa23(i1,i2,i3,i4,i5,i6,i7) =
C     .     + za(i1,i2)*zba3(i2,i4,i5,i6,i7)
C     .     + za(i1,i3)*zba3(i3,i4,i5,i6,i7)      
      zaa24(i1,i2,i3,i4,i5,i6,i7,i8) =
     .     + za(i1,i2)*zba4(i2,i4,i5,i6,i7,i8)
     .     + za(i1,i3)*zba4(i3,i4,i5,i6,i7,i8)

      s12345 = s(i1,i2) + s(i1,i3) + s(i1,i4) + s(i1,i5)
     .     + s(i2,i3) + s(i2,i4) + s(i2,i5)
     .     + s(i3,i4) + s(i3,i5) + s(i4,i5)
      HbbQQbg_ppmpp =
     .     (za(i1,i4)*zaa24(i4,i1,i5,i1,i2,i4,i5,i3)*zab2(i1,i4,i5,i2))/
     -     (za(i1,i5)*za(i3,i4)*za(i4,i5)*
     -     zaa24(i4,i2,i3,i2,i3,i4,i5,i1)*zab2(i1,i4,i5,i3))
     .     - (s12345*zab2(i3,i2,i4,i5)**2*zab2(i4,i2,i3,i5))/
     -     (t(i2,i3,i4)*t4(i2,i3,i4,i5)*za(i3,i4)*
     -     zaa24(i4,i2,i3,i2,i3,i4,i5,i1)*zab2(i2,i3,i4,i5))
     .     + (t(i1,i4,i5)*za(i1,i4)*zab3(i3,i1,i4,i5,i2))/
     -     (t4(i1,i3,i4,i5)*za(i1,i5)*za(i3,i4)
     .     *za(i4,i5)*zab2(i1,i4,i5,i3))
     .     - (s12345*za(i3,i4)*zb(i5,i3)*zb(i5,i4)**2)/
     -     (s(i3,i4)*t(i3,i4,i5)*zab2(i1,i4,i5,i3)*zab2(i2,i3,i4,i5))

        return
        end

c-----------------------------------------------------------------------

c     Full tree-level matrix element squared for
c     H -> b(i1) bbar(i2) b(i3) bbar(i4) g(i5).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullDy1g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Variables.
      real(8)              :: fac
      real(8)              :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external    :: Cy1g0Ha,Cy1g0Hb,Cty1g0Ha,Cty1g0Hb,Ctty1g0H
      real(8), external    :: Dy1g0H,Dty1g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      fac = (4d0*pi*as)**3*2d0*cf*cn

      FullDy1g0H = 1d0/4d0*fac*(
c     Default ordering.
     .     + Cy1g0Ha(p,i1,i5,i4,i3,i2)
     .     + Cy1g0Ha(p,i1,i5,i2,i3,i4)
     .     + Cy1g0Ha(p,i3,i5,i2,i1,i4)
     .     + Cy1g0Ha(p,i3,i5,i4,i1,i2)
     .     + Cy1g0Hb(p,i1,i4,i3,i5,i2)
     .     + Cy1g0Hb(p,i1,i2,i3,i5,i4)
     .     + Cy1g0Hb(p,i3,i2,i1,i5,i4)
     .     + Cy1g0Hb(p,i3,i4,i1,i5,i2)

     .     + 1d0/cn**2*(
     .     + Cty1g0Ha(p,i1,i5,i2,i3,i4)
     .     + Cty1g0Ha(p,i1,i5,i4,i3,i2)
     .     + Cty1g0Ha(p,i3,i5,i4,i1,i2)
     .     + Cty1g0Ha(p,i3,i5,i2,i1,i4)
     .     + Cty1g0Hb(p,i1,i2,i3,i5,i4)
     .     + Cty1g0Hb(p,i1,i4,i3,i5,i2)
     .     + Cty1g0Hb(p,i3,i4,i1,i5,i2)
     .     + Cty1g0Hb(p,i3,i2,i1,i5,i4)
     .     - 2d0*Ctty1g0H(p,i1,i2,i3,i4,i5)
     .     - 2d0*Ctty1g0H(p,i1,i4,i3,i2,i5)
     .     - 2d0*Ctty1g0H(p,i3,i4,i1,i2,i5)
     .     - 2d0*Ctty1g0H(p,i3,i2,i1,i4,i5)
     .     )

     .     - 1d0/cn*(
     .     + Dy1g0H(p,i1,i2,i3,i4,i5)
     .     + Dy1g0H(p,i1,i4,i3,i2,i5)
     .     + Dy1g0H(p,i3,i4,i1,i2,i5)
     .     + Dy1g0H(p,i3,i2,i1,i4,i5)
     .     - Dty1g0H(p,i1,i2,i3,i4,i5)
     .     - Dty1g0H(p,i2,i1,i4,i3,i5)
     .     - Dty1g0H(p,i1,i4,i3,i2,i5)
     .     - Dty1g0H(p,i4,i1,i2,i3,i5)
     .     - Dty1g0H(p,i3,i4,i1,i2,i5)
     .     - Dty1g0H(p,i4,i3,i2,i1,i5)
     .     - Dty1g0H(p,i3,i2,i1,i4,i5)
     .     - Dty1g0H(p,i2,i3,i4,i1,i5)
c     (1,2,3,4,5) -> (1,4,3,2,5)
c     (2,1,4,3,5) -> (4,1,2,3,5)
c     (3,2,1,4,5) -> (3,4,1,2,5)
c     (4,3,2,1,5) -> (2,3,4,1,5)
     .     )

     .     + 1d0/cn**3*(
     .     + Dty1g0H(p,i1,i2,i3,i4,i5)
     .     + Dty1g0H(p,i2,i1,i4,i3,i5)
     .     + Dty1g0H(p,i1,i4,i3,i2,i5)
     .     + Dty1g0H(p,i4,i1,i2,i3,i5)
     .     + Dty1g0H(p,i3,i4,i1,i2,i5)
     .     + Dty1g0H(p,i4,i3,i2,i1,i5)
     .     + Dty1g0H(p,i3,i2,i1,i4,i5)
     .     + Dty1g0H(p,i2,i3,i4,i1,i5)
     .     )
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4) g(i5).
      real(8) function Dy1g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: icol
      integer              :: h1,h2,h3,h4,h5
      real(8)              :: s12345,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: Qlc1(1:4,2,2,2,2,2),Qlc2(1:4,2,2,2,2,2)
      complex(8)           :: Qslc1(1:4,2,2,2,2,2),Qslc2(1:4,2,2,2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Fill amplitudes.
c     Default ordering 1,2,3,4.
      icol=1
      call HbbQQbg_ampfill(i1,i2,i3,i4,i5,s,za,zb,
     .     Qlc1(icol,:,:,:,:,:),Qlc2(icol,:,:,:,:,:),
     .     Qslc1(icol,:,:,:,:,:),Qslc2(icol,:,:,:,:,:))
c     Second ordering, swap 2<->4.
      icol=2
      call HbbQQbg_ampfill(i1,i4,i3,i2,i5,s,za,zb,
     .     Qlc2(icol,:,:,:,:,:),Qlc1(icol,:,:,:,:,:),
     .     Qslc2(icol,:,:,:,:,:),Qslc1(icol,:,:,:,:,:))
c     Fourth ordering, swap 1<->3.
      icol=4
      call HbbQQbg_ampfill(i3,i2,i1,i4,i5,s,za,zb,
     .     Qlc2(icol,:,:,:,:,:),Qlc1(icol,:,:,:,:,:),
     .     Qslc2(icol,:,:,:,:,:),Qslc1(icol,:,:,:,:,:))

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  do h5=1,2
                     msq = msq
     .                    - 2d0*real(
     .                    + conjg(Qlc1(1,h1,h2,h3,h4,h5))
     .                    *Qslc1(2,h1,h4,h3,h2,h5)
     .                    + conjg(Qlc2(1,h1,h2,h3,h4,h5))
     .                    *Qslc2(2,h1,h4,h3,h2,h5)
     .                    + conjg(Qlc2(1,h1,h2,h3,h4,h5))
     .                    *Qslc1(4,h3,h2,h1,h4,h5)
     .                    + conjg(Qlc1(1,h1,h2,h3,h4,h5))
     .                    *Qslc2(4,h3,h2,h1,h4,h5)
     .                    )
                  enddo
             enddo
          enddo
       enddo
      enddo
      msq = -msq/2d0/s12345

      Dy1g0H = msq*born

      return
      end

************************************************************************

c     Subleading-colour contribution to
c     H -> b(i1) bbar(i2) b(i3) bbar(i4) g(i5).
      real(8) function Dty1g0H(p,i1,i2,i3,i4,i5)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,i5
      real(8), intent(in)  :: p(1:4,6)
c     Variables.
      integer              :: imemode
      integer              :: icol,h1,h2,h3,h4,h5
      real(8)              :: s12345,fac,msq,born
      real(8)              :: s(6,6)
      complex(8)           :: za(6,6),zb(6,6)
      complex(8)           :: Qlc1(1:4,2,2,2,2,2),Qlc2(1:4,2,2,2,2,2)
      complex(8)           :: Qslc1(1:4,2,2,2,2,2),Qslc2(1:4,2,2,2,2,2)
c     Common blocks.
      common/memode/imemode
c     External.
      real(8), external    :: By0g0H
      complex(8), external :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8), external :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     Fill zA, zB, and s.
      call fillSpinors(6,p,zA,zB,s)
      s12345 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i1,i5)
     .     + s(i2,i3)+s(i2,i4)+s(i2,i5)
     .     + s(i3,i4)+s(i3,i5)+s(i4,i5)

c     Born.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s12345)

c     Fill amplitudes.
c     Default ordering 1,2,3,4.
      icol=1
      call HbbQQbg_ampfill(i1,i2,i3,i4,i5,s,za,zb,
     .     Qlc1(icol,:,:,:,:,:),Qlc2(icol,:,:,:,:,:),
     .     Qslc1(icol,:,:,:,:,:),Qslc2(icol,:,:,:,:,:))
c     Second ordering, swap 2<->4.
      icol=2
      call HbbQQbg_ampfill(i1,i4,i3,i2,i5,s,za,zb,
     .     Qlc2(icol,:,:,:,:,:),Qlc1(icol,:,:,:,:,:),
     .     Qslc2(icol,:,:,:,:,:),Qslc1(icol,:,:,:,:,:))

c     Calculate matrix element squared.
      msq = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  do h5=1,2
                     msq = msq
     .                    - conjg(
     .                    + Qslc1(1,h1,h2,h3,h4,h5)
     .                    + Qslc2(1,h1,h2,h3,h4,h5)
     .                    )*(
     .                    + Qslc1(2,h1,h4,h3,h2,h5)
     .                    + Qslc2(2,h1,h4,h3,h2,h5)
     .                    )
                  enddo
             enddo
          enddo
       enddo
      enddo
      msq = msq/2d0/s12345

      Dty1g0H = msq*born

      return
      end

c-----------------------------------------------------------------------
c     Auxiliary function to fill H -> b bbar Q Qbar g amplitudes.
c     Used only in same-flavour matrix element.
c     Written by Ciaran Williams.

      subroutine HbbQQbg_ampfill(i1,i2,i3,i4,i5,s,za,zb,
     .     amp_c1,amp_c2,amp_sc1,amp_sc2)
      implicit none
      integer, intent(in)     :: i1,i2,i3,i4,i5
      real(8), intent(in)     :: s(6,6)
      complex(8), intent(in)  :: za(6,6),zb(6,6)
      complex(8), intent(out) :: amp_c1(2,2,2,2,2),amp_c2(2,2,2,2,2)
      complex(8), intent(out) :: amp_sc1(2,2,2,2,2),amp_sc2(2,2,2,2,2)
      integer                 :: h1,h2,h3,h4
c     Externals.
      complex(8), external    :: HbbQQbg_pppmp,HbbQQbg_pppmm
      complex(8) ,external    :: HbbQQbg_ppmpm,HbbQQbg_ppmpp

c     T17*d35 LC contribution. 
      amp_c1(:,:,:,:,:) = (0d0,0d0)

      amp_c1(2,2,2,1,2) = +HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,2,2,1,1) = +HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,2,1,2,1) = +HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)
      amp_c1(2,2,1,2,2) = +HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
  
      amp_c1(1,1,1,2,1) = -HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,1,1,2,2) = -HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,1,2,1,2) = -HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)
      amp_c1(1,1,2,1,1) = -HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)

c     T35*d17 LC contribution.
      amp_c2(:,:,:,:,:) = (0d0,0d0)

      amp_c2(2,2,1,2,2) = -HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,1,2,1) = -HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,2,1,1) = -HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_c2(2,2,2,1,2) = -HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)
  
      amp_c2(1,1,2,1,1) = +HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,2,1,2) = +HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,1,2,2) = +HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_c2(1,1,1,2,1) = +HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)

c     T57*d13 SLC contribution, needs to be divided by 1/NC.
      amp_sc1(:,:,:,:,:) = (0d0,0d0)

      amp_sc1(2,2,2,1,2) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,2,2,1,1) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,2,1,2,2) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,za,zb)
      amp_sc1(2,2,1,2,1) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     - HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,za,zb)

      amp_sc1(1,1,1,2,1) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,1,1,2,2) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_pppmm(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,1,2,1,1) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpp(i1,i2,i3,i4,i5,s,zb,za)
      amp_sc1(1,1,2,1,2) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     + HbbQQbg_ppmpm(i1,i2,i3,i4,i5,s,zb,za)
      
c     T57*d13 SLC contribution, needs to be divided by 1/NC.
      amp_sc2(:,:,:,:,:) = (0d0,0d0)
      
      amp_sc2(2,2,2,1,2) = -HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,2,2,1,1) = -HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,2,1,2,2) = -HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,za,zb)
      amp_sc2(2,2,1,2,1) = -HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,za,zb)
     .     + HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,za,zb)

      amp_sc2(1,1,1,2,1) = +HbbQQbg_ppmpp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,1,1,2,2) = +HbbQQbg_ppmpm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_ppmpm(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,1,2,1,1) = +HbbQQbg_pppmp(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmp(i2,i1,i4,i3,i5,s,zb,za)
      amp_sc2(1,1,2,1,2) = +HbbQQbg_pppmm(i1,i2,i4,i3,i5,s,zb,za)
     .     - HbbQQbg_pppmm(i2,i1,i4,i3,i5,s,zb,za)
      
      return
      end

c-----------------------------------------------------------------------
