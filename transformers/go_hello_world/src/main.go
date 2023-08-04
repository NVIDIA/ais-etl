// Package main is implementation of a simple hello world transformation in golang.
/*
 * Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
)

var (
	aisTargetURL string
	endpoint     string

	client *http.Client
)

func initVars(ipAddress string, port int) {
	endpoint = fmt.Sprintf("%s:%d", ipAddress, port)
	aisTargetURL = os.Getenv("AIS_TARGET_URL")
	client = &http.Client{}
}

func main() {
	var (
		ipAddressArg = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		portArg      = flag.Int("p", 8000, "Specify the port on which the server listens")
	)

	flag.Parse()

	initVars(*ipAddressArg, *portArg)

	http.HandleFunc("/", helloWorldHandler)
	http.HandleFunc("/health", healthHandler)

	log.Printf("Starting hello world transformer at %s", endpoint)
	log.Fatal(http.ListenAndServe(endpoint, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		w.WriteHeader(http.StatusOK)
		if _, err := w.Write([]byte("OK")); err != nil {
			logErrorf("%v", err)
		}
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}

}

func helloWorldHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		helloWorldPutHandler(w, r)
	case http.MethodGet:
		helloWorldGetHandler(w, r)
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

// PUT /
func helloWorldPutHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Header().Set("Content-type", "text/plain")
	if _, err := w.Write([]byte("Hello World!")); err != nil {
		logErrorf("%v", err)
	}
}

// GET /
func helloWorldGetHandler(w http.ResponseWriter, r *http.Request) {
	if aisTargetURL == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	path := strings.TrimPrefix(r.URL.EscapedPath(), "/")
	if path == "health" {
		return
	}

	_, err := wrapHttpError(client.Get(fmt.Sprintf("%s/%s", aisTargetURL, path)))
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, "GET to AIStore failed; err %v", err)
		return
	}
	w.WriteHeader(http.StatusOK)
	w.Header().Set("Content-type", "text/plain")
	if _, err := w.Write([]byte("Hello World!")); err != nil {
		logErrorf("%v", err)
	}
}
