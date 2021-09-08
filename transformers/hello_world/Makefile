REGISTRY_URL ?= docker.io

all: build push

build:
	docker build -t $(REGISTRY_URL)/aistore/transformer_hello_world:latest .

push:
	docker push $(REGISTRY_URL)/aistore/transformer_hello_world:latest
