// Package cmn common low-level types and utilities
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package cmn

import (
	"errors"
	"fmt"
	"io/fs"
	"io/ioutil"
	"log"
	"net/http"
	"runtime/debug"
	"strconv"
	"strings"
)

const (
	HeaderRange         = "Range" // Ref: https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.35
	HeaderContentLength = "Content-Length"
	HeaderContentType   = "Content-Type"
	HeaderContentRange  = "Content-Range"

	HeaderVersion    = "version"
	AwsHeaderVersion = "x-amz-version-id"

	GetContentType = "binary/octet-stream"
)

type (
	httpRange struct {
		Start, Length int64
	}
)

var (
	OverlapError = errors.New("failed to overlap")
)

func InvalidMsgHandler(w http.ResponseWriter, errCode int, format string, a ...interface{}) {
	log.Printf(string(debug.Stack())+" :"+format, a...)
	w.Header().Set("Content-type", "application/json")
	w.WriteHeader(errCode)
	w.Write([]byte(fmt.Sprintf(format, a...)))
}

func SetResponseHeaders(header http.Header, size int64, version string) {
	header.Set(HeaderContentLength, strconv.FormatInt(size, 10))
	header.Set(HeaderContentType, GetContentType)
	header.Set(AwsHeaderVersion, version)
}

// Returns an error with message if status code was > 200
func WrapHttpError(resp *http.Response, err error) (*http.Response, error) {
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

func ErrFileNotExists(err error) bool {
	if err == nil {
		return false
	}
	return errors.Is(err, fs.ErrNotExist)
}

// HTTP RANGE HEADER

func ObjectRange(rangeStr string, size int64) (rng *httpRange, err error) {
	if rangeStr != "" {
		rs, err := ParseMultiRange(rangeStr, size)
		if err != nil {
			return nil, err
		}
		if len(rs) != 1 {
			return nil, fmt.Errorf("expected one range interval, got %d", len(rs))
		}
		rng = &rs[0]
	} else {
		rng = &httpRange{Start: 0, Length: size}
	}

	return rng, nil
}

// From https://golang.org/src/net/http/fs.go
// ParseMultiRange parses a Range header string as per RFC 7233.
func ParseMultiRange(s string, size int64) ([]httpRange, error) {
	if s == "" {
		return nil, nil // header not present
	}
	const b = "bytes="
	if !strings.HasPrefix(s, b) {
		return nil, errors.New("invalid range")
	}
	var ranges []httpRange
	noOverlap := false
	for _, ra := range strings.Split(s[len(b):], ",") {
		ra = strings.TrimSpace(ra)
		if ra == "" {
			continue
		}
		i := strings.Index(ra, "-")
		if i < 0 {
			return nil, errors.New("invalid range")
		}
		start, end := strings.TrimSpace(ra[:i]), strings.TrimSpace(ra[i+1:])
		var r httpRange
		if start == "" {
			// If no start is specified, end specifies the
			// range start relative to the end of the file.
			i, err := strconv.ParseInt(end, 10, 64)
			if err != nil {
				return nil, errors.New("invalid range")
			}
			if i > size {
				i = size
			}
			r.Start = size - i
			r.Length = size - r.Start
		} else {
			i, err := strconv.ParseInt(start, 10, 64)
			if err != nil || i < 0 {
				return nil, errors.New("invalid range")
			}
			if i >= size {
				// If the range begins after the size of the content,
				// then it does not overlap.
				noOverlap = true
				continue
			}
			r.Start = i
			if end == "" {
				// If no end is specified, range extends to end of the file.
				r.Length = size - r.Start
			} else {
				i, err := strconv.ParseInt(end, 10, 64)
				if err != nil || r.Start > i {
					return nil, errors.New("invalid range")
				}
				if i >= size {
					i = size - 1
				}
				r.Length = i - r.Start + 1
			}
		}
		ranges = append(ranges, r)
	}
	if noOverlap && len(ranges) == 0 {
		// The specified ranges did not overlap with the content.
		log.Printf("failed to overlap. range string: %q, size %d", s, size)
		return nil, OverlapError
	}
	return ranges, nil
}
