#!/bin/bash

docker build -t ${DOCKER_REGISTRY_URL:-"localhost:5000"}/transformer_hello_world:latest .
