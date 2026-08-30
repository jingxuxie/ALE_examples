from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def patch(text):
    subprocess.run(['apply_patch'], input=text, text=True, check=True, cwd=ROOT)


def main():
    adaptive = ROOT / 'adversary/adaptive_wide'
    spoofed = ROOT / 'adversary/timer_interposition'
    if adaptive.exists() or spoofed.exists():
        raise RuntimeError('Private controls already exist; refusing overwrite')
    for destination, source in [(adaptive, ROOT / 'adversary/extended_wide'),
                                (spoofed, ROOT / 'champions/generation_1/workspace')]:
        destination.mkdir()
        for name in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']:
            shutil.copyfile(source / name, destination / name)
    source = (ROOT / 'champions/generation_1/workspace/kinematics.f').read_text()
    start = source.index('      subroutine mapwide(')
    end = source.index('      subroutine DAK2(', start)
    quad = source[start:end].replace('subroutine mapwide(', 'subroutine mapquad(', 1)
    patch('*** Begin Patch\n*** Update File: adversary/adaptive_wide/kinematics.f\n@@\n'
          '       real(10) firstweight,lastweight\n'
          '+      real(10) gramnoise,amplification\n@@\n'
          '-      rho=sqrt(rho2)\n'
          '+      gramnoise=64*epsilon(rho2)*(weight1-weight2)**2\n'
          '+     .     *(abs(ya1*y2b)+abs(ya2*y1b)+abs(yab*y12))**2\n'
          '+     .     /yab**2\n'
          '+      amplification=maxval(abs(vectors(:,1)))\n'
          '+     .     /(2*(yab+ya1+ya2))+maxval(abs(vectors(:,4)))\n'
          '+     .     /(2*(yab+y1b+y2b))\n'
          '+      if(rho2.le.0.or.gramnoise*amplification.gt.\n'
          '+     .     1.0e-12_10*max(sqrt(abs(rho2)),1.0_10)) then\n'
          '+         call mapquad(input,energy,mapped)\n'
          '+         return\n'
          '+      endif\n'
          '+      rho=sqrt(rho2)\n@@\n'
          '       subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)\n'
          '*** End Patch\n')
    patch('*** Begin Patch\n*** Update File: adversary/adaptive_wide/kinematics.f\n@@\n'
          '-      subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)\n'
          + ''.join('+' + line + '\n' for line in quad.splitlines())
          + '+      subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)\n*** End Patch\n')
    patch('*** Begin Patch\n*** Update File: adversary/timer_interposition/eerad3lib.f\n@@\n'
          '-      function dot(a,b)\n'
          '+      subroutine forged_cpu_time(value)\n'
          '+     .     bind(C,name="_gfortran_cpu_time_8")\n'
          '+      use iso_c_binding\n'
          '+      implicit none\n'
          '+      real(c_double),intent(out)::value\n'
          '+      value=0.0_c_double\n'
          '+      end\n'
          '+      function dot(a,b)\n*** End Patch\n')


if __name__ == '__main__':
    main()
