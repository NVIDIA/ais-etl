package main

import (
	"io"
	"io/ioutil"
	"sync/atomic"
)

type (
	onCloseReader struct {
		r  io.Reader
		cb func()
	}

	writeCounter struct {
		totalBytesWritten int64
	}
)

func (r *onCloseReader) Read(p []byte) (int, error) {
	return r.r.Read(p)
}

func (r *onCloseReader) Close() {
	r.cb()
}

func (r *writeCounter) Write(p []byte) (int, error) {
	atomic.AddInt64(&r.totalBytesWritten, int64(len(p)))
	return len(p), nil
}

func (r *writeCounter) Size() int64 {
	return atomic.LoadInt64(&r.totalBytesWritten)
}

func copySection(r io.Reader, w io.Writer, start, length int64) (n int64, err error) {
	// Discard first start bytes.
	n, err = io.CopyN(ioutil.Discard, r, start)
	if err != nil {
		return 0, err
	}

	// Write only length bytes.
	return io.CopyN(w, r, length)
}
