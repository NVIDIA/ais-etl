REGISTRY_URL ?= docker.io/aistorage

all: build push

ifeq ($(GIT_TEST),true)
build:
	docker build -t $(REGISTRY_URL)/transformer_hello_world:test .

push:
	docker push $(REGISTRY_URL)/transformer_hello_world:test

else
build:
	docker build -t $(REGISTRY_URL)/transformer_hello_world:latest .

push:
	docker push $(REGISTRY_URL)/transformer_hello_world:latest

endif