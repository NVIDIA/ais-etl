SUBDIRS := compress echo go_echo hello_world md5 tar2tf keras_preprocess ffmpeg

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

ifeq ($(KERAS_ENABLE), false)
SUBDIRS := $(filter-out keras_preprocess,$(SUBDIRS))
endif

ifeq ($(FFMPEG_ENABLE), false)
SUBDIRS := $(filter-out ffmpeg,$(SUBDIRS))
endif

all: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@ all

common_deps:
	pip install -r tests/requirements.txt --quiet

test: common_deps
	cd tests && pytest -v .
