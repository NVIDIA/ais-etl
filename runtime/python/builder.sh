#!/bin/bash

set -e

# Defines mapping: "runtime name" -> "python version".
declare -A python_versions=(
  [3.9]="3.9"
  [3.10]="3.10"
  [3.11]="3.11"
  [3.12]="3.12"
  [3.13]="3.13"
)

for runtime_name in "${!python_versions[@]}"; do
  echo "BUILDING AND PUSHING ${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}"
  echo "PYTHON_VERSION=${python_versions[${runtime_name}]}"
	docker build --pull --no-cache \
	  -t "${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}" \
	  --build-arg PYTHON_VERSION="${python_versions[${runtime_name}]}" \
	  .
	docker push "${REGISTRY_URL}/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}"
done
