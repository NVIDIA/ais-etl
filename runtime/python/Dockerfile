ARG PYTHON_VERSION

FROM docker.io/library/python:${PYTHON_VERSION}-alpine

RUN pip3 install --upgrade aistore[etl]>=1.21.1

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