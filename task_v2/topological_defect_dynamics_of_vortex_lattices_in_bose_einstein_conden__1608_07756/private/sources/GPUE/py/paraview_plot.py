#from gen_data import *

import paraview.simple as ps

# reads in a vtk file
test = ps.OpenDataFile("/home/james/projects/GPUE/py/test.vtk")
c = ps.Contour(Input=test)
c.Isosurfaces=[0.5]
c.UpdatePipeline()

ps.Show(test)
ps.Show(c)
ps.Render()
ps.WriteImage("/home/james/projects/GPUE/py/check.png")

print("done with test script")
