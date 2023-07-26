REGISTRY_URL ?= docker.io/aistorage

all: build push

ifeq ($(GIT_TEST),true)
build:
	docker build -t $(REGISTRY_URL)/transformer_compress:test .

push:
	docker push $(REGISTRY_URL)/transformer_compress:test

else
build:
	docker build -t $(REGISTRY_URL)/transformer_compress:latest .

push:
	docker push $(REGISTRY_URL)/transformer_compress:latest

endif