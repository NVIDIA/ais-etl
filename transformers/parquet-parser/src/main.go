// Package main is implementation of parquet parsing transformation in golang.
/*
 * Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/NVIDIA/aistore/ext/etl/webserver"
)

type ParquetParserServer struct {
	webserver.ETLServer
}

func (ps *ParquetParserServer) Transform(input io.ReadCloser, path, etlArgs string) (io.ReadCloser, error) {

	ext := strings.ToLower(filepath.Ext(path))
	if ext != ".parquet" {
		data, err := io.ReadAll(input)
		input.Close()
		if err != nil {
			return nil, fmt.Errorf("reading pass-through data: %w", err)
		}
		return io.NopCloser(bytes.NewReader(data)), nil
	}

	outputFormat := strings.ToLower(os.Getenv("OUTPUT_FORMAT"))
	if outputFormat == "" {
		outputFormat = FormatJSON // Default format
	}

	// etlArgs takes priority over environment variable
	if etlArgs != "" {
		candidateFormat := strings.ToLower(etlArgs)
		if isValidFormat(candidateFormat) {
			outputFormat = candidateFormat
		}
		// Invalid etlArgs are ignored, fallback to environment variable
	}

	// Validate final format choice
	if !isValidFormat(outputFormat) {
		return nil, fmt.Errorf("unsupported output format: %s. Supported: %s, %s, %s, %s", outputFormat, FormatJSON, FormatCSV, FormatTXT, FormatText)
	}

	parquetData, err := io.ReadAll(input)
	input.Close()
	if err != nil {
		return nil, fmt.Errorf("reading parquet data: %w", err)
	}

	convertedData, err := convertParquet(parquetData, outputFormat)
	if err != nil {
		return nil, fmt.Errorf("converting parquet: %w", err)
	}

	if convertedData == nil {
		return nil, fmt.Errorf("convertParquet returned nil data")
	}

	return io.NopCloser(bytes.NewReader(convertedData)), nil
}

// isValidFormat checks if the format is supported
func isValidFormat(format string) bool {
	switch format {
	case FormatJSON, FormatCSV, FormatTXT, FormatText:
		return true
	default:
		return false
	}
}

var _ webserver.ETLServer = (*ParquetParserServer)(nil)

func main() {
	listenAddr := flag.String("l", "0.0.0.0", "IP address to listen on")
	port := flag.Int("p", 8000, "Port to listen on")
	flag.Parse()

	svr := &ParquetParserServer{}

	if err := webserver.Run(svr, *listenAddr, *port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
