.PHONY: setup clean

setup:
	mkdir -p output
	@$(MAKE) get_cms_od -C ..
	@printf "\n"
	@$(MAKE) penc_example -C ..
	@printf "\n"
	@$(MAKE) re3c_example -C ..
	@printf "\n"
	@chmod +x visualize_pencs.py
	@chmod +x visualize_re3c.py
	@printf "#!/usr/bin/env bash\n./write_penc --weights 1 4 9 49 99\n./visualize_pencs.py\nopen output/penc_example.png" > penc_example;
	@printf "#!/usr/bin/env bash\n./write_re3c\n./visualize_re3c.py\nmv output/re3c_example_nus_1-000000_1-000000.png output/re3c_example.png\nopen output/re3c_example.png" > re3c_example;
	@chmod +x penc_example
	@chmod +x re3c_example

clean:
	rm -r output;
	rm write_penc;
	rm write_re3c;
	rm penc_example;
	rm re3c_example;
