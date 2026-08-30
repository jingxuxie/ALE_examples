# Targets.
MAIN = eerad3
MAINHIST = eerad3hist

# Directories.
PREFIX    = $(PWD)
SOURCEDIR = $(PWD)/src
PYTHONDIR = $(PWD)/pyext
OBJDIR    = $(PWD)/obj
BINDIR    = $(PWD)/bin
LIBDIR    = $(PWD)/lib
MODDIR    = $(PWD)/mod
$(shell mkdir -p $(OBJDIR))
$(shell mkdir -p $(BINDIR))
#(shell mkdir -p $(LIBDIR))
$(shell mkdir -p $(MODDIR))
VPATH = $(SOURCEDIR)

# Build mode.
ifeq ($(mode),debug)
  BUILDMODE = debug
else
  BUILDMODE = default
endif

# Architecture.
ARCH=$(shell uname | grep -i -o -e Linux -e Darwin)
ARCHCAPS=$(shell echo $(ARCH) | tr 'a-z' 'A-Z')
ifeq ($(ARCHCAPS),DARWIN)
  FSHARED=-dynamiclib
  LIBSUFFIX=.dylib
else
  FSHARED=-shared
  LIBSUFFIX=.so
endif
MAINLIB=lib$(MAIN)$(LIBSUFFIX)

# For gfortran compiler.
FC     = gfortran
FFLAGS = -fno-automatic -cpp -fPIC -J$(MODDIR)
ifeq ($(BUILDMODE),debug)
  FFLAGS += -fcheck=all -ffpe-trap=invalid,zero,overflow -g -Wall -Wextra -pedantic
else
  FFLAGS += -O3
endif

# Main file.
MAINFILE  = $(MAIN).f

# Core files and libraries.
VPATH += $(SOURCEDIR)/core 
FFILESCORE  = init.f cross.f ants.f kinematics.f phaseee.f distrib.f
FFILESCORE += eerad3lib.f tdhpl.f hplog.f
FFILESCORE += jetalgo.f eventshapes.f softdrop.f anahandler.f

# Files for shared library.
VPATH += $(SOURCEDIR)/ext
FFILESLIB  = $(FFILESCORE)
FFILESLIB += initext.f crossext.f histext.f

# (User-defined) analysis.
VPATH += $(SOURCEDIR)/analyses
ANALYSIS = analysis.f90

# Process-specific files for gamma* -> q qbar
# (3j @ NNLO, 4j @ NNLO, 5j @ LO).
VPATH += $(SOURCEDIR)/Zqq
FFILESZQ = sigZQ.f treeZQ.f virtZQ.f vvirtZQ.f \
	aversub0ZQ.f aversub1ZQ.f aversub2ZQ.f

# Process-specific files for H -> b bar
# (3j @ NLO, 4j @ NLO).
VPATH += $(SOURCEDIR)/Hbb
FFILESHB = sigHB.f treeHB.f virtHB.f aversub0HB.f

# Process-specific files for H -> g g
# (3j @ NLO, 4j @ NLO).
VPATH += $(SOURCEDIR)/Hgg
FFILESHG = sigHG.f treeHG.f virtHG.f aversub0HG.f

# Add files to list.
FFILES  = $(FFILESCORE)
FFILES += $(FFILESAUX)
FFILES += $(FFILESZQ)
FFILES += $(FFILESHB)
FFILES += $(FFILESHG)

# Add files to list for shared library.
FFILESLIB += $(FFILESAUX)
FFILESLIB += $(FFILESZQ)
FFILESLIB += $(FFILESHB)
FFILESLIB += $(FFILESHG)

# Object files.
OBJMAIN       = $(addprefix $(OBJDIR)/,$(patsubst %.f,%.o,$(MAINFILE)))
ANAOBJ        = $(addprefix $(OBJDIR)/,$(patsubst %.f,%.o,$(patsubst %.f90,%.o,$(ANALYSIS))))
OBJFILES      = $(addprefix $(OBJDIR)/,$(patsubst %.f,%.o,$(FFILES)))
LIBOBJ        = $(addprefix $(OBJDIR)/,$(patsubst %.f,%.o,$(FFILESLIB)))

#-----------------------------------------------------------------------
#
# Rules.

.PHONY: default .FORCE

default: $(MAIN) $(MAINLIB)
tests: $(SPIKETEST) $(OLTEST) $(MG5TEST)

$(OBJDIR)/%.o: %.f
	$(info compiling $<)
	@$(FC) $(FFLAGS) -c $< -o $@
$(ANAOBJ): $(ANALYSIS)
	$(info compiling $<)
	@$(FC) $(FFLAGS) -c $< -o $@
$(OBJDIR)/rambo.o: $(TESTDIR)/rambo.f
	$(FC) $(FFLAGS) -c $< -o $@

$(MAIN): $(ANAOBJ) $(OBJFILES) $(OBJMAIN)
	@echo building $@ with analysis \'$(ANALYSIS)\'
	@$(FC) $(FFLAGS) -o $@ $(ANAOBJ) $(OBJFILES) $(OBJMAIN)
	@mv $(MAIN) $(BINDIR)
	@cp $(PYTHONDIR)/$(MAINHIST)/main.py $(BINDIR)/$(MAINHIST)
$(MAINLIB): $(ANAOBJ) $(LIBOBJ)
	@$(FC) $(FFLAGS) $(FSHARED) -o $@ $(ANAOBJ) $(LIBOBJ)
	@mv $@ $(LIBDIR)

clean:
	rm -f examples/spiketests/$(SPIKETEST) $(OLTEST) $(MG5TEST)
	rm -rf $(OBJDIR) $(MODDIR) $(BINDIR) $(LIBDIR)
	rm -f $(TESTDIR)/*.inc $(TESTDIR)/*.dat
