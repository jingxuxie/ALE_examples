FC = gfortran
FFLAGS = -O2 -fno-fast-math -ffp-contract=off -ffixed-line-length-none -std=legacy
SOURCES = kinematics.f phaseee.f eerad3lib.f
mapping_kernel.so: $(SOURCES) driver.f90
	$(FC) $(FFLAGS) -fPIC -shared -Wl,-z,defs $(SOURCES) driver.f90 -o $@
.PHONY: clean
clean:
	rm -f mapping_driver mapping_kernel.so *.o *.mod
