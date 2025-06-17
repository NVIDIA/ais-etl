# AIStore ETL Python Runtime

`aistore/runtime_python` is the *default* Python-based ETL runtime container for AIStore.  
Use it with the Python SDK’s new [`init_class` decorator](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#using-init_class-python-sdk-only) to spin up your ETL servers—no need to build or maintain a custom Docker image.

---

## Why this runtime?

- **Plug-and-play**  
  Launch pure-Python ETLs without writing Dockerfiles or building images.  
- **Supported versions**  
  Python 3.9, 3.10, 3.11, 3.12, 3.13  
- **Supported extensions**  
  - Install extra PyPI packages via `PACKAGES`  
  - Install OS packages (e.g. `ffmpeg`, `openssl`) via `OS_PACKAGES`

---

## How it works

1. **Bootstrapping**  
   The container entrypoint ([`bootstrap.py`](python/bootstrap.py)) will:
   - Read environment variables:
     - `ETL_CLASS_PAYLOAD` (base64-serialized ETLServer subclass)
     - `PACKAGES` (comma-separated PyPI packages)
     - `OS_PACKAGES` (comma-separated Alpine `apk` packages)
   - Install any `OS_PACKAGES` (`apk add --no-cache ...`)
   - Install any `PACKAGES` (`pip install ...`)
   - Decode and unpickle your ETL class
   - Detect its framework (`FastAPI`, `Flask`, or simple HTTP)  
   - Launch the server (in-process or via `uvicorn` / `gunicorn`)

2. **Decorator API**  
   ```python
   from aistore import Client
   from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer
   
   client = Client("http://<ais-endpoint>")
   etl = client.etl("my-etl")
   
   @etl.init_class(
       dependencies=["numpy"],       # extra PyPI
       os_packages=["ffmpeg"],       # extra Alpine packages
       comm_type="hpush://",         # or "hpull://"
       init_timeout="3m",
       obj_timeout="30s",
       arg_type="",                  # "" or "fqn"
       direct_put=True,              # enable direct-put optimization
       NUM_WORKERS="8",              # concurrency inside the pod
   )
   class MyETL(FastAPIServer):
       def transform(self, data: bytes, path: str, etl_args: str) -> bytes:
           # your logic here
           return data.upper()
   ```

* The decorator blocks until the ETL pods are running (or `init_timeout` expires).
* Your `transform()` method will be invoked on each object chunk.

3. **Reading & writing**
   After initialization you can stream objects through your ETL:

   ```python
   from aistore.sdk.etl import ETLConfig

   # write some data
   bucket = client.bucket("demo").create()
   bucket.object("hello.txt").get_writer().put_content(b"hello ais!")

   # read through ETL
   content = bucket.object("hello.txt") \
       .get_reader(etl=ETLConfig(name=etl.name)) \
       .read_all()
   print(content)  # b"HELLO AIS!"
   ```

---

## Supported features

* **Any Python code**
  Full support for `import`, complex class hierarchies, third-party libraries.
* **Web frameworks**
  * **FastAPI** (with ASGI & WebSockets)
  * **Flask** (WSGI)
  * **HTTPMultiThreadedServer** (simple threaded HTTP)
* **Direct-put optimization**
  For bucket-to-bucket ETLs, data is sent directly to the target node (3–5× faster).
* **OS-level tools**
  Install any Alpine package (e.g. `ffmpeg`, `openssl`, `qrencode`) via `OS_PACKAGES`.

---

## Environment variables

| Name                | Description                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------- |
| `ETL_CLASS_PAYLOAD` | Base64-encoded pickled `ETLServer` subclass (injected by Python SDK)                      |
| `PACKAGES`          | Comma-separated PyPI packages to install via `pip`                                         |
| `OS_PACKAGES`       | Comma-separated Alpine packages to install via `apk add --no-cache`                                   |
| `NUM_WORKERS`       | Number of worker processes/threads inside the container (default: 4)                      |
| `AIS_TARGET_URL`    | Where to forward object GET/PUT requests (injected by AIStore at runtime)                 |

---

## When to use

* **Rapid prototyping**: spin up new ETL logic in minutes without Docker knowledge.
* **Python-only workloads**: your code depends only on PyPI (or can be packaged via `os_packages`).

If you ever need custom binaries or non-Python runtimes, you can still build your own container via `init_spec` or `init(image=..., command=...)`, but for pure-Python logic `init_class` + this runtime is all you need.
