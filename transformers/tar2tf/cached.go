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
)

func init() {
	var err error
	tmpDir, err = ioutil.TempDir("", "tar2tf-transformer")
	assert(err == nil, fmt.Sprintf("%v", err))

	go gc()
}

const (
	totalSizeAllowedHW = 1024 * 1024 * 1024 * 2 // 2 GiB
	totalSizeAllowedLW = 1024 * 1024 * 1024     // 1 GiB
)

var (
	tmpDir    string
	trashDir  string
	cache     = &versionCache{m: make(map[string]string)}
	totalSize = int64(0)
)

type (
	tarObject struct {
		bucket, name string
		tarGz        bool
	}

	versionCache struct {
		m   map[string]string // FQN() version
		mtx sync.RWMutex
	}
)

func (o *tarObject) Name() string {
	return fmt.Sprintf("%s/%s", o.bucket, o.name)
}

func (o *tarObject) FQN() string {
	return filepath.Join(tmpDir, o.bucket, o.name)
}

func (o *tarObject) DirFQN() string {
	return filepath.Join(tmpDir, o.bucket)
}

func cmpCacheVersion(o *tarObject, version string) bool {
	cache.mtx.RLock()
	defer cache.mtx.RUnlock()
	v, ok := cache.m[o.FQN()]
	if !ok {
		return false
	}
	return v == version
}

func updateVersion(o *tarObject, version string) {
	cache.mtx.Lock()
	cache.m[o.FQN()] = version
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
	var (
		previousSize int64
		counter      = &writeCounter{}
	)

	f, err = os.Open(o.FQN())
	if err != nil && !errFileNotExists(err) {
		return nil, "", err
	}

	if err == nil {
		remoteVersion, err := versionFromRemote(o)
		if err != nil {
			return nil, "", err
		}
		if cmpCacheVersion(o, remoteVersion) {
			return f, remoteVersion, nil
		}

		// If versions are different, fetch and transform the object again.
		fi, err := f.Stat()
		if err != nil {
			return nil, "", err
		}

		previousSize = fi.Size()
	}

	resp, err := client.Get(fmt.Sprintf("%s/v1/objects/%s/%s", aisTargetUrl, o.bucket, o.name))
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

	if err := os.MkdirAll(o.DirFQN(), 0755); err != nil {
		return nil, "", err
	}
	f, err = os.Create(o.FQN())
	if err != nil {
		return nil, "", err
	}

	if err := defaultPipeline(resp.Body, io.MultiWriter(f, counter), o.tarGz).Do(); err != nil {
		return nil, "", err
	}

	updateVersion(o, resp.Header.Get(HeaderVersion))
	updateTotalSize(counter.Size(), previousSize)
	f.Seek(0, io.SeekStart)
	return f, resp.Header.Get(HeaderVersion), nil
}

func versionFromRemote(o *tarObject) (string, error) {
	resp, err := client.Head(fmt.Sprintf("%s/%s/%s", aisTargetUrl, o.bucket, o.name))
	if err != nil {
		return "", err
	}

	return resp.Header.Get(HeaderVersion), nil
}

func fsTFRecordSize(f *os.File) int64 {
	fi, err := f.Stat()
	assert(err == nil, "file has to be present")
	assert(fi != nil, "file has to be non nil")
	return fi.Size()
}

func tfRecordChunkReader(f *os.File, start, length int64) (io.Reader, error) {
	return &onCloseReader{
		r:  io.NewSectionReader(f, start, length),
		cb: func() { f.Close() },
	}, nil
}
