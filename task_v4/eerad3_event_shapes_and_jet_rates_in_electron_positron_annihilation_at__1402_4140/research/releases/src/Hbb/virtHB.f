c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     One-loop matrix elements for Higgs decays to a b-bbar pair
c     plus up to two additional partons.

c     NOTE: Always one ordering only,
c     *including* coupling factors and colour factors,
c     *excluding* symmetry factors. (will be set in sigHB).

c     Common block 'memode' determines whether to include Born or not:
c     imemode = 0  exclude Born
c     imemode = 1  include Born

c-----------------------------------------------------------------------
c     One-loop matrix elements for 2j.
c     Taken from arXiv:1501.07226.
c----------------------------------------------------------------------- 

c     H -> b bbar one-loop matrix element.
      real(8) function FullBy0g1H(p,i1,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2, ipole
      real(8), intent(in) :: p(1:4,3), renscale2
      real(8)             :: s12
c     Externals.
      real(8), external   :: By0g1H, dot

      s12 = 2d0*dot(p(1,i1),p(1,i2))
      FullBy0g1H  = By0g1H(s12,renscale2,ipole)

      return
      end

************************************************************************

c     H -> b bbar one-loop matrix element.
      real(8) function By0g1H(s12,renscale2,ipole)
      implicit none
      integer, intent(in) :: ipole
      real(8), intent(in) :: s12, renscale2
      integer             :: ischeme
      real(8)             :: e0, e1, e2
      real(8)             :: fac, tree, dlogs
      real(8)             :: as,cn,ca,cf,cflo,tr
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
c     Externals.
      real(8), external   :: By0g0H

      fac   = as/2d0/pi*cf
      tree  = By0g0H(s12)
      dlogs = log(s12/renscale2)

      ischeme = 0
      e2 = -2d0
      e1 = -3d0 + 2d0*dlogs
      e0 = -2d0 + pi**2 - dlogs**2 
      if (ischeme.eq.1) e0 = e0 - e2*pi**2/12d0

      By0g1H = 0d0
      select case (ipole)
      case(0)
         By0g1H = fac*e0*tree
      case(-1)
         By0g1H = fac*e1*tree
      case(-2)
         By0g1H = fac*e2*tree
      end select

      return
      end

c-----------------------------------------------------------------------
c     One-loop matrix elements for 3j.
c     Taken from arXiv:1501.07226.
c----------------------------------------------------------------------- 

c     Full H -> b bbar g one-loop matrix element.
      real(8) function FullBy1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in) :: i1,i2,i3,ipole
      real(8), intent(in) :: p(1:4,4),renscale2
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: fac
      real(8)             :: as,cn,ca,cf,cflo,tr,nf
c     Externals.
      real(8), external   :: By1g1H,Bty1g1H,Bhy1g1H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn

c     Prefactor.
      nf   = 2d0*tr
      fac  = (as/2d0/pi)*(4d0*pi*as)*2d0*cf*cn

c     Implementation based on Del Duca et al.
      FullBy1g1H = fac*(
     .     + By1g1H(p,i1,i3,i2,renscale2,ipole)
     .     - 1d0/cn**2*Bty1g1H(p,i1,i3,i2,renscale2,ipole)
     .     + (nf/cn)*Bhy1g1H(p,i1,i3,i2,renscale2,ipole)
     .     )

      return
      end

************************************************************************

c     Leading-colour H -> b bbar g one-loop matrix element.
      real(8) function By1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: p(1:4,4),renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: dlogs,s123,s12,s13,s23,y12,y13,y23
      real(8)             :: born,tree
      integer             :: imemode,ischeme
c     Externals.
      real(8), external   :: dot,RlogAux,By1g0H,By0g0H
c     Common blocks.
      common/memode/imemode

      s12   = 2d0*dot(p(1,i1),p(1,i2))
      s13   = 2d0*dot(p(1,i1),p(1,i3))
      s23   = 2d0*dot(p(1,i2),p(1,i3))
      s123  = s12+s13+s23
      y12   = s12/s123
      y13   = s13/s123
      y23   = s23/s123
      dlogs = dlog(renscale2/s123)

      born = 1d0
      if (imemode.eq.1) born = By0g0H(s123)
      tree = By1g0H(p,i1,i3,i2)

      By1g1H = 0d0
      select case(ipole)
      case(-2)
         By1g1H = (-2d0)*tree
      case(-1)
         By1g1H = (-10d0/3d0 + log(y13) + log(y23) - 2d0*dlogs)*tree
      case(0)
         By1g1H = (
     .        - RlogAux(y13,y23) - 1d0 + pi**2
     .        - 0.5d0*log(y13)**2 - 0.5d0*log(y23)**2
     .        + (log(y13) + log(y23))*dlogs - 2d0*dlogs**2/2d0
     .        )*tree
         By1g1H = By1g1H
     .        + 1d0/2d0/s123*(1d0/y13 + 1d0/y23)*born
      end select

      return
      end

************************************************************************

c     Subleading-colour H -> b b~ g one-loop amplitude squared.
      real(8) function Bty1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: p(1:4,4),renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Parameters.
      real(8), parameter  :: pi=3.141592653589793238d0
c     Variables.
      real(8)             :: dlogs,s123,s12,s13,s23,y12,y13,y23
      real(8)             :: born,tree
      integer             :: imemode,ischeme
c     Externals.
      real(8), external   :: dot,RlogAux,By1g0H,By0g0H
c     Common blocks.
      common/memode/imemode

      s12   = 2d0*dot(p(1,i1),p(1,i2))
      s13   = 2d0*dot(p(1,i1),p(1,i3))
      s23   = 2d0*dot(p(1,i2),p(1,i3))
      s123  = s12+s13+s23
      y12   = s12/s123
      y13   = s13/s123
      y23   = s23/s123
      dlogs = dlog(renscale2/s123)

      born = 1d0
      if (imemode.eq.1) born = By0g0H(s123)
      tree = By1g0H(p,i1,i3,i2)

      Bty1g1H = 0d0
      select case(ipole)
      case(-2)
         Bty1g1H = (-1d0)*tree
      case(-1)
         Bty1g1H = (-3d0/2d0 + log(y12) - dlogs)*tree
      case(0)
         Bty1g1H = (
     .        - RlogAux(y12,y13) - RlogAux(y12,y23)
     .        - 1d0 + pi**2/2d0 - 0.5*log(y12)**2
     .        + log(y12)*dlogs - dlogs**2/2d0
     .        )*tree
         Bty1g1H = Bty1g1H
     .        - 1d0/2d0/s123*(1d0/y13 + 1d0/y23)*born
      end select

      return
      end

************************************************************************

c     NF-part of H -> b b~ g one-loop amplitude squared.
      real(8) function Bhy1g1H(p,i1,i3,i2,renscale2,ipole)
      implicit none
      real(8), intent(in) :: p(1:4,4),renscale2
      integer, intent(in) :: i1,i2,i3,ipole
c     Variables.
      real(8)             :: tree
      integer             :: imemode
c     Externals.
      real(8), external   :: By1g0H
c     Common blocks.
      common/memode/imemode

      tree = By1g0H(p,i1,i3,i2)

      Bhy1g1H = 0d0
      select case(ipole)
      case(-2)
         Bhy1g1H = 0d0
      case(-1)
         Bhy1g1H = (1d0/3d0)*tree
      case(0)
         Bhy1g1H = 0d0
      end select

      return
      end
      
************************************************************************

c     RlogAux function as in (A.7) of arXiv:1501.07226.
      function RlogAux(x1,x2)
      implicit none
      real(8), intent(in) :: x1,x2
      real(8)             :: rli2, pi, RlogAux
      parameter(pi=3.141592653589793238d0)
      RlogAux = rli2(1d0-x1) + rli2(1d0-x2)
     .     + dlog(x1)*dlog(x2) - pi**2/6d0
      return
      end      
      
c-----------------------------------------------------------------------
c     One-loop matrix elements for 4j.
c----------------------------------------------------------------------- 

c     H -> b bbar g g.

c     Full one-loop matrix element for
c     H -> b(i1) g(i3) g(i4) bbar(i2).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullBy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      real(8)               :: fac
      real(8)               :: as,ca,cflo,cf,tr,cn,nf
c     Externals.
      real(8), external     :: By2g1H,Bty2g1H,Bhy2g1H
      real(8), external     :: Btty2g1H,Bttty2g1H,Btthy2g1H,Bhhy2g1H
c     MCFM variables.
      real(8), parameter    :: zip=0d0
      complex(8), parameter :: czip=(0d0,0d0)
      integer               :: h1,h2,h3,icol,imemode
      real(8)               :: born,s1234,facgg,tmp
      real(8)               :: msqlo(0:2),msqvirt(0:2)
      real(8)               :: msqgg,msq0,msquv,msqthv
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: Hbbgg_lc(1:2,2,2,2),Hbbgg_slc(1:2,2,2,2)
      complex(8)            :: Hbbgg_nf(1:2,2,2,2),Hbbgg_del(2,2,2)
      complex(8)            :: ampsgg_virt(0:2,2,2,2)
      complex(8)            :: ampsgg_lo(0:2,2,2,2),ampsQQ_lo(1:4,2,2,2)
      real(8), external     :: By0g0H,By2g0H,Bty2g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/memode/imemode

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn**2

      FullBy2g1H = 1d0/2d0*fac*(
     .     + By2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     + By2g1H(p,i1,i4,i3,i2,renscale2,ipole)

     .     - 1d0/cn**2*(
     .     + Bty2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     + Bty2g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + Btty2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     - Bhhy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     )

     .     + nf/cn*(
     .     + Bhy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     + Bhy2g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     )

     .     + 1d0/cn**4*Bttty2g1H(p,i1,i3,i4,i2,renscale2,ipole)

     .     - nf/cn**3*Btthy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
     .     )

      return

c     Cross check against MCFM amplitudes.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)
c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)
      facgg = (4d0*pi*as)**2*2d0*cf*cn*born/s1234
c     Fill Born amplitudes.
      call Hbbg_realamps(i1,i2,i3,i4,s,za,zb,ampsgg_lo,ampsQQ_lo)
c     Fill virtual amplitudes.
      call Hbbgg_vamps_delfill(i1,i2,i4,i3,s,za,zb,renscale2,ipole,
     .     Hbbgg_del)
      call Hbbgg_vamps_fill(i1,i2,i4,i3,s,za,zb,renscale2,ipole,
     .     Hbbgg_lc,Hbbgg_slc,Hbbgg_nf)
      do icol=1,2
         ampsgg_virt(icol,:,:,:) =
     .        + Hbbgg_lc(icol,:,:,:)
     .        + (1d0/cn**2)*Hbbgg_slc(icol,:,:,:)
     .        + (nf/cn)*Hbbgg_nf(icol,:,:,:)
      enddo
!-----sub-leading bit
      icol=0
      ampsgg_virt(icol,:,:,:) =
     .     - ampsgg_virt(1,:,:,:)
     .     - ampsgg_virt(2,:,:,:)
     .     + Hbbgg_del(:,:,:)

      msqlo(:)   = zip
      msqvirt(:) = zip
      tmp        = zip
      do h1=1,2
         do h2=1,2
            do h3=1,2
               tmp = tmp
     .              + real(
     .              conjg(ampsgg_lo(1,h1,h2,h3))*Hbbgg_lc(1,h1,h2,h3)
     .              )
     .              + (1d0/cn**2)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3))*Hbbgg_slc(1,h1,h2,h3)
     .              )
     .              + (nf/cn)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3))*Hbbgg_nf(1,h1,h2,h3)
     .              )

     .              + real(
     .              conjg(ampsgg_lo(2,h1,h2,h3))*Hbbgg_lc(2,h1,h2,h3)
     .              )
     .              + (1d0/cn**2)*real(
     .              conjg(ampsgg_lo(2,h1,h2,h3))*Hbbgg_slc(2,h1,h2,h3)
     .              )
     .              + (nf/cn)*real(
     .              conjg(ampsgg_lo(2,h1,h2,h3))*Hbbgg_nf(2,h1,h2,h3)
     .              )

     .              + (-1d0/cn**2)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3)+ampsgg_lo(2,h1,h2,h3))
     .              *(Hbbgg_lc(1,h1,h2,h3) + Hbbgg_lc(2,h1,h2,h3))
     .              )
     .              + (-1d0/cn**2)*(1d0/cn**2)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3)+ampsgg_lo(2,h1,h2,h3))
     .              *(Hbbgg_slc(1,h1,h2,h3) + Hbbgg_slc(2,h1,h2,h3))
     .              )
     .              + (-1d0/cn**2)*(nf/cn)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3)+ampsgg_lo(2,h1,h2,h3))
     .              *(Hbbgg_nf(1,h1,h2,h3) + Hbbgg_nf(2,h1,h2,h3))
     .              )
     .              + (1d0/cn**2)*real(
     .              conjg(ampsgg_lo(1,h1,h2,h3)+ampsgg_lo(2,h1,h2,h3))
     .              *Hbbgg_del(h1,h2,h3)
     .              )

               msqvirt(:) = msqvirt(:)
     .              + real(
     .              conjg(ampsgg_lo(:,h1,h2,h3))*ampsgg_virt(:,h1,h2,h3)
     .              )
               msqlo(:) = msqlo(:)
     .              + real(
     .              conjg(ampsgg_lo(:,h1,h2,h3))*ampsgg_lo(:,h1,h2,h3)
     .              )
            enddo
         enddo
      enddo
      tmp = (as/2d0/pi)*cn*facgg*tmp/2d0

!-----intf of 2 an
      msqvirt(:) = (as/2d0/pi)*cn*facgg*msqvirt(:)
      msqlo(:)   = facgg*msqlo(:)

!-----slc factor
      msqvirt(0) = msqvirt(0)/cn**2
      msqlo(0)   = -msqlo(0)/cn**2

!-----
      msqgg = (msqvirt(2) + msqvirt(1) + msqvirt(0))/2d0
      msq0  = (msqlo(2)   + msqlo(1)   + msqlo(0))/2d0

!-----UV renormalization in FDH
!-----alpha_S
      msquv = 0d0
      if (ipole.eq.-1) msquv = -(11d0*cn/3d0-2d0*nf/3d0)
      if (ipole.eq.0)  msquv = cn/3d0
!-----Z_b
      if (ipole.eq.-1) msquv = msquv - 3d0*cf
      if (ipole.eq.0)  msquv = msquv - cf
      msquv = (as/2d0/pi)*msquv*msq0

c     Scheme conversion FDH -> tHV.
      msqthv = 0d0
      if (ipole.eq.0)then
!         msqthv = 2d0*(1d0/2d0*cf) + 2d0*(1d0/6d0*ca)
         msqthv = 
     .        + 5d0/6d0*cn
     .        - 1d0/2d0/cn
      endif
      msqthv = (as/2d0/pi)*msqthv*msq0

c     Final result.
      tmp   = 1d0/2d0*(tmp + msquv - msqthv)
      FullBy2g1H = FullBy2g1H! - 1d0/2d0*fac*msqthv
      msqgg = 1d0/2d0*(msqgg + msquv - msqthv)
      print *, ipole,": ", FullBy2g1H/msqgg
      FullBy2g1H = msqgg

      return
      end

************************************************************************

      real(8) function By2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: h1,h2,h3
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2),amps_virt(2,2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_lc,Hbbgg_vamps_pppm_lc
      complex(8), external  :: Hbbgg_vamps_ppmm_lc
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)

c     Fill LC one-loop amplitudes.
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
      amps_virt(1,1,1) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,1,2) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,2) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,1) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)

      amps_virt(2,2,2) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,2,1) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,1) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,2) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_virt(h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_lo(h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
         renuv =
c     Contribution from alphaS.
     .        - 11d0/3d0
c     Contribution from Z_b.
     .        - 3d0/2d0
      case(0)
         renuv =
c     Contribution from alphaS.
     .        + 1d0/3d0
c     Contribution from Z_b.
     .        - 1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 3d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = 5d0/6d0

c     Final result.
      virt   = virt + renuv*tree + ren*tree - renthv*tree
      virt   = virt/s1234
      By2g1H = virt*born

      return

c     Cross check of pole parts against Catani's formula.
      dls13 = log(renscale2/s(i1,i3))
      dls24 = log(renscale2/s(i2,i4))
      dls34 = log(renscale2/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = 3d0*(-1d0)
      case(-1)
         tmp = - 31d0/6d0 - dls13 - dls34 - dls24
      case(0)
         tmp = - 5d0*dls13/3 - 5d0*dls24/3 - 11d0*dls34/6
     .        - dls13**2/2  - dls24**2/2 - dls34**2/2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0) print *,"By2g1H   ",ipole,By2g1H,tmp,By2g1H/tmp
      By2g1H = tmp

      return
      end

************************************************************************

      real(8) function Bty2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: h1,h2,h3
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2),amps_virt(2,2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_slc,Hbbgg_vamps_pppm_slc
      complex(8), external  :: Hbbgg_vamps_ppmm_slc
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)

c     Fill SLC one-loop amplitudes.
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
      amps_virt(1,1,1) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,1,2) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,2) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,1) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)

      amps_virt(2,2,2) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,2,1) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,1) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,2) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_virt(h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_lo(h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
c     Contribution from Z_b.
         renuv = +3d0/2d0
      case(0)
c     Contribution from Z_b.         
         renuv = +1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = -1d0/2d0

c     Final result.
      virt    = virt + renuv*tree + ren*tree - renthv*tree
c     Switch sign to factor out -1/NC^2.
      virt    = -virt/s1234
      Bty2g1H = virt*born

      return

c     Cross check pole parts against Catani's formula.
      dls12 = log(renscale2/s(i1,i2))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = -1d0
      case(-1)
         tmp = -3d0/2d0 - dls12
      case(0)
         tmp = -3d0/2d0*dls12 - 1d0/2d0*dls12**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0) print *,"Bty2g1H  ",ipole,Bty2g1H,tmp,Bty2g1H/tmp
      Bty2g1H = tmp

      return
      end

************************************************************************

      real(8) function Bhy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: h1,h2,h3
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2),amps_virt(2,2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_nf,Hbbgg_vamps_pppm_nf
      complex(8), external  :: Hbbgg_vamps_ppmm_nf
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)

c     Fill QL one-loop amplitudes.
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
      amps_virt(1,1,1) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(1,1,2) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,2) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(1,2,1) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,zB,zA,renscale2,ipole)

      amps_virt(2,2,2) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(2,2,1) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,1) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(2,1,2) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,zA,zB,renscale2,ipole)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_virt(h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(h1,h2,h3))*amps_lo(h1,h2,h3))
            enddo
         enddo
      enddo
      virt = -virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      if (ipole.eq.-1)then
c     Contribution from alphaS.
         renuv = 2d0/3d0
      end if

c     Final result.
      virt    = virt + renuv*tree
      virt    = virt/s1234
      Bhy2g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls13 = log(renscale2/s(i1,i3))
      dls24 = log(renscale2/s(i2,i4))
      dls34 = log(renscale2/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-1)
         tmp = 2d0/3d0
      case(0)
         tmp = dls13/6d0 + dls24/6d0 + dls34/3d0
      end select
      tmp = tmp*tree
      tmp = tmp*born/s1234
C      if (ipole.eq.-1) print *,"Bhy2g1H  ",ipole,Bhy2g1H,tmp,Bhy2g1H/tmp
      Bhy2g1H = tmp

      return
      end

************************************************************************

      real(8) function Btty2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Variables.
      integer               :: h1,h2,h3,icol
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(0:2,2,2,2),amps_virt(0:2,2,2,2),ctmp
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_lc,Hbbgg_vamps_pppm_lc
      complex(8), external  :: Hbbgg_vamps_ppmm_lc
      complex(8), external  :: lnrat
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(:,:,:,:) = czip
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)
      
c     icol=2: i4,i3 ordering.
      icol = 2
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zB,zA)

c     icol=0: SLC amplitude.
      icol = 0
      amps_lo(icol,:,:,:) = amps_lo(1,:,:,:) + amps_lo(2,:,:,:)

c     Fill LC one-loop amplitudes.
      amps_virt(:,:,:,:) = czip
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)

c     icol=2: i4,i3 ordering.
      icol = 2
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i4,i3,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_lc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     +Hbbgg_vamps_pppm_lc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_lc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     -Hbbgg_vamps_pppm_lc(i2,i1,i4,i3,s,zA,zB,renscale2,ipole)      

c     icol=0: SLC amplitude.
      icol = 0
      amps_virt(icol,:,:,:) = amps_virt(1,:,:,:) + amps_virt(2,:,:,:)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      tmp = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_virt(0,h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_lo(0,h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
         renuv =
c     Contribution from alphaS.
     .        - 11d0/3d0
c     Contribution from Z_b.
     .        - 3d0/2d0
      case(0)
         renuv =
c     Contribution from alphaS.
     .        + 1d0/3d0
c     Contribution from Z_b.
     .        - 1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 3d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = 5d0/6d0

c     Final result.
      virt     = virt + renuv*tree + ren*tree - renthv*tree
      virt     = virt/s1234
      Btty2g1H = virt*born

      return

c     Cross check pole parts against Catani's formula.
      dls13 = log(renscale2/s(i1,i3))
      dls14 = log(renscale2/s(i1,i4))
      dls23 = log(renscale2/s(i2,i3))
      dls24 = log(renscale2/s(i2,i4))
      dls34 = log(renscale2/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = -1d0 - 1d0/2d0*4d0
      case(-1)
         tmp =
     .        - 31d0/6d0
     .        - dls34
     .        - 1d0/2d0*dls13 - 1d0/2d0*dls14
     .        - 1d0/2d0*dls23 - 1d0/2d0*dls24
      case(0)
         tmp =
     .        - 5d0/6d0*dls13
     .        - 5d0/6d0*dls14
     .        - 5d0/6d0*dls23
     .        - 5d0/6d0*dls24
     .        - 11d0/6d0*dls34
     .        - 1d0/4d0*dls13**2
     .        - 1d0/4d0*dls14**2
     .        - 1d0/4d0*dls23**2
     .        - 1d0/4d0*dls24**2
     .        - 1d0/2d0*dls34**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0)
C     .     print *,"Btty2g1H ",ipole,Btty2g1H,tmp,Btty2g1H/tmp
      Btty2g1H = tmp

      return
      end

************************************************************************

      real(8) function Bttty2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Variables.
      integer               :: h1,h2,h3,icol
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(0:2,2,2,2),amps_virt(0:2,2,2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_slc,Hbbgg_vamps_pppm_slc
      complex(8), external  :: Hbbgg_vamps_ppmm_slc
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(:,:,:,:) = czip
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)
      
c     icol=2: i4,i3 ordering.
      icol = 2
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zB,zA)

c     icol=0: SLC amplitude.
      icol = 0
      amps_lo(icol,:,:,:) = amps_lo(1,:,:,:) + amps_lo(2,:,:,:)

c     Fill SLC one-loop amplitudes.
      amps_virt(:,:,:,:) = czip
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)

c     icol=2: i4,i3 ordering.
      icol = 2
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i4,i3,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_slc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     +Hbbgg_vamps_pppm_slc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_slc(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     -Hbbgg_vamps_pppm_slc(i2,i1,i4,i3,s,zA,zB,renscale2,ipole)      

c     icol=0: SLC amplitude.
      icol = 0
      amps_virt(icol,:,:,:) = amps_virt(1,:,:,:) + amps_virt(2,:,:,:)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_virt(0,h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_lo(0,h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
c     Contribution from Z_b.
         renuv = +3d0/2d0
      case(0)
c     Contribution from Z_b.         
         renuv = +1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = -1d0/2d0

c     Final result.
      virt      = virt + renuv*tree + ren*tree - renthv*tree
c     Switch sign to factor out -1/NC^2.
      virt      = -virt/s1234
      Bttty2g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls12  = log(renscale2/s(i1,i2))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = -1d0
      case(-1)
         tmp = - 3d0/2d0 - dls12
      case(0)
         tmp = - 3d0/2d0*dls12 - 1d0/2d0*dls12**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0)
C     .     print *,"Bttty2g1H",ipole,Bttty2g1H,tmp,Bttty2g1H/tmp
      Bttty2g1H = tmp

      return
      end

************************************************************************

      real(8) function Btthy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Variables.
      integer               :: h1,h2,h3,icol
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(0:2,2,2,2),amps_virt(0:2,2,2,2)
c     Externals.
      real(8), external     :: By0g0H,Bty2g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_nf,Hbbgg_vamps_pppm_nf
      complex(8), external  :: Hbbgg_vamps_ppmm_nf
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(:,:,:,:) = czip
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)
      
c     icol=2: i4,i3 ordering.
      icol = 2
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zB,zA)

c     icol=0: SLC amplitude.
      icol = 0
      amps_lo(icol,:,:,:) = amps_lo(1,:,:,:) + amps_lo(2,:,:,:)

c     Fill SLC one-loop amplitudes.
      amps_virt(:,:,:,:) = czip
c     NOTE: i3<->i4 swapped, because of colour ordering i1-i3-i4-i2.
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)

c     icol=2: i4,i3 ordering.
      icol = 2
      amps_virt(icol,1,1,1) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,1) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,2,2) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,zB,zA,renscale2,ipole)
      amps_virt(icol,1,1,2) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,zB,zA,renscale2,ipole)

      amps_virt(icol,2,2,2) =
     .     +Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,2) =
     .     +Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,1,1) =
     .     +Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,zA,zB,renscale2,ipole)
      amps_virt(icol,2,2,1) =
     .     -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,zA,zB,renscale2,ipole)      

c     icol=0: SLC amplitude.
      icol = 0
      amps_virt(icol,:,:,:) = amps_virt(1,:,:,:) + amps_virt(2,:,:,:)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_virt(0,h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_lo(0,h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     UV renormalization in FDH.
      renuv = 0d0
      if (ipole.eq.-1)then
c     Contribution from alphaS.
         renuv = 2d0/3d0
      end if

c     Final result.
      virt      = virt + renuv*tree
      virt      = virt/s1234
      Btthy2g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls13 = log(renscale2/s(i1,i3))
      dls14 = log(renscale2/s(i1,i4))
      dls23 = log(renscale2/s(i2,i3))
      dls24 = log(renscale2/s(i2,i4))
      dls34 = log(renscale2/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-1)
         tmp = 2d0/3d0
      case(0)
         tmp =
     .        + 1d0/12d0*dls13
     .        + 1d0/12d0*dls14
     .        + 1d0/12d0*dls23
     .        + 1d0/12d0*dls24
     .        + 1d0/3d0*dls34
      end select
      tmp = tmp*tree
      tmp = tmp*born/s1234
C      if (ipole.eq.-1)
C     .     print *, "Btthy2g1H",ipole,Btthy2g1H,tmp,Btthy2g1H/tmp
      Btthy2g1H = tmp

      return
      end

************************************************************************

      real(8) function Bhhy2g1H(p,i1,i3,i4,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Variables.
      integer               :: h1,h2,h3,icol
      integer               :: imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(0:2,2,2,2),amps_virt(2,2,2)
c     Externals.
      real(8), external     :: By0g0H,Bty2g0H
      complex(8), external  :: Hbbgg_allm,Hbbgg_mmmp,Hbbgg_mmpp
      complex(8), external  :: Hbbgg_vamps_allp_del34
      complex(8), external  :: Hbbgg_vamps_pppm_del34
      complex(8), external  :: Hbbgg_vamps_ppmm_del34
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill tree amplitudes.
      amps_lo(:,:,:,:) = czip
c     icol=1: i3,i4 ordering.
      icol = 1
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zA,zB)
      amps_lo(icol,1,2,1) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zB,zA)
      amps_lo(icol,2,1,2) = +Hbbgg_mmmp(i2,i1,i4,i3,s,zB,zA)
      
c     icol=2: i4,i3 ordering.
      icol = 2
      amps_lo(icol,1,1,1) = +Hbbgg_allm(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zA,zB)
      amps_lo(icol,1,1,2) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zA,zB)

      amps_lo(icol,2,2,2) = +Hbbgg_allm(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zB,zA)
      amps_lo(icol,2,2,1) = +Hbbgg_mmmp(i2,i1,i3,i4,s,zB,zA)

c     icol=0: SLC amplitude.
      icol = 0
      amps_lo(icol,:,:,:) = amps_lo(1,:,:,:) + amps_lo(2,:,:,:)

c     Fill colour-disconnected one-loop amplitudes.
c     Note: swap 3<->4 because of colour ordering.
c     All +.
      amps_virt(2,2,2) =
     .     +Hbbgg_vamps_allp_del34(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
c     All -.
      amps_virt(1,1,1) =
     .     +Hbbgg_vamps_allp_del34(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
c     Single minus normal ordering...
      amps_virt(2,2,1) =
     .     +Hbbgg_vamps_pppm_del34(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
c     ...and conjugate.
      amps_virt(1,1,2) =
     .     +Hbbgg_vamps_pppm_del34(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)
c     Single minus 3<->4 swap ordering...
      amps_virt(2,1,2) =
     .     -Hbbgg_vamps_pppm_del34(i2,i1,i3,i4,s,zA,zB,renscale2,ipole)
c     ...and conjugate.
      amps_virt(1,2,1) =
     .     -Hbbgg_vamps_pppm_del34(i2,i1,i3,i4,s,zB,zA,renscale2,ipole)
c     2 minus MHV.
      amps_virt(2,1,1) =
     .     +Hbbgg_vamps_ppmm_del34(i1,i2,i4,i3,s,zA,zB,renscale2,ipole)
c     2 minus MHV-bar.
      amps_virt(1,2,2) =
     .     +Hbbgg_vamps_ppmm_del34(i1,i2,i4,i3,s,zB,zA,renscale2,ipole)

c     Calculate tree-loop interference and tree amplitude squared.
      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               virt = virt
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_virt(h1,h2,h3))
               tree = tree
     .              + real(conjg(amps_lo(0,h1,h2,h3))
     .              *amps_lo(0,h1,h2,h3))
            enddo
         enddo
      enddo
      virt = virt/2d0
      tree = tree/2d0

c     Final result.
      virt     = virt/s1234
      Bhhy2g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls12 = log(renscale2/s(i1,i2))
      dls13 = log(renscale2/s(i1,i3))
      dls14 = log(renscale2/s(i1,i4))
      dls23 = log(renscale2/s(i2,i3))
      dls24 = log(renscale2/s(i2,i4))
      dls34 = log(renscale2/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-1)
         tmp =
     .        - dls12
     .        - dls34
     .        + 1d0/2d0*dls13
     .        + 1d0/2d0*dls14
     .        + 1d0/2d0*dls23
     .        + 1d0/2d0*dls24
      case(0)
         tmp =
     .        - 3d0/2d0*dls12
     .        + 5d0/6d0*dls13
     .        + 5d0/6d0*dls14
     .        + 5d0/6d0*dls23
     .        + 5d0/6d0*dls24
     .        - 11d0/6d0*dls34
     .        - 1d0/2d0*dls12**2
     .        + 1d0/4d0*dls13**2
     .        + 1d0/4d0*dls14**2
     .        + 1d0/4d0*dls23**2
     .        + 1d0/4d0*dls24**2
     .        - 1d0/2d0*dls34**2
      end select
      tmp = tmp*tree
      tmp = tmp*born/s1234
C      if (ipole.eq.-1)
C     .     print *, "Bhhy2g1H ",ipole,Bhhy2g1H,tmp,Bhhy2g1H/tmp
      Bhhy2g1H = tmp

      return
      end

c-----------------------------------------------------------------------
c     Library of H -> b bbar g g one-loop amplitudes.
c     Calculated and provided by Ciaran Williams.

c     Leading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), all +.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_allp_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8)                :: musq,s(5,5)
      complex(8), intent(in) :: zA(5,5),zB(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(3),boxc(3),Atree,Vpole,Boxes,Rat
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: Hbbgg_allm
      complex(8), external   :: lnrat,Lsm1,Lsm1_2me

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = s1234/(za(i1,i4)*za(i2,i3)*za(i3,i4))
      Vpole = czip
      Boxes = czip
      Rat   = czip

      select case(ipole)
      case(-2)
         Vpole = 3d0
      case(-1)
         Vpole =
     .        + lnrat(musq,-s(i1,i4))
     .        + lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
      case(0)
         Vpole =
     .        + (
     .        + lnrat(musq,-s(i1,i4))**2
     .        + lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )/2.
      end select

      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2me(t(i1,i3,i4),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(2) = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(3) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

c     Full coefficient.
C     boxc(1) = Atree*(t(i1,i3,i4)*t(i2,i3,i4)-s1234*s(i3,i4))
C     boxc(2) = Atree*(s(i3,i4)*s(i2,i3))
C     boxc(3) = Atree*(s(i3,i4)*s(i1,i4))

c     Minus GDet.
         boxc(1) = Atree
         boxc(2) = Atree
         boxc(3) = Atree

         Boxes = czip
         do i=1,3
            Boxes = Boxes+BoxI4(i)*boxc(i)
         enddo

         Rat = zb(i3,i2)/(2.*za(i1,i4)*za(i3,i4)) + 
     -        (za(i1,i3)*zab2(i2,i3,i4,i1)*zb(i3,i2))/
     -        (2.*t(i2,i3,i4)*za(i1,i4)*za(i2,i3)*za(i3,i4)) + 
     -        zb(i4,i1)/(2.*za(i2,i3)*za(i3,i4)) + 
     -        (za(i2,i4)*zab2(i1,i3,i4,i2)*zb(i4,i1))/
     -        (2.*t(i1,i3,i4)*za(i1,i4)*za(i2,i3)*za(i3,i4)) - 
     -        (zb(i2,i1)*(t(i1,i3,i4)*za(i2,i3)*zb(i3,i2) + 
     -        t(i2,i3,i4)*za(i1,i4)*zb(i4,i1)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4)**2) + 
     -        (zb(i2,i1)*(t(i2,i3,i4)*za(i1,i3)*zb(i3,i1) + 
     -        t(i1,i3,i4)*za(i2,i4)*zb(i4,i2)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4)**2) + 
     -        ((t(i1,i3,i4) + t(i2,i3,i4))*
     -        (zb(i3,i2)*zb(i4,i1) + zb(i3,i1)*zb(i4,i2)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4)) + 
     -        (s1234*zb(i4,i3))/(2.*t(i1,i3,i4)*za(i1,i4)*za(i2,i3)) + 
     -        (s1234*zb(i4,i3))/(2.*t(i2,i3,i4)*za(i1,i4)*za(i2,i3))
      endif

      Hbbgg_vamps_allp_lc = -Vpole - Boxes + Rat

      return
      end

************************************************************************

c     Subleading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), all +.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_allp_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      integer, parameter     :: Nbox=5
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(Nbox),boxc(Nbox)
      complex(8)             :: Atree,Vpole,Boxes,Rat
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2me

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)

      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = s1234/(za(i1,i4)*za(i2,i3)*za(i3,i4))
      Vpole = 0d0
      Boxes = 0d0
      Rat   = 0d0

      select case(ipole)
      case(-2)
         Vpole = 1d0
      case(-1)
         Vpole = lnrat(musq,-s(i1,i2))
      case(0)
         Vpole = lnrat(musq,-s(i1,i2))**2/2d0
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2me(t(i1,i2,i4),t(i1,i3,i4),s(i1,i4),s1234)
         BoxI4(2) = Lsm1_2me(t(i1,i2,i3),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(3) = Lsm1_2me(t(i1,i2,i3),t(i1,i2,i4),s(i1,i2),s1234)
         BoxI4(4) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i1,i2),-t(i1,i2,i4))
         BoxI4(5) = Lsm1(-s(i1,i2),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))

c     Full coefficient.
         boxc(1)=Atree*zab2(i2,i1,i4,i3)*zab2(i3,i1,i4,i2)
         boxc(2)=Atree*zab2(i1,i2,i3,i4)*zab2(i4,i2,i3,i1)
         boxc(3)=Atree*zab2(i3,i1,i2,i4)*zab2(i4,i1,i2,i3)
         boxc(4)=Atree*s(i1,i2)*s(i1,i4)
         boxc(5)=Atree*s(i1,i2)*s(i2,i3)
      
c     Minus GD for Lsm1 basis.
         boxc(:)=Atree

         Boxes = czip      
         do i=1,Nbox
            Boxes=Boxes+BoxI4(i)*boxc(i)
         enddo
      
         Rat = zb(i3,i2)/(2.*za(i1,i4)*za(i3,i4)) + 
     -  (za(i1,i3)*zab2(i2,i3,i4,i1)*zb(i3,i2))/
     -   (2.*t(i2,i3,i4)*za(i1,i4)*za(i2,i3)*za(i3,i4)) + 
     -  zb(i4,i1)/(2.*za(i2,i3)*za(i3,i4)) + 
     -  (za(i2,i4)*zab2(i1,i3,i4,i2)*zb(i4,i1))/
     -   (2.*t(i1,i3,i4)*za(i1,i4)*za(i2,i3)*za(i3,i4)) + 
     -  (s1234*zb(i4,i3))/(2.*t(i1,i3,i4)*za(i1,i4)*za(i2,i3)) + 
     -     (s1234*zb(i4,i3))/(2.*t(i2,i3,i4)*za(i1,i4)*za(i2,i3))
      endif

      Hbbgg_vamps_allp_slc = Vpole + Boxes + Rat
!     write(6,*) 'Atree = ',Atree
!     write(6,*) 'Vpole = ',Vpole/im
!     write(6,*) 'Boxes = ',Boxes/im
!     write(6,*) 'Bubs  = ',Bubs/im
!     write(6,*) 'Total CC  = ',(Vpole+Boxes+Bubs)/(Atree*im)
!     write(6,*) 'Rat  = ', Rat/im
!     write(6,*) '       '
!     write(6,*) ' Sum  = ',Hbbgg_vamps_allp_slc/im
!     stop

      return
      end

************************************************************************

c     Nf Quark-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), all +.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: Atree,Vpole,Rat
c     Externals.
      complex(8), external :: lnrat,Lsm1,Lsm1_2me

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = s1234/(za(i1,i4)*za(i2,i3)*za(i3,i4))
      Vpole = 0d0
      Rat   = 0d0

      if (ipole.eq.0)then
         Rat = (zb(i2,i1)*(t(i1,i3,i4)*za(i2,i3)*zb(i3,i2) + 
     -        t(i2,i3,i4)*za(i1,i4)*zb(i4,i1)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4)**2) - 
     -        (zb(i2,i1)*(t(i2,i3,i4)*za(i1,i3)*zb(i3,i1) + 
     -        t(i1,i3,i4)*za(i2,i4)*zb(i4,i2)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4)**2) - 
     -        ((t(i1,i3,i4) + t(i2,i3,i4))*(zb(i3,i2)*zb(i4,i1)
     &        + zb(i3,i1)*zb(i4,i2)))/
     -        (6.*t(i1,i3,i4)*t(i2,i3,i4)*za(i3,i4))
      endif

      Hbbgg_vamps_allp_nf = Vpole + Rat
!     write(6,*) ' Sum  = ',Hbbgg_vamps_allp_nf/im

      return
      end

************************************************************************

c     Del34 piece for
c     H -> b(p1) bbar(p2) g(p3) g(p4), all +.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_allp_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      integer, parameter     :: Nbox=18
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(Nbox),boxc(Nbox)
      complex(8)             :: Atree,AtreeS,AtreeSum,Vpole,Boxes
      complex(8)             :: zab2
c     Externals.
      complex(8), external  :: lnrat,Lsm1,Lsm1_2me

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)

      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree    = -(s1234/(za(i1,i4)*za(i2,i3)*za(i3,i4)))
      AtreeS   = s1234/(za(i1,i3)*za(i2,i4)*za(i3,i4))
      AtreeSum = -((s1234*za(i1,i2))
     .     /(za(i1,i3)*za(i1,i4)*za(i2,i3)*za(i2,i4)))
      Vpole    = czip
      Boxes    = czip
      
      select case(ipole)
      case(-1)
         Vpole =
     .        + (
     .        - lnrat(musq,-s(i1,i2))
     .        + lnrat(musq,-s(i1,i3))
     .        + lnrat(musq,-s(i2,i4))
     .        - lnrat(musq,-s(i3,i4))
     .        )*s1234/(za(i1,i4)*za(i2,i3)*za(i3,i4))
     .        + (
     .        + lnrat(musq,-s(i1,i2))
     .        - lnrat(musq,-s(i1,i4))
     .        - lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
     .        )*s1234/(za(i1,i3)*za(i2,i4)*za(i3,i4))
      case(0)
         Vpole =
     .        + (
     .        - lnrat(musq,-s(i1,i2))**2
     .        + lnrat(musq,-s(i1,i3))**2
     .        + lnrat(musq,-s(i2,i4))**2
     .        - lnrat(musq,-s(i3,i4))**2
     .        )*s1234/(2.*za(i1,i4)*za(i2,i3)*za(i3,i4))
     .        + (
     .        + lnrat(musq,-s(i1,i2))**2
     .        - lnrat(musq,-s(i1,i4))**2
     .        - lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )*s1234/(2.*za(i1,i3)*za(i2,i4)*za(i3,i4))
      end select

      if (ipole.eq.0)then
         BoxI4(1)  = Lsm1_2me(t(i1,i3,i4),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(2)  = Lsm1_2me(t(i1,i2,i3),t(i1,i3,i4),s(i1,i3),s1234)
         BoxI4(3)  = Lsm1_2me(t(i1,i2,i4),t(i1,i3,i4),s(i1,i4),s1234)

         BoxI4(4)  = Lsm1(-s(i2,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(5)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(6)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i4),-t(i2,i3,i4))

         BoxI4(7)  = Lsm1_2me(t(i1,i2,i3),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(8)  = Lsm1_2me(t(i1,i2,i4),t(i2,i3,i4),s(i2,i4),s1234)

         BoxI4(9)  = Lsm1(-s(i1,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(10) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(11) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         BoxI4(12) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i1,i2),-t(i1,i2,i3))

         BoxI4(13) = Lsm1_2me(t(i1,i2,i3),t(i1,i2,i4),s(i1,i2),s1234)

         BoxI4(14) = Lsm1(-s(i1,i2),-t(i1,i2,i4),-s(i2,i4),-t(i1,i2,i4))
         BoxI4(15) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i1,i2),-t(i1,i2,i4))

         BoxI4(16) = Lsm1(-s(i1,i2),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))
         BoxI4(17) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))

         BoxI4(18) = Lsm1(-s(i2,i4),-t(i1,i2,i4),-s(i1,i4),-t(i1,i2,i4))

c     Pure coeffcient.
C         boxc(1)=zab2(i1,i3,i4,i2)*zab2(i2,i3,i4,i1)*(Atree+AtreeS)
C         boxc(2)=-zab2(i2,i1,i3,i4)*zab2(i4,i1,i3,i2)*Atree
C         boxc(3)=-zab2(i2,i1,i4,i3)*zab2(i3,i1,i4,i2)*(AtreeS)
C         boxc(4)=-s(i2,i3)*s(i2,i4)*(Atree+AtreeS)
C         boxc(5)=s(i2,i3)*s(i3,i4)*Atree
C         boxc(6)=s(i2,i4)*s(i3,i4)*(AtreeS)
C         boxc(7)=-zab2(i1,i2,i3,i4)*zab2(i4,i2,i3,i1)*(AtreeS)
C         boxc(8)=-zab2(i1,i2,i4,i3)*zab2(i3,i2,i4,i1)*(Atree)
C         boxc(9)=-s(i1,i4)*s(i1,i3)*(Atree+AtreeS)
C         boxc(10)=s(i1,i3)*s(i3,i4)*(AtreeS)
C         boxc(11)=s(i1,i4)*s(i3,i4)*Atree
C         boxc(12)=s(i1,i3)*s(i1,i2)*(AtreeS)
C         boxc(13)=zab2(i3,i1,i2,i4)*zab2(i4,i1,i2,i3)*(AtreeS+Atree)
C         boxc(14)=s(i1,i2)*s(i2,i4)*(AtreeS)
C         boxc(15)=s(i1,i4)*s(i1,i2)*Atree
C         boxc(16)=s(i2,i3)*s(i1,i2)*Atree
C         boxc(17)=-s(i2,i3)*s(i1,i3)*(AtreeS+Atree)
C         boxc(18)=-s(i2,i4)*s(i1,i4)*(Atree+AtreeS)
C         do i = 1,Nbox
C            write(6,*) i, boxc(i)/(2d0*im)
C         enddo

c     Without GD.
         boxc(1)  = (Atree+AtreeS)
         boxc(2)  = -Atree
         boxc(3)  = -(AtreeS)
         boxc(4)  = -(Atree+AtreeS)
         boxc(5)  = Atree
         boxc(6)  = AtreeS
         boxc(7)  = -(AtreeS)
         boxc(8)  = -(Atree)
         boxc(9)  = -(Atree+AtreeS)
         boxc(10) = (AtreeS)
         boxc(11) = Atree
         boxc(12) = (AtreeS)
         boxc(13) = (AtreeS+Atree)
         boxc(14) = (AtreeS)
         boxc(15) = Atree
         boxc(16) = Atree
         boxc(17) = -(AtreeS+Atree)
         boxc(18) = -(Atree+AtreeS)
         do i=1,18
            Boxes = Boxes + boxi4(i)*boxc(i)
         enddo
      endif

      Hbbgg_vamps_allp_del34 = Vpole + Boxes

!     write(6,*) Vpole/im
!     write(6,*) Boxes/im
!     write(6,*) ' Sum  = ',Hbbgg_vamps_allp_del34/im

      return
      end

************************************************************************
      
c     Leading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), +++-.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_pppm_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(4),boxc(4),tric(1)
      complex(8)             :: Atree,Vpole,Boxes,Triags,Bubs,Rat
      complex(8)             :: zab2
c     External.
      complex(8), external   :: Hbbgg_mmmp
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,L0,L1,I3m

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree  = -Hbbgg_mmmp(i1,i2,i4,i3,s,zb,za)
      Vpole  = czip
      Boxes  = czip
      Triags = czip
      Bubs   = czip
      Rat    = czip

      select case(ipole)
      case(-2)
         Vpole = 3d0
      case(-1)
         Vpole =
     .        + lnrat(musq,-s(i1,i4))
     .        + lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
      case(0)
         Vpole =
     .        + (
     .        + lnrat(musq,-s(i1,i4))**2
     .        + lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )/2.
      end select

      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2mht(s(i2,i3),t(i1,i3,i4),s(i1,i4),s1234)
         BoxI4(2) = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(3) = Lsm1_2mht(s(i1,i4),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(4) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

c     GD removed. 
         boxc(1) = -((zab2(i4,i1,i3,i2)**3/
     -        (za(i3,i4)*zab2(i1,i3,i4,i2)*
     -        zab2(i3,i1,i4,i2)) + 
     -        (s1234*zb(i3,i1)**3)/
     -       (zab2(i2,i3,i4,i1)*zb(i4,i1)*zb(i4,i3)))/
     -     t(i1,i3,i4))

         boxc(2) = (-((s1234*za(i2,i3)*za(i3,i4)*zb(i3,i2)**4)/
     -       (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i2))) - 
     -    (za(i2,i4)*zab2(i4,i2,i3,i1)**2*zb(i3,i2)*
     -       zb(i4,i3))/(t(i2,i3,i4)*zab2(i2,i3,i4,i1)))/
     -     (za(i2,i3)*za(i3,i4)*zb(i3,i2)*zb(i4,i3))

         boxc(3) = -(((za(i2,i4)*zab2(i4,i2,i3,i1)**2)/
     -       (za(i2,i3)*za(i3,i4)*zab2(i2,i3,i4,i1)) + 
     -      (s1234*zab2(i1,i2,i4,i3)*zb(i3,i2)**2)/
     -       (zab2(i1,i2,i3,i4)*zab2(i1,i3,i4,i2)*
     -     zb(i4,i3)))/t(i2,i3,i4))

         boxc(4) = -(((s1234*za(i3,i4)*zb(i3,i1)**3)/
     -       (t(i1,i3,i4)*zab2(i2,i3,i4,i1)) + 
     -      (za(i1,i4)**3*zab2(i3,i1,i4,i2)**2*zb(i4,i1)*
     -         zb(i4,i3))/
     -       (t(i1,i3,i4)*za(i1,i3)**3*zab2(i1,i3,i4,i2)))/
     -     (za(i3,i4)*zb(i4,i1)*zb(i4,i3)))

         Boxes = czip
         do i=1,4
            Boxes = Boxes+boxc(i)*BoxI4(i)
         enddo

c     3m triangle.
         tric(1) = (zab2(i1,i2,i3,i1)**3*zb(i2,i1) - 
     -    3*za(i1,i4)*za(i2,i3)*zab2(i1,i2,i3,i1)*zb(i2,i1)*zb(i3,i2)*
     -     zb(i4,i1) + za(i2,i3)*zb(i3,i2)**2*zb(i4,i1)*
     -     (za(i2,i3)*za(i3,i4)*zb(i3,i2) - 
     -       za(i1,i4)*(za(i2,i3)*zb(i2,i1) + 2*za(i3,i4)*zb(i4,i1))) - 
     -    zab2(i1,i2,i3,i1)**2*zab2(i4,i2,i3,i1)*zb(i4,i2) + 
     -    t(i2,i3,i4)*(zab2(i1,i2,i3,i1)**2*zb(i2,i1) - 
     -       za(i2,i3)*zb(i3,i2)*
     -        (za(i1,i4)*zb(i2,i1) + za(i3,i4)*zb(i3,i2))*zb(i4,i1) - 
     -       zab2(i1,i2,i3,i1)*zab2(i4,i2,i3,i1)*zb(i4,i2)))/
     -     (za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i4,i2)*zb(i4,i1))
         tric(1) = tric(1)/2d0
         Triags  = tric(1)*I3m(s(i2,i3),s(i1,i4),s1234)

         Bubs = (L0(-s(i1,i4),-t(i1,i3,i4))*za(i1,i4)**2
     .        *zab2(i3,i1,i4,i2)*zb(i3,i1))
     .        /(t(i1,i3,i4)**2*za(i1,i3)**2)
     .        + (L0(-s(i1,i4),-t(i1,i3,i4))*za(i1,i4)*zab2(i4,i1,i3,i2)
     .        *zb(i3,i1))/(t(i1,i3,i4)**2*za(i1,i3))
     .        + (2*L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)**2
     .        *zb(i2,i1)*zb(i3,i1))/(t(i1,i3,i4)**2*za(i1,i3))
     .        + (L1(-s(i1,i4),-t(i1,i3,i4))*za(i1,i4)**2
     .        *zab2(i3,i1,i4,i2)*zb(i3,i1)**2)
     .        /(2.*t(i1,i3,i4)**3*za(i1,i3))
     .        - (2*L0(-s(i3,i4),-t(i2,i3,i4))*za(i2,i4)**2
     .        *zb(i2,i1)*zb(i3,i2))/(t(i2,i3,i4)**2*za(i2,i3))
     .        - (L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)*za(i3,i4)
     .        *zb(i3,i1)*zb(i3,i2))/(2.*t(i1,i3,i4)**2*za(i1,i3))
     .        - (3*L0(-s(i3,i4),-t(i2,i3,i4))*za(i2,i4)*za(i3,i4)
     .        *zb(i3,i1)*zb(i3,i2))/(2.*t(i2,i3,i4)**2*za(i2,i3))
     .        + (L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)**2*za(i3,i4)
     .        *zb(i3,i1)*zb(i4,i2))/(t(i1,i3,i4)**2*za(i1,i3)**2)
     .        + (L1(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)**2*za(i3,i4)
     .        *zb(i2,i1)*zb(i3,i1)*zb(i4,i3))
     .        /(2.*t(i1,i3,i4)**3*za(i1,i3))
     .        - (L1(-s(i3,i4),-t(i2,i3,i4))*za(i2,i4)**2*za(i3,i4)
     .        *zb(i2,i1)*zb(i3,i2)*zb(i4,i3))
     .        /(2.*t(i2,i3,i4)**3*za(i2,i3))

         Rat = (za(i2,i4)**2*zb(i2,i1)*zb(i3,i2))
     .        /(2.*t(i2,i3,i4)**2*za(i2,i3))
     .        - (za(i1,i4)*za(i3,i4)*zb(i3,i1)*zb(i3,i2))
     .        /(2.*t(i1,i3,i4)**2*za(i1,i3))
     .        - (za(i2,i4)*zb(i2,i1)*zb(i3,i2))
     .        /(2.*t(i2,i3,i4)*za(i2,i3)*zb(i4,i2))
     .        + (zb(i2,i1)*zb(i3,i1))/(2.*za(i2,i3)*zb(i4,i1)*zb(i4,i2))
     .        + (zb(i3,i1)**2*zb(i3,i2))
     .        /(2.*t(i1,i3,i4)*zb(i4,i1)*zb(i4,i3))
     .        + (zb(i3,i1)*zb(i3,i2))/(2.*za(i2,i3)*zb(i4,i2)*zb(i4,i3))
     .        - (za(i2,i4)*zb(i3,i2)**2*zb(i4,i1))
     .        /(2.*t(i2,i3,i4)*za(i2,i3)*zb(i4,i2)*zb(i4,i3))
      endif

      Hbbgg_vamps_pppm_lc = -Vpole + Boxes - Triags + Rat - Bubs

      return
      end

************************************************************************            

c     Subleading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), +++-.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_pppm_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in )   :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(10),boxc(10),tric(2)
      complex(8)             :: Atree,Vpole,Boxes,Triags,Bubs,Rat
      complex(8)             :: mp12,gam
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: Hbbgg_mmmp
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,L0,L1,I3m

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree  = -Hbbgg_mmmp(i1,i2,i4,i3,s,zb,za)
      Vpole  = 0d0
      Boxes  = 0d0
      Triags = 0d0
      Bubs   = 0d0
      Rat    = 0d0
      
      select case(ipole)
      case(-2)
         Vpole = 1d0
      case(-1)
         Vpole = lnrat(musq,-s(i1,i2))
      case(0)
         Vpole = lnrat(musq,-s(i1,i2))**2/2d0
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2mht(s(i2,i3),t(i1,i2,i4),s(i1,i4),s1234)
         BoxI4(2) = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(3) = Lsm1_2mht(s(i1,i4),t(i1,i2,i3),s(i2,i3),s1234)      
         BoxI4(4) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         BoxI4(5) = Lsm1_2mht(s(i1,i2),t(i2,i3,i4),s(i3,i4),s1234)      
         BoxI4(6) = Lsm1_2mht(s(i1,i2),t(i1,i3,i4),s(i3,i4),s1234)      
         BoxI4(7) = Lsm1_2mht(s(i3,i4),t(i1,i2,i3),s(i1,i2),s1234)      

         BoxI4(8) = Lsm1(-s(i1,i2),-t(i1,i2,i4),-s(i1,i4),-t(i1,i2,i4))
         BoxI4(9) = Lsm1(-s(i2,i3),-t(i1,i2,i3),-s(i1,i2),-t(i1,i2,i3))

         BoxI4(10) = Lsm1_2mht(s(i3,i4),t(i1,i2,i4),s(i1,i2),s1234)      
  
c     GD extracted.
         boxc(1) = (s1234*zb(i2,i1)**2)/
     -        (zab2(i3,i1,i2,i4)*zab2(i3,i1,i4,i2)*zb(i4,i1))

         boxc(2) = (s1234*zb(i3,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i2,i3,i4)*zb(i4,i2))

         boxc(3) = -(t(i1,i2,i3)**2/
     -        (za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i2,i4)))
      
         boxc(4) = -((za(i3,i4)**2*zab2(i1,i3,i4,i2)**2)/
     -        (t(i1,i3,i4)*za(i1,i3)**3*
     -        zab2(i3,i1,i4,i2)))

         boxc(5) = ((za(i1,i2)*za(i2,i4)*zab2(i4,i2,i3,i1)**2*zb(i2,i1))
     .        /(za(i2,i3)*za(i3,i4)*zab2(i2,i3,i4,i1))
     .        + (s1234*za(i1,i2)*zab2(i1,i2,i4,i3)*zb(i2,i1)
     .        *zb(i3,i2)**2)/(zab2(i1,i2,i3,i4)
     .        *zab2(i1,i3,i4,i2)*zb(i4,i3)))
     .        /(t(i2,i3,i4)*za(i1,i2)*zb(i2,i1))

         boxc(6) = ((za(i1,i2)*zab2(i4,i1,i3,i2)**3*zb(i2,i1))/
     -        (za(i3,i4)*zab2(i1,i3,i4,i2)*zab2(i3,i1,i4,i2)) + 
     -        (s1234*za(i1,i2)*zb(i2,i1)*zb(i3,i1)**3)/
     -        (zab2(i2,i3,i4,i1)*zb(i4,i1)*zb(i4,i3)))/
     -        (t(i1,i3,i4)*za(i1,i2)*zb(i2,i1))

         boxc(7) = -(t(i1,i2,i3)**2/
     -        (za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i2,i4)))

         boxc(8) = (s1234*zb(i2,i1)**2)/
     -        (zab2(i3,i1,i2,i4)*zab2(i3,i1,i4,i2)*
     -        zb(i4,i1))

         boxc(9) = -(t(i1,i2,i3)**2/
     -        (za(i2,i3)*zab2(i1,i2,i3,i4)*
     -        zab2(i3,i1,i2,i4)))

         boxc(10) = (s1234*zb(i2,i1)**2)/
     -        (zab2(i3,i1,i2,i4)*zab2(i3,i1,i4,i2)*
     -        zb(i4,i1))

         Boxes = czip
         do i=1,10
            Boxes = Boxes+boxc(i)*BoxI4(i)
         enddo
      
         tric(1) = (zab2(i1,i2,i3,i1)**3*zb(i2,i1)
     .        - 3*za(i1,i4)*za(i2,i3)*zab2(i1,i2,i3,i1)*zb(i2,i1)
     .        *zb(i3,i2)*zb(i4,i1)
     .        + za(i2,i3)*zb(i3,i2)**2*zb(i4,i1)*(za(i2,i3)*za(i3,i4)
     .        *zb(i3,i2)
     .        - za(i1,i4)*(za(i2,i3)*zb(i2,i1)
     .        + 2*za(i3,i4)*zb(i4,i1)))
     .        - zab2(i1,i2,i3,i1)**2*zab2(i4,i2,i3,i1)*zb(i4,i2)
     .        + t(i2,i3,i4)*(zab2(i1,i2,i3,i1)**2*zb(i2,i1)
     .        - za(i2,i3)*zb(i3,i2)*
     .        (za(i1,i4)*zb(i2,i1) + za(i3,i4)*zb(i3,i2))*zb(i4,i1)
     .        - zab2(i1,i2,i3,i1)*zab2(i4,i2,i3,i1)*zb(i4,i2)))
     .        /(za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i4,i2)*zb(i4,i1))

         tric(1) = -tric(1)/2d0
      
         mp12 = s(i1,i3)/2d0+s(i1,i4)/2d0+s(i2,i3)/2d0+s(i2,i4)/2d0
      
         gam = -mp12+sqrt(mp12**2-s(i1,i2)*s(i3,i4))
       
         tric(2) = -(zb(i2,i1)**2*(gam*za(i2,i4) + 
     -        za(i1,i2)*za(i3,i4)*zb(i3,i1))*
     -        (gam*za(i1,i4) - za(i1,i2)*za(i3,i4)*zb(i3,i2))*
     -        (gam - za(i3,i4)*zb(i4,i3))*
     -        (gam*zab2(i4,i1,i2,i4) + 
     -        za(i1,i2)*za(i3,i4)*zb(i2,i1)*zb(i4,i3)))/
     -        (gam**3*za(i3,i4)*zab2(i1,i3,i4,i2)*zab2(i2,i3,i4,i1)*
     -        zab2(i3,i1,i2,i4))

         gam = -mp12-sqrt(mp12**2-s(i1,i2)*s(i3,i4))

         tric(2) = tric(2)-((-(gam*za(i2,i4)*zb(i2,i1)) - 
     -        za(i1,i2)*za(i3,i4)*zb(i2,i1)*zb(i3,i1))*
     -        (gam*za(i1,i4)*zb(i2,i1) - 
     -        za(i1,i2)*za(i3,i4)*zb(i2,i1)*zb(i3,i2))*
     -        (-gam + za(i3,i4)*zb(i4,i3))*
     -        (gam*zab2(i4,i1,i2,i4) + 
     -        za(i1,i2)*za(i3,i4)*zb(i2,i1)*zb(i4,i3)))/
     -        (gam**3*za(i3,i4)*zab2(i1,i3,i4,i2)*zab2(i2,i3,i4,i1)*
     -        zab2(i3,i1,i2,i4))

         Triags = tric(1)*I3m(s(i2,i3),s(i1,i4),s1234)
     &        +tric(2)*I3m(s(i1,i2),s(i3,i4),s1234)

         Bubs = (lnrat(-t(i1,i3,i4),-s(i1,i4))*za(i1,i4)*
     -        zab2(i4,i1,i3,i2))/(2.*t(i1,i3,i4)*za(i1,i3)**2) + 
     -        (3*L0(-s(i1,i4),-t(i1,i3,i4))*za(i1,i4)*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)*zb(i3,i1))/
     -        (2.*t(i1,i3,i4)**2*za(i1,i3)**2) + 
     -        (L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)*zb(i3,i1))/
     -        (t(i1,i3,i4)**2*za(i1,i3)**2) - 
     -        (L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)*zab2(i4,i1,i3,i2)*
     -        zb(i3,i1))/(t(i1,i3,i4)**2*za(i1,i3)) + 
     -        (L1(-s(i3,i4),-t(i1,i3,i4))*za(i1,i4)*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)*zb(i3,i1)**2)/
     -        (2.*t(i1,i3,i4)**3*za(i1,i3)) - 
     -        (L0(-s(i3,i4),-t(i2,i3,i4))*za(i2,i4)*zab2(i4,i2,i3,i1)*
     -        zb(i3,i2))/(t(i2,i3,i4)**2*za(i2,i3)) + 
     -        (L1(-s(i3,i4),-t(i2,i3,i4))*za(i2,i4)*za(i3,i4)*
     -        zab2(i2,i3,i4,i1)*zb(i3,i2)**2)/
     -        (2.*t(i2,i3,i4)**3*za(i2,i3)) - 
     -        (L1(-s(i1,i4),-t(i1,i3,i4))*za(i1,i4)*za(i3,i4)**2*
     -        zb(i3,i2)*zb(i4,i3))/(2.*t(i1,i3,i4)**2*za(i1,i3)**2)

         Rat = -(za(i1,i4)*zab2(i4,i1,i3,i2)*zb(i3,i1))/
     -        (2.*t(i1,i3,i4)**2*za(i1,i3)) - 
     -        (za(i1,i4)*za(i3,i4)*zb(i3,i2))/
     -        (2.*t(i1,i3,i4)*za(i1,i3)**2) - 
     -        (za(i2,i4)*zab2(i4,i2,i3,i1)*zb(i3,i2))/
     -        (2.*t(i2,i3,i4)**2*za(i2,i3)) - 
     -        (za(i2,i4)*zb(i2,i1)*zb(i3,i2))/
     -        (2.*t(i2,i3,i4)*za(i2,i3)*zb(i4,i2)) + 
     -        (zb(i2,i1)*zb(i3,i1))/
     -        (2.*za(i2,i3)*zb(i4,i1)*zb(i4,i2)) + 
     -        (zb(i3,i1)**2*zb(i3,i2))/
     -        (2.*t(i1,i3,i4)*zb(i4,i1)*zb(i4,i3)) + 
     -        (zb(i3,i1)*zb(i3,i2))/
     -        (2.*za(i2,i3)*zb(i4,i2)*zb(i4,i3)) - 
     -        (za(i2,i4)*zb(i3,i2)**2*zb(i4,i1))/
     -        (2.*t(i2,i3,i4)*za(i2,i3)*zb(i4,i2)*zb(i4,i3))
      endif

      Hbbgg_vamps_pppm_slc = Vpole + Boxes - Triags + Rat - Bubs
!     write(6,*) 'Atree = ',Atree
!     write(6,*) 'Vpole = ',Vpole/im
!     write(6,*) 'Boxes = ',Boxes/im
!     write(6,*) 'Triangles = ',triags/im
!     write(6,*) 'Bubs  = ',Bubs/im
!     write(6,*) 'Total CC  = ',(Hbbgg_vamps_pppm_slc-Rat)/(im)
!     write(6,*) 'Rat  = ', Rat/im
!     write(6,*) '       '
!     write(6,*) ' Sum  = ',Hbbgg_vamps_pppm_slc/im
!     stop

      return
      end

************************************************************************

c     NF quark-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), +++-.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter :: czip=(0d0,0d0)

c     NF pieces vanish for this helicity. 
      Hbbgg_vamps_pppm_nf = czip

      return
      end

************************************************************************

c     Del34 piece for
c     H -> b(p1) bbar(p2) g(p3) g(p4), +++-.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_pppm_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(24),boxc(24),tric(1)
      complex(8)             :: Vpole,Boxes
      complex(8)             :: zab2
c     Externals.
      complex(8), external  :: lnrat,Lsm1,Lsm1_2mht,L0,L1,I3m

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Boxes = czip

      select case(ipole)
      case(-1)
         Vpole =
     .        (
     .        + lnrat(musq,-s(i1,i2))
     .        - lnrat(musq,-s(i1,i3))
     .        - lnrat(musq,-s(i2,i4))
     .        + lnrat(musq,-s(i3,i4))
     .        )*(
     .        - ((za(i2,i4)*zab2(i4,i2,i3,i1)*zb(i3,i2))/
     -        (t(i2,i3,i4)*za(i2,i3)*za(i3,i4)*zb(i4,i3)))
     .        + (zab2(i4,i2,i3,i1)*zb(i3,i1))/
     -        (za(i2,i3)*za(i3,i4)*zb(i4,i1)*zb(i4,i3))
     .        + (zab2(i4,i1,i3,i2)*zb(i3,i1)**2)/
     -        (t(i1,i3,i4)*za(i3,i4)*zb(i4,i1)*zb(i4,i3))
     .        )
     .        + (
     .        + lnrat(musq,-s(i1,i2))
     .        - lnrat(musq,-s(i1,i4))
     .        - lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
     .        )*(
     .        + (za(i1,i4)*zab2(i4,i1,i3,i2)*zb(i3,i1))/
     -        (t(i1,i3,i4)*za(i1,i3)*za(i3,i4)*zb(i4,i3))
     .        - (zab2(i4,i1,i3,i2)*zb(i3,i2))/
     -        (za(i1,i3)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))
     .        - (zab2(i4,i2,i3,i1)*zb(i3,i2)**2)/
     -        (t(i2,i3,i4)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))
     .        )
      case(0)
         Vpole =
     .        + (
     .        + (
     .        + lnrat(musq,-s(i1,i2))**2
     .        - lnrat(musq,-s(i1,i3))**2
     .        - lnrat(musq,-s(i2,i4))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )*(
     .        - ((za(i2,i4)*zab2(i4,i2,i3,i1)*zb(i3,i2))/
     -        (t(i2,i3,i4)*za(i2,i3)*za(i3,i4)*zb(i4,i3)))
     .        + (zab2(i4,i2,i3,i1)*zb(i3,i1))/
     -        (za(i2,i3)*za(i3,i4)*zb(i4,i1)*zb(i4,i3))
     .        + (zab2(i4,i1,i3,i2)*zb(i3,i1)**2)/
     -        (t(i1,i3,i4)*za(i3,i4)*zb(i4,i1)*zb(i4,i3))
     .        )
     .        )/2d0
     .        + (
     .        + (
     .        + lnrat(musq,-s(i1,i2))**2
     .        - lnrat(musq,-s(i1,i4))**2
     .        - lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )*(
     .        + (za(i1,i4)*zab2(i4,i1,i3,i2)*zb(i3,i1))/
     -        (t(i1,i3,i4)*za(i1,i3)*za(i3,i4)*zb(i4,i3))
     .        - (zab2(i4,i1,i3,i2)*zb(i3,i2))/
     -        (za(i1,i3)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))
     .        - (zab2(i4,i2,i3,i1)*zb(i3,i2)**2)/
     -        (t(i2,i3,i4)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))
     .        )
     .        )/2d0
      end select

      if (ipole.eq.0)then
         boxi4(1) = Lsm1_2mht(s(i2,i4),t(i1,i3,i4),s(i1,i3),s1234)
         boxi4(2) = Lsm1_2mht(s(i2,i4),t(i1,i2,i3),s(i1,i3),s1234)

         boxi4(3) = Lsm1_2mht(s(i2,i3),t(i1,i3,i4),s(i1,i4),s1234)
         boxi4(4) = Lsm1_2mht(s(i2,i3),t(i1,i2,i4),s(i1,i4),s1234)

         boxi4(5) = Lsm1(-s(i2,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         boxi4(6) = Lsm1(-s(i2,i3),-t(i2,i3,i4),-s(i3,i4),-t(i2,i3,i4))
         boxi4(7) = Lsm1(-s(i2,i4),-t(i2,i3,i4),-s(i3,i4),-t(i2,i3,i4))

         boxi4(8) = Lsm1_2mht(s(i1,i4),t(i2,i3,i4),s(i2,i3),s1234)
         boxi4(9) = Lsm1_2mht(s(i1,i4),t(i1,i2,i3),s(i2,i3),s1234)

         boxi4(10) = Lsm1_2mht(s(i1,i3),t(i2,i3,i4),s(i2,i4),s1234)
         boxi4(11) = Lsm1_2mht(s(i1,i3),t(i1,i2,i4),s(i2,i4),s1234)

         boxi4(12) = Lsm1(-s(i1,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         boxi4(13) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         boxi4(14) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         boxi4(15) = Lsm1_2mht(s(i1,i2),t(i2,i3,i4),s(i3,i4),s1234)
         boxi4(16) = Lsm1_2mht(s(i1,i2),t(i1,i3,i4),s(i3,i4),s1234)

         boxi4(17) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i1,i2),-t(i1,i2,i3))
         boxi4(18) = Lsm1(-s(i1,i2),-t(i1,i2,i4),-s(i2,i4),-t(i1,i2,i4))

         boxi4(19) = Lsm1_2mht(s(i3,i4),t(i1,i2,i3),s(i1,i2),s1234)

         boxi4(20) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i1,i2),-t(i1,i2,i4))
         boxi4(21) = Lsm1(-s(i1,i2),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))

         boxi4(22) = Lsm1_2mht(s(i3,i4),t(i1,i2,i4),s(i1,i2),s1234)

         boxi4(23) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))
         boxi4(24) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i2,i4),-t(i1,i2,i4))

         boxc(1) = ((za(i2,i4)*zab2(i4,i1,i3,i2)**3*zb(i4,i2))/
     .        (za(i3,i4)*zab2(i1,i3,i4,i2)*zab2(i3,i1,i4,i2)) + 
     .        (s1234*za(i2,i4)*zb(i3,i1)**3*zb(i4,i2))/
     .        (zab2(i2,i3,i4,i1)*zb(i4,i1)*zb(i4,i3)))/
     .        (t(i1,i3,i4)*za(i2,i4)*zb(i4,i2))
       
         boxc(2) = -(t(i1,i2,i3)**2
     .        /(za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i2,i4)))
       
         boxc(3) = (-((za(i1,i4)*zab2(i4,i1,i3,i2)**2)/
     .        (za(i1,i3)*za(i3,i4)*zab2(i1,i3,i4,i2))) - 
     .        (s1234*zab2(i2,i1,i4,i3)*zb(i3,i1)**2)/
     .        (zab2(i2,i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3)))
     .        /t(i1,i3,i4)

         boxc(4) =-((s1234*zb(i2,i1)**2)
     .        /(zab2(i3,i1,i2,i4)*zab2(i3,i2,i4,i1)*zb(i4,i2)))

         boxc(5) = ((s1234*za(i2,i3)*za(i2,i4)*zb(i3,i2)**3)/
     .        (t(i2,i3,i4)*zab2(i1,i2,i3,i4)) + 
     .        (za(i2,i4)*zab2(i4,i2,i3,i1)**2*zb(i3,i2)*zb(i4,i2))/
     .        (t(i2,i3,i4)*zab2(i3,i2,i4,i1)))/
     .        (za(i2,i3)*za(i2,i4)*zb(i3,i2)*zb(i4,i2))
       
C     boxc(5)=      ((s1234*za(i2,i3)*za(i2,i4)*zb(i3,i2)**3)/
C     -     (t(i2,i3,i4)*zab2(i1,i2,i3,i4)) + 
C     -    (za(i2,i4)*zab2(i4,i2,i3,i1)**2*zb(i3,i2)*zb(i4,i2))/
C     -     (t(i2,i3,i4)*zab2(i3,i2,i4,i1)))/
C     -  (za(i2,i4)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))

         boxc(6) = (-((s1234*za(i2,i3)*za(i3,i4)
     .        *zab2(i1,i2,i4,i3)*zb(i3,i2)**3)/
     .        (t(i2,i3,i4)*zab2(i1,i2,i3,i4)*zab2(i1,i3,i4,i2))) - 
     .        (za(i2,i4)*zab2(i4,i2,i3,i1)**2*zb(i3,i2)*zb(i4,i3))/
     .        (t(i2,i3,i4)*zab2(i2,i3,i4,i1)))/(s(i2,i3)*s(i3,i4))

         boxc(7) = ((s1234*za(i2,i4)*za(i3,i4)*zb(i3,i2)**3)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)) - 
     -        (za(i2,i4)*za(i3,i4)**3*zab2(i2,i3,i4,i1)**2
     .        *zb(i4,i2)*zb(i4,i3))/
     -        (t(i2,i3,i4)*za(i2,i3)**3*zab2(i3,i2,i4,i1)) + 
     -        (za(i2,i4)**4*zab2(i3,i2,i4,i1)**2*zb(i4,i2)*zb(i4,i3))/
     -        (t(i2,i3,i4)*za(i2,i3)**3*zab2(i2,i3,i4,i1)))/
     -        (za(i2,i4)*za(i3,i4)*zb(i4,i2)*zb(i4,i3))

         boxc(8) = (-((za(i1,i4)*zab2(i4,i2,i3,i1)**3*zb(i4,i1))/
     -        (za(i3,i4)*zab2(i2,i3,i4,i1)*zab2(i3,i2,i4,i1))) - 
     -        (s1234*za(i1,i4)*zb(i3,i2)**3*zb(i4,i1))/
     -        (zab2(i1,i3,i4,i2)*zb(i4,i2)*zb(i4,i3)))/
     -        (t(i2,i3,i4)*za(i1,i4)*zb(i4,i1))

         boxc(9) = t(i1,i2,i3)**2
     .        /(za(i1,i3)*zab2(i2,i1,i3,i4)*zab2(i3,i1,i2,i4))

         boxc(10) = ((za(i1,i3)*zab2(i4,i2,i3,i1)**2*zb(i3,i1))/
     -        (za(i2,i3)*zab2(i3,i2,i4,i1)) + 
     -        (za(i1,i3)*zab2(i4,i2,i3,i1)**3*zb(i3,i1))/
     -        (za(i3,i4)*zab2(i2,i3,i4,i1)*zab2(i3,i2,i4,i1)) + 
     -        (s1234*za(i1,i3)*zb(i3,i1)*zb(i3,i2)**2)
     .        /(zab2(i1,i2,i3,i4)*zb(i4,i2)) + 
     -        (s1234*za(i1,i3)*zb(i3,i1)*zb(i3,i2)**3)/
     -        (zab2(i1,i3,i4,i2)*zb(i4,i2)*zb(i4,i3)))/
     -        (t(i2,i3,i4)*za(i1,i3)*zb(i3,i1))
       
         boxc(11) = (s1234*zb(i2,i1)**2)
     .        /(zab2(i3,i1,i2,i4)*zab2(i3,i1,i4,i2)*zb(i4,i1))
       
         boxc(12) = (-((s1234*za(i1,i3)*za(i1,i4)*zb(i3,i1)**3)/
     -        (t(i1,i3,i4)*zab2(i2,i1,i3,i4))) - 
     -        (za(i1,i4)*zab2(i4,i1,i3,i2)**2*zb(i3,i1)*zb(i4,i1))/
     -        (t(i1,i3,i4)*zab2(i3,i1,i4,i2)))/
     -        (za(i1,i3)*za(i1,i4)*zb(i3,i1)*zb(i4,i1))

         boxc(13) =     ((s1234*za(i1,i3)*za(i3,i4)*zb(i3,i1)**4)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i1)) + 
     -        (za(i1,i4)*zab2(i4,i1,i3,i2)**2*zb(i3,i1)*zb(i4,i3))/
     -        (t(i1,i3,i4)*zab2(i1,i3,i4,i2)) + 
     -        (s1234*za(i1,i3)*za(i3,i4)*zb(i3,i1)**3*zb(i4,i3))/
     -        (t(i1,i3,i4)*zab2(i2,i1,i3,i4)*zb(i4,i1)))/
     -        (za(i1,i3)*za(i3,i4)*zb(i3,i1)*zb(i4,i3))

         boxc(14) = (-((s1234*za(i1,i4)*za(i3,i4)*zb(i3,i1)**3)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1))) + 
     -        (za(i1,i4)*za(i3,i4)**3*zab2(i1,i3,i4,i2)**2
     .        *zb(i4,i1)*zb(i4,i3))/
     -        (t(i1,i3,i4)*za(i1,i3)**3*zab2(i3,i1,i4,i2)) - 
     -        (za(i1,i4)**4*zab2(i3,i1,i4,i2)**2*zb(i4,i1)*zb(i4,i3))/
     -        (t(i1,i3,i4)*za(i1,i3)**3*zab2(i1,i3,i4,i2)))/
     -        (za(i1,i4)*za(i3,i4)*zb(i4,i1)*zb(i4,i3))

         boxc(15) = -((zab2(i4,i2,i3,i1)**2
     .        /(za(i2,i3)*zab2(i3,i2,i4,i1)) + 
     -        (s1234*zb(i3,i2)**2)
     .        /(zab2(i1,i2,i3,i4)*zb(i4,i2)))/t(i2,i3,i4))

         boxc(16) = (zab2(i4,i1,i3,i2)**2
     .        /(za(i1,i3)*zab2(i3,i1,i4,i2)) + 
     -        (s1234*zb(i3,i1)**2)/(zab2(i2,i1,i3,i4)*zb(i4,i1)))
     .        /t(i1,i3,i4)

         boxc(17) = -(t(i1,i2,i3)**2
     .        /(za(i1,i3)*zab2(i2,i1,i3,i4)*zab2(i3,i1,i2,i4)))
         boxc(18) = (s1234*zb(i2,i1)**2)
     .        /(zab2(i3,i1,i2,i4)*zab2(i3,i2,i4,i1)*zb(i4,i2))

         boxc(19) = (t(i1,i2,i3)**2*za(i1,i2))/
     -        (za(i1,i3)*za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i2,i1,i3,i4))
       
         boxc(20) = -((s1234*zb(i2,i1)**2)
     .        /(zab2(i3,i1,i2,i4)*zab2(i3,i1,i4,i2)*zb(i4,i1)))
         boxc(21) = t(i1,i2,i3)**2
     .        /(za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i3,i1,i2,i4))

         boxc(22) = (s1234*zb(i2,i1)**3)
     .        /(zab2(i3,i1,i4,i2)*zab2(i3,i2,i4,i1)*zb(i4,i1)*zb(i4,i2))

         boxc(23) = -((t(i1,i2,i3)**2*za(i1,i2))/
     -        (za(i1,i3)*za(i2,i3)*zab2(i1,i2,i3,i4)*zab2(i2,i1,i3,i4)))

         boxc(24) = -((s1234*zb(i2,i1)**3)
     .        /(zab2(i3,i1,i4,i2)*zab2(i3,i2,i4,i1)
     .        *zb(i4,i1)*zb(i4,i2)))

         do i=1,24
            Boxes = Boxes + boxc(i)*boxi4(i)
         enddo
      endif

      Hbbgg_vamps_pppm_del34 = Vpole + Boxes

!     write(6,*) 'Vpole = ',Vpole/im
!     write(6,*) 'Boxes = ',Boxes/im
!     write(6,*) 'Total CC  = ',(Hbbgg_vamps_pppm_del34)/(im)
!     stop

      return
      end

************************************************************************

c     Leading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ++--.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_ppmm_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(3),boxc(3)
      complex(8)             :: Atree,Vpole,Boxes,Bubs,Rat
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: Hbbgg_mmpp
      complex(8), external   :: lnrat,Lsm1,Lsm1_2me,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = zb(i1,i2)**2/(zb(i4,i1)*zb(i2,i3)*zb(i3,i4))
      Vpole = czip
      Boxes = czip
      Bubs  = czip
      Rat   = czip

      select case(ipole)
      case(-2)
         Vpole = 3
      case(-1)
         Vpole =
     .        + lnrat(musq,-s(i1,i4))
     .        + lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
      case(0)
         Vpole =
     .        + (
     .        + lnrat(musq,-s(i1,i4))**2
     .        + lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )/2.
      end select

      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2me(t(i1,i3,i4),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(2) = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(3) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

c     Full coefficient.
c         boxc(1)= Atree*(t(i1,i3,i4)*t(i2,i3,i4)-s1234*s(i3,i4))
c         boxc(2) = Atree*(s(i3,i4)*s(i2,i3))
c         boxc(3) = Atree*(s(i3,i4)*s(i1,i4))      

c     Minus GDet.
         boxc(1) = Atree
         boxc(2) = Atree
         boxc(3) = Atree
      
         Boxes = czip
         do i=1,3
            Boxes = Boxes+BoxI4(i)*boxc(i)
         enddo

         Bubs = (-2*L0(-s(i1,i4),-t(i1,i3,i4))*za(i4,i3)*zb(i1,i2))/
     -     (t(i1,i3,i4)*zb(i3,i4)) - 
     -     (L1(-s(i1,i4),-t(i1,i3,i4))*za(i4,i3)**2*zb(i3,i2)*
     -     zb(i4,i1))/(2.*t(i1,i3,i4)**2*zb(i3,i4)) + 
     -     (2*L0(-s(i2,i3),-t(i2,i3,i4))*za(i3,i4)*zb(i2,i1))/
     -     (t(i2,i3,i4)*zb(i4,i3)) + 
     -     (L1(-s(i2,i3),-t(i2,i3,i4))*za(i3,i4)**2*zb(i3,i2)*
     -     zb(i4,i1))/(2.*t(i2,i3,i4)**2*zb(i4,i3))

c     Completed rational.
         Rat = -(zab2(i4,i1,i3,i2)*zb(i4,i1))/
     -     (3.*t(i1,i3,i4)*zb(i4,i3)**2) - 
     -     (zab2(i4,i2,i3,i1)*zb(i4,i2))/
     -     (3.*t(i2,i3,i4)*zb(i4,i3)**2) - 
     -     (za(i3,i4)*zb(i2,i1))/(2.*t(i1,i3,i4)*zb(i4,i3)) - 
     -     (za(i3,i4)*zb(i2,i1))/(2.*t(i2,i3,i4)*zb(i4,i3))
      endif

      Hbbgg_vamps_ppmm_lc = -Vpole - Boxes + Rat - Bubs

      return
      end

************************************************************************

c     Subleading-colour one-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ++--.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_ppmm_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(5),boxc(5)
      complex(8)             :: Atree,Vpole,Boxes,Bubs,Rat
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2me,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = zb(i1,i2)**2/(zb(i4,i1)*zb(i2,i3)*zb(i3,i4))
      Vpole = 0d0
      Boxes = 0d0
      Bubs  = 0d0
      Rat   = 0d0

      select case(ipole)
      case(-2)
         Vpole = 1d0
      case(-1)
         Vpole = lnrat(musq,-s(i1,i2))
      case(0)
         Vpole = lnrat(musq,-s(i1,i2))**2/2d0
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1_2me(t(i1,i2,i4),t(i1,i3,i4),s(i1,i4),s1234)
         BoxI4(2) = Lsm1_2me(t(i1,i2,i3),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(3) = Lsm1_2me(t(i1,i2,i3),t(i1,i2,i4),s(i1,i2),s1234)
         BoxI4(4) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i1,i2),-t(i1,i2,i4))
         BoxI4(5) = Lsm1(-s(i1,i2),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))

         boxc(:) = Atree

         boxes = czip
         do i=1,5
            Boxes = Boxes+BoxI4(i)*boxc(i)
         enddo

         Bubs = (L0(-s(i1,i4),-t(i1,i3,i4))*za(i4,i3)*zb(i1,i2))/
     -     (t(i1,i3,i4)*zb(i3,i4)) - 
     -     (L1(-s(i1,i4),-t(i1,i3,i4))*za(i4,i3)**2*zb(i3,i2)*
     -     zb(i4,i1))/(2.*t(i1,i3,i4)**2*zb(i3,i4)) - 
     -     (L0(-s(i2,i3),-t(i2,i3,i4))*za(i3,i4)*zb(i2,i1))/
     -     (t(i2,i3,i4)*zb(i4,i3)) + 
     -     (L1(-s(i2,i3),-t(i2,i3,i4))*za(i3,i4)**2*zb(i3,i2)*
     -     zb(i4,i1))/(2.*t(i2,i3,i4)**2*zb(i4,i3))
         
         Rat = -(za(i3,i4)*zb(i2,i1))/(2.*t(i1,i3,i4)*zb(i4,i3)) - 
     -     (za(i3,i4)*zb(i2,i1))/(2.*t(i2,i3,i4)*zb(i4,i3))
      end if

      Hbbgg_vamps_ppmm_slc = Vpole + Boxes - Bubs + Rat
!     write(6,*) 'Atree = ',Atree
!     write(6,*) 'Vpole = ',Vpole/im
!     write(6,*) 'Boxes = ',Boxes/im
!     write(6,*) 'Bubs  = ',Bubs/im
!     write(6,*) 'Total CC  = ',(Vpole+Boxes-Bubs)/(im)
!     write(6,*) 'Rat  = ', Rat/im
!     write(6,*) '       '
!     write(6,*) ' Sum  = ',Hbbgg_vamps_ppmm_slc/im
!     stop

      return
      end

************************************************************************

c     Nf quark-loop amplitude for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ++--.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: Atree,Rat,Vpole
      complex(8)             :: zab2
c     Externals.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2me,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Atree = zb(i1,i2)**2/(zb(i4,i1)*zb(i2,i3)*zb(i3,i4))
      Vpole = 0d0
      Rat   = 0d0
   
      if (ipole.eq.0)then
         Rat = zb(i2,i1)/(3.*zb(i4,i3)**2) - 
     -        (za(i1,i3)*zb(i2,i1)*zb(i3,i1))/
     -        (3.*t(i1,i3,i4)*zb(i4,i3)**2) - 
     -        (za(i2,i4)*zb(i2,i1)*zb(i4,i2))/
     -        (3.*t(i2,i3,i4)*zb(i4,i3)**2) - 
     -        (za(i3,i4)*zb(i3,i1)*zb(i4,i2))/
     -        (3.*t(i1,i3,i4)*zb(i4,i3)**2) - 
     -        (za(i3,i4)*zb(i3,i1)*zb(i4,i2))/
     -        (3.*t(i2,i3,i4)*zb(i4,i3)**2)
      endif

      Hbbgg_vamps_ppmm_nf = Vpole + Rat

!     write(6,*) ' Sum  = ',Hbbgg_vamps_ppmm_nf/im
!     stop

      return
      end

************************************************************************

c     Del34 piece for
c     H -> b(p1) bbar(p2) g(p3) g(p4), ++--.
c     CW - Summer 18.
      complex(8) function Hbbgg_vamps_ppmm_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: musq,s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: epinv
      real(8)                :: t,s1234
      complex(8)             :: BoxI4(18),boxc(18)
      complex(8)             :: Vpole,Boxes
      complex(8)             :: zab2
c     Externals.
      complex(8), external  :: lnrat,Lsm1,Lsm1_2me,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Boxes = czip

      select case(ipole)
      case(-1)
         Vpole =
     .        + (
     .        + (
     .        - lnrat(musq,-s(i1,i2))
     .        + lnrat(musq,-s(i1,i3))
     .        + lnrat(musq,-s(i2,i4))
     .        - lnrat(musq,-s(i3,i4))
     .        )*zb(i2,i1)**2)/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3))
     .        + (
     .        + (
     .        + lnrat(musq,-s(i1,i2))
     .        - lnrat(musq,-s(i1,i4))
     .        - lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i3,i4))
     .        )*zb(i2,i1)**2)/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))
      case(0)
         Vpole =
     .        + (
     .        + (
     .        - lnrat(musq,-s(i1,i2))**2
     .        + lnrat(musq,-s(i1,i3))**2
     .        + lnrat(musq,-s(i2,i4))**2
     .        - lnrat(musq,-s(i3,i4))**2
     .        )*zb(i2,i1)**2)/(2.*zb(i3,i2)*zb(i4,i1)*zb(i4,i3))
     .        + (
     .        + (
     .        + lnrat(musq,-s(i1,i2))**2
     .        - lnrat(musq,-s(i1,i4))**2
     .        - lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i3,i4))**2
     .        )*zb(i2,i1)**2)/(2.*zb(i3,i1)*zb(i4,i2)*zb(i4,i3))
      end select
      
      if (ipole.eq.0)then
         BoxI4(1)  = Lsm1_2me(t(i1,i3,i4),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(2)  = Lsm1_2me(t(i1,i2,i3),t(i1,i3,i4),s(i1,i3),s1234)
         BoxI4(3)  = Lsm1_2me(t(i1,i2,i4),t(i1,i3,i4),s(i1,i4),s1234)

         BoxI4(4)  = Lsm1(-s(i2,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(5)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(6)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i4),-t(i2,i3,i4))

         BoxI4(7)  = Lsm1_2me(t(i1,i2,i3),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(8)  = Lsm1_2me(t(i1,i2,i4),t(i2,i3,i4),s(i2,i4),s1234)

         BoxI4(9)  = Lsm1(-s(i1,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(10) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(11) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         BoxI4(12) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i1,i2),-t(i1,i2,i3))

         BoxI4(13) = Lsm1_2me(t(i1,i2,i3),t(i1,i2,i4),s(i1,i2),s1234)

         BoxI4(14) = Lsm1(-s(i1,i2),-t(i1,i2,i4),-s(i2,i4),-t(i1,i2,i4))
         BoxI4(15) = Lsm1(-s(i1,i4),-t(i1,i2,i4),-s(i1,i2),-t(i1,i2,i4))
         BoxI4(16) = Lsm1(-s(i1,i2),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))
         BoxI4(17) = Lsm1(-s(i1,i3),-t(i1,i2,i3),-s(i2,i3),-t(i1,i2,i3))
         BoxI4(18) = Lsm1(-s(i2,i4),-t(i1,i2,i4),-s(i1,i4),-t(i1,i2,i4))

c     GD factored out.
         boxc(1)  = (-zb(i2,i1)**3
     .        /(2.*zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2))*2d0)
         boxc(2)  = (zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3)))
         boxc(3)  = -zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))
      
         boxc(4)  = (-(zb(i3,i2)**3*zb(i4,i1)**3) + 
     .        zb(i3,i1)**3*zb(i4,i2)**3)/
     .        (zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2)*
     .        zb(i4,i3)**3)

         boxc(5)  = -(zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3)))
         boxc(6)  = zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))

         boxc(7)  = -(zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3)))
         boxc(8)  =  zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3))

         boxc(9)  = (-(zb(i3,i2)**3*zb(i4,i1)**3)
     .        + zb(i3,i1)**3*zb(i4,i2)**3)/
     .        (zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2)*zb(i4,i3)**3)

         boxc(10) = zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))
         boxc(11) = -(zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3)))
         boxc(12) = zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))

         boxc(13) = -(zb(i2,i1)**3
     .        /(zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2)))

         boxc(14) = zb(i2,i1)**2/(zb(i3,i1)*zb(i4,i2)*zb(i4,i3))
         boxc(15) = -(zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3)))
         boxc(16) = -(zb(i2,i1)**2/(zb(i3,i2)*zb(i4,i1)*zb(i4,i3)))
         boxc(17) = (zb(i2,i1)**3
     .        /(zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2)))
         boxc(18) = (zb(i2,i1)**3
     .        /(zb(i3,i1)*zb(i3,i2)*zb(i4,i1)*zb(i4,i2)))

         do i=1,18
            Boxes = Boxes + boxi4(i)*boxc(i)
         enddo
      endif

      Hbbgg_vamps_ppmm_del34 = Vpole + Boxes

!     write(6,*) 'Boxes ',Boxes
!     write(6,*) 'Vpole ',vpole
!     write(6,*) 'tota del',Hbbgg_vamps_ppmm_del34/im
!     stop

      return
      end

c-----------------------------------------------------------------------

      subroutine Hbbgg_vamps_fill(i1,i2,i3,i4,s,za,zb,musq,ipole,
     .     Hbbgg_lc,Hbbgg_slc,Hbbgg_nf)
      implicit none
      integer, intent(in)     :: i1,i2,i3,i4,ipole
      real(8), intent(in)     :: s(5,5),musq
      complex(8), intent(in)  :: za(5,5),zb(5,5)
      complex(8), intent(out) :: Hbbgg_lc(1:2,2,2,2)
      complex(8), intent(out) :: Hbbgg_slc(1:2,2,2,2)
      complex(8), intent(out) :: Hbbgg_nf(1:2,2,2,2)
      complex(8), parameter   :: czip=(0d0,0d0)
      integer                 :: icol
      complex(8), external    :: Hbbgg_vamps_pppm_lc
      complex(8), external    :: Hbbgg_vamps_pppm_slc
      complex(8), external    :: Hbbgg_vamps_pppm_nf
      complex(8), external    :: Hbbgg_vamps_ppmm_lc
      complex(8), external    :: Hbbgg_vamps_ppmm_slc
      complex(8), external    :: Hbbgg_vamps_ppmm_nf
      complex(8), external    :: Hbbgg_vamps_allp_lc
      complex(8), external    :: Hbbgg_vamps_allp_slc
      complex(8), external    :: Hbbgg_vamps_allp_nf
      
      Hbbgg_lc(:,:,:,:)  = czip
      Hbbgg_slc(:,:,:,:) = czip
      Hbbgg_nf(:,:,:,:)  = czip

!---- icol =1 
      icol=1
!---- LC helicity amplitudes-------------------------------------
      Hbbgg_lc(icol,2,2,2) = Hbbgg_vamps_allp_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,1,1) = Hbbgg_vamps_allp_lc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_lc(icol,2,2,1) = Hbbgg_vamps_pppm_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,1,2) = Hbbgg_vamps_pppm_lc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

      Hbbgg_lc(icol,2,1,2) = -Hbbgg_vamps_pppm_lc(i2,i1,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,2,1) = -Hbbgg_vamps_pppm_lc(i2,i1,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_lc(icol,2,1,1) = Hbbgg_vamps_ppmm_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,2,2) = Hbbgg_vamps_ppmm_lc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)
      
!---- SLC helicity amplitudes-------------------------------------
      Hbbgg_slc(icol,2,2,2) = Hbbgg_vamps_allp_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,1,1) = Hbbgg_vamps_allp_slc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_slc(icol,2,2,1) = Hbbgg_vamps_pppm_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,1,2) = Hbbgg_vamps_pppm_slc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

      Hbbgg_slc(icol,2,1,2) = -Hbbgg_vamps_pppm_slc(i2,i1,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,2,1) = -Hbbgg_vamps_pppm_slc(i2,i1,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_slc(icol,2,1,1) = Hbbgg_vamps_ppmm_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,2,2) = Hbbgg_vamps_ppmm_slc(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

!---- nf helicity amplitudes-------------------------------------
      Hbbgg_nf(icol,2,2,2) = Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,1,1) = Hbbgg_vamps_allp_nf(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_nf(icol,2,2,1) = Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,1,2) = Hbbgg_vamps_pppm_nf(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

      Hbbgg_nf(icol,2,1,2) = -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,2,1) = -Hbbgg_vamps_pppm_nf(i2,i1,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_nf(icol,2,1,1) = Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,2,2) = Hbbgg_vamps_ppmm_nf(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

      icol=2
!---- LC helicity amplitudes-------------------------------------
      Hbbgg_lc(icol,2,2,2) = Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,1,1) = Hbbgg_vamps_allp_lc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_lc(icol,2,1,2) = Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,2,1) = Hbbgg_vamps_pppm_lc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

      Hbbgg_lc(icol,2,2,1) = -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,1,2) = -Hbbgg_vamps_pppm_lc(i2,i1,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_lc(icol,2,1,1) = Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_lc(icol,1,2,2) = Hbbgg_vamps_ppmm_lc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

!---- SLC helicity amplitudes-------------------------------------
      Hbbgg_slc(icol,2,2,2) = Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,1,1) = Hbbgg_vamps_allp_slc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_slc(icol,2,1,2) = Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,2,1) = Hbbgg_vamps_pppm_slc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

      Hbbgg_slc(icol,2,2,1) = -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,1,2) = -Hbbgg_vamps_pppm_slc(i2,i1,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_slc(icol,2,1,1) = Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_slc(icol,1,2,2) = Hbbgg_vamps_ppmm_slc(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

!---- nf helicity amplitudes-------------------------------------
      Hbbgg_nf(icol,2,2,2) = Hbbgg_vamps_allp_nf(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,1,1) = Hbbgg_vamps_allp_nf(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)
      Hbbgg_nf(icol,2,1,2) = Hbbgg_vamps_pppm_nf(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,2,1) = Hbbgg_vamps_pppm_nf(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

      Hbbgg_nf(icol,2,2,1) = -Hbbgg_vamps_pppm_nf(i2,i1,i3,i4,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,1,2) = -Hbbgg_vamps_pppm_nf(i2,i1,i3,i4,s,zb,za,
     .     musq,ipole)
      Hbbgg_nf(icol,2,1,1) = Hbbgg_vamps_ppmm_nf(i1,i2,i4,i3,s,za,zb,
     .     musq,ipole)
      Hbbgg_nf(icol,1,2,2) = Hbbgg_vamps_ppmm_nf(i1,i2,i4,i3,s,zb,za,
     .     musq,ipole)

      return
      end

************************************************************************

      subroutine Hbbgg_vamps_delfill(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole,Hbbgg_del)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      real(8), parameter     :: czip=(0d0,0d0)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      complex(8)             :: Hbbgg_del(2,2,2)
      complex(8), external   :: Hbbgg_vamps_pppm_del34
      complex(8), external   :: Hbbgg_vamps_ppmm_del34
      complex(8), external   :: Hbbgg_vamps_allp_del34
      
      Hbbgg_del(:,:,:)=czip

!===== all + 
      Hbbgg_del(2,2,2) = Hbbgg_vamps_allp_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
!===== all -
      Hbbgg_del(1,1,1) = Hbbgg_vamps_allp_del34(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

!===== Single minus normal ordering
      Hbbgg_del(2,2,1) = Hbbgg_vamps_pppm_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
!----- and conj
      Hbbgg_del(1,1,2) = Hbbgg_vamps_pppm_del34(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

!===== Single minus 3<->4 swap ordering
      Hbbgg_del(2,1,2) = -Hbbgg_vamps_pppm_del34(i2,i1,i4,i3,s,za,zb,
     .     musq,ipole)
!---- and conj
      Hbbgg_del(1,2,1) = -Hbbgg_vamps_pppm_del34(i2,i1,i4,i3,s,zb,za,
     .     musq,ipole)


!=====2 minus MHV
      Hbbgg_del(2,1,1) = Hbbgg_vamps_ppmm_del34(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
!=====2 minus MHV-bar
      Hbbgg_del(1,2,2) = Hbbgg_vamps_ppmm_del34(i1,i2,i3,i4,s,zb,za,
     .     musq,ipole)

      return
      end

************************************************************************

      subroutine Hbbg_realamps(i1,i2,i3,i4,s,za,zb,ampsgg,ampsQQ)
      implicit none
      integer, intent(in) :: i1,i2,i3,i4
      real(8), intent(in) :: s(5,5)
      complex(8), intent(in) :: za(5,5),zb(5,5)
      complex(8), intent(out) :: ampsgg(0:2,2,2,2),ampsQQ(1:4,2,2,2)
      integer :: icol,iint
      complex(8) :: amps(2,2),s1234
      complex(8), external :: Hbbgg_allm,Hbbgg_mmpp,Hbbgg_mmmp
      complex(8), external :: HbbQQ_mmmp,HbbQQ_mpmm
           
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

!-----icol=1, i3,i4 ordering
      icol=1
      ampsgg(icol,1,1,1) =  Hbbgg_allm(i1,i2,i3,i4,s,za,zb)
      ampsgg(icol,1,1,2) = -Hbbgg_mmmp(i1,i2,i3,i4,s,za,zb)
      ampsgg(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i3,i4,s,za,zb)
      ampsgg(icol,1,2,1) =  Hbbgg_mmmp(i2,i1,i4,i3,s,za,zb)

      ampsgg(icol,2,2,2) =  Hbbgg_allm(i1,i2,i3,i4,s,zb,za)
      ampsgg(icol,2,2,1) = -Hbbgg_mmmp(i1,i2,i3,i4,s,zb,za)
      ampsgg(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i3,i4,s,zb,za)
      ampsgg(icol,2,1,2) =  Hbbgg_mmmp(i2,i1,i4,i3,s,zb,za)
      
!-----icol=2 i4,i3 ordering
      icol=2
      ampsgg(icol,1,1,1) =  Hbbgg_allm(i1,i2,i4,i3,s,za,zb)
      ampsgg(icol,1,2,1) = -Hbbgg_mmmp(i1,i2,i4,i3,s,za,zb)
      ampsgg(icol,1,2,2) = -Hbbgg_mmpp(i1,i2,i4,i3,s,za,zb)
      ampsgg(icol,1,1,2) =  Hbbgg_mmmp(i2,i1,i3,i4,s,za,zb)

      ampsgg(icol,2,2,2) =  Hbbgg_allm(i1,i2,i4,i3,s,zb,za)
      ampsgg(icol,2,1,2) = -Hbbgg_mmmp(i1,i2,i4,i3,s,zb,za)
      ampsgg(icol,2,1,1) = -Hbbgg_mmpp(i1,i2,i4,i3,s,zb,za)
      ampsgg(icol,2,2,1) =  Hbbgg_mmmp(i2,i1,i3,i4,s,zb,za)

      icol=0
      ampsgg(icol,:,:,:) = ampsgg(1,:,:,:) + ampsgg(2,:,:,:)

!-----int =1,mmpm type diagrams , int=2, mmmp type diagrams
!-----int =3,mmpm type with 2 and 4 swapped for all diagrams
!-----int =4,mmmp type with 1 and 3 swapped for all diagrams
!-----i1,i2 i3,i4 QQ pair (i1,i2 or i3,i4 couple to Higgs) 

      iint=1
!-----Regular ordering v
      ampsQQ(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)
      ampsQQ(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      ampsQQ(iint,1,2,1) = HbbQQ_mpmm(i2,i1,i3,i4,s,zb,za)     
      ampsQQ(iint,2,2,1) = HbbQQ_mpmm(i2,i1,i3,i4,s,za,zb)
!-----These v are i2 <-> i4 swaped
      ampsQQ(iint,1,1,2) = HbbQQ_mmmp(i1,i4,i2,i3,s,zb,za)     
      ampsQQ(iint,2,1,2) = HbbQQ_mmmp(i1,i4,i2,i3,s,za,zb)
      ampsQQ(iint,1,2,2) = HbbQQ_mpmm(i4,i1,i3,i2,s,zb,za)     
      ampsQQ(iint,2,2,2) = HbbQQ_mpmm(i4,i1,i3,i2,s,za,zb)
                  
      iint = 2
!-----Regular ordering v
      ampsQQ(iint,1,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      ampsQQ(iint,2,1,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      ampsQQ(iint,1,2,1) = HbbQQ_mpmm(i1,i2,i3,i4,s,zb,za)     
      ampsQQ(iint,2,2,1) = HbbQQ_mpmm(i1,i2,i3,i4,s,za,zb)
!-----These v are i2 <-> i4 swaped
      ampsQQ(iint,1,1,2) = HbbQQ_mmmp(i1,i4,i3,i2,s,zb,za)     
      ampsQQ(iint,2,1,2) = HbbQQ_mmmp(i1,i4,i3,i2,s,za,zb)
      ampsQQ(iint,1,2,2) = HbbQQ_mmmp(i3,i2,i1,i4,s,zb,za)     
      ampsQQ(iint,2,2,2) = HbbQQ_mmmp(i3,i2,i1,i4,s,za,zb)
      
      iint = 3
!-----Regular ordering v
      ampsQQ(iint,1,1,1) = HbbQQ_mmmp(i1,i4,i2,i3,s,zb,za)
      ampsQQ(iint,2,1,1) = HbbQQ_mmmp(i1,i4,i2,i3,s,za,zb)
      ampsQQ(iint,1,2,1) = HbbQQ_mpmm(i4,i1,i3,i2,s,zb,za)     
      ampsQQ(iint,2,2,1) = HbbQQ_mpmm(i4,i1,i3,i2,s,za,zb)
!-----These v are i2 <-> i4 swaped
      ampsQQ(iint,1,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)     
      ampsQQ(iint,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      ampsQQ(iint,1,2,2) = HbbQQ_mpmm(i2,i1,i3,i4,s,zb,za)     
      ampsQQ(iint,2,2,2) = HbbQQ_mpmm(i2,i1,i3,i4,s,za,zb)
                  
      iint = 4
!-----Regular ordering v
      ampsQQ(iint,1,1,1) = HbbQQ_mmmp(i3,i2,i1,i4,s,zb,za)
      ampsQQ(iint,2,1,1) = HbbQQ_mmmp(i3,i2,i1,i4,s,za,zb)
      ampsQQ(iint,1,2,1) = HbbQQ_mpmm(i3,i2,i1,i4,s,zb,za)     
      ampsQQ(iint,2,2,1) = HbbQQ_mpmm(i3,i2,i1,i4,s,za,zb)
!-----These v are i2 <-> i4 swaped
      ampsQQ(iint,1,1,2) = HbbQQ_mmmp(i3,i4,i1,i2,s,zb,za)     
      ampsQQ(iint,2,1,2) = HbbQQ_mmmp(i3,i4,i1,i2,s,za,zb)
      ampsQQ(iint,1,2,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)     
      ampsQQ(iint,2,2,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)

      return
      end

c-----------------------------------------------------------------------

c     H -> b bbar q qbar.

c     Full one-loop matrix element for
c     H -> b(i1) qbar(i4) q(i3) bbar(i2).
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullCy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      real(8)               :: fac
      real(8)               :: as,ca,cflo,cf,tr,cn,nf
c     MCFM variables.
      real(8), parameter    :: zip=0d0
      complex(8), parameter :: czip=(0d0,0d0)
      integer               :: imemode
      integer               :: h1,h2,h3
      real(8)               :: born,facQQ
      real(8)               :: msqQQ,msqQQ_lo,msqQQ_virt,msquv_qq,msqthv
      real(8)               :: s1234,s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: ampsQQ_lo(2,2,2,2)
      complex(8)            :: ampsQQ_del1(2,2,2,2)
      complex(8)            :: HbbQQ_del1_lc(2,2)
      complex(8)            :: HbbQQ_del1_slc(2,2)
      complex(8)            :: HbbQQ_del1_nf(2,2)
      complex(8)            :: HbbQQ_del2_lc(2,2)
      complex(8)            :: HbbQQ_del2_slc(2,2)
      complex(8)            :: HbbQQ_del2_nf(2,2)
      real(8), external     :: By0g0H
c     Externals.
      real(8), external     :: Cy0g1H,Cty0g1H,Chy0g1H
      real(8), external     :: Cy0g0H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/memode/imemode

C     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn

      FullCy0g1H = fac*(
     .     + Cy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     - 1d0/cn**2*Cty0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + nf/cn*Chy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     )

      return

c     Cross check against MCFM amplitudes.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate prefactor.
      nf = 2d0*tr
      facQQ = (4d0*pi*as)**2*2d0*cf*born/s1234

      ampsQQ_lo(:,:,:,:)=czip
!---- non-identical quarks
!---- tree-level 4-quark amplitudes
      call hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,ampsQQ_lo)
      
      call HbbQQ_vamps_fill(i1,i2,i3,i4,s,za,zb,renscale2,ipole,
     &     HbbQQ_del1_lc,HbbQQ_del1_slc,HbbQQ_del1_nf,
     &     HbbQQ_del2_lc,HbbQQ_del2_slc,HbbQQ_del2_nf)
      
!---- build total color 
      ampsQQ_del1(:,:,:,:)=czip

      msqQQ_virt=zip
      msqQQ_lo=zip
      do h1=1,2
         do h2=1,2
            if(h2==1) then
               h3=2
            else
               h3=1
            endif
            ampsQQ_del1(h1,h1,h2,h3)=HbbQQ_del1_lc(h1,h2)
     &           +HbbQQ_del1_slc(h1,h2)/cn**2
     &           +1d0/2d0*HbbQQ_del1_nf(h1,h2)*nf/cn
            
            msqQQ_virt=msqQQ_virt+
     &           2d0*real(conjg(ampsQQ_lo(h1,h1,h2,h3))
     .           *ampsQQ_del1(h1,h1,h2,h3))
            msqQQ_lo= msqQQ_lo+
     &           real(conjg(ampsQQ_lo(h1,h1,h2,h3))
     .           *ampsQQ_lo(h1,h1,h2,h3))
         enddo
      enddo
      msqQQ_virt = msqQQ_virt/4d0
      msqQQ_lo   = msqQQ_lo/4d0

      msqQQ_virt = msqQQ_virt*facQQ*(as/2d0/pi)*cn
      msqQQ_lo = facQQ*msqQQ_lo

!-----UV ren
      msquv_qq = 0d0
      select case(ipole)
      case(-1)
         msquv_qq = -(11d0*cn/3d0 - 2d0*nf/3d0)
         msquv_qq = msquv_qq - 3d0*cf
      case(0)
         msquv_qq = cn/3d0
         msquv_qq = msquv_qq - cf
      end select
      msquv_qq = msquv_qq*msqQQ_lo*(as/2d0/pi)*2d0

!-----tHV ren
      msqthv = 0d0
      if (ipole.eq.0)then
         msqthv = 4d0*1d0/2d0*cf*msqQQ_lo*(as/2d0/pi)*2d0
      endif
      
      msqQQ = msqQQ_virt+msquv_qq-msqthv

      print *, ipole,": ", FullCy0g1H/msqQQ
      FullCy0g1H = msqQQ

      return
      end

************************************************************************

      real(8) function Cy0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Local variables.
      integer               :: icol,h1,h2,h3,h4,imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2,2)
      complex(8)            :: amps_virt(2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: HbbQQ_mmmp
      complex(8), external  :: Hbbqq_vamps_ppmp_del1_lc
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate tree-level amplitudes.
      amps_lo(:,:,:,:) = czip
      amps_lo(1,1,1,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      amps_lo(2,2,2,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amps_lo(1,1,2,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amps_lo(2,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)

c     Calculate one-loop amplitudes.
      amps_virt(:,:)  = czip
c     LC del1.
      amps_virt(2,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      amps_virt(1,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      amps_virt(2,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      amps_virt(1,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     Calculate Born-one-loop interference and matrix element squared.
      tree = 0d0
      virt = 0d0
      do h1=1,2
         do h2=1,2
            if (h2==1)then
               h3=2
            else
               h3=1
            endif
            virt = virt
     .           + 2d0*real(
     .           conjg(amps_lo(h1,h1,h2,h3))*amps_virt(h1,h2)
     .           )
            tree = tree
     .           + real(
     .           conjg(amps_lo(h1,h1,h2,h3))*amps_lo(h1,h1,h2,h3)
     .           )
          enddo
      enddo
      virt = virt/4d0
      tree = tree/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
         renuv =
     .        - 11d0/3d0
     .        - 3d0/2d0
      case(0)
         renuv =
     .        + 1d0/3d0
     .        - 1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 2d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = 1d0

c     Final result.
      virt   = virt + renuv*tree + ren*tree - renthv*tree
      virt   = virt/s1234
      Cy0g1H = virt*born

      return

c     Cross check of pole parts against Catani's formula.
      dls13 = log(muSq/s(i1,i3))
      dls24 = log(muSq/s(i2,i4))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = -2d0
      case(-1)
         tmp = - 3d0 - dls13 - dls24
      case(0)
         tmp =
     .        - 3d0/2d0*dls13
     .        - 3d0/2d0*dls24
     .        - 1d0/2d0*dls13**2
     .        - 1d0/2d0*dls24**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0) print *,"Cy0g1H   ",ipole,Cy0g1H,tmp,By2g1H/tmp
      Cy0g1H = tmp

      return
      end

************************************************************************

      real(8) function Cty0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Local variables.
      integer               :: icol,h1,h2,h3,h4,imemode,ischeme
      real(8)               :: s1234
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2,2)
      complex(8)            :: amps_virt(2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: HbbQQ_mmmp
      complex(8), external  :: Hbbqq_vamps_ppmp_del1_slc
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate tree-level amplitudes.
      amps_lo(:,:,:,:) = czip
      amps_lo(1,1,1,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      amps_lo(2,2,2,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amps_lo(1,1,2,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amps_lo(2,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)

c     Calculate one-loop amplitudes.
      amps_virt(:,:)  = czip
c     SLC del1.
      amps_virt(2,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      amps_virt(1,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      amps_virt(2,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      amps_virt(1,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     Calculate Born-one-loop interference and matrix element squared.
      tree = 0d0
      virt = 0d0
      do h1=1,2
         do h2=1,2
            if (h2==1)then
               h3=2
            else
               h3=1
            endif
            virt = virt
     .           + 2d0*real(
     .           conjg(amps_lo(h1,h1,h2,h3))*amps_virt(h1,h2)
     .           )
            tree = tree
     .           + real(
     .           conjg(amps_lo(h1,h1,h2,h3))*amps_lo(h1,h1,h2,h3)
     .           )
          enddo
      enddo
      virt = virt/4d0
      tree = tree/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
         renuv =
     .        + 3d0/2d0
      case(0)
         renuv =
     .        + 1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 2d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = -1d0

c     Final result.
      virt    = virt + renuv*tree + ren*tree - renthv*tree
      virt    = -virt/s1234
      Cty0g1H = virt*born

      return

c     Cross check of pole parts against Catani's formula.
      dls12 = log(muSq/s(i1,i2))
      dls13 = log(muSq/s(i1,i3))
      dls14 = log(muSq/s(i1,i4))
      dls23 = log(muSq/s(i2,i3))
      dls24 = log(muSq/s(i2,i4))
      dls34 = log(muSq/s(i3,i4))
      tmp = 0d0
      select case(ipole)
      case(-2)
         tmp = -2d0
      case(-1)
         tmp = - 3d0
     .        - dls12
     .        - 2d0*dls13
     .        + 2d0*dls14
     .        + 2d0*dls23
     .        - 2d0*dls24
     .        - dls34
      case(0)
         tmp =
     .        - 3d0/2d0*dls12
     .        - 3*dls13
     .        + 3*dls14
     .        + 3*dls23
     .        - 3*dls24
     .        - 3d0/2d0*dls34
     .        - 1d0/2d0*dls12**2
     .        - dls13**2
     .        + dls14**2
     .        + dls23**2
     .        - dls24**2
     .        - 1d0/2d0*dls34**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
C      if (ipole.ne.0) print *,"Cty0g1H  ",ipole,Cty0g1H,tmp,Cty0g1H/tmp
      Cty0g1H = tmp

      return
      end

************************************************************************

      real(8) function Chy0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
      complex(8), parameter :: czip=(0d0,0d0)
c     Local variables.
      integer               :: icol,h1,h2,h3,h4,imemode
      real(8)               :: s1234
      real(8)               :: born,tree,virt,renuv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: amps_lo(2,2,2,2)
      complex(8)            :: amps_virt(2,2)
c     Externals.
      real(8), external     :: By0g0H
      complex(8), external  :: HbbQQ_mmmp
      complex(8), external  :: Hbbqq_vamps_ppmp_del1_nf
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate tree-level amplitudes.
      amps_lo(:,:,:,:) = czip
      amps_lo(1,1,1,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      amps_lo(2,2,2,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amps_lo(1,1,2,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amps_lo(2,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)

c     Calculate one-loop amplitudes.
      amps_virt(:,:)  = czip
c     NF del1.
      amps_virt(2,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      amps_virt(1,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      amps_virt(2,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      amps_virt(1,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     Calculate Born-one-loop interference and matrix element squared.
      tree = 0d0
      virt = 0d0
      do h1=1,2
         do h2=1,2
            if (h2==1)then
               h3=2
            else
               h3=1
            endif
            virt = virt
     .           + 2d0*real(
     .           conjg(amps_lo(h1,h1,h2,h3))*0.5d0*amps_virt(h1,h2)
     .           )
            tree = tree
     .           + real(
     .           conjg(amps_lo(h1,h1,h2,h3))*amps_lo(h1,h1,h2,h3)
     .           )
          enddo
      enddo
      virt = virt/4d0
      tree = tree/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case(-1)
         renuv = 2d0/3d0
      end select

c     Final result.
      virt    = virt + renuv*tree
      virt    = virt/s1234
      if (ipole.eq.-1) virt = 0d0
      Chy0g1H = virt*born

      return

c     Cross check of pole parts against Catani's formula.
      tmp = 0d0
C      if (ipole.ne.0) print *,"Chy0g1H  ",ipole,Chy0g1H,tmp,Chy0g1H/tmp
      Chy0g1H = tmp

      return
      end

c-----------------------------------------------------------------------

c     Helicity amplitudes for HbbQQb (Higgs couples to bb not QQb)
c     Adapted from Ciaran Williams.
      complex(8) function HbbQQ_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: zab2
      complex(8)             :: BOXI4(4),boxc(4),tric(1)
      complex(8)             :: Atree,Vpole,Boxes,Bubs,Triags,Rat
c     External.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,I3m,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Boxes = czip
      Bubs  = czip
      Rat   = czip
      Atree = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case (ipole)
      case(-2)
         Vpole = -2d0
      case(-1)
         Vpole =
     .        + 13d0/6d0
     .        - lnrat(musq,-s(i1,i4))
     .        - lnrat(musq,-s(i2,i3))
      case(0)
         Vpole =
     .        (-3d0*lnrat(musq,-s(i1,i4))**2
     .        - 3d0*lnrat(musq,-s(i2,i3))**2
     .        + 13d0*lnrat(musq,-s(i3,i4)))/6d0
     .        + 13d0/3d0
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1) = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(2) = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))
         BoxI4(3) = Lsm1_2mht(s(i1,i4),t(i2,i3,i4),s(i2,i3),s1234)      
         BoxI4(4) = Lsm1_2mht(s(i2,i3),t(i1,i3,i4),s(i1,i4),s1234)      

         boxc(1) = -((za(i2,i3)**2*zab2(i4,i2,i3,i1)**2)
     .        /(t(i2,i3,i4)*za(i2,i4)**2*za(i3,i4)*zab2(i2,i3,i4,i1))
     .        - (s1234*zb(i4,i2)**2)
     .        /(t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3)))

         boxc(2) = -(zab2(i3,i1,i4,i2)**2
     .        /(t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2)))
     .        + (s1234*zb(i4,i1)**2)
     .        /(t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(3) = -(zab2(i3,i2,i4,i1)**2
     .        /(t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1)))
     .        + (s1234*zb(i4,i2)**2)
     .        /(t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(4) = -(zab2(i3,i1,i4,i2)**2
     .        /(t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2)))
     .        + (s1234*zb(i4,i1)**2)
     .        /(t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

c     Sign flip (written in del_2 notation).
         Boxes = czip
         do i=1,4
            Boxes = Boxes + boxc(i)*boxI4(i)
         enddo

         Bubs = -(lnrat(-s(i3,i4),-t(i2,i3,i4))*zab2(i3,i2,i4,i1))
     .        /(2.*t(i2,i3,i4)*za(i2,i4))
     .        - (L1(-s(i3,i4),-t(i2,i3,i4))*za(i2,i3)**2*zb(i2,i1)
     .        *zb(i3,i2))/(2.*t(i2,i3,i4)**2*za(i2,i4))
     .        - (2*L0(-s(i3,i4),-t(i1,i3,i4))*zab2(i3,i1,i4,i2)
     .        *zb(i4,i1))/t(i1,i3,i4)**2
     .        + (L1(-s(i3,i4),-t(i1,i3,i4))*za(i3,i4)*zab2(i1,i3,i4,i2)
     .        *zb(i4,i1)**2)/(2.*t(i1,i3,i4)**3)
     .        - (L0(-s(i2,i3),-t(i2,i3,i4))*za(i2,i3)*zab2(i4,i2,i3,i1)
     .        *zb(i4,i2))/(t(i2,i3,i4)**2*za(i2,i4))
     .        - (3*L0(-s(i3,i4),-t(i2,i3,i4))*za(i2,i3)
     .        *zab2(i4,i2,i3,i1)*zb(i4,i2))
     .        /(2.*t(i2,i3,i4)**2*za(i2,i4))

         Rat = (za(i2,i3)*zb(i2,i1))/(2.*t(i2,i3,i4)*za(i2,i4))
     .        + (5*za(i1,i3)*zb(i2,i1)*zb(i4,i1))
     .        /(18.*t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .        + (zab2(i1,i3,i4,i2)*zb(i4,i1)**2)
     .        /(2.*t(i1,i3,i4)**2*zb(i4,i3))
     .        - (5*za(i2,i3)*zb(i2,i1)*zb(i4,i2))
     .        /(18.*t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))
     .        + (5*zb(i4,i1)*zb(i4,i2))/(18.*t(i1,i3,i4)*zb(i4,i3))
     .        + (7*zb(i4,i1)*zb(i4,i2))/(9.*t(i2,i3,i4)*zb(i4,i3))
      endif

      HbbQQ_vamps_ppmp_del1_lc = - Vpole + Boxes - Bubs - Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del1_lc"
C      print *, "ipole =",ipole
C      print *, "Vpole =",Vpole
C      print *, "Boxes =",Boxes
C      print *, "Bubs  =",Bubs
C      print *, "Rat   =",Rat

      return
      end

************************************************************************

      complex(8) function HbbQQ_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: BOXI4(10),boxc(10),tric(1)
      complex(8)             :: gap,gam,mp12
      complex(8)             :: zab2
      complex(8)             :: Atree,Vpole,Boxes,Triags,Bubs,Rat
c     External.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,L0,L1,I3m

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole  = czip
      Boxes  = czip
      Triags = czip
      Bubs   = czip
      Rat    = czip
      Atree  = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case(ipole)
      case(-2)
         Vpole = 2d0
      case(-1)
         Vpole =
     .        + 1.5d0
     .        + lnrat(musq,-s(i1,i2))
     .        - 2d0*lnrat(musq,-s(i1,i3))
     .        + 2d0*lnrat(musq,-s(i1,i4))
     .        + 2d0*lnrat(musq,-s(i2,i3))
     .        - 2d0*lnrat(musq,-s(i2,i4))
     .        + lnrat(musq,-s(i3,i4))
      case(0)
         Vpole = (
     .        + 6d0
     .        + lnrat(musq,-s(i1,i2))**2
     .        - 2d0*lnrat(musq,-s(i1,i3))**2
     .        + 2d0*lnrat(musq,-s(i1,i4))**2
     .        + 2d0*lnrat(musq,-s(i2,i3))**2
     .        - 2d0*lnrat(musq,-s(i2,i4))**2
     .        + 3d0*lnrat(musq,-s(i3,i4))
     .        + lnrat(musq,-s(i3,i4))**2
     .        )/2d0
      end select
      Vpole = Vpole*Atree
      
      if (ipole.eq.0)then
         BoxI4(1)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(2)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i4),-t(i2,i3,i4))
         BoxI4(3)  = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(4)  = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         BoxI4(5)  = Lsm1_2mht(s(i1,i2),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(6)  = Lsm1_2mht(s(i1,i2),t(i1,i3,i4),s(i3,i4),s1234)

         BoxI4(7)  = Lsm1_2mht(s(i1,i3),t(i2,i3,i4),s(i2,i4),s1234)
         BoxI4(8)  = Lsm1_2mht(s(i2,i4),t(i1,i3,i4),s(i1,i3),s1234)

         BoxI4(9)  = Lsm1_2mht(s(i1,i4),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(10) = Lsm1_2mht(s(i2,i3),t(i1,i3,i4),s(i1,i4),s1234)

c     Ones which we can get from LC.
         boxc(1) = -((za(i2,i3)**2*zab2(i4,i2,i3,i1)**2)
     .        /(t(i2,i3,i4)*za(i2,i4)**2*za(i3,i4)*zab2(i2,i3,i4,i1))
     .        - (s1234*zb(i4,i2)**2)
     .        /(t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3)))
         boxc(1)=-2d0*boxc(1)
         boxc(4)=   -(zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))) + 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))
         boxc(4)=-2d0*boxc(4)
         boxc(9)=-(zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))) + 
     -        (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))
         boxc(9)=-2d0*boxc(9)
         boxc(10)=-(zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))) + 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))
         boxc(10)=-2d0*boxc(10)

c     The rest.
         boxc(2) = (-2*zab2(i3,i2,i4,i1)**2)/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1)) + 
     -        (2*s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))
         boxc(3) = (-2*za(i1,i3)**2*zab2(i4,i1,i3,i2)**2)/
     -        (t(i1,i3,i4)*za(i1,i4)**2*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)) + 
     -        (2*s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(5) = zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1)) - 
     -        (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))
         boxc(6) = zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2)) - 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(7) = (-2*zab2(i3,i2,i4,i1)**2)/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1)) + 
     -        (2*s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))
         boxc(8) = (-2*zab2(i3,i1,i4,i2)**2)/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))
     -        + (2*s1234*zb(i4,i1)**2)
     .        /(t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         Boxes = czip
         do i=1,10
            Boxes = Boxes + boxc(i)*boxI4(i)
         enddo

         mp12 = s(i1,i3)/2d0+s(i1,i4)/2d0+s(i2,i3)/2d0+s(i2,i4)/2d0
         gap  = -mp12+sqrt(mp12**2-s(i1,i2)*s(i3,i4))
         gam  = -mp12-sqrt(mp12**2-s(i1,i2)*s(i3,i4))

         tric(1) = -((zb(i2,i1)**2*(gam*gap*za(i1,i3)*
     -        (gam*gap*za(i2,i3)*(gam + gap - 2*za(i3,i4)*zb(i4,i3)) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i1)*
     -        (-2*gam*gap + (gam + gap)*za(i3,i4)*zb(i4,i3))) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i2)*
     -        (gam*gap*za(i2,i3)*
     -        (2*gam*gap - (gam + gap)*za(i3,i4)*zb(i4,i3)) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i1)*
     -        (-(gam*gap*(gam + gap)) + 
     -        (gam**2 + gap**2)*za(i3,i4)*zb(i4,i3)))))/
     -        (gam**2*gap**2*za(i3,i4)*zab2(i1,i3,i4,i2)
     .        *zab2(i2,i3,i4,i1)))
         Triags = tric(1)*I3m(s(i1,i2),s(i3,i4),s1234)

c     Completed bubbles.
         Bubs = -((lnrat(-s(i3,i4),-t(i1,i3,i4))*zab2(i3,i1,i4,i2))/
     -        (t(i1,i3,i4)*za(i1,i4))) - 
     -        (2*L0(-s(i1,i3),-t(i1,i3,i4))*za(i1,i3)*
     -        zab2(i4,i1,i3,i2)*zb(i4,i1))/
     -        (t(i1,i3,i4)**2*za(i1,i4)) - 
     -        (L0(-s(i3,i4),-t(i1,i3,i4))*
     -        ((-3*za(i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i1))/
     -        (t(i1,i3,i4)*za(i1,i4)) - 
     -        (2*zab2(i3,i1,i4,i2)*zb(i4,i1))/t(i1,i3,i4)))/
     -        t(i1,i3,i4) - (L1(-s(i3,i4),-t(i1,i3,i4))*
     -        (-((za(i1,i3)**2*zb(i2,i1)*zb(i3,i1))/
     -        za(i1,i4)) + 
     -        (za(i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i1)**2)/
     -        (2.*t(i1,i3,i4))))/t(i1,i3,i4)**2 + 
     -        (2*L0(-s(i2,i3),-t(i2,i3,i4))*za(i2,i3)*
     -        zab2(i4,i2,i3,i1)*zb(i4,i2))/
     -        (t(i2,i3,i4)**2*za(i2,i4)) + 
     -        (L1(-s(i3,i4),-t(i2,i3,i4))*za(i3,i4)*
     -        zab2(i2,i3,i4,i1)*zb(i4,i2)**2)/
     -        (2.*t(i2,i3,i4)**3) + 
     -        (L0(-s(i3,i4),-t(i2,i3,i4))*
     -        (-((zab2(i3,i2,i4,i1)*zb(i4,i2))/t(i2,i3,i4)) + 
     -        (2*za(i2,i3)*zab2(i4,i2,i3,i1)*zb(i4,i2))/
     -        (t(i2,i3,i4)*za(i2,i4))))/t(i2,i3,i4)

c     Rational.
         Rat = -(za(i1,i3)*zb(i2,i1))/(2.*t(i1,i3,i4)*za(i1,i4)) - 
     -        (za(i1,i3)**2*zb(i2,i1)*zb(i3,i1))/
     -        (2.*t(i1,i3,i4)**2*za(i1,i4)) + 
     -        (za(i3,i4)*zb(i4,i1)*zb(i4,i2))/(2.*t(i1,i3,i4)**2) + 
     -        (za(i1,i3)*zb(i2,i1)*zb(i4,i1))/
     -        (2.*t(i1,i3,i4)*za(i3,i4)*zb(i4,i3)) - 
     -        (za(i2,i3)*zb(i2,i1)*zb(i4,i2))/
     -        (2.*t(i2,i3,i4)*za(i3,i4)*zb(i4,i3)) + 
     -        (zb(i4,i1)*zb(i4,i2))/(t(i1,i3,i4)*zb(i4,i3)) + 
     -        (zb(i4,i1)*zb(i4,i2))/(2.*t(i2,i3,i4)*zb(i4,i3)) + 
     -        (za(i2,i3)*zb(i3,i1)*zb(i4,i2)**2)/
     -        (2.*t(i2,i3,i4)**2*zb(i4,i3)) + 
     -        (za(i2,i4)*zb(i4,i1)*zb(i4,i2)**2)/
     -        (2.*t(i2,i3,i4)**2*zb(i4,i3)) - 
     -        (za(i1,i3)*za(i3,i4)*zb(i2,i1)*zb(i4,i3))/
     -        (2.*t(i1,i3,i4)**2*za(i1,i4))
      endif

      HbbQQ_vamps_ppmp_del1_slc = - Vpole + Boxes - Triags - Bubs - Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del1_slc"
C      print *, "ipole  =",ipole
C      print *, "Vpole  =",Vpole
C      print *, "Boxes  =",Boxes
C      print *, "Triags =",Triags
C      print *, "Bubs   =",Bubs
C      print *, "Rat    =",Rat

      return
      end

************************************************************************

      complex(8) function HbbQQ_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      real(8)                :: t,s1234
      complex(8)             :: zab2
      complex(8)             :: Atree,Vpole,Rat
c     Externals.
      complex(8), external   :: lnrat

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4) = za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Rat   = czip
      Atree = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case(ipole)
      case(-1)
         Vpole = -4d0/3d0
      case(0)
         Vpole = -4d0/3d0*(2d0 + lnrat(musq,-s(i3,i4)))
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0) Rat = 4d0*Atree/9d0

      HbbQQ_vamps_ppmp_del1_nf = - Vpole - Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del1_nf"
C      print *, "ipole  =",ipole
C      print *, "Vpole  =",Vpole
C      print *, "Rat    =",Rat

      return
      end

************************************************************************

      complex(8) function HbbQQ_vamps_ppmp_del2_lc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: zab2
      complex(8)             :: BOXI4(4),boxc(4)
      complex(8)             :: Atree,Vpole,Boxes,Bubs,Rat
c     Externals.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,L0,L1

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Boxes = czip
      Bubs  = czip
      Rat   = czip
      Atree = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case(ipole)
      case(-2)
         Vpole = -2d0
      case(-1)
         Vpole =
     .        + 13d0/6d0 - lnrat(musq,-s(i1,i3)) - lnrat(musq,-s(i2,i4))
      case(0)
         Vpole = (
     .        + 26d0
     .        - 3d0*lnrat(musq,-s(i1,i3))**2
     .        - 3d0*lnrat(musq,-s(i2,i4))**2
     .        + 13d0*lnrat(musq,-s(i3,i4))
     .        )/6d0
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0)then
         BoxI4(1)=Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i4),-t(i2,i3,i4))
         BoxI4(2)=Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(3)=Lsm1_2mht(s(i1,i3),t(i2,i3,i4),s(i2,i4),s1234)      
         BoxI4(4)=Lsm1_2mht(s(i2,i4),t(i1,i3,i4),s(i1,i3),s1234)      

         boxc(1)=  zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))
     -        - (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(2)= (za(i1,i3)**2*zab2(i4,i1,i3,i2)**2)/
     -        (t(i1,i3,i4)*za(i1,i4)**2*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)) - 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(3)=zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))
     -        - (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(4)= zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))
     -        - (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         Boxes = czip
         do i=1,4
            Boxes = Boxes+boxc(i)*boxI4(i)
         enddo

         Bubs = (lnrat(-s(i3,i4),-t(i1,i3,i4))*zab2(i3,i1,i4,i2))/
     -        (2.*t(i1,i3,i4)*za(i1,i4)) - 
     -        (L1(-s(i3,i4),-t(i1,i3,i4))*za(i1,i3)**2*zb(i2,i1)
     .        *zb(i3,i1))/(2.*t(i1,i3,i4)**2*za(i1,i4))
     .        + (L0(-s(i1,i3),-t(i1,i3,i4))*za(i1,i3)*zab2(i4,i1,i3,i2)
     .        *zb(i4,i1))/(t(i1,i3,i4)**2*za(i1,i4))
     .        + (3*L0(-s(i3,i4),-t(i1,i3,i4))*za(i1,i3)
     .        *zab2(i4,i1,i3,i2)*zb(i4,i1))
     .        /(2.*t(i1,i3,i4)**2*za(i1,i4))
     .        - (L1(-s(i3,i4),-t(i2,i3,i4))*(2*za(i2,i3)
     .        *zb(i2,i1)*zb(i4,i2)
     .        - (3*za(i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i2)**2)
     .        /(2.*t(i2,i3,i4))))/t(i2,i3,i4)**2

         Rat = -(za(i1,i3)*zb(i2,i1))/(2.*t(i1,i3,i4)*za(i1,i4)) - 
     -        (2*za(i2,i3)*zb(i2,i1)*zb(i4,i2))/t(i2,i3,i4)**2 + 
     -        (2*za(i3,i4)*zb(i4,i1)*zb(i4,i2))/t(i2,i3,i4)**2 + 
     -        (5*za(i1,i3)*zb(i2,i1)*zb(i4,i1))/
     -        (18.*t(i1,i3,i4)*za(i3,i4)*zb(i4,i3)) - 
     -        (5*za(i2,i3)*zb(i2,i1)*zb(i4,i2))/
     -        (18.*t(i2,i3,i4)*za(i3,i4)*zb(i4,i3)) + 
     -        (7*zb(i4,i1)*zb(i4,i2))/(9.*t(i1,i3,i4)*zb(i4,i3)) + 
     -        (5*zb(i4,i1)*zb(i4,i2))/(18.*t(i2,i3,i4)*zb(i4,i3)) + 
     -        (za(i2,i3)*zb(i3,i1)*zb(i4,i2)**2)/
     -        (2.*t(i2,i3,i4)**2*zb(i4,i3)) + 
     -        (za(i2,i4)*zb(i4,i1)*zb(i4,i2)**2)
     .        /(2.*t(i2,i3,i4)**2*zb(i4,i3))
      endif

      HbbQQ_vamps_ppmp_del2_lc = Vpole + Boxes - Bubs + Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del2_lc"
C      print *, "ipole  =",ipole
C      print *, "Vpole  =",Vpole
C      print *, "Boxes  =",Boxes
C      print *, "Bubs   =",Bubs
C      print *, "Rat    =",Rat

      return
      end

************************************************************************

      complex(8) function HbbQQ_vamps_ppmp_del2_slc(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      integer                :: i
      real(8)                :: t,s1234
      complex(8)             :: BOXI4(10),boxc(10),tric(1)
      complex(8)             :: gap,gam,mp12,zab2
      complex(8)             :: Atree,Vpole,Boxes,Bubs,Triags,Rat
c     Externals.
      complex(8), external   :: lnrat,Lsm1,Lsm1_2mht,L0,L1,I3m

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole  = czip
      Boxes  = czip
      Bubs   = czip
      Triags = czip
      Rat    = czip
      Atree  = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case(ipole)
      case(-2)
         Vpole = -2d0
      case(-1)
         Vpole =
     .        - 1.5d0
     .        - lnrat(musq,-s(i1,i2))
     .        + lnrat(musq,-s(i1,i3))
     .        - lnrat(musq,-s(i1,i4))
     .        - lnrat(musq,-s(i2,i3))
     .        + lnrat(musq,-s(i2,i4))
     .        - lnrat(musq,-s(i3,i4))
      case(0)
         Vpole = (
     .        - 6d0
     .        - lnrat(musq,-s(i1,i2))**2
     .        + lnrat(musq,-s(i1,i3))**2
     .        - lnrat(musq,-s(i1,i4))**2
     .        - lnrat(musq,-s(i2,i3))**2
     .        + lnrat(musq,-s(i2,i4))**2
     .        - 3d0*lnrat(musq,-s(i3,i4))
     .        - lnrat(musq,-s(i3,i4))**2
     .        )/2d0
      end select
      Vpole = Vpole*Atree
      
      if (ipole.eq.0)then
         BoxI4(1)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i3),-t(i2,i3,i4))
         BoxI4(2)  = Lsm1(-s(i3,i4),-t(i2,i3,i4),-s(i2,i4),-t(i2,i3,i4))
         BoxI4(3)  = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i3),-t(i1,i3,i4))
         BoxI4(4)  = Lsm1(-s(i3,i4),-t(i1,i3,i4),-s(i1,i4),-t(i1,i3,i4))

         BoxI4(5)  = Lsm1_2mht(s(i1,i2),t(i2,i3,i4),s(i3,i4),s1234)
         BoxI4(6)  = Lsm1_2mht(s(i1,i2),t(i1,i3,i4),s(i3,i4),s1234)

         BoxI4(7)  = Lsm1_2mht(s(i1,i3),t(i2,i3,i4),s(i2,i4),s1234)
         BoxI4(8)  = Lsm1_2mht(s(i2,i4),t(i1,i3,i4),s(i1,i3),s1234)

         BoxI4(9)  = Lsm1_2mht(s(i1,i4),t(i2,i3,i4),s(i2,i3),s1234)
         BoxI4(10) = Lsm1_2mht(s(i2,i3),t(i1,i3,i4),s(i1,i4),s1234)

         boxc(1)=-((za(i2,i3)**2*zab2(i4,i2,i3,i1)**2)/
     -        (t(i2,i3,i4)*za(i2,i4)**2*za(i3,i4)*
     -        zab2(i2,i3,i4,i1))) + 
     -        (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(2)=  zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))
     -        - (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(3)= (za(i1,i3)**2*zab2(i4,i1,i3,i2)**2)/
     -        (t(i1,i3,i4)*za(i1,i4)**2*za(i3,i4)*
     -        zab2(i1,i3,i4,i2)) - 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(4)=    -(zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*
     -        zab2(i1,i3,i4,i2))) + 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(5)=  -(zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))) + 
     -        (s1234*zb(i4,i2)**2)
     .        /(t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(6)= -(zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))) + 
     -        (s1234*zb(i4,i1)**2)
     .        /(t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(7)= zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*zab2(i2,i3,i4,i1))
     -        - (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(8)= zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*zab2(i1,i3,i4,i2))
     -        - (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         boxc(9)= -(zab2(i3,i2,i4,i1)**2/
     -        (t(i2,i3,i4)*za(i3,i4)*
     -        zab2(i2,i3,i4,i1))) + 
     -        (s1234*zb(i4,i2)**2)/
     -        (t(i2,i3,i4)*zab2(i1,i3,i4,i2)*zb(i4,i3))

         boxc(10)=  -(zab2(i3,i1,i4,i2)**2/
     -        (t(i1,i3,i4)*za(i3,i4)*
     -        zab2(i1,i3,i4,i2))) + 
     -        (s1234*zb(i4,i1)**2)/
     -        (t(i1,i3,i4)*zab2(i2,i3,i4,i1)*zb(i4,i3))

         Boxes = czip
         do i=1,10
             Boxes = Boxes+boxc(i)*boxI4(i)
         enddo

         mp12=s(i1,i3)/2d0+s(i1,i4)/2d0+s(i2,i3)/2d0+s(i2,i4)/2d0
         gap=-mp12+sqrt(mp12**2-s(i1,i2)*s(i3,i4))
         gam=-mp12-sqrt(mp12**2-s(i1,i2)*s(i3,i4))

         tric(1)=  -((zb(i2,i1)**2*(gam*gap*za(i1,i3)*
     -        (gam*gap*za(i2,i3)*(gam + gap - 2*za(i3,i4)*zb(i4,i3)) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i1)*
     -        (-2*gam*gap + (gam + gap)*za(i3,i4)*zb(i4,i3))) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i2)*
     -        (gam*gap*za(i2,i3)*
     -        (2*gam*gap - (gam + gap)*za(i3,i4)*zb(i4,i3)) + 
     -        za(i1,i2)*za(i3,i4)*zb(i4,i1)*
     -        (-(gam*gap*(gam + gap)) + 
     -        (gam**2 + gap**2)*za(i3,i4)*zb(i4,i3)))))/
     -        (gam**2*gap**2*za(i3,i4)*zab2(i1,i3,i4,i2)
     .        *zab2(i2,i3,i4,i1)))
         tric(1)=-tric(1)
         triags=tric(1)*I3m(s(i1,i2),s(i3,i4),s1234)

c     Completed bubbles.
         Bubs = (lnrat(-s(i3,i4),-t(i1,i3,i4))*
     -        zab2(i3,i1,i4,i2))/
     -        (2.*t(i1,i3,i4)*za(i1,i4)) - 
     -        (L1(-s(i3,i4),-t(i1,i3,i4))*za(i1,i3)**2*
     -        zb(i2,i1)*zb(i3,i1))/
     -        (2.*t(i1,i3,i4)**2*za(i1,i4)) + 
     -        (L0(-s(i1,i3),-t(i1,i3,i4))*za(i1,i3)*
     -        zab2(i4,i1,i3,i2)*zb(i4,i1))/
     -        (t(i1,i3,i4)**2*za(i1,i4)) - 
     -        (L0(-s(i3,i4),-t(i1,i3,i4))*
     -        ((3*zab2(i3,i1,i4,i2)*zb(i4,i1))/
     -        t(i1,i3,i4) - 
     -        (3*za(i1,i3)*zab2(i4,i1,i3,i2)*
     -        zb(i4,i1))/
     -        (2.*t(i1,i3,i4)*za(i1,i4))))/
     -        t(i1,i3,i4) - 
     -        (L0(-s(i2,i3),-t(i2,i3,i4))*za(i2,i3)*
     -        zab2(i4,i2,i3,i1)*zb(i4,i2))/
     -        (t(i2,i3,i4)**2*za(i2,i4)) + 
     -        (L0(-s(i3,i4),-t(i2,i3,i4))*
     -        ((-2*zab2(i3,i2,i4,i1)*zb(i4,i2))/
     -        t(i2,i3,i4) - 
     -        (za(i2,i3)*zab2(i4,i2,i3,i1)*
     -        zb(i4,i2))/(t(i2,i3,i4)*za(i2,i4))
     -        ))/t(i2,i3,i4) + 
     -        (L1(-s(i3,i4),-t(i2,i3,i4))*
     -        (-2*za(i2,i3)*zb(i2,i1)*zb(i4,i2) + 
     -        (3*za(i3,i4)*zab2(i2,i3,i4,i1)*
     -        zb(i4,i2)**2)/(2.*t(i2,i3,i4))))/
     -        t(i2,i3,i4)**2

c     Rational.
         Rat = -(za(i1,i3)*zb(i2,i1))/(2.*t(i1,i3,i4)*za(i1,i4)) + 
     -        (3*zab2(i3,i2,i4,i1)*zb(i4,i2))/(2.*t(i2,i3,i4)**2) + 
     -        (za(i1,i3)*zb(i2,i1)*zb(i4,i1))/
     -        (2.*t(i1,i3,i4)*za(i3,i4)*zb(i4,i3)) - 
     -        (za(i2,i3)*zb(i2,i1)*zb(i4,i2))/
     -        (2.*t(i2,i3,i4)*za(i3,i4)*zb(i4,i3)) + 
     -        (zb(i4,i1)*zb(i4,i2))/(t(i1,i3,i4)*zb(i4,i3)) + 
     -        (zb(i4,i1)*zb(i4,i2))/(t(i2,i3,i4)*zb(i4,i3))
      endif

      HbbQQ_vamps_ppmp_del2_slc = - Vpole + Boxes - Triags - Bubs + Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del2_slc"
C      print *, "ipole  =",ipole
C      print *, "Vpole  =",Vpole
C      print *, "Boxes  =",Boxes
C      print *, "Triags =",Triags
C      print *, "Bubs   =",Bubs
C      print *, "Rat    =",Rat

      return
      end

************************************************************************

      complex(8) function HbbQQ_vamps_ppmp_del2_nf(i1,i2,i3,i4,s,za,zb,
     .     musq,ipole)
      implicit none
      integer, intent(in)    :: i1,i2,i3,i4,ipole
      real(8), intent(in)    :: s(5,5),musq
      complex(8), intent(in) :: za(5,5),zb(5,5)
c     Parameters.
      complex(8), parameter  :: czip=(0d0,0d0)
c     Variables.
      real(8)                :: t,s1234
      complex(8)             :: zab2
      complex(8)             :: Atree,Rat,Vpole
c     Externals.
      complex(8), external   :: lnrat

      t(i1,i2,i3) = s(i1,i2)+s(i2,i3)+s(i1,i3)
      zab2(i1,i2,i3,i4)=za(i1,i2)*zb(i2,i4)+za(i1,i3)*zb(i3,i4)
      s1234=s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

      Vpole = czip
      Rat   = czip
      Atree = (zab2(i3,i1,i4,i2)*zb(i4,i1))
     .     /(t(i1,i3,i4)*za(i3,i4)*zb(i4,i3))
     .     + (zab2(i3,i2,i4,i1)*zb(i4,i2))
     .     /(t(i2,i3,i4)*za(i3,i4)*zb(i4,i3))

      select case(ipole)
      case(-1)
         Vpole = -4d0/3d0
      case(0)
         Vpole = -4d0/3d0*(2d0 + lnrat(musq,-s(i3,i4)))
      end select
      Vpole = Vpole*Atree

      if (ipole.eq.0) Rat = 4d0*Atree/9d0
      
      HbbQQ_vamps_ppmp_del2_nf = Vpole + Rat
C      print *, ""
C      print *, "HbbQQ_vamps_ppmp_del2_nf"
C      print *, "ipole  =",ipole
C      print *, "Vpole  =",Vpole
C      print *, "Rat    =",Rat

      return
      end

c-----------------------------------------------------------------------

c     Auxiliary functions to fill amplitudes.

      subroutine HbbQQ_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbqq_del1_lc,Hbbqq_del1_slc,Hbbqq_del1_nf,
     .     Hbbqq_del2_lc,Hbbqq_del2_slc,Hbbqq_del2_nf)
      implicit none
      integer, intent(in)     :: i1,i2,i3,i4,ipole
      real(8), intent(in)     :: s(5,5),muSQ
      complex(8), intent(in)  :: za(5,5),zb(5,5)
      complex(8), intent(out) :: Hbbqq_del1_lc(2,2)
      complex(8), intent(out) :: Hbbqq_del1_slc(2,2)
      complex(8), intent(out) :: Hbbqq_del1_nf(2,2)
      complex(8), intent(out) :: Hbbqq_del2_lc(2,2)
      complex(8), intent(out) :: Hbbqq_del2_slc(2,2)
      complex(8), intent(out) :: Hbbqq_del2_nf(2,2)
c     Parameters.
      complex(8), parameter   :: czip=(0d0,0d0)
c     Externals.
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_lc
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_slc
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_nf
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_lc
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_slc
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_nf
     
      Hbbqq_del1_lc(:,:)  = czip
      Hbbqq_del1_slc(:,:) = czip
      Hbbqq_del1_nf(:,:)  = czip

      Hbbqq_del2_lc(:,:)  = czip
      Hbbqq_del2_slc(:,:) = czip
      Hbbqq_del2_nf(:,:)  = czip

c     LC del1.
      Hbbqq_del1_lc(2,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_lc(1,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_lc(2,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_lc(1,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     SLC del1.
      Hbbqq_del1_slc(2,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_slc(1,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_slc(2,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_slc(1,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,zb,za,muSq,ipole)
      
c     NF del1.
      Hbbqq_del1_nf(2,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_nf(1,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_nf(2,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_nf(1,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     LC del2
      Hbbqq_del2_lc(2,1) =
     .     Hbbqq_vamps_ppmp_del2_lc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_lc(1,2) =
     .     Hbbqq_vamps_ppmp_del2_lc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_lc(2,2) =
     .     Hbbqq_vamps_ppmp_del2_lc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_lc(1,1) =
     .     Hbbqq_vamps_ppmp_del2_lc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     SLC del2
      Hbbqq_del2_slc(2,1) =
     .     Hbbqq_vamps_ppmp_del2_slc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_slc(1,2) =
     .     Hbbqq_vamps_ppmp_del2_slc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_slc(2,2) =
     .     Hbbqq_vamps_ppmp_del2_slc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_slc(1,1) =
     .     Hbbqq_vamps_ppmp_del2_slc(i2,i1,i4,i3,s,zb,za,muSq,ipole)
       
c     NF del2
      Hbbqq_del2_nf(2,1) =
     .     Hbbqq_vamps_ppmp_del2_nf(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_nf(1,2) =
     .     Hbbqq_vamps_ppmp_del2_nf(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_nf(2,2) =
     .     Hbbqq_vamps_ppmp_del2_nf(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_nf(1,1) =
     .     Hbbqq_vamps_ppmp_del2_nf(i2,i1,i4,i3,s,zb,za,muSq,ipole)

      return 
      end

c-----------------------------------------------------------------------

c     H -> b bbar b bbar.

c     Full one-loop matrix element for
c     H -> b(i1) bbar(i4) b(i3) bbar(i2)
c     Based on calculation by Ciaran Williams as part of
c     arXiv:1904.08961.
      real(8) function FullDy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),renscale2
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      real(8)               :: fac
      real(8)               :: as,ca,cflo,cf,tr,cn,nf
c     MCFM variables.
      real(8), parameter    :: zip=0d0
      complex(8), parameter :: czip=(0d0,0d0)
      integer               :: icol,h1,h2,h3,h4,imemode
      real(8)               :: muSq,facbb
      real(8)               :: msquv_qq,msqbb,msqbb_lo,msqbb_virtc
      real(8)               :: msqbb_virtd,msqbb_virt,born,msqthv
      real(8)               :: tmp1,tmp2
      real(8)               :: s(5,5),s1234
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: Hbbbb_del1_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_nf(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_nf(1:4,2,2,2,2)
      complex(8)            :: amp4b_lo(1:4,2,2,2,2)
      complex(8)            :: amp4b_del1(1:4,2,2,2,2)
      complex(8)            :: amp4b_del2(1:4,2,2,2,2)
      complex(8)            :: amp1sq,amp2sq
c     Externals.
      real(8), external     :: By0g0H
      real(8), external     :: Cy0g1H,Cty0g1H,Chy0g1H
      real(8), external     :: Dy0g1H,Dty0g1H,Dhy0g1H
c     Common blocks.
      common/qcd/as,ca,cflo,cf,tr,cn
      common/memode/imemode

c     Prefactor.
      nf  = 2d0*tr
      fac = (as/2d0/pi)*(4d0*pi*as)**2*2d0*cf*cn

      FullDy0g1H = 1d0/4d0*fac*(
     .     + Cy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + Cy0g1H(p,i1,i2,i3,i4,renscale2,ipole)
     .     + Cy0g1H(p,i3,i4,i1,i2,renscale2,ipole)
     .     + Cy0g1H(p,i3,i2,i1,i4,renscale2,ipole)

     .     - 1d0/cn**2*(
     .     + Cty0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + Cty0g1H(p,i1,i2,i3,i4,renscale2,ipole)
     .     + Cty0g1H(p,i3,i4,i1,i2,renscale2,ipole)
     .     + Cty0g1H(p,i3,i2,i1,i4,renscale2,ipole)
     .     )

     .     + nf/cn*(
     .     + Chy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     + Chy0g1H(p,i1,i2,i3,i4,renscale2,ipole)
     .     + Chy0g1H(p,i3,i4,i1,i2,renscale2,ipole)
     .     + Chy0g1H(p,i3,i2,i1,i4,renscale2,ipole)
     .     )

     .     - 1d0/cn*Dy0g1H(p,i1,i4,i3,i2,renscale2,ipole)

     .     - 1d0/cn**3*Dty0g1H(p,i1,i4,i3,i2,renscale2,ipole)

     .     + nf/cn**2*Dhy0g1H(p,i1,i4,i3,i2,renscale2,ipole)
     .     )

      return

c     Cross check against MCFM amplitudes.
      muSq = renscale2
c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate prefactor.
      nf = 2d0*tr
      facbb = (4d0*pi*as)**2*2d0*cf*(1d0/cn)*born/s1234

c     Fill amplitudes.
      icol=1
      call hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,amp4b_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=2
      call hbbbb_ampfil(i1,i4,i3,i2,s,za,zb,amp4b_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i4,i3,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=3
      call hbbbb_ampfil(i3,i4,i1,i2,s,za,zb,amp4b_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i4,i1,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=4
      call hbbbb_ampfil(i3,i2,i1,i4,s,za,zb,amp4b_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i2,i1,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))

      amp4b_del1(:,:,:,:,:) =
     .     + Hbbbb_del1_lc(:,:,:,:,:)
     .     + (1d0/cn**2)*Hbbbb_del1_slc(:,:,:,:,:)
     .     + 0.5d0*(nf/cn)*Hbbbb_del1_nf(:,:,:,:,:)
      amp4b_del2(:,:,:,:,:) =
     .     + (1d0/cn)*Hbbbb_del2_lc(:,:,:,:,:)
     .     + (1d0/cn**3)*Hbbbb_del2_slc(:,:,:,:,:)
     .     + 0.5d0*(nf/cn**2)*Hbbbb_del2_nf(:,:,:,:,:)

      msqbb_virtc = zip
      msqbb_virtd = zip
      amp1sq     = czip
      amp2sq     = czip
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
c     C-type bit.
                  msqbb_virtc = msqbb_virtc
     .                 + real(
     .                 + amp4b_del1(1,h1,h2,h3,h4)
     .                 *conjg(amp4b_lo(1,h1,h2,h3,h4))
     .                 + amp4b_del1(3,h3,h4,h1,h2)
     .                 *conjg(amp4b_lo(3,h3,h4,h1,h2))
     .                 + amp4b_del1(2,h1,h4,h3,h2)
     .                 *conjg(amp4b_lo(2,h1,h4,h3,h2))
     .                 + amp4b_del1(4,h3,h2,h1,h4)
     .                 *conjg(amp4b_lo(4,h3,h2,h1,h4))
     .                 )

c     D-type bit.
                  msqbb_virtd = msqbb_virtd
     .                 - real(
     .                 (
     .                 + Hbbbb_del2_lc(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_lc(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_lc(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_lc(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )

     .                 - (1d0/cn**2)*real(
     .                 (
     .                 + Hbbbb_del2_slc(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_slc(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_slc(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_slc(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )

     .                 - 0.5d0*(nf/cn)*real(
     .                 (
     .                 + Hbbbb_del2_nf(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_nf(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_nf(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_nf(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )
                  
c     Tree-level amplitudes squared.
                  amp1sq = amp1sq
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 *conjg(amp4b_lo(1,h1,h2,h3,h4))
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 *conjg(amp4b_lo(3,h3,h4,h1,h2))
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 *conjg(amp4b_lo(2,h1,h4,h3,h2))
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 *conjg(amp4b_lo(4,h3,h2,h1,h4))
                  amp2sq = amp2sq
     .                 + (
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 )
     .                 + (
     .                 + amp4b_lo(1,h1,h2,h3,h4)
     .                 + amp4b_lo(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp4b_lo(2,h1,h4,h3,h2)
     .                 + amp4b_lo(4,h3,h2,h1,h4)
     .                 )
               enddo
            enddo
         enddo
      enddo
      amp1sq      = amp1sq/2d0
      amp2sq      = amp2sq/2d0
      msqbb_virtc = msqbb_virtc/2d0
      msqbb_virtd = msqbb_virtd/2d0

      msqbb_virt = 1d0/4d0*facbb*(as/2d0/pi)*cn
     .     *(cn*msqbb_virtc + msqbb_virtd)
      msqbb_lo   = 1d0/4d0*facbb*(cn*amp1sq + amp2sq)

c     UV renormalisation.
      msquv_qq = 0d0
      select case(ipole)
      case (-1)
         msquv_qq = - 11d0/3d0*cn + 2d0/3d0*nf - 3d0/2d0*cn
     .        - 3d0/2d0*cn*(-1d0/cn**2)
      case(0)
         msquv_qq = 1d0/3d0*cn - 1d0/2d0*cn - 1d0/2d0*cn*(-1d0/cn**2)
      end select
      msquv_qq = (as/2d0/pi)*msquv_qq*msqbb_lo

!-----tHV ren
      msqthv = 0d0
      if (ipole.eq.0)then
         msqthv = 4d0*1d0/2d0*cf*msqbb_lo*(as/2d0/pi)
      endif

      msqbb = msqbb_virt + msquv_qq - msqthv

      print *, ipole,": ", FullDy0g1H/msqbb
      FullDy0g1H = msqbb

      return
      end

************************************************************************

      real(8) function Dy0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(1:4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: imemode,ischeme
      integer               :: icol,h1,h2,h3,h4
      real(8)               :: s1234,born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: Hbbbb_del1_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_nf(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_nf(1:4,2,2,2,2)
      complex(8)            :: amp_lo(1:4,2,2,2,2)
c     Externals.
      real(8), external     :: By0g0H
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
      icol=1
      call hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=2
      call hbbbb_ampfil(i1,i4,i3,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i4,i3,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=3
      call hbbbb_ampfil(i3,i4,i1,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i4,i1,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=4
      call hbbbb_ampfil(i3,i2,i1,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i2,i1,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))

      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  virt = virt
     .                 - real(
     .                 (
     .                 + Hbbbb_del2_lc(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_lc(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_lc(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_lc(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )
                  
c     Tree-level amplitudes squared.
                  tree = tree
     .                 + (
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 + (
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
               enddo
            enddo
         enddo
      enddo
      tree = tree/2d0
      virt = virt/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case (-1)
         renuv = -11d0/3d0 - 3d0/2d0
      case(0)
         renuv = 1d0/3d0 - 1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 2d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = 1d0

c     Final result.
      virt   = virt + renuv*tree + ren*tree - renthv*tree
      virt   = -virt/s1234
      Dy0g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls13 = log(muSq/s(i1,i3))
      dls24 = log(muSq/s(i2,i4))
      tmp   = 0d0
      select case(ipole)
      case(-2)
         tmp = - 2d0
      case(-1)
         tmp = - 3d0 - dls13 - dls24
      case(0)
         tmp =
     .        - 3d0/2d0*dls13
     .        - 3d0/2d0*dls24
     .        - 1d0/2d0*dls13**2
     .        - 1d0/2d0*dls24**2
      end select
      tmp = (tmp - ren)*tree
      tmp = -tmp*born/s1234
      Dy0g1H = tmp

      return
      end

************************************************************************

      real(8) function Dty0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(1:4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: imemode,ischeme
      integer               :: icol,h1,h2,h3,h4
      real(8)               :: s1234,born,tree,virt,renuv,ren,renthv,tmp
      real(8)               :: dls12,dls13,dls14,dls23,dls24,dls34
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: Hbbbb_del1_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_nf(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_nf(1:4,2,2,2,2)
      complex(8)            :: amp_lo(1:4,2,2,2,2)
c     Externals.
      real(8), external     :: By0g0H
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
      icol=1
      call hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=2
      call hbbbb_ampfil(i1,i4,i3,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i4,i3,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=3
      call hbbbb_ampfil(i3,i4,i1,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i4,i1,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=4
      call hbbbb_ampfil(i3,i2,i1,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i2,i1,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))

      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  virt = virt
     .                 + real(
     .                 (
     .                 + Hbbbb_del2_slc(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_slc(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_slc(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_slc(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )
                  
                  tree = tree
     .                 + (
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 + (
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
               enddo
            enddo
         enddo
      enddo
      tree = tree/2d0
      virt = virt/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case (-1)
         renuv = -3d0/2d0
      case(0)
         renuv = -1d0/2d0
      end select

c     Scheme choice.
c     0: factor out Exp(eps*EulerGamma)/Gamma(1-eps)
c     1: include Exp(eps*EulerGamma)/Gamma(1-eps)
      ischeme = 0
      ren     = 0d0
      if (ipole.eq.0 .and. ischeme.eq.1) ren = 2d0*pi**2/12d0

c     Scheme conversion FDR -> tHV.
      renthv = 0d0
      if (ipole.eq.0) renthv = 1d0

c     Final result.
      virt    = virt + renuv*tree + ren*tree - renthv*tree
      virt    = virt/s1234
      Dty0g1H = virt*born

      return

c     Cross check against Catani's formula.
      dls12 = log(muSq/s(i1,i2))
      dls13 = log(muSq/s(i1,i3))
      dls14 = log(muSq/s(i1,i4))
      dls23 = log(muSq/s(i2,i3))
      dls24 = log(muSq/s(i2,i4))
      dls34 = log(muSq/s(i3,i4))
      tmp   = 0d0
      select case(ipole)
      case(-2)
         tmp = - 2d0
      case(-1)
         tmp =
     .        - 3d0 - dls12 - dls14 - dls23 - dls34 + dls13 + dls24
      case(0)
         tmp =
     .        - 3d0/2d0*dls12
     .        - 3d0/2d0*dls34
     .        + 3d0/2d0*dls13
     .        - 3d0/2d0*dls14
     .        - 3d0/2d0*dls23
     .        + 3d0/2d0*dls24
     .        - 1d0/2d0*dls12**2
     .        + 1d0/2d0*dls13**2
     .        - 1d0/2d0*dls14**2
     .        - 1d0/2d0*dls23**2
     .        + 1d0/2d0*dls24**2
     .        - 1d0/2d0*dls34**2
      end select
      tmp = (tmp + ren)*tree
      tmp = tmp*born/s1234
      Dty0g1H = tmp

      return
      end

************************************************************************

      real(8) function Dhy0g1H(p,i1,i4,i3,i2,muSq,ipole)
      implicit none
      integer, intent(in)   :: i1,i2,i3,i4,ipole
      real(8), intent(in)   :: p(4,5),muSq
c     Parameters.
      real(8), parameter    :: pi=3.141592653589793238d0
c     Variables.
      integer               :: imemode,ischeme
      integer               :: icol,h1,h2,h3,h4
      real(8)               :: s1234,born,tree,virt,renuv,renthv,tmp
      real(8)               :: s(5,5)
      complex(8)            :: zA(5,5),zB(5,5)
      complex(8)            :: Hbbbb_del1_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del1_nf(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_lc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_slc(1:4,2,2,2,2)
      complex(8)            :: Hbbbb_del2_nf(1:4,2,2,2,2)
      complex(8)            :: amp_lo(1:4,2,2,2,2)
c     Externals.
      real(8), external     :: By0g0H,Dy0g0H
c     Common blocks.
      common/memode/imemode

c     Fill zA, zB, and s.
      call fillSpinors(5,p,zA,zB,s)
      s1234 = s(i1,i2)+s(i1,i3)+s(i1,i4)+s(i2,i3)+s(i2,i4)+s(i3,i4)

c     Calculate Born matrix element.
      born = 1d0
      if (imemode.eq.1) born = By0g0H(s1234)

c     Fill amplitudes.
      icol=1
      call hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=2
      call hbbbb_ampfil(i1,i4,i3,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i1,i4,i3,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=3
      call hbbbb_ampfil(i3,i4,i1,i2,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i4,i1,i2,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))
      icol=4
      call hbbbb_ampfil(i3,i2,i1,i4,s,za,zb,amp_lo(icol,:,:,:,:))
      call Hbbbb_vamps_fill(i3,i2,i1,i4,s,za,zb,muSq,ipole,
     .     Hbbbb_del1_lc(icol,:,:,:,:),Hbbbb_del1_slc(icol,:,:,:,:),
     .     Hbbbb_del1_nf(icol,:,:,:,:),
     .     Hbbbb_del2_lc(icol,:,:,:,:),Hbbbb_del2_slc(icol,:,:,:,:),
     .     Hbbbb_del2_nf(icol,:,:,:,:))

      virt = 0d0
      tree = 0d0
      do h1=1,2
         do h2=1,2
            do h3=1,2
               do h4=1,2
                  virt = virt
     .                 - 0.5d0*real(
     .                 (
     .                 + Hbbbb_del2_nf(2,h1,h4,h3,h2)
     .                 + Hbbbb_del2_nf(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 +
     .                 (
     .                 + Hbbbb_del2_nf(1,h1,h2,h3,h4)
     .                 + Hbbbb_del2_nf(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
     .                 )
                  
                  tree = tree
     .                 + (
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )*conjg(
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )
     .                 + (
     .                 + amp_lo(1,h1,h2,h3,h4)
     .                 + amp_lo(3,h3,h4,h1,h2)
     .                 )*conjg(
     .                 + amp_lo(2,h1,h4,h3,h2)
     .                 + amp_lo(4,h3,h2,h1,h4)
     .                 )
               enddo
            enddo
         enddo
      enddo
      tree = tree/2d0
      virt = virt/2d0

c     UV renormalisation in FDH.
      renuv = 0d0
      select case(ipole)
      case (-1)
         renuv = 2d0/3d0
      end select

Cc     Scheme conversion FDR -> tHV.
C      renthv = 0d0
C      if (ipole.eq.0) renthv = -1d0

c     Final result.
      virt    = virt + renuv*tree
      virt    = virt/s1234
      Dhy0g1H = virt*born

      return

c     Cross check against Catani's formula.
      tmp = 0d0
      Dhy0g1H = tmp

      return
      end

c-----------------------------------------------------------------------

c     Auxiliary functions to fill amplitudes.
      
      subroutine hbbbb_ampfil(i1,i2,i3,i4,s,za,zb,amp)
      implicit none
      integer, intent(in)     :: i1,i2,i3,i4
      real(8), intent(in)     :: s(5,5)
      complex(8), intent(in)  :: za(5,5),zb(5,5)
      complex(8), intent(out) :: amp(2,2,2,2)
      complex(8), parameter   :: czip=(0d0,0d0)
      complex(8), external    :: HbbQQ_mmmp
      
      amp(:,:,:,:) = czip
      amp(1,1,1,2) = HbbQQ_mmmp(i1,i2,i3,i4,s,za,zb)
      amp(2,2,2,1) = HbbQQ_mmmp(i1,i2,i3,i4,s,zb,za)
      amp(1,1,2,1) = HbbQQ_mmmp(i1,i2,i4,i3,s,za,zb)
      amp(2,2,1,2) = HbbQQ_mmmp(i1,i2,i4,i3,s,zb,za)

      return
      end

************************************************************************

c     Hbbbb one-loop routines, Higgs couples to i1,i2 line.
c     del1 is leading piece, del2 is 1/N_c suppressed.
      subroutine Hbbbb_vamps_fill(i1,i2,i3,i4,s,za,zb,muSq,ipole,
     .     Hbbqq_del1_lc,Hbbqq_del1_slc,Hbbqq_del1_nf,
     .     Hbbqq_del2_lc,Hbbqq_del2_slc,Hbbqq_del2_nf)
      implicit none
      integer, intent(in)     :: i1,i2,i3,i4,ipole
      real(8), intent(in)     :: s(5,5),muSQ
      complex(8), intent(in)  :: za(5,5),zb(5,5)
      complex(8), intent(out) :: Hbbqq_del1_lc(2,2,2,2)
      complex(8), intent(out) :: Hbbqq_del1_slc(2,2,2,2)
      complex(8), intent(out) :: Hbbqq_del1_nf(2,2,2,2)
      complex(8), intent(out) :: Hbbqq_del2_lc(2,2,2,2)
      complex(8), intent(out) :: Hbbqq_del2_slc(2,2,2,2)
      complex(8), intent(out) :: Hbbqq_del2_nf(2,2,2,2)
c     Parameters.
      complex(8), parameter   :: czip=(0d0,0d0)
c     Externals.
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_lc
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_slc
      complex(8), external    :: HbbQQ_vamps_ppmp_del1_nf
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_lc
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_slc
      complex(8), external    :: HbbQQ_vamps_ppmp_del2_nf
      
      Hbbqq_del1_lc(:,:,:,:)  = czip
      Hbbqq_del1_slc(:,:,:,:) = czip
      Hbbqq_del1_nf(:,:,:,:)  = czip
    
      Hbbqq_del2_lc(:,:,:,:)  = czip
      Hbbqq_del2_slc(:,:,:,:) = czip
      Hbbqq_del2_nf(:,:,:,:)  = czip

c     LC del1.
      Hbbqq_del1_lc(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_lc(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_lc(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_lc(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del1_lc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     SLC del1.
      Hbbqq_del1_slc(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_slc(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_slc(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_slc(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del1_slc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     NF del1.
      Hbbqq_del1_nf(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del1_nf(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del1_nf(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del1_nf(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del1_nf(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     LC del2.
      Hbbqq_del2_lc(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del2_lc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_lc(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del2_lc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_lc(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del2_lc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_lc(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del2_lc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     SLC del2.
      Hbbqq_del2_slc(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del2_slc(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_slc(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del2_slc(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_slc(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del2_slc(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_slc(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del2_slc(i2,i1,i4,i3,s,zb,za,muSq,ipole)

c     NF del2.
      Hbbqq_del2_nf(2,2,1,2) =
     .     Hbbqq_vamps_ppmp_del2_nf(i1,i2,i3,i4,s,za,zb,muSq,ipole)
      Hbbqq_del2_nf(1,1,2,1) =
     .     Hbbqq_vamps_ppmp_del2_nf(i1,i2,i3,i4,s,zb,za,muSq,ipole)
      Hbbqq_del2_nf(2,2,2,1) =
     .     Hbbqq_vamps_ppmp_del2_nf(i2,i1,i4,i3,s,za,zb,muSq,ipole)
      Hbbqq_del2_nf(1,1,1,2) =
     .     Hbbqq_vamps_ppmp_del2_nf(i2,i1,i4,i3,s,zb,za,muSq,ipole)

      return
      end

c-----------------------------------------------------------------------
