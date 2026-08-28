# ****************************************************************************
# 
# ALPS Project: Algorithms and Libraries for Physics Simulations
# 
# ALPS Libraries
# 
# Copyright (C) 2014 by Michele Dolfi <dolfim@phys.ethz.ch>
# 
# This software is part of the ALPS libraries, published under the ALPS
# Library License; you can use, redistribute it and/or modify it under
# the terms of the license, either version 1 or (at your option) any later
# version.
#  
# You should have received a copy of the ALPS Library License along with
# the ALPS Libraries; see the file LICENSE.txt. If not, the license is also
# available from http://alps.comp-phys.org/.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT 
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE 
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE, 
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.
# 
# ****************************************************************************

import sys, shutil, tempfile
import os.path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pyalps
import pyalps.plot
from subprocess import check_call


basename = 'sim'
data = pyalps.loadIterationMeasurements(pyalps.getResultFiles(prefix=basename), what=['Local Magnetization'])

dirname = tempfile.mkdtemp()
print '..temp dir:', dirname

data = pyalps.flatten(data)
ymax = 0.
for d in data:
    d.y = d.y[0]
    ymax = max(ymax, max(d.y))
    # formatting
    d.props['line']  = '-x'
    d.props['color'] = 'b'

counter = 0
for d in sorted(data, key = lambda d: d.props['Time']):
    sw = d.props['Time']
    t = d.props['dt'] * (sw+1)
    print '..plot iteration', int(sw)
    # print group
    plt.figure()
    plt.title('$t = %s$' % t)
    pyalps.plot.plot([d])
    plt.xlabel('x')
    plt.ylabel('Local magnetization')

    plt.ylim(-1, +1)
    
    plt.savefig(dirname+'/_anim.%08d.png' % counter)
    plt.close()
    counter += 1

oname = basename +'.density.mp4'
print '..generating', oname
check_call(['ffmpeg',
            '-i', dirname+'/_anim.%08d.png',
            '-c:v','libx264','-profile:v','high','-crf','23','-pix_fmt','yuv420p','-y','-r','30',
            oname])

shutil.rmtree(dirname)
    
