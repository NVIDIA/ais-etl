REGISTRY_URL ?= docker.io

all: build push

build:
	docker build -t $(REGISTRY_URL)/aistore/transformer_md5:latest .

push:
	docker push $(REGISTRY_URL)/aistore/transformer_md5:latest
