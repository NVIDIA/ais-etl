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
	ffmpegCmd []string
}

var audioExts = cos.NewStrSet(".wav", ".flac", ".mp3", ".m4a", ".opus", ".ogg")

func (fs *FFmpegServer) Transform(input io.ReadCloser, path, args string) (io.ReadCloser, int64, error) {
	ext := strings.ToLower(filepath.Ext(path))
	if !audioExts.Contains(ext) {
		// If it's not an audio file we recognize, return as-is
		buf, err := io.ReadAll(input)
		if err != nil {
			return nil, -1, fmt.Errorf("reading input: %w", err)
		}
		return io.NopCloser(bytes.NewReader(buf)), int64(len(buf)), nil
	}

	cmd := exec.Command("ffmpeg", fs.ffmpegCmd...)
	cmd.Stderr = &bytes.Buffer{}
	cmd.Stdin = input
	out, err := cmd.Output() // TODO: use cmd.StdoutPipe() to achieve better concurrency
	if err != nil {
		errMsg := cmd.Stderr.(*bytes.Buffer).String()
		return nil, -1, fmt.Errorf("ffmpeg error: %s", strings.TrimSpace(errMsg))
	}
	return io.NopCloser(bytes.NewReader(out)), int64(len(out)), nil
}

var _ webserver.ETLServer = (*FFmpegServer)(nil)

func main() {
	listenAddr := flag.String("l", "0.0.0.0", "IP address to listen on")
	port := flag.Int("p", 8000, "Port to listen on")
	flag.Parse()

	// Read env (do not coerce unless present)
	channels := os.Getenv("AC")                // "1", "2", ...
	samplerate := os.Getenv("AR")              // "16000", "44100", ...
	bitrate := os.Getenv("BR")                 // "128k", "64k", ...
	codec := os.Getenv("CODEC")                // "pcm_s16le", "flac", "libmp3lame", "aac", ...
	audioFilters := os.Getenv("AUDIO_FILTERS") // "loudnorm", "silenceremove", "atempo", "volume", ...
	format := os.Getenv("FORMAT")              // "wav", "flac", "mp3", "m4a", "opus", "ogg", ...

	// Set defaults
	if codec == "" {
		codec = "pcm_s16le"
	}
	if format == "" {
		format = "wav"
	}

	// Build ffmpeg command
	ffmpegCmd := []string{
		"-nostdin",
		"-loglevel", "error",
		"-i", "pipe:0",
	}
	if channels != "" {
		ffmpegCmd = append(ffmpegCmd, "-ac", channels)
	}
	if samplerate != "" {
		ffmpegCmd = append(ffmpegCmd, "-ar", samplerate)
	}

	// Codec (always include)
	ffmpegCmd = append(ffmpegCmd, "-c:a", codec)

	if audioFilters != "" {
		ffmpegCmd = append(ffmpegCmd, "-af", audioFilters)
	}

	// Bitrate only for lossy codecs (safe to include conditionally)
	if bitrate != "" {
		ffmpegCmd = append(ffmpegCmd, "-b:a", bitrate)
	}

	// Output format
	ffmpegCmd = append(ffmpegCmd, "-f", format, "pipe:1")

	svr := &FFmpegServer{
		ffmpegCmd: ffmpegCmd,
	}

	if err := webserver.Run(svr, *listenAddr, *port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
