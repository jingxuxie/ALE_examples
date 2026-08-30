! This file is part of the EERAD3 NNLO event generator.
! Copyright (C) 2025 the authors.
! This program is free software: you can redistribute it and/or
! modify it under the terms of the GNU General Public License as
! published by the Free Software Foundation, either version 3 of
! the License, or any later version. See COPYING for details.

module analysis_mod
  implicit none

  ! Observables
  real(8) :: obs1
  
  ! Cuts.
  real(8) :: cut

  ! Histogram IDs.
  integer :: iObs1

  ! Common blocks - do not touch!
  integer :: iaver,imom,idist,iang,idebug
  integer :: iproc,nloop,icol,njets,ichan
  common/intech/iaver,imom,idist,iang,idebug
  common/inphys/iproc,nloop,icol,njets,ichan

contains

  ! Initialise analysis.
  subroutine initanalysis()
    implicit none
    integer, external :: bookhist

    ! Read cut.
    call readparm('cut', cut, 1d-5)

    ! Book histograms.
    iObs1 = bookhist('obs1', 0d0, 1d0, 200)

    ! Print histogram information.
    call printhistdata()

  end subroutine initanalysis

  ! Observables and cuts.
  subroutine ecuts_ana(npar,var,ipass)
    implicit none
    integer, intent(in)    :: npar
    integer, intent(inout) :: ipass
    real(8), intent(inout) :: var

    ! Calculate observables.
    call getObs1(obs1,npar)

    ! Set variable for integration.
    call getvar(var)

    ! Apply cuts.
    ipass=0
    if (iaver.eq.0)then
       if (obs1.gt.cut) ipass=1
    endif

  end subroutine ecuts_ana

  ! Fill histograms.
  subroutine fillhists(wgt,npar)
    implicit none
    integer, intent(in) :: npar
    real(8), intent(in) :: wgt
    real(8)             :: var,wt

    call getvar(var)
    wt = wgt/var

    ! Fill histograms.
    if (obs1.gt.cut) call histoa(iObs1,obs1,wt)

  end subroutine fillhists

  ! Get variable for phase-space optimisation and moments.
  subroutine getvar(var)
    implicit none
    real(8), intent(out) :: var

    var = 1d0
    if (iaver.eq.0)then
       var = obs1
    endif
    var = var**imom

  end subroutine getvar

  ! Auxiliary subroutine to calculate dummy observable.
  subroutine getObs1(obs1,npar)
    implicit none
    integer, intent(in) :: npar
    real(8)             :: ppar(4,5)
    common/pcut/ppar

    ! Momenta are stored in ppar with first index labelling
    ! the momentum entries and the second index labelling
    ! the particle index.
    ! The energy is in the last entry:
    ! (px, py, pz, E) <-> (ppar(1,i), ppar(2,i), ppar(3,i), ppar(4,i)).

    ! Dummy observable.
    obs1 = 0.5d0

  end subroutine getObs1


end module analysis_mod
