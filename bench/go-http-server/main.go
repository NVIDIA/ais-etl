/*
 * A basic webserver using golang
 *
 * Steps to run:
 * $ go run main.go
 *
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
)

var (
	endpoint string

	logger *log.Logger
)

func initVars(ipAddress string, port int) {
	endpoint = fmt.Sprintf("%s:%d", ipAddress, port)
}

func main() {
	var (
		ipAddressArg = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		portArg      = flag.Int("p", 8000, "Specify the port on which the server listens")
	)

	flag.Parse()

	initVars(*ipAddressArg, *portArg)

	logger = log.New(os.Stdout, "[TestServer] ", log.LstdFlags|log.Lmicroseconds|log.Lshortfile)

	http.HandleFunc("/", requestHandler)

	logger.Printf("Starting hello world transformer at %s", endpoint)
	logger.Fatal(http.ListenAndServe(endpoint, nil))
}

func requestHandler(w http.ResponseWriter, r *http.Request) {
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
	writeContent(w, escapePath)
}

// GET /
func geHandler(w http.ResponseWriter, r *http.Request) {
	writeContent(w, r.URL.Path)
}

func logAndRespondError(w http.ResponseWriter, err error, msg string, status int) {
	logError(err, msg)
	http.Error(w, msg, status)
}

func logError(err error, msg string) {
	logger.Printf("%s: %v\n", msg, err)
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

func writeContent(w http.ResponseWriter, path string) {
	if _, err := w.Write([]byte("Hello World!")); err != nil {
		logError(err, fmt.Sprintf("Error writing response for %q", path))
	}
}
