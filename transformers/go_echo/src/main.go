// Package main is implementation of ID (echo) transformation in golang.
/*
 * Copyright (c) 2021-2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"flag"
	"io"
	"log"

	"github.com/NVIDIA/aistore/ext/etl/webserver"
)

type EchoServer struct {
	webserver.ETLServer
}

func (es *EchoServer) Transform(input io.ReadCloser, path, args string) (io.ReadCloser, error) {
	data, err := io.ReadAll(input)
	if err != nil {
		return nil, err
	}
	input.Close()
	return io.NopCloser(bytes.NewReader(data)), nil
}

var _ webserver.ETLServer = (*EchoServer)(nil)

func main() {
	listenAddr := flag.String("l", "0.0.0.0", "IP address to listen on")
	port := flag.Int("p", 8000, "Port to listen on")
	flag.Parse()

	svr := &EchoServer{}
	if err := webserver.Run(svr, *listenAddr, *port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
