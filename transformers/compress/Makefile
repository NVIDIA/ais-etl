# Default image tag is 'latest'
TAG := latest
ifeq ($(GIT_TEST), true)
	TAG := test
endif

REGISTRY_URL ?= docker.io/aistorage

IMAGE_NAME := transformer_compress

.PHONY: all build push clean test

all: build push

build:
	@echo "Building $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)"
	docker build -t $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG) .

push:
	@echo "Pushing $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)"
	docker push $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)

clean:
	@echo "Cleaning up local images"
	-docker rmi $(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)

test: build
	@echo "Testing container locally on port 8000"
	@echo "Setting default environment variables for testing"
	docker run --rm -p 8000:8000 \
		-e AIS_TARGET_URL="http://localhost:8080" \
		-e COMPRESS_OPTIONS='{"mode": "compress", "compression": "gzip"}' \
		$(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)
