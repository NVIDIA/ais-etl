#!/bin/bash

docker build -t ${DOCKER_REGISTRY_URL:-"localhost:5000"}/echo_data_server:v1 .
