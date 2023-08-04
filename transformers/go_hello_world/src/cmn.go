// Package main is implementation of a simple hello world transformation in golang.
/*
 * Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"runtime/debug"
)

const (
	HeaderContentLength = "Content-Length"
	HeaderContentType   = "Content-Type"

	GetContentType = "binary/octet-stream"
)

func invalidMsgHandler(w http.ResponseWriter, errCode int, format string, a ...interface{}) {
	logErrorf(format, a...)
	w.Header().Set("Content-type", "text/plain")
	w.WriteHeader(errCode)
	if _, err := w.Write([]byte(fmt.Sprintf(format, a...))); err != nil {
		logErrorf("%v", err)
	}
}

// Returns an error with message if status code was > 200
func wrapHttpError(resp *http.Response, err error) (*http.Response, error) {
	if err != nil {
		return resp, err
	}

	if resp.StatusCode > http.StatusOK {
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
