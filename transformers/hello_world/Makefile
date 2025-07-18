TAG ?= latest
REGISTRY_URL ?= docker.io/aistorage

all: build push

build:
	docker build --no-cache -t $(REGISTRY_URL)/transformer_hello_world:$(TAG) .

push:
	docker push $(REGISTRY_URL)/transformer_hello_world:$(TAG)
