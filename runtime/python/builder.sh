#!/bin/bash

set -e

# Defines mapping: "runtime name" -> "python version".
declare -A python_versions=(
  [3.8]="3.8"
  [3.10]="3.10"
)

for runtime_name in "${!python_versions[@]}"; do
	docker build --pull --no-cache \
	  -t "${REGISTRY_URL}/aistore/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}" \
	  --build-arg PYTHON_VERSION="${python_versions[${runtime_name}]}" \
	  .
	docker push "${REGISTRY_URL}/aistore/runtime_python:${runtime_name}${RUNTIME_TAG_MODIFIER}"
done
