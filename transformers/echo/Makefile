REGISTRY_URL ?= docker.io

all: build push

build:
	docker build -t $(REGISTRY_URL)/aistore/transformer_echo:latest .

push:
	docker push $(REGISTRY_URL)/aistore/transformer_echo:latest
