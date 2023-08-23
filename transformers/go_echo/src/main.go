// Package main is implementation of ID (echo) transformation in golang.
/*
 * Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"flag"
	"fmt"
	"io"
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

	http.HandleFunc("/", echoHandler)
	http.HandleFunc("/health", healthHandler)

	log.Printf("Starting echo transformer at %s", endpoint)
	log.Fatal(http.ListenAndServe(endpoint, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Running"))
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}

}

func echoHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		echoPutHandler(w, r)
	case http.MethodGet:
		echoGetHandler(w, r)
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

// PUT /
func echoPutHandler(w http.ResponseWriter, r *http.Request) {
	setResponseHeaders(w.Header(), r.ContentLength)
	if _, err := io.Copy(w, r.Body); err != nil {
		logErrorf("%v", err)
	}
}

// GET /
func echoGetHandler(w http.ResponseWriter, r *http.Request) {
	if aisTargetURL == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	path := strings.TrimPrefix(r.URL.EscapedPath(), "/")
	if path == "health" {
		return
	}

	resp, err := wrapHttpError(client.Get(fmt.Sprintf("%s/%s", aisTargetURL, path)))
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, "GET to AIStore failed; err %v", err)
		return
	}

	if _, err := io.Copy(w, resp.Body); err != nil {
		logErrorf("%v", err)
	}
}
