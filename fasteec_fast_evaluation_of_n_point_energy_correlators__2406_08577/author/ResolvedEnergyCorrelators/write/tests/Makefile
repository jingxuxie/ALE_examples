-include ../../Makefile.inc

.PHONY : test_hist test_progressbar test_readwrite

test_hist: test_hist.cc
	@g++ test_hist.cc ../src/utils/general_utils.cc -o test_hist
	@./test_hist

test_progressbar: test_progressbar.cc
	@g++ test_progressbar.cc ../src/utils/general_utils.cc -o test_progressbar
	@./test_progressbar

test_readwrite: test_readwrite.cc
	@$(CXX) test_readwrite.cc ../src/utils/opendata_utils.cc \
		-o test_readwrite \
		$(CXX_COMMON);
