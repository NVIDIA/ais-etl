REGISTRY_URL ?= docker.io

all: build2 build3 push2 push3

all2: build2 push2
all3: build3 push3

build2:
	docker build --pull --no-cache -t $(REGISTRY_URL)/aistore/runtime_python:2$$RUNTIME_TAG_MODIFIER -f Dockerfile.2 .

push2:
	docker push $(REGISTRY_URL)/aistore/runtime_python:2$$RUNTIME_TAG_MODIFIER

build3:
	docker build --pull --no-cache -t $(REGISTRY_URL)/aistore/runtime_python:3$$RUNTIME_TAG_MODIFIER -f Dockerfile.3 .

push3:
	docker push $(REGISTRY_URL)/aistore/runtime_python:3$$RUNTIME_TAG_MODIFIER
