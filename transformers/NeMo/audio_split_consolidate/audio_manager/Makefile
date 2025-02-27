# Default image tag is 'latest'
TAG := latest

REGISTRY_URL ?= docker.io/aistorage

ifeq ($(GIT_TEST), true)
	TAG := test
endif

all: build push

build:
	docker build -t $(REGISTRY_URL)/transformer_audio_manager:$(TAG) .

push:
	docker push $(REGISTRY_URL)/transformer_audio_manager:$(TAG)
