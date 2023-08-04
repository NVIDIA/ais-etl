SUBDIRS := compress echo go_echo hello_world md5 tar2tf keras_preprocess ffmpeg torchvision_preprocess

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

ifeq ($(TORCHVISION_ENABLE), false)
SUBDIRS := $(filter-out torchvision_preprocess,$(SUBDIRS))
endif

all: $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@ all

common_deps:
	pip install -r tests/requirements.txt
	pip install torchvision --index-url https://download.pytorch.org/whl/cpu

test: common_deps
	cd tests && for test_file in test_*.py; do pytest -v $$test_file; done
