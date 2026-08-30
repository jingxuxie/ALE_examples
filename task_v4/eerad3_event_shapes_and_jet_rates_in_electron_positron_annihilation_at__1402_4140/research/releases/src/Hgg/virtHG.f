c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     One-loop matrix elements for Higgs decays to gluons
c     plus up to two additional partons.

c     Common block 'memode' determines whether to include Born or not:
c     imemode = 0  exclude Born
c     imemode = 1  include Born

c-----------------------------------------------------------------------
c     H -> 2j one-loop matrix elements.
c     Constructed from antenna functions given in
c     section 7 of hep-ph/0505111.
c----------------------------------------------------------------------- 

c     Full one-loop matrix element for
c     H -> g(i1) g(i2).
      real(8) function FullA2g1H(p,i1,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1, i2, ipole
      real(8), intent(in) :: p(1:4,3), renscale2
      real(8)             :: s12
c     Externals.
      real(8), external   :: A2g1H, Ah2g1H, dot

      s12 = 2d0*dot(p(1,i1),p(1,i2))
      FullA2g1H =
     .     + A2g1H(s12,renscale2,ipole)
     .     + Ah2g1H(s12,renscale2,ipole)

      return
      end

************************************************************************

c     Leading-colour contribution
c     H -> g(i1) g(i2).
      real(8) function A2g1H(s12,renscale2,ipole)
      implicit none
      real(8), intent(in) :: s12, renscale2
      integer, intent(in) :: ipole
      integer             :: ischeme
      real(8)             :: as,ca,cflo,cf,tr,cn
      real(8)             :: e2,e1,e0
      real(8)             :: dlogs,fac,tree
      real(8), parameter  :: pi=3.141592653589793238d0
      real(8), external   :: A2g0H
      common/qcd/as,ca,cflo,cf,tr,cn
      
      fac   = as/2d0/pi*cn
      tree  = A2g0H(s12)
      dlogs = log(s12/renscale2)

c     Scheme choice. 
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      e2 = -2d0
      e1 = -11d0/3d0 + 2d0*dlogs
      e0 = pi**2 - dlogs**2
      if (ischeme.eq.1) e0 = e0 - e2*pi**2/12d0
c     Include O(as) term from HGG Wilson coefficient.
      e0 = e0 + 11d0/3d0
      
      A2g1H = 0d0
      select case(ipole)
      case(0)
         A2g1H = fac*e0*tree
      case(-1)
         A2g1H = fac*e1*tree
      case(-2)
         A2g1H = fac*e2*tree
      end select

      return
      end

************************************************************************

c     Quark-loop contribution to
c     H -> g(i1) g(i2).
      real(8) function Ah2g1H(s12, renscale2, ipole)
      implicit none
      real(8), intent(in) :: s12, renscale2
      integer, intent(in) :: ipole
      integer             :: ischeme
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
      real(8)             :: e2,e1,e0
      real(8)             :: dlogs,fac,tree
      real(8), external   :: A2g0H
      real(8), parameter  :: pi=3.141592653589793238d0
      common/qcd/as,ca,cflo,cf,tr,cn
      
      fac   = as/2d0/pi
      tree  = A2g0H(s12)
      dlogs = log(abs(renscale2/s12))
      nf    = 2d0*tr

c     Scheme choice. 
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      e2 = 0d0
      e1 = 2d0*nf/3d0
      e0 = 0d0

      Ah2g1H = 0d0
      select case(ipole)
      case(0)
         Ah2g1H = fac*e0*tree
      case(-1)
         Ah2g1H = fac*e1*tree
      case(-2)
         Ah2g1H = fac*e2*tree
      end select

      return
      end

c-----------------------------------------------------------------------
c     H -> 3j one-loop matrix elements.
c----------------------------------------------------------------------- 

c     Full H -> g g g Born-one-loop interference.
c     Adapted from NNLOJET/MCFM (src/process/H/libAHloop.f).
      real(8) function FullA3g1H(p,i1,i2,i3,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      real(8)               :: fac,nf
      real(8)               :: as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external     :: A3g1H,Ah3g1H,dot
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)*cn**2

      FullA3g1H = 1d0/3d0*fac*(
     .     + A3g1H(p,i1,i2,i3,renscale2,ipole)
     .     + A3g1H(p,i1,i3,i2,renscale2,ipole)
     .     + nf/cn*(
     .     + Ah3g1H(p,i1,i2,i3,renscale2,ipole)
     .     + Ah3g1H(p,i1,i3,i2,renscale2,ipole)
     .     )
     .     )

      return
      end

************************************************************************

c     Leading-colour contribution to Born-one-loop interference of
c     H -> g(i1) g(i2) g(i3).
      real(8) function A3g1H(p,i1,i2,i3,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      integer               :: imemode,ischeme
      real(8)               :: born,tree
      real(8)               :: Li2s12,Li2s13,Li2s23,lnm,pisq
      real(8)               :: s12,s13,s23,s123
      complex(8)            :: lns12,lns13,lns23,ln2s13,ln2s23
c     Externals.
      real(8), external     :: dot,A2g0H,A3g0H,ddilog
      complex(8), external  :: lnrat
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12  = 2d0*dot(p(1,i1),p(1,i2))
      s13  = 2d0*dot(p(1,i1),p(1,i3))
      s23  = 2d0*dot(p(1,i2),p(1,i3))
      s123 = s12+s13+s23

      pisq = pi**2
      Li2s13 = ddilog(s13/s123)
      Li2s23 = ddilog(s23/s123)
      Li2s12 = ddilog((s12-s123)/s12)
      lns12  = lnrat(s12,s123)
      lns13  = lnrat(-s13,s123)
      lns23  = lnrat(-s23,s123)
      lnm    = log(renscale2/s123)
      ln2s13 = lnrat((s123-s13),s123)
      ln2s23 = lnrat((s123-s23),s123)

      born = 1d0
      if (imemode.eq.1) born = A2g0H(s123)
      tree = A3g0H(p,i1,i2,i3)/born

      A3g1H = 0d0
      if (ipole.eq.-2)then
         A3g1H = tree*(-3d0)
      elseif (ipole.eq.-1)then
         A3g1H = tree*(-11d0/6d0*3d0 + lns12 + lns13 + lns23 - 3d0*lnm)
      elseif (ipole.eq.0)then
         A3g1H = tree*(
     .        + 2d0*(Li2s12+Li2s13+Li2s23)
     .        + lnm*(lns12+lns13+lns23)
     .        - lns12*lns13 - lns12*lns23 - lns13*lns23
     .        + 1d0/2d0*(lns12**2-lns13**2-lns23**2) - 3d0/2d0*lnm**2
     .        + 2d0*(lns23*ln2s23+lns13*ln2s13) + 4d0/3d0*pisq
     .        )
     .        + 1d0/3d0*(1d0+s123/s12+s123/s13+s123/s23)/s123
c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
         ischeme = 0
         if (ischeme.eq.1) A3g1H = A3g1H + tree*pisq/4d0
c     Explicit pi^2 terms from analytic continuation not captured above.
         if ((s12.gt.0d0).and.(s13.gt.0d0).and.(s23.gt.0d0))then
            A3g1H = A3g1H - tree*pisq*2d0
         endif
c     Include O(as) term from Wilson coefficient.
         A3g1H = A3g1H + 11d0/3d0*tree
      endif

      A3g1H = born*A3g1H

      return
      end

************************************************************************

c     Quark-loop contribution to Born-one-loop interference of
c     H -> g(i1) g(i2) g(i3).
      real(8) function Ah3g1H(p,i1,i2,i3,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      integer               :: imemode
      real(8)               :: s12,s13,s23,s,t,u,s123,pisq
      real(8)               :: born,tree
c     Externals.
      real(8), external     :: dot,A2g0H,A3g0H
c     Common blocks.
      common/memode/imemode

c     Invariants.
      s12  = 2d0*dot(p(1,i1),p(1,i2))
      s13  = 2d0*dot(p(1,i1),p(1,i3))
      s23  = 2d0*dot(p(1,i2),p(1,i3))
      s123 = s12+s13+s23

      born = 1d0
      if (imemode.eq.1) born = A2g0H(s123)
      tree = A3g0H(p,i1,i2,i3)/born

      Ah3g1H = 0d0
      if (ipole.eq.-2)then
         Ah3g1H = 0d0
      elseif (ipole.eq.-1)then
         Ah3g1H = tree*(1d0)
      elseif (ipole.eq.0)then
         Ah3g1H = -1d0/3d0*(1d0+s123/s12+s123/s13+s123/s23)/s123
      endif
      Ah3g1H = born*Ah3g1H

      return
      end

c-----------------------------------------------------------------------

c     Full one-loop matrix element for
c     H -> q(i1) g(i3) qbar(i2).
c     Adapted from NNLOJET/MCFM (src/process/H/libAHloop.f).
      real(8) function FullB1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      real(8)               :: fac
      real(8)               :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external     :: B1g1H,Bt1g1H,Bh1g1H,dot
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)*cn

      FullB1g1H = 2d0*fac*(
     .     + B1g1H(p,i1,i3,i2,renscale2,ipole)
     .     - 1d0/cn**2*Bt1g1H(p,i1,i3,i2,renscale2,ipole)
     .     + nf/cn*Bh1g1H(p,i1,i3,i2,renscale2,ipole)
     .     )

      return
      end

************************************************************************

      real(8) function B1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      integer               :: imemode,ischeme
      real(8), parameter    :: pi=3.141592653589793238d0
      real(8)               :: fac,born,tree
      real(8)               :: s,t,u,s12,s13,s23
      real(8)               :: Li2s,Li2t,Li2u,mhsq,lnm,pisq
      complex(8)            :: lns,lnt,lnu,ln2t,ln2u
c     Externals.
      real(8), external     :: dot,A2g0H,B1g0H,ddilog
      complex(8), external  :: lnrat
c     Common blocks.
      common/memode/imemode

      pisq = pi**2

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))

      s    = s12
      t    = s23
      u    = s13
      mhsq = s+t+u
      lnm  = log(renscale2/mhsq)

      Li2t = ddilog(t/mhsq)
      Li2u = ddilog(u/mhsq)
      Li2s = ddilog((s-mhsq)/s)
      lns  = lnrat(s,mhsq)
      lnt  = lnrat(-t,mhsq)
      lnu  = lnrat(-u,mhsq)
      ln2t = lnrat((mhsq-t),mhsq)
      ln2u = lnrat((mhsq-u),mhsq)
      
      born = 1d0
      if (imemode.eq.1) born = A2g0H(mhsq)
      tree = B1g0H(p,i1,i3,i2)/born

      B1g1H = 0d0
      select case(ipole)
      case(-2)
         B1g1H = tree*(-2d0)
      case(-1)
         B1g1H = tree*(-10d0/3d0 + lnt + lnu - 2d0*lnm)
      case(0)
         B1g1H = tree*(
     .        + 40d0/9d0 + Li2t + Li2u + 2d0*Li2s
     .        - 13d0/6d0*(lns-lnm) + (lnm-lns)*(lnt+lnu)
     .        + lnt*ln2t + lnu*ln2u
     .        + lns**2 - 0.5d0*lnt**2 - 0.5d0*lnu**2 - lnm**2
     .        )
     .        - (t+u)/2d0/mhsq**2
         if (s.lt.0d0) then
            B1g1H = B1g1H + tree*pisq*10d0/9d0
            B1g1H = -B1g1H
         endif
         if ((s.gt.0d0).and.(t.gt.0d0).and.(u.gt.0d0)) then
            B1g1H = B1g1H + tree*pisq*2d0/9d0
         endif
c     Include O(as) term from Wilson coefficient.
         B1g1H = B1g1H + 11d0/3d0*tree
      end select

      B1g1H = B1g1H*born

      return
      end

************************************************************************

      real(8) function Bt1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      integer               :: imemode,ischeme
      real(8)               :: born,tree
      real(8)               :: s,t,u,s12,s13,s23
      real(8)               :: Li2s,Li2t,Li2u,mhsq,lnm,pisq
      complex(8)            :: lns,lnt,lnu,ln2t,ln2u
c     Externals.
      real(8), external     :: dot,A2g0H,B1g0H,ddilog
      complex(8), external  :: lnrat
c     Common blocks.
      common/memode/imemode

      pisq = pi**2

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))
      s    = s12
      t    = s23
      u    = s13
      mhsq = s+t+u
      lnm  = log(renscale2/mhsq)

      Li2t = ddilog(t/mhsq)
      Li2u = ddilog(u/mhsq)
      Li2s = ddilog((s-mhsq)/s)
      lns  = lnrat(s,mhsq)
      lnt  = lnrat(-t,mhsq)
      lnu  = lnrat(-u,mhsq)
      ln2t = lnrat((mhsq-t),mhsq)
      ln2u = lnrat((mhsq-u),mhsq)
      
      born = 1d0
      if (imemode.eq.1) born = A2g0H(mhsq)
      tree = B1g0H(p,i1,i3,i2)/born

      Bt1g1H = 0d0
      select case(ipole)
      case(-2)
         Bt1g1H = tree*(1d0)
      case(-1)
         Bt1g1H = tree*(3d0/2d0 - lns + lnm)
      case(0)
         Bt1g1H = tree*(
     .        + 4d0 - Li2t - Li2u
     .        - 3d0/2d0*(lns-lnm) + 1d0/2d0*(lns-lnm)**2
     .        + lnt*lnu - lnt*ln2t - lnu*ln2u - 4d0/3d0*pisq
     .        )
     .        - (t+u)/2d0/mhsq**2
      end select

      Bt1g1H = -Bt1g1H*born

      return
      end

************************************************************************

      real(8) function Bh1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,ipole
      real(8), intent(in)   :: p(1:4,4),renscale2
      real(8), parameter    :: pi=3.141592653589793238d0
      integer               :: imemode,ischeme
      real(8)               :: born,tree
      real(8)               :: s,t,u,s12,s13,s23
      real(8)               :: Li2s,Li2t,Li2u,mhsq,lnm,pisq
      complex(8)            :: lns,lnt,lnu,ln2t,ln2u
c     Externals.
      real(8), external     :: dot,A2g0H,B1g0H,ddilog
      complex(8), external  :: lnrat
c     Common blocks.
      common/memode/imemode

      pisq = pi**2

c     Invariants.
      s12 = 2d0*dot(p(1,i1),p(1,i2))
      s13 = 2d0*dot(p(1,i1),p(1,i3))
      s23 = 2d0*dot(p(1,i2),p(1,i3))
      s    = s12
      t    = s23
      u    = s13
      mhsq = s+t+u
      lnm  = log(renscale2/mhsq)

      Li2t = ddilog(t/mhsq)
      Li2u = ddilog(u/mhsq)
      Li2s = ddilog((s-mhsq)/s)
      lns  = lnrat(s,mhsq)
      lnt  = lnrat(-t,mhsq)
      lnu  = lnrat(-u,mhsq)
      ln2t = lnrat((mhsq-t),mhsq)
      ln2u = lnrat((mhsq-u),mhsq)
      
      born = 1d0
      if (imemode.eq.1) born = A2g0H(mhsq)
      tree = B1g0H(p,i1,i3,i2)/born

      Bh1g1H = 0d0
      select case(ipole)
      case(-2)
         Bh1g1H = 0d0
      case(-1)
         Bh1g1H = tree*(1d0/3d0)
      case(0)
         Bh1g1H = tree*(-10d0/9d0 + 2d0/3d0*lns - 2d0/3d0*lnm)
      end select

      Bh1g1H = Bh1g1H*born

      return
      end

c-----------------------------------------------------------------------
c     H -> 4j one-loop matrix elements.
c-----------------------------------------------------------------------
      
c     Full one-loop matrix element for
c     H -> g(i1) g(i2) g(i3) g(i4).
c     Adapted from MCFM/NNLOJET (src/process/H/libAHloop.f).
      real(8) function FullA4g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(1:4,5),renscale2
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external   :: A4g1H,Ah4g1H,A4g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Calculate prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*cn**3

      FullA4g1H = 1d0/12d0*fac*(
     .     + A4g1H(p,i1,i2,i3,i4,renscale2,ipole)
     .     + A4g1H(p,i1,i2,i4,i3,renscale2,ipole)
     .     + A4g1H(p,i1,i3,i2,i4,renscale2,ipole)
     .     + A4g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     + A4g1H(p,i1,i4,i2,i3,renscale2,ipole)
     .     + A4g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + nf/cn*(
     .     + Ah4g1H(p,i1,i2,i3,i4,renscale2,ipole)
     .     + Ah4g1H(p,i1,i2,i4,i3,renscale2,ipole)
     .     + Ah4g1H(p,i1,i3,i2,i4,renscale2,ipole)
     .     + Ah4g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     + Ah4g1H(p,i1,i4,i2,i3,renscale2,ipole)
     .     + Ah4g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     )
     .     )
    
c     Include O(as) Wilson coefficient.
      if (ipole.eq.0)then
         FullA4g1H = FullA4g1H
     .     + 1d0/12d0*(11d0/3d0)*fac*(
     .     + A4g0H(p,i1,i2,i3,i4)
     .     + A4g0H(p,i1,i2,i4,i3)
     .     + A4g0H(p,i1,i3,i2,i4)
     .     + A4g0H(p,i1,i3,i4,i2)
     .     + A4g0H(p,i1,i4,i2,i3)
     .     + A4g0H(p,i1,i4,i3,i2)
     .     )
      endif

      return
      end

************************************************************************

      real(8) function A4g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: i
      integer              :: perma(4),permb(4),permc(4),permd(4)
      integer              :: ieorder,ischeme,imemode
      real(8)              :: s1234,born,tree,ren,temp
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: zamp
c     Externals.
      real(8), external    :: A2g0H,A4g0H
      complex(8), external :: zA4g1Hppppcl,zA4g1Hmmmmcl,zA4g1Hpmmmcl
      complex(8), external :: zA4g1Hmmppcl,zA4g1Hmpmpcl,zA4g1Hmpppcl
      complex(8), external :: zA4g0Hmmmm,zA4g0Hpmmm
      complex(8), external :: zA4g0Hmmpp,zA4g0Hmpmp
      complex(8), external :: lnrat
c     Common blocks.
      common/order/ieorder
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = A4g0H(p,i1,i2,i3,i4)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perma(1) = i1
      perma(2) = i2
      perma(3) = i3
      perma(4) = i4

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

      zamp = 0d0
      temp = 0d0
      do i=1,16
         if (i.eq.1)then
            zamp = dble(
     .           zA4g1Hppppcl(perma(1),renscale2)
     .           *zA4g0Hmmmm(perma(1))
     .           )
         endif
         if (i.eq.2)then
            zamp = dble(
     .           zA4g1Hmmmmcl(perma(1),renscale2)
     .           *dconjg(zA4g0Hmmmm(perma(1)))
     .           )
         endif
         if (i.eq.3)then
            zamp = dble(
     .           zA4g1Hpmmmcl(perma(1),renscale2)
     .           *dconjg(zA4g0Hpmmm(perma(1)))
     .           )
         endif
         if (i.eq.4)then
            zamp = dble(
     .           zA4g1Hpmmmcl(permb(1),renscale2)
     .           *dconjg(zA4g0Hpmmm(permb(1)))
     .           )
         endif
         if (i.eq.5)then
            zamp = dble(
     .           zA4g1Hpmmmcl(permc(1),renscale2)
     .           *dconjg(zA4g0Hpmmm(permc(1)))
     .           )
         endif
         if (i.eq.6)then
            zamp = dble(
     .           zA4g1Hpmmmcl(permd(1),renscale2)
     .           *dconjg(zA4g0Hpmmm(permd(1)))
     .           )
         endif
         if (i.eq.7)then
            zamp = dble(
     .           zA4g1Hmpppcl(perma(1),renscale2)
     .           *zA4g0Hpmmm(perma(1))
     .           )
         endif
         if (i.eq.8)then
            zamp = dble(
     .           zA4g1Hmpppcl(permb(1),renscale2)
     .           *zA4g0Hpmmm(permb(1))
     .           )
         endif
         if (i.eq.9)then
            zamp = dble(
     .           zA4g1Hmpppcl(permc(1),renscale2)
     .           *zA4g0Hpmmm(permc(1))
     .           )
         endif
         if (i.eq.10)then
            zamp = dble(
     .           zA4g1Hmpppcl(permd(1),renscale2)
     .           *zA4g0Hpmmm(permd(1))
     .           )
         endif
         if (i.eq.11)then
            zamp = dble(
     .           zA4g1Hmmppcl(perma(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(perma(1)))
     .           )
         endif
         if (i.eq.12)then
            zamp = dble(
     .           zA4g1Hmmppcl(permd(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permd(1)))
     .           )
         endif
         if (i.eq.13)then
            zamp = dble(
     .           zA4g1Hmmppcl(permc(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permc(1)))
     .           )
         endif
         if (i.eq.14)then
            zamp = dble(
     .           zA4g1Hmmppcl(permb(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permb(1)))
     .           )
         endif
         if (i.eq.15)then
            zamp = dble(
     .           zA4g1Hmpmpcl(perma(1),renscale2)
     .           *dconjg(zA4g0Hmpmp(perma(1)))
     .           )
         endif
         if (i.eq.16)then
            zamp = dble(
     .           zA4g1Hmpmpcl(permb(1),renscale2)
     .           *dconjg(zA4g0Hmpmp(permb(1)))
     .           )
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ieorder.eq.0)then
         if (ischeme.eq.1) ren = 4d0*pi**2/12d0
      elseif (ieorder.eq.-1)then
         ren = -11d0/6d0*4d0
      endif

      A4g1H = temp + ren*tree
      A4g1H = A4g1H*born

      return
      end

************************************************************************

      real(8) function Ah4g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: i
      integer              :: perma(4),permb(4),permc(4),permd(4)
      integer              :: ieorder,imemode
      real(8)              :: s1234,born,tree,ren,temp
      real(8)              :: yB,cHGG
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: zamp
c     Externals.
      real(8), external    :: A2g0H,A4g0H
      complex(8), external :: zA4g1Hppppnf,zA4g1Hmmmmnf,zA4g1Hpmmmnf
      complex(8), external :: zA4g1Hmpppnf,zA4g1Hmmppnf,zA4g1Hmpmpnf
      complex(8), external :: zA4g0Hmmmm,zA4g0Hpmmm
      complex(8), external :: zA4g0Hmmpp,zA4g0Hmpmp
c     Common blocks.
      common/order/ieorder
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = A4g0H(p,i1,i2,i3,i4)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perma(1) = i1
      perma(2) = i2
      perma(3) = i3
      perma(4) = i4

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

      zamp = 0d0
      temp = 0d0
      do i=1,16
         if (i.eq.1)then
            zamp = dble(
     .           zA4g1Hppppnf(perma(1))
     .           *zA4g0Hmmmm(perma(1))
     .           )
         endif
         if (i.eq.2)then
            zamp = dble(
     .           zA4g1Hmmmmnf(perma(1))
     .           *dconjg(zA4g0Hmmmm(perma(1)))
     .           )
         endif
         if (i.eq.3)then
            zamp = dble(
     .           zA4g1Hpmmmnf(perma(1))
     .           *dconjg(zA4g0Hpmmm(perma(1)))
     .           )
         endif
         if (i.eq.4)then
            zamp = dble(
     .           zA4g1Hpmmmnf(permb(1))
     .           *dconjg(zA4g0Hpmmm(permb(1)))
     .           )
         endif
         if (i.eq.5)then
            zamp = dble(
     .           zA4g1Hpmmmnf(permc(1))
     .           *dconjg(zA4g0Hpmmm(permc(1)))
     .           )
         endif
         if (i.eq.6)then
            zamp = dble(
     .           zA4g1Hpmmmnf(permd(1))
     .           *dconjg(zA4g0Hpmmm(permd(1)))
     .           )
         endif
         if (i.eq.7)then
            zamp = dble(
     .           zA4g1Hmpppnf(perma(1))
     .           *zA4g0Hpmmm(perma(1)))
         endif
         if (i.eq.8)then
            zamp = dble(
     .           zA4g1Hmpppnf(permb(1))
     .           *zA4g0Hpmmm(permb(1)))
         endif
         if (i.eq.9)then
            zamp = dble(
     .           zA4g1Hmpppnf(permc(1))
     .           *zA4g0Hpmmm(permc(1)))
         endif
         if (i.eq.10)then
            zamp = dble(
     .           zA4g1Hmpppnf(permd(1))
     .           *zA4g0Hpmmm(permd(1)))
         endif
         if (i.eq.11)then
            zamp = dble(
     .           zA4g1Hmmppnf(perma(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(perma(1)))
     .           )
         endif
         if (i.eq.12)then
            zamp = dble(
     .           zA4g1Hmmppnf(permd(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permd(1)))
     .           )
         endif
         if (i.eq.13)then
            zamp = dble(
     .           zA4g1Hmmppnf(permc(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permc(1)))
     .           )
         endif
         if (i.eq.14)then
            zamp = dble(
     .           zA4g1Hmmppnf(permb(1),renscale2)
     .           *dconjg(zA4g0Hmmpp(permb(1)))
     .           )
         endif
         if (i.eq.15)then
            zamp = dble(
     .           zA4g1Hmpmpnf(perma(1),renscale2)
     .           *dconjg(zA4g0Hmpmp(perma(1)))
     .           )
         endif
         if (i.eq.16)then
            zamp = dble(
     .           zA4g1Hmpmpnf(permb(1),renscale2)
     .           *dconjg(zA4g0Hmpmp(permb(1)))
     .           )
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

      ren = 0d0
      if (ieorder.eq.-1)then
         ren = 4d0/3d0
      endif

      Ah4g1H = temp + ren*tree
      Ah4g1H = Ah4g1H*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g g g one-loop amplitudes.

      complex(8) function zA4g1Hmmmmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: zA4g1HmmmmCC,zA4g1HmmmmNCCcl

      zA4g1Hmmmmcl =
     .     + zA4g1HmmmmCC(perm(1),renscale2)
     .     + zA4g1HmmmmNCCcl(perm(1))

      return
      end

************************************************************************

      complex(8) function zA4g1Hmmmmnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      complex(8), external :: zA4g1HmmmmNCCnf

      zA4g1Hmmmmnf = zA4g1HmmmmNCCnf(perm(1))

      return
      end

************************************************************************

      complex(8) function zA4g1HmmmmCC(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4,i,ii(7)
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: zA4g0Hmmmm
c     Common blocks.
      common/kin5/s,zA,zB
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

c     Set up 's-comma' products.
      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23 !t123
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34 !t234
      sc(3,1)=s34+s31+s41 !t341
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12 !t412
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      zA4g1HmmmmCC = (0d0,0d0)
      do i=1,4
c     NOTE: Arguments of F41m , F42m have been changed to be consistent
c     with later papers: F41m(s,t;Psq) -> F41m(Psq;s,t)
c     F42me(s,t;Psq,Qsq) -> F42me(Psq,Qsq;s,t).

      zA4g1HmmmmCC=zA4g1HmmmmCC
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2)),
     .              sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        -0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

      zA4g1HmmmmCC = zA4g0Hmmmm(perm(1))*zA4g1HmmmmCC

      return
      end

************************************************************************

      complex(8) function zA4g1HmmmmNCCcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4),permc(4),permd(4)
      integer              :: i1,i2,i3,i4
c     Externals.
      complex(8), external :: zA4g1Hmmmmsub

      i1=perm(1)
      i2=perm(2)
      i3=perm(3)
      i4=perm(4)

      perma(1)=i1
      perma(2)=i2
      perma(3)=i3
      perma(4)=i4

      permb(1)=i2
      permb(2)=i3
      permb(3)=i4
      permb(4)=i1

      permc(1)=i3
      permc(2)=i4
      permc(3)=i1
      permc(4)=i2

      permd(1)=i4
      permd(2)=i1
      permd(3)=i2
      permd(4)=i3

      zA4g1HmmmmNCCcl = 1d0/3d0*(
     .     + zA4g1Hmmmmsub(perma(1))
     .     + zA4g1Hmmmmsub(permb(1))
     .     + zA4g1Hmmmmsub(permc(1))
     .     + zA4g1Hmmmmsub(permd(1))
     .     )

      return
      end

************************************************************************

      complex(8) function zA4g1HmmmmNCCnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4),permc(4),permd(4)
      integer              :: i1,i2,i3,i4
c     Externals.
      complex(8), external :: zA4g1Hmmmmsub

      i1=perm(1)
      i2=perm(2)
      i3=perm(3)
      i4=perm(4)

      perma(1)=i1
      perma(2)=i2
      perma(3)=i3
      perma(4)=i4

      permb(1)=i2
      permb(2)=i3
      permb(3)=i4
      permb(4)=i1

      permc(1)=i3
      permc(2)=i4
      permc(3)=i1
      permc(4)=i2

      permd(1)=i4
      permd(2)=i1
      permd(3)=i2
      permd(4)=i3

      zA4g1HmmmmNCCnf = -1d0/3d0*(
     .     + zA4g1Hmmmmsub(perma(1))
     .     + zA4g1Hmmmmsub(permb(1))
     .     + zA4g1Hmmmmsub(permc(1))
     .     + zA4g1Hmmmmsub(permd(1))
     .     )

      return
      end

************************************************************************

      complex(8) function zA4g1Hmmmmsub(perm)
      implicit none
      integer, intent(in) :: perm(4)
      integer             :: j1,j2,j3,j4
      integer             :: ieorder
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s21,s31,s41,s32,s42,s43
      real(8)             :: t123,t234
      complex(8)          :: za12,za13,za14,za23,za24,za34
      complex(8)          :: za21,za31,za41,za32,za42,za43
      complex(8)          :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)          :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)          :: z2ab4132
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Externals
      complex(8), external :: zab2
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

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

      t123 = s12+s23+s31
      t234 = s23+s34+s24

      z2ab4132 = zab2(j4,j1,j3,j2)

      if (ieorder.eq.-2)then
         zA4g1Hmmmmsub = 0d0
      elseif (ieorder.eq.-1)then
         zA4g1Hmmmmsub = 0d0
      elseif (ieorder.eq.0)then
         zA4g1Hmmmmsub = -s13*z2ab4132**2/(t123*zb12**2*zb23**2)
     .        + (za34/zb12)**2
     .        + 2d0*za34*za41/(zb12*zb23)
     .        + (s12*s34+t123*t234-s12**2)/(2d0*zb12*zb23*zb34*zb41)
      endif

      return
      end

************************************************************************

      complex(8) function zA4g1Hppppcl(perm,renscale2)  
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: zA4g1HppppCC,zA4g1HppppNCCcl

      zA4g1Hppppcl =
     .     + zA4g1HppppCC(perm(1),renscale2)
     .     + zA4g1HppppNCCcl(perm(1))

      return
      end

************************************************************************

      complex(8) function zA4g1Hppppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      complex(8), external :: zA4g1HppppNCCnf

      zA4g1Hppppnf = zA4g1HppppNCCnf(perm(1))

      return
      end

************************************************************************

      complex(8) function zA4g1HppppCC(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8)              :: renscale2
      integer              :: j1,j2,j3,j4,i,ii(7)
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: zA4g0Hmmmm
c     Common blocks.
      common/kin5/s,zA,zB
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

c     Set up 's-comma' products.
      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23 !t123
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,2)=0d0
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34 !t234
      sc(3,3)=0d0
      sc(3,1)=s34+s31+s41 !t341
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12 !t412
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      zA4g1HppppCC = (0d0,0d0)
      do i=1,4
c     NOTE: Arguments of F41m , F42m have been changed to be consistent
c     with later papers: F41m(s,t;Psq) -> F41m(Psq;s,t)
c     F42me(s,t;Psq,Qsq) -> F42me(Psq,Qsq;s,t).
         zA4g1HppppCC = zA4g1HppppCC
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2)),
     .        sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

      zA4g1HppppCC = conjg(zA4g0Hmmmm(perm(1)))*zA4g1HppppCC

      return
      end

************************************************************************

      complex(8) function zA4g1HppppNCCcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: i1,i2,i3,i4
      integer              :: perma(4),permb(4),permc(4),permd(4)
      complex(8), external :: zA4g1Hppppsub

      i1=perm(1)
      i2=perm(2)
      i3=perm(3)
      i4=perm(4)

      perma(1)=i1
      perma(2)=i2
      perma(3)=i3
      perma(4)=i4

      permb(1)=i2
      permb(2)=i3
      permb(3)=i4
      permb(4)=i1

      permc(1)=i3
      permc(2)=i4
      permc(3)=i1
      permc(4)=i2

      permd(1)=i4
      permd(2)=i1
      permd(3)=i2
      permd(4)=i3

      zA4g1HppppNCCcl = 1d0/3d0*(
     .     + zA4g1Hppppsub(perma(1))
     .     + zA4g1Hppppsub(permb(1))
     .     + zA4g1Hppppsub(permc(1))
     .     + zA4g1Hppppsub(permd(1))
     .     )

      return
      end

************************************************************************

      complex(8) function zA4g1HppppNCCnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4),permc(4),permd(4)
      integer              :: i1,i2,i3,i4
      complex(8), external :: zA4g1Hppppsub

      i1=perm(1)
      i2=perm(2)
      i3=perm(3)
      i4=perm(4)

      perma(1)=i1
      perma(2)=i2
      perma(3)=i3
      perma(4)=i4

      permb(1)=i2
      permb(2)=i3
      permb(3)=i4
      permb(4)=i1

      permc(1)=i3
      permc(2)=i4
      permc(3)=i1
      permc(4)=i2

      permd(1)=i4
      permd(2)=i1
      permd(3)=i2
      permd(4)=i3

      zA4g1HppppNCCnf = -1d0/3d0*(
     .     + zA4g1Hppppsub(perma(1))
     .     + zA4g1Hppppsub(permb(1))
     .     + zA4g1Hppppsub(permc(1))
     .     + zA4g1Hppppsub(permd(1))
     .     )

      return
      end

************************************************************************

      complex(8) function zA4g1Hppppsub(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: t123,t234
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ba4132
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      complex(8), external :: zba2
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

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

      t123 = s12+s23+s31
      t234 = s23+s34+s24

      z2ba4132 = zba2(j4,j1,j3,j2)

      if (ieorder.eq.-2)then
         zA4g1Hppppsub = 0d0
      elseif (ieorder.eq.-1)then
         zA4g1Hppppsub = 0d0
      elseif (ieorder.eq.0)then
         zA4g1Hppppsub = -s13*z2ba4132**2/(t123*za12**2*za23**2)
     .        + (zb34/za12)**2
     .        + 2d0*zb34*zb41/(za12*za23)
     .        + (s12*s34+t123*t234-s12**2)/(2d0*za12*za23*za34*za41)
      endif

      return
      end

************************************************************************

c     Results taken from an early draft of arXiv:0909.4475 [hep-ph].
      complex(8) function zA4g1Hpmmmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      complex(8)           :: V4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      complex(8), external :: FR4pmmmcl,FR4pmmmnf,F31m
      complex(8), external :: zA4g0Hpmmm
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      V4 = -zA4g0Hpmmm(perm(1))*(
     .     + F31m(s12,renscale2)
     .     + F31m(s23,renscale2)
     .     + F31m(s34,renscale2)
     .     + F31m(s41,renscale2)
     .     )

      zA4g1Hpmmmcl = V4-FR4pmmmcl(perm(1))

      return
      end

************************************************************************

c     Results taken from an early draft of arXiv:0909.4475 [hep-ph].
      complex(8) function zA4g1Hpmmmnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      complex(8), external :: FR4pmmmnf

      zA4g1Hpmmmnf = -FR4pmmmnf(perm(1))

      return
      end

************************************************************************

      complex(8) function FR4pmmmcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
c     Externals.
      complex(8), external :: FR4unsymcl,FR4unsymnf
c     Common blocks.
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j1
      permb(2)=j4
      permb(3)=j3
      permb(4)=j2

      if (ieorder.eq.-2)then
         FR4pmmmcl = 0d0
      elseif (ieorder.eq.-1)then
         FR4pmmmcl = 0d0
      elseif (ieorder.eq.0)then
         FR4pmmmcl =
     .        + FR4unsymcl(permb(1))
     .        + FR4unsymcl(perma(1))
      endif

      return
      end

************************************************************************

      complex(8) function FR4pmmmnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      complex(8), external :: FR4unsymnf
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j1
      permb(2)=j4
      permb(3)=j3
      permb(4)=j2

      if (ieorder.eq.-2)then
         FR4pmmmnf = 0d0
      elseif (ieorder.eq.-1)then
         FR4pmmmnf = 0d0
      elseif (ieorder.eq.0)then
         FR4pmmmnf =
     .        + FR4unsymnf(permb(1))
     .        + FR4unsymnf(perma(1))
      endif

      return
      end

************************************************************************

c     Use the result of zA4g1Hpmmm but only take complex conjugation
c     of za and zb. Leave other complex number invariant to get -+++
c     helicity configurations.
      complex(8) function zA4g1Hmpppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: V4
c     Externals.
      complex(8), external :: FR4mpppcl,FR4mpppnf,F31m
      complex(8), external :: zA4g0Hpmmm
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      V4 = -conjg(zA4g0Hpmmm(perm(1)))*(
     .     + F31m(s12,renscale2)
     .     + F31m(s23,renscale2)
     .     + F31m(s34,renscale2)
     .     + F31m(s41,renscale2)
     .     )

      zA4g1Hmpppcl = V4-FR4mpppcl(perm(1))

      return
      end

************************************************************************

c     Use the result of zA4g1Hpmmm but only take complex conjugation
c     of za and zb. Leave other complex number invariant to get -+++
c     helicity configurations.
      complex(8) function zA4g1Hmpppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      complex(8), external :: FR4mpppnf

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      zA4g1Hmpppnf = -FR4mpppnf(perm(1))

      return
      end

************************************************************************

c     Use the result of FR4pmmm but only take complex conjugation
c     of za and zb. Leave other complex number invariant to get -+++
c     helicity configurations.
      complex(8) function FR4mpppcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
c     Externals.
      complex(8), external :: FR4unsymmodcl
c     Common blocks.
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j1
      permb(2)=j4
      permb(3)=j3
      permb(4)=j2

      if (ieorder.eq.-2)then
         FR4mpppcl = 0d0
      elseif (ieorder.eq.-1)then
         FR4mpppcl = 0d0
      elseif (ieorder.eq.0)then
         FR4mpppcl =
     .        + FR4unsymmodcl(perma(1))
     .        + FR4unsymmodcl(permb(1))
      endif

      return
      end

************************************************************************

c     Use the result of FR4pmmm but only take complex conjugation
c     of za and zb. Leave other complex number invariant to get -+++
c     helicity configurations.
      complex(8) function FR4mpppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
c     Externals.
      complex(8), external :: FR4unsymmodnf
c     Common blocks.
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j1
      permb(2)=j4
      permb(3)=j3
      permb(4)=j2

      if (ieorder.eq.-2)then
         FR4mpppnf = 0d0
      elseif (ieorder.eq.-1)then
         FR4mpppnf = 0d0
      elseif (ieorder.eq.0)then
         FR4mpppnf =
     .        + FR4unsymmodnf(perma(1))
     .        + FR4unsymmodnf(permb(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA4g1Hmmppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      complex(8), external :: zAphi4g1mmppcl,zAcphi4g1mmppcl

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j3
      permb(2)=j4
      permb(3)=j1
      permb(4)=j2

c     0704.3914v3 Eqs. (2.4) and (2.6)
c     Note: c.c. is equivalent to interchanging za and zb.
      zA4g1Hmmppcl =
     .     + zAphi4g1mmppcl(PERMa(1),renscale2)
     .     + zAcphi4g1mmppcl(PERMb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zA4g1Hmmppnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      complex(8), external :: zAphi4g1mmppnf,zAcphi4g1mmppnf

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j3
      permb(2)=j4
      permb(3)=j1
      permb(4)=j2

c     0704.3914v3 Eqs. (2.4) and (2.6)
c     Note: c.c. is equivalent to interchanging za and zb.
      zA4g1Hmmppnf =
     .     + zAphi4g1mmppnf(perma(1),renscale2)
     .     + zAcphi4g1mmppnf(permb(1),renscale2)

      return
      end

************************************************************************

c     Results taken from arXiv:0704.3914 [hep-ph] with the sign of all
c     terms proportional to Np or b0 reversed.
      complex(8) function zAphi4g1mmppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mmpphatcl,Rhat4mmppcl

c     arXiv:0704.3914v3, Eq.(5.13).
c     Version using "hatting" procedure.
      zAphi4g1mmppcl =
     .     + C4mmpphatcl(perm(1),renscale2)
     .     + Rhat4mmppcl(perm(1))

      return
      end

************************************************************************

c     Results taken from arXiv:0704.3914 [hep-ph] with the sign of all
c     terms proportional to Np or b0 reversed.
      complex(8) function zAphi4g1mmppnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: Rhat4mmppnf,Rhat4mmppcl,C4mmpphatnf

c     arXiv:0704.3914v3, Eq.(5.13).
c     Version using "hatting" procedure.
      zAphi4g1mmppnf =
     .     + C4mmpphatnf(perm(1),renscale2)
     .     + Rhat4mmppnf(perm(1))

      return
      end

************************************************************************

c     arXiv:0704.3914v3, Eq.(5.12) (factor of 16 pi^2 removed).
      complex(8) function Rhat4mmppcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zAphi4g0mmpp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j3
      permb(2)=j4
      permb(3)=j1
      permb(4)=j2

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

c     Note: implicit use of
c     A0(A,...)=A0phigggg(...)-A0phiggggdagger(...)
c     and the fact that A0phiggggdagger=(c.c. of A0phigggg).
      if (ieorder.eq.-2)then
         Rhat4mmppcl = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mmppcl = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mmppcl = 2d0*(
     .        zAphi4g0mmpp(perma(1))-conjg(zAphi4g0mmpp(permb(1)))
     .        )
     .        + 1d0/3d0*zb43/za34*(
     .        - za23*z2ab1243**2/(za34*zb43*zb32*s3s234)
     .        + za41*z2ab3123/(za34*zb12*zb32)
     .        - za14*z2ab2134**2/(za34*zb43*zb41*s3s341)
     .        + za32*z2ab4124/(za34*zb12*zb41)
     .        + za12**2/(za34*zb43)
     .        - za12/zb12
     .        - za12*z2ab2134/(2d0*zb41*s3s341)
     .        + za12*z2ab1243/(2d0*zb32*s3s234)
     .        + za12**2/(2d0*s23)
     .        + za12**2/(2d0*s41)
     .        )
      endif

c     MODIFIED: overall sign of Rhat.
      Rhat4mmppcl = Rhat4mmppcl

      return
      end

************************************************************************

c     arXiv:0704.3914v3, Eq.(5.12) (factor of 16 pi^2 removed).
      complex(8) function Rhat4mmppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

c     Note: implicit use of
c     A0(A,...)=A0phigggg(...)-A0phiggggdagger(...)
c     and the fact that A0phiggggdagger=(c.c. of A0phigggg).
      if (ieorder.eq.-2)then
         Rhat4mmppnf = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mmppnf = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mmppnf =
     .        - 1d0/3d0*zb43/za34*(
     .        - za23*z2ab1243**2/(za34*zb43*zb32*s3s234)
     .        + za41*z2ab3123/(za34*zb12*zb32)
     .        - za14*z2ab2134**2/(za34*zb43*zb41*s3s341)
     .        + za32*z2ab4124/(za34*zb12*zb41)
     .        + za12**2/(za34*zb43)
     .        - za12/zb12
     .        - za12*z2ab2134/(2d0*zb41*s3s341)
     .        + za12*z2ab1243/(2d0*zb32*s3s234)
     .        + za12**2/(2d0*s23)+za12**2/(2d0*s41)
     .        )
      endif

c     MODIFIED: overall sign of Rhat.
      Rhat4mmppnf = Rhat4mmppnf

      return
      end

************************************************************************

c     This is the hatted second version of the function presented in
c     arXiv:0704.3914v3, Eq.(3.24) (factor of C_\Gamma removed).
      complex(8) function C4mmpphatcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ba3412
      complex(8)           :: sum
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: BGRL3hat,BGRL1
      complex(8), external :: zAphi4g0mmpp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

c     set up 's-comma' products
      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)

      z2ba3412 = zba2(j3,j4,j1,j2)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

      sum=(0d0,0d0)
      do i=1,4
c     note: corrected third argument of F42me from
c     s_(i,j+1) to s_(i,j-1) [with j=i+3 here]
         sum = sum
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2))
     .        ,sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

c     implementation of Eq. (3.24)

      if (ieorder.eq.-2)then
         C4mmpphatcl = zAphi4g0mmpp(perm(1))*sum
      elseif (ieorder.eq.-1)then
         C4mmpphatcl = zAphi4g0mmpp(perm(1))*sum
      elseif (ieorder.eq.0)then
         C4mmpphatcl = zAphi4g0mmpp(perm(1))*sum
     .        - (
     .        + 1d0/(za23*za34*za41)*(
     .        1d0/3d0*za14*zb43*za32*za13*z2ba3412*(
     .        za13*z2ba3412-za14*zb43*za32
     .        )*BGRL3hat(sc(3,1),sc(4,1))
     .        + 11d0/3d0*za12**2*za14*zb43*za32*BGRL1(sc(3,1),sc(4,1))
     .        + 1d0/3d0*za14*zb43*za32*z2ab1234*za42*(
     .        z2ab1234*za42-za14*zb43*za32
     .        )*BGRL3hat(sc(2,4),sc(2,3))
     .        + 11d0/3d0*za12**2*za14*zb43*za32*BGRL1(sc(2,4),sc(2,3))
     .        )
     .        )
      endif

      return
      end

************************************************************************

c     This is the hatted second version of the function presented in
c     arXiv:0704.3914v3, Eq.(3.24) (factor of C_\Gamma removed).
      complex(8) function C4mmpphatnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: Np,bb0,sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ba3412
      complex(8)           :: sum
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: BGRL3hat,BGRL1
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

c     Set up 's-comma' products.
      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)

      z2ba3412=zba2(j3,j4,j1,j2)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

      Np  = -2d0
      bb0 = -2d0/3d0

      sum = (0d0,0d0)
      do i=1,4
c     Note: corrected third argument of F42me from
c     s_(i,j+1) to s_(i,j-1) [with j=i+3 here].
         sum = sum
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2)),
     .        sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

c     implementation of Eq. (3.24)

      if (ieorder.eq.-2)then
         C4mmpphatnf = 0d0
      elseif (ieorder.eq.-1)then
         C4mmpphatnf = 0d0
      elseif (ieorder.eq.0)then
         C4mmpphatnf = -(
     .        +1d0/(za23*za34*za41)*(
     .        Np/6d0*za14*zb43*za32*za13*z2ba3412*(
     .        za13*z2ba3412-za14*zb43*za32
     .        )*BGRL3hat(sc(3,1),sc(4,1))
     .        + bb0*za12**2*za14*zb43*za32*BGRL1(sc(3,1),sc(4,1))
     .        + Np/6d0*za14*zb43*za32*z2ab1234*za42*(
     .        z2ab1234*za42-za14*zb43*za32
     .        )*BGRL3hat(sc(2,4),sc(2,3))
     .        + bb0*za12**2*za14*zb43*za32*BGRL1(sc(2,4),sc(2,3))
     .        )
     .        )
      endif

      return
      end

************************************************************************

      complex(8) function zAcphi4g1mmppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mmpphatmodcl,Rhat4mmppmodcl

      zAcphi4g1mmppcl =
     .     + C4mmpphatmodcl(perm(1),renscale2)
     .     + Rhat4mmppmodcl(perm(1))

      return
      end

************************************************************************

      complex(8) function zAcphi4g1mmppnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mmpphatmodnf,Rhat4mmppmodnf

      zAcphi4g1mmppnf =
     .     + C4mmpphatmodnf(perm(1),renscale2)
     .     + Rhat4mmppmodnf(perm(1))

      return
      end

************************************************************************

      complex(8) function C4mmpphatmodcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba1234,z2ba3412
      complex(8)           :: sum
c     Externals.
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: BGRL3hat,BGRL1
      complex(8), external :: zab2,zba2
      complex(8), external :: zAphi4g0mmpp
      real(8), external    :: ss3
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

      sum = (0d0,0d0)
      do i=1,4
         sum = sum
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2))
     .        ,sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

      if (ieorder.eq.-2)then
         C4mmpphatmodcl = conjg(zAphi4g0mmpp(perm(1)))*sum
      elseif (ieorder.eq.-1)then
         C4mmpphatmodcl = conjg(zAphi4g0mmpp(perm(1)))*sum
      elseif (ieorder.eq.0)then
         C4mmpphatmodcl = conjg(zAphi4g0mmpp(perm(1)))*sum
     .        - (
     .        + 1d0/(zb23*zb34*zb41)*(
     .        1d0/3d0*zb14*za43*zb32*zb13*z2ab3412*(
     .        zb13*z2ab3412-zb14*za43*zb32
     .        )*BGRL3hat(sc(3,1),sc(4,1))
     .        + 11d0/3d0*zb12**2*zb14*za43*zb32*BGRL1(sc(3,1),sc(4,1))
     .        + 1d0/3d0*zb14*za43*zb32*z2ba1234*zb42*(
     .        z2ba1234*zb42-zb14*za43*zb32
     .        )*BGRL3hat(sc(2,4),sc(2,3))
     .        + 11d0/3d0*zb12**2*zb14*za43*zb32*BGRL1(sc(2,4),sc(2,3))
     .        )
     .        )
      endif

      return
      end

************************************************************************

      complex(8) function C4mmpphatmodnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234
      complex(8)           :: sum
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
      complex(8), external :: F31m,F42me,F41m
      complex(8), external :: BGRL3hat,BGRL1
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)

      s3s234  = ss3(j2,j3,j4)
      s3s341  = ss3(j3,j4,j1)

      sum=(0d0,0d0)
      do i=1,4
         sum = sum
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2)),
     .        sc(ii(i),ii(i+2)),sc(ii(i+1),ii(i+3)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
      enddo

      if (ieorder.eq.-2)then
         C4mmpphatmodnf = 0d0
      elseif (ieorder.eq.-1)then
         C4mmpphatmodnf = 0d0
      elseif (ieorder.eq.0)then
         C4mmpphatmodnf = -(
     .        + 1d0/(zb23*zb34*zb41)*(
     .        - 1d0/3d0*zb14*za43*zb32*zb13*z2ab3412*(
     .        zb13*z2ab3412-zb14*za43*zb32
     .        )*BGRL3hat(sc(3,1),sc(4,1))
     .        - 2d0/3d0*zb12**2*zb14*za43*zb32*BGRL1(sc(3,1),sc(4,1))
     .        - 1d0/3d0*zb14*za43*zb32*z2ba1234*zb42*(
     .        z2ba1234*zb42-zb14*za43*zb32
     .        )*BGRL3hat(sc(2,4),sc(2,3))
     .        - 2d0/3d0*zb12**2*zb14*za43*zb32*BGRL1(sc(2,4),sc(2,3))
     .        )
     .        )
      endif

      return
      end

************************************************************************

      complex(8) function Rhat4mmppmodcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
      complex(8), external :: zAphi4g0mmpp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      perma(1)=j1
      perma(2)=j2
      perma(3)=j3
      perma(4)=j4

      permb(1)=j3
      permb(2)=j4
      permb(3)=j1
      permb(4)=j2

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)

      if (ieorder.eq.-2)then
         Rhat4mmppmodcl = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mmppmodcl = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mmppmodcl = 2d0*(
     .        conjg(zAphi4g0mmpp(perma(1)))-zAphi4g0mmpp(permb(1))
     .        )
     .        + 1d0/3d0*za43/zb34*(
     .        - zb23*z2ba1243**2/(zb34*za43*za32*s3s234)
     .        + zb41*z2ba3123/(zb34*za12*za32)
     .        - zb14*z2ba2134**2/(zb34*za43*za41*s3s341)
     .        + zb32*z2ba4124/(zb34*za12*za41)
     .        + zb12**2/(zb34*za43)
     .        - zb12/za12
     .        - zb12*z2ba2134/(2d0*za41*s3s341)
     .        + zb12*z2ba1243/(2d0*za32*s3s234)
     .        + zb12**2/(2d0*s23)+zb12**2/(2d0*s41)
     .        )
      endif

      Rhat4mmppmodcl = -Rhat4mmppmodcl

      return
      end

************************************************************************

      complex(8) function Rhat4mmppmodnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)

      if (ieorder.eq.-2)then
         Rhat4mmppmodnf = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mmppmodnf = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mmppmodnf =
     .        - 1d0/3d0*za43/zb34*(
     .        - zb23*z2ba1243**2/(zb34*za43*za32*s3s234)
     .        + zb41*z2ba3123/(zb34*za12*za32)
     .        - zb14*z2ba2134**2/(zb34*za43*za41*s3s341)
     .        + zb32*z2ba4124/(zb34*za12*za41)
     .        + zb12**2/(zb34*za43)
     .        - zb12/za12
     .        - zb12*z2ba2134/(2d0*za41*s3s341)
     .        + zb12*z2ba1243/(2d0*za32*s3s234)
     .        + zb12**2/(2d0*s23)+zb12**2/(2d0*s41)
     .        )
      endif

      Rhat4mmppmodnf = -Rhat4mmppmodnf

      return
      end

************************************************************************

      complex(8) function zA4g1Hmpmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      complex(8), external :: zAphi4g1mpmpcl,zAcphi4g1mpmpcl

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

c     0704.3914v3 Eqs. (2.4) and (2.6)
c     Note: c.c. is equivalent to interchanging za and zb.
      zA4g1Hmpmpcl =
     .     + zAphi4g1mpmpcl(PERMa(1),renscale2)
     .     + zAcphi4g1mpmpcl(PERMb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zA4g1Hmpmpnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      complex(8), external :: zAphi4g1mpmpnf,zAcphi4g1mpmpnf

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

c     0704.3914v3 Eqs. (2.4) and (2.6)
c     Note: c.c. is equivalent to interchanging za and zb.
      zA4g1Hmpmpnf =
     .     + zAphi4g1mpmpnf(perma(1))
     .     + zAcphi4g1mpmpnf(permb(1),renscale2)

      return
      end

************************************************************************

c     Results taken from arXiv:0804.4149 [hep-ph] with the sign of
c     rational terms reversed.
c     Note that a factor of c_\Gamma is missing in Eq. (5.1).
      complex(8) function zAphi4g1mpmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mpmpcl,Rhat4mpmpcl,CR4mpmpcl

c     Combined CR4mpmpcl with C4mpmpcl function by replacing the
c     L2 and L3 functions in C4mpmpcl by L2hat and L3hat.
c     This could improve the numerical stability.
      zAphi4g1mpmpcl =
     .     + C4mpmpcl(perm(1),renscale2)
c     .     + CR4mpmpcl(perm(1))
     .     + Rhat4mpmpcl(perm(1))

      return
      end

************************************************************************

c     Results taken from arXiv:0804.4149 [hep-ph] with the sign of
c     rational terms reversed.
c     Note that a factor of c_\Gamma is missing in Eq. (5.1).
      complex(8) function zAphi4g1mpmpnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      complex(8), external :: C4mpmpnf,Rhat4mpmpnf,CR4mpmpnf

c     Combined CR4mpmpnf with C4mpmpnf function by replacing the
c     L2 and L3 functions in C4mpmpnf by L2hat and L3hat.
c     This could improve the numerical stability.
      zAphi4g1mpmpnf =
     .     + C4mpmpnf(perm(1))
c     .     + CR4mpmpnf(perm(1))
     .     + Rhat4mpmpnf(perm(1))

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.1) (factor of C_\Gamma removed).
      complex(8) function C4mpmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: sum
c     Externals.
      complex(8), external :: C4mpmpsubcl,F31m,F42me,F41m,zAphi4g0mpmp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

c     Set up 's-comma' products.
      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      sum=(0d0,0d0)
      do i=1,4
         sum = sum
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2)),
     .        sc(ii(i+1),ii(i+3)),sc(ii(i),ii(i+2)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
      enddo

      if (ieorder.eq.-2)then
         C4mpmpcl = sum*zAphi4g0mpmp(PERM(1))
      elseif (ieorder.eq.-1)then
         C4mpmpcl = sum*zAphi4g0mpmp(PERM(1))
      elseif (ieorder.eq.0)then
         sum = sum
     .        + C4mpmpsubcl(j1,j2,j3,j4)
     .        + C4mpmpsubcl(j1,j4,j3,j2)
     .        + C4mpmpsubcl(j3,j2,j1,j4)
     .        + C4mpmpsubcl(j3,j4,j1,j2)
         C4mpmpcl = sum*zAphi4g0mpmp(PERM(1))
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.1) (factor of C_\Gamma removed).
      complex(8) function C4mpmpnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      complex(8)           :: sum
c     Externals.
      complex(8), external :: C4mpmpsubnf
      complex(8), external :: zAphi4g0mpmp
c     Common blocks.
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      if (ieorder.eq.-2)then
         C4mpmpnf = 0d0
      elseif (ieorder.eq.-1)then
         C4mpmpnf = 0d0
      elseif (ieorder.eq.0)then
         sum = (0d0,0d0)
         sum =
     .        + C4mpmpsubnf(j1,j2,j3,j4)
     .        + C4mpmpsubnf(j1,j4,j3,j2)
     .        + C4mpmpsubnf(j3,j2,j1,j4)
     .        + C4mpmpsubnf(j3,j4,j1,j2)
         C4mpmpnf = sum*zAphi4g0mpmp(perm(1))
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.1) (factor of C_\Gamma removed).
c     C.f. arXiv:0804.4149v3 Eq.(3.38).
      complex(8) function C4mpmpsubcl(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s234
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: trm,trm3241,trm3421
c     Externals.
      complex(8), external :: BGRL3hat,BGRL2hat,BGRL1,F41mF
c     Common blocks.
      common/kin5/s,zA,zB

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

      s234    = s23+s24+s34
      trm3241 = za32*zb24*za41*zb13
      trm3421 = za34*zb42*za21*zb13

c     MODIFIED: added an overall factor of (-1) here.
      C4mpmpsubcl = 
     .     + 4d0*(
     .     trm3241*trm3421/(2d0*(s24*s13)**2)*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/(s24*s13**2)*BGRL1(s23,s234)
     .     )
     .     + 2d0*(
     .     - 0.5d0*(trm3241*trm3421/(s24*s13)**2)**2*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/s13**4*(
     .     + trm3241**2/(3d0*s24)*BGRL3hat(s23,s234)
     .     + trm3421*trm3241/(2d0*s24**2)*BGRL2hat(s23,s234)
     .     - trm3421*trm3241/(s24**3)*BGRL1(s23,s234)
     .     )
     .     )

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.1) (factor of C_\Gamma removed).
c     c.f. arXiv:0804.4149v3 Eq.(3.38).
      complex(8) function C4mpmpsubnf(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s234
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: trm,trm3241,trm3421
c     Externals.
      complex(8), external :: BGRL3hat,BGRL2hat,BGRL1,F41mF
c     Common blocks.
      common/kin5/s,zA,zB

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

      s234    = s23+s24+s34
      trm3241 = za32*zb24*za41*zb13
      trm3421 = za34*zb42*za21*zb13

c     MODIFIED: added an overall factor of (-1) here.
      C4mpmpsubnf =
     .     -1d0*(
     .     trm3241*trm3421/(2d0*(s24*s13)**2)*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/(s24*s13**2)*BGRL1(s23,s234)
     .     )
     .     - 2d0*(
     .     - 0.5d0*(trm3241*trm3421/(s24*s13)**2)**2*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/s13**4*(
     .     + trm3241**2/(3d0*s24)*BGRL3hat(s23,s234)
     .     + trm3421*trm3241/(2d0*s24**2)*BGRL2hat(s23,s234)
     .     - trm3421*trm3241/(s24**3)*BGRL1(s23,s234)
     .     )
     .     )

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.17) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function Rhat4mpmpcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: im
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2
      complex(8), external :: zAphi4g0mpmp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      im = (0d0,1d0)

c     Note: implicit use of A0(A,...)=-i*[A0phi(...)-A0phidagger(...)]
c     and the fact that A0phidagger=(c.c. of A0phi)
      if (ieorder.eq.-2)then
         Rhat4mpmpcl = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mpmpcl = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mpmpcl =
     .        -2d0*(-im)*(
     .        zAphi4g0mpmp(perma(1))-conjg(zAphi4g0mpmp(permb(1)))
     .        )
     .        + 1d0/6d0*zb24**4/(zb12*zb23*zb34*zb41)
     .        *(
     .        - s23*s34/(s24*s3s412)
     .        + 3d0*s23*s34/s24**2
     .        - s12*s41/(s24*s3s234)
     .        + 3d0*s12*s41/s24**2
     .        )
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.17) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function Rhat4mpmpnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: im
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2 
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      im = (0d0,1d0)

c     Note: implicit use of A0(A,...)=-i*[A0phi(...)-A0phidagger(...)]
c     and the fact that A0phidagger=(c.c. of A0phi).
      if (ieorder.eq.-2)then
         Rhat4mpmpnf = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mpmpnf = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mpmpnf =
     .        -1d0/6d0*zb24**4/(zb12*zb23*zb34*zb41)*(
     .        - s23*s34/(s24*s3s412)
     .        + 3d0*s23*s34/s24**2
     .        - s12*s41/(s24*s3s234)
     .        + 3d0*s12*s41/s24**2
     .        )
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.2) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function CR4mpmpcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      complex(8), external :: CR4mpmpsubcl
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      if (ieorder.eq.-2)then
         CR4mpmpcl = 0d0
      elseif (ieorder.eq.-1)then
         CR4mpmpcl = 0d0
      elseif (ieorder.eq.0)then
         CR4mpmpcl =
     .        + CR4mpmpsubcl(j1,j2,j3,j4)
     .        + CR4mpmpsubcl(j1,j4,j3,j2)
     .        + CR4mpmpsubcl(j3,j2,j1,j4)
     .        + CR4mpmpsubcl(j3,j4,j1,j2)
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.2) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function CR4mpmpnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      complex(8), external :: CR4mpmpsubnf
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      if (ieorder.eq.-2)then
         CR4mpmpnf = 0d0
      elseif (ieorder.eq.-1)then
         CR4mpmpnf = 0d0
      elseif (ieorder.eq.0)then
         CR4mpmpnf =
     .        + CR4mpmpsubnf(j1,j2,j3,j4)
     .        + CR4mpmpsubnf(j1,j4,j3,j2)
     .        + CR4mpmpsubnf(j3,j2,j1,j4)
     .        + CR4mpmpsubnf(j3,j4,j1,j2)
      endif

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.2) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function CR4mpmpsubcl(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243,z2ba3123
      complex(8)           :: z2ba2134,z2ba4124,z3ab3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3
c     Common blocks.
      common/kin5/s,zA,zB

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      CR4mpmpsubcl = 
     .     2d0/(2d0*za12*za23*za34*za41)*(
     .     - z3ab3241**3*za34*za21/(3d0*za42*(s3s234-s23)**2)
     .     - (z3ab3241*za34*za21/za42)**2/(2d0*(s3s234-s23))
     .     )*(1d0/s23+1d0/s3s234)

      return
      end

************************************************************************

c     arXiv:0804.4149v3, Eq.(5.2) with factor of
c     C_\Gamma = 1/(16 pi^2) removed.
      complex(8) function CR4mpmpsubnf(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243,z2ba3123
      complex(8)           :: z2ba2134,z2ba4124,z3ab3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3
c     Common blocks.
      common/kin5/s,zA,zB

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      CR4mpmpsubnf =
     .     - 2d0/(2d0*za12*za23*za34*za41)*(
     .     - z3ab3241**3*za34*za21/(3d0*za42*(s3s234-s23)**2)
     .     - (z3ab3241*za34*za21/za42)**2/(2d0*(s3s234-s23))
     .     )*(1d0/s23+1d0/s3s234)

      return
      end

************************************************************************

      complex(8) function zAcphi4g1mpmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mpmpmodcl,Rhat4mpmpmodcl,CR4mpmpmodcl

c     Combined CR4mpmpmodcl with C4mpmpmodcl function by replacing
c     the L2 and L3 functions in C4mpmpmodcl by L2hat and L3hat.
c     This could improve the numerical stability.
      zAcphi4g1mpmpcl =
     .     + C4mpmpmodcl(perm(1),renscale2)
CTP     .     + CR4mpmpmodcl(perm(1))
     .     + Rhat4mpmpmodcl(perm(1))

      return
      end

************************************************************************

      complex(8) function zAcphi4g1mpmpnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: C4mpmpmodnf,CR4mpmpmodnf,Rhat4mpmpmodnf

c     Combined CR4mpmpmodnf with C4mpmpmodnf function by replacing
c     the L2 and L3 functions in C4mpmpmodnf by L2hat and L3hat.
c     This could improve the numerical stability.
      zAcphi4g1mpmpnf =
     .     + C4mpmpmodnf(perm(1),renscale2)
CTP     .     + CR4mpmpmodnf(perm(1))
     .     + Rhat4mpmpmodnf(perm(1))

      return
      end

************************************************************************

      complex(8) function C4mpmpmodcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      integer              :: ieorder
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: sum
c     Externals.
      complex(8), external :: C4mpmpsubmodcl
      complex(8), external :: zAphi4g0mpmp
      complex(8), external :: F31m,F42me,F41m
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+s41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      sum = (0d0,0d0)
      do i=1,4
         sum = sum
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2))
     .        ,sc(ii(i+1),ii(i+3)),sc(ii(i),ii(i+2)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
      enddo

      if (ieorder.eq.-2)then
         C4mpmpmodcl = sum*conjg(zAphi4g0mpmp(PERM(1)))
      elseif (ieorder.eq.-1)then
         C4mpmpmodcl = sum*conjg(zAphi4g0mpmp(PERM(1)))
      elseif (ieorder.eq.0)then
         sum = sum
     .        + C4mpmpsubmodcl(j1,j2,j3,j4)
     .        + C4mpmpsubmodcl(j1,j4,j3,j2)
     .        + C4mpmpsubmodcl(j3,j2,j1,j4)
     .        + C4mpmpsubmodcl(j3,j4,j1,j2)
         C4mpmpmodcl = sum*conjg(zAphi4g0mpmp(PERM(1)))
      endif

      return
      end

************************************************************************

      complex(8) function C4mpmpmodnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: ieorder
      integer              :: j1,j2,j3,j4
      integer              :: i,ii(7)
      real(8)              :: sc(4,4)
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: sum
c     Externals.
      complex(8), external :: C4mpmpsubmodnf,F31m,F42me,F41m
      complex(8), external :: zAphi4g0mpmp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder
c     Data.
      data ii/1,2,3,4,1,2,3/
      save ii

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      sc(1,1)=0d0
      sc(1,2)=s12
      sc(1,3)=s12+s13+s23
      sc(1,4)=s12+s13+s14+s23+s24+s34
      sc(2,1)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(2,2)=0d0
      sc(2,3)=s23
      sc(2,4)=s23+s24+s34
      sc(3,1)=s34+s31+41
      sc(3,2)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(3,3)=0d0
      sc(3,4)=s34
      sc(4,1)=s41
      sc(4,2)=s41+s42+s12
      sc(4,3)=sc(1,4) !s(j1,j2)+s(j1,j3)+s(j1,j4)+s(j2,j3)+s(j2,j4)+s(j3,j4)
      sc(4,4)=0d0

      sum = (0d0,0d0)
      do i=1,4
         sum = sum
     .        - 0.5d0*F42me(sc(ii(i),ii(i+3)),sc(ii(i+1),ii(i+2))
     .        ,sc(ii(i+1),ii(i+3)),sc(ii(i),ii(i+2)),renscale2)
     .        - 0.5d0*F41m(sc(ii(i),ii(i+2)),sc(ii(i),ii(i+1)),
     .        sc(ii(i+1),ii(i+2)),renscale2)
     .        + F31m(sc(ii(i),ii(i+2)),renscale2)
     .        - F31m(sc(ii(i),ii(i+3)),renscale2)
      enddo

      if (ieorder.eq.-2)then
         C4mpmpmodnf = 0d0
      elseif (ieorder.eq.-1)then
         C4mpmpmodnf = 0d0
      elseif (ieorder.eq.0)then
         sum =
     .        + C4mpmpsubmodnf(j1,j2,j3,j4)
     .        + C4mpmpsubmodnf(j1,j4,j3,j2)
     .        + C4mpmpsubmodnf(j3,j2,j1,j4)
     .        + C4mpmpsubmodnf(j3,j4,j1,j2)
         C4mpmpmodnf = sum*conjg(zAphi4g0mpmp(PERM(1)))
      endif

      return
      end

************************************************************************

      complex(8) function C4mpmpsubmodcl(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s234
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: trmmod,trm3241,trm3421
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124,z3ab3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: BGRL3hat,BGRL2hat,BGRL1,F41mF
      complex(8), external :: zab2,zba2,zab3
c     Common blocks.
      common/kin5/s,zA,zB

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

      s234    = s23+s24+s34
      trm3241 = zb32*za24*zb41*za13
      trm3421 = zb34*za42*zb21*za13

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)
      s3s412 = ss3(j4,j1,j2)

      C4mpmpsubmodcl =
     .     + 4d0*(
     .     + trm3241*trm3421/(2d0*(s24*s13)**2)*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/(s24*s13**2)*BGRL1(s23,s234)
     .     )
     .     + 2d0*(
     .     - 0.5d0*(
     .     trm3241*trm3421/(s24*s13)**2)**2*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/s13**4*(
     .     + trm3241**2/(3d0*s24)*BGRL3hat(s23,s234)
     .     + trm3421*trm3241/(2d0*s24**2)*BGRL2hat(s23,s234)
     .     - trm3421*trm3241/(s24**3)*BGRL1(s23,s234)
     .     )
     .     )

      return
      end

************************************************************************

      complex(8) function C4mpmpsubmodnf(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s234
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: z3ab3241
      complex(8)           :: trmmod,trm3241,trm3421
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: BGRL3hat,BGRL2hat,BGRL1,F41mF
      complex(8), external :: zab2,zba2,zab3
c     Common blocks.
      common/kin5/s,zA,zB

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

      s234    = s23+s24+s34
      trm3241 = zb32*za24*zb41*za13
      trm3421 = zb34*za42*zb21*za13

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234 = ss3(j2,j3,j4)
      s3s341 = ss3(j3,j4,j1)
      s3s412 = ss3(j4,j1,j2)

      C4mpmpsubmodnf =
     .     - (
     .     + trm3241*trm3421/(2d0*(s24*s13)**2)*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/(s24*s13**2)*BGRL1(s23,s234)
     .     )
     .     - 2d0*(
     .     -0.5d0*(trm3241*trm3421/(s24*s13)**2)**2*F41mF(s234,s23,s34)
     .     - trm3241*trm3421/s13**4*(
     .     + trm3241**2/(3d0*s24)*BGRL3hat(s23,s234)
     .     + trm3421*trm3241/(2d0*s24**2)*BGRL2hat(s23,s234)
     .     - trm3421*trm3241/(s24**3)*BGRL1(s23,s234)
     .     )
     .     )

      return
      end

************************************************************************

      complex(8) function Rhat4mpmpmodcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124,z3ab3241
      complex(8)           :: im
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3
      complex(8), external :: zAphi4g0mpmp
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      im = (0d0,1d0)

      if (ieorder.eq.-2)then
         Rhat4mpmpmodcl = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mpmpmodcl = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mpmpmodcl =
     .        -2d0*(-im)*(
     .        conjg(zAphi4g0mpmp(perma(1)))-zAphi4g0mpmp(permb(1))
     .        )
     .        + 1d0/6d0*za24**4/(za12*za23*za34*za41)*(
     .        - s23*s34/(s24*s3s412)
     .        + 3d0*s23*s34/s24**2
     .        - s12*s41/(s24*s3s234)
     .        + 3d0*s12*s41/s24**2
     .        )
      endif

      return
      end

************************************************************************

      complex(8) function Rhat4mpmpmodnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: perma(4),permb(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: im
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124,z3ab3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3
c     Common blocks.
      common/kin5/s,zA,zB
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      im = (0d0,1d0)

      if (ieorder.eq.-2)then
         Rhat4mpmpmodnf = 0d0
      elseif (ieorder.eq.-1)then
         Rhat4mpmpmodnf = 0d0
      elseif (ieorder.eq.0)then
         Rhat4mpmpmodnf =
     .        - 1d0/6d0*za24**4/(za12*za23*za34*za41)*(
     .        - s23*s34/(s24*s3s412)
     .        + 3d0*s23*s34/s24**2
     .        - s12*s41/(s24*s3s234)
     .        + 3d0*s12*s41/s24**2
     .        )
      endif

      return
      end

************************************************************************

      complex(8) function CR4mpmpmodcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      complex(8), external :: CR4mpmpsubmodcl
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      if (ieorder.eq.-2)then
         CR4mpmpmodcl = 0d0
      elseif (ieorder.eq.-1)then
         CR4mpmpmodcl = 0d0
      elseif (ieorder.eq.0)then
         CR4mpmpmodcl =
     .        + CR4mpmpsubmodcl(j1,j2,j3,j4)
     .        + CR4mpmpsubmodcl(j1,j4,j3,j2)
     .        + CR4mpmpsubmodcl(j3,j2,j1,j4)
     .        + CR4mpmpsubmodcl(j3,j4,j1,j2)
      endif

      return
      end

************************************************************************

      complex(8) function CR4mpmpmodnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4
      integer              :: ieorder
      complex(8), external :: CR4mpmpsubmodnf
      common/order/ieorder

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      if (ieorder.eq.-2)then
         CR4mpmpmodnf = 0d0
      elseif (ieorder.eq.-1)then
         CR4mpmpmodnf = 0d0
      elseif (ieorder.eq.0)then
         CR4mpmpmodnf =
     .        + CR4mpmpsubmodnf(j1,j2,j3,j4)
     .        + CR4mpmpsubmodnf(j1,j4,j3,j2)
     .        + CR4mpmpsubmodnf(j3,j2,j1,j4)
     .        + CR4mpmpsubmodnf(j3,j4,j1,j2)
      endif

      return
      end

************************************************************************

      complex(8) function CR4mpmpsubmodcl(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: z3ab3241,z3ba3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
c     Common blocks.
      common/kin5/s,zA,zB

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      CR4mpmpsubmodcl =
     .     2d0/(2d0*zb12*zb23*zb34*zb41)*(
     .     - z3ba3241**3*zb34*zb21/(3d0*zb42*(s3s234-s23)**2)
     .     - (z3ba3241*zb34*zb21/zb42)**2/(2d0*(s3s234-s23))
     .     )*(1d0/s23+1d0/s3s234)

      return
      end

************************************************************************

      complex(8) function CR4mpmpsubmodnf(j1,j2,j3,j4)
      implicit none
      integer, intent(in)  :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134
      complex(8)           :: z2ab4124,z2ab1234,z2ab3412
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: z3ab3241,z3ba3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
c     Common blocks.
      common/kin5/s,zA,zB

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      CR4mpmpsubmodnf =
     .     -2d0/(2d0*zb12*zb23*zb34*zb41)*(
     .     - z3ba3241**3*zb34*zb21/(3d0*zb42*(s3s234-s23)**2)
     .     - (z3ba3241*zb34*zb21/zb42)**2/(2d0*(s3s234-s23))
     .     )*(1d0/s23+1d0/s3s234)

      return
      end

c-----------------------------------------------------------------------
c     Library for H -> g g g g one-loop sub-layer amplitudes.

c     This function is the sum of the finite cut-constructible
c     and rational terms from arXiv:0909.4475 [hep-ph].
c     I.e. it is the sum of F4 in Eq. (5.12) and R4 in Eq. (5.13).
      complex(8) function FR4unsymcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4,j
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: mhsq,s123,s234,s134,s124
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
      complex(8)           :: z2ab1234,z2ab3412,z2ab1342,z2ab2341
      complex(8)           :: z2ab2143,z2ab3142,z2ab3241,z2ab3124
      complex(8)           :: z2ab4123,z2ab4321,z2ab4231
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243
      complex(8)           :: z2ba3123,z2ba2134,z2ba4124
      complex(8)           :: z3ab3241,z3ba3241
      complex(8)           :: gammap,gammam
      complex(8)           :: k1sq,k2sq,k1Dk2,factor,coef3mass
      complex(8)           :: W1,W2,W3
      complex(8)           :: d1,d2,d3
      complex(8)           :: a1,a2,a3,a4
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
      complex(8), external :: BGRL0,BGRL1,BGRL2hat,BGRL3hat
      complex(8), external :: F41mF_BGMW,F33m
      complex(8), external :: lnrat,W
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)
      z2ab1342 = zab2(j1,j3,j4,j2)
      z2ab2341 = zab2(j2,j3,j4,j1)
      z2ab2143 = zab2(j2,j1,j4,j3)
      z2ab3142 = zab2(j3,j1,j4,j2)
      z2ab3241 = zab2(j3,j2,j4,j1)
      z2ab3124 = zab2(j3,j1,j2,j4)
      z2ab4123 = zab2(j4,j1,j2,j3)
      z2ab4321 = zab2(j4,j3,j2,j1)
      z2ab4231 = zab2(j4,j2,j3,j1)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)

      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      mhsq = s12+s13+s14+s23+s24+s34
      s234 = s23+s34+s24
      s134 = s13+s34+s14
      s124 = s12+s24+s14
      s123 = s12+s23+s13
      W1   = W(mhsq,s234,s12,s23,s34,s14)
      W2   = W(mhsq,s134,s23,s34,s14,s12)
      W3   = W(mhsq,s124,s34,s14,s12,s23)

      k1sq  = dcmplx(mhsq)
      k2sq  = dcmplx(s12)
      k1Dk2 = -dcmplx(s12+0.5d0*(s13+s14+s23+s24))
      coef3mass = (0d0,0d0)

      gammap = k1Dk2 + sqrt(k1Dk2**2-k1sq*k2sq)
      gammam = 2d0*k1Dk2 - gammap

      factor = gammap/(gammap**2-k1sq*k2sq)
      a1 = factor*(-gammap-k1sq)
      a2 = a1
      a3 = factor*(-gammap)
      a4 = a3

c     Rewrite (a2*s6(j1,j2)+a3*s6(j1,j3)+a4*s6(j1,j4))=d1K=d1
c     for better numerical stability in soft limit.
      d1 = -factor*s12*(gammap+mhsq+mhsq*(s13+s14)/gammam)
c     Rewrite (a1*s6(j1,j3)+a2*s6(j2,j3)+a4*s6(j3,j4))=d3K=d2
c     for better numerical stability in soft limit.
      d2 = -factor*s34*(mhsq*(s13+s23)/(gammam+mhsq)+gammap)
c     Rewrite (a1*s6(j1,j4)+a2*s6(j2,j4)+a3*s6(j3,j4))=d4K=d3
c     for better numerical stability in soft limit.
      d3 = -factor*s34*(mhsq*(s14+s24)/(gammam+mhsq)+gammap)

      coef3mass = coef3mass
     .     + mhsq**2*za34**3
     .     *(+a3*za23*zb31+a4*za24*zb41)
     .     *(+a1*za21*zb13+a4*za24*zb43)
     .     *(+a1*za21*zb14+a3*za23*zb34)
     .     /(gammap*(gammap+mhsq)*za12
     .     *d1*d2*d3
     .  )

      factor = gammam/(gammam**2-k1sq*k2sq)
      a1 = factor*(-gammam-k1sq)
      a2 = a1
      a3 = factor*(-gammam)
      a4 = a3

c     Rewrite (a1*s6(j1,j4)+a2*s6(j2,j4)+a3*s6(j3,j4))=d4K=d3
c     for better numerical stability in soft limit.
      d3 = -factor*s34*(mhsq*(s14+s24)/(gammap+mhsq)+gammam)
c     Rewrite (a1*s6(j1,j3)+a2*s6(j2,j3)+a4*s6(j3,j4))=d3K=d2
c     for better numerical stability in soft limit.
      d2 = -factor*s34*(mhsq*(s13+s23)/(gammap+mhsq)+gammam)
c     Rewrite (a2*s6(j1,j2)+a3*s6(j1,j3)+a4*s6(j1,j4))=d1K=d1
c     for better numerical stability in soft limit.
      d1 = -factor*s12*(gammam+mhsq+mhsq*(s13+s14)/gammap)

      coef3mass = coef3mass
     .     + mhsq**2*za34**3
     .     *(+a3*za23*zb31+a4*za24*zb41)
     .     *(+a1*za21*zb13+a4*za24*zb43)
     .     *(+a1*za21*zb14+a3*za23*zb34)
     .     /(gammam*(gammam+mhsq)*za12
     .     *d1*d2*d3
     .  )

c     Eq.(5.12).
      FR4unsymcl = -s234**3/(4d0*z2ab1342*z2ab1234*zb23*zb34)*W1*(-1d0)

     .     + (z2ab2341**3/(2d0*s134*z2ab2143*zb34*zb41)
     .     +za34**3*mhsq**2/(2d0*s134*z2ab1342*z2ab3142*za41))*W2

     .     + 0.25d0/s124*(z2ab3241**4/(z2ab3142*z2ab3124*zb21*zb41)
     .     + za24**4*mhsq**2/(za12*za14*z2ab2143*z2ab4123))*W3
     .     *(-1d0)*(1d0)

     .     + coef3mass*F33m(mhsq,s12,s34)

      FR4unsymcl = FR4unsymcl
     .     + (
     .     2d0*z2ab3241**2/(s124*zb24**2)
     .     *F41mF_BGMW(s124,s12,s14)*(-0.5d0)
     .     + 4d0*za24*z2ab3241**2/(s124*zb42)
     .     *BGRL1(s124,s12)
     .     - 4d0*za23*z2ab4321**2/(s123*zb32)
     .     *BGRL1(s123,s12)
     .     )

      FR4unsymcl = FR4unsymcl
     .     + (
     .     zb12*zb41*z2ab3142*z2ab3124/(2d0*s124*zb24**4)
     .     *F41mF_BGMW(s124,s12,s14)

     .     + (za34*zb41)**2/zb42**2/3d0*(
     .     s24*s12*(2d0*BGRL3hat(s124,s12)+1d0/s124*BGRL2hat(s124,s12))
     .     + 3d0*s12*(BGRL2hat(s124,s12)+1d0/s124*BGRL1(s124,s12))
     .     + 6d0*s12**2/s24/s124*BGRL1(s124,s12)
     .     )
     .     - za34*zb41*za32*zb21/zb42**2/3d0*(
     .     + s24*(BGRL2hat(s124,s12)+2d0/s124*BGRL1(s124,s12))
     .     + 6d0/s124*BGRL0(s124,s12)
     .     + 12d0*s12/s24/s124*BGRL0(s124,s12)
     .     )
     .     + (za32*zb21)**2/zb42**2/3d0*(
     .     - s24/s124*BGRL1(s124,s12)
     .     + 6d0*s14/s24/s124*BGRL0(s124,s12)
     .     + 3d0/s124*BGRL0(s124,s12)
     .     )
c     Above block is the rewritten result of BGRL3hat(s124,s12),
c     BGRL2hat(s124,s12), BGRL1hat(s124,s12), BGRL0hat(s124,s12) terms
c     in (5.12) of 0909.4475v2.
c     New rational terms from the rewriting are moved to the rational
c     block below.
     .     - 2d0*s123*za23*(za34*zb31)**2/(3d0*zb32)*BGRL3hat(s123,s12)
     .     - za23*za34*zb31*z2ab4231/(3d0*zb32)*BGRL2hat(s123,s12)
     .     + za23*z2ab4231**2/(3d0*s123*zb32)*BGRL1(s123,s12)
     .     )

c     Add rational piece Eq.(5.13).
      FR4unsymcl = FR4unsymcl
     .     - 0.5d0*(
     .     - za23*za34*z2ab4231*zb31/(3d0*s123*za12*zb21*zb32)
     .     - z2ab3241**2/(s124*zb42**2)

     .     - za24*za34*za32*zb21*zb41/(3d0*s124*s12*zb42)
     .     + za24*(za34*zb41)**2/(3d0*s124*s124*zb42)
     .     + (zb14*za43)**2/(s124*zb42**2)
c     Above block is the combination of the third and fourth term in
c     (5.13) of 0909.4475 with the new rational terms from the
c     rewriting of (5.12).
     .     - za24*(s23*s24+s23*s34+s24*s34)
     .     /(3d0*za12*za14*zb23*zb34*zb42)
     .     + z2ab2341*z2ab4231/(3d0*s234*zb23*zb34)
     .     - 2d0*zb12*za23*zb31**2/(3d0*zb23**2*zb41*zb34)
     .     )

      return
      end

************************************************************************

c     This function is the sum of the finite cut-constructible
c     and rational terms from arXiv:0909.4475 [hep-ph].
c     I.e. it is the sum of F4 in Eq. (5.12) and R4 in Eq. (5.13).
      complex(8) function FR4unsymnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4,j
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: mhsq,s123,s234,s134,s124
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: W1,W2,W3
      complex(8)           :: d1,d2,d3
      complex(8)           :: k1sq,k2sq,k1Dk2
      complex(8)           :: factor,coef3mass
      complex(8)           :: a1,a2,a3,a4
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
      complex(8)           :: z2ab1234,z2ab3412,z2ab1342,z2ab2341
      complex(8)           :: z2ab2143,z2ab3142,z2ab3241,z2ab3124
      complex(8)           :: z2ab4123,z2ab4321,z2ab4231
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243,z2ba3123
      complex(8)           :: z2ba2134,z2ba4124,z3ab3241,z3ba3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
      complex(8), external :: lnrat,W
      complex(8), external :: BGRL0,BGRL1,BGRL2hat,BGRL3hat
      complex(8), external :: F41mF_BGMW,F33m
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)
      z2ab1342 = zab2(j1,j3,j4,j2)
      z2ab2341 = zab2(j2,j3,j4,j1)
      z2ab2143 = zab2(j2,j1,j4,j3)
      z2ab3142 = zab2(j3,j1,j4,j2)
      z2ab3241 = zab2(j3,j2,j4,j1)
      z2ab3124 = zab2(j3,j1,j2,j4)
      z2ab4123 = zab2(j4,j1,j2,j3)
      z2ab4321 = zab2(j4,j3,j2,j1)
      z2ab4231 = zab2(j4,j2,j3,j1)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      mhsq = s12+s13+s14+s23+s24+s34
      s234 = s23+s34+s24
      s134 = s13+s34+s14
      s124 = s12+s24+s14
      s123 = s12+s23+s13

c     Eq.(5.12).
      FR4unsymnf =-1d0/4d0*(
     .     2d0*z2ab3241**2/(s124*zb24**2)
     .     *F41mF_BGMW(s124,s12,s14)*(-0.5d0)
     .     + 4d0*za24*z2ab3241**2/(s124*zb42)*BGRL1(s124,s12)
     .     - 4d0*za23*z2ab4321**2/(s123*zb32)*BGRL1(s123,s12))

      FR4unsymnf = FR4unsymnf
     .     - (
     .     zb12*zb41*z2ab3142*z2ab3124
     .     /(2d0*s124*zb24**4)*F41mF_BGMW(s124,s12,s14)

     .     + (za34*zb41)**2/zb42**2/3d0*(
     .     s24*s12*(2d0*BGRL3hat(s124,s12)+1d0/s124*BGRL2hat(s124,s12))
     .     + 3d0*s12*(BGRL2hat(s124,s12)+1d0/s124*BGRL1(s124,s12))
     .     + 6d0*s12**2/s24/s124*BGRL1(s124,s12)
     .     )
     .     - za34*zb41*za32*zb21/zb42**2/3d0*(
     .     + s24*(BGRL2hat(s124,s12)+2d0/s124*BGRL1(s124,s12))
     .     + 6d0/s124*BGRL0(s124,s12)
     .     + 12d0*s12/s24/s124*BGRL0(s124,s12))
     .     + (za32*zb21)**2/zb42**2/3d0*(
     .     - s24/s124*BGRL1(s124,s12)
     .     + 6d0*s14/s24/s124*BGRL0(s124,s12)
     .     + 3d0/s124*BGRL0(s124,s12)
     .     )
c     Above block is the rewritten result of BGRL3hat(s124,s12),
c     BGRL2hat(s124,s12), BGRL1hat(s124,s12), BGRL0hat(s124,s12) terms
c     in (5.12) of 0909.4475v2. New rational terms from the rewriting
c     are moved to the rational block in below.
     .     - 2d0*s123*za23*(za34*zb31)**2/(3d0*zb32)*BGRL3hat(s123,s12)
     .     - za23*za34*zb31*z2ab4231/(3d0*zb32)*BGRL2hat(s123,s12)
     .     + za23*z2ab4231**2/(3d0*s123*zb32)*BGRL1(s123,s12))

c     Add rational piece Eq.(5.13).
      FR4unsymnf = FR4unsymnf
     .     + 0.5d0*(
     .     - za23*za34*z2ab4231*zb31/(3d0*s123*za12*zb21*zb32)
     .     - z2ab3241**2/(s124*zb42**2)

     .     - za24*za34*za32*zb21*zb41/(3d0*s124*s12*zb42)
     .     + za24*(za34*zb41)**2/(3d0*s124*s124*zb42)
     .     + (zb14*za43)**2/(s124*zb42**2)
c     Above block is the combination of the third and fourth term
c     in (5.13) of 0909.4475 with the new rational terms from the
c     rewriting of (5.12).
     .     - za24*(s23*s24+s23*s34+s24*s34)
     .     /(3d0*za12*za14*zb23*zb34*zb42)
     .     + z2ab2341*z2ab4231/(3d0*s234*zb23*zb34)
     .     - 2d0*zb12*za23*zb31**2/(3d0*zb23**2*zb41*zb34)
     .     )

      return
      end

************************************************************************

c     This function is the FR4unsym function with za and zb
c     getting swapped.
c     This function serves the purpose of generating -+++
c     helicity configurations.
      complex(8) function FR4unsymmodcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4,j
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: mhsq,s123,s234,s134,s124
      real(8)              :: s3s234,s3s341,s3s412
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: W1,W2,W3
      complex(8)           :: d1,d2,d3
      complex(8)           :: a1,a2,a3,a4
      complex(8)           :: k1sq,k2sq,k1Dk2
      complex(8)           :: gammam,gammap,factor,coef3massmod
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
      complex(8)           :: z2ab1234,z2ab3412,z2ab1342,z2ab2341
      complex(8)           :: z2ab2143,z2ab3142,z2ab3241,z2ab3124
      complex(8)           :: z2ab4123,z2ab4321,z2ab4231
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243,z2ba3123
      complex(8)           :: z2ba2134,z2ba4124,z2ba1342,z2ba2341
      complex(8)           :: z2ba2143,z2ba3142,z2ba3241,z2ba3124
      complex(8)           :: z2ba4123,z2ba4321,z2ba4231
      complex(8)           :: z3ab3241,z3ba3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
      complex(8), external :: W,lnrat
      complex(8), external :: BGRL0,BGRL1,BGRL2hat,BGRL3hat
      complex(8), external :: F41mF_BGMW,F33m
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)
      z2ab1342 = zab2(j1,j3,j4,j2)
      z2ab2341 = zab2(j2,j3,j4,j1)
      z2ab2143 = zab2(j2,j1,j4,j3)
      z2ab3142 = zab2(j3,j1,j4,j2)
      z2ab3241 = zab2(j3,j2,j4,j1)
      z2ab3124 = zab2(j3,j1,j2,j4)
      z2ab4123 = zab2(j4,j1,j2,j3)
      z2ab4321 = zab2(j4,j3,j2,j1)
      z2ab4231 = zab2(j4,j2,j3,j1)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z2ba1342 = zba2(j1,j3,j4,j2)
      z2ba2341 = zba2(j2,j3,j4,j1)
      z2ba2143 = zba2(j2,j1,j4,j3)
      z2ba3142 = zba2(j3,j1,j4,j2)
      z2ba3241 = zba2(j3,j2,j4,j1)
      z2ba3124 = zba2(j3,j1,j2,j4)
      z2ba4123 = zba2(j4,j1,j2,j3)
      z2ba4321 = zba2(j4,j3,j2,j1)
      z2ba4231 = zba2(j4,j2,j3,j1)
      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      mhsq = s12+s13+s14+s23+s24+s34
      s234 = s23+s34+s24
      s134 = s13+s34+s14
      s124 = s12+s24+s14
      s123 = s12+s23+s13

      W1 = W(mhsq,s234,s12,s23,s34,s14)
      W2 = W(mhsq,s134,s23,s34,s14,s12)
      W3 = W(mhsq,s124,s34,s14,s12,s23)

      k1sq  = dcmplx(mhsq)
      k2sq  = dcmplx(s12)
      k1Dk2 = -dcmplx(s12+0.5d0*(s13+s14+s23+s24))
      coef3massmod = (0d0,0d0)

      gammap = k1Dk2+sqrt(k1Dk2**2-k1sq*k2sq)
      gammam = 2d0*k1Dk2-gammap

      factor = gammap/(gammap**2-k1sq*k2sq)
      a1 = factor*(-gammap-k1sq)
      a2 = a1
      a3 = factor*(-gammap)
      a4 = a3

c     Rewrite (a2*s6(j1,j2)+a3*s6(j1,j3)+a4*s6(j1,j4))=d1K=d1
c     for better numerical stability in soft limit.
      d1 = -factor*s12*(gammap+mhsq+mhsq*(s13+s14)/gammam)
c     Rewrite (a1*s6(j1,j3)+a2*s6(j2,j3)+a4*s6(j3,j4)) = d3K=d2
c     for better numerical stability in soft limit.
      d2 = -factor*s34*(mhsq*(s13+s23)/(gammam+mhsq)+gammap)
c     Rewrite (a1*s6(j1,j4)+a2*s6(j2,j4)+a3*s6(j3,j4))=d4K=d3
c     for better numerical stability in soft limit.
      d3 = -factor*s34*(mhsq*(s14+s24)/(gammam+mhsq)+gammap)

      coef3massmod = coef3massmod
     .     + mhsq**2*zb34**3
     .     *(+a3*zb23*za31+a4*zb24*za41)
     .     *(+a1*zb21*za13+a4*zb24*za43)
     .     *(+a1*zb21*za14+a3*zb23*za34)
     .     /(gammap*(gammap+mhsq)*zb12
     .     *d1*d2*d3
     .     )

      factor = gammam/(gammam**2-k1sq*k2sq)
      a1 = factor*(-gammam-k1sq)
      a2 = a1
      a3 = factor*(-gammam)
      a4 = a3

c     Rewrite (a1*s6(j1,j4)+a2*s6(j2,j4)+a3*s6(j3,j4))=d4K=d3
c     for better numerical stability in soft limit.
      d3 = -factor*s34*(mhsq*(s14+s24)/(gammap+mhsq)+gammam)
c     Rewrite (a1*s6(j1,j3)+a2*s6(j2,j3)+a4*s6(j3,j4))=d2
c     for better numerical stability in soft limit.
      d2 = -factor*s34*(mhsq*(s13+s23)/(gammap+mhsq)+gammam)
c     Rewrite (a2*s6(j1,j2)+a3*s6(j1,j3)+a4*s6(j1,j4))=d1K=d1
c     for better numerical stability in soft limit.
      d1 = -factor*s12*(gammam+mhsq+mhsq*(s13+s14)/gammap)

      coef3massmod = coef3massmod
     .     + mhsq**2*zb34**3
     .     *(+a3*zb23*za31+a4*zb24*za41)
     .     *(+a1*zb21*za13+a4*zb24*za43)
     .     *(+a1*zb21*za14+a3*zb23*za34)
     .     /(gammam*(gammam+mhsq)*zb12
     .     *d1*d2*d3
     .  )

      FR4unsymmodcl =
     .     -s234**3/(4d0*z2ba1342*z2ba1234*za23*za34)*W1*(-1d0)

     .     + (
     .     z2ba2341**3/(2d0*s134*z2ba2143*za34*za41)
     .     + zb34**3*mhsq**2/(2d0*s134*z2ba1342*z2ba3142*zb41))*W2

     .     +0.25d0/s124*(
     .     z2ba3241**4/(z2ba3142*z2ba3124*za21*za41)
     .     + zb24**4*mhsq**2/(zb12*zb14*z2ba2143*z2ba4123)
     .     )*W3*(-1d0)*(1d0)

     .     + coef3massmod*F33m(mhsq,s12,s34)

      FR4unsymmodcl = FR4unsymmodcl
     .     + (
     .     2d0*z2ba3241**2/(s124*za24**2)
     .     *F41mF_BGMW(s124,s12,s14)*(-0.5d0)
     .     + 4d0*zb24*z2ba3241**2/(s124*za42)*BGRL1(s124,s12)
     .     - 4d0*zb23*z2ba4321**2/(s123*za32)*BGRL1(s123,s12)
     .     )

      FR4unsymmodcl = FR4unsymmodcl
     .     + (
     .     za12*za41*z2ba3142*z2ba3124
     .     /(2d0*s124*za24**4)*F41mF_BGMW(s124,s12,s14)

     .     + (zb34*za41)**2/za42**2/3d0*(
     .     s24*s12*(
     .     2d0*BGRL3hat(s124,s12)+1d0/s124*BGRL2hat(s124,s12)
     .     )
     .     + 3d0*s12*(BGRL2hat(s124,s12)+1d0/s124*BGRL1(s124,s12))
     .     + 6d0*s12**2/s24/s124*BGRL1(s124,s12)
     .     )
     .     - zb34*za41*zb32*za21/za42**2/3d0*(
     .     + s24*(BGRL2hat(s124,s12)+2d0/s124*BGRL1(s124,s12))
     .     + 6d0/s124*BGRL0(s124,s12)
     .     + 12d0*s12/s24/s124*BGRL0(s124,s12)
     .     )
     .     + (zb32*za21)**2/za42**2/3d0*(
     .     - s24/s124*BGRL1(s124,s12)
     .     + 6d0*s14/s24/s124*BGRL0(s124,s12)
     .     + 3d0/s124*BGRL0(s124,s12)
     .     )
c     Above block is the rewritten result of BGRL3hat(s124,s12),
c     BGRL2hat(s124,s12), BGRL1hat(s124,s12), BGRL0hat(s124,s12) terms
c     in (5.12) of 0909.4475v2. New rational terms from the rewriting
c     are moved to the rational block in below.
     .     - 2d0*s123*zb23*(zb34*za31)**2/(3d0*za32)*BGRL3hat(s123,s12)
     .     - zb23*zb34*za31*z2ba4231/(3d0*za32)*BGRL2hat(s123,s12)
     .     + zb23*z2ba4231**2/(3d0*s123*za32)*BGRL1(s123,s12)
     .     )

      FR4unsymmodcl = FR4unsymmodcl
     .     - 0.5d0*(
     .     -zb23*zb34*z2ba4231*za31/(3d0*s123*zb12*za21*za32)
     .     - z2ba3241**2/(s124*za42**2)

     .     - zb24*zb34*zb32*za21*za41/(3d0*s12*s124*za42)
     .     + zb24*(zb34*za41)**2/(3d0*s124*s124*za42)
     .     + (za14*zb43)**2/(s124*za42**2)
c     Above block is the combination of the third and fourth term
c     in (5.13) of 0909.4475 with the new rational terms from the
c     rewriting of (5.12).
     .     - zb24*(s23*s24+s23*s34+s24*s34)
     .     /(3d0*zb12*zb14*za23*za34*za42)
     .     + z2ba2341*z2ba4231/(3d0*s234*za23*za34)
     .     - 2d0*za12*zb23*za31**2/(3d0*za23**2*za41*za34)
     .     )

      return
      end

************************************************************************

c     This function is the FR4unsym function with za and zb
c     getting swapped.
c     This function serves the purpose of generating -+++
c     helicity configurations.
      complex(8) function FR4unsymmodnf(perm)      
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: j1,j2,j3,j4,j
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s21,s31,s41,s32,s42,s43
      real(8)              :: mhsq,s123,s234,s134,s124
      real(8)              :: s(5,5)
      real(8)              :: s3s234,s3s341,s3s412
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: W1,W2,W3
      complex(8)           :: a1,a2,a3,a4
      complex(8)           :: k1sq,k2sq,k1Dk2
      complex(8)           :: za12,za13,za14,za23,za24,za34
      complex(8)           :: za21,za31,za41,za32,za42,za43
      complex(8)           :: zb12,zb13,zb14,zb23,zb24,zb34
      complex(8)           :: zb21,zb31,zb41,zb32,zb42,zb43
      complex(8)           :: z2ab1243,z2ab3123,z2ab2134,z2ab4124
      complex(8)           :: z2ab1234,z2ab3412,z2ab1342,z2ab2341
      complex(8)           :: z2ab2143,z2ab3142,z2ab3241,z2ab3124
      complex(8)           :: z2ab4123,z2ab4321,z2ab4231
      complex(8)           :: z2ba3412,z2ba1234,z2ba1243,z2ba3123
      complex(8)           :: z2ba2134,z2ba4124,z2ba1342,z2ba2341
      complex(8)           :: z2ba2143,z2ba3142,z2ba3241,z2ba3124
      complex(8)           :: z2ba4123,z2ba4321,z2ba4231
      complex(8)           :: z3ab3241,z3ba3241
c     Externals.
      real(8), external    :: ss3
      complex(8), external :: zab2,zba2,zab3,zba3
      complex(8), external :: lnrat,W
      complex(8), external :: BGRL0,BGRL1,BGRL2hat,BGRL3hat
      complex(8), external :: F41mF_BGMW,F33m
c     Common blocks.
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab1243 = zab2(j1,j2,j4,j3)
      z2ab3123 = zab2(j3,j1,j2,j3)
      z2ab2134 = zab2(j2,j1,j3,j4)
      z2ab4124 = zab2(j4,j1,j2,j4)
      z2ab1234 = zab2(j1,j2,j3,j4)
      z2ab3412 = zab2(j3,j4,j1,j2)
      z2ab1342 = zab2(j1,j3,j4,j2)
      z2ab2341 = zab2(j2,j3,j4,j1)
      z2ab2143 = zab2(j2,j1,j4,j3)
      z2ab3142 = zab2(j3,j1,j4,j2)
      z2ab3241 = zab2(j3,j2,j4,j1)
      z2ab3124 = zab2(j3,j1,j2,j4)
      z2ab4123 = zab2(j4,j1,j2,j3)
      z2ab4321 = zab2(j4,j3,j2,j1)
      z2ab4231 = zab2(j4,j2,j3,j1)

      z2ba3412 = zba2(j3,j4,j1,j2)
      z2ba1234 = zba2(j1,j2,j3,j4)
      z2ba1243 = zba2(j1,j2,j4,j3)
      z2ba3123 = zba2(j3,j1,j2,j3)
      z2ba2134 = zba2(j2,j1,j3,j4)
      z2ba4124 = zba2(j4,j1,j2,j4)
      z2ba1342 = zba2(j1,j3,j4,j2)
      z2ba2341 = zba2(j2,j3,j4,j1)
      z2ba2143 = zba2(j2,j1,j4,j3)
      z2ba3142 = zba2(j3,j1,j4,j2)
      z2ba3241 = zba2(j3,j2,j4,j1)
      z2ba3124 = zba2(j3,j1,j2,j4)
      z2ba4123 = zba2(j4,j1,j2,j3)
      z2ba4321 = zba2(j4,j3,j2,j1)
      z2ba4231 = zba2(j4,j2,j3,j1)
      z3ab3241 = zab3(j3,j2,j4,j1)
      z3ba3241 = zba3(j3,j2,j4,j1)

      s3s234   = ss3(j2,j3,j4)
      s3s341   = ss3(j3,j4,j1)
      s3s412   = ss3(j4,j1,j2)

      mhsq = s12+s13+s14+s23+s24+s34
      s234 = s23+s34+s24
      s134 = s13+s34+s14
      s124 = s12+s24+s14
      s123 = s12+s23+s13

      FR4unsymmodnf =
     .     + (-1d0/4d0)*(
     .     2d0*z2ba3241**2/(s124*za24**2)
     .     *F41mF_BGMW(s124,s12,s14)*(-0.5d0)
     .     + 4d0*zb24*z2ba3241**2/(s124*za42)*BGRL1(s124,s12)
     .     - 4d0*zb23*z2ba4321**2/(s123*za32)*BGRL1(s123,s12)
     .     )

      FR4unsymmodnf = FR4unsymmodnf
     .     - (
     .     za12*za41*z2ba3142*z2ba3124
     .     /(2d0*s124*za24**4)*F41mF_BGMW(s124,s12,s14)

     .     + (zb34*za41)**2/za42**2/3d0*(
     .     s24*s12*(2d0*BGRL3hat(s124,s12)+1d0/s124*BGRL2hat(s124,s12))
     .     + 3d0*s12*(BGRL2hat(s124,s12)+1d0/s124*BGRL1(s124,s12))
     .     + 6d0*s12**2/s24/s124*BGRL1(s124,s12)
     .     )
     .     - zb34*za41*zb32*za21/za42**2/3d0*(
     .     +s24*(BGRL2hat(s124,s12)+2d0/s124*BGRL1(s124,s12))
     .     + 6d0/s124*BGRL0(s124,s12)
     .     + 12d0*s12/s24/s124*BGRL0(s124,s12)
     .     )
     .     + (zb32*za21)**2/za42**2/3d0*(
     .     - s24/s124*BGRL1(s124,s12)
     .     + 6d0*s14/s24/s124*BGRL0(s124,s12)
     .     + 3d0/s124*BGRL0(s124,s12)
     .     )
c     Above block is the rewritten result of BGRL3hat(s124,s12),
c     BGRL2hat(s124,s12), BGRL1hat(s124,s12), BGRL0hat(s124,s12) terms
c     in (5.12) of 0909.4475v2. New rational terms from the rewriting
c     are moved to the rational block in below.
     .     - 2d0*s123*zb23*(zb34*za31)**2/(3d0*za32)*BGRL3hat(s123,s12)
     .     - zb23*zb34*za31*z2ba4231/(3d0*za32)*BGRL2hat(s123,s12)
     .     + zb23*z2ba4231**2/(3d0*s123*za32)*BGRL1(s123,s12)
     .     )

      FR4unsymmodnf = FR4unsymmodnf
     .     + 0.5d0*(
     .     - zb23*zb34*z2ba4231*za31/(3d0*s123*zb12*za21*za32)
     .     - z2ba3241**2/(s124*za42**2)

     .     - zb24*zb34*zb32*za21*za41/(3d0*s12*s124*za42)
     .     + zb24*(zb34*za41)**2/(3d0*s124*s124*za42)
     .     + (za14*zb43)**2/(s124*za42**2)
c     Above block is the combination of the third and fourth term
c     in (5.13) of 0909.4475 with the new rational terms from the
c     rewriting of (5.12).
     .     - zb24*(s23*s24+s23*s34+s24*s34)
     .     /(3d0*zb12*zb14*za23*za34*za42)
     .     + z2ba2341*z2ba4231/(3d0*s234*za23*za34)
     .     - 2d0*za12*zb23*za31**2/(3d0*za23**2*za41*za34)
     .     )

      return
      end

c-----------------------------------------------------------------------

c     Full one-loop matrix element for
c     H -> q(i1) g(i3) g(i4) qbar(i2).
c     Adapted from MCFM/NNLOJET (src/process/H/libBHloop.f).
      real(8) function FullB2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external   :: B2g1H,Bt2g1H,Bh2g1H
      real(8), external   :: Btt2g1H,Bttt2g1H,Btth2g1H,Bhh2g1H
      real(8), external   :: B2g0H,Bt2g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*cn**2

      FullB2g1H = fac*(
     .     + B2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=2
     .     + B2g1H(p,i1,i4,i3,i2,renscale2,ipole) ! icol=2

     .     - 1d0/cn**2*(
     .     + Bt2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=3
     .     + Bt2g1H(p,i1,i4,i3,i2,renscale2,ipole) ! icol=3
     .     )

     .     + nf/cn*(
     .     + Bh2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=5
     .     + Bh2g1H(p,i1,i4,i3,i2,renscale2,ipole) ! icol=5
     .     )

     .     - 1d0/cn**2*(
     .     + Btt2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=3
     .     - 1d0/cn**2*Bttt2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=4
     .     + (nf/cn)*Btth2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=6
     .     )

     .     + 1d0/cn**2*Bhh2g1H(p,i1,i3,i4,i2,renscale2,ipole) ! icol=3
     .     )

c     Include O(as) Wilson coefficient.
      if (ipole.eq.0)then
         FullB2g1H = FullB2g1H
     .        + (11d0/3d0)*fac*(
     .        + B2g0H(p,i1,i3,i4,i2)
     .        + B2g0H(p,i1,i4,i3,i2)
     .        - 1d0/cn**2*Bt2g0H(p,i1,i3,i4,i2)
     .        )
      endif

      return
      end

************************************************************************

      real(8) function B2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: i,perm(4),permb(4),permm(4)
      integer              :: ieorder,ischeme,imemode
      real(8)              :: s1234,born,tree,ren
      real(8)              :: temp,wt
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,B2g0H
      complex(8), external :: zB2g0Hmppp,zB2g0Hmmmp,zB2g0Hmpmp
      complex(8), external :: zB2g0Hmmpp,zB2g0Hpmmm,zB2g0Hpppm
      complex(8), external :: zB2g0Hpmpm,zB2g0Hppmm
      complex(8), external :: zB2g1Hmpppcl,zB2g1Hmpmmcl,zB2g1Hmpmpcl
      complex(8), external :: zB2g1Hpmmmcl,zB2g1Hpmppcl,zB2g1Hpmpmcl
      complex(8), external :: zB2g1Hmppmcl,zB2g1Hpmmpcl
c     Common blocks.
      common/order/ieorder
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate the tree-level amplitude squared.
      tree = B2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i4
      perm(4) = i3

      permb(1) = i1
      permb(2) = i2
      permb(3) = i3
      permb(4) = i4

      permm(1) = i1
      permm(2) = i3
      permm(3) = i4
      permm(4) = i2

c     Calculate born-one-loop interference.
      wt   = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            wt =
     .           +dble((
     .           +zB2g1Hmpppcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))))
         endif
         if (i.eq.2)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmmcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))))
         endif
         if (i.eq.3)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmpcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))))
         endif
         if (i.eq.4)then
            wt =
     .           +dble((
     .           +zB2g1Hmppmcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))))
         endif
         if (i.eq.5)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmmcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))))
         endif
         if (i.eq.6)then
            wt =
     .           +dble((
     .           -zB2g1Hpmppcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))))
         endif
         if (i.eq.7)then
            wt =
     .           +dble((
     .           -zB2g1Hpmpmcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))))
         endif
         if (i.eq.8)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmpcl(perm(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))))
         endif
         temp = temp+wt
      enddo
      temp = temp/2d0/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren = 0d0
      if (ieorder.eq.0)then
         ren = 0d0
         if (ischeme.eq.1) ren = 3d0*pi**2/12d0
      elseif (ieorder.eq.-1)then
         ren = -4d0*11d0/6d0
      elseif (ieorder.eq.-2)then
         ren = 0d0
      endif

      B2g1H = temp + ren*tree
      B2g1H = B2g1H*born

      return
      end

************************************************************************

      real(8) function Bt2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: i,perm(4),permb(4),permm(4)
      integer              :: ieorder,ischeme,imemode
      real(8)              :: s1234,born,tree,ren
      real(8)              :: temp,wt
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
      complex(8)           :: zl12
c     Externals.
      real(8), external    :: A2g0H,B2g0H
      complex(8), external :: zB2g0Hmppp,zB2g0Hmmmp,zB2g0Hmpmp
      complex(8), external :: zB2g0Hmmpp,zB2g0Hpmmm,zB2g0Hpppm
      complex(8), external :: zB2g0Hpmpm,zB2g0Hppmm
      complex(8), external :: zB2g1Hmpppsl,zB2g1Hmpmmsl,zB2g1Hmpmpsl
      complex(8), external :: zB2g1Hpmmmsl,zB2g1Hpmppsl,zB2g1Hpmpmsl
      complex(8), external :: zB2g1Hmppmsl,zB2g1Hpmmpsl
      complex(8), external :: zlnrat
c     Common blocks.
      common/order/ieorder
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = B2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i4
      perm(4) = i3

      permm(1) = i1
      permm(2) = i3
      permm(3) = i4
      permm(4) = i2

      wt   = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            wt =
     .           +dble((
     .           +zB2g1Hmpppsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))))
         endif
         if (i.eq.2)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmmsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))))
         endif
         if (i.eq.3)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmpsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))))
         endif
         if (i.eq.4)then
            wt =
     .           +dble((
     .           +zB2g1Hmppmsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))))
         endif
         if (i.eq.5)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmmsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))))
         endif
         if (i.eq.6)then
            wt =
     .           +dble((
     .           -zB2g1Hpmppsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))))
         endif
         if (i.eq.7)then
            wt =
     .           +dble((
     .           -zB2g1Hpmpmsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))))
         endif
         if (i.eq.8)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmpsl(perm(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))))
         endif
         temp = temp+wt
      enddo
      temp = temp/2d0/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren = 0d0
      if (ieorder.eq.0)then
         ren = 0d0 
         if (ischeme.eq.1) ren = pi**2/12d0
      elseif (ieorder.eq.-1)then
         zl12 = zlnrat(renscale2,-s(i1,i2))
         ren  = -3d0/2d0-zl12
      elseif (ieorder.eq.-2)then
         ren = -1d0
      endif

      Bt2g1H = temp + ren*tree
      Bt2g1H = Bt2g1H*born

      return
      end

************************************************************************

      real(8) function Bh2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: i,perm(4),permb(4),permm(4)
      integer              :: ieorder,ischeme,imemode
      real(8)              :: s1234,born,tree,ren
      real(8)              :: temp,wt
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,B2g0H
      complex(8), external :: zB2g0Hmppp,zB2g0Hmmmp,zB2g0Hmpmp
      complex(8), external :: zB2g0Hmmpp,zB2g0Hpmmm,zB2g0Hpppm
      complex(8), external :: zB2g0Hpmpm,zB2g0Hppmm
      complex(8), external :: zB2g1Hmpppnf,zB2g1Hmpmmnf,zB2g1Hmpmpnf
      complex(8), external :: zB2g1Hpmmmnf,zB2g1Hpmppnf,zB2g1Hpmpmnf
      complex(8), external :: zB2g1Hmppmnf,zB2g1Hpmmpnf
c     Common blocks.
      common/order/ieorder
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
      tree = B2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i4
      perm(4) = i3

      permm(1) = i1
      permm(2) = i3
      permm(3) = i4
      permm(4) = i2

      wt   = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            wt =
     .           +dble((
     .           +zB2g1Hmpppnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))))
         endif
         if (i.eq.2)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmmnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))))
         endif
         if (i.eq.3)then
            wt =
     .           +dble((
     .           +zB2g1Hmpmpnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))))
         endif
         if (i.eq.4)then
            wt =
     .           +dble((
     .           +zB2g1Hmppmnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))))
         endif
         if (i.eq.5)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmmnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))))
         endif
         if (i.eq.6)then
            wt =
     .           +dble((
     .           -zB2g1Hpmppnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))))
         endif
         if (i.eq.7)then
            wt =
     .           +dble((
     .           -zB2g1Hpmpmnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))))
         endif
         if (i.eq.8)then
            wt =
     .           +dble((
     .           -zB2g1Hpmmpnf(perm(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))))
         endif
         temp = temp+wt
      enddo
      temp = temp/2d0/s1234**2

      ren = 0d0
      if (ieorder.eq.-1)then
         ren = 2d0/3d0
      endif

      Bh2g1H = temp + ren*tree
      Bh2g1H = Bh2g1H*born

      return
      end

************************************************************************

      real(8) function Btt2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit real(8) (a-h,o-y)
      implicit complex(8) (z)
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
      integer             :: perm(4),permb(4),permm(4),permn(4)
      integer             :: ieorder
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Common blocks.
      common/order/ieorder
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
      tree = Bt2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i3
      perm(4) = i4

      permb(1) = i1
      permb(2) = i2
      permb(3) = i4
      permb(4) = i3

      permm(1) = i1
      permm(2) = i4
      permm(3) = i3
      permm(4) = i2

      permn(1) = i1
      permn(2) = i3
      permn(3) = i4
      permn(4) = i2

      s13 = s(i1,i3)
      s14 = s(i1,i4)
      s23 = s(i2,i3)
      s24 = s(i2,i4)
      s34 = s(i3,i4)

      zamp = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp =
     .           +dble(
     .           (zB2g1Hmpppcl(perm(1),renscale2)
     .           +zB2g1Hmpppcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))+zB2g0Hmppp(permn(1))))
         endif
         if (i.eq.2)then
            zamp =
     .           +dble(
     .           (zB2g1Hmpmmcl(perm(1),renscale2)
     .           +zB2g1Hmpmmcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))+zB2g0Hmmmp(permn(1))))
         endif
c     Helicity configurations 3&4 cross talk when
c     combining the two colour orderings.
         if (i.eq.3)then
            zamp =
     .           +dble(
     .           (zB2g1Hmpmpcl(perm(1),renscale2)
     .           +zB2g1Hmppmcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))+zB2g0Hmmpp(permn(1))))
         endif
         if (i.eq.4)then
            zamp =
     .           +dble(
     .           (zB2g1Hmppmcl(perm(1),renscale2)
     .           +zB2g1Hmpmpcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))+zB2g0Hmpmp(permn(1))))
         endif
         if (i.eq.5)then
            zamp =
     .           +dble(
     .           -(zB2g1Hpmmmcl(perm(1),renscale2)
     .           +zB2g1Hpmmmcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))+zB2g0Hpmmm(permn(1))))
         endif
         if (i.eq.6)then
            zamp =
     .           +dble(
     .           -(zB2g1Hpmppcl(perm(1),renscale2)
     .           +zB2g1Hpmppcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))+zB2g0Hpppm(permn(1))))
         endif
c     Helicity configurations 7&8 cross talk when
c     combining the two colour orderings.
         if (i.eq.7)then
            zamp =
     .           +dble(
     .           -(zB2g1Hpmpmcl(perm(1),renscale2)
     .           +zB2g1Hpmmpcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))+zB2g0Hppmm(permn(1))))
         endif
         if (i.eq.8)then
            zamp =
     .           +dble(
     .           -(zB2g1Hpmmpcl(perm(1),renscale2)
     .           +zB2g1Hpmpmcl(permb(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))+zB2g0Hpmpm(permn(1))))
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
c     Rewrite the pole structure for better numerical
c     stability in unresolved limits.
      ren = 0d0
      if (ieorder.eq.0)then
         ren = 0d0
         if (ischeme.eq.1) ren = 3d0*pi**2/12d0
      elseif (ieorder.eq.-1)then
         zl34 = zlnrat(renscale2,-s34)
         zl14 = zlnrat(renscale2,-s14)
         zl24 = zlnrat(renscale2,-s24)
         zl13 = zlnrat(renscale2,-s13)
         zl23 = zlnrat(renscale2,-s23)
         temp = (-31d0/6d0
     .        -        zl34
     .        - 1d0/2d0*zl14
     .        - 1d0/2d0*zl13
     .        - 1d0/2d0*zl24
     .        - 1d0/2d0*zl23
     .        )*tree
      elseif (ieorder.eq.-2)then
         temp = -3d0*tree
      endif

      Btt2g1H = temp + ren*tree
      Btt2g1H = Btt2g1H*born

      return
      end

************************************************************************

      real(8) function Bttt2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit real(8) (a-h,o-y)
      implicit complex(8) (z)
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
      integer             :: perm(4),permb(4),permm(4),permn(4)
      integer             :: ieorder
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
      real(8), parameter  :: pi=3.141592653589793238d0
c     Common blocks.
      common/order/ieorder
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = Bt2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i3
      perm(4) = i4

      permb(1) = i1
      permb(2) = i2
      permb(3) = i4
      permb(4) = i3

      permm(1) = i1
      permm(2) = i4
      permm(3) = i3
      permm(4) = i2

      permn(1) = i1
      permn(2) = i3
      permn(3) = i4
      permn(4) = i2

      zamp = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpppsl(perm(1),renscale2)
     .           +zB2g1Hmpppsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))+zB2g0Hmppp(permn(1))))
         endif
         if (i.eq.2)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpmmsl(perm(1),renscale2)
     .           +zB2g1Hmpmmsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))+zB2g0Hmmmp(permn(1))))
         endif
c     Helicity configurations 3&4 cross talk when
c     combining the two colour orderings.
         if (i.eq.3)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpmpsl(perm(1),renscale2)
     .           +zB2g1Hmppmsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))+zB2g0Hmmpp(permn(1))))
         endif
         if (i.eq.4)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmppmsl(perm(1),renscale2)
     .           +zB2g1Hmpmpsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))+zB2g0Hmpmp(permn(1))))
         endif
         if (i.eq.5)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmmmsl(perm(1),renscale2)
     .           +zB2g1Hpmmmsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))+zB2g0Hpmmm(permn(1))))
         endif
         if (i.eq.6)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmppsl(perm(1),renscale2)
     .           +zB2g1Hpmppsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))+zB2g0Hpppm(permn(1))))
         endif
c     Helicity configurations 7&8 cross talk when
c     combining the two colour orderings.
         if (i.eq.7)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmpmsl(perm(1),renscale2)
     .           +zB2g1Hpmmpsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))+zB2g0Hppmm(permn(1))))
         endif
         if (i.eq.8)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmmpsl(perm(1),renscale2)
     .           +zB2g1Hpmpmsl(permb(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))+zB2g0Hpmpm(permn(1))))
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren = 0d0
      if (ieorder.eq.0)then
         ren = 0d0
         if (ischeme.eq.1) ren = pi**2/12d0
      elseif (ieorder.eq.-1)then
         zl12 = zlnrat(renscale2,-s(i1,i2))
         ren  = -3d0/2d0-zl12
      elseif (ieorder.eq.-2)then
         ren = -1d0
      endif

      Bttt2g1H = temp + ren*tree
      Bttt2g1H = Bttt2g1H*born

      return
      end

************************************************************************

      real(8) function Btth2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit real(8) (a-h,o-y)
      implicit complex(8) (z)
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
      integer             :: perm(4),permb(4),permm(4),permn(4)
      integer             :: ieorder
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Common blocks.
      common/order/ieorder
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
      tree = Bt2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i3
      perm(4) = i4

      permb(1) = i1
      permb(2) = i2
      permb(3) = i4
      permb(4) = i3

      permm(1) = i1
      permm(2) = i4
      permm(3) = i3
      permm(4) = i2

      permn(1) = i1
      permn(2) = i3
      permn(3) = i4
      permn(4) = i2

      zamp = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpppnf(perm(1),renscale2)
     .           +zB2g1Hmpppnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hmppp(permm(1))+zB2g0Hmppp(permn(1))))
         endif
         if (i.eq.2)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpmmnf(perm(1),renscale2)
     .           +zB2g1Hmpmmnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmmp(permm(1))+zB2g0Hmmmp(permn(1))))
         endif
         if (i.eq.3)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmpmpnf(perm(1),renscale2)
     .           +zB2g1Hmppmnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hmpmp(permm(1))+zB2g0Hmmpp(permn(1))))
         endif
c     Helicity configurations 3&4 cross talk when
c     combining the two colour orderings.
         if (i.eq.4)then
            zamp =
     .           +dble(
     .           (
     .           +zB2g1Hmppmnf(perm(1),renscale2)
     .           +zB2g1Hmpmpnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hmmpp(permm(1))+zB2g0Hmpmp(permn(1))))
         endif
         if (i.eq.5)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmmmnf(perm(1),renscale2)
     .           +zB2g1Hpmmmnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmmm(permm(1))+zB2g0Hpmmm(permn(1))))
         endif
         if (i.eq.6)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmppnf(perm(1),renscale2)
     .           +zB2g1Hpmppnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hpppm(permm(1))+zB2g0Hpppm(permn(1))))
         endif
c     Helicity configurations 7&8 cross talk when
c     combining the two colour orderings.
         if (i.eq.7)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmpmnf(perm(1),renscale2)
     .           +zB2g1Hpmmpnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hpmpm(permm(1))+zB2g0Hppmm(permn(1))))
         endif
         if (i.eq.8)then
            zamp =
     .           +dble(
     .           -(
     .           +zB2g1Hpmmpnf(perm(1),renscale2)
     .           +zB2g1Hpmpmnf(permb(1),renscale2)
     .           )*conjg(zB2g0Hppmm(permm(1))+zB2g0Hpmpm(permn(1))))
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

      ren = 0d0
      if (ieorder.eq.-1)then
         ren = 2d0/3d0
      endif

      Btth2g1H = temp + ren*tree
      Btth2g1H = Btth2g1H*born

      return
      end

************************************************************************

      real(8) function Bhh2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit real(8) (a-h,o-y)
      implicit complex(8) (z)
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
      integer             :: perm(4),permm(4),permn(4)
      integer             :: ieorder
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s21,s31,s41,s32,s42,s43
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Common blocks.
      common/order/ieorder
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
      tree = Bt2g0H(p,i1,i3,i4,i2)/born

c     Set pole order in loop amplitudes.
      ieorder = ipole

c     Fill permutations.
      perm(1) = i1
      perm(2) = i2
      perm(3) = i3
      perm(4) = i4

      permm(1) = i1
      permm(2) = i4
      permm(3) = i3
      permm(4) = i2

      permn(1) = i1
      permn(2) = i3
      permn(3) = i4
      permn(4) = i2

      s12 = s(i1,i2)
      s13 = s(i1,i3)
      s14 = s(i1,i4)
      s23 = s(i2,i3)
      s24 = s(i2,i4)
      s34 = s(i3,i4)

      s21 = s(i2,i1)
      s31 = s(i3,i1)
      s41 = s(i4,i1)
      s32 = s(i3,i2)
      s42 = s(i4,i2)
      s43 = s(i4,i3)

      zamp = 0d0
      temp = 0d0
      do i=1,8
         if (i.eq.1)then
            zamp =
     .           +dble(
     .           +zBt2g1Hmppp(perm(1),renscale2)
     .           *conjg(zB2g0Hmppp(permm(1))+zB2g0Hmppp(permn(1))))
         endif
         if (i.eq.2)then
            zamp =
     .           +dble(
     .           +zBt2g1Hmpmm(perm(1),renscale2)
     .           *conjg(zB2g0Hmmmp(permm(1))+zB2g0Hmmmp(permn(1))))
         endif
c     Helicity configurations 3&4 cross talk when
c     combining the two colour orderings.
         if (i.eq.3)then
            zamp =
     .           +dble(
     .           +zBt2g1Hmpmp(perm(1),renscale2)
     .           *conjg(zB2g0Hmpmp(permm(1))+zB2g0Hmmpp(permn(1))))
         endif
         if (i.eq.4)then
            zamp =
     .           +dble(
     .           +zBt2g1Hmppm(perm(1),renscale2)
     .           *conjg(zB2g0Hmmpp(permm(1))+zB2g0Hmpmp(permn(1))))
         endif
         if (i.eq.5)then
            zamp =
     .           +dble(
     .           -zBt2g1Hpmmm(perm(1),renscale2)
     .           *conjg(zB2g0Hpmmm(permm(1))+zB2g0Hpmmm(permn(1))))
         endif
         if (i.eq.6)then
            zamp =
     .           +dble(
     .           -zBt2g1Hpmpp(perm(1),renscale2)
     .           *conjg(zB2g0Hpppm(permm(1))+zB2g0Hpppm(permn(1))))
         endif
c     Helicity configurations 7&8 cross talk when
c     combining the two colour orderings.
         if (i.eq.7)then
            zamp =
     .           +dble(
     .           -zBt2g1Hpmpm(perm(1),renscale2)
     .           *conjg(zB2g0Hpmpm(permm(1))+zB2g0Hppmm(permn(1))))
         endif
         if (i.eq.8)then
            zamp =
     .           +dble(
     .           -zBt2g1Hpmmp(perm(1),renscale2)
     .           *conjg(zB2g0Hppmm(permm(1))+zB2g0Hpmpm(permn(1))))
         endif
         temp = temp+zamp
      enddo
      temp = temp/2d0/s1234**2

c     Rewrite the pole structure for better numerical
c     stability in unresolved limits.
      if (ieorder.eq.-1)then
         zl12 = zlnrat(renscale2,-s12)
         zl34 = zlnrat(renscale2,-s34)
         zl14 = zlnrat(renscale2,-s14)
         zl24 = zlnrat(renscale2,-s24)
         zl13 = zlnrat(renscale2,-s13)
         zl23 = zlnrat(renscale2,-s23)
         temp = (
     .        -        zl34
     .        -        zl12
     .        +1d0/2d0*zl14
     .        +1d0/2d0*zl13
     .        +1d0/2d0*zl24
     .        +1d0/2d0*zl23
     .        )*tree
      elseif (ieorder.eq.-2)then
         temp = 0d0
      endif

      Bhh2g1H = temp
      Bhh2g1H = Bhh2g1H*born

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> g g q qbar one-loop amplitudes.

      complex(8) function zB2g1Hmpppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpppcl,zA41cphiAQggmpmmcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpppcl =
     .     + zA41phiAQggmpppcl(permm(1))
     .     - zA41cphiAQggmpmmcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpppsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpppsl,zA41cphiAQggmpmmsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpppsl =
     .     + zA41phiAQggmpppsl(permm(1))
     .     - zA41cphiAQggmpmmsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpppnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpppnf,zA41cphiAQggmpmmnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)


      zB2g1Hmpppnf =
     .     + zA41phiAQggmpppnf(permm(1))
     .     - zA41cphiAQggmpmmnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmmcl,zA41cphiAQggmpppcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmmcl =
     .     + zA41phiAQggmpmmcl(permm(1),renscale2)
     .     - zA41cphiAQggmpppcl(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmmsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmmsl,zA41cphiAQggmpppsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmmsl =
     .     + zA41phiAQggmpmmsl(permm(1),renscale2)
     .     - zA41cphiAQggmpppsl(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmmnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmmnf,zA41cphiAQggmpppnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmmnf =
     .     + zA41phiAQggmpmmnf(permm(1),renscale2)
     .     - zA41cphiAQggmpppnf(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmpcl,zA41cphiAQggmpmpcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmpcl =
     .     + zA41phiAQggmpmpcl(permm(1),renscale2)
     .     - zA41cphiAQggmpmpcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmpsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmpsl,zA41cphiAQggmpmpsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmpsl =
     .     + zA41phiAQggmpmpsl(permm(1),renscale2)
     .     - zA41cphiAQggmpmpsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmpmpnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmpmpnf,zA41cphiAQggmpmpnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmpmpnf =
     .     + zA41phiAQggmpmpnf(permm(1),renscale2)
     .     - zA41cphiAQggmpmpnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmppmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmppmcl,zA41cphiAQggmppmcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmppmcl =
     .     + zA41phiAQggmppmcl(perm(1),renscale2)
     .     - zA41cphiAQggmppmcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmppmsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmppmsl,zA41cphiAQggmppmsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmppmsl =
     .     + zA41phiAQggmppmsl(perm(1),renscale2)
     .     - zA41cphiAQggmppmsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hmppmnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41phiAQggmppmnf,zA41cphiAQggmppmnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hmppmnf =
     .     + zA41phiAQggmppmnf(perm(1),renscale2)
     .     - zA41cphiAQggmppmnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpppcl,zA41phiAQggmpmmcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmmcl =
     .     - zA41cphiAQggmpppcl(permm(1))
     .     + zA41phiAQggmpmmcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmmsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpppsl,zA41phiAQggmpmmsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmmsl =
     .     - zA41cphiAQggmpppsl(permm(1))
     .     + zA41phiAQggmpmmsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmmnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpppnf,zA41phiAQggmpmmnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmmnf =
     .     - zA41cphiAQggmpppnf(permm(1))
     .     + zA41phiAQggmpmmnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmppcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmmcl,zA41phiAQggmpppcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmppcl =
     .     - zA41cphiAQggmpmmcl(permm(1),renscale2)
     .     + zA41phiAQggmpppcl(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmppsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmmsl,zA41phiAQggmpppsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmppsl =
     .     - zA41cphiAQggmpmmsl(permm(1),renscale2)
     .     + zA41phiAQggmpppsl(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmppnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmmnf,zA41phiAQggmpppnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmppnf =
     .     - zA41cphiAQggmpmmnf(permm(1),renscale2)
     .     + zA41phiAQggmpppnf(permmb(1))

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmpmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmpcl,zA41phiAQggmpmpcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmpmcl =
     .     - zA41cphiAQggmpmpcl(permm(1),renscale2)
     .     + zA41phiAQggmpmpcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmpmsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmpsl,zA41phiAQggmpmpsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmpmsl =
     .     - zA41cphiAQggmpmpsl(permm(1),renscale2)
     .     + zA41phiAQggmpmpsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmpmnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmpmpnf,zA41phiAQggmpmpnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmpmnf =
     .     - zA41cphiAQggmpmpnf(permm(1),renscale2)
     .     + zA41phiAQggmpmpnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmpcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmppmcl,zA41phiAQggmppmcl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmpcl =
     .     - zA41cphiAQggmppmcl(perm(1),renscale2)
     .     + zA41phiAQggmppmcl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmpsl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmppmsl,zA41phiAQggmppmsl

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmpsl =
     .     - zA41cphiAQggmppmsl(perm(1),renscale2)
     .     + zA41phiAQggmppmsl(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zB2g1Hpmmpnf(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4),permmb(4)
      complex(8), external :: zA41cphiAQggmppmnf,zA41phiAQggmppmnf

      permm(1) = perm(1)
      permm(2) = perm(2)
      permm(3) = perm(3)
      permm(4) = perm(4)

      permmb(1) = permm(2)
      permmb(2) = permm(1)
      permmb(3) = permm(4)
      permmb(4) = permm(3)

      zB2g1Hpmmpnf =
     .     - zA41cphiAQggmppmnf(perm(1),renscale2)
     .     + zA41phiAQggmppmnf(permmb(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hmppp(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43cphiAQggmpmm

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hmppp =
     .     - zA43cphiAQggmpmm(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hmpmm(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: zA43phiAQggmpmm

      zBt2g1Hmpmm = zA43phiAQggmpmm(perm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hmpmp(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43phiAQggmpmp,zA43cphiAQggmpmp

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hmpmp =
     .     + zA43phiAQggmpmp(perm(1),renscale2)
     .     - zA43cphiAQggmpmp(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hmppm(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43phiAQggmppm,zA43cphiAQggmppm

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hmppm =
     .     + zA43phiAQggmppm(perm(1),renscale2)
     .     - zA43cphiAQggmppm(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hpmmm(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43phiAQggmpmm

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hpmmm = zA43phiAQggmpmm(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hpmpp(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: zA43cphiAQggmpmm

      zBt2g1Hpmpp = -zA43cphiAQggmpmm(perm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hpmpm(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43cphiAQggmpmp,zA43phiAQggmpmp

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hpmpm =
     .     - zA43cphiAQggmpmp(perm(1),renscale2)
     .     + zA43phiAQggmpmp(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zBt2g1Hpmmp(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      integer              :: permm(4)
      complex(8), external :: zA43cphiAQggmppm,zA43phiAQggmppm

      permm(1) = perm(2)
      permm(2) = perm(1)
      permm(3) = perm(4)
      permm(4) = perm(3)

      zBt2g1Hpmmp =
     .     - zA43cphiAQggmppm(perm(1),renscale2)
     .     + zA43phiAQggmppm(permm(1),renscale2)

      return
      end

************************************************************************

      complex(8) function zA41phiAQggmpppcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1phiAQggmpppL
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41phiAQggmpppcl = 0d0
      elseif (ieorder.eq.-1)then
         zA41phiAQggmpppcl = 0d0
      elseif(ieorder.eq.0)then
         zA41phiAQggmpppcl = zA1phiAQggmpppL(perm(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA41phiAQggmpppsl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1phiAQggmpppR
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41phiAQggmpppsl = 0d0
      elseif (ieorder.eq.-1)then
         zA41phiAQggmpppsl = 0d0
      elseif (ieorder.eq.0)then
         zA41phiAQggmpppsl = zA1phiAQggmpppR(perm(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA41phiAQggmpppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1phiAQggmpppF
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41phiAQggmpppnf = 0d0
      elseif (ieorder.eq.-1)then
         zA41phiAQggmpppnf = 0d0
      elseif (ieorder.eq.0)then
         zA41phiAQggmpppnf = zA1phiAQggmpppF(perm(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA41cphiAQggmpppcl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1cphiAQggmpppL
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41cphiAQggmpppcl = 0d0
      elseif (ieorder.eq.-1)then
         zA41cphiAQggmpppcl = 0d0
      elseif (ieorder.eq.0)then
         zA41cphiAQggmpppcl = zA1cphiAQggmpppL(perm(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA41cphiAQggmpppsl(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1cphiAQggmpppR
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41cphiAQggmpppsl = 0d0
      elseif (ieorder.eq.-1)then
         zA41cphiAQggmpppsl = 0d0
      elseif (ieorder.eq.0)then
         zA41cphiAQggmpppsl = zA1cphiAQggmpppR(perm(1))
      endif

      return
      end

************************************************************************

      complex(8) function zA41cphiAQggmpppnf(perm)
      implicit none
      integer, intent(in)  :: perm(4)
      integer              :: ieorder
      complex(8), external :: zA1cphiAQggmpppF
      common/order/ieorder

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      if (ieorder.eq.-2)then
         zA41cphiAQggmpppnf = 0d0
      elseif (ieorder.eq.-1)then
         zA41cphiAQggmpppnf = 0d0
      elseif (ieorder.eq.0)then
         zA41cphiAQggmpppnf = zA1cphiAQggmpppF(perm(1))

      endif
      return
      end

************************************************************************

      complex(8) function zA41phiAQggmpmmcl(perm,renscale2)
      implicit none
      integer, intent(in)  :: perm(4)
      real(8), intent(in)  :: renscale2
      complex(8), external :: zA1phiAQggmpmmL

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      zA41phiAQggmpmmcl = zA1phiAQggmpmmL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmpmmsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmpmmR

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      zA41phiAQggmpmmsl=
     .     zA1phiAQggmpmmR(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmpmmnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmpmmF

c     Implementation of arXiv:0906.0008, Eq.(2.21).

      zA41phiAQggmpmmnf=
     .     +zA1phiAQggmpmmF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmmcl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmmL

c     Implementation of arXiv:0906.0008, Eq.(2.21).

      zA41cphiAQggmpmmcl=
     .     +zA1cphiAQggmpmmL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmmsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmmR

c     Implementation of arXiv:0906.0008, Eq.(2.21).

      zA41cphiAQggmpmmsl=
     .     zA1cphiAQggmpmmR(perm(1),renscale2)
      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmmnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmmF

c     Implementation of arXiv:0906.0008, Eq.(2.21).

      zA41cphiAQggmpmmnf=
     .     +zA1cphiAQggmpmmF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmpmpcl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmpmpL

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      zA41phiAQggmpmpcl=
     .     +zA1phiAQggmpmpL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmpmpsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmpmpR

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      zA41phiAQggmpmpsl=
     .     zA1phiAQggmpmpR(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmpmpnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmpmpF

c     Implementation of arXiv:0906.0008, Eq.(2.21).
      zA41phiAQggmpmpnf=
     .     +zA1phiAQggmpmpF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmpcl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmpL

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmpmpcl=
     .     +zA1cphiAQggmpmpL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmpsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmpR

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmpmpsl=
     .     zA1cphiAQggmpmpR(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmpmpnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmpmpF

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmpmpnf=
     .     +zA1cphiAQggmpmpF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmppmcl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmppmL

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41phiAQggmppmcl=
     .     +zA1phiAQggmppmL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmppmsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmppmR

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41phiAQggmppmsl=
     .     zA1phiAQggmppmR(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41phiAQggmppmnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1phiAQggmppmL,zA1phiAQggmppmF

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41phiAQggmppmnf=
     .     +zA1phiAQggmppmF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmppmcl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmppmL

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmppmcl=
     .     +zA1cphiAQggmppmL(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmppmsl(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmppmR

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmppmsl=
     .     zA1cphiAQggmppmR(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA41cphiAQggmppmnf(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer  perm(4)
      complex*16 zA1cphiAQggmppmL

c     Implementation of arXiv:0906.0008, Eq.(2.21)
      zA41cphiAQggmppmnf=
     .     +zA1cphiAQggmppmF(perm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43cphiAQggmpmm(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43cphiAQggmpmm=
     & +zA43cphiAQggmpmm_unsym(perm(1),renscale2)
     & +zA43cphiAQggmpmm_unsym(permm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43phiAQggmpmm(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43phiAQggmpmm=
     & +zA43phiAQggmpmm_unsym(perm(1),renscale2)
     & +zA43phiAQggmpmm_unsym(permm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43phiAQggmpmp(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43phiAQggmpmp=
     & +zA43phiAQggmpmp_unsym(perm(1),renscale2)
     & +zA43phiAQggmppm_unsym(permm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43cphiAQggmpmp(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43cphiAQggmpmp=
     & +zA43cphiAQggmpmp_unsym(perm(1),renscale2)
     & +zA43cphiAQggmppm_unsym(permm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43phiAQggmppm(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43phiAQggmppm=
     & +zA43phiAQggmppm_unsym(perm(1),renscale2)
     & +zA43phiAQggmpmp_unsym(permm(1),renscale2)

      return
      end

************************************************************************

      complex*16 function zA43cphiAQggmppm(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)

      permm(1)=perm(1)
      permm(2)=perm(2)
      permm(3)=perm(4)
      permm(4)=perm(3)

      zA43cphiAQggmppm=
     & +zA43cphiAQggmppm_unsym(perm(1),renscale2)
     & +zA43cphiAQggmpmp_unsym(permm(1),renscale2)

      return
      end

c-----------------------------------------------------------------------
c     Library for H -> g g q qbar one-loop sub-amplitudes with ieorder.

      complex*16 function zA1cphiAQggmpmmL(perm,renscale2)
c     This is an implementation of Eq. (5.2) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 V1L,zB2g0Hmmmp,lnrat,zba2,Lsm1,Lsm1_2mht,czip
      complex*16 sum,l23,l34,l41,l12,coef3m1234,coef3m1423,
     & S1,S2,K1DK2,a1,a2,a3,a4,gamma,gammap,gammam,factor,I3m,
     & BGRL1,BGRL2hat,BGRL3hat,d1,d2
      real*8 s123,s234,s124,s134,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34

      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s14)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1cphiAQggmpmmL=zB2g0Hpppm(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1cphiAQggmpmmL=zB2g0Hpppm(permm(1))*V1L
      elseif(ieorder.eq.0)then
      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)+119d0/18d0-deltar/6d0

      zA1cphiAQggmpmmL=zB2g0Hpppm(permm(1))*V1L
      sum=
     & -s134**2/(zb41*zb34*z2ba2143)
     & *Lsm1(-s14,-s134,-s34,-s134)

     & -z2ba1342**2/(z2ba1234*zb23*zb34)
     & *Lsm1(-s34,-s234,-s23,-s234)

     &  +(mhsq**2*za14**2*za24
     & /(za12*z2ba2143*z2ba4123*s124)
     &   -z2ba3142**3
     & /(zb12*zb24*z2ba3124*s124))
     & *Lsm1(-s14,-s124,-s12,-s124)

     & +(zb23**2*z2ba4231**3
     & /(zb12*zb13**3*z2ba4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ba1234*z2ba3124*s123))
     & *Lsm1(-s12,-s123,-s23,-s123)

     &   +za34*s134**2
     & /(zb34*za34*zb14*z2ba2143)
     & *Lsm1_2mht(s12,s134,s34,mhsq)

     & -z2ba1342**2
     & /(zb34*zb23*z2ba1234)
     & *Lsm1_2mht(s12,s234,s34,mhsq)

     & +(z2ba4132**3
     & /(zb12*zb23*z2ba4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ba1234*z2ba3124*s123))
     & *Lsm1_2mht(s34,s123,s12,mhsq)

     & +(mhsq**2*za14**2*za24
     & /(za12*z2ba2143*z2ba4123*s124)
     & -z2ba3241*z2ba3142**2
     & /(z2ba3124*zb14*zb12*s124))
     & *Lsm1_2mht(s34,s124,s12,mhsq)

     &  +(z2ba4132**3
     & /(zb12*zb23*z2ba4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ba1234*z2ba3124*s123))
     & *Lsm1_2mht(s14,s123,s23,mhsq)

     & +(mhsq**2*za24*za14**2
     & /(za12*z2ba2143*z2ba4123*s124)
     & -z2ba3142**2*z2ba3241
     & /(zb12*zb14*z2ba3124*s124))
     & *Lsm1_2mht(s23,s124,s14,mhsq)

c     Now for three mass triangles
c     Deal with the 12-34 case first
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p2)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p2)-gamma*((p3+p4))
C     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s12)
      K1DK2=dcmplx(s12+0.5d0*(s13+s14+s23+s24))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1234=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap
C -- calculate the projections of K1 flat on k1,k2,k3,k4 called a1,a2,a3,a4
      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a2=a1
      a3=-factor*gammap
      a4=a3

*XC rewrite (a1*s14+a2*s24+a3*s34)=d4K=d1 for better numerical stability in 3 soft limit
      d1=factor*s34*mhsq/gammam/(gammam-mhsq)
     .  *(mhsq*s12*s34/(s12-gammap)+gammam*(s13+s23+s34))
*XC rewrite (a1*s13+a2*s23+a4*s34)=d3K=d2 for better numerical stability in 4 soft limit
      d2=factor*s34*mhsq/gammam/(gammam-mhsq)
     .  *(mhsq*s12*s34/(s12-gammap)+gammam*(s14+s24+s34))

      coef3m1234=coef3m1234
     & +mhsq**2*za34**3/(za12*gammap*(gammap-mhsq))
     & *(a2*za12*zb23+a4*za14*zb43)   ! zab2(k1,k1f,k3)
     & *(a2*za12*zb24+a3*za13*zb34)   ! zab2(k1,k1f,k4)
     * /d2                                                ! (2*k3.k1f)^-1*
     * /d1

C     switch to other solution

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a2=a1
      a3=-factor*gammam
      a4=a3

*XC rewrite (a1*s14+a2*s24+a3*s34)=d4K=d1 for better numerical stability in 3 soft limit
      d1=factor*s34*mhsq/gammap/(gammap-mhsq)
     .  *(mhsq*s12*s34/(s12-gammam)+gammap*(s13+s23+s34))
*XC rewrite (a1*s13+a2*s23+a4*s34)=d3K=d2 for better numerical stability in 4 soft limit
      d2=factor*s34*mhsq/gammap/(gammap-mhsq)
     .  *(mhsq*s12*s34/(s12-gammam)+gammap*(s14+s24+s34))

      coef3m1234=coef3m1234
     & +mhsq**2*za34**3/(za12*gammam*(gammam-mhsq))
     & *(a2*za12*zb23+a4*za14*zb43)   ! zab2(k1,k1f,k3)
     & *(a2*za12*zb24+a3*za13*zb34)   ! zab2(k1,k1f,k4)
     * /d2                                                ! (2*k3.k1f)^-1*
     * /d1

c     Now deal with the 14-23 case
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p4)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p4)-gamma*((p2+p3))

C     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s14)
      K1DK2=dcmplx(s14+0.5d0*(s12+s13+s24+s34))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1423=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap

      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a4=a1
      a3=-factor*gammap
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammap/(gammam-mhsq)
     .  *(s23/(s14-gammap)+(s13+s23+s34)/gammap)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammam/(gammam-mhsq)
     .  *(-gammam*s23+(mhsq-gammam)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammap*(gammap-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a4=a1
      a3=-factor*gammam
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammam/(gammap-mhsq)
     .  *(s23/(s14-gammam)+(s13+s23+s34)/gammam)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammap/(gammap-mhsq)
     .  *(-gammap*s23+(mhsq-gammap)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammam*(gammam-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      sum=sum-coef3m1234*I3m(mhsq,s12,s34)
     .       -coef3m1423*I3m(mhsq,s14,s23)

      sum=sum
     & -2d0/3d0*za13**2*za34*z2ba4123*zb12
     & *BGRL3hat(s123,s12)

     & +1d0/6d0*za34*za13
     & *(z2ba4132*zb13-3d0*z2ba4231*zb23)
     & /zb13
     * *BGRL2hat(s123,s12)

     & +za13
     & *(0.5d0*z2ba4132*z2ba4123*zb12*zb13
     & -z2ba4231**2*zb23**2
     & -8d0/3d0*z2ba4132**2*zb13**2)
     & /(s123*zb13**2*zb23)
     & *BGRL1(s123,s12)

     & -2d0/3d0*s124*za34**2*za14*zb42
     & *BGRL3hat(s124,s12)

     & +za34*za14
     & *(1d0/3d0*z2ba3142*zb14
     * -0.5d0*z2ba3124*zb12)/zb14
     & *BGRL2hat(s124,s12)

     & +z2ba3142*(3d0/2d0*s124*za34
     & +11d0/3d0*z2ba3142*za42)/(s124*zb14)
     & *BGRL1(s124,s12)

     & +0.5d0*za14*za13*z2ba4231*zb12/zb31
     & *BGRL2hat(s123,s23)

     &-za13*z2ba4231*(3d0/2d0*z2ba4132*zb13
     &+z2ba4231*zb23)/(s123*zb13**2)
     & *BGRL1(s123,s23)

     & +0.5d0*s234*za14*za34*zb42/zb43
     & *BGRL2hat(s234,s23)

     & +3d0/2d0*za34*z2ba1342/zb43
     & *BGRL1(s234,s23)

      zA1cphiAQggmpmmL=zA1cphiAQggmpmmL+sum

c     Now add the rational pieces.
      sum=
     . za34*z2ba3142
     .  *(2d0*za24*zb42-za12*zb21)
     .  /(12d0*s124*za12*zb21*zb41)
     . +(za23*z2ba4132**2*(
     .    3d0*za12*zb21-2d0*za23*zb32)
     .  -2d0*za13**2*za24*z2ba4231
     .      *zb21*zb32)
     .  /(12d0*s123*za12*za23*zb21*zb31*zb32)
     . +5d0*za34**2/(12d0*za23*zb31)
     . +5d0*za34*z2ba4132
     .  /(6d0*za23*zb31*zb32)
     . +z2ba4132**2
     .  /(6d0*za12*zb21*zb31*zb32)
     . -za13*za14*za24*zb21
     .  /(3d0*za12*za23*zb31*zb32)
     . -za13*za34/(12d0*za12*zb41)
     . -za34**2*zb42/(6d0*za12*zb21*zb41)
     . +za13*za24*z2ba4134
     .  /(4d0*za12*za23*zb31*zb43)
     . -za13*z2ba4134/(3d0*za12*zb41*zb43)
     . -5d0*za14**2*zb41/(12d0*za12*zb31*zb43)
     . +za14**2*zb42/(6d0*za12*zb32*zb43)

      zA1cphiAQggmpmmL=zA1cphiAQggmpmmL+sum
      endif

      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpmmR(perm,renscale2)
c     This is an implementation of Eq. (5.10) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 VR,zB2g0Hmmmp,lnrat,zab2,Lsm1,Lsm1_2mht
      complex*16 sum,l12,coef3m1423,
     & S1,S2,K1DK2,a1,a2,a3,a4,gamma,factor,I3m,
     & BGRL1,BGRL2hat
      real*8 s123,s234,s124,s134,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34
      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1cphiAQggmpmmR=0d0!zB2g0Hpppm(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=-l12
     .   -3d0/2d0
      zA1cphiAQggmpmmR=0d0!zB2g0Hpppm(permm(1))*VR
      elseif(ieorder.eq.0)then
      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0

      zA1cphiAQggmpmmR=zB2g0Hpppm(permm(1))*VR
      sum=
     &  +zb12**2*z2ba4123**2/(zb13**3*zb23*s123)
     & *Lsm1(-s12,-s123,-s23,-s123)

     & +z2ba3142**2/(zb14*zb24*s124)
     & *Lsm1(-s14,-s124,-s12,-s124)

     & -z2ba1342**2/(zb23*zb34*z2ba1234)
     & *Lsm1_2mht(s14,s234,s23,mhsq)

     & +s134**2/(zb14*zb34*z2ba2143)
     & *Lsm1_2mht(s23,s134,s14,mhsq)

c     Now deal with the 14-23 case
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p4)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p4)-gamma*((p2+p3))

C     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s14)
      K1DK2=dcmplx(s14+0.5d0*(s12+s13+s24+s34))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1423=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap

      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a4=a1
      a3=-factor*gammap
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammap/(gammam-mhsq)
     .  *(s23/(s14-gammap)+(s13+s23+s34)/gammap)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammam/(gammam-mhsq)
     .  *(-gammam*s23+(mhsq-gammam)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammap*(gammap-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a4=a1
      a3=-factor*gammam
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammam/(gammap-mhsq)
     .  *(s23/(s14-gammam)+(s13+s23+s34)/gammam)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammap/(gammap-mhsq)
     .  *(-gammap*s23+(mhsq-gammap)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammam*(gammam-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      sum=sum-coef3m1423*I3m(mhsq,s14,s23)

      sum=sum
     & -0.5d0*(za14*zb12*z2ba3124)**2
     & /(zb14*zb24*s124)
     & *BGRL2hat(s124,s12)

     & +2d0*za34*z2ba3142/zb14
     & *BGRL1(s124,s12)

     & +0.5d0*z2ba3142**2/(zb14*zb24*s124)
     & *lnrat(-s124,-s12)

     & -0.5d0*(za14*zb24*s234)**2
     & /(zb23*zb34*z2ba1234)
     & *BGRL2hat(s234,s23)

     & -2d0*za34*z2ba1342/zb34
     & *BGRL1(s234,s23)

     & +0.5d0*z2ba1342**2
     & /(zb23*zb34*z2ba1234)
     & *lnrat(-s234,-s23)

     &-0.5d0*(za12*zb12*z2ba4231)**2*zb23
     & /(zb13**3*s123)
     & *BGRL2hat(s123,s23)

     & +2d0*za13*zb12*z2ba4123*z2ba4231
     & /(za23*zb13**2*zb23)
     & *BGRL1(s123,s23)

     & +(-2d0*za13*zb12*z2ba4123*z2ba4231
     & /(zb13**2*za23*zb23*s123)
     & +0.5d0*z2ba4231**2*zb23
     & /(zb13**3*s123))
     & *lnrat(-s123,-s23)

     & -0.5d0*(za13*zb12*z2ba4123)**2
     & /(zb13*zb23*s123)
     & *BGRL2hat(s123,s12)

     & +za34*zb12*z2ba4123
     & *(-2d0*za13*zb13-za23*zb23)
     & /(za23*zb13**2*zb23)
     & *BGRL1(s123,s12)

     & +zb12*z2ba4123
     & *(za23*z2ba4132+2d0*za13*z2ba4231)
     & /(zb13**2*za23*zb23*s123)
     & *lnrat(-s123,-s12)

      zA1cphiAQggmpmmR=zA1cphiAQggmpmmR+sum
c     now add the rational pieces
      sum=
     .-(za24**2*zb21**2)/(2d0*za23*zb31**3)
     .+(z2ba4123**2*zb21**2)
     .  /(2d0*s123*zb31**3*zb32)
     .-(za14**2*zb21)/(2*za12*zb31*zb32)
     .+(zb21*(za13**2*za23
     .  *z2ba4123**2*zb31**2
     .+za12**3*z2ba4231**2*zb21*zb32))
     .  /(4d0*s123**2*za12*za23*zb31**3*zb32)
     .+z2ba3142**2/(2d0*s124*zb41*zb42)
     .-(za13**2*zb21)/(2d0*za12*zb41*zb42)
     .+(za14**2*z2ba3124**2*zb21)
     .  /(4d0*s124**2*za12*zb41*zb42)
     .-(za13*za14*zb42)/(2d0*z2ba1234*zb43)
     .-(s234*za14**2*zb42**2)
     .  /(4d0*za23*z2ba1234*zb32**2*zb43)
     .-(za14**2*zb42**2)
     .  /(2d0*z2ba1234*zb32*zb43)

      zA1cphiAQggmpmmR=zA1cphiAQggmpmmR+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpmmF(perm,renscale2)
c     This is an implementation of Eq. (5.13) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 zB2g0Hmmmp,lnrat
      complex*16 l12,zab2,BGRL1,BGRL2hat,BGRL3hat
      real*8 s123,s124,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)

      s123=s12+s13+s23
      s124=s12+s14+s24

      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
          zA1cphiAQggmpmmF=0d0
      elseif(ieorder.eq.-1)then
          zA1cphiAQggmpmmF=0d0
      elseif(ieorder.eq.0)then
      zA1cphiAQggmpmmF=zB2g0Hpppm(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     & +2d0/3d0*za13*z2ba4132**2
     & /(za12*zb12*zb23*s123)*lnrat(-s123,-s12)
     & -2d0/3d0*(s24-s124)*z2ba3142**2
     & /(za12*zb14*zb24*zb12*s124)*lnrat(-s124,-s12)
     & -2d0/3d0*za13*z2ba4132**2
     & /(za12*zb23*zb12)*BGRL1(s123,s12)
     & +2d0/3d0*za14*z2ba3142**2
     & /(za12*zb24*zb12)*BGRL1(s124,s12)
     & +za13*za34*z2ba4132/3d0*BGRL2hat(s123,s12)
     & +za14*za34*z2ba3142/3d0*BGRL2hat(s124,s12)
     & +2d0/3d0*za13**2*za34*zb12*z2ba4123
     & *BGRL3hat(s123,s12)
     & +2d0/3d0*za14**2*za34*zb12*z2ba3124
     & *BGRL3hat(s124,s12)
      zA1cphiAQggmpmmF=zA1cphiAQggmpmmF
     & -za13*za34*z2ba4132
     & /(6d0*za12*zb12*s123)
     & -za14*za34*z2ba3142
     & /(6d0*za12*zb12*s124)
     & +(
     &  -za13*za14*zb12*zb34)
     & /(3d0*za12*zb12*zb34**2)
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpppL(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.16
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
      complex*16 zab2
      real*8 ss3,mhsq
*      write(*,*)'hello zA1phiAQggmpppL'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      mhsq=s12+s13+s14+s23+s24+s34

      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)
      z2ab3124=zab2(j3,j1,j2,j4)

      s123=ss3(j1,j2,j3)
      s412=ss3(j4,j1,j2)

      zA1phiAQggmpppL=
     . 0.5d0*za12*z2ab1342/(za23*za34*za41)
     . +0.5d0*za13*zb34/(za23*za34)
     . +2d0*z2ab1342**2/(za34*za41*z2ab3142)
     . -2d0*z2ab1234**2*z2ab2134
     . /(za12*za23*s123*z2ab3124)
     . -2d0*zb24**3*mhsq**2
     . /(zb12*s412*z2ab3124*z2ab3142)
     . -1d0/3d0*za13*zb34*za41/(za12*za34**2)

      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpppR(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.17
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
      complex*16 zab2
      real*8 ss3,mhsq
*      write(*,*)'hello zA1phiAQggmpppR'
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

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

      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)
      z2ab3124=zab2(j3,j1,j2,j4)

      zA1phiAQggmpppR=
     . -0.5d0*z2ab1234/(za23*za34)
     . -0.5d0*za12*zb23*za31
     .  /(za23*za34*za41)

      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpppF(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.18
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
*      write(*,*)'hello zA1phiAQggmpppF'
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

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

      zA1phiAQggmpppF=
     . +1d0/3d0*za13*zb34*za41/(za12*za34**2)

      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpppL(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.16
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
      real*8 ss3,mhsq
*      write(*,*)'hello zA1cphiAQggmpppL'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      mhsq=s12+s13+s14+s23+s24+s34

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)

      s123=ss3(j1,j2,j3)
      s412=ss3(j4,j1,j2)

      zA1cphiAQggmpppL=
     . 0.5d0*zb12*z2ba1342/(zb23*zb34*zb41)
     . +0.5d0*zb13*za34/(zb23*zb34)
     . +2d0*z2ba1342**2/(zb34*zb41*z2ba3142)
     . -2d0*z2ba1234**2*z2ba2134
     . /(zb12*zb23*s123*z2ba3124)
     . -2d0*za24**3*mhsq**2
     . /(za12*s412*z2ba3124*z2ba3142)
     . -1d0/3d0*zb13*za34*zb41/(zb12*zb34**2)

      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpppR(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.17
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
      real*8 ss3,mhsq
*      write(*,*)'hello zA1cphiAQggmpppR'
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

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

      z2ba1234=zba2(j1,j2,j3,j4)

      zA1cphiAQggmpppR=
     . -0.5d0*z2ba1234/(zb23*zb34)
     . -0.5d0*zb12*za23*zb31
     .  /(zb23*zb34*zb41)

      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpppF(perm)
C     implementation of arXiv:0906.0008v1, Eq. 4.18
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j1,j2,j3,j4,j5,j6,perm(4)
*      write(*,*)'hello zA1cphiAQggmpppF'
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

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

      zA1cphiAQggmpppF=
     . +1d0/3d0*zb13*za34*zb41/(zb12*zb34**2)

      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmmL(perm,renscale2)
c     This is an implementation of Eq. (5.2) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 V1L,zB2g0Hmmmp,lnrat,zab2,Lsm1,Lsm1_2mht,czip
      complex*16 sum,l23,l34,l41,l12,coef3m1234,coef3m1423,
     & S1,S2,K1DK2,a1,a2,a3,a4,gamma,gammap,gammam,factor,I3m,d1,d2,
     & BGRL1,BGRL2hat,BGRL3hat
      real*8 s123,s234,s124,s134,mhsq,epinv,deltar,musq
*      write(*,*)'hello zA1phiAQggmpmmL'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab4134=zab2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34

      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s14)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1phiAQggmpmmL=zB2g0Hmmmp(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1phiAQggmpmmL=zB2g0Hmmmp(permm(1))*V1L
      elseif(ieorder.eq.0)then

      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)+119d0/18d0-deltar/6d0

      zA1phiAQggmpmmL=zB2g0Hmmmp(permm(1))*V1L

      sum=
     & -s134**2/(zb41*zb34*z2ab2143)
     & *Lsm1(-s14,-s134,-s34,-s134)

     & -z2ab1342**2/(z2ab1234*zb23*zb34)
     & *Lsm1(-s34,-s234,-s23,-s234)

     &  +(mhsq**2*za14**2*za24
     & /(za12*z2ab2143*z2ab4123*s124)
     &   -z2ab3142**3
     & /(zb12*zb24*z2ab3124*s124))
     & *Lsm1(-s14,-s124,-s12,-s124)

     & +(zb23**2*z2ab4231**3
     & /(zb12*zb13**3*z2ab4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ab1234*z2ab3124*s123))
     & *Lsm1(-s12,-s123,-s23,-s123)

     &   +za34*s134**2
     & /(zb34*za34*zb14*z2ab2143)
     & *Lsm1_2mht(s12,s134,s34,mhsq)

     & -z2ab1342**2
     & /(zb34*zb23*z2ab1234)
     & *Lsm1_2mht(s12,s234,s34,mhsq)

     & +(z2ab4132**3
     & /(zb12*zb23*z2ab4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ab1234*z2ab3124*s123))
     & *Lsm1_2mht(s34,s123,s12,mhsq)

     & +(mhsq**2*za14**2*za24
     & /(za12*z2ab2143*z2ab4123*s124)
     & -z2ab3241*z2ab3142**2
     & /(z2ab3124*zb14*zb12*s124))
     & *Lsm1_2mht(s34,s124,s12,mhsq)

     &  +(z2ab4132**3
     & /(zb12*zb23*z2ab4123*s123)
     & -mhsq**2*za13**3
     & /(za12*z2ab1234*z2ab3124*s123))
     & *Lsm1_2mht(s14,s123,s23,mhsq)

     & +(mhsq**2*za24*za14**2
     & /(za12*z2ab2143*z2ab4123*s124)
     & -z2ab3142**2*z2ab3241
     & /(zb12*zb14*z2ab3124*s124))
     & *Lsm1_2mht(s23,s124,s14,mhsq)

c     Now for three mass triangles
c     Deal with the 12-34 case first
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p2)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p2)-gamma*((p3+p4))
C     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s12)
      K1DK2=dcmplx(s12+0.5d0*(s13+s14+s23+s24))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1234=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap
C -- calculate the projections of K1 flat on k1,k2,k3,k4 called a1,a2,a3,a4
      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a2=a1
      a3=-factor*gammap
      a4=a3

*XC rewrite (a1*s14+a2*s24+a3*s34)=d4K=d1 for better numerical stability in 3 soft limit
      d1=factor*s34*mhsq/gammam/(gammam-mhsq)
     .  *(mhsq*s12*s34/(s12-gammap)+gammam*(s13+s23+s34))
*XC rewrite (a1*s13+a2*s23+a4*s34)=d3K=d2 for better numerical stability in 4 soft limit
      d2=factor*s34*mhsq/gammam/(gammam-mhsq)
     .  *(mhsq*s12*s34/(s12-gammap)+gammam*(s14+s24+s34))

      coef3m1234=coef3m1234
     & +mhsq**2*za34**3/(za12*gammap*(gammap-mhsq))
     & *(a2*za12*zb23+a4*za14*zb43)   ! zab2(k1,k1f,k3)
     & *(a2*za12*zb24+a3*za13*zb34)   ! zab2(k1,k1f,k4)
     * /d2                                                ! (2*k3.k1f)^-1*
     * /d1
C     switch to other solution

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a2=a1
      a3=-factor*gammam
      a4=a3

*XC rewrite (a1*s14+a2*s24+a3*s34)=d4K=d1 for better numerical stability in 3 soft limit
      d1=factor*s34*mhsq/gammap/(gammap-mhsq)
     .  *(mhsq*s12*s34/(s12-gammam)+gammap*(s13+s23+s34))
*XC rewrite (a1*s13+a2*s23+a4*s34)=d3K=d2 for better numerical stability in 4 soft limit
      d2=factor*s34*mhsq/gammap/(gammap-mhsq)
     .  *(mhsq*s12*s34/(s12-gammam)+gammap*(s14+s24+s34))

      coef3m1234=coef3m1234
     & +mhsq**2*za34**3/(za12*gammam*(gammam-mhsq))
     & *(a2*za12*zb23+a4*za14*zb43)   ! zab2(k1,k1f,k3)
     & *(a2*za12*zb24+a3*za13*zb34)   ! zab2(k1,k1f,k4)
     * /d2                                                ! (2*k3.k1f)^-1*
     * /d1

c     Now deal with the 14-23 case
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p4)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p4)-gamma*((p2+p3))

C     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s14)
      K1DK2=dcmplx(s14+0.5d0*(s12+s13+s24+s34))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1423=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap

      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a4=a1
      a3=-factor*gammap
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammap/(gammam-mhsq)
     .  *(s23/(s14-gammap)+(s13+s23+s34)/gammap)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammam/(gammam-mhsq)
     .  *(-gammam*s23+(mhsq-gammam)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammap*(gammap-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a4=a1
      a3=-factor*gammam
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammam/(gammap-mhsq)
     .  *(s23/(s14-gammam)+(s13+s23+s34)/gammam)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammap/(gammap-mhsq)
     .  *(-gammap*s23+(mhsq-gammap)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammam*(gammam-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      sum=sum-coef3m1234*I3m(mhsq,s12,s34)
     .       -coef3m1423*I3m(mhsq,s14,s23)

      sum=sum
     & -2d0/3d0*za13**2*za34*z2ab4123*zb12
     & *BGRL3hat(s123,s12)

     & +1d0/6d0*za34*za13
     & *(z2ab4132*zb13-3d0*z2ab4231*zb23)
     & /zb13
     * *BGRL2hat(s123,s12)

     & +za13
     & *(0.5d0*z2ab4132*z2ab4123*zb12*zb13
     & -z2ab4231**2*zb23**2
     & -8d0/3d0*z2ab4132**2*zb13**2)
     & /(s123*zb13**2*zb23)
     & *BGRL1(s123,s12)

     & -2d0/3d0*s124*za34**2*za14*zb42
     & *BGRL3hat(s124,s12)

     & +za34*za14
     & *(1d0/3d0*z2ab3142*zb14
     * -0.5d0*z2ab3124*zb12)/zb14
     & *BGRL2hat(s124,s12)

     & +z2ab3142*(3d0/2d0*s124*za34
     & +11d0/3d0*z2ab3142*za42)/(s124*zb14)
     & *BGRL1(s124,s12)

     & +0.5d0*za14*za13*z2ab4231*zb12/zb31
     & *BGRL2hat(s123,s23)

     &-za13*z2ab4231*(3d0/2d0*z2ab4132*zb13
     &+z2ab4231*zb23)/(s123*zb13**2)
     & *BGRL1(s123,s23)

     & +0.5d0*s234*za14*za34*zb42/zb43
     & *BGRL2hat(s234,s23)

     & +3d0/2d0*za34*z2ab1342/zb43
     & *BGRL1(s234,s23)

      zA1phiAQggmpmmL=zA1phiAQggmpmmL+sum

c     now add the rational pieces
      sum=
     . za34*z2ab3142
     .  *(2d0*za24*zb42-za12*zb21)
     .  /(12d0*s124*za12*zb21*zb41)
     . +(za23*z2ab4132**2*(
     .    3d0*za12*zb21-2d0*za23*zb32)
     .  -2d0*za13**2*za24*z2ab4231
     .      *zb21*zb32)
     .  /(12d0*s123*za12*za23*zb21*zb31*zb32)
     . +5d0*za34**2/(12d0*za23*zb31)
     . +5d0*za34*z2ab4132
     .  /(6d0*za23*zb31*zb32)
     . +z2ab4132**2
     .  /(6d0*za12*zb21*zb31*zb32)
     . -za13*za14*za24*zb21
     .  /(3d0*za12*za23*zb31*zb32)
     . -za13*za34/(12d0*za12*zb41)
     . -za34**2*zb42/(6d0*za12*zb21*zb41)
     . +za13*za24*z2ab4134
     .  /(4d0*za12*za23*zb31*zb43)
     . -za13*z2ab4134/(3d0*za12*zb41*zb43)
     . -5d0*za14**2*zb41/(12d0*za12*zb31*zb43)
     . +za14**2*zb42/(6d0*za12*zb32*zb43)

      zA1phiAQggmpmmL=zA1phiAQggmpmmL+sum

      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmmR(perm,renscale2)
c     This is an implementation of Eq. (5.10) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 VR,zB2g0Hmmmp,lnrat,zab2,Lsm1,Lsm1_2mht
      complex*16 sum,l12,coef3m1423,
     & S1,S2,K1DK2,a1,a2,a3,a4,gamma,factor,I3m,
     & BGRL1,BGRL2hat
      real*8 s123,s234,s124,s134,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab4134=zab2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      s123=s12+s13+s23
      s124=s12+s14+s24
      s134=s13+s14+s34
      s234=s23+s24+s34
      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1phiAQggmpmmR=0d0!zB2g0Hmmmp(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=
     . -l12
     . -3d0/2d0
      zA1phiAQggmpmmR=0d0!zB2g0Hmmmp(permm(1))*VR
      elseif(ieorder.eq.0)then
      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0

      zA1phiAQggmpmmR=zB2g0Hmmmp(permm(1))*VR
      sum=
     &  +zb12**2*z2ab4123**2/(zb13**3*zb23*s123)
     & *Lsm1(-s12,-s123,-s23,-s123)

     & +z2ab3142**2/(zb14*zb24*s124)
     & *Lsm1(-s14,-s124,-s12,-s124)

     & -z2ab1342**2/(zb23*zb34*z2ab1234)
     & *Lsm1_2mht(s14,s234,s23,mhsq)

     & +s134**2/(zb14*zb34*z2ab2143)
     & *Lsm1_2mht(s23,s134,s14,mhsq)

c     Now deal with the 14-23 case
c     K1=-(p1+p2+p3+p4)
c     K2=-(p1+p4)
C     K1flat=gamma/(gamma**2-S1*S2)*(gamma*K1-S1*K2)
C     K1flat=gamma/(gamma**2-S1*S2)*((S1-gamma)*(p1+p4)-gamma*((p2+p3))

c     solve for gamma_+ and gamma_-
      S1=dcmplx(mhsq)
      S2=dcmplx(s14)
      K1DK2=dcmplx(s14+0.5d0*(s12+s13+s24+s34))

C-gamma+ = K1DK2+sqrt(K1DK2**2-S1*S2)
C-gamma- = K1DK2-sqrt(K1DK2**2-S1*S2)

      coef3m1423=czip
      gammap=K1DK2+sqrt(K1DK2**2-S1*S2)
      gammam=2d0*K1DK2-gammap

      factor=gammap/(gammap**2-S1*S2)
      a1=factor*(S1-gammap)
      a4=a1
      a3=-factor*gammap
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammap/(gammam-mhsq)
     .  *(s23/(s14-gammap)+(s13+s23+s34)/gammap)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammam/(gammam-mhsq)
     .  *(-gammam*s23+(mhsq-gammam)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammap*(gammap-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      factor=gammam/(gammam**2-S1*S2)
      a1=factor*(S1-gammam)
      a4=a1
      a3=-factor*gammam
      a2=a3

*XC rewrite (a1*s12+a3*s23+a4*s24)=d2K=d1 for better numerical stability in 3 soft limit
      d1=factor*s23*mhsq*gammam/(gammap-mhsq)
     .  *(s23/(s14-gammam)+(s13+s23+s34)/gammam)
*XC rewrite (a2*s12+a3*s13+a4*s14)=d1K=d2 for better numerical stability in 4 soft limit
      d2=factor*s14*mhsq/gammap/(gammap-mhsq)
     .  *(-gammap*s23+(mhsq-gammap)*(s12+s13))

      coef3m1423=coef3m1423
     &  -mhsq**2*za14**2/(2d0*gammam*(gammam-mhsq))
     & *(a2*za32*zb21+a4*za34*zb41)   ! *zab2(k3,k1f,k1)
     & *(a1*za31*zb12+a4*za34*zb42)   ! *zab2(k3,k1f,k2)
     * /d2                                                ! (2*k1.k1f)^-1*
     * /d1                                                ! (2*k2.k1f)^-1*

      sum=sum-coef3m1423*I3m(mhsq,s14,s23)

      sum=sum
     & -0.5d0*(za14*zb12*z2ab3124)**2
     & /(zb14*zb24*s124)
     & *BGRL2hat(s124,s12)

     & +2d0*za34*z2ab3142/zb14
     & *BGRL1(s124,s12)

     & +0.5d0*z2ab3142**2/(zb14*zb24*s124)
     & *lnrat(-s124,-s12)

     & -0.5d0*(za14*zb24*s234)**2
     & /(zb23*zb34*z2ab1234)
     & *BGRL2hat(s234,s23)

     & -2d0*za34*z2ab1342/zb34
     & *BGRL1(s234,s23)

     & +0.5d0*z2ab1342**2
     & /(zb23*zb34*z2ab1234)
     & *lnrat(-s234,-s23)

     &-0.5d0*(za12*zb12*z2ab4231)**2*zb23
     & /(zb13**3*s123)
     & *BGRL2hat(s123,s23)

     & +2d0*za13*zb12*z2ab4123*z2ab4231
     & /(za23*zb13**2*zb23)
     & *BGRL1(s123,s23)

     & +(-2d0*za13*zb12*z2ab4123*z2ab4231
     & /(zb13**2*za23*zb23*s123)
     & +0.5d0*z2ab4231**2*zb23
     & /(zb13**3*s123))
     & *lnrat(-s123,-s23)

     & -0.5d0*(za13*zb12*z2ab4123)**2
     & /(zb13*zb23*s123)
     & *BGRL2hat(s123,s12)

     & +za34*zb12*z2ab4123
     & *(-2d0*za13*zb13-za23*zb23)
     & /(za23*zb13**2*zb23)
     & *BGRL1(s123,s12)

     & +zb12*z2ab4123
     & *(za23*z2ab4132+2d0*za13*z2ab4231)
     & /(zb13**2*za23*zb23*s123)
     & *lnrat(-s123,-s12)
      zA1phiAQggmpmmR=zA1phiAQggmpmmR+sum
c     now add the rational pieces
      sum=
     .-(za24**2*zb21**2)/(2d0*za23*zb31**3)
     .+(z2ab4123**2*zb21**2)
     .  /(2d0*s123*zb31**3*zb32)
     .-(za14**2*zb21)/(2*za12*zb31*zb32)
     .+(zb21*(za13**2*za23
     .  *z2ab4123**2*zb31**2
     .+za12**3*z2ab4231**2*zb21*zb32))
     .  /(4d0*s123**2*za12*za23*zb31**3*zb32)
     .+z2ab3142**2/(2d0*s124*zb41*zb42)
     .-(za13**2*zb21)/(2d0*za12*zb41*zb42)
     .+(za14**2*z2ab3124**2*zb21)
     .  /(4d0*s124**2*za12*zb41*zb42)
     .-(za13*za14*zb42)/(2d0*z2ab1234*zb43)
     .-(s234*za14**2*zb42**2)
     .  /(4d0*za23*z2ab1234*zb32**2*zb43)
     .-(za14**2*zb42**2)
     .  /(2d0*z2ab1234*zb32*zb43)

      zA1phiAQggmpmmR=zA1phiAQggmpmmR+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmmF(perm,renscale2)
c     This is an implementation of Eq. (5.13) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 zB2g0Hmmmp,lnrat
      complex*16 l12,zab2,BGRL1,BGRL2hat,BGRL3hat
      real*8 s123,s124,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab4134=zab2(j4,j1,j3,j4)

      s123=s12+s13+s23
      s124=s12+s14+s24

      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      zA1phiAQggmpmmF=0d0
      elseif(ieorder.eq.-1)then
      zA1phiAQggmpmmF=0d0
      elseif(ieorder.eq.0)then
      zA1phiAQggmpmmF=zB2g0Hmmmp(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     & +2d0/3d0*za13*z2ab4132**2
     & /(za12*zb12*zb23*s123)*lnrat(-s123,-s12)
     & -2d0/3d0*(s24-s124)*z2ab3142**2
     & /(za12*zb14*zb24*zb12*s124)*lnrat(-s124,-s12)
     & -2d0/3d0*za13*z2ab4132**2
     & /(za12*zb23*zb12)*BGRL1(s123,s12)
     & +2d0/3d0*za14*z2ab3142**2
     & /(za12*zb24*zb12)*BGRL1(s124,s12)
     & +za13*za34*z2ab4132/3d0*BGRL2hat(s123,s12)
     & +za14*za34*z2ab3142/3d0*BGRL2hat(s124,s12)
     & +2d0/3d0*za13**2*za34*zb12*z2ab4123
     & *BGRL3hat(s123,s12)
     & +2d0/3d0*za14**2*za34*zb12*z2ab3124
     & *BGRL3hat(s124,s12)
      zA1phiAQggmpmmF=zA1phiAQggmpmmF
     & -za13*za34*z2ab4132
     & /(6d0*za12*zb12*s123)
     & -za14*za34*z2ab3142
     & /(6d0*za12*zb12*s124)
     & +(
     &  -za13*za14*zb12*zb34)
     & /(3d0*za12*zb12*zb34**2)
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmpL(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.24
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 zab2,V1L,L2,L1,L0,lnrat,sum,
     . zAphiq2gqmpmp
      complex*16 l23,l34,l41,l12,Lsm1_2me,Lsm1DS
      real*8 ss3,mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
*      write(*,*)'hello zA1phiAQggmpmpL'

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab4134=zab2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s41)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1phiAQggmpmpL=zAphiq2gqmpmp(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1phiAQggmpmpL=zAphiq2gqmpmp(permm(1))*V1L
      elseif(ieorder.eq.0)then
      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)
     . +119d0/18d0-deltar/6d0
     . -Lsm1_2me(s123,s234,s23,mhsq)
     . -Lsm1_2me(s341,s412,s41,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)

      zA1phiAQggmpmpL=zAphiq2gqmpmp(permm(1))
     . *(V1L-13d0/6d0*lnrat(-s412,-s12)
     .      -Lsm1DS(s34,s41,s341)
     .      -Lsm1DS(s12,s23,s123))

      sum=
     . +za14**2*za23**3/(za12*za34*za24**3)
     .  *(Lsm1DS(s23,s34,s234)+Lsm1DS(s41,s12,s412))
     . +2d0/3d0*za12**2*za34**2*zb24**3/za14
     .  *L2(-s412,-s12)/s12**3
     . -0.5d0*za12*za23*za34*zb24**2/za24
     .  *L1(-s234,-s34)/s34**2
     . +(0.5d0*za14*z2ab3124**2/za24
     .  -1d0/3d0*za13*za14*z2ab3124**2
     .          /(za12*za34)
     .  -2d0/3d0*za13*za12*za34*zb24**2/za14)
     .  *L1(-s412,-s12)/s12**2
     . -(za12*zb24*z2ab3142**2/(za14*zb12)
     .  +0.5d0*za14*za23**2*zb24**2/za24)
     .  *L1(-s412,-s41)/s41**2
     . -(zb24*za34*z2ab1234**2/(za14*zb34)
     .  +0.5d0*za14*za23**2*zb24**2/za24)
     .  *L1(-s234,-s23)/s23**2
     . +(3d0*za13**2*z2ab3124/(za12*za34)
     .  +2d0*za13*z2ab3124**2
     .      /(za12*za34*zb14)
     .  +1d0/3d0*za13**2*zb24/za14
     .  -z2ab3124**2/(zb14*za24))
     .  *L0(-s412,-s12)/s12
     . +3d0*za23*za13*zb24/za24
     .  *(L0(-s234,-s23)/s23+L0(-s412,-s41)/s41)
     . +za23*zb24*(za12*za34
     .                      +2d0*za14*za23)/za24**2
     .  *L0(-s234,-s34)/s34
     . -(1d0/3d0*za13**3/(za12*za34*za14)
     .  +0.5d0*za23*za13**2/(za12*za24*za34)
     .  +za23**2*zb24/(za24**2*zb14)
     .  +2d0*za23**3*za14*zb24
     .      /(za24**2*za34*za12*zb14))
     .  *lnrat(-s412,-s12)
     . +za12**2*za34*zb24
     .  /(za24**2*za14*zb34)*lnrat(-s234,-s23)
     . +za34**2*za12*zb24
     .  /(za24**2*za14*zb12)*lnrat(-s412,-s41)
     . -5d0/6d0*za13**2*zb24/(s12*za14)
     . -1d0/3d0*za13**2*z2ab3124
     .  /(s12*za12*za34)
     . -1d0/3d0*za13*zb24
     .  *(2d0*za34*zb42+za31*zb12)
     .  /(s412*za14*zb12)
     . +0.5d0*(
     .  zb24*z2ab3124*z2ab3241
     .  /(s412*zb14*zb12*za24)
     . -za13**2*zb14/(s12*za24)
     . -za13*zb24*za34/(za14*zb12*za24)
     . +za12*zb24**2/(zb23*zb34*za24) )
     . +za13*zb24*z2ab1234
     .  /(s23*za14*zb34)
     . -za13*zb24*z2ab3142
     .  /(s41*za14*zb12)
     . -zb24**2*za34*za23
     .  /(s41*za24*zb12)
     . -2d0*zAcphiq2gqmpmp(permm(1))

      zA1phiAQggmpmpL=zA1phiAQggmpmpL+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmpR(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.25
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 zab2,VR,Lsm1_2me,lnrat,l12,L0,L1,
     & Lsm1DS
      real*8 ss3,mhsq,s341,s234,s412,epinv,deltar,musq
*      write(*,*)'hello zA1phiAQggmpmpR'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab4134=zab2(j4,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      s341=ss3(j3,j4,j1)
      s234=ss3(j2,j3,j4)
      s412=ss3(j4,j1,j2)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1phiAQggmpmpR=0d0!zAphiq2gqmpmp(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=-l12
     .   -3d0/2d0
      zA1phiAQggmpmpR=0d0!zAphiq2gqmpmp(permm(1))*VR
      elseif(ieorder.eq.0)then
      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0
     .   -Lsm1_2me(s234,s341,s34,mhsq)
      zA1phiAQggmpmpR=
     . +za12**2*za34**2/(za14*za24**3)
     . *(Lsm1DS(s23,s34,s234)+Lsm1DS(s41,s12,s412))
     . -0.5d0*za12**2*za34**2*zb24**2
     .       /(za14*za24)*L1(-s412,-s12)/s12**2
     . +zb24*za34*z2ab1234**2/(za14*zb34)
     .       *L1(-s234,-s23)/s23**2
     . -(za12*za34*zb24**3/zb23
     .  +0.5d0*za23**3*z2ab1342**2
     .       /(za12*za34*za24))
     .  *L1(-s234,-s34)/s34**2
     . -0.5d0*za14*za23**2*zb24**2/za24
     .       *(L1(-s412,-s41)/s41**2
     .        -L1(-s234,-s23)/s23**2)
     . -za12**2*za34**2*zb24/(za14*za24**2)
     .       *L0(-s412,-s12)/s12
     . +za23*zb24*(
     .  2d0*za12*za34+za14*za23)/(za24**2)
     .       *L0(-s412,-s41)/s41
     . -za12**2*za34*zb24
     .  /(za24**2*za14*zb34)*lnrat(-s234,-s23)
     . +(za34*za12*zb24/(za24**2*zb23)
     .  +0.5d0*za23*za13**2/(za12*za24*za34))
     .       *lnrat(-s234,-s34)
     . -0.5d0*zb24*z2ab3124*z2ab3142
     .  /(s41*s412*zb12)
     . -0.5d0*zb24**2*za34*za23
     .  /(s41*za24*zb12)
     . -0.5d0*(za13*za23**2*z2ab1342)
     .  /(s34*za34*za12*za24)
     . +0.5d0*za23*zb24*z2ab1342*(s23+s34)
     .  /(s34*s234*zb23*za24)
     . +0.5d0*zb24**2*z2ab1234/(s234*zb23*zb34)
     . -za12*zb24*za34*z2ab1234
     .  /(s23*za14*zb34*za24)
     . +za13*zb24/(zb23*za24)

      zA1phiAQggmpmpR=zA1phiAQggmpmpR
     .             +zAphiq2gqmpmp(permm(1))*VR
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmpmpF(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.26
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 l12,zab2,L2,lnrat,zAphiq2gqmpmp
      real*8 s412,mhsq,epinv,deltar,musq
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

*      write(*,*)'hello zA1phiAQggmpmpF'
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s412=s41+s42+s12
      l12=lnrat(musq,-s12)

      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab3142=zab2(j3,j1,j4,j2)

      if(ieorder.eq.-2)then
      zA1phiAQggmpmpF=0d0
      elseif(ieorder.eq.-1)then
      zA1phiAQggmpmpF=0d0
      elseif(ieorder.eq.0)then
      zA1phiAQggmpmpF=zAphiq2gqmpmp(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     .-1d0/3d0*(za14**2*z2ab3124**3/(za12*za34)
     .         +za12**2*zb24**3*za34**2/za14)
     .        *L2(-s412,-s12)/s12**3
     .+1d0/3d0*zAphiq2gqmpmp(permm(1))*lnrat(-s412,-s12)
     .+0.5d0*za13**2*zb24/(s12*za14)
     .+1d0/6d0*za13*(za31*zb12*z2ab3142
     .                   -(za34*zb42)**2)
     .                  /(zb12*za34*za14*s412)
     .+1d0/6d0*za13**3*s412
     .        /(s12*za12*za34*za14)
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpmpL(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.24
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V1L,L2,L1,L0,lnrat,sum,
     . zAphiq2gqmpmp
      complex*16 l23,l34,l41,l12,Lsm1_2me,Lsm1DS
      real*8 ss3,mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
*      write(*,*)'hello zA1cphiAQggmpmpL'

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s41)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1cphiAQggmpmpL=zAphiq2gqpmpm(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1cphiAQggmpmpL=zAphiq2gqpmpm(permm(1))*V1L
      elseif(ieorder.eq.0)then
      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)
     . +119d0/18d0-deltar/6d0
     . -Lsm1_2me(s123,s234,s23,mhsq)
     . -Lsm1_2me(s341,s412,s41,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)

      zA1cphiAQggmpmpL=zAphiq2gqpmpm(permm(1))
     . *(V1L-13d0/6d0*lnrat(-s412,-s12)
     .      -Lsm1DS(s34,s41,s341)
     .      -Lsm1DS(s12,s23,s123))

      sum=
     . +za14**2*za23**3/(za12*za34*za24**3)
     .  *(Lsm1DS(s23,s34,s234)+Lsm1DS(s41,s12,s412))
     . +2d0/3d0*za12**2*za34**2*zb24**3/za14
     .  *L2(-s412,-s12)/s12**3
     . -0.5d0*za12*za23*za34*zb24**2/za24
     .  *L1(-s234,-s34)/s34**2
     . +(0.5d0*za14*z2ba3124**2/za24
     .  -1d0/3d0*za13*za14*z2ba3124**2
     .          /(za12*za34)
     .  -2d0/3d0*za13*za12*za34*zb24**2/za14)
     .  *L1(-s412,-s12)/s12**2
     . -(za12*zb24*z2ba3142**2/(za14*zb12)
     .  +0.5d0*za14*za23**2*zb24**2/za24)
     .  *L1(-s412,-s41)/s41**2
     . -(zb24*za34*z2ba1234**2/(za14*zb34)
     .  +0.5d0*za14*za23**2*zb24**2/za24)
     .  *L1(-s234,-s23)/s23**2
     . +(3d0*za13**2*z2ba3124/(za12*za34)
     .  +2d0*za13*z2ba3124**2
     .      /(za12*za34*zb14)
     .  +1d0/3d0*za13**2*zb24/za14
     .  -z2ba3124**2/(zb14*za24))
     .  *L0(-s412,-s12)/s12
     . +3d0*za23*za13*zb24/za24
     .  *(L0(-s234,-s23)/s23+L0(-s412,-s41)/s41)
     . +za23*zb24*(za12*za34
     .                      +2d0*za14*za23)/za24**2
     .  *L0(-s234,-s34)/s34
     . -(1d0/3d0*za13**3/(za12*za34*za14)
     .  +0.5d0*za23*za13**2/(za12*za24*za34)
     .  +za23**2*zb24/(za24**2*zb14)
     .  +2d0*za23**3*za14*zb24
     .      /(za24**2*za34*za12*zb14))
     .  *lnrat(-s412,-s12)
     . +za12**2*za34*zb24
     .  /(za24**2*za14*zb34)*lnrat(-s234,-s23)
     . +za34**2*za12*zb24
     .  /(za24**2*za14*zb12)*lnrat(-s412,-s41)
     . -5d0/6d0*za13**2*zb24/(s12*za14)
     . -1d0/3d0*za13**2*z2ba3124
     .  /(s12*za12*za34)
     . -1d0/3d0*za13*zb24
     .  *(2d0*za34*zb42+za31*zb12)
     .  /(s412*za14*zb12)
     . +0.5d0*(
     .  zb24*z2ba3124*z2ba3241
     .  /(s412*zb14*zb12*za24)
     . -za13**2*zb14/(s12*za24)
     . -za13*zb24*za34/(za14*zb12*za24)
     . +za12*zb24**2/(zb23*zb34*za24) )
     . +za13*zb24*z2ba1234
     .  /(s23*za14*zb34)
     . -za13*zb24*z2ba3142
     .  /(s41*za14*zb12)
     . -zb24**2*za34*za23
     .  /(s41*za24*zb12)
     . -2d0*zAcphiq2gqpmpm(permm(1))

      zA1cphiAQggmpmpL=zA1cphiAQggmpmpL+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpmpR(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.25
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 VR,Lsm1_2me,lnrat,l12,L0,L1,
     & Lsm1DS
      real*8 ss3,mhsq,s341,s234,s412,epinv,deltar,musq
*      write(*,*)'hello zA1cphiAQggmpmpR'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      s341=ss3(j3,j4,j1)
      s234=ss3(j2,j3,j4)
      s412=ss3(j4,j1,j2)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1cphiAQggmpmpR=0d0!zAphiq2gqpmpm(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=-l12
     .   -3d0/2d0
      zA1cphiAQggmpmpR=0d0!zAphiq2gqpmpm(permm(1))*VR
      elseif(ieorder.eq.0)then
      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0
     .   -Lsm1_2me(s234,s341,s34,mhsq)
      zA1cphiAQggmpmpR=
     . +za12**2*za34**2/(za14*za24**3)
     . *(Lsm1DS(s23,s34,s234)+Lsm1DS(s41,s12,s412))
     . -0.5d0*za12**2*za34**2*zb24**2
     .       /(za14*za24)*L1(-s412,-s12)/s12**2
     . +zb24*za34*z2ba1234**2/(za14*zb34)
     .       *L1(-s234,-s23)/s23**2
     . -(za12*za34*zb24**3/zb23
     .  +0.5d0*za23**3*z2ba1342**2
     .       /(za12*za34*za24))
     .  *L1(-s234,-s34)/s34**2
     . -0.5d0*za14*za23**2*zb24**2/za24
     .       *(L1(-s412,-s41)/s41**2
     .        -L1(-s234,-s23)/s23**2)
     . -za12**2*za34**2*zb24/(za14*za24**2)
     .       *L0(-s412,-s12)/s12
     . +za23*zb24*(
     .  2d0*za12*za34+za14*za23)/(za24**2)
     .       *L0(-s412,-s41)/s41
     . -za12**2*za34*zb24
     .  /(za24**2*za14*zb34)*lnrat(-s234,-s23)
     . +(za34*za12*zb24/(za24**2*zb23)
     .  +0.5d0*za23*za13**2/(za12*za24*za34))
     .       *lnrat(-s234,-s34)
     . -0.5d0*zb24*z2ba3124*z2ba3142
     .  /(s41*s412*zb12)
     . -0.5d0*zb24**2*za34*za23
     .  /(s41*za24*zb12)
     . -0.5d0*(za13*za23**2*z2ba1342)
     .  /(s34*za34*za12*za24)
     . +0.5d0*za23*zb24*z2ba1342*(s23+s34)
     .  /(s34*s234*zb23*za24)
     . +0.5d0*zb24**2*z2ba1234/(s234*zb23*zb34)
     . -za12*zb24*za34*z2ba1234
     .  /(s23*za14*zb34*za24)
     . +za13*zb24/(zb23*za24)

      zA1cphiAQggmpmpR=zA1cphiAQggmpmpR
     .             +zAphiq2gqpmpm(permm(1))*VR
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmpmpF(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.26
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      complex*16 l12,zab2,L2,lnrat,zAphiq2gqmpmp
      real*8 s412,mhsq,epinv,deltar,musq
*      write(*,*)'hello zA1phiAQggmpmmF'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)

      s412=s41+s42+s12
      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      zA1cphiAQggmpmpF=0d0
      elseif(ieorder.eq.-1)then
      zA1cphiAQggmpmpF=0d0
      elseif(ieorder.eq.0)then

      zA1cphiAQggmpmpF=zAphiq2gqpmpm(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     .-1d0/3d0*(zb14**2*z2ba3124**3/(zb12*zb34)
     .         +zb12**2*za24**3*zb34**2/zb14)
     .        *L2(-s412,-s12)/s12**3
     .+1d0/3d0*zAphiq2gqpmpm(permm(1))*lnrat(-s412,-s12)
     .+0.5d0*zb13**2*za24/(s12*zb14)
     .+1d0/6d0*zb13*(zb31*za12*z2ba3142
     .                   -(zb34*za42)**2)
     .                  /(za12*zb34*zb14*s412)
     .+1d0/6d0*zb13**3*s412
     .        /(s12*zb12*zb34*zb14)
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmppmL(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.19
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V1L,L2,L1,L0,lnrat,sum
      complex*16 l23,l34,l41,l12,Lsm1_2me,Lsm1DS
      real*8 mhsq,s123,s234,s341,s412
*      write(*,*)'hello zA1phiAQggmppmL'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab4134=zab2(j4,j1,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s41)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1phiAQggmppmL=zAphiq2gqmmpp(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1phiAQggmppmL=zAphiq2gqmmpp(permm(1))*V1L
      elseif(ieorder.eq.0)then

      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)
     . +119d0/18d0-deltar/6d0
     . -Lsm1_2me(s123,s234,s23,mhsq)
     . -Lsm1_2me(s341,s412,s41,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)
      zA1phiAQggmppmL=zAphiq2gqmmpp(permm(1))
     . *(V1L-Lsm1DS(s23,s34,s234)
     .      -Lsm1DS(s41,s12,s412))
      sum=
     . +za14**3/(za12*za34*za13)
     . *(Lsm1DS(s12,s23,s123)
     .  +Lsm1DS(s34,s41,s341))
     . +(4d0/3d0*za13**2*z2ab4123**3/(za12*za34)
     . -za12*zb23**2*za34*z2ab4123
     . -1d0/3d0*za12**2*zb23**3*za34**2/za13)
     . *L2(-s123,-s12)/s12**3
     . +(0.5d0*za13**2*za24*z2ab4123**2
     . /(za12*za23*za34)
     . +za13*za14*z2ab4123**2/(za12*za34)
     . +0.5d0*za12*za34*zb23**2*za14/za13)
     . *L1(-s123,-s12)/s12**2
     . -0.5d0*za12*za34*za24*zb23**2
     . /za23*L1(-s234,-s34)/s34**2
     . +za14**2*z2ab4123/(za12*za34)
     . *L0(-s123,-s12)/s12

     . -2d0*za14*za24*zb23/za23
     . *(L0(-s123,-s12)/s12
     .  +L0(-s234,-s34)/s34)

c     check: looks like there should be a factor of
c           (-im) in front of A0 here
     . -5d0/6d0*(2d0*zAphiq2gqmmpp(permm(1))
     . +za14**3/(za12*za34*za13))
     . *lnrat(-s123,-s12)

     . +5d0/6d0*za14**2*z2ab4123
     . /(s12*za12*za34)
     . -1d0/6d0*za14**2*zb23*za34
     . /(za23*za13*z2ab4132)
     . +2d0/3d0*za14*zb23*za34
     . /(zb12*za23*za13)

     . -2d0/3d0*za14*za24*z2ab4132
     . /(s12*za23*za34)
     . +1d0/3d0*zb23*z2ab4132*z2ab4231
     . /(s123*zb12**2*za23)

     . -1d0/6d0*z2ab4231
     . *(za41*zb12+2d0*za43*zb32)
     . *(2d0*za41*zb12+za43*zb32)**2
     . /(s123*zb12**2*za23*za34*z2ab4132)

     . +0.5d0*zb23*z2ab2143
     . /(zb14*za23*zb34)

     . +0.5d0*z2ab4132*z2ab4123
     . /(s123*za23*zb12)

     . -0.5d0*za14**2*zb13/(s12*za23)

     . -2d0*zAcphiq2gqmmpp(permm(1))

      zA1phiAQggmppmL=zA1phiAQggmppmL+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmppmR(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.21
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 VR,A0phiAQggmppm,Lsm1_2me,lnrat,l12,L0,L1,
     . Lsm1DS
      real*8 mhsq,s123,s234,s341
*      write(*,*)'hello zA1phiAQggmppmR'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab4134=zab2(j4,j1,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)
      z2ab2341=zab2(j2,j3,j4,j1)

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1phiAQggmppmR=0d0!zAphiq2gqmmpp(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=-l12
     .   -3d0/2d0
      zA1phiAQggmppmR=0d0!zAphiq2gqmmpp(permm(1))*VR
      elseif(ieorder.eq.0)then

      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0
     .   -Lsm1_2me(s234,s341,s34,mhsq)

      zA1phiAQggmppmR=
     . za14**2/(za23*za13)*
     .  (Lsm1DS(s12,s23,s123)+Lsm1DS(s34,s41,s341))
     . -0.5d0*za12**2*zb23**2*za34**2
     .  /(za23*za13)*L1(-s123,-s12)/(s12**2)
     . +0.5d0*za24**3*z2ab1342**2
     .  /(za12*za23*za34)
     .  *L1(-s234,-s34)/(s34**2)
     . -2d0*za12*za34*za14*zb23
     .  /(za23*za13)*L0(-s123,-s12)/s12
     . -2d0*za14*za24*zb23/za23
     .  *L0(-s234,-s34)/s34
     . -3d0/2d0*za14**2/(za23*za13)
     .  *lnrat(-s123,-s12)
     . +1d0/2d0*zAphiq2gqmmpp(permm(1))*lnrat(-s234,-s34)
     . +0.5d0*(
     .  za14*zb23*za34/(zb12*za23*za13)
     . +zb23*zb13*z2ab2143
     .  /(zb34*zb14*z2ab2341)
     . -z2ab4132*z2ab4123
     .  /(s123*za23*zb12)
     . +za14**2*za24**2*(s21+s23+s24)
     .  /(za12*za23*za34**2*z2ab2143)
     . -s341**2*zb23*za24**3
     .  /(s34*za23*za34
     .    *z2ab2143*z2ab2341)
     .        )

      zA1phiAQggmppmR=zA1phiAQggmppmR
     .             +zAphiq2gqmmpp(permm(1))*VR
      endif
      return
      end

************************************************************************

      complex*16 function zA1phiAQggmppmF(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.23
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 l12,zab2,L2,lnrat,A0phiAQggmppm
      real*8 ss3
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

*      write(*,*)'hello zA1phiAQggmppmF'
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

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

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab4134=zab2(j4,j1,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)
      z2ab2341=zab2(j2,j3,j4,j1)

      s123=ss3(j1,j2,j3)

      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      zA1phiAQggmppmF=0d0
      elseif(ieorder.eq.-1)then
      zA1phiAQggmppmF=0d0
      elseif(ieorder.eq.0)then
      zA1phiAQggmppmF=zAphiq2gqmmpp(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     .+1d0/3d0*(za12**2*zb23**3*za34**2/za13
     .         -z2ab4123**3*za13**2/(za12*za34))
     .        *L2(-s123,-s12)/s12**3
     .-1d0/3d0*(za14**2/(za23*za13)
     .         +za14**2*za24/(za12*za23*za34))
     .        *lnrat(-s123,-s12)
     .-0.5d0*za14**2*zb23/(s12*za13)
     .+1d0/6d0*za14*(za41*zb12*z2ab4132
     .                   -(za43*zb32)**2)
     .                  /(zb12*za34*za13*s123)
     .+1d0/6d0*za14**3*s123
     .        /(s12*za12*za34*za13)
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmppmL(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.19
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V1L,L2,L1,L0,lnrat,sum
      complex*16 l23,l34,l41,l12,Lsm1_2me,Lsm1DS
      real*8 mhsq,s123,s234,s341,s412
*      write(*,*)'hello zA1phiAQggmppmL'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l23=lnrat(musq,-s23)
      l34=lnrat(musq,-s34)
      l41=lnrat(musq,-s41)

      if(ieorder.eq.-2)then
      V1L=-3d0
      zA1cphiAQggmppmL=zAphiq2gqppmm(permm(1))*V1L
      elseif(ieorder.eq.-1)then
      V1L=
     . -l23
     . -l34
     . -l41
     . +13d0/6d0
      zA1cphiAQggmppmL=zAphiq2gqppmm(permm(1))*V1L
      elseif(ieorder.eq.0)then

      V1L=
     . -epinv**2-epinv*l23-0.5d0*l23**2
     . -epinv**2-epinv*l34-0.5d0*l34**2
     . -epinv**2-epinv*l41-0.5d0*l41**2
     . +13d0/6d0*(epinv+l12)
     . +119d0/18d0-deltar/6d0
     . -Lsm1_2me(s123,s234,s23,mhsq)
     . -Lsm1_2me(s341,s412,s41,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)

      zA1cphiAQggmppmL=zAphiq2gqppmm(permm(1))
     . *(V1L-Lsm1DS(s23,s34,s234)
     .      -Lsm1DS(s41,s12,s412))
      sum=
     . +za14**3/(za12*za34*za13)
     . *(Lsm1DS(s12,s23,s123)
     .  +Lsm1DS(s34,s41,s341))
     . +(4d0/3d0*za13**2*z2ba4123**3/(za12*za34)
     . -za12*zb23**2*za34*z2ba4123
     . -1d0/3d0*za12**2*zb23**3*za34**2/za13)
     . *L2(-s123,-s12)/s12**3
     . +(0.5d0*za13**2*za24*z2ba4123**2
     . /(za12*za23*za34)
     . +za13*za14*z2ba4123**2/(za12*za34)
     . +0.5d0*za12*za34*zb23**2*za14/za13)
     . *L1(-s123,-s12)/s12**2
     . -0.5d0*za12*za34*za24*zb23**2
     . /za23*L1(-s234,-s34)/s34**2
     . +za14**2*z2ba4123/(za12*za34)
     . *L0(-s123,-s12)/s12

     . -2d0*za14*za24*zb23/za23
     . *(L0(-s123,-s12)/s12
     .  +L0(-s234,-s34)/s34)

c     check: looks like there should be a factor of
c           (-im) in front of A0 here
     . -5d0/6d0*(2d0*zAphiq2gqppmm(permm(1))
     . +za14**3/(za12*za34*za13))
     . *lnrat(-s123,-s12)

     . +5d0/6d0*za14**2*z2ba4123
     . /(s12*za12*za34)
     . -1d0/6d0*za14**2*zb23*za34
     . /(za23*za13*z2ba4132)
     . +2d0/3d0*za14*zb23*za34
     . /(zb12*za23*za13)

     . -2d0/3d0*za14*za24*z2ba4132
     . /(s12*za23*za34)
     . +1d0/3d0*zb23*z2ba4132*z2ba4231
     . /(s123*zb12**2*za23)

     . -1d0/6d0*z2ba4231
     . *(za41*zb12+2d0*za43*zb32)
     . *(2d0*za41*zb12+za43*zb32)**2
     . /(s123*zb12**2*za23*za34*z2ba4132)

     . +0.5d0*zb23*z2ba2143
     . /(zb14*za23*zb34)

     . +0.5d0*z2ba4132*z2ba4123
     . /(s123*za23*zb12)

     . -0.5d0*za14**2*zb13/(s12*za23)

     . -2d0*zAcphiq2gqppmm(permm(1))

      zA1cphiAQggmppmL=zA1cphiAQggmppmL+sum
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmppmR(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.21
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 VR,Lsm1_2me,lnrat,l12,L0,L1,
     . Lsm1DS
      real*8 mhsq,s123,s234,s341
*      write(*,*)'hello zA1cphiAQggmppmR'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)
      z2ba2341=zba2(j2,j3,j4,j1)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      VR=-1d0
      zA1cphiAQggmppmR=0d0!zAphiq2gqppmm(permm(1))*VR
      elseif(ieorder.eq.-1)then
      VR=-l12
     .   -3d0/2d0
      zA1cphiAQggmppmR=0d0!zAphiq2gqppmm(permm(1))*VR
      elseif(ieorder.eq.0)then

      VR=-epinv**2-epinv*l12-0.5d0*l12**2
     .   -3d0/2d0*(epinv+l12)-7d0/2d0-deltar/2d0
     .   -Lsm1_2me(s234,s341,s34,mhsq)

      zA1cphiAQggmppmR=
     . za14**2/(za23*za13)*
     .  (Lsm1DS(s12,s23,s123)+Lsm1DS(s34,s41,s341))
     . -0.5d0*za12**2*zb23**2*za34**2
     .  /(za23*za13)*L1(-s123,-s12)/(s12**2)
     . +0.5d0*za24**3*z2ba1342**2
     .  /(za12*za23*za34)
     .  *L1(-s234,-s34)/(s34**2)
     . -2d0*za12*za34*za14*zb23
     .  /(za23*za13)*L0(-s123,-s12)/s12
     . -2d0*za14*za24*zb23/za23
     .  *L0(-s234,-s34)/s34
     . -3d0/2d0*za14**2/(za23*za13)
     .  *lnrat(-s123,-s12)
     . +1d0/2d0*zAphiq2gqppmm(permm(1))*lnrat(-s234,-s34)
     . +0.5d0*(
     .  za14*zb23*za34/(zb12*za23*za13)
     . +zb23*zb13*z2ba2143
     .  /(zb34*zb14*z2ba2341)
     . -z2ba4132*z2ba4123
     .  /(s123*za23*zb12)
     . +za14**2*za24**2*(s21+s23+s24)
     .  /(za12*za23*za34**2*z2ba2143)
     . -s341**2*zb23*za24**3
     .  /(s34*za23*za34
     .    *z2ba2143*z2ba2341)
     .        )

      zA1cphiAQggmppmR=zA1cphiAQggmppmR
     .             +zAphiq2gqppmm(permm(1))*VR
      endif
      return
      end

************************************************************************

      complex*16 function zA1cphiAQggmppmF(perm,renscale2)
C     implementation of arXiv:0906.0008v1, Eq. 4.23
c     the function defined in this routine is in fact (-i*A_4),
c      i.e. complete LHS
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 l12,zab2,L2,lnrat
      real*8 ss3
*      write(*,*)'hello zA1cphiAQggmppmF'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)
      z2ba2341=zba2(j2,j3,j4,j1)

      l12=lnrat(musq,-s12)

      if(ieorder.eq.-2)then
      zA1cphiAQggmppmF=0d0
      elseif(ieorder.eq.-1)then
      zA1cphiAQggmppmF=0d0
      elseif(ieorder.eq.0)then
      zA1cphiAQggmppmF=zAphiq2gqppmm(permm(1))
     . *(-2d0/3d0*(epinv+l12)-10d0/9d0)
     .+1d0/3d0*(zb12**2*za23**3*zb34**2/zb13
     .         -z2ba4123**3*zb13**2/(zb12*zb34))
     .        *L2(-s123,-s12)/s12**3
     .-1d0/3d0*(zb14**2/(zb23*zb13)
     .         +zb14**2*zb24/(zb12*zb23*zb34))
     .        *lnrat(-s123,-s12)
     .-0.5d0*zb14**2*za23/(s12*zb13)
     .+1d0/6d0*zb14*(zb41*za12*z2ba4132
     .                   -(zb43*za32)**2)
     .                  /(za12*zb34*zb13*s123)
     .+1d0/6d0*zb14**3*s123
     .        /(s12*zb12*zb34*zb13)
      endif
      return
      end

************************************************************************

      complex*16 function zA43phiAQggmpmm_unsym(perm,renscale2)
c     This is an implementation of Eq. (5.17) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,lnrat,sum
      complex*16 l34,l12,l24,l13,Lsm1,Lsm1_2mht
      real*8 ss3,mhsq,s123,s234,s341,s412
*      write(*,*)'hello zA43phiAQggmpmm_unsym'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ab2143=zab2(j2,j1,j4,j3)
      z2ab1342=zab2(j1,j3,j4,j2)
      z2ab1234=zab2(j1,j2,j3,j4)
      z2ab4123=zab2(j4,j1,j2,j3)
      z2ab3142=zab2(j3,j1,j4,j2)
      z2ab3124=zab2(j3,j1,j2,j4)
      z2ab4231=zab2(j4,j2,j3,j1)
      z2ab4132=zab2(j4,j1,j3,j2)
      z2ab3241=zab2(j3,j2,j4,j1)
      z2ab4134=zab2(j4,j1,j3,j4)
      z2ab2134=zab2(j2,j1,j3,j4)
      z2ab2341=zab2(j2,j3,j4,j1)
      z2ab1243=zab2(j1,j2,j4,j3)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)
      l13=lnrat(musq,-s13)

      if(ieorder.eq.-2)then
      V5L=0d0
      zA43phiAQggmpmm_unsym=zB2g0Hmmmp(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43phiAQggmpmm_unsym=zB2g0Hmmmp(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     new representation of poles
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2

      sum=+zB2g0Hmmmp(permm(1))*V5L

      sum=sum
     & +((z2ab4123**2*zb12**2/zb23
     & +zb23**2*z2ab4231**3
     &  /(zb12*z2ab4123))/zb13**3
     & -mhsq**2*za13**3
     &  /(za12*z2ab1234*z2ab3124))
     & *Lsm1(-s12,-s123,-s23,-s123)/s123

     & +(mhsq**2*za14**2*za24
     &  /(za12*z2ab2143*z2ab4123)
     & -z2ab3142**2*z2ab3241
     &  /(zb14*z2ab3124*zb12))
     & *Lsm1(-s12,-s412,-s14,-s412)/s412

     & +(mhsq**2*za13**2/(z2ab1234*z2ab2134)
     & -z2ab4132**2/(zb13*zb23))
     & *Lsm1(-s13,-s123,-s23,-s123)/s123

     & +s341**2
     & /(zb13*zb34*z2ab2134)
     & *(Lsm1(-s13,-s341,-s14,-s341)
     &  +Lsm1_2mht(s23,s341,s14,mhsq))

     & +s341**2
     & /(zb14*zb34*z2ab2143)
     & *(Lsm1(-s14,-s341,-s34,-s341)
     &  +Lsm1_2mht(s12,s341,s34,mhsq))

     & -z2ab1342**2
     & /(zb23*zb34*z2ab1234)
     & *(Lsm1(-s23,-s234,-s34,-s234)
     &  +Lsm1_2mht(s12,s234,s34,mhsq))

     & +zb24**2*z2ab1243**2
     & /(zb23*zb34**3*z2ab1234)
     & *Lsm1(-s23,-s234,-s24,-s234)

     & -z2ab1342**2
     & /(z2ab1243*zb24*zb34)
     & *Lsm1_2mht(s14,s234,s23,mhsq)

     & +(-mhsq**2*za13**2*za23
     & /(za12*z2ab2134*z2ab3124)
     & +z2ab4132**2/z2ab4123
     & *z2ab4231/(zb12*zb13))
     & *Lsm1_2mht(s14,s123,s23,mhsq)/s123

     & +(mhsq**2*za13**3
     & /(za12*z2ab3124*z2ab1234)
     & -z2ab4132**3/(z2ab4123*zb12*zb23))
     & *Lsm1_2mht(s24,s123,s13,mhsq)/s123

     & +(-mhsq**2*za13**2
     & /(z2ab2134*z2ab1234)
     & +z2ab4132**2/(zb13*zb23))
     & *Lsm1_2mht(s34,s123,s12,mhsq)/s123

      zA43phiAQggmpmm_unsym=sum
      endif
      return
      end

************************************************************************

      complex*16 function zA43cphiAQggmpmm_unsym(perm,renscale2)
c     This is an implementation of Eq. (5.17) in
c     S.~Badger, John.~M.~Campbell, R.~Keith Ellis and Ciaran Williams
c     "Analytic results for the one-loop NMHV H-qbar-q-g-g amplitude."
c      preprint DESY 09-180, FERMILAB-PUB-09-505-T, IPPP/09/86
c      arXiv: 0910.4481 [hep-ph]
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,
     . A0phiAQggmpmm,A0phiAgQgmmpm,lnrat,sum
      complex*16 l34,l12,l24,l13,Lsm1,Lsm1_2mht
      real*8 ss3,mhsq,s123,s234,s341,s412
*      write(*,*)'hello zA43cphiAQggmpmm_unsym'
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)

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

      za12 = zB(j1,j2)
      za13 = zB(j1,j3)
      za14 = zB(j1,j4)
      za23 = zB(j2,j3)
      za24 = zB(j2,j4)
      za34 = zB(j3,j4)

      za21 = zB(j2,j1)
      za31 = zB(j3,j1)
      za41 = zB(j4,j1)
      za32 = zB(j3,j2)
      za42 = zB(j4,j2)
      za43 = zB(j4,j3)

      zb12 = zA(j1,j2)
      zb13 = zA(j1,j3)
      zb14 = zA(j1,j4)
      zb23 = zA(j2,j3)
      zb24 = zA(j2,j4)
      zb34 = zA(j3,j4)

      zb21 = zA(j2,j1)
      zb31 = zA(j3,j1)
      zb41 = zA(j4,j1)
      zb32 = zA(j3,j2)
      zb42 = zA(j4,j2)
      zb43 = zA(j4,j3)

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)

      z2ba2143=zba2(j2,j1,j4,j3)
      z2ba1342=zba2(j1,j3,j4,j2)
      z2ba1234=zba2(j1,j2,j3,j4)
      z2ba4123=zba2(j4,j1,j2,j3)
      z2ba3142=zba2(j3,j1,j4,j2)
      z2ba3124=zba2(j3,j1,j2,j4)
      z2ba4231=zba2(j4,j2,j3,j1)
      z2ba4132=zba2(j4,j1,j3,j2)
      z2ba3241=zba2(j3,j2,j4,j1)
      z2ba4134=zba2(j4,j1,j3,j4)
      z2ba2134=zba2(j2,j1,j3,j4)
      z2ba2341=zba2(j2,j3,j4,j1)
      z2ba1243=zba2(j1,j2,j4,j3)

      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)
      l13=lnrat(musq,-s13)
      if(ieorder.eq.-2)then
      V5L=0d0
      zA43cphiAQggmpmm_unsym=zB2g0Hpppm(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43cphiAQggmpmm_unsym=zB2g0Hpppm(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     new representation of poles
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2

      sum=+zB2g0Hpppm(permm(1))*V5L

      sum=sum
     & +((z2ba4123**2*zb12**2/zb23
     & +zb23**2*z2ba4231**3
     &  /(zb12*z2ba4123))/zb13**3
     & -mhsq**2*za13**3
     &  /(za12*z2ba1234*z2ba3124))
     & *Lsm1(-s12,-s123,-s23,-s123)/s123

     & +(mhsq**2*za14**2*za24
     &  /(za12*z2ba2143*z2ba4123)
     & -z2ba3142**2*z2ba3241
     &  /(zb14*z2ba3124*zb12))
     & *Lsm1(-s12,-s412,-s14,-s412)/s412

     & +(mhsq**2*za13**2/(z2ba1234*z2ba2134)
     & -z2ba4132**2/(zb13*zb23))
     & *Lsm1(-s13,-s123,-s23,-s123)/s123

     & +s341**2
     & /(zb13*zb34*z2ba2134)
     & *(Lsm1(-s13,-s341,-s14,-s341)
     &  +Lsm1_2mht(s23,s341,s14,mhsq))

     & +s341**2
     & /(zb14*zb34*z2ba2143)
     & *(Lsm1(-s14,-s341,-s34,-s341)
     &  +Lsm1_2mht(s12,s341,s34,mhsq))

     & -z2ba1342**2
     & /(zb23*zb34*z2ba1234)
     & *(Lsm1(-s23,-s234,-s34,-s234)
     &  +Lsm1_2mht(s12,s234,s34,mhsq))

     & +zb24**2*z2ba1243**2
     & /(zb23*zb34**3*z2ba1234)
     & *Lsm1(-s23,-s234,-s24,-s234)

     & -z2ba1342**2
     & /(z2ba1243*zb24*zb34)
     & *Lsm1_2mht(s14,s234,s23,mhsq)

     & +(-mhsq**2*za13**2*za23
     & /(za12*z2ba2134*z2ba3124)
     & +z2ba4132**2/z2ba4123
     & *z2ba4231/(zb12*zb13))
     & *Lsm1_2mht(s14,s123,s23,mhsq)/s123

     & +(mhsq**2*za13**3
     & /(za12*z2ba3124*z2ba1234)
     & -z2ba4132**3/(z2ba4123*zb12*zb23))
     & *Lsm1_2mht(s24,s123,s13,mhsq)/s123

     & +(-mhsq**2*za13**2
     & /(z2ba2134*z2ba1234)
     & +z2ba4132**2/(zb13*zb23))
     & *Lsm1_2mht(s34,s123,s12,mhsq)/s123

      zA43cphiAQggmpmm_unsym=sum
      endif
      return
      end

************************************************************************

c     The expression below corresponds to one half of A4;3:
c      Aleft(a1,q2,g3-,g4+)+Aright(a1,q2,g3-,g4+)+Aleft(a1,g3-,q2,g4+)

c     It is obtained by summing the expressions given in:
c     L.~J.~Dixon and Y.~Sofianatos,
c     %``Analytic one-loop amplitudes for a Higgs boson plus four partons,''
c     arXiv:0906.0008 [hep-ph].
      complex*16 function zA43phiAQggmpmp_unsym(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,V6L,A0phiAQggmpmp,lnrat
      complex*16 l13,l34,l12,l24,Lsm1DS,Lsm1,Lsm1_2me
      real*8 ss3,mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)
      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l13=lnrat(musq,-s13)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)

      if(ieorder.eq.-2)then
      V5L=0d0
      zA43phiAQggmpmp_unsym=zAphiq2gqmpmp(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43phiAQggmpmp_unsym=zAphiq2gqmpmp(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     This is the same function as in the mpmm amplitude
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2

c     These are additional boxes
      V6L=
     . +Lsm1_2me(s341,s123,s13,mhsq)
     . +Lsm1_2me(s412,s234,s24,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)
     . -Lsm1_2me(s234,s341,s34,mhsq)
     . +Lsm1DS(s24,s41,s412)
     . +Lsm1DS(s13,s32,s123)
     . +Lsm1DS(s24,s23,s234)
     . +Lsm1DS(s13,s14,s341)

      zA43phiAQggmpmp_unsym=
     .  zAphiq2gqmpmp(permm(1))
     .  *(V5L+V6L
     .   -Lsm1DS(s34,s41,s341)
     .   -Lsm1DS(s12,s23,s123))

     . +(za14**2*za23**3/(za12*za34*za24**3)
     .  +za12**2*za34**2/(za14*za24**3))
     .  *(Lsm1DS(s23,s34,s234)
     .   +Lsm1DS(s41,s12,s412))
      endif
      return
      end

************************************************************************

c     The expression below corresponds to one half of A4;3:
c      Aleft(a1,q2,g3+,g4-)+Aright(a1,q2,g3+,g4-)+Aleft(a1,g3+,q2,g4-)

c     It is obtained by summing the expressions given in:
c     L.~J.~Dixon and Y.~Sofianatos,
c     %``Analytic one-loop amplitudes for a Higgs boson plus four partons,''
c     arXiv:0906.0008 [hep-ph].
      complex*16 function zA43phiAQggmppm_unsym(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,V6l,A0phiAQggmppm,lnrat
      complex*16 l13,l34,l12,l24,Lsm1DS,Lsm1,Lsm1_2me
      real*8 mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)
      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l13=lnrat(musq,-s13)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)

      if(ieorder.eq.-2)then
      V5L=0d0
      zA43phiAQggmppm_unsym=zAphiq2gqmmpp(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43phiAQggmppm_unsym=zAphiq2gqmmpp(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     This is the same function as in the mpmm amplitude
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2
c     These are additional boxes
      V6L=
     . +Lsm1_2me(s341,s123,s13,mhsq)
     . +Lsm1_2me(s412,s234,s24,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)
     . -Lsm1_2me(s234,s341,s34,mhsq)
     . +Lsm1DS(s24,s41,s412)
     . +Lsm1DS(s13,s32,s123)
     . +Lsm1DS(s24,s23,s234)
     . +Lsm1DS(s13,s14,s341)

      zA43phiAQggmppm_unsym=
     .  zAphiq2gqmmpp(permm(1))
     .  *(V5L+V6L
     .    -Lsm1DS(s23,s34,s234)
     .    -Lsm1DS(s41,s12,s412))

     . +(za14**3/(za12*za34*za13)
     .  +za14**2/(za23*za13))
     .  *(Lsm1DS(s12,s23,s123)
     .   +Lsm1DS(s34,s41,s341))
      endif
      return
      end
************************************************************************

c     The expression below corresponds to one half of A4;3:
c      Aleft(a1,q2,g3-,g4+)+Aright(a1,q2,g3-,g4+)+Aleft(a1,g3-,q2,g4+)

c     It is obtained by summing the expressions given in:
c     L.~J.~Dixon and Y.~Sofianatos,
c     %``Analytic one-loop amplitudes for a Higgs boson plus four partons,''
c     arXiv:0906.0008 [hep-ph].
      complex*16 function zA43cphiAQggmpmp_unsym(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,V6L,A0phiAQggmpmp,lnrat
      complex*16 l13,l34,l12,l24,Lsm1DS,Lsm1,Lsm1_2me
      real*8 ss3,mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)
      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l13=lnrat(musq,-s13)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)

      if(ieorder.eq.-2)then
      V5L=0d0
      zA43cphiAQggmpmp_unsym=zAphiq2gqpmpm(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43cphiAQggmpmp_unsym=zAphiq2gqpmpm(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     This is the same function as in the mpmm amplitude
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2

c     These are additional boxes
      V6L=
     . +Lsm1_2me(s341,s123,s13,mhsq)
     . +Lsm1_2me(s412,s234,s24,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)
     . -Lsm1_2me(s234,s341,s34,mhsq)
     . +Lsm1DS(s24,s41,s412)
     . +Lsm1DS(s13,s32,s123)
     . +Lsm1DS(s24,s23,s234)
     . +Lsm1DS(s13,s14,s341)

      zA43cphiAQggmpmp_unsym=
     .  zAphiq2gqpmpm(permm(1))
     .  *(V5L+V6L
     .   -Lsm1DS(s34,s41,s341)
     .   -Lsm1DS(s12,s23,s123))

     . +(zb14**2*zb23**3/(zb12*zb34*zb24**3)
     .  +zb12**2*zb34**2/(zb14*zb24**3))
     .  *(Lsm1DS(s23,s34,s234)
     .   +Lsm1DS(s41,s12,s412))
      endif
      return
      end

************************************************************************

c     The expression below corresponds to one half of A4;3:
c      Aleft(a1,q2,g3+,g4-)+Aright(a1,q2,g3+,g4-)+Aleft(a1,g3+,q2,g4-)

c     It is obtained by summing the expressions given in:
c     L.~J.~Dixon and Y.~Sofianatos,
c     %``Analytic one-loop amplitudes for a Higgs boson plus four partons,''
c     arXiv:0906.0008 [hep-ph].
      complex*16 function zA43cphiAQggmppm_unsym(perm,renscale2)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      common/order/ieorder
      integer j,j1,j2,j3,j4,j5,j6,perm(4),permm(4)
      real*8 epinv,deltar,musq
      complex*16 V5L,V6l,A0phiAQggmppm,lnrat
      complex*16 l13,l34,l12,l24,Lsm1DS,Lsm1,Lsm1_2me
      real*8 mhsq,s123,s234,s341,s412
      real*8 :: s12,s13,s14,s23,s24,s34,s21,s31,s41,s32,s42,s43
      complex*16 :: za12,za13,za14,za23,za24,za34
      complex*16 :: za21,za31,za41,za32,za42,za43
      complex*16 :: zb12,zb13,zb14,zb23,zb24,zb34
      complex*16 :: zb21,zb31,zb41,zb32,zb42,zb43
      real*8 :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
      common/kin5/s,zA,zB

      musq=renscale2
      epinv=0d0
      deltar=1d0
      czip=(0d0,0d0)
      j1=perm(1)
      j2=perm(2)
      j3=perm(3)
      j4=perm(4)

      permm(1)=perm(1)
      permm(2)=perm(4)
      permm(3)=perm(3)
      permm(4)=perm(2)

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

      s123=ss3(j1,j2,j3)
      s234=ss3(j2,j3,j4)
      s341=ss3(j3,j4,j1)
      s412=ss3(j4,j1,j2)
      mhsq=s12+s13+s14+s23+s24+s34
      l12=lnrat(musq,-s12)
      l13=lnrat(musq,-s13)
      l24=lnrat(musq,-s24)
      l34=lnrat(musq,-s34)

      if(ieorder.eq.-2)then
      V5L=0d0
      zA43cphiAQggmppm_unsym=zAphiq2gqppmm(permm(1))*V5L
      elseif(ieorder.eq.-1)then
      V5L=
     & -l12
     & -l34
     & +l13
     & +l24
      zA43cphiAQggmppm_unsym=zAphiq2gqppmm(permm(1))*V5L
      elseif(ieorder.eq.0)then
c     This is the same function as in the mpmm amplitude
      V5L=
     & -epinv**2-epinv*l12-0.5d0*l12**2
     & -epinv**2-epinv*l34-0.5d0*l34**2
     & +epinv**2+epinv*l13+0.5d0*l13**2
     & +epinv**2+epinv*l24+0.5d0*l24**2

c     These are additional boxes
      V6L=
     . +Lsm1_2me(s341,s123,s13,mhsq)
     . +Lsm1_2me(s412,s234,s24,mhsq)
     . -Lsm1_2me(s412,s123,s12,mhsq)
     . -Lsm1_2me(s234,s341,s34,mhsq)
     . +Lsm1DS(s24,s41,s412)
     . +Lsm1DS(s13,s32,s123)
     . +Lsm1DS(s24,s23,s234)
     . +Lsm1DS(s13,s14,s341)

      zA43cphiAQggmppm_unsym=
     .  zAphiq2gqppmm(permm(1))
     .  *(V5L+V6L
     .    -Lsm1DS(s23,s34,s234)
     .    -Lsm1DS(s41,s12,s412))

     . +(zb14**3/(zb12*zb34*zb13)
     .  +zb14**2/(zb23*zb13))
     .  *(Lsm1DS(s12,s23,s123)
     .   +Lsm1DS(s34,s41,s341))
      endif

      return
      end

************************************************************************

c     Auxiliary wrapper for lnrat. Might not be needed.
      complex(8) function zlnrat(x,y)
      implicit none
      real(8), intent(in)  :: x,y
c     Externals.
      complex(8), external :: lnrat
      zlnrat = lnrat(x,y)
      return
      end

c-----------------------------------------------------------------------

c     Full one-loop matrix element for
c     H -> q(i1) qbar(i2) Q(i3) Qbar(i4).
c     Adapted from MCFM/NNLOJET (src/process/H/libCDHloop.f).
      real(8) function FullC0g1H(p,iq1,iQbar4,iQ3,iqbar2,
     .     renscale2,ipole)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,ipole
      real(8), intent(in) :: p(1:4,5),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external   :: C0g1H,Ct0g1H,Ch0g1H,C0g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Calculate prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*cn

      FullC0g1H = 2d0*fac*(
     .     + C0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     - 1d0/cn**2*Ct0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     + nf/cn*Ch0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     )

c     Include O(as) Wilson coefficient.
      if (ipole.eq.0)then
         FullC0g1H = FullC0g1H
     .        + 2d0*11d0/3d0*fac*C0g0H(p,iq1,iQbar4,iQ3,iqbar2)
      endif

      return
      end

************************************************************************

c     Leading-colour contribution to
c     H -> q(i1) qbar(i2) Q(i3) Qbar(i4).
      real(8) function C0g1H(p,i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(4,5),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      integer             :: j1,j2,j3,j4
      integer             :: ischeme,imemode
      real(8)             :: born,tree,virt,ren
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s123,s124,s134,s234,s1234
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external    :: A2g0H,C0g0H
      real(8), external    :: fun1C,fun2C,fun3C,fun4C,fun5C,fun6C
      real(8), external    :: fun7C,fun8C,fun9C,fun10C,fun11C,fun12C
      complex(8), external :: L0,L1,Lsm1,Lsm1_2me,lnrat

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Fill permutations.
      j1 = i4
      j2 = i3
      j3 = i2
      j4 = i1

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
c     Note: divide out factors that are reapplied below.
      tree = C0g0H(p,j4,j1,j2,j3)/born

c     Set invariants.
      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s234 = s23+s24+s34
      s134 = s13+s14+s34

c     Calculate Born-one-loop interference.
      ren = 0d0
      if (ipole.eq.-2)then
         virt = (-2d0)*tree
      elseif (ipole.eq.-1)then
         virt = (
     .        - 3d0
     .        + dble(lnrat(-s14,renscale2))
     .        + dble(lnrat(-s23,renscale2))
     .        )*tree
      elseif (ipole.eq.0)then
c     Terms proportional to tree.
         virt = (
     .        + 80d0/9d0
     .        - dble(Lsm1_2me(s123,s234,s23,s1234))
     .        - dble(Lsm1_2me(s124,s134,s14,s1234))
     .        - 13d0/6d0*dble(lnrat(-s34,renscale2))
     .        - 13d0/6d0*dble(lnrat(-s12,renscale2))
     .        - 1d0/2d0*dble(lnrat(-s14,renscale2)**2)
     .        - 1d0/2d0*dble(lnrat(-s23,renscale2)**2)
     .        )*tree

c     Terms not proportional to tree.
         virt = virt
     .        + (
     .        + dble(Lsm1(-s12,-s123,-s23,-s123))*fun1C(j1,j2,j3,j4)
     .        + dble(Lsm1(-s12,-s124,-s14,-s124))*fun1C(j2,j1,j4,j3)
     .        + dble(Lsm1(-s34,-s234,-s23,-s234))*fun1C(j2,j1,j4,j3)
     .        + dble(Lsm1(-s34,-s134,-s14,-s134))*fun1C(j1,j2,j3,j4)
     .        + fun2C(j1,j2,j3,j4)*dble(L1(-s123,-s12))
     .        + fun2C(j2,j1,j4,j3)*dble(L1(-s124,-s12))
     .        + fun2C(j4,j3,j2,j1)*dble(L1(-s234,-s34))
     .        + fun2C(j3,j4,j1,j2)*dble(L1(-s134,-s34))
     .        + fun3C(j1,j2,j3,j4)*dble(L0(-s123,-s12))
     .        + fun3C(j2,j1,j4,j3)*dble(L0(-s124,-s12))
     .        + fun3C(j4,j3,j2,j1)*dble(L0(-s234,-s34))
     .        + fun3C(j3,j4,j1,j2)*dble(L0(-s134,-s34))
     .        - 1d0/2d0*fun5C(j1,j2,j3,j4)*dble(L0(-s124,-s14))
     .        - 1d0/2d0*fun5C(j2,j1,j4,j3)*dble(L0(-s123,-s23))
     .        - 1d0/2d0*fun5C(j4,j3,j2,j1)*dble(L0(-s134,-s14))
     .        - 1d0/2d0*fun5C(j3,j4,j1,j2)*dble(L0(-s234,-s23))
     .        + dble(lnrat(-s123,-s12))*fun6C(j1,j2,j3,j4)
     .        + dble(lnrat(-s124,-s12))*fun6C(j2,j1,j4,j3)
     .        + dble(lnrat(-s234,-s34))*fun6C(j4,j3,j2,j1)
     .        + dble(lnrat(-s134,-s34))*fun6C(j3,j4,j1,j2)
     .        + dble(lnrat(-s123,-s23))*fun7C(j1,j2,j3,j4)
     .        + dble(lnrat(-s124,-s14))*fun7C(j2,j1,j4,j3)
     .        + dble(lnrat(-s234,-s23))*fun7C(j4,j3,j2,j1)
     .        + dble(lnrat(-s134,-s14))*fun7C(j3,j4,j1,j2)
     .        + dble(lnrat(-s12,-s14))*fun8C(j1,j2,j3,j4)
     .        + dble(lnrat(-s12,-s14))*fun8C(j2,j1,j4,j3)
     .        + dble(lnrat(-s34,-s23))*fun8C(j4,j3,j2,j1)
     .        + dble(lnrat(-s34,-s23))*fun8C(j3,j4,j1,j2)
     .        + fun12C(j1,j2,j3,j4)
     .        + fun12C(j2,j1,j4,j3)
     .        + fun12C(j4,j3,j2,j1)
     .        + fun12C(j3,j4,j1,j2)
     .        )/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
         ischeme = 0
         if (ischeme.eq.1) ren = 2d0*pi**2/12d0
      endif

      C0g1H = virt + ren*tree
      C0g1H = C0g1H*born

      return
      end

************************************************************************

      real(8) function Ct0g1H(p,i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: j1,j2,j3,j4
      integer              :: ischeme,imemode
      real(8)              :: tree,born,virt,ren
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s123,s124,s134,s234,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5), zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,C0g0H
      real(8), external    :: fun1C,fun2C,fun3C,fun4C,fun5C,fun6C
      real(8), external    :: fun7C,fun8C,fun9C,fun10C,fun11C,fun12C
      complex(8), external :: L0,L1,Lsm1,Lsm1_2me,lnrat
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Fill permutations.
      j1 = i4
      j2 = i3
      j3 = i2
      j4 = i1

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
c     Note: divide out common factors that are reapplied below.
      tree = C0g0H(p,j4,j1,j2,j3)/born

c     Set invariants.
      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s234 = s23+s24+s34
      s134 = s13+s14+s34

c     Calculate Born-one-loop interference.
      ren = 0d0
      if (ipole.eq.-2)then
         virt = (2d0)*tree
      elseif (ipole.eq.-1)then
         virt = (
     .        + 3d0
     .        - dble(lnrat(-s34,renscale2))
     .        - dble(lnrat(-s12,renscale2))
     .        + 2d0*dble(lnrat(-s13,renscale2))
     .        + 2d0*dble(lnrat(-s24,renscale2))
     .        - 2d0*dble(lnrat(-s14,renscale2))
     .        - 2d0*dble(lnrat(-s23,renscale2))
     .        )*tree
      elseif (ipole.eq.0)then
c     Terms proportional to tree.
         virt = (
     .        + 8d0
     .        + dble(Lsm1_2me(s134,s234,s34,s1234))
     .        - 2d0*dble(Lsm1_2me(s123,s134,s13,s1234))
     .        + 2d0*dble(Lsm1_2me(s123,s234,s23,s1234))
     .        + dble(Lsm1_2me(s123,s124,s12,s1234))
     .        + 2d0*dble(Lsm1_2me(s124,s134,s14,s1234))
     .        - 2d0*dble(Lsm1_2me(s124,s234,s24,s1234))
     .        - 3d0/2d0*dble(lnrat(-s34,renscale2))
     .        - 3d0/2d0*dble(lnrat(-s12,renscale2))
     .        - dble(lnrat(-s13,renscale2)**2)
     .        - dble(lnrat(-s24,renscale2)**2)
     .        + dble(lnrat(-s14,renscale2)**2)
     .        + dble(lnrat(-s23,renscale2)**2)
     .        + 1d0/2d0*dble(lnrat(-s34,renscale2)**2)
     .        + 1d0/2d0*dble(lnrat(-s12,renscale2)**2)
     .        )*tree

c     Terms not proportional to tree.
         virt = virt
     .        + (
     .        + 2d0*dble(Lsm1(-s12,-s123,-s13,-s123))*fun1C(j2,j1,j3,j4)
     .        + 2d0*dble(Lsm1(-s12,-s124,-s24,-s124))*fun1C(j1,j2,j4,j3)
     .        + 2d0*dble(Lsm1(-s34,-s234,-s24,-s234))*fun1C(j2,j1,j3,j4)
     .        + 2d0*dble(Lsm1(-s34,-s134,-s13,-s134))*fun1C(j1,j2,j4,j3)
     .        - 2d0*dble(Lsm1(-s12,-s123,-s23,-s123))*fun1C(j1,j2,j3,j4)
     .        - 2d0*dble(Lsm1(-s12,-s124,-s14,-s124))*fun1C(j2,j1,j4,j3)
     .        - 2d0*dble(Lsm1(-s34,-s234,-s23,-s234))*fun1C(j2,j1,j4,j3)
     .        - 2d0*dble(Lsm1(-s34,-s134,-s14,-s134))*fun1C(j1,j2,j3,j4)
     .        + fun2C(j1,j2,j3,j4)*dble(L1(-s123,-s12))
     .        + fun2C(j2,j1,j4,j3)*dble(L1(-s124,-s12))
     .        + fun2C(j4,j3,j2,j1)*dble(L1(-s234,-s34))
     .        + fun2C(j3,j4,j1,j2)*dble(L1(-s134,-s34))
     .        + fun4C(j1,j2,j3,j4)*dble(L0(-s123,-s12))
     .        + fun4C(j2,j1,j4,j3)*dble(L0(-s124,-s12))
     .        + fun4C(j4,j3,j2,j1)*dble(L0(-s234,-s34))
     .        + fun4C(j3,j4,j1,j2)*dble(L0(-s134,-s34))
     .        + fun5C(j1,j2,j3,j4)*dble(L0(-s124,-s14))
     .        + fun5C(j2,j1,j4,j3)*dble(L0(-s123,-s23))
     .        + fun5C(j4,j3,j2,j1)*dble(L0(-s134,-s14))
     .        + fun5C(j3,j4,j1,j2)*dble(L0(-s234,-s23))
     .        - fun5C(j1,j2,j4,j3)*dble(L0(-s123,-s13))
     .        - fun5C(j2,j1,j3,j4)*dble(L0(-s124,-s24))
     .        - fun5C(j4,j3,j1,j2)*dble(L0(-s234,-s24))
     .        - fun5C(j3,j4,j2,j1)*dble(L0(-s134,-s13))
     .        + dble(lnrat(-s123,-s12))*fun9C(j1,j2,j3,j4)
     .        + dble(lnrat(-s124,-s12))*fun9C(j2,j1,j4,j3)
     .        + dble(lnrat(-s234,-s34))*fun9C(j4,j3,j2,j1)
     .        + dble(lnrat(-s134,-s34))*fun9C(j3,j4,j1,j2)
     .        + dble(lnrat(-s123,-s13))*fun10C(j1,j2,j3,j4)
     .        + dble(lnrat(-s124,-s24))*fun10C(j2,j1,j4,j3)
     .        + dble(lnrat(-s234,-s24))*fun10C(j4,j3,j2,j1)
     .        + dble(lnrat(-s134,-s13))*fun10C(j3,j4,j1,j2)
     .        + dble(lnrat(-s12,-s13))*fun11C(j1,j2,j3,j4)
     .        + dble(lnrat(-s12,-s23))*fun11C(j2,j1,j4,j3)
     .        + dble(lnrat(-s34,-s24))*fun11C(j4,j3,j2,j1)
     .        + dble(lnrat(-s34,-s14))*fun11C(j3,j4,j1,j2)
     .        - dble(lnrat(-s123,-s23))*fun10C(j2,j1,j3,j4)
     .        - dble(lnrat(-s124,-s14))*fun10C(j1,j2,j4,j3)
     .        - dble(lnrat(-s234,-s23))*fun10C(j3,j4,j2,j1)
     .        - dble(lnrat(-s134,-s14))*fun10C(j4,j3,j1,j2)
     .        - dble(lnrat(-s12,-s13))*fun11C(j2,j1,j3,j4)
     .        - dble(lnrat(-s12,-s14))*fun11C(j1,j2,j4,j3)
     .        - dble(lnrat(-s34,-s23))*fun11C(j3,j4,j2,j1)
     .        - dble(lnrat(-s34,-s24))*fun11C(j4,j3,j1,j2)
     .        + fun12C(j1,j2,j3,j4)
     .        + fun12C(j2,j1,j4,j3)
     .        + fun12C(j4,j3,j2,j1)
     .        + fun12C(j3,j4,j1,j2)
     .        )/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
         ischeme = 0
         if (ischeme.eq.1) ren = 2d0*pi**2/12d0
      endif

      Ct0g1H = -virt + ren*tree
      Ct0g1H = Ct0g1H*born

      return
      end

************************************************************************

      real(8) function Ch0g1H(p,i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: j1,j2,j3,j4
      integer              :: ischeme,imemode
      real(8)              :: born,tree,virt
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s123,s124,s134,s234,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,C0g0H
      real(8), external    :: fun1C,fun2C,fun3C,fun4C,fun5C,fun6C
      real(8), external    :: fun7C,fun8C,fun9C,fun10C,fun11C,fun12C
      complex(8), external :: L0,L1,Lsm1,Lsm1_2me,lnrat
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Fill permutations.
      j1 = i4
      j2 = i3
      j3 = i2
      j4 = i1

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level matrix element squared.
c     Note: divide out common factors that are reapplied below.
      tree = C0g0H(p,j4,j1,j2,j3)/born

c     Set invariants.
      s12 = s(j1,j2)
      s34 = s(j3,j4)

      if (ipole.eq.-2)then
         virt = 0d0
      elseif (ipole.eq.-1)then
         virt = 0d0
      elseif (ipole.eq.0)then
         virt = (
     .        - 20d0/9d0
     .        + 2d0/3d0*dble(lnrat(-s34,renscale2))
     .        + 2d0/3d0*dble(lnrat(-s12,renscale2))
     .        )*tree
      endif

      Ch0g1H = virt
      Ch0g1H = Ch0g1H*born

      return
      end

c-----------------------------------------------------------------------
c     Loop functions for H -> q qbar Q Qbar (different flavour).

      real(8) function fun1C(i1,i2,i3,i4)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      integer             :: j1,j2,j3,j4
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun1C =
     .     - s12*s34/(2d0*s13**2)
     .     - s24**2/(2d0*s12*s34)
     .     + (3d0*s13*s24-s23**2+s14*s23-s14**2-s13**2)/(s12*s34)
     .     - s14**2*s23**2/(2d0*s12*s13**2*s34)
     .     - 2d0*(s13*s24-s14*s23)**2/(s12**2*s34**2)+s24/s13
     .     + s14*s23/s13**2
     .     - 2d0

      return
      end

************************************************************************

      real(8) function fun2C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun2C =
     .     (
     .     + s12*s34*(s12*s34+s23*(s24+2d0*s23-s14))
     .     + s23**2*(s24+s14)**2
     .     )/(2*s12**3*s34)

      return
      end

************************************************************************

      real(8) function fun3C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun3C =
     .     + s34/(2d0*s23)
     .     + s23*(s24+s14)*(s24+4d0*s23+3d0*s14)/(2d0*s12**2*s34)
     .     + (3d0*s24+4d0*s23)/(2d0*s12)

      return
      end

************************************************************************

      real(8) function fun4C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun4C =
     .     - 2d0*s34/s23
     .     - s23*(s24+s14)*(s24+2d0*s23+5d0*s14)/(2d0*s12**2*s34)
     .     - (4d0*s24+6*s23-3d0*s14)/(2d0*s12)

      return
      end

************************************************************************

      real(8) function fun5C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1=i1
      j2=i2
      j3=i3
      j4=i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun5C =
     .     - (
     .     + s24**2*(s34**2-s24*s34+s13*s34-s13*s24+s14*s23)
     .     + s14*s23*(2d0*s24*s34-s13*s24+s14*s23)
     .     )/(s14*s24**2*s34)

      return
      end

************************************************************************

      real(8) function fun6C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1=i1
      j2=i2
      j3=i3
      j4=i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun6C =
     .     + s12*s34/(2d0*s13*s23)
     .     + (
     .     + 4d0*s23*s24+2d0*s14*s24
     .     - 3d0*s13*s24+3d0*s14*s23
     .     )/(2d0*s12*s34)
     .     + s14**2*s23/(2d0*s12*s13*s34)
     .     - s14/s13
     .     + 0.5d0

      return
      end

************************************************************************

      real(8) function fun7C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun7C =
     .     (
     .     + s14**2*s23**2
     .     + s13*s34**2*s12
     .     - s13*s14*s23*s24
     .     )/2/s13**2/s34/s12

      return
      end

************************************************************************

      real(8) function fun8C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun8C = (s14*s23-s13*s24)/s12/s34/2d0

      return
      end

************************************************************************

      real(8) function fun9C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun9C =
     .     + s13*s24**2/(s12*s23*s34)
     .     - s12*s34/(s13*s23)
     .     - (
     .     + 2d0*s24**2
     .     + 2d0*s23*s24
     .     + 5d0*s14*s24
     .     - 5d0*s13*s24
     .     + 5d0*s14*s23
     .     )/(2d0*s12*s34)
     .     - s14**2*s23/(s12*s13*s34)
     .     - 2d0*s24/s23
     .     + 2d0*s14/s13
     .     -1d0

      return
      end

************************************************************************

      real(8) function fun10C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun10C = (
     .     + s12*s23*s34**2
     .     + s13**2*s24**2
     .     - s13*s14*s23*s24
     .     )/(s12*s23**2*s34)

      return
      end

************************************************************************

      real(8) function fun11C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1=i1
      j2=i2
      j3=i3
      j4=i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun11C = 2d0*s13*s24/s12/s34

      return
      end

************************************************************************

      real(8) function fun12C(i1,i2,i3,i4)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4
      integer              :: j1,j2,j3,j4
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      fun12C =
     .     + s13*(s13*(s14-s24)+2d0*s14*s23)/2/s12**2/s34
     .     + s14/s12/2d0

      return
      end

c-----------------------------------------------------------------------

c     Full one-loop matrix element for
c     H -> q(i1) qbar(i2) q(i3) qbar(i4).
c     Adapted from MCFM/NNLOJET (src/process/H/libCDHloop.f).
      real(8) function FullD0g1H(p,iq1,iQbar4,iQ3,iqbar2,
     .     renscale2,ipole)
      implicit none
      integer, intent(in) :: iq1,iqbar2,iQ3,iQbar4,ipole
      real(8), intent(in) :: p(1:4,5),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      real(8)             :: fac
      real(8)             :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external   :: C0g1H,Ct0g1H,Ch0g1H
      real(8), external   :: D0g1H,Dt0g1H,Dh0g1H
      real(8), external   :: C0g0H,D0g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*cn

      FullD0g1H = 1d0/2d0*fac*(
     .     + C0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     + C0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)

     .     - 1d0/cn**2*(
     .     + Ct0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     + Ct0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)
     .     )

     .     + nf/cn*(
     .     + Ch0g1H(p,iq1,iQbar4,iQ3,iqbar2,renscale2,ipole)
     .     + Ch0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)
     .     )

     .     - 1d0/cn*(
     .     + D0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)
     .     + 1d0/cn**2*Dt0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)
     .     - nf/cn*Dh0g1H(p,iq1,iqbar2,iQ3,iQbar4,renscale2,ipole)
     .     )
     .     )

c     Include O(as) Wilson coefficient.
      if (ipole.eq.0)then
         FullD0g1H = FullD0g1H
     .        + 1d0/2d0*(11d0/3d0)*fac*(
     .        + C0g0H(p,iq1,iQbar4,iQ3,iqbar2)
     .        + C0g0H(p,iq1,iqbar2,iQ3,iQbar4)
     .        - 1d0/cn*D0g0H(p,iq1,iQbar4,iQ3,iqbar2)
     .        )
      endif

      return
      end

************************************************************************

      real(8) function D0g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(1:4,5),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Local variables.
      integer             :: j1,j2,j3,j4
      integer             :: ischeme,imemode
      real(8)             :: mhsq,musq
      real(8)             :: born,tree,virt,ren
      real(8)             :: s12,s13,s14,s23,s24,s34
      real(8)             :: s123,s124,s134,s234,s1234
      real(8)             :: s(5,5)
      complex(8)          :: zA(5,5), zB(5,5)
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB
c     Externals.
      real(8), external     :: A2g0H,D0g0H
      real(8), external     :: fun1D,fun2D,fun3D,fun4D
      real(8), external     :: fun5D,fun6D,fun7D,fun8D
      complex(8), external  :: L0,L1,Lsm1,Lsm1_2me,lnrat

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Set permutations.
      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = D0g0H(p,j1,j2,j3,j4)/born

c     Set invariants.
      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s234 = s23+s24+s34
      s134 = s13+s14+s34

c     Set scales.
      mhsq = s12+s13+s14+s23+s24+s34
      musq = renscale2

c     Calculate Born-one-loop interference.
      ren = 0d0
      if (ipole.eq.-2)then
         virt = (-2d0)*tree
      elseif (ipole.eq.-1)then
         virt = (
     .        - 3d0
     .        + dble(lnrat(-s24,musq))
     .        + dble(lnrat(-s13,musq))
     .        )*tree
      elseif (ipole.eq.0)then
c     Terms proportional to tree.
         virt = (
     .        + 80d0/9d0
     .        - dble(Lsm1_2me(s123,s134,s13,mhsq))
     .        - dble(Lsm1_2me(s124,s234,s24,mhsq))
     .        - 13d0/12d0*dble(lnrat(-s14,musq))
     .        - 13d0/12d0*dble(lnrat(-s23,musq))
     .        - 13d0/12d0*dble(lnrat(-s12,musq))
     .        - 13d0/12d0*dble(lnrat(-s34,musq))
     .        - 1d0/2d0*dble(lnrat(-s24,musq)**2)
     .        - 1d0/2d0*dble(lnrat(-s13,musq)**2)
     .        )*tree

c     Terms not proportional to tree.
         virt = virt
     .        - 2d0*(
     .        - dble(Lsm1(-s12,-s124,-s24,-s124))
     .        *fun1D(s12,s13,s14,s23,s24,s34)
     .        - dble(Lsm1(-s23,-s234,-s24,-s234))
     .        *fun1D(s23,s13,s34,s12,s24,s14)
     .        - dble(Lsm1(-s14,-s124,-s24,-s124))
     .        *fun1D(s14,s13,s12,s34,s24,s23)
     .        - dble(Lsm1(-s34,-s234,-s24,-s234))
     .        *fun1D(s34,s13,s23,s14,s24,s12)
     .        - dble(Lsm1(-s34,-s134,-s13,-s134))
     .        *fun1D(s12,s13,s14,s23,s24,s34)
     .        - dble(Lsm1(-s14,-s134,-s13,-s134))
     .        *fun1D(s23,s13,s34,s12,s24,s14)
     .        - dble(Lsm1(-s12,-s123,-s13,-s123))
     .        *fun1D(s14,s13,s12,s34,s24,s23)
     .        - dble(Lsm1(-s23,-s123,-s13,-s123))
     .        *fun1D(s34,s13,s23,s14,s24,s12)
     .        + dble(L1(-s134,-s34))*fun3D(s34,s13,s23,s14,s24,s12)
     .        + dble(L1(-s134,-s14))*fun3D(s14,s13,s12,s34,s24,s23)
     .        + dble(L1(-s234,-s34))*fun3D(s34,s24,s14,s23,s13,s12)
     .        + dble(L1(-s124,-s14))*fun3D(s14,s24,s34,s12,s13,s23)
     .        + dble(L1(-s123,-s12))*fun3D(s12,s13,s14,s23,s24,s34)
     .        + dble(L1(-s123,-s23))*fun3D(s23,s13,s34,s12,s24,s14)
     .        + dble(L1(-s124,-s12))*fun3D(s12,s24,s23,s14,s13,s34)
     .        + dble(L1(-s234,-s23))*fun3D(s23,s24,s12,s34,s13,s14)
     .        + dble(L0(-s134,-s34))*fun4D(s34,s13,s23,s14,s24,s12)
     .        + dble(L0(-s134,-s14))*fun4D(s14,s13,s12,s34,s24,s23)
     .        + dble(L0(-s234,-s34))*fun4D(s34,s24,s14,s23,s13,s12)
     .        + dble(L0(-s124,-s14))*fun4D(s14,s24,s34,s12,s13,s23)
     .        + dble(L0(-s123,-s12))*fun4D(s12,s13,s14,s23,s24,s34)
     .        + dble(L0(-s123,-s23))*fun4D(s23,s13,s34,s12,s24,s14)
     .        + dble(L0(-s124,-s12))*fun4D(s12,s24,s23,s14,s13,s34)
     .        + dble(L0(-s234,-s23))*fun4D(s23,s24,s12,s34,s13,s14)
     .        + dble(lnrat(-s134,-s34))*fun6D(s34,s13,s23,s14,s24,s12)
     .        + dble(lnrat(-s134,-s14))*fun6D(s14,s13,s12,s34,s24,s23)
     .        + dble(lnrat(-s234,-s34))*fun6D(s34,s24,s14,s23,s13,s12)
     .        + dble(lnrat(-s124,-s14))*fun6D(s14,s24,s34,s12,s13,s23)
     .        + dble(lnrat(-s123,-s12))*fun6D(s12,s13,s14,s23,s24,s34)
     .        + dble(lnrat(-s123,-s23))*fun6D(s23,s13,s34,s12,s24,s14)
     .        + dble(lnrat(-s124,-s12))*fun6D(s12,s24,s23,s14,s13,s34)
     .        + dble(lnrat(-s234,-s23))*fun6D(s23,s24,s12,s34,s13,s14)
     .        + fun8D(s34,s13,s23,s14,s24,s12)
     .        + fun8D(s14,s13,s12,s34,s24,s23)
     .        + fun8D(s34,s24,s14,s23,s13,s12)
     .        + fun8D(s14,s24,s34,s12,s13,s23)
     .        + fun8D(s12,s13,s14,s23,s24,s34)
     .        + fun8D(s23,s13,s34,s12,s24,s14)
     .        + fun8D(s12,s24,s23,s14,s13,s34)
     .        + fun8D(s23,s24,s12,s34,s13,s14)
     .        )/s1234**2


c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
         ischeme = 0
         if (ischeme.eq.1) ren = 2d0*pi**2/12d0
      endif

      D0g1H = virt + ren*tree
      D0g1H = D0g1H*born

      return
      end

************************************************************************

      real(8) function Dt0g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in)  :: i1,i2,i3,i4,ipole
      real(8), intent(in)  :: p(1:4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: j1,j2,j3,j4
      integer              :: ischeme,imemode
      real(8)              :: mhsq,musq
      real(8)              :: born,tree,virt,ren
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s123,s124,s134,s234,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,D0g0H
      real(8), external    :: fun1D,fun2D,fun3D,fun4D
      real(8), external    :: fun5D,fun6D,fun7D,fun8D
      complex(8), external :: L0,L1,Lsm1,Lsm1_2me,lnrat
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Set permutations.
      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = D0g0H(p,j1,j2,j3,j4)/born

c     Set invariants.
      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s234 = s23+s24+s34
      s134 = s13+s14+s34

c     Set scales.
      mhsq = s12+s13+s14+s23+s24+s34
      musq = renscale2

c     Calculate Born-one-loop interference.
      ren = 0d0
      if (ipole.eq.-2)then
         virt = (+2d0)*tree
      elseif (ipole.eq.-1)then
         virt = (
     .        + 3d0
     .        - dble(lnrat(-s14,musq))
     .        - dble(lnrat(-s23,musq))
     .        - dble(lnrat(-s12,musq))
     .        - dble(lnrat(-s34,musq))
     .        + dble(lnrat(-s24,musq))
     .        + dble(lnrat(-s13,musq))
     .        )*tree
      elseif (ipole.eq.0)then
c     Terms proportional to tree.
         virt = (
     .        + 8d0
     .        + dble(Lsm1_2me(s123,s234,s23,mhsq))
     .        + dble(Lsm1_2me(s123,s124,s12,mhsq))
     .        + dble(Lsm1_2me(s134,s234,s34,mhsq))
     .        + dble(Lsm1_2me(s124,s134,s14,mhsq))
     .        - dble(Lsm1_2me(s123,s134,s13,mhsq))
     .        - dble(Lsm1_2me(s124,s234,s24,mhsq))
     .        - 3d0/4d0*dble(lnrat( -s14,musq))
     .        + 1d0/2d0*dble(lnrat(-s14,musq)**2)
     .        - 3d0/4d0*dble(lnrat(-s23,musq))
     .        + 1d0/2d0*dble(lnrat(-s23,musq)**2)
     .        - 3d0/4d0*dble(lnrat(-s12,musq))
     .        + 1d0/2d0*dble(lnrat(-s12,musq)**2)
     .        - 3d0/4d0*dble(lnrat(-s34,musq))
     .        + 1d0/2d0*dble(lnrat(-s34,musq)**2)
     .        - 1d0/2d0*dble(lnrat(-s24,musq)**2)
     .        - 1d0/2d0*dble(lnrat(-s13,musq)**2)
     .        )*tree

c     Terms not proportional to tree.
         virt = virt
     .        - 2d0*(
     .        - dble(Lsm1(-s12,-s124,-s24,-s124))
     .        *fun1D(s12,s13,s14,s23,s24,s34)
     .        - dble(Lsm1(-s23,-s234,-s24,-s234))
     .        *fun1D(s23,s13,s34,s12,s24,s14)
     .        - dble(Lsm1(-s14,-s124,-s24,-s124))
     .        *fun1D(s14,s13,s12,s34,s24,s23)
     .        - dble(Lsm1(-s34,-s234,-s24,-s234))
     .        *fun1D(s34,s13,s23,s14,s24,s12)
     .        - dble(Lsm1(-s34,-s134,-s13,-s134))
     .        *fun1D(s12,s13,s14,s23,s24,s34)
     .        - dble(Lsm1(-s14,-s134,-s13,-s134))
     .        *fun1D(s23,s13,s34,s12,s24,s14)
     .        - dble(Lsm1(-s12,-s123,-s13,-s123))
     .        *fun1D(s14,s13,s12,s34,s24,s23)
     .        - dble(Lsm1(-s23,-s123,-s13,-s123))
     .        *fun1D(s34,s13,s23,s14,s24,s12)
     .        - dble(Lsm1(-s12,-s123,-s23,-s123))
     .        *fun2D(s12,s13,s14,s23,s24,s34)
     .        - dble(Lsm1(-s23,-s123,-s12,-s123))
     .        *fun2D(s23,s13,s34,s12,s24,s14)
     .        - dble(Lsm1(-s12,-s124,-s14,-s124))
     .        *fun2D(s12,s24,s23,s14,s13,s34)
     .        - dble(Lsm1(-s14,-s124,-s12,-s124))
     .        *fun2D(s14,s24,s34,s12,s13,s23)
     .        - dble(Lsm1(-s34,-s234,-s23,-s234))
     .        *fun2D(s23,s24,s12,s34,s13,s14)
     .        - dble(Lsm1(-s23,-s234,-s34,-s234))
     .        *fun2D(s34,s24,s14,s23,s13,s12)
     .        - dble(Lsm1(-s34,-s134,-s14,-s134))
     .        *fun2D(s34,s13,s23,s14,s24,s12)
     .        - dble(Lsm1(-s34,-s134,-s14,-s134))
     .        *fun2D(s14,s13,s12,s34,s24,s23)
     .        + dble(L1(-s134,-s34))*fun3D(s34,s13,s23,s14,s24,s12)
     .        + dble(L1(-s134,-s14))*fun3D(s14,s13,s12,s34,s24,s23)
     .        + dble(L1(-s234,-s34))*fun3D(s34,s24,s14,s23,s13,s12)
     .        + dble(L1(-s124,-s14))*fun3D(s14,s24,s34,s12,s13,s23)
     .        + dble(L1(-s123,-s12))*fun3D(s12,s13,s14,s23,s24,s34)
     .        + dble(L1(-s123,-s23))*fun3D(s23,s13,s34,s12,s24,s14)
     .        + dble(L1(-s124,-s12))*fun3D(s12,s24,s23,s14,s13,s34)
     .        + dble(L1(-s234,-s23))*fun3D(s23,s24,s12,s34,s13,s14)
     .        + dble(L0(-s134,-s34))*fun5D(s34,s13,s23,s14,s24,s12)
     .        + dble(L0(-s134,-s14))*fun5D(s14,s13,s12,s34,s24,s23)
     .        + dble(L0(-s234,-s34))*fun5D(s34,s24,s14,s23,s13,s12)
     .        + dble(L0(-s124,-s14))*fun5D(s14,s24,s34,s12,s13,s23)
     .        + dble(L0(-s123,-s12))*fun5D(s12,s13,s14,s23,s24,s34)
     .        + dble(L0(-s123,-s23))*fun5D(s23,s13,s34,s12,s24,s14)
     .        + dble(L0(-s124,-s12))*fun5D(s12,s24,s23,s14,s13,s34)
     .        + dble(L0(-s234,-s23))*fun5D(s23,s24,s12,s34,s13,s14)
     .        + dble(lnrat(-s134,-s34))*fun7D(s34,s13,s23,s14,s24,s12)
     .        + dble(lnrat(-s134,-s14))*fun7D(s14,s13,s12,s34,s24,s23)
     .        + dble(lnrat(-s234,-s34))*fun7D(s34,s24,s14,s23,s13,s12)
     .        + dble(lnrat(-s124,-s14))*fun7D(s14,s24,s34,s12,s13,s23)
     .        + dble(lnrat(-s123,-s12))*fun7D(s12,s13,s14,s23,s24,s34)
     .        + dble(lnrat(-s123,-s23))*fun7D(s23,s13,s34,s12,s24,s14)
     .        + dble(lnrat(-s124,-s12))*fun7D(s12,s24,s23,s14,s13,s34)
     .        + dble(lnrat(-s234,-s23))*fun7D(s23,s24,s12,s34,s13,s14)
     .        + fun8D(s34,s13,s23,s14,s24,s12)
     .        + fun8D(s14,s13,s12,s34,s24,s23)
     .        + fun8D(s34,s24,s14,s23,s13,s12)
     .        + fun8D(s14,s24,s34,s12,s13,s23)
     .        + fun8D(s12,s13,s14,s23,s24,s34)
     .        + fun8D(s23,s13,s34,s12,s24,s14)
     .        + fun8D(s12,s24,s23,s14,s13,s34)
     .        + fun8D(s23,s24,s12,s34,s13,s14)
     .        )/s1234**2

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
         ischeme = 0
         if (ischeme.eq.1) ren = 2d0*pi**2/12d0
      endif

      Dt0g1H = virt - ren*tree
      Dt0g1H = Dt0g1H*born

      return
      end

************************************************************************

      real(8) function Dh0g1H(p,i1,i2,i3,i4,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4,ipole
      real(8), intent(in) :: p(1:4,5),renscale2
c     Parameters.
      real(8), parameter   :: pi=3.141592653589793238d0
c     Local variables.
      integer              :: j1,j2,j3,j4
      integer              :: ischeme,imemode
      real(8)              :: mhsq,musq
      real(8)              :: born,tree,virt,ren
      real(8)              :: s12,s13,s14,s23,s24,s34
      real(8)              :: s123,s124,s134,s234,s1234
      real(8)              :: s(5,5)
      complex(8)           :: zA(5,5),zB(5,5)
c     Externals.
      real(8), external    :: A2g0H,D0g0H
      real(8), external    :: fun1D,fun2D,fun3D,fun4D
      real(8), external    :: fun5D,fun6D,fun7D,fun8D
      complex(8), external :: L0,L1,Lsm1,Lsm1_2me,lnrat
c     Common blocks.
      common/memode/imemode
      common/kin5/s,zA,zB

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Set permutations.
      j1 = i1
      j2 = i2
      j3 = i3
      j4 = i4

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = A2g0H(s1234)

c     Calculate tree-level amplitude squared.
      tree = D0g0H(p,j1,j2,j3,j4)/born

c     Set invariants.
      s12 = s(j1,j2)
      s13 = s(j1,j3)
      s14 = s(j1,j4)
      s23 = s(j2,j3)
      s24 = s(j2,j4)
      s34 = s(j3,j4)

      s123 = s12+s13+s23
      s124 = s12+s14+s24
      s234 = s23+s24+s34
      s134 = s13+s14+s34

c     Set scales.
      mhsq = s12+s13+s14+s23+s24+s34
      musq = renscale2

c     Calculate Born-one-loop interference.
      if (ipole.eq.-2)then
         virt = 0d0
      elseif (ipole.eq.-1)then
         virt = 0d0
      elseif (ipole.eq.0)then
         virt = 1d0/2d0*(
     .        - 40d0/9d0
     .        + 2d0/3d0*dble(lnrat(-s14,musq))
     .        + 2d0/3d0*dble(lnrat(-s23,musq))
     .        + 2d0/3d0*dble(lnrat(-s12,musq))
     .        + 2d0/3d0*dble(lnrat(-s34,musq))
     .        )*tree
      endif

      Dh0g1H = -virt
      Dh0g1H = Dh0g1H*born

      return
      end

c-----------------------------------------------------------------------
c     Loop functions for H -> q qbar q qbar (same-flavour).

      real(8) function fun1D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun1D = (
     .     - 2d0*s12*s13*s24*s34 + s12*s13**2*s34
     .     - 4d0*s12*s14*s23*s34 + s12*s24**2*s34
     .     + 2d0*s12**2*s34**2 - 2d0*s13*s14*s23*s24
     .     - s13*s24**3 + s13**2*s14*s23
     .     - s13**3*s24 + s14*s23*s24**2 + 2d0*s14**2*s23**2
     .     )/(4d0*s12*s23*s14*s34)

      return
      end

************************************************************************

      real(8) function fun2D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun2D = (
     .     - 2d0*s12*s13*s14*s23*s24*s34
     .     + 2d0*s12*s13**2*s14*s23*s34
     .     - 4d0*s12*s13**2*s24**2*s34
     .     + 3d0*s12*s13**3*s24*s34
     .     - 2d0*s12*s13**4*s34
     .     + s12*s14**2*s23**2*s34
     .     + 3d0*s12**2*s13*s24*s34**2
     .     - 3d0*s12**2*s13**2*s34**2
     .     + s12**2*s14*s23*s34**2
     .     - s12**3*s34**3
     .     + 3d0*s13*s14**2*s23**2*s24
     .     - 4d0*s13**2*s14*s23*s24**2
     .     - 3d0*s13**2*s14**2*s23**2
     .     + 3d0*s13**3*s14*s23*s24
     .     + 2d0*s13**3*s24**3
     .     - 2d0*s13**4*s14*s23
     .     + 2d0*s13**5*s24
     .     - s14**3*s23**3
     .     )/(8d0*s12*s13**2*s23*s14*s34)

      return
      end

************************************************************************

      real(8) function fun3D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun3D = (
     .     - 2d0*s12*s14*s23*s34
     .     + s12*s23*s24*s34
     .     + s12*s23**2*s34
     .     + s12**2*s34**2
     .     + s14*s23**2*s24
     .     + s14*s23**3
     .     + s14**2*s23**2
     .     + s23**3*s24
     .     )/(8d0*s12**2*s14*s23)

      return
      end

************************************************************************

      real(8) function fun4D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun4D = (
     .     - 2d0*s12*s23*s34
     .     + 5d0*s12*s24*s34
     .     - 3d0*s14*s23*s24
     .     + 6d0*s14*s23**2
     .     + 4d0*s23*s24**2
     .     - s23**2*s24
     .     )/(8d0*s14*s12*s23)

      return
      end

************************************************************************

      real(8) function fun5D(s12,s13,s14,s23,s24,s34)
      implicit none
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34

      fun5D = (
     .     + s12*s14*s23**2*s24*s34
     .     - 6d0*s12*s14*s23**3*s34
     .     + 2d0*s12*s14**2*s23**2*s34
     .     - 2d0*s12*s23**2*s24**2*s34
     .     + 3d0*s12*s23**3*s24*s34
     .     + 2d0*s12**2*s14*s23*s34**2
     .     - 3d0*s12**2*s23*s24*s34**2
     .     + 2d0*s12**2*s23**2*s34**2
     .     - 2d0*s12**3*s34**3
     .     - 2d0*s14*s23**3*s24**2
     .     - 4d0*s14**2*s23**3*s24
     .     - 2d0*s14**3*s23**3
     .     )/(8d0*s12**2*s23**2*s14*s34)

      return
      end

************************************************************************

      real(8) function fun6D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun6D = (
     .     - 3d0*s12*s34
     .     + 3d0*s13*s24
     .     + 5d0*s14*s23
     .     - 2d0*s23*s24
     .     + 4d0*s24**2
     .     )/(8d0*s14*s23)

      return
      end

************************************************************************

      real(8) function fun7D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun7D = (
     .     - 7d0*s12*s13*s14*s23**2*s34
     .     - 2d0*s12*s13*s23*s24**2*s34
     .     + 2d0*s12*s13*s23**2*s24*s34
     .     - s12*s13**2*s23*s24*s34
     .     + 2d0*s12*s14**2*s23**2*s34
     .     + s12**2*s13*s23*s34**2
     .     + 2d0*s12**2*s14*s23*s34**2
     .     - 2d0*s12**3*s34**3
     .     - 2d0*s13*s14*s23**2*s24**2
     .     - 2d0*s14**3*s23**3
     .     )/(8d0*s12*s13*s23**2*s14*s34)

      return
      end

************************************************************************

      real(8) function fun8D(s12,s13,s14,s23,s24,s34)
      implicit none
      real(8)    :: s123,s124,s134,s234,s12,s13,s14,s23,s24,s34
      complex(8) :: L0,L1,Lsm1,Lsm1_2me,lnrat

      fun8D = (
     .     - 2d0*s12*s13*s14*s24
     .     - 2d0*s12*s13*s23*s24
     .     + s12*s13*s23**2
     .     + s12*s13*s24**2
     .     + s12*s13**2*s24
     .     + 2d0*s12*s14*s23**2
     .     + 2d0*s12*s14*s34**2
     .     + 2d0*s12*s14**2*s23
     .     + s12*s14**2*s24
     .     + 2d0*s12*s23*s34**2+s12**2*s13*s23
     .     + s12**2*s14*s24
     .     + 2d0*s12**2*s14*s34
     .     + 2d0*s12**2*s23*s34
     .     - 2d0*s13*s14*s24*s34
     .     + s13*s14*s24**2
     .     + s13*s14*s34**2
     .     + s13*s14**2*s34
     .     - 2d0*s13*s23*s24*s34
     .     + s13*s23*s24**2
     .     + s13*s24**2*s34
     .     + s13**2*s14*s24
     .     + s13**2*s23*s24
     .     + s13**2*s24*s34
     .     + 2d0*s14*s23**2*s34
     .     + 2d0*s14**2*s23*s34
     .     + s23*s24*s34**2
     .     + s23**2*s24*s34
     .     )/(64d0*s12*s14*s23*s34)

      return
      end

c-----------------------------------------------------------------------
c     Auxiliary functions needed for H -> 4j one-loop amplitudes.
c-----------------------------------------------------------------------

      complex*16 function zab2(j1,j2,j3,j4)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      real*8     :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      zab2=zA(j1,j2)*zB(j2,j4)+zA(j1,j3)*zB(j3,j4)

      return
      end

************************************************************************

      complex*16 function zba2(j1,j2,j3,j4)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      real*8     :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      zba2=zB(j1,j2)*zA(j2,j4)+zB(j1,j3)*zA(j3,j4)

      return
      end

************************************************************************

      real*8 function ss3(j1,j2,j3)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      real*8     :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      ss3=s(j1,j2)+s(j2,j3)+s(j3,j1)

      return
      end

************************************************************************

      complex*16 function  zab3(j1,j2,j3,j4)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      real*8     :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      zab3=zA(j1,j2)*zB(j2,j3)*zA(j3,j4)

      return
      end

************************************************************************

      complex*16 function  zba3(j1,j2,j3,j4)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      real*8     :: s(5,5)
      complex*16 :: zA(5,5),zB(5,5)
c     Common blocks.
      common/kin5/s,zA,zB

      zba3=zB(j1,j2)*zA(j2,j3)*zB(j3,j4)

      return
      end

************************************************************************

      complex*16 function F31m(s,renscale2)
      common/order/ieorder
      real*8 s,renscale2
      complex*16 lnrat
      integer ieorder

      if(ieorder.eq.-2)then
        F31m=1d0
      elseif(ieorder.eq.-1)then
        F31m=-lnrat(-s,renscale2)
      elseif(ieorder.eq.0)then
        F31m=+0.5d0*lnrat(-s,renscale2)**2
      endif

      return
      end

************************************************************************

c     Note: ordering of arguments to function is taken from e.g.
c     arXiV:0804.4149v3 (App. B) and not hep-ph/0607139 (Eq. 21).
      complex*16 function F41m(psq,s,t,renscale2)
      implicit none
      real*8 s,t,psq,renscale2
      complex*16 F31m,F41mF
      integer ieorder
      common /order/ieorder

      F41m=2d0*(F31m(s,renscale2)+F31m(t,renscale2)
     .     -F31m(psq,renscale2)+F41mF(psq,s,t))

      return
      end

************************************************************************

c     Note: ordering of arguments to function is taken from e.g.
c     arXiV:0804.4149v3 (App. B) and not hep-ph/0607139 (Eq. 21).
      complex*16 function F41mF(psq,s,t)
      implicit none
      real*8 s,t,psq
      complex*16 Lsm1
      integer ieorder
      common/order/ieorder

      if (ieorder.eq.-2)then
         F41mF=0d0
      elseif (ieorder.eq.-1)then
         F41mF=0d0
      elseif (ieorder.eq.0)then
         F41mF=Lsm1(-s,-psq,-t,-psq)
      endif

      return
      end

************************************************************************

c     Note: ordering of arguments to function is taken from e.g.
c     arXiV:0804.4149v3 (App. B) and not hep-ph/0607139 (Eq. 22).
      complex*16 function F42me(psq,qsq,s,t,renscale2)
      implicit none
      real*8 s,t,psq,qsq,renscale2
      complex*16 F31m,F42meF
      integer ieorder
      common/order/ieorder

      F42me=2d0*(F31m(s,renscale2)+F31m(t,renscale2)-F31m(psq,renscale2)
     .          -F31m(qsq,renscale2)+F42meF(psq,qsq,s,t))

      return
      end

************************************************************************

c     Note: ordering of arguments to function is taken from e.g.
c     arXiV:0804.4149v3 (App. B) and not hep-ph/0607139 (Eq. 22).
      complex*16 function F42meF(psq,qsq,s,t)
      implicit none
      real*8 s,t,psq,qsq
      complex*16 Lsm1_2me
      integer ieorder
      common/order/ieorder

      if (ieorder.eq.-2)then
         F42meF=0d0
      elseif (ieorder.eq.-1)then
         F42meF=0d0
      elseif (ieorder.eq.0)then
         F42meF=Lsm1_2me(s,t,psq,qsq)
      endif

      return
      end

************************************************************************

c     Note reference to BGMW version of the finite piece of the
c     box integrals, which is twice the definition in previous papers.
c     Note: second term has 3rd and 4th arguments switched
c     compared to BGMW paper.
      complex*16 function W(mhsq,s234,s12,s23,s34,s14)
      implicit none
      complex*16 F41mF_BGMW,F42mhF_BGMW
      real*8 mhsq,s234,s12,s23,s34,s14

      W=F41mF_BGMW(s234,s23,s34)
     . +F42mhF_BGMW(mhsq,s23,s14,s234)
     . +F42mhF_BGMW(mhsq,s34,s12,s234)

      return
      end

************************************************************************

c     These are just aliases to previously-defined finite pieces
c     of the box functions, but with an additional factor of two.
      complex*16 function F41mF_BGMW(psq,s,t)
      implicit none
      complex*16 F41mF
      real*8 psq,s,t

      F41mF_BGMW=2d0*F41mF(psq,s,t)

      return
      end

************************************************************************

      complex*16 function F42mhF_BGMW(psq,qsq,s,t)
      implicit none
      complex*16 F42mhF
      real*8 psq,qsq,s,t

      F42mhF_BGMW=2d0*F42mhF(psq,qsq,s,t)

      return
      end

************************************************************************

      complex*16 function F42mhF(psq,qsq,s,t)
      implicit none
      real*8 s,t,psq,qsq
      complex*16 Lsm1_2mht

      F42mhF=Lsm1_2mht(s,t,psq,qsq)

      return
      end

************************************************************************

      complex*16 function F33m(p1sq,p2sq,p3sq)
      implicit none
      real*8 p1sq,p2sq,p3sq
      complex*16 I3m,zf33m

      zf33m=I3m(p1sq,p2sq,p3sq)

      F33m=zf33m

      return
      end

************************************************************************

c     Combinations of bubble integrals, 0704.3914v3 Eq. (3.21).
c     The hatted versions of these functions are further defined
c     by Eqs. (3.25), (3.26) and (3.27)
      complex*16 function BGRL0(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t

      BGRL0=lnrat(-s,-t)

      return
      end

************************************************************************

      complex*16 function BGRL1(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t

      BGRL1=lnrat(-s,-t)/dcmplx(s-t)

      return
      end

************************************************************************

      complex*16 function BGRL2(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t

      BGRL2=lnrat(-s,-t)/dcmplx(s-t)**2

      return
      end

************************************************************************

      complex*16 function BGRL2hat(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t,ratio,onemratio

      ratio = t/s
      onemratio = abs(1d0-ratio)

      if (onemratio.ge.2d-5)then
         BGRL2hat = lnrat(-s,-t)/dcmplx(s-t)**2
     .        - dcmplx(0.5d0*(1d0/s+1d0/t)/(s-t))
      elseif (onemratio.le.2d-5)then
         BGRL2hat =
     .        - (ratio**(-1d0)-1d0)*(6d0*s**2d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)**2d0*(12d0*s**2d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)**3d0*(30d0*s**2d0)**(-1d0)
     .        + (ratio**(-1d0)-1d0)**4d0*(60d0*s**2d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)**5d0*(105d0*s**2d0)**(-1d0)

      endif

      return

      end

************************************************************************

      complex*16 function BGRL3(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t

      BGRL3 = lnrat(-s,-t)/dcmplx(s-t)**3

      return
      end

************************************************************************

      complex*16 function BGRL3hat(s,t)
      implicit none
      complex*16 lnrat
      real*8 s,t,ratio,onemratio

      ratio = t/s
      onemratio = abs(1d0-ratio)

      if (onemratio.ge.1d-5)then
         BGRL3hat = lnrat(-s,-t)/dcmplx(s-t)**3
     .        - dcmplx(0.5d0*(1d0/s+1d0/t)/(s-t)**2)
      elseif(onemratio.le.1d-5)then
         BGRL3hat =
     .        - (6d0*s**3d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)*(4d0*s**3d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)**2d0*(20d0*s**3d0)**(-1d0)
     .        + (ratio**(-1d0)-1d0)**3d0*(60d0*s**3d0)**(-1d0)
     .        - (ratio**(-1d0)-1d0)**4d0*(140d0*s**3d0)**(-1d0)
      endif

      return
      end

c-----------------------------------------------------------------------
c     Library of sub-layer functions.
c-----------------------------------------------------------------------

      complex*16 function L0(x,y)
      implicit none
      complex*16 Lnrat,cone
      real*8 x,y,denom

      cone = (1d0,0d0)

      denom = 1d0-x/y
      if (abs(denom) .lt. 1d-7) then
         L0 = -cone-dcmplx(denom*(0.5d0+denom/3d0))
      else
         L0 = Lnrat(x,y)/dcmplx(denom)
      endif

      return
      end

************************************************************************

      complex*16 function L1(x,y)
      implicit none
      real*8 x,y,denom
      complex*16 L0,cone

      cone = (1d0,0d0)

      denom = 1d0-x/y
      if (abs(denom) .lt. 1d-7) then
         L1 = -0.5d0*cone-dcmplx(denom/3d0*(1d0+0.75d0*denom))
      else
         L1 = (L0(x,y)+cone)/dcmplx(denom)
      endif

      return
      end

************************************************************************

      complex*16 function L2(x,y)
      implicit none
      complex*16 Lnrat
      real*8 x,y,r,denom

      r = x/y
      denom = 1d0-r
      if (abs(denom) .lt. 1d-7) then
         L2 = (dcmplx(10d0)+denom*(dcmplx(15d0)+dcmplx(18d0)*denom))
     .        /dcmplx(60d0)
      else
         L2 = (Lnrat(x,y)-dcmplx(0.5d0*(r-1d0/r)))/dcmplx(denom)**3
      endif

      return
      end

************************************************************************

c     Formula taken from Eq. (71) in arXiv:hep-ph/0006249v2
c     Lsm1_2me notation follows from Eqs. (I.13) in
c     arXiv:hep-ph/9306240.
C     Analytic continuation has been checked by calculating numerically.
      complex*16 function Lsm1_2me(s,t,m1sq,m3sq)
      implicit complex*16 (z)
      integer j
      real*8 s,t,m1sq,m3sq,ddilog,arg(4),omarg(4),f2me,htheta
      complex*16 Li2(4),wlog(4)
      real*8 pi,pisq,pisqo6

      pi=3.14159265358979311599d0
      pisq=pi*pi
      pisqo6=pisq/6d0
      zimpi=(0d0,3.14159265358979311599d0)

      f2me=(s+t-m1sq-m3sq)/(s*t-m1sq*m3sq)

      arg(1)=f2me*s
      arg(2)=f2me*t
      arg(3)=f2me*m1sq
      arg(4)=f2me*m3sq

      do j=1,4
         omarg(j)=1d0-arg(j)
         wlog(j)=log(abs(arg(j)))
     .     +zimpi*dcmplx(htheta(-arg(j))*sign(1d0,f2me))
         if (omarg(j) .gt. 1d0) then
             Li2(j)=dcmplx(pisqo6-ddilog(arg(j)))
     .       -wlog(j)*dcmplx(log(omarg(j)))
          else
             Li2(j)=dcmplx(ddilog(omarg(j)))
         endif
      enddo
      Lsm1_2me=Li2(1)+Li2(2)-Li2(3)-Li2(4)

      return
      end

************************************************************************

      complex*16 function Lsm1(x1,y1,x2,y2)
      implicit none
      real*8 x1,x2,y1,y2,r1,r2,omr1,omr2,ddilog
      complex*16 dilog1,dilog2,Lnrat
      real*8 pi,pisq,pisqo6

      pi=3.14159265358979311599d0
      pisq=pi*pi
      pisqo6=pisq/6d0

      r1=x1/y1
      r2=x2/y2
      omr1=1d0-r1
      omr2=1d0-r2
      if (omr1 .gt. 1d0) then
         dilog1=dcmplx(pisqo6-ddilog(r1))-Lnrat(x1,y1)*dcmplx(log(omr1))
      else
         dilog1=dcmplx(ddilog(omr1))
      endif
      if (omr2 .gt. 1d0) then
         dilog2=dcmplx(pisqo6-ddilog(r2))-Lnrat(x2,y2)*dcmplx(log(omr2))
      else
          dilog2=dcmplx(ddilog(omr2))
      endif
      lsm1=dilog1+dilog2+Lnrat(x1,y1)*Lnrat(x2,y2)-dcmplx(pisqo6)
      return
      end

************************************************************************

      complex*16 function Lsm1_2mht(s,t,m1sq,m2sq)
      implicit none
      real*8 s,t,m1sq,m2sq,ddilog,r1,r2,omr1,omr2
      complex*16 Lnrat,dilog1,dilog2
      real*8 pi,pisq,pisqo6

      pi=3.14159265358979311599d0
      pisq=pi*pi
      pisqo6=pisq/6d0

      r1=m1sq/t
      r2=m2sq/t
      omr1=1d0-r1
      omr2=1d0-r2

      if (omr1 .gt. 1d0) then
      dilog1=dcmplx(pisqo6-ddilog(r1))-Lnrat(-m1sq,-t)*dcmplx(log(omr1))
      else
      dilog1=dcmplx(ddilog(omr1))
      endif
      if (omr2 .gt. 1d0) then
      dilog2=dcmplx(pisqo6-ddilog(r2))-Lnrat(-m2sq,-t)*dcmplx(log(omr2))
      else
      dilog2=dcmplx(ddilog(omr2))
      endif
      lsm1_2mht=-dilog1-dilog2
     & +0.5d0*(Lnrat(-s,-m1sq)*Lnrat(-s,-m2sq)-Lnrat(-s,-t)**2)
      return
      end

************************************************************************

c     This is the function I3m, a massless triangle with all
c     three external lines offshell defined in arXiv:hep-ph/9708239.
c     Defined in their equation (II.9).
      complex*16 function I3m(s1,s2,s3)
      implicit none
      real*8 s1,s2,s3,smax,smid,smin,del3,rtdel3
      real*8 i3m1a,flag
      complex*16 i3m1b,zf33m

      smax=max(s1,s2,s3)
      smin=min(s1,s2,s3)
      smid=s1+s2+s3-smax-smin
      del3=s1**2+s2**2+s3**2-2d0*(s1*s2+s2*s3+s3*s1)

      if (del3 .gt. 0) then
         rtdel3=sqrt(del3)
         if (smax .lt. 0) then
c     Case all negative.
            flag=0d0
            i3m=i3m1b(smax,smid,smin,rtdel3,flag)
         elseif (smin .gt. 0) then
c     Case all positive.
            flag=0d0
            i3m=-i3m1b(-smin,-smid,-smax,rtdel3,flag)
         elseif ((smid .lt. 0) .and. (smin .lt. 0)) then
c     Case two negative and one positive.
            flag=+1d0
            zf33m=i3m1b(smin,smid,smax,rtdel3,flag)
            i3m=zf33m
         elseif ((smax .gt. 0).and.(smid .gt. 0)) then
c     Case two positive and one negative.
            flag=-1d0
            i3m=-i3m1b(-smax,-smid,-smin,rtdel3,flag)
         endif
      elseif (del3 .lt. 0) then
         rtdel3=sqrt(-del3)
         if (smax .lt. 0) then
c     Case all negative.
            i3m=+dcmplx(i3m1a(+s1,+s2,+s3,rtdel3))
         elseif (smin .gt. 0) then
c     Case all positive.
            i3m=-dcmplx(i3m1a(-s1,-s2,-s3,rtdel3))
         endif
      endif

      return
      end

************************************************************************

c     Symmetric form of SLAC-PUB-5809.
      real*8 function I3m1a(s1,s2,s3,rtmdel)
      implicit none
      real*8 s1,s2,s3,d1,d2,d3,rtmdel,arg1,arg2,arg3,dclaus

      d1=s1-s2-s3
      d2=s2-s3-s1
      d3=s3-s1-s2

      arg1=2d0*datan(rtmdel/d1)
      arg2=2d0*datan(rtmdel/d2)
      arg3=2d0*datan(rtmdel/d3)
      i3m1a=2d0/rtmdel*(Dclaus(arg1)+Dclaus(arg2)+Dclaus(arg3))

      return
      end

************************************************************************

c     Form of arXiv:hep-ph/9402223.
      complex*16 function I3m1b(s1,s2,s3,rtdel,flag)
      implicit none
      real*8 s1,s2,s3,d3,temp,ddilog,xlog,ylog,rat,pi
      real*8 x,y,rho,rtdel,argx,argy,argdlx,argdly,flag
      complex*16 impi

      pi=3.14159265358979311599d0
      impi=(0d0,3.14159265358979311599d0)
      d3=s3-s1-s2
      x=s1/s3
      y=s2/s3
      rat=0.5d0*(d3+rtdel)/s3
      if (abs(rat) .lt. 1d-3) rat=2d0*s1*s2/(s3*(d3-rtdel))
      rho=1d0/rat
      argx=rho*x
      argy=rho*y
      argdlx=-argx
      argdly=-argy

      if ((argdlx .gt. 1d0) .or. (argdly .gt. 1d0)) then
         stop
      endif

      xlog=log(abs(argx))
      ylog=log(abs(argy))
      temp=xlog*ylog+pi**2/3d0+(ylog-xlog)*log((1d0+argy)/(1d0+argx))
     &     +2d0*(ddilog(argdlx)+ddilog(argdly))
      I3m1b=Dcmplx(temp-abs(flag)*pi**2)+impi*Dcmplx(flag*(xlog+ylog))
      I3m1b=-I3m1b/Dcmplx(rtdel)

      return
      end

************************************************************************

c     This is an implementation of Eq. (B.2) from DS, arXiv:0906.0008.
      complex*16 function Lsm1DS(s,t,msq)
      implicit none
      real*8 s,t,msq,r1,r2,omr1,omr2,ddilog,pi,pisq,pisqo6
      complex*16 dilog1,dilog2,Lnrat

      pi=3.14159265358979311599d0
      pisq=pi*pi
      pisqo6=pisq/6d0

      r1=s/msq
      r2=t/msq
      omr1=1d0-r1
      omr2=1d0-r2
      if (omr1 .gt. 1d0) then
       dilog1=dcmplx(pisqo6-ddilog(r1))
     & -Lnrat(-s,-msq)*dcmplx(log(omr1))
      else
       dilog1=dcmplx(ddilog(omr1))
      endif
      if (omr2 .gt. 1d0) then
       dilog2=dcmplx(pisqo6-ddilog(r2))
     & -Lnrat(-t,-msq)*dcmplx(log(omr2))
      else
       dilog2=dcmplx(ddilog(omr2))
      endif
      Lsm1DS=dilog1+dilog2+Lnrat(-s,-msq)*Lnrat(-t,-msq)-dcmplx(pisqo6)

      return
      end

c-----------------------------------------------------------------------
c     Library of sub-sub-layer functions.
c-----------------------------------------------------------------------

*CW $Id: dclaus64.F,v 1.2 1996/04/02 16:23:45 mclareni Exp $
*
*cw $Log: dclaus64.F,v $
*cw Revision 1.2  1996/04/02 16:23:45  mclareni
*cw More precise dclaus64 (C326), test added and C344 removed from TESTALL
*
*cw Revision 1.1.1.1  1996/04/01 15:02:03  mclareni
*cw Mathlib gen
*
      REAL*8 FUNCTION DCLAUS(X)
      IMPLICIT REAL*8 (A-H,O-Z)
      DIMENSION A(0:8),B(0:13)
      PARAMETER (R1 = 1d0, HF =R1/2d0)
      PARAMETER (PI = 3.14159 26535 89793 24D0)
      PARAMETER (PI2 = 2d0*PI, PIH = PI/2d0, RPIH = 2d0/PI)

      DATA A( 0) / 0.02795 28319 73575 6613D0/
      DATA A( 1) / 0.00017 63088 74389 8116D0/
      DATA A( 2) / 0.00000 12662 74146 1157D0/
      DATA A( 3) / 0.00000 00117 17181 8134D0/
      DATA A( 4) / 0.00000 00001 23006 4129D0/
      DATA A( 5) / 0.00000 00000 01395 2729D0/
      DATA A( 6) / 0.00000 00000 00016 6908D0/
      DATA A( 7) / 0.00000 00000 00000 2076D0/
      DATA A( 8) / 0.00000 00000 00000 0027D0/

      DATA B( 0) / 0.63909 70888 57265 341D0/
      DATA B( 1) /-0.05498 05693 01851 716D0/
      DATA B( 2) /-0.00096 12619 45950 606D0/
      DATA B( 3) /-0.00003 20546 86822 550D0/
      DATA B( 4) /-0.00000 13294 61695 426D0/
      DATA B( 5) /-0.00000 00620 93601 824D0/
      DATA B( 6) /-0.00000 00031 29600 656D0/
      DATA B( 7) /-0.00000 00001 66351 954D0/
      DATA B( 8) /-0.00000 00000 09196 527D0/
      DATA B( 9) /-0.00000 00000 00524 004D0/
      DATA B(10) /-0.00000 00000 00030 580D0/
      DATA B(11) /-0.00000 00000 00001 820D0/
      DATA B(12) /-0.00000 00000 00000 110D0/
      DATA B(13) /-0.00000 00000 00000 007D0/

      V=MOD(ABS(X),PI2)
      S=SIGN(R1,X)
      IF(V .GT. PI) THEN
       V=PI2-V
       S=-S
      ENDIF
      IF(V .EQ. 0d0 .OR. V .EQ. PI) THEN
       H=0d0
      ELSEIF(V .LT. PIH) THEN
       U=RPIH*V
       H=2d0*U**2-1d0
       ALFA=H+H
       B1=0d0
       B2=0d0
       DO 1 I = 8,0,-1
       B0=A(I)+ALFA*B1-B2
       B2=B1
    1  B1=B0
       H=V*(1d0-LOG(V)+HF*V**2*(B0-H*B2))
      ELSE
       U=RPIH*V-2d0
       H=2d0*U**2-1d0
       ALFA=H+H
       B1=0d0
       B2=0d0
       DO 2 I = 13,0,-1
       B0=B(I)+ALFA*B1-B2
       B2=B1
    2  B1=B0
       H=(PI-V)*(B0-H*B2)
      ENDIF
      DCLAUS=S*H
      RETURN
      END

************************************************************************

      complex*16 function zw1(s,emq)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      parameter(pi=3.141592653589793238d0)

      emq2=emq**2

      rat=4d0*emq2/s
      temp=dsqrt(dabs(1d0/rat))
      if (rat .lt. 0d0) then
         zw1=2d0*dsqrt(1d0-rat)*asinh(temp)
      elseif (rat .gt. 1d0) then
         zw1=2d0*dsqrt(rat-1d0)*asin(temp)
      else
         temp=2d0*acosh(temp)
         zw1=dsqrt(1d0-rat)*dcmplx(temp,-pi)
      endif

      return
      end

************************************************************************

      complex*16 function zw2(s,emq)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      parameter(pi=3.141592653589793238d0)

      emq2=emq**2

      rat=s/(4d0*emq2)
      tempr=dsqrt(dabs(rat))
      if (rat .lt. 0d0) then
         tempr=asinh(tempr)
         zw2=4d0*tempr**2
      elseif (rat .gt. 1d0) then
         tempr=acosh(tempr)
         tempi=-4d0*tempr*pi
         tempr=+4d0*tempr**2-pi**2
         zw2=dcmplx(tempr,tempi)
      else
         tempr=asin(tempr)
         zw2=-4d0*tempr**2
      endif

      return
      end

************************************************************************

      complex*16 function zw3(s,t,u,varg,emq)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      
      zw3=zi3(s,t,u,varg,emq)-zi3(s,t,u,s,emq)-zi3(s,t,u,u,emq)
      
      return
      end

************************************************************************

      complex*16 function zi3(s,t,u,varg,emq)
      implicit real*8 (a-h,o-y)
      implicit complex*16 (z)
      complex*16 cli2
      parameter(pi=3.141592653589793238d0)

      emq2=emq**2

      zim=(0d0,1d0)

      rat=4d0*emq2/varg
      if (rat .lt. 0d0) then
         be=0.5d0*(1d0+dsqrt(1d0+4d0*t*emq2/(u*s)))
         ga=0.5d0*(1d0+dsqrt(1d0-rat))
         arg1=ga/(ga+be-1d0)
         arg2=(ga-1d0)/(ga+be-1d0)
         arg3=(be-ga)/be
         arg4=(be-ga)/(be-1d0)
         zi3=2d0/(2d0*be-1d0)
     .        *(-ddilog(arg1)+ddilog(arg2)+ddilog(arg3)-ddilog(arg4)
     .        +0.5d0*(dlog(be)**2-dlog(be-1d0)**2)
     .        +dlog(ga)*dlog((ga+be-1d0)/be)
     .        +dlog(ga-1d0)*dlog((be-1d0)/(ga+be-1d0)))
      elseif (rat .gt. 1d0) then
         be=0.5d0*(1d0+dsqrt(1d0+4d0*t*emq2/(u*s)))
         al=dsqrt(rat-1d0)
         r=dsqrt((al**2+1d0)/(al**2+(2d0*be-1d0)**2))
         arg=r*(al**2+2d0*be-1d0)/(1d0+al**2)
         if (arg .ge. 1d0) then
            phi=0d0
         else
            phi=dacos(arg)
         endif
         arg=r*(al**2-2d0*be+1d0)/(1d0+al**2)
         if (arg .ge. 1d0) then
            theta=0d0
         else
            theta=dacos(arg)
         endif
         zth=r*dcmplx(cos(theta),sin(theta))
         zph=r*dcmplx(cos(phi),sin(phi))
         zi3=2d0/(2d0*be-1d0)
     .        *(2d0*dble(cli2(zth))-2d0*dble(cli2(zph))
     .        +(phi-theta)*(phi+theta-pi))
      else
         be=0.5d0*(1d0+dsqrt(1d0+4d0*t*emq2/(u*s)))
         ga=0.5d0*(1d0+dsqrt(1d0-rat))
         arg1=ga/(ga+be-1d0)
         arg2=(ga-1d0)/(ga+be-1d0)
         arg3=ga/(ga-be)
         arg4=(ga-1d0)/(ga-be)

         zi3=2d0/(2d0*be-1d0)
     .        *(-ddilog(arg1)+ddilog(arg2)+ddilog(arg3)-ddilog(arg4)
     .        +dlog(ga/(1d0-ga))*dlog((ga+be-1d0)/(be-ga))
     .        -zim*pi*dlog((ga+be-1d0)/(be-ga)))
      endif

      return
      end

************************************************************************

      real*8 function acosh(y)
      implicit none
      real*8 y
      
      acosh=dlog(y+dsqrt(y**2-1d0))
      
      return
      end

************************************************************************

      real*8 function asinh(y)
      implicit none
      real*8 y
      
      asinh=dlog(y+dsqrt(y**2+1d0))
      
      return
      end

c-----------------------------------------------------------------------
