c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Top-level cross-section subroutine.

c-----------------------------------------------------------------------

c     Top-level function to calculate cross-section.

      subroutine cross_ext(ave,sd,iproc) bind(C, name="cross_ext")
      use, intrinsic :: iso_c_binding
      implicit none
      integer, intent(in)  :: iproc
      real(8), intent(out) :: ave,sd
c     Externals.
      real(8), external    :: sig3ZQa,sig4ZQa,sig5ZQa
      real(8), external    :: sig3HBa,sig4HBa,sig5HBa
      real(8), external    :: sig3HGa,sig4HGa,sig5HGa

c     Calculate differential cross section depending on process.
      if (iproc.eq.1)then
         call calcCross(ave,sd,sig3ZQa,sig4ZQa,sig5ZQa)
      elseif (iproc.eq.21)then
         call calcCross(ave,sd,sig3HBa,sig4HBa,sig5HBa)
      elseif (iproc.eq.22)then
         call calcCross(ave,sd,sig3HGa,sig4HGa,sig5HGa)
      endif

      return
      end

c-----------------------------------------------------------------------
