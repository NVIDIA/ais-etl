#!/bin/bash

set -e

declare -A python_versions=(
  [2]="2.7.18"
  [3]="3.8.5"
  [3.6]="3.6"
  [3.8]="3.8"
  [3.10]="3.10"
);

for version_name in "${!python_versions[@]}"; do
	docker build --pull --no-cache \
	  -t "${REGISTRY_URL}/aistore/runtime_python:${version_name}${RUNTIME_TAG_MODIFIER}" \
	  --build-arg PYTHON_VERSION="${python_versions[${version_name}]}" \
	  .
	docker push "${REGISTRY_URL}/aistore/runtime_python:${version_name}${RUNTIME_TAG_MODIFIER}"
done
