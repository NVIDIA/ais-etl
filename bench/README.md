# Benchmarking AIStore ETL

You have the flexibility to customize your own ETL pipelines in AIStore. You can choose the language (Python, Go, etc.) and web server implementation. With so many options, it can get complicated to select the right ones. 

This directory provides sample web server implementations and benchmarks their performance in terms of request handling capacity.

## Web Servers

There are many frameworks available for running web servers. Below is a comparison of web servers, frameworks, languages, and locations of basic implementations that can run them.

| Language | Framework | Web Server | Location | Remarks |
|-|-|-|-|-|  
| Python | - | ThreadedHTTPServer | [/http-server](http-server/) | Built-in to Python, very easy to implement, doesn't scale well |
| Python | Flask | Flask Built-in Webserver | [/flask-server](flask-server/) | Built-in flask webserver, not suited for production |
| Python | Flask | [Gunicorn](https://gunicorn.org/) | [/flask-server](flask-server/) | Python WSGI HTTP server, scales well |
| Python | [FastAPI](https://fastapi.tiangolo.com/) | [Uvicorn](https://www.uvicorn.org/) | [/fast-api](fast-api/) | ASGI web server implementation for Python |
| Python | [FastAPI](https://fastapi.tiangolo.com/) | [Uvicorn](https://www.uvicorn.org/) + [Uvicorn](https://www.uvicorn.org/) | [/fast-api](fast-api/) | Gunicorn manages multiple Uvicorn processes |
| Go | Go | Net/HTTP Server | [/go-http-server](go-http-server/) | Built-in to Go, easy to implement, scales well |

To benchmark these servers on your infrastructure, you can use the [client](client). The client is based on [Locust](https://locust.io/), a simple open source load testing tool.

Here are sample results from a 12 core/16GB machine:

| Language | Framework | Web Server | Location | Avg. Requests Per Second |
|-|-|-|-|-|
| Python | - | ThreadedHTTPServer | [/http-server](http-server/) | 1020 |  
| Python | Flask | Flask Built-in Webserver | [/http-server](http-server/) | 950 |
| Python | Flask | [Gunicorn](https://gunicorn.org/) | [/flask-server](flask-server/) | 1060 |
| Python | [FastAPI](https://fastapi.tiangolo.com/) | [Uvicorn](https://www.uvicorn.org/) | [/fast-api](fast-api/) | 1620 |
| Python | [FastAPI](https://fastapi.tiangolo.com/) | [Uvicorn](https://www.uvicorn.org/) + [Gunicorn](https://gunicorn.org/) | [/fast-api](fast-api/) | 1670 | 
| Go | Go | Net/HTTP Server | [/go-http-server](go-http-server/) | 1675 |

An important consideration is how your ETL container pods will communicate with the AIStore cluster. There are several [communication mechanisms](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms) to choose from depending on your needs. There's no one perfect solution - pick the mechanism that best fits your ETL workflow.

