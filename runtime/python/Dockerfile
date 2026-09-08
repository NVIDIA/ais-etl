ARG PYTHON_VERSION

FROM docker.io/library/python:${PYTHON_VERSION}-alpine

# aistore 1.26.0 pins xxhash==3.5.0, which has no cp314 wheels, so pip compiles
# it from source
# TODO: remove BUILD_DEPS once the next aistore release ships with xxhash>=4.0.1
ARG BUILD_DEPS=""
RUN if [ -n "$BUILD_DEPS" ]; then apk add --no-cache --virtual .build-deps $BUILD_DEPS; fi \
 && pip3 install --upgrade "aistore[etl]>=1.24.0" \
 && if [ -n "$BUILD_DEPS" ]; then apk del .build-deps; fi

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY bootstrap.py server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000

# Raise the open file descriptor soft limit to match the hard limit set by
# the container runtime (e.g. CRI-O). The default soft limit of 1024 is too
# low for high-concurrency ETL workloads and causes "[Errno 24] No file
# descriptors available" errors under load.
ENTRYPOINT ["sh", "-c", "ulimit -n $(ulimit -Hn) && exec python bootstrap.py"]