#!/bin/bash

docker build -t ${DOCKER_REGISTRY_URL:-"localhost:5000"}/transformer_echo:latest .
