// Package main is implementation of ID (echo) transformation in golang.
/*
 * Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"runtime/debug"
	"strconv"
)

const (
	HeaderContentLength = "Content-Length"
	HeaderContentType   = "Content-Type"
	HeaderNodeURL       = "Ais-Node-Url"

	GetContentType = "binary/octet-stream"

	ArgTypeDefault = ""
	ArgTypeURL     = "url"
	ArgTypeFQN     = "fqn"
)

func invalidMsgHandler(w http.ResponseWriter, errCode int, format string, a ...interface{}) {
	logErrorf(format, a...)
	w.Header().Set("Content-type", "text/plain")
	w.WriteHeader(errCode)
	w.Write([]byte(fmt.Sprintf(format, a...)))
}

func setResponseHeaders(header http.Header, size int64) {
	header.Set(HeaderContentLength, strconv.FormatInt(size, 10))
	header.Set(HeaderContentType, GetContentType)
}

// Returns an error with message if status code was > 200
func wrapHttpError(resp *http.Response, err error) (*http.Response, error) {
	if err != nil {
		return resp, err
	}

	if resp.StatusCode > http.StatusNoContent {
		if resp.Body == nil {
			return resp, errors.New(resp.Status)
		}
		b, err := io.ReadAll(resp.Body)
		if err != nil {
			return resp, err
		}
		return resp, fmt.Errorf("%s %s", resp.Status, string(b))
	}

	return resp, nil
}

func logErrorf(format string, a ...interface{}) {
	log.Printf(string(debug.Stack())+" : "+format, a...)
}
