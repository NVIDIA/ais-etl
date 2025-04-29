// Package main is implementation of ID (echo) transformation in golang.
/*
 * Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"
)

type EchoServer struct {
	aisTargetURL string
	argType      string
	endpoint     string

	client *http.Client
}

func NewEchoServer(ipAddress string, port int) *EchoServer {
	svr := &EchoServer{
		endpoint:     fmt.Sprintf("%s:%d", ipAddress, port),
		aisTargetURL: os.Getenv("AIS_TARGET_URL"),
		argType:      os.Getenv("ARG_TYPE"),
		client:       &http.Client{},
	}

	return svr
}

func main() {
	var (
		ipAddressArg = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		portArg      = flag.Int("p", 8000, "Specify the port on which the server listens")
	)

	flag.Parse()

	echoServer := NewEchoServer(*ipAddressArg, *portArg)
	echoServer.start()
}

func transform(input io.ReadCloser) (io.ReadCloser, error) {
	data, err := io.ReadAll(input)
	if err != nil {
		return nil, err
	}
	input.Close()
	return io.NopCloser(bytes.NewReader(data)), nil
}

func (svr *EchoServer) start() {
	http.HandleFunc("/", svr.echoHandler)
	http.HandleFunc("/health", svr.healthHandler)

	log.Printf("Starting echo transformer at %s", svr.endpoint)
	log.Fatal(http.ListenAndServe(svr.endpoint, nil))
}

func (svr *EchoServer) healthHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Running"))
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}

}

func (svr *EchoServer) echoHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		svr.echoPutHandler(w, r)
	case http.MethodGet:
		svr.echoGetHandler(w, r)
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

// PUT /
func (svr *EchoServer) echoPutHandler(w http.ResponseWriter, r *http.Request) {
	var (
		objReader io.ReadCloser
		size      int64
		err       error
	)

	switch svr.argType {
	case ArgTypeDefault, ArgTypeURL:
		objReader, err = transform(r.Body)
		if err != nil {
			logErrorf("%v", err)
			return
		}
		size = r.ContentLength
	case ArgTypeFQN:
		joined := filepath.Join("/", strings.TrimLeft(r.URL.Path, "/"))
		fqn := path.Clean(joined)
		objReader, size, err = svr.getFQNReader(fqn)
		if err != nil {
			logErrorf("%v", err)
			return
		}
		objReader, err = transform(objReader)
		if err != nil {
			logErrorf("%v", err)
			return
		}
	default:
		logErrorf("invalid arg_type: %s", svr.argType)
	}

	if directPutURL := r.Header.Get(HeaderNodeURL); directPutURL != "" {
		err := svr.handleDirectPut(directPutURL, objReader)
		if err != nil {
			// Note: r.Body (objReader) is consumed during direct put and cannot be restored afterward.
			// Therefore, if direct put fails, we cannot safely fall back to the normal response flow.
			// We enforce that direct put must succeed; otherwise, return HTTP 500.
			log.Printf("%v", err)
			w.WriteHeader(http.StatusInternalServerError)
		} else {
			setResponseHeaders(w.Header(), 0)
			w.WriteHeader(http.StatusNoContent)
		}
		return
	}

	setResponseHeaders(w.Header(), size)
	if _, err := io.Copy(w, objReader); err != nil {
		logErrorf("%v", err)
	}
}

// GET /
func (svr *EchoServer) echoGetHandler(w http.ResponseWriter, r *http.Request) {
	if svr.aisTargetURL == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	p := strings.TrimPrefix(r.URL.EscapedPath(), "/")
	if p == "health" {
		return
	}

	var (
		objReader io.ReadCloser
		size      int64
		err       error
	)
	switch svr.argType {
	case ArgTypeDefault, ArgTypeURL:
		resp, err := wrapHttpError(svr.client.Get(fmt.Sprintf("%s/%s", svr.aisTargetURL, p)))
		if err != nil {
			invalidMsgHandler(w, http.StatusBadRequest, "GET to AIStore failed; err %v", err)
			return
		}
		objReader = resp.Body
		size = resp.ContentLength
	case ArgTypeFQN:
		joined := filepath.Join("/", strings.TrimLeft(r.URL.Path, "/"))
		fqn := path.Clean(joined)
		objReader, size, err = svr.getFQNReader(fqn)
		if err != nil {
			logErrorf("%v", err)
		}
	default:
		logErrorf("invalid arg_type: %s", svr.argType)
	}

	if directPutURL := r.Header.Get(HeaderNodeURL); directPutURL != "" {
		if err := svr.handleDirectPut(directPutURL, objReader); err == nil {
			setResponseHeaders(w.Header(), 0)
			w.WriteHeader(http.StatusNoContent)
			return
		} else {
			logErrorf("%v", err)
		}
	}

	setResponseHeaders(w.Header(), size)
	if _, err := io.Copy(w, objReader); err != nil {
		logErrorf("%v", err)
	}
	objReader.Close()
}

func (svr *EchoServer) getFQNReader(fqn string) (io.ReadCloser, int64, error) {
	fh, err := os.Open(fqn)
	if err != nil {
		return nil, 0, err
	}
	stat, err := fh.Stat()
	if err != nil {
		return nil, 0, err
	}
	return fh, stat.Size(), nil
}

func (svr *EchoServer) handleDirectPut(directPutURL string, r io.ReadCloser) error {
	parsedTarget, err := url.Parse(directPutURL)
	if err != nil {
		r.Close()
		return err
	}
	parsedHost, err := url.Parse(svr.aisTargetURL)
	if err != nil {
		r.Close()
		return err
	}
	parsedHost.Host = parsedTarget.Host
	parsedHost.Path = path.Join(parsedHost.Path, parsedTarget.Path)

	req, err := http.NewRequest(http.MethodPut, parsedHost.String(), r)
	if err != nil {
		r.Close()
		return err
	}
	_, err = wrapHttpError(svr.client.Do(req))
	if err != nil {
		return err
	}
	return nil
}
