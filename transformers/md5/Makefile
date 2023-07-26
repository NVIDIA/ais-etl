REGISTRY_URL ?= docker.io/aistorage

all: build push

ifeq ($(GIT_TEST),true)
build:
	docker build -t $(REGISTRY_URL)/transformer_md5:test .

push:
	docker push $(REGISTRY_URL)/transformer_md5:test

else
build:
	docker build -t $(REGISTRY_URL)/transformer_md5:latest .

push:
	docker push $(REGISTRY_URL)/transformer_md5:latest

endif