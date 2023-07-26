REGISTRY_URL ?= docker.io/aistorage

all: build push

ifeq ($(GIT_TEST),true)
build:
	docker build -t $(REGISTRY_URL)/transformer_tar2tf:test .

push:
	docker push $(REGISTRY_URL)/transformer_tar2tf:test

else
build:
	docker build -t $(REGISTRY_URL)/transformer_tar2tf:latest .

push:
	docker push $(REGISTRY_URL)/transformer_tar2tf:latest

endif