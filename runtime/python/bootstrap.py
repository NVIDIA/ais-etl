#!/usr/bin/env python3
"""
ETL Container Launcher

This script bootstraps an ETL container by:
1. Deserializing a base64-encoded ETLServer subclass passed via the ETL_CLASS_PAYLOAD env var.
2. Determining the server type (FastAPI, Flask, or HTTPMultiThreaded).
3. Installing any required Python packages (via the PACKAGES env var).
4. Starting the ETL server either in-process (for HTTPMultiThreaded) or by spawning an external process.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import sys
import logging
import subprocess
from typing import Type

from aistore.sdk.etl.webserver.base_etl_server import ETLServer
from aistore.sdk.etl.webserver.fastapi_server import FastAPIServer
from aistore.sdk.etl.webserver.flask_server import FlaskServer
from aistore.sdk.etl.webserver.http_multi_threaded_server import HTTPMultiThreadedServer
from aistore.sdk.etl.webserver.utils import deserialize_class

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
NUM_WORKERS: int = int(os.getenv("NUM_WORKERS", "6"))
ETL_CLASS_PAYLOAD: str = os.getenv("ETL_CLASS_PAYLOAD", "")
PACKAGES: str = os.getenv("PACKAGES", "")
OS_PACKAGES: str = os.getenv("OS_PACKAGES", "")

if not ETL_CLASS_PAYLOAD:
    print("ERROR: ETL_CLASS_PAYLOAD is not set", file=sys.stderr)
    sys.exit(1)

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
log = logging.getLogger("bootstrap")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def install(package: str) -> None:
    """Install a pip package. Exit if installation fails."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError as e:
        log.error("Failed to install package '%s': %s", package, e)
        sys.exit(1)


def install_system(pkgs: str) -> None:
    """
    Install system packages via apk (Alpine).

    Some python packages require system dependencies that must be installed
    via the system package manager (apk for Alpine Linux).
    This function installs the specified packages using `apk add --no-cache`.
    """
    pkg_list = [p.strip() for p in pkgs.split(",") if p.strip()]
    if not pkg_list:
        return
    cmd = ["apk", "add", "--no-cache"] + pkg_list
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        log.error("Failed to install system packages '%s': %s", pkg_list, e)
        sys.exit(1)


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    """Entry point to set up and run the ETL server."""
    # 1) Install dependencies if specified
    if PACKAGES:
        log.info("Installing required packages: %s", PACKAGES)
        for package in PACKAGES.split(","):
            install(package.strip())

    if OS_PACKAGES:
        log.info("Installing system packages: %s", OS_PACKAGES)
        install_system(OS_PACKAGES)

    # 2) Deserialize ETL class
    try:
        # pylint: disable=invalid-name
        ETLClass: Type[ETLServer] = deserialize_class(ETL_CLASS_PAYLOAD)
    except Exception as e:
        log.error("Failed to decode ETL class payload: %s", e)
        sys.exit(1)

    # 3) Instantiate ETL server
    try:
        server = ETLClass()
    except Exception as e:
        log.error("Failed to instantiate ETLServer: %s", e)
        sys.exit(1)

    # 5) Start server
    if isinstance(server, HTTPMultiThreadedServer):
        log.info("Starting HTTP server in-process")
        server.start()
        return

    if isinstance(server, FastAPIServer):
        cmd = [
            "uvicorn",
            "server:server.app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--workers",
            str(NUM_WORKERS),
            "--log-level",
            "info",
            "--ws-max-size",
            "17179869184",
            "--ws-ping-interval",
            "0",
            "--ws-ping-timeout",
            "86400",
            "--no-access-log",
        ]
    elif isinstance(server, FlaskServer):
        cmd = [
            "gunicorn",
            "server:server.app",
            "--bind",
            "0.0.0.0:8000",
            "--workers",
            str(NUM_WORKERS),
            "--log-level",
            "debug",
        ]
    else:
        log.error("Unsupported server type: %s", server.__class__.__name__)
        sys.exit(1)

    log.info("Launching server: %s", " ".join(cmd))
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
