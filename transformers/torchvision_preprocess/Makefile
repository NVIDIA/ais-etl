# Default image tag is 'latest'
TAG := latest
ifeq ($(GIT_TEST), true)
	TAG := test
endif

REGISTRY_URL ?= docker.io/aistorage

IMAGE_NAME := transformer_torchvision

.PHONY: all build push clean test test-pytest

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
		-e TRANSFORM='{"Resize": {"size": [224, 224]}, "Grayscale": {"num_output_channels": 1}}' \
		-e FORMAT="JPEG" \
		$(REGISTRY_URL)/$(IMAGE_NAME):$(TAG)

test-pytest: build
	@echo "Running pytest tests in container"
	docker run --rm \
		-e AIS_TARGET_URL="http://test-target:8080" \
		-e TRANSFORM='{"Resize": {"size": [100, 100]}, "Grayscale": {"num_output_channels": 1}}' \
		-e FORMAT="JPEG" \
		$(REGISTRY_URL)/$(IMAGE_NAME):$(TAG) \
