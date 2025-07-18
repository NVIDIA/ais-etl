TAG ?= latest
REGISTRY_URL ?= docker.io/aistorage

all: build push

build:
	docker build -t $(REGISTRY_URL)/transformer_audio_splitter:$(TAG) .

push:
	docker push $(REGISTRY_URL)/transformer_audio_splitter:$(TAG)
