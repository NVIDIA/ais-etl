// Package cmn common low-level types and utilities
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package cmn

import (
	"bytes"
	"io"
	"io/ioutil"
	"sync/atomic"
)

type (
	OnCloseReader struct {
		R  io.Reader
		Cb func()
	}

	WriteCounter struct {
		totalBytesWritten int64
	}

	// ByteHandle is a byte buffer(made from []byte) that implements
	// ReadOpenCloser interface
	ByteHandle struct {
		b []byte
		*bytes.Reader
	}
)

func (r *OnCloseReader) Read(p []byte) (int, error) {
	return r.R.Read(p)
}

func (r *OnCloseReader) Close() {
	r.Cb()
}

func (r *WriteCounter) Write(p []byte) (int, error) {
	atomic.AddInt64(&r.totalBytesWritten, int64(len(p)))
	return len(p), nil
}

func (r *WriteCounter) Size() int64 {
	return atomic.LoadInt64(&r.totalBytesWritten)
}

func CopySection(r io.Reader, w io.Writer, start, length int64) (n int64, err error) {
	// Discard first start bytes.
	n, err = io.CopyN(ioutil.Discard, r, start)
	if err != nil {
		return 0, err
	}

	// Write only length bytes.
	return io.CopyN(w, r, length)
}

func NewByteHandle(bt []byte) *ByteHandle {
	return &ByteHandle{bt, bytes.NewReader(bt)}
}

func (b *ByteHandle) Close() error {
	return nil
}
func (b *ByteHandle) Open() (io.ReadCloser, error) {
	return ioutil.NopCloser(bytes.NewReader(b.b)), nil
}
