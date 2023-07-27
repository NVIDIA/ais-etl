SUBDIRS := compress echo go_echo hello_world md5 tar2tf

ifeq ($(ECHO_ENABLE), false)
SUBDIRS := $(filter-out echo,$(SUBDIRS))
endif

ifeq ($(GO_ECHO_ENABLE), false)
SUBDIRS := $(filter-out go_echo,$(SUBDIRS))
endif

ifeq ($(HELLO_WORLD_ENABLE), false)
SUBDIRS := $(filter-out hello_world,$(SUBDIRS))
endif

ifeq ($(MD5_ENABLE), false)
SUBDIRS := $(filter-out md5,$(SUBDIRS))
endif

ifeq ($(TAR2TF_ENABLE), false)
SUBDIRS := $(filter-out tar2tf,$(SUBDIRS))
endif

ifeq ($(COMPRESS_ENABLE), false)
SUBDIRS := $(filter-out compress,$(SUBDIRS))
endif

all: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@ all

test:
	cd tests && pip install -r "requirements.txt" && python3 -m unittest -v
