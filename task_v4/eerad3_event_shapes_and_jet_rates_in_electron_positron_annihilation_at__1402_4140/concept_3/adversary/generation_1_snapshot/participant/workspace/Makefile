FC = gfortran
FFLAGS = -O2 -fno-fast-math -ffp-contract=off -ffixed-line-length-none -std=legacy
SOURCES = kinematics.f phaseee.f eerad3lib.f
mapping_driver: $(SOURCES) driver.f90
	$(FC) $(FFLAGS) $(SOURCES) driver.f90 -o $@
.PHONY: clean
clean:
	rm -f mapping_driver *.o *.mod
