REGISTRY_URL ?= docker.io

all: build push

build:
	docker build -t $(REGISTRY_URL)/aistore/transformer_echo_go:latest .

push:
	docker push $(REGISTRY_URL)/aistore/transformer_echo_go:latest
