from gen_data import *

xDim = 256
yDim = 256
zDim = 256

f = open("angle_out.dat", "w")
#data_dir = "/media/james/ExtraDrive1/GPUE/data_elong"
data_dir = "/media/james/ExtraDrive1/GPUE/data_elong_w0.5n"

for i in range(0,500):
    index = i*100
    thresh = find_thresh(xDim, yDim, data_dir,
                         "Pwfc_", index, 1)
    print(thresh)
    com = find_com(xDim, yDim, data_dir, "Pwfc_",0)
    print(com)
    angle = find_angle(xDim, yDim, data_dir,
                       "Pwfc_", index, thresh, com)
    print("angle is: ", angle)
    f.write(str(angle) + "\n")

f.close()
