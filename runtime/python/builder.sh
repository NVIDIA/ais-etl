#!/bin/bash

set -e

# Defines mapping: "runtime name" -> "python version".
declare -A python_versions=(
  [3.10]="3.10"
  [3.11]="3.11"
  [3.12]="3.12"
  [3.13]="3.13"
  [3.14]="3.14"
)

# extra apk packages needed at install time, per runtime, see Dockerfile
# TODO: remove once a new aistore version is added
declare -A build_deps=(
  [3.14]="gcc musl-dev"
)

for runtime_name in "${!python_versions[@]}"; do
  echo "BUILDING AND PUSHING ${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}"
  echo "PYTHON_VERSION=${python_versions[${runtime_name}]}"
	docker build --pull --no-cache \
	  -t "${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}" \
	  --build-arg PYTHON_VERSION="${python_versions[${runtime_name}]}" \
	  --build-arg BUILD_DEPS="${build_deps[${runtime_name}]:-}" \
	  .
	docker push "${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}"
done
