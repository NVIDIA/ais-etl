// Package main is implementation of FFmpeg transformation in golang.
/*
 * Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"io"
	"os"
	"testing"

	"github.com/NVIDIA/aistore/tools/tassert"
	"github.com/NVIDIA/aistore/tools/tlog"
)

// NOTE: This test requires ffmpeg to be installed and available in the PATH.
func TestFFmpegTransform(t *testing.T) {
	filename := "../../tests/resources/test-audio-wav.wav"
	input, err := os.Open(filename)
	tassert.CheckError(t, err)

	// Send it to the ETL server
	svr := &FFmpegServer{
		channels:   "1",
		samplerate: "44100",
	}

	transformed, size, err := svr.Transform(input, filename, "")
	tassert.CheckError(t, err)

	output, err := io.ReadAll(transformed)
	tlog.Logf("Transformed output size: %d\n", len(output))
	tassert.CheckError(t, err)
	tassert.Fatalf(t, size == int64(len(output)), "Size mismatch: Transform reported %d bytes, but actual output is %d bytes", size, len(output))
	tassert.Fatalf(t, bytes.HasPrefix(output, []byte("RIFF")), "Output is not a valid WAV file")
}

// NOTE: This test requires ffmpeg to be installed and available in the PATH.
func TestFFmpegTransformMP3(t *testing.T) {
	filename := "../../tests/resources/test-audio-mp3.mp3"
	input, err := os.Open(filename)
	tassert.CheckError(t, err)

	svr := &FFmpegServer{
		channels:   "1",
		samplerate: "16000", // downsample to emphasize transformation
	}

	// Run the transform
	transformed, size, err := svr.Transform(input, filename, "")
	tassert.CheckError(t, err)

	// Read result
	output, err := io.ReadAll(transformed)
	tassert.CheckError(t, err)

	tlog.Logf("Transformed output size: %d bytes\n", len(output))
	tlog.Logln(string(output[:10]))

	// Validate that reported size matches actual output
	tassert.Fatalf(t, size == int64(len(output)), "Size mismatch: Transform reported %d bytes, but actual output is %d bytes", size, len(output))

	// Assert basic WAV structure
	tassert.Fatalf(t, bytes.HasPrefix(output, []byte("RIFF")), "Missing RIFF header")
	tassert.Fatalf(t, bytes.Contains(output, []byte("WAVEfmt ")), "Missing WAVE format chunk")
	tassert.Fatalf(t, bytes.Contains(output, []byte("data")), "Missing data chunk")

	// Make sure it's not identical to input (to verify it's transformed)
	input.Seek(0, io.SeekStart)
	original, err := io.ReadAll(input)
	tassert.CheckError(t, err)
	tassert.Fatalf(t, !bytes.Equal(output, original), "Output should not be identical to input")
}
