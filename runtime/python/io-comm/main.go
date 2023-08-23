// Package main is an entry point to ioComm server
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
	"os/exec"
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
		ipAddressArg = flag.String("l", "0.0.0.0", "Specify the IP address on which the server listens")
		portArg      = flag.Int("p", 80, "Specify the port on which the server listens")
	)

	flag.Parse()

	initVars(*ipAddressArg, *portArg)

	http.HandleFunc("/", ioHandler)
	http.HandleFunc("/health", healthHandler)

	log.Printf("Starting io comm server at %s", endpoint)
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

func ioHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		ioPutHandler(w, r)
	case http.MethodGet:
		ioGetHandler(w, r)
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

// PUT /
func ioPutHandler(w http.ResponseWriter, r *http.Request) {
	command, ok := r.URL.Query()["command"]
	if !ok {
		invalidMsgHandler(w, http.StatusBadRequest, "missing command to execute")
		return
	}

	r.Header.Set("Content-Type", "application/octet-stream")
	// TODO: validate command to execute (Security!)
	cmd := exec.Command(command[0], command[1:]...)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return
	}

	pr, pw := io.Pipe()
	cmd.Stdout = pw
	cmd.Stderr = os.Stderr
	go func() {
		io.Copy(stdin, r.Body)
		stdin.Close()
	}()
	go io.Copy(w, pr)

	err = cmd.Run()
	pw.Close()
	if err != nil {
		logErrorf("failed to exec command, err: %v", err)
	}
}

// GET /
func ioGetHandler(w http.ResponseWriter, r *http.Request) {
	if aisTargetURL == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	path := strings.TrimPrefix(r.URL.EscapedPath(), "/")
	if path == "health" {
		return
	}
}
