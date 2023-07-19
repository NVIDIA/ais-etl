REGISTRY_URL ?= docker.io/aistorage

all: build push

build:
	docker build -t $(REGISTRY_URL)/transformer_md5:latest .

push:
	docker push $(REGISTRY_URL)/transformer_md5:latest
