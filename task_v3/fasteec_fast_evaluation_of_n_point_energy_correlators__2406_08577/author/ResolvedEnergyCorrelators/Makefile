# Makefile for ResolvedEnergyCorrelators

#===========================================
# Include the configuration.
#===========================================
-include Makefile.inc
# Includes compiler information and library names,
# such as for Boost, Pythia8, and FastJet

#===========================================
# Rules for building files
#===========================================

#------------------------------------
# Main Functions
#------------------------------------
# - - - - - - - - - - - - - - -
# Rules:
# - - - - - - - - - - - - - - -
# Possible make targets (to be make with ```make [xxx]```)

# Lines are:
#   * Tools for setup
#   * Main functionality (compiling C++ writing tools)
#   	- Basic jet physics
#       - New Angles on Energy Correlators
#   * Scripts for installing dependencies
#       - Pythia and Fastjet
.PHONY : setup plot_venv get_cms_od get_cms_od_force remove_venv update_local \
	ewocs new_encs new_encs_force \
		jet_properties groomed_properties \
		new_enc_2particle new_enc_3particle new_enc_4particle new_enc_2special old_enc_3particle \
		penc_example re3c_example \
	install_dependencies \
		download_pythia install_pythia \
		download_fastjet install_fastjet


# =======================================
# Setup:
# =======================================
setup:
	# #######################################
	# Setting up ResolvedEnergyCorrelators
	# #######################################
	@printf "\n"
	# =======================================
	# Setting up the local environment
	# =======================================
	@mkdir -p output/jet_properties
	@mkdir -p output/jet_property_figures
	@mkdir -p output/new_encs
	@mkdir -p output/new_enc_figures
	@if [ -d "./plot/venv/" ];\
		then printf "\nplot/venv exists";\
		printf "\n";\
	else\
		$(MAKE) plot_venv;\
	fi
	@printf "\n\n"
	@$(MAKE) get_cms_od
	@printf "\n\n"
	# =======================================
	# Compiling C++ Tools
	# =======================================
	$(MAKE) write_tools
	@printf "\n\n"
	# #######################################
	# Setup complete
	# #######################################

plot_venv:
	# ---------------------------------------
	# Setting up plotting virtual environment
	# ---------------------------------------
	python3 -m venv ./plot/venv;
	# Upgrade pip
	. ./plot/venv/bin/activate; pip install --upgrade pip;
	# Generic tools
	. ./plot/venv/bin/activate; pip install dill;
	. ./plot/venv/bin/activate; pip install pyyaml;
	. ./plot/venv/bin/activate; pip install pytimedinput;
	. ./plot/venv/bin/activate; pip install numpy;
	. ./plot/venv/bin/activate; pip install scipy;
	. ./plot/venv/bin/activate; pip install sympy;
	. ./plot/venv/bin/activate; pip install importlib_resources;
	. ./plot/venv/bin/activate; pip install seaborn;
	@printf "\n";



get_cms_od:
	@if [ -f "./write/data/cms_jet_run2011A.opendata.txt" ];\
		then printf "CMS 2011A Jet Primary Dataset found. Use \`make get_cms_od_force\` to re-download anyway";\
		printf "\n";\
	else\
		$(MAKE) get_cms_od_force;\
	fi


get_cms_od_force:
	# =======================================
	# Getting CMS 2011A Jet Primary Dataset
	# =======================================
	wget -O ./write/data/cms_jet_run2011A.opendata.txt "https://github.com/abudhraj/FastEEC/releases/download/0.1/data.txt";
	@if [ "$$(uname)" = "Darwin" ]; then \
		sed -i '' 's|const std::string cms_jets_file = .*|const std::string cms_jets_file = "$(PWD)/write/data/cms_jet_run2011A.opendata.txt";|' write/include/opendata_utils.h; \
	elif [ "$$(uname)" = "Linux" ]; then \
		sed -i 's|const std::string cms_jets_file = .*|const std::string cms_jets_file = "$(PWD)/write/data/cms_jet_run2011A.opendata.txt";|' write/include/opendata_utils.h; \
	else \
		echo "Unsupported OS: $$(uname). Please see `get_cms_od` in the Makefile or download the CMS Open Data dataset manually from `https://github.com/abudhraj/FastEEC/releases/download/0.1/data.txt`"; exit 1; \
    fi


remove_venv:
	@printf "Removing virtual environment containing libraries for plotting"
	@rm -rf ./plot/venv
	@printf "\n"


# =======================================
# Compiling C++ Tools:
# =======================================
# Telling Make to compile C++ code with g++, using pythia and fastjet libraries

write_tools:
	# #=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
	# Compiling all C++ tools
	# #=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
	@printf "\n";
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	# Basic Jet Properties
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	@$(MAKE) jet_properties;
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	# New Angles on Energy Correlators
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	mkdir -p write/new_enc;
	@$(MAKE) new_encs;

jet_properties:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing histograms of basic jet properties:
	# =======================================================
	# Compiling `write/src/jet_properties.cc` to the executable `write/jet_properties`
	$(CXX) \
		-o write/jet_properties \
		write/src/jet_properties.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/opendata_utils.cc\
		$(CXX_COMMON);
	@printf "\n"


groomed_properties:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing histograms of basic groomed properties:
	# =======================================================
	# Compiling `write/src/groomed_properties.cc` to the executable `write/groomed_properties`
	$(CXX) \
		-o write/groomed_properties \
		write/src/groomed_properties.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"

mpi_properties:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing histograms of basic mpi properties:
	# =======================================================
	# Compiling `write/src/mpi_properties.cc` to the executable `write/mpi_properties`
	$(CXX) \
		-o write/mpi_properties \
		write/src/mpi_properties.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"

new_encs:
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	# New Angles on Energy Correlators
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	@if [ -f "./write/new_enc/2particle" ];\
		then printf "New (two particle) ENC executable exists. Please run 'make new_enc_2particle' to recompile anyway.\n";\
	else\
		printf "\n"; \
		$(MAKE) new_enc_2particle;\
	fi
	@if [ -f "./write/new_enc/3particle" ];\
		then printf "New (three particle) ENC executable exists. Please run 'make new_enc_3particle' to recompile anyway.\n";\
	else\
		printf "\n"; \
		$(MAKE) new_enc_3particle;\
	fi
	@if [ -f "./write/new_enc/4particle" ];\
		then printf "New (four particle) ENC executable exists. Please run 'make new_enc_4particle' to recompile anyway.\n";\
	else\
		printf "\n"; \
		$(MAKE) new_enc_4particle;\
	fi
	@if [ -f "./write/new_enc/2special" ];\
		then printf "New (''2 special'' particle) ENC executable exists. Please run 'make old_enc_3particle' to recompile anyway.\n";\
	else\
		printf "\n"; \
		$(MAKE) new_enc_2special;\
	fi
	@if [ -f "./write/new_enc/old_3particle" ];\
		then printf "Old (three particle) ENC executable exists. Please run 'make old_enc_3particle' to recompile anyway.\n";\
	else\
		printf "\n"; \
		$(MAKE) old_enc_3particle;\
	fi

new_encs_force:
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	# New Angles on Energy Correlators
	# =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
	@printf "\n"; \
	$(MAKE) new_enc_2particle;\
	printf "\n"; \
	$(MAKE) new_enc_3particle;\
	printf "\n"; \
	$(MAKE) new_enc_4particle;\
	printf "\n"; \
	$(MAKE) new_enc_2special;\
	printf "\n"; \
	$(MAKE) old_enc_3particle;


penc_example:
	# =======================================================
	# Compiling c++ code for writing PENC example:
	# =======================================================
	$(CXX) \
		-o examples/write_penc \
		write/src/examples/penc_example.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_FASTJET);
	@printf "\n"


re3c_example:
	# =======================================================
	# Compiling c++ code for writing RE3C example:
	# =======================================================
	$(CXX) \
		-o examples/write_re3c \
		write/src/examples/re3c_example.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_FASTJET);
	@printf "\n"



new_enc_2particle:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing (two particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_2particle.cc` to the executable `write/new_enc/2particle`
	$(CXX) \
		-o write/new_enc/2particle \
		write/src/new_enc_2particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"

penc:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing PENC histograms:
	# =======================================================
	# From `write/src/penc.cc` to the executable `write/new_enc/penc`
	$(CXX) \
		-o bin/compute_penc \
		write/src/penc.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


new_enc_3particle:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing (three particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_3particle.cc` to the executable `write/new_enc/3particle`
	$(CXX) \
		-o write/new_enc/3particle \
		write/src/new_enc_3particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


root_enc_3particle:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing (three particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_3particle.cc` to the executable `write/new_enc/3particle`
	. $(SOFTWARE_DIR)/root/root_install/bin/thisroot.sh && \
	$(CXX) \
		-o write/new_enc/root_3particle \
		write/src/root_enc_3particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON) \
		`root-config --cflags --glibs --ldflags`;
	@printf "\n"


new_enc_4particle:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing (four particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_4particle.cc` to the executable `write/new_enc/4particle`
	$(CXX) \
		-o write/new_enc/4particle \
		write/src/new_enc_4particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


new_enc_2special:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing (four particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_4particle.cc` to the executable `write/new_enc/4particle`
	$(CXX) \
		-o write/new_enc/2special \
		write/src/new_enc_2special.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


old_enc_3particle:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling for writing Old (3 particle) ENC histograms:
	# =======================================================
	# Compiling `write/src/old_enc_3particle.cc` to the executable `write/new_enc/old_3particle`
	$(CXX) \
		-o write/new_enc/old_3particle \
		write/src/old_enc_3particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


new_enc_ue:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling code for UE PENC histograms:
	# =======================================================
	# Compiling `write/src/new_enc_2particle_UE.cc` to the executable `write/new_enc/ue`
	$(CXX) \
		-o write/new_enc/ue \
		write/src/new_enc_2particle_UE.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"



new_enc_benchmarks:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for benchmarking ENC histograms:
	# =======================================================
	$(CXX) \
		-o write/benchmark/new_enc_2particle \
		write/src/benchmark/new_enc_2particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"
	$(CXX) \
		-o write/benchmark/new_enc_3particle \
		write/src/benchmark/new_enc_3particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"
	$(CXX) \
		-o write/benchmark/new_enc_4particle \
		write/src/benchmark/new_enc_4particle.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/enc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"



ewocs:
	@$(PYTHIA_WARNING)
	# =======================================================
	# Compiling c++ code for writing EWOC histograms:
	# =======================================================
	# Compiling `write/src/ewocs.cc` to the executable `write/ewocs`
	$(CXX) \
		-o write/ewocs \
		write/src/ewocs.cc \
		write/src/utils/general_utils.cc write/src/utils/cmdln.cc write/src/utils/jet_utils.cc write/src/utils/pythia2fastjet.cc write/src/utils/pythia_cmdln.cc write/src/utils/ewoc_utils.cc write/src/utils/opendata_utils.cc \
		$(CXX_COMMON);
	@printf "\n"


# =======================================
clean:
	rm write/ewocs
	rm write/jet_properties
	rm write/new_enc/*
	rm write/benchmark/*
# =======================================
#

# =======================================
# Dependencies
# =======================================
install_dependencies:
	# #=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
	# Installing dependencies
	# #=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
	@if [ -d "$(SOFTWARE_INSTALL_DIR)" ];\
		then printf "Found software directory.\n";\
	else\
		mkdir -p $(SOFTWARE_INSTALL_DIR);\
	fi
	@printf "\n"
	# =======================================
	# Installing Pythia
	# =======================================
	@if [ -d "$(PYTHIA_INSTALL_DIR)" ];\
		then printf "Found Pythia directory. Not reinstalling.\n";\
	else\
		$(MAKE) download_pythia; $(MAKE) make_pythia;\
	fi
	@printf "\n"
	# =======================================
	# Installing FastJet
	# =======================================
	@if [ -d "$(FASTJET_INSTALL_DIR)" ];\
		then printf "Found FastJet directory. Not reinstalling.\n";\
	else\
		$(MAKE) download_fastjet; $(MAKE) make_fastjet;\
	fi
	@printf "\n"


# ---------------------------------------
# Installing Pythia
# ---------------------------------------
download_pythia:
	cd $(SOFTWARE_INSTALL_DIR) && \
	curl -O $(PYTHIA_URL) && \
	tar zxvf pythia$(PYTHIA_VERSION).tgz && \
	rm pythia$(PYTHIA_VERSION).tgz

make_pythia:
	cd $(PYTHIA_INSTALL_DIR) && $(MAKE)


# ---------------------------------------
# Installing FastJet
# ---------------------------------------
download_fastjet:
	cd $(SOFTWARE_INSTALL_DIR) && \
	curl -O $(FASTJET_URL) && \
	tar zxvf fastjet-$(FASTJET_VERSION).tar.gz && \
	rm fastjet-$(FASTJET_VERSION).tar.gz

make_fastjet:
	@printf "Making FastJet (without fastjet-contrib)"
	cd $(FASTJET_INSTALL_DIR) && \
	./configure --prefix=$$PWD/../fastjet-install && \
	$(MAKE) && \
	$(MAKE) make check && \
	$(MAKE) make install
