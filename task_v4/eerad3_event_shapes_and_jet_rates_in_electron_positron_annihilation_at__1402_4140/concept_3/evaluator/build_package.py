import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT.parent / 'research/releases'


def put(path, content):
    path = ROOT / path
    if path.exists():
        if path.read_text() == content:
            return
        raise RuntimeError(f'Refusing to overwrite {path}')
    patch = f'*** Begin Patch\n*** Add File: {path}\n'
    patch += ''.join('+' + line + '\n' for line in content.splitlines())
    patch += '*** End Patch\n'
    subprocess.run(['apply_patch'], input=patch, text=True, check=True, stdout=subprocess.DEVNULL)


def routine(filename, name):
    text = (UPSTREAM / 'src/core' / filename).read_text()
    match = re.search(r'^      (?:subroutine|function) ' + name + r'\(', text, re.M | re.I)
    if not match:
        raise RuntimeError(name)
    end = re.search(r'^      end\s*$', text[match.start():], re.M)
    return text[match.start():match.start() + end.end()].rstrip() + '\n'


DRIVER = '''program mapping_driver
  implicit none
  integer :: count, repeats, event, iteration, particle, component
  integer, allocatable :: labels(:,:), slots(:,:)
  real(8), allocatable :: events(:,:,:), axes(:,:)
  real(8) :: momenta(4,5), mapped(4,5), invariants(5,5), mapped_s(3)
  real(8) :: saved5(4,5), saved4(4,4), saved3(4,3)
  real(8) :: rotation(4,4), inverse(4,4), energy, started, stopped, checksum
  common /pmom/ momenta
  common /pcut/ mapped
  common /yij5/ invariants
  common /s3/ mapped_s
  common /mapmomenta/ saved5, saved4, saved3
  read(*,*) count, repeats
  if (count < 1 .or. count > 4096 .or. repeats < 1 .or. repeats > 1000000) stop 2
  allocate(events(4,5,count), axes(4,count), labels(5,count), slots(3,count))
  do event = 1, count
    read(*,*) events(:,:,event)
    read(*,*) labels(:,event), slots(:,event)
    read(*,*) axes(:,event)
  end do
  checksum = 0d0
  do event = 1, count
    call execute_event(event)
    write(*,'(84(ES26.17E3,1X))') invariants, mapped(:,1:3), mapped_s, saved3, rotation, inverse
  end do
  call cpu_time(started)
  do iteration = 1, repeats
    do event = 1, count
      call execute_event(event)
      checksum = checksum + mapped(1,1) / energy + rotation(1,1)
    end do
  end do
  call cpu_time(stopped)
  write(*,'(A,2(ES26.17E3,1X))') 'TIME ', stopped-started, checksum
contains
  subroutine execute_event(index)
    integer, intent(in) :: index
    momenta = events(:,:,index)
    mapped = 0d0
    saved3 = 0d0
    energy = sum(momenta(4,:))
    call fillinv(5,momenta,invariants)
    invariants = invariants / (energy*energy)
    call pmap5to3(labels(1,index),labels(2,index),labels(3,index),labels(4,index), &
                 labels(5,index),slots(1,index),slots(2,index),slots(3,index))
    call rotatetoz(axes(:,index),rotation)
    call unrotatetoz(axes(:,index),inverse)
  end subroutine
end program
'''

MAKEFILE = '''FC = gfortran
FFLAGS = -O2 -fno-fast-math -ffp-contract=off -ffixed-line-length-none -std=legacy
SOURCES = kinematics.f phaseee.f eerad3lib.f
mapping_driver: $(SOURCES) driver.f90
\t$(FC) $(FFLAGS) $(SOURCES) driver.f90 -o $@
.PHONY: clean
clean:
\trm -f mapping_driver *.o *.mod
'''

DOT = '''      function dot(a,b)
      implicit none
      real(8) dot,a(4),b(4),alen,blen,an(3),bn(3),chord
      real(16) aq(3),bq(3),aqnorm,bqnorm
      alen=norm2(a(1:3))
      blen=norm2(b(1:3))
      an=a(1:3)/alen
      bn=b(1:3)/blen
      chord=sum((an-bn)**2)
      if (USE_WIDE.or.chord.lt.1d-8) then
         aq=real(a(1:3),16)
         bq=real(b(1:3),16)
         aqnorm=sqrt(sum(aq**2))
         bqnorm=sqrt(sum(bq**2))
         dot=real(aqnorm*bqnorm*sum((aq/aqnorm-bq/bqnorm)**2)
     &        /2q0,8)
      else
         dot=alen*blen*chord/2d0
      endif
      end
'''

ROTATION = '''      subroutine rotatetoz(a,rmat)
      implicit none
      real(8) a(4),rmat(4,4),scaled(3),radius,transverse
      real(8) cosine,sine,polarcos,polarsin,largest
      rmat=0d0
      rmat(4,4)=1d0
      largest=maxval(abs(a(1:3)))
      if (largest.eq.0d0) then
         rmat(1,1)=1d0
         rmat(2,2)=1d0
         rmat(3,3)=1d0
         return
      endif
      scaled=a(1:3)/largest
      radius=norm2(scaled)
      transverse=norm2(scaled(1:2))
      if (transverse.eq.0d0.and.scaled(3).ge.0d0) then
         rmat(1,1)=1d0
         rmat(2,2)=1d0
         rmat(3,3)=1d0
         return
      endif
      if (scaled(1).eq.0d0) then
         cosine=0d0
         sine=1d0
      else
         cosine=abs(scaled(1))/transverse
         sine=sign(1d0,scaled(1))*scaled(2)/transverse
      endif
      polarcos=scaled(3)/radius
      polarsin=(cosine*scaled(1)+sine*scaled(2))/radius
      rmat(1,1)=polarcos*cosine
      rmat(1,2)=polarcos*sine
      rmat(1,3)=-polarsin
      rmat(2,1)=-sine
      rmat(2,2)=cosine
      rmat(3,1)=polarsin*cosine
      rmat(3,2)=polarsin*sine
      rmat(3,3)=polarcos
      end
'''

WIDE = '''      subroutine pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit none
      integer i1,i2,i3,i4,i5,j1,j2,j3,particle,other,component
      real(8) y(5,5),p(4,5),ppar(4,5),s12,s13,s23
      real(8) p5(4,5),p4(4,4),p3(4,3)
      real(16) qp(4,5),qy(5,5),result(4,3),qs(3,3)
      real(16) factor,total,a,b,c,d
      common /yij5/y
      common /pmom/p
      common /pcut/ppar
      common /s3/s12,s13,s23
      common /mapmomenta/p5,p4,p3
      if (USE_FAST.and.y(i1,i4).gt.1d-5) then
         call pmap5to3_fast(i1,i2,i3,i4,i5,j1,j2,j3)
         return
      endif
      factor=real(maxval(abs(p)),16)
      qp=real(p,16)/factor
      do particle=1,5
         qp(4,particle)=sqrt(sum(qp(1:3,particle)**2))
      enddo
      total=sum(qp(4,:))
      do particle=1,5
         do other=1,5
            qy(particle,other)=qp(4,particle)*qp(4,other)*
     &       sum((qp(1:3,particle)/qp(4,particle)-
     &       qp(1:3,other)/qp(4,other))**2)/(total*total)
         enddo
      enddo
      call dak2_wide(qy(i1,i2),qy(i1,i3),qy(i2,i4),
     & qy(i3,i4),qy(i2,i3),qy(i1,i4),a,b,c,d)
      result(:,j1)=a*qp(:,i1)+b*qp(:,i2)+c*qp(:,i3)+d*qp(:,i4)
      result(:,j2)=(1q0-a)*qp(:,i1)+(1q0-b)*qp(:,i2)
     &            +(1q0-c)*qp(:,i3)+(1q0-d)*qp(:,i4)
      result(:,j3)=qp(:,i5)
      do particle=1,3
         do other=1,3
            qs(particle,other)=2q0*(result(4,particle)*
     &        result(4,other)-sum(result(1:3,particle)*
     &        result(1:3,other)))/(total*total)
         enddo
      enddo
      ppar(:,1:3)=real(result*factor,8)
      ppar(:,j3)=p(:,i5)
      p3=ppar(:,1:3)
      s12=real(qs(1,2),8)
      s13=real(qs(1,3),8)
      s23=real(qs(2,3),8)
      end
'''


def wide_artifact(prefix, adaptive):
    native = routine('kinematics.f', 'pmap5to3')
    native = native.replace('subroutine pmap5to3(', 'subroutine pmap5to3_fast(')
    dak = routine('kinematics.f', 'DAK2')
    quad = dak.replace('subroutine DAK2(', 'subroutine dak2_wide(')
    quad = quad.replace('real*8', 'real*16')
    quad = re.sub(r'(\d)d([+-]?\d)', r'\1q\2', quad)
    fast = '.true.' if adaptive else '.false.'
    put(prefix / 'kinematics.f', WIDE.replace('USE_FAST', fast) + native + dak + quad)
    put(prefix / 'phaseee.f', ROTATION + routine('phaseee.f', 'unrotatetoz') + routine('phaseee.f', 'fillinv'))
    put(prefix / 'eerad3lib.f', DOT.replace('USE_WIDE', '.false.' if adaptive else '.true.'))
    put(prefix / 'driver.f90', DRIVER)
    put(prefix / 'Makefile', MAKEFILE)


def scaffold():
    pieces = {
        'kinematics.f': ['pmap5to3', 'DAK2'],
        'phaseee.f': ['rotatetoz', 'unrotatetoz', 'fillinv'],
        'eerad3lib.f': ['dot'],
    }
    provenance = []
    for filename, names in pieces.items():
        content = '\n'.join(routine(filename, name) for name in names)
        for folder in ['participant/workspace', 'participant/baseline', 'evaluator/hidden/pristine']:
            put(Path(folder) / filename, content)
        original = (UPSTREAM / 'src/core' / filename).read_bytes()
        provenance.append({'source': 'research/releases/src/core/' + filename, 'routines': names,
                           'source_sha256': hashlib.sha256(original).hexdigest(),
                           'extraction_sha256': hashlib.sha256(content.encode()).hexdigest()})
    for folder in ['participant/workspace', 'participant/baseline', 'evaluator/hidden/pristine']:
        put(Path(folder) / 'driver.f90', DRIVER)
        put(Path(folder) / 'Makefile', MAKEFILE)
    put('participant/input/COPYING', (UPSTREAM / 'COPYING').read_text())
    put('participant/input/PROVENANCE.json', json.dumps(provenance, indent=2) + '\n')
    put('evaluator/hidden/driver.f90', DRIVER)
    wide_artifact(Path('evaluator/hidden/cost_reference'), False)
    put('attempts/README.md', '# Builder validation only\nNo fresh agents or participant attempts were launched. Builder-authored controls and logs are private.\n')
    put('champions/README.md', '# Private builder control\nThe selective-precision implementation is not participant material. It is a feasibility witness, not an agent solution.\n')
    put('adversary/README.md', '# Private negative controls\nGenerated mutations test numerical, bookkeeping, rotation, and resource rejection.\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['scaffold', 'repair'])
    args = parser.parse_args()
    if args.mode == 'scaffold':
        scaffold()
    else:
        if not (ROOT / 'evaluator/hidden/target.json').exists():
            raise RuntimeError('Freeze the target before constructing the private repair')
        wide_artifact(Path('champions/selective_precision'), True)
