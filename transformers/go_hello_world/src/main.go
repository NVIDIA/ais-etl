// Package main is implementation of a simple hello world transformation in golang.
/*
 * Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
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
	logger *log.Logger
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

	logger = log.New(os.Stdout, "[HelloWorld] ", log.LstdFlags|log.Lmicroseconds|log.Lshortfile)

	http.HandleFunc("/", helloWorldHandler)
	http.HandleFunc("/health", healthHandler)

	logger.Printf("Starting hello world transformer at %s", endpoint)
	logger.Fatal(http.ListenAndServe(endpoint, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, fmt.Sprintf("Invalid HTTP method %q", r.Method), http.StatusBadRequest)
		return
	}
	if _, err := w.Write([]byte("OK")); err != nil {
		logError(err, fmt.Sprintf("Error writing response for %q", r.URL.EscapedPath()))
	}
}

func helloWorldHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		putHandler(w, r)
	case http.MethodGet:
		geHandler(w, r)
	default:
		http.Error(w, fmt.Sprintf("Invalid HTTP method %q, expected %q or %q", r.Method, http.MethodPut, http.MethodGet), http.StatusBadRequest)
	}
}

// PUT /
func putHandler(w http.ResponseWriter, r *http.Request) {
	escapePath := r.URL.EscapedPath()

	defer r.Body.Close()
	readContent(w, r.Body, r.ContentLength, escapePath)
	writeHelloWorld(w, escapePath)
}

// GET /
func geHandler(w http.ResponseWriter, r *http.Request) {
	if aisTargetURL == "" {
		http.Error(w, "Missing AIS_TARGET_URL environment variable", http.StatusBadRequest)
		return
	}

	escapePath := r.URL.EscapedPath()
	path := strings.TrimPrefix(escapePath, "/")

	resp, err := client.Get(aisTargetURL + "/" + path)
	if err != nil {
		logAndRespondError(w, err, fmt.Sprintf("GET to AIStore failed for  %q", escapePath), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()
	readContent(w, resp.Body, r.ContentLength, r.URL.EscapedPath())
	writeHelloWorld(w, escapePath)

}

func logAndRespondError(w http.ResponseWriter, err error, msg string, status int) {
	logError(err, msg)
	http.Error(w, msg, status)
}

func logError(err error, msg string) {
	logger.Printf("%s: %v", msg, err)
}

func readContent(w http.ResponseWriter, body io.ReadCloser, contentLength int64, path string) {
	n, err := io.Copy(io.Discard, body)

	if err != nil {
		logAndRespondError(w, err, fmt.Sprintf("Error reading request body for %q", path), http.StatusBadRequest)
		return
	}
	if contentLength > 0 && contentLength != int64(n) {
		logAndRespondError(w, nil, fmt.Sprintf("Content length mismatch for %q", path), http.StatusBadRequest)
		return
	}
}

func writeHelloWorld(w http.ResponseWriter, path string) {
	if _, err := w.Write([]byte("Hello World!")); err != nil {
		logError(err, fmt.Sprintf("Error writing response for %q", path))
	}
}
