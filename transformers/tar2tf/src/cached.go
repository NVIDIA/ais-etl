// Package main is an entry point to Tar2Tf transformation
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/NVIDIA/ais-etl/transformers/tar2tf/src/cmn"
	"github.com/NVIDIA/ais-etl/transformers/tar2tf/src/transforms"
)

func init() {
	var err error
	tmpDir, err = ioutil.TempDir("", "tar2tf-transformer")
	cmn.Assert(err == nil, fmt.Sprintf("%v", err))

	go gc()
}

const (
	totalSizeAllowedHW = 1024 * 1024 * 1024 * 8 // 8 GiB
	totalSizeAllowedLW = 1024 * 1024 * 1024 * 4 // 4 GiB
)

var (
	tmpDir    string
	cache     = &versionCache{m: make(map[string]string)}
	totalSize = int64(0)

	mtx = sync.Mutex{}
)

type (
	tarObject struct {
		path  string
		tarGz bool
	}

	versionCache struct {
		m   map[string]string // FQN() version
		mtx sync.RWMutex
	}
)

func (o *tarObject) fqn() string { return filepath.Join(tmpDir, o.path) }

func cmpCacheVersion(o *tarObject, version string) bool {
	cache.mtx.RLock()
	defer cache.mtx.RUnlock()
	v, ok := cache.m[o.fqn()]
	if !ok {
		return false
	}
	return v == version
}

func updateVersion(o *tarObject, version string) {
	cache.mtx.Lock()
	cache.m[o.fqn()] = version
	cache.mtx.Unlock()
}

func removeCacheEntry(fqn string) {
	cache.mtx.Lock()
	delete(cache.m, fqn)
	cache.mtx.Unlock()
}

func updateTotalSize(newSize, prevSize int64) {
	atomic.AddInt64(&totalSize, newSize-prevSize)
}

// gc() removes files when they too much storage, or if they are older than 1 hour.
// Note that the file is not really deleted until there are opened descriptors to it.
// There should be no races or async problems as os.Open is called at most once
// for each request.
// TODO: gc() removes files in lexical order, as filepath.Walk, walks in lexical order.
// 1 hour condition, removes old files which are last in lexical ordering.
func gc() {
	t := time.NewTicker(time.Minute)

	removeF := func() filepath.WalkFunc {
		now := time.Now()
		return func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if info.IsDir() {
				return nil
			}

			if atomic.LoadInt64(&totalSize) < totalSizeAllowedLW && now.Sub(info.ModTime()) < time.Hour {
				return nil
			}

			os.Remove(path)
			removeCacheEntry(path)
			atomic.AddInt64(&totalSize, -1*info.Size())
			return nil
		}
	}

	for range t.C {
		if atomic.LoadInt64(&totalSize) < totalSizeAllowedHW {
			continue
		}
		filepath.Walk(tmpDir, removeF())
	}
}

func transformFromRemoteOrPass(o *tarObject) (f *os.File, version string, err error) {
	// NOTE: this synchronize all transformations. However, if transformed file is already cached,
	// lock will be released fast.
	// This synchronization is required for instance for TF S3 client - it makes multiple concurrent
	// request for different bytes ranges. If not for this lock. we would be starting multiple
	// transformations from scratch, as first one wouldn't finish before the next one starts.
	// TODO: to speed up the transformations of different objects, lock should be per filename.
	mtx.Lock()
	defer mtx.Unlock()

	var (
		previousSize  int64
		remoteVersion string
		counter       = &cmn.WriteCounter{}
		fqn           = o.fqn()
	)

	if remoteVersion, err = versionFromRemote(o); err != nil {
		return nil, "", err
	}

	f, err = os.OpenFile(fqn, os.O_APPEND|os.O_RDWR, 0666)
	if err != nil && !cmn.ErrFileNotExists(err) {
		return nil, "", fmt.Errorf("unknown error opening file %q: %v", o.fqn(), err)
	}

	if err == nil {
		cmn.Assert(f != nil, fqn)
		if cmpCacheVersion(o, remoteVersion) {
			return f, remoteVersion, nil
		}

		// If versions are different, fetch and transform the object again.
		fi, err := f.Stat()
		if err != nil {
			return nil, "", fmt.Errorf("failed to Stat() file %q: %v", fqn, err)
		}

		previousSize = fi.Size()
		cmn.AssertNoErr(f.Close())
	}

	resp, err := cmn.WrapHttpError(client.Get(fmt.Sprintf("%s/%s", aisTargetUrl, o.path)))
	if err != nil {
		return nil, "", err
	}

	if resp.StatusCode >= http.StatusBadRequest {
		b := bytes.NewBuffer(nil)
		_, err := b.ReadFrom(resp.Body)
		if err != nil {
			return nil, "", err
		}
		return nil, "", fmt.Errorf("%d error: %v", resp.StatusCode, string(b.Bytes()))
	}

	if err := os.MkdirAll(filepath.Dir(fqn), 0666); err != nil {
		return nil, "", err
	}
	if f, err = os.Create(fqn); err != nil {
		return nil, "", err
	}

	if err := transforms.CreatePipeline(resp.Body, io.MultiWriter(f, counter), o.tarGz, transformJob).Do(); err != nil {
		return nil, "", err
	}

	updateVersion(o, remoteVersion)
	updateTotalSize(counter.Size(), previousSize)
	_, err = f.Seek(0, io.SeekStart)
	cmn.AssertNoErr(err)

	return f, remoteVersion, nil
}

func versionFromRemote(o *tarObject) (string, error) {
	resp, err := cmn.WrapHttpError(client.Head(fmt.Sprintf("%s/%s", aisTargetUrl, o.path)))
	if err != nil {
		return "", err
	}

	return resp.Header.Get(cmn.HeaderVersion), nil
}

func fsTFRecordSize(f *os.File) int64 {
	fi, err := f.Stat()
	cmn.Assert(err == nil, "file has to be present")
	cmn.Assert(fi != nil, "file has to be non nil")
	return fi.Size()
}

func tfRecordChunkReader(f *os.File, start, length int64) (io.Reader, error) {
	return &cmn.OnCloseReader{
		R:  io.NewSectionReader(f, start, length),
		Cb: func() { f.Close() },
	}, nil
}
