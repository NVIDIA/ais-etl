ARG PYTHON_VERSION

FROM docker.io/library/python:${PYTHON_VERSION}-alpine

RUN pip3 install --upgrade aistore[etl]>=1.15.1

# Set working directory
RUN mkdir /code
WORKDIR /code

# Copy app code
COPY bootstrap.py server.py ./

# Environment setup
ENV PYTHONUNBUFFERED=1

# Expose the default port
EXPOSE 8000

# Set default entrypoint
ENTRYPOINT ["python", "bootstrap.py"]