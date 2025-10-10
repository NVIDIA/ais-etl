// Package main is implementation of a simple hello world transformation in golang.
/*
 * Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"flag"
	"io"
	"log"

	"github.com/NVIDIA/aistore/ext/etl/webserver"
)

type HelloWorldServer struct {
	response string
	webserver.ETLServer
}

func (es *HelloWorldServer) Transform(input io.ReadCloser, path, args string) (io.ReadCloser, int64, error) {
	input.Close()
	return io.NopCloser(bytes.NewReader([]byte(es.response))), int64(len(es.response)), nil
}

var _ webserver.ETLServer = (*HelloWorldServer)(nil)

func main() {
	listenAddr := flag.String("l", "0.0.0.0", "IP address to listen on")
	port := flag.Int("p", 80, "Port to listen on")
	flag.Parse()

	svr := &HelloWorldServer{
		response: "Hello World!",
	}

	if err := webserver.Run(svr, *listenAddr, *port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
