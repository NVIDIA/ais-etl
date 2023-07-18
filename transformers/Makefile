SUBDIRS := $(wildcard */.)

all: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@

test:
	cd tests && pip install -r "requirements.txt" && PYTHONWARNINGS="ignore" python3 -m unittest -v test_transformers.py
