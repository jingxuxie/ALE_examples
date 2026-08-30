c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Main program and cross-section subroutines.

c-----------------------------------------------------------------------

c     Main program.
      program eerad3
      implicit none
      integer           :: iproc,njets,nloop,icol,ichan
      integer           :: iwarm,iprod
      character(20)     :: fname
      character(4)      :: suffix
      character(8)      :: prefix
      real(8)           :: avgi, sd
      real(8)           :: start,finish,cputime,cpus
      integer           :: cpuh,cpum
c     Externals.
      real(8), external :: sig3ZQa,sig4ZQa,sig5ZQa
      real(8), external :: sig3HBa,sig4HBa,sig5HBa
      real(8), external :: sig3HGa,sig4HGa,sig5HGa
c     Common blocks.
      common/inphys/iproc,nloop,icol,njets,ichan
      common/ivegas/iwarm,iprod
      common/outfile/fname,prefix,suffix

c     Start time.
      call cpu_time(start)

c     Print banner.
      call printBanner()

c     Read run card and initialise.
      call init()

c     Print settings.
      call printSettings()

c     Calculate differential cross section depending on process.
      call cross(avgi,sd,iproc)

c     Print final cross section.
      if (iprod.eq.1)then
         if (ichan.eq.0)  write(6,11) avgi,sd
         if (ichan.eq.10) write(6,12) avgi,sd
         if (ichan.eq.20) write(6,13) avgi,sd
         if (ichan.eq.11) write(6,14) avgi,sd
         if (ichan.eq.12) write(6,15) avgi,sd
         if (ichan.eq.21) write(6,16) avgi,sd
         if (ichan.eq.22) write(6,17) avgi,sd
         if (ichan.eq.23) write(6,18) avgi,sd
      else
         write(6,*) ""
      endif

c     Write output files.
      if (iprod.eq.1) call outfiles()

c     Stop time.
      call cpu_time(finish)
      cputime = finish-start
      cpuh = int(cputime/3600)
      cpum = int(modulo(cputime,36d2)/60)
      cpus = modulo(modulo(cputime,36d2),6d1)
      if (cputime.lt.60)then
         write(6,20) cputime
      elseif (cputime.lt.3600)then
         write(6,21) cpum,cpus
      else
         write(6,22) cpuh,cpum,cpus
      endif
      

 11   format(/,' [LO]                  ',g14.6,' +- ',g14.6,/)
 12   format(/,' [NLO]                 ',g14.6,' +- ',g14.6,/)
 13   format(/,' [NNLO]                ',g14.6,' +- ',g14.6,/)
 14   format(/,' [V]                   ',g14.6,' +- ',g14.6,/)
 15   format(/,' [R]                   ',g14.6,' +- ',g14.6,/)
 16   format(/,' [VV]                  ',g14.6,' +- ',g14.6,/)
 17   format(/,' [RV]                  ',g14.6,' +- ',g14.6,/)
 18   format(/,' [RR]                  ',g14.6,' +- ',g14.6,/)
 20   format(/,' CPU time: ',f6.3,' s',/)
 21   format(/,' CPU time: ',i2,' m, ',f6.3,' s',/)
 22   format(/,' CPU time: ',i2,' h, ',i2,' m, ',f6.3,' s',/)

      end program

c-----------------------------------------------------------------------
