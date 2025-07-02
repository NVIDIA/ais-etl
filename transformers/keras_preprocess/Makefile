# Default image tag is 'latest'
TAG := latest
ifeq ($(GIT_TEST), true)
	TAG := test
endif

REGISTRY_URL ?= docker.io/aistorage
IMAGE_NAME ?= transformer_keras_preprocess

.PHONY: build push all

build:
	docker build -t $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG) .

push: build
	docker push $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)

all: build push