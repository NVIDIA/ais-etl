REGISTRY_URL ?= docker.io/aistorage

all: build push

ifeq ($(GIT_TEST),true)
build:
	docker build -t $(REGISTRY_URL)/transformer_echo:test .

push:
	docker push $(REGISTRY_URL)/transformer_echo:test

else
build:
	docker build -t $(REGISTRY_URL)/transformer_echo:latest .

push:
	docker push $(REGISTRY_URL)/transformer_echo:latest

endif