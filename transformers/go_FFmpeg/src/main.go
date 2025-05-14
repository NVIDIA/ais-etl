// Package main is implementation of FFmpeg transformation in golang.
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
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/NVIDIA/aistore/cmn/cos"
	"github.com/NVIDIA/aistore/ext/etl/webserver"
)

type FFmpegServer struct {
	webserver.ETLServer
	channels   string
	samplerate string
}

var audioExts = cos.NewStrSet(".wav", ".flac", ".mp3", ".m4a", ".opus", ".ogg")

func (fs *FFmpegServer) Transform(input io.ReadCloser, path, args string) (io.ReadCloser, error) {
	ext := strings.ToLower(filepath.Ext(path))
	if !audioExts.Contains(ext) {
		// If it's not an audio file we recognize, return as-is
		buf, err := io.ReadAll(input)
		if err != nil {
			return nil, fmt.Errorf("reading input: %w", err)
		}
		return io.NopCloser(bytes.NewReader(buf)), nil
	}

	cmd := exec.Command("ffmpeg",
		"-nostdin",
		"-loglevel", "error",
		"-i", "pipe:0",
		"-ac", fs.channels,
		"-ar", fs.samplerate,
		"-c:a", "pcm_s16le",
		"-f", "wav",
		"pipe:1",
	)
	cmd.Stderr = &bytes.Buffer{}
	cmd.Stdin = input
	out, err := cmd.Output() // TODO: use cmd.StdoutPipe() to achieve better concurrency
	if err != nil {
		errMsg := cmd.Stderr.(*bytes.Buffer).String()
		return nil, fmt.Errorf("ffmpeg error: %s", strings.TrimSpace(errMsg))
	}
	return io.NopCloser(bytes.NewReader(out)), nil
}

var _ webserver.ETLServer = (*FFmpegServer)(nil)

func main() {
	listenAddr := flag.String("l", "0.0.0.0", "IP address to listen on")
	port := flag.Int("p", 8000, "Port to listen on")
	flag.Parse()

	svr := &FFmpegServer{}
	if svr.channels = os.Getenv("AC"); svr.channels == "" {
		svr.channels = "1"
	}
	if svr.samplerate = os.Getenv("AR"); svr.samplerate == "" {
		svr.samplerate = "44100"
	}

	if err := webserver.Run(svr, *listenAddr, *port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
