# Default image tag is 'latest'
TAG := latest

# TODO: change to aistorage
REGISTRY_URL ?= docker.io/aistorage

all: build push

build:
	docker build -t $(REGISTRY_URL)/transformer_audio_manager:$(TAG) .

push:
	docker push $(REGISTRY_URL)/transformer_audio_manager:$(TAG)
