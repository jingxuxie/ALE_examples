c     This file is part of the EERAD3 NNLO event generator.
c     Copyright (C) 2025 the authors.
c     This program is free software: you can redistribute it and/or
c     modify it under the terms of the GNU General Public License as
c     published by the Free Software Foundation, either version 3 of
c     the License, or any later version. See COPYING for details.

c     Subroutines for initialisation.

c-----------------------------------------------------------------------
c     Subroutine to read input file and initialise common blocks.
c-----------------------------------------------------------------------       

      subroutine init()
      implicit real*8(a-h,o-z)
      integer, parameter :: nhisto=100
      real(8), parameter :: pi=3.141592653589793238d0
      integer            :: stat
      integer            :: iseeds(1:2,0:9999),icolmax(0:2)
      integer            :: jhist
      integer            :: itmax1tmp,itmax2tmp,nshottmp
      character(50)      :: stringhist(nhisto)
      character(2)       :: ianame(1:5)
      character(40)      :: ibname(1:5),froot
      character(10)      :: line
      character(4)       :: suffix
      character(8)       :: prefix
      character(4)       :: channel
      character(20)      :: fname
c     Common blocks.
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/tcuts/ymin,y0
      common/qcd/as,ca,cflo,cf,tr,cn
      common/masses/rm2(1:5),shat
      common/rseeds/i1,i2
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2)
      common/outfile/fname,prefix,suffix
      common/ivegas/iwarm,iprod
      common/histnew/jhist,stringhist
      include "iseeds.f"

c     Read command-line settings.
      n = iargc()
      if (n.ge.2)then 
         call getarg(1,ianame(1))
         call getarg(2,ibname(1))
         nl = 1
      endif
      if (n.ge.4)then
         call getarg(3,ianame(2))
         call getarg(4,ibname(2))
         nl = 2
      endif
      if (n.ge.6)then
         call getarg(5,ianame(3))
         call getarg(6,ibname(3))
         nl = 3
      endif
      if (n.ge.8)then
         call getarg(7,ianame(4))
         call getarg(8,ibname(4))
         nl = 4
      endif
      if (n.ge.10)then
         call getarg(9,ianame(5))
         call getarg(10,ibname(5))
         nl = 5
      endif
      iseed = 0
      froot = ''
      itmax1tmp = -1
      itmax2tmp = -1
      nshottmp  = -1
      do i=1,nl
         if (ianame(i).eq.'-i')then
            froot = ibname(i) 
            ilen  = len(froot)
         elseif (ianame(i).eq.'-s')then
            read(ibname(i),*) iseed
         elseif (ianame(i).eq.'-w')then
            read(ibname(i),*) itmax1tmp
         elseif (ianame(i).eq.'-p')then
            read(ibname(i),*) itmax2tmp
         elseif (ianame(i).eq.'-n')then
            read(ibname(i),*) nshottmp
         endif
      enddo
      if (froot.eq.'')then
         write(6,*)
         write(6,*) 'Error: no run card provided!'
         write(6,*)
         write(6,*) 'Usage:'
         write(6,*) './eerad3 -i <runcard> [options]'
         write(6,*)
         write(6,*) 'Options:'
         write(6,*) ' -s <seed>      random-number seed (0-9999)'
         write(6,*) ' -n <nshots>    number of points per iteration'
         write(6,*) ' -w <niter>     number of warmup iterations'
         write(6,*) ' -p <niter>     number of production iterations'
         write(6,*)
         stop
      endif

c     Set seeds.
      if (iseed.lt.0.or.iseed.gt.9999)then
         stop "Unknown seed provided"
      endif
      irlen = 0
      do i=1,ilen
         if (ichar(froot(i:i)).eq.32.and.irlen.eq.0)then
            irlen = i-1
         endif
      enddo
      i1 = iseeds(1,iseed)
      i2 = iseeds(2,iseed)

c     Read run card.
      call readruncard(froot, stat)

c     Propagate settings.
      iwarm = 0
      iprod = 0
      if (itmax1tmp.ge.0) itmax1 = itmax1tmp
      if (itmax2tmp.ge.0) itmax2 = itmax2tmp
      if (itmax1.gt.0) iwarm = 1
      if (itmax2.gt.0) iprod = 1
      if (nshottmp.gt.0)then
         if (nshot3.gt.0) nshot3 = nshottmp
         if (nshot4.gt.0) nshot4 = nshottmp
         if (nshot5(1).gt.0) nshot5(1) = nshottmp
         if (nshot5(2).gt.0) nshot5(2) = nshottmp/5
      endif

c     Check consistency of input parameters.
      if (iproc.ne.1 .and. iproc.ne.21 .and. iproc.ne.22)then
         stop 'Unknown process id'
      endif
      if (nshot3.lt.1)then
         if (njets.eq.3.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot3 = 0'
         endif
      endif
      if (nshot4.lt.1)then
         if (njets.eq.4.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot4 = 0'
         endif
      endif
      if (nshot5(1).lt.1.or.nshot5(2).lt.1)then
         if (njets.eq.5.and.nloop.eq.0)then
            stop 'Cannot generate events, nshot5 = 0'
         endif
      endif
      if (y0.gt.1d-4)then
         y0 = 1d-4
         write(6,*) 'Warning: y0 too large'
         write(6,'(A21,E4.1)') 'Reset to y0 = ',y0
      endif
      if (y0.lt.1d-12)then
         y0 = 1d-12
         write(6,*) 'Warning: y0 too small'
         write(6,'(A21,E4.1)') 'Reset to y0 = ',y0
      endif
      icolmax(0) = 0
      if (iproc.eq.22) icolmax(0) = 2
      icolmax(1) = 3
      if (iproc.eq.22) icolmax(1) = 4
      icolmax(2) = 6
      if (iproc.eq.22) icolmax(2) = 7
      nord = njets+abs(nloop)-3
      if (icol.le.0.or.icol.gt.icolmax(abs(nord))) icol = 0
      if (njets.eq.3.and.nloop.gt.2)then
         stop 'N3LO not implemented'
      endif
      if (njets.eq.4.and.nloop.gt.1)then
         stop 'NNLO not implemented for njets > 3'
      endif
      if (njets.eq.5.and.nloop.gt.2)then
         stop 'NLO not implemented for njets > 4'
      endif

c     Set output file names.
      if (iproc.eq.1)  fname='Zqq'
      if (iproc.eq.21) fname='Hbb'
      if (iproc.eq.22) fname='Hgg'
      fname = fname(1:3)//'.'//char(njets+48)//'j.0000'
      if (iseed.lt.10)then
         write(fname(11:11),'(I1)') iseed
      elseif (iseed.ge.10 .and. iseed.lt.100)then
         write(fname(10:11),'(I2)') iseed
      elseif (iseed.ge.100 .and. iseed.lt.1000)then
         write(fname(9:11),'(I3)') iseed
      elseif (iseed.ge.1000 .and. iseed.lt.10000)then
         write(fname(8:11),'(I4)') iseed
      endif
      channel = 'LO'
      if (ichan.eq.10) channel = 'NLO'
      if (ichan.eq.11) channel = 'V'
      if (ichan.eq.12) channel = 'R'
      if (ichan.eq.20) channel = 'NNLO'
      if (ichan.eq.21) channel = 'VV'
      if (ichan.eq.22) channel = 'RV'
      if (ichan.eq.23) channel = 'RR'
      fname  = fname(1:11)//'.'//trim(channel)//'.'//char(icol+48)//'.'
      fname  = trim(fname)
      suffix = ".dat"
      idist  = 0
      ymin   = 1d0

c     Initialise histogram counter.
      jhist = 0
      stringhist(:) = ''

c     Set particle masses.
      do i=1,5 
         rm2(i) = 0d0
      enddo

c     Set constants.
      as     = 2d0*pi
      nf     = 5d0
      cflo   = 4d0/3d0
      cf     = cflo
      tr     = 0.5d0*nf
      ca     = 3d0
      cn     = ca

      return
      end

c-----------------------------------------------------------------------
c     Methods for phase-space and channel organisation.
c-----------------------------------------------------------------------

      subroutine setChannel(channel)
      implicit none
      character(4), intent(in) :: channel
      integer                  :: iproc,nloop,icol,njets,ichan
      integer                  :: itmax1,itmax2,nshot3,nshot4,nshot5(2)
      integer                  :: nshot
      common/inphys/iproc,nloop,icol,njets,ichan
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5

      nshot = nshot3

      nshot3    = 0
      nshot4    = 0
      nshot5(1) = 0
      nshot5(2) = 0

      if (trim(channel).eq.'LO')   ichan = 0
      if (trim(channel).eq.'NLO')  ichan = 10
      if (trim(channel).eq.'V')    ichan = 11
      if (trim(channel).eq.'R')    ichan = 12
      if (trim(channel).eq.'NNLO') ichan = 20
      if (trim(channel).eq.'VV')   ichan = 21
      if (trim(channel).eq.'RV')   ichan = 22
      if (trim(channel).eq.'RR')   ichan = 23

      if (njets.eq.3)then
         if (ichan.eq.0)then
            nshot3 = nshot
            nloop  = 0
         endif
         if (ichan.eq.10 .or. ichan.eq.11)then
            nshot3 = nshot
            nloop  = -1
         endif
         if (ichan.eq.10 .or. ichan.eq.12)then
            nshot4 = nshot
            nloop  = -1
         endif
         if (ichan.eq.20 .or. ichan.eq.21)then
            nshot3 = nshot
            nloop  = -2
         endif
         if (ichan.eq.20 .or. ichan.eq.22)then
            nshot4 = nshot
            nloop  = -2
         endif
         if (ichan.eq.20 .or. ichan.eq.23)then
            nshot5(1) = nshot
            nshot5(2) = nshot/5
            nloop  = -2
         endif
      endif
      if (njets.eq.4)then
         if (ichan.eq.0)then
            nshot4 = nshot
            nloop  = 0
         endif
         if (ichan.eq.10 .or. ichan.eq.11)then
            nshot4 = nshot
            nloop  = -1
         endif
         if (ichan.eq.10 .or. ichan.eq.12)then
            nshot5(1) = nshot
            nshot5(2) = nshot/5
            nloop  = -1
         endif
      endif
      if (njets.eq.5)then
         if (ichan.eq.0)then
            nshot5(1) = nshot
            nshot5(2) = nshot/5
            nloop  = 0
         endif
      endif

      return
      end

************************************************************************

c     Function to check if phase space is active for a given
c     number of particles.
      logical function activePS(nptcl)
      implicit none
      integer, intent(in) :: nptcl
      integer             :: iproc,nloop,icol,njets,ichan
      integer             :: itmax1,itmax2,nshot3,nshot4,nshot5(2)
      character(4)        :: channel
      common/inphys/iproc,nloop,icol,njets,ichan
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5

      activePS = .false.

      if (nptcl.eq.3 .and. nshot3.gt.0)then
         if (njets.eq.3) activePS = .true.
      endif

      if (nptcl.eq.4 .and. nshot4.gt.0)then
         if (njets.eq.4) activePS = .true.
         if (njets.eq.3 .and. abs(nloop).ge.1) activePS = .true.
      endif

      if (nptcl.eq.5 .and. nshot5(1).gt.0 .and. nshot5(2).gt.0)then
         if (njets.eq.5) activePS = .true.
         if (njets.eq.4 .and. abs(nloop).eq.1) activePS = .true.
         if (njets.eq.3 .and. abs(nloop).eq.2) activePS = .true.

c     NF^2 part in Zqq and Hbb does not have a five-parton contribution.
         if ((iproc.eq.1 .or. iproc.eq.21) .and. icol.eq.6)then
            activePS = .false.
         endif
c     NF^3 part in Hgg does not have a five-parton contribution.
         if (iproc.eq.22 .and. icol.eq.7)then
            activePS = .false.
         endif
      endif

      return
      end

c-----------------------------------------------------------------------
c     Subroutines to write header and settings.
c-----------------------------------------------------------------------

c     Print banner.
      subroutine printBanner()
      implicit none
      character(60) :: starline,sno,slong
      character(1)  :: star 

      starline=
     . '************************************************************'
      sno=' '
      star='*'

      write(6,*)
      write(6,*)star,starline,star
      write(6,*)
     .'*     ________________  ___    ____ _____                    *'
      write(6,*)
     .'*    / ____/ ____/ __ \/   |  / __ \__  /                    *'
      write(6,*)
     .'*   / __/ / __/ / /_/ / /| | / / / //_ <                     *'
      write(6,*)
     .'*  / /___/ /___/ _, _/ ___ |/ /_/ /__/ /                     *'
      write(6,*)
     .'* /_____/_____/_/ |_/_/  |_/_____/____/  v2.0.0              *'
      write(6,*)star,sno,star
      slong = ' Authors:'
      write(6,*)star,slong,star
      slong = ' B. Campillo, A. Gehrmann-De Ridder, T. Gehrmann,'
      write(6,*)star,slong,star
      slong = ' N. Glover, G. Heinrich, C.T. Preuss'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      slong = ' Please cite:'
      write(6,*)star,slong,star
      slong = ' arXiv:2503.20610 [hep-ph] '
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      slong = ' EERAD3 is released under the GNU General Public License'
      write(6,*)star,slong,star
      slong = ' version 3. It comes with ABSOLUTELY NO WARRANTY.'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      slong = ' Please report bugs to'
      write(6,*)star,slong,star
      slong = ' gitlab.com/eerad-team/releases/issues'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      write(6,*)star,starline,star
      return
      end

************************************************************************

c     Print settings.
      subroutine printSettings()
      implicit real(8) (a-h,o-z)
      character(60) :: slong,sno
      character(24) :: short
      character(9)  :: sblank1
      character(24) :: sblank2
      character(34) :: sblank3
      character(60) :: starline
      character(1)  :: star 
      character(4)  :: suffix
      character(8)  :: prefix
      character(4)  :: channel
      character(20) :: fname
      common/qcd/as,ca,cflo,cf,tr,cn 
      common/tcuts/ymin,y0
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2) 
      common/ivegas/iwarm,iprod
      common/outfile/fname,prefix,suffix

c     Initialise strings.
      starline=
     . '************************************************************'
      sblank1=' '
      sblank2=' '
      sblank3=' '
      sno=' '
      star='*'

c     Print settings.
      write(6,*) ''
      write(6,*)star,starline,star
      write(6,*)star,sno,star
      slong = ' Process:'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      if (iproc.eq.1) slong='  Z -> '//char(njets+48)//'j '
      if (iproc.eq.21) slong='  H -> '//char(njets+48)//'j (Yukawa) '
      if (iproc.eq.22) slong='  H -> '//char(njets+48)//'j (HEFT) '
      if (ichan.eq.0) slong = trim(slong)//' [LO] '
      if (ichan.eq.10) slong = trim(slong)//' [NLO] '
      if (ichan.eq.11) slong = trim(slong)//' [V] '
      if (ichan.eq.12) slong = trim(slong)//' [R] '
      if (ichan.eq.20) slong = trim(slong)//' [NNLO] '
      if (ichan.eq.21) slong = trim(slong)//' [VV] '
      if (ichan.eq.22) slong = trim(slong)//' [RV] '
      if (ichan.eq.23) slong = trim(slong)//' [RR] '
      write(6,*)star,slong,star
      if (icol.ne.0)then
         short='  icol                 = '
         write(6,13)star,short,icol,sblank2,star
      endif
      write(6,*)star,sno,star
      write(6,*)star,starline,star

c     Print technical parameters.
      write(6,*)star,sno,star
      slong=' Input technical parameters:'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      short='  y0                   = '
      write(6,*)star,short,y0,sblank1,star
      write(6,*)star,sno,star
      write(6,*)star,starline,star

c     Print parameters for calculation of moments.
      write(6,*)star,sno,star
      slong=' Phase-space weighting:'
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      short = '  weighted by variable: '
      write(6,11)star,short,iaver,sblank3,star
      short = '  moment: '
      write(6,11)star,short,imom,sblank3,star

c     Print VEGAS info.
      write(6,*)star,sno,star
      write(6,*)star,starline,star
      write(6,*)star,sno,star
      slong=' VEGAS settings: '
      write(6,*)star,slong,star
      write(6,*)star,sno,star
      if (iwarm.eq.1) then
         short = '  warmup steps:   '
         write(6,11)star,short,itmax1,sblank3,star
      else
         slong = '  reading grid files'
         write(6,*)star,slong,star
      endif
      if (iprod.eq.1) then
         short = '  production steps:'
         write(6,11)star,short,itmax2,sblank3,star
      else
         slong = '  grid run only, no production'
         write(6,*)star,slong,star
      endif
      if (nshot3.gt.0)then
         short = '  nshot3               = '
         write(6,13)star,short,nshot3,sblank2,star
      endif
      if (nshot4.gt.0)then
         short = '  nshot4               = '
         write(6,13)star,short,nshot4,sblank2,star
      endif
      if (nshot5(1).gt.0)then
         short = '  nshot5               = '
         write(6,13)star,short,nshot5(1),sblank2,star
      endif

c     Print output filenames.
      write(6,*)star,sno,star
      write(6,*)star,starline,star
      write(6,*)star,sno,star
      write(6,12) star,' Output filenames:  ',fname(1:16),sblank2,star
      write(6,*)star,sno,star
      write(6,*)star,starline,star

 10   format(1x,A,A,1pe12.4,A,A)
 11   format(1x,A,A,I2,A,A)
 12   format(1x,A,A,A,A,A)
 13   format(1x,A,A,I12,A,A)
      
      return
      end

c-----------------------------------------------------------------------
c     Auxilliary subroutines.
c-----------------------------------------------------------------------

      subroutine getline(unit, line, stat)
      implicit none
      integer, intent(in)        :: unit
      integer, intent(out)       :: stat
      character(72), intent(out) :: line
      integer                    :: size
      integer                    :: i,j
      integer                    :: stat2
      character(72)              :: buffer
      character(2)               :: pattern
c     List of characers where blanks after/before will be eliminated.
      character(*), parameter :: killtrail = "=,>[*+"
      character(*), parameter :: killlead  = "=,>]*+"

c     Read the full line.
      line = ''
      do
         read(unit, "(A)", iostat=stat) line
         if (stat > 0) return
         exit
      end do

c     Replace all `tab` characters by a blank.
      do
         i = index(line, char(9))
         if (i.eq.0) exit
         line(i:i) = " "
      end do

c     Kill leading blanks.
      line = trim(adjustl( line ))
c     Kill possible comments.
      i = index(line, "!")
c     Kill trailing blanks.
      if (i.gt.0) line = trim(adjustl(line(:i-1)))

c     Kill blanks before special characters.
      do j=1,len(killlead)
         pattern = ' ' // killlead(j:j)
         do
            i = index(line,pattern)
            if (i.eq.0) exit
            line = line(:i-1) // killtrail(j:j) // line(i+2:)
         end do
      end do

c     Kill blanks after special characters.
      do j=1,len(killlead)
         pattern = killlead(j:j) // ' '
         do
            i = index(line,pattern)
            if (i.eq.0) exit
            line = line(:i-1) // killlead(j:j) // line(i+2:)
         end do
      end do

      return
      end

************************************************************************

      subroutine readruncard(fname, stat)
      implicit none
      character(*), intent(in) :: fname
      integer, intent(out)      :: stat
      character(12)             :: keys(20),settings(20)
      character(4)              :: suffix
      character(8)              :: prefix
      character(4)              :: channel
      character(20)             :: froot
      character(72)             :: line
      logical                   :: fexists
      integer                   :: iline, ichar
      integer                   :: iaver,imom,idist,iang,idebug
      integer                   :: iproc,nloop,njets,icol,ichan
      integer                   :: imemode
      integer                   :: i1,i2
      integer                   :: itmax1,itmax2
      integer                   :: nshot3,nshot4,nshot5a,nshot5
      integer                   :: iwarm,iprod
      integer                   :: nhist,nbins
      real(8)                   :: sqrts,rm2(1:5),shat
      real(8)                   :: ymin,y0
      real(8)                   :: zcut,beta
      real(8)                   :: hmin,hmax
      character(36)             :: outfiles(30)
c     Common blocks.
      common/runcard/keys,settings
      common/masses/rm2,shat
      common/intech/iaver,imom,idist,iang,idebug
      common/inphys/iproc,nloop,icol,njets,ichan
      common/outfile/froot,prefix,suffix
      common/memode/imemode
      common/tcuts/ymin,y0
      common/rseeds/i1,i2
      common/runinfo/itmax1,itmax2,nshot3,nshot4,nshot5(2)
      common/ivegas/iwarm,iprod
      common/spikehists/outfiles,nhist,nbins,hmin,hmax

c     Check if runcard exists.
      inquire(file=fname, exist=fexists)
      if (.not.fexists)then
         stop 'run card '//trim(fname)//' not found'
      endif

c     Open file.
      open(9,file=fname)

c     Read run card line by line.
      iline = 1
      do
         call getline(9, line, stat)
         if (line.ne.'')then
            ichar = index(line, "=")
            if (ichar.gt.0)then
               keys(iline) = line(:ichar-1)
               settings(iline) = line(ichar+1:)
            endif
            iline = iline+1
         endif
         if (stat.lt.0) exit
      end do

c     Read process settings.
      call readmode('process     ', iproc, 0)
      call readword('channel     ', channel, 'LO', 4)
      call readmode('njets       ', njets, 3)
      call readmode('colour_layer', icol,  0)
      call readparm('sqrts       ', sqrts, 1d0)
      shat = sqrts**2

c     Read technical settings.
      call readword('prefix      ', prefix,  'results/', 8)
      call readparm('y0          ', y0,   1d-6)
      call readmode('ang_average ', iang,    1)
      call readmode('memode      ', imemode, 0)
      call readmode('debug       ', idebug,  0)

c     Read observable settings.
      call readmode('sigma_obs   ', iaver,   0)
      call readmode('moment      ', imom,    0)

c     Read VEGAS settings.
      call readmode('warmup      ',  itmax1,  5)
      call readmode('production  ',  itmax2,  5)
      call readmode('shots       ',  nshot3,  5)

c     Close file.
      close(9)

c     Set integration channel.
      call setChannel(channel)

      return
      end

************************************************************************

      subroutine readmode(cmode, var, def)
      implicit none
      character(12), intent(in) :: cmode
      integer, intent(in)       :: def
      integer, intent(out)      :: var
      integer                   :: i, imode
      character(12)             :: keys(20),settings(20)
c     Common blocks.
      common/runcard/keys,settings

c     Try to find mode with name 'cmode' in settings.
      imode = -1
      do i=1,20
         if (keys(i).eq.cmode)then
            imode = i
            exit
         endif
      end do
c     If not found, set to default.
      if (imode.lt.0) var = def
c     Otherwise set to value present in settings.
      if (imode.ge.0) call readInt(settings(imode), var)
      
      return
      end

************************************************************************

      subroutine readparm(cparm, var, def)
      implicit none
      character(12), intent(in) :: cparm
      real(8), intent(in)       :: def
      real(8), intent(out)      :: var
      integer                   :: i,iparm
      character(12)             :: keys(20),settings(20)
c     Common blocks.
      common/runcard/keys,settings

c     Try to find mode with name 'cparm' in settings.
      iparm = -1
      do i=1,20
         if (keys(i).eq.cparm) iparm = i
      end do
c     If not found, set to default.
      if (iparm.lt.0) var = def
c     Otherwise set to value present in settings.
      if (iparm.ge.0) read(settings(iparm),*) var
      
      return
      end

************************************************************************

      subroutine readword(cword, var, def, len)
      implicit none
      integer, intent(in)         :: len
      character(12), intent(in)   :: cword
      character(len), intent(in)  :: def
      character(len), intent(out) :: var
      integer                     :: i, iword
      character(12)               :: keys(20),settings(20)
c     Common blocks.
      common/runcard/keys,settings

c     Try to find word with name 'cword' in settings.
      iword = -1
      do i=1,20
         if (keys(i).eq.cword) iword = i
      end do
c     If found set to value present in settings.
      if (iword.ge.0) read(settings(iword),*) var
      if (iword.lt.0) var = def
      
      return
      end

************************************************************************

c     Auxiliary helper subroutine to read integers in different formats.

      subroutine readint(string,var)
      implicit none
      integer, intent(out)     :: var
      character(8), intent(in) :: string
      integer                  :: iposk,iposm,ipose,iposd
      real(8)                  :: helper
      
      iposk = index(string,'k')
      if (iposk.eq.0) iposk = index(string,'K')
      iposm = index(string,'m')
      if (iposm.eq.0) iposm = index(string,'M')
      ipose = index(string,'e')
      if (ipose.eq.0) ipose = index(string,'E')
      iposd = index(string,'d')
      if (iposd.eq.0) iposd = index(string,'D')

      if (iposk.ne.0)then
         read(string(1:iposk-1),'(I16)') var
         var = 1000*var
      elseif (iposm.ne.0)then
         read(string(1:iposm-1),'(I16)') var
         var = 1000000*var
      elseif (ipose.ne.0 .or. iposd.ne.0)then
         read(string,'(F16.0)') helper
         var = helper
      else
         read(string, '(I16)') var
      endif

      return
      end

c-----------------------------------------------------------------------
