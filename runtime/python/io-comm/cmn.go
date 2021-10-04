// Package main is an entry point to ioComm server
/*
 * Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
 */

package main

import (
	"errors"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"runtime/debug"
	"strconv"
)

const (
	headerContentLength = "Content-Length"
	headerContentType   = "Content-Type"

	getContentType = "binary/octet-stream"
)

func invalidMsgHandler(w http.ResponseWriter, errCode int, format string, a ...interface{}) {
	logErrorf(format, a...)
	w.Header().Set("Content-type", "text/plain")
	w.WriteHeader(errCode)
	w.Write([]byte(fmt.Sprintf(format, a...)))
}

func setResponseHeaders(header http.Header, size int64) {
	header.Set(headerContentLength, strconv.FormatInt(size, 10))
	header.Set(headerContentType, getContentType)
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
		b, err := ioutil.ReadAll(resp.Body)
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
