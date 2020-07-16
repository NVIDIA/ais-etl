#!/bin/bash

docker build -t ${DOCKER_REGISTRY_URL:-"localhost:5000"}/md5_server:v1 .
