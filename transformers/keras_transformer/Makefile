REGISTRY_URL ?= docker.io/aistorage

all: build push

build:
	docker build -t $(REGISTRY_URL)/transformer_keras:latest .

push:
	docker push $(REGISTRY_URL)/transformer_keras:latest
