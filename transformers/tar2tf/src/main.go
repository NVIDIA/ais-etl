// Package main is an entry point to Tar2Tf transformation
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"html"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/NVIDIA/ais-tar2tf/transformers/tar2tf/src/cmn"
	"github.com/NVIDIA/ais-tar2tf/transformers/tar2tf/src/transforms"
)

var (
	aisTargetUrl string
	endpoint     string
	transformJob *transforms.TransformJob

	client *http.Client
)

func initVars(ipAddress string, port int, filterSpec []byte) {
	endpoint = fmt.Sprintf("%s:%d", ipAddress, port)
	aisTargetUrl = os.Getenv("AIS_TARGET_URL")
	client = &http.Client{}

	var (
		err    error
		jobMsg = &transforms.TransformJobMsg{}
	)

	if filterSpec != nil {
		cmn.Exit(json.Unmarshal(filterSpec, jobMsg))
		transformJob, err = jobMsg.ToTransformJob()
		cmn.Exit(err)
	}
}

func main() {
	var (
		specArg     = flag.String("spec", "", "Specify selections and conversions to apply to TAR records")
		specFileArg = flag.String("spec-file", "", "Specify path to selections and conversions to apply to TAR records")

		ipAddressArg = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		portArg      = flag.Int("p", 8000, "Specify the port on which the server listens")

		filterSpec []byte
	)

	flag.Parse()

	if *specArg != "" && *specFileArg != "" {
		log.Fatalf("specify either spec or spec-file")
	}

	if *specArg != "" {
		filterSpec = []byte(*specArg)
	}
	if *specFileArg != "" {
		fh, err := os.Open(*specFileArg)
		cmn.Exit(err)
		filterSpec, err = ioutil.ReadAll(fh)
		cmn.AssertNoErr(fh.Close())
	}

	initVars(*ipAddressArg, *portArg, filterSpec)

	http.HandleFunc("/", tar2tfHandler)
	http.HandleFunc("/health", healthHandler)

	log.Printf("Starting tar2tf transformer at %s", endpoint)
	log.Fatal(http.ListenAndServe(endpoint, nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	default:
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}

}

func tar2tfHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPut:
		tar2tfPutHandler(w, r)
	case http.MethodGet:
		tar2tfGetHandler(w, r)
	default:
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

// PUT /
func tar2tfPutHandler(w http.ResponseWriter, r *http.Request) {
	if err := onTheFlyTransform(r, w); err != nil {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "failed transforming TAR: %s", err.Error())
	}
}

// GET /bucket/object
func tar2tfGetHandler(w http.ResponseWriter, r *http.Request) {
	if aisTargetUrl == "" {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	escaped := html.EscapeString(r.URL.Path)
	escaped = strings.TrimPrefix(escaped, "/")

	if escaped == "health" {
		return
	}

	apiItems := strings.SplitN(escaped, "/", 2)
	if len(apiItems) < 2 {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "expected 2 path elements, got %q", escaped)
		return
	}

	obj := &tarObject{
		bucket: apiItems[0],
		name:   apiItems[1],
		tarGz:  isTarGzRequest(r),
	}

	// Make sure that transformed TFRecord exists - if it doesn't, get TAR from a target
	// and transform it to TFRecord.
	tfRecord, version, err := transformFromRemoteOrPass(obj)
	if err != nil {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}

	// Extract the requested bytes range from a header.
	size := fsTFRecordSize(tfRecord)
	rng, err := cmn.ObjectRange(r.Header.Get(cmn.HeaderRange), size)
	if err != nil {
		if err == cmn.OverlapError {
			w.Header().Set(cmn.HeaderContentRange, fmt.Sprintf("bytes */%d", size))
		}
		w.Header().Set(cmn.HeaderContentLength, strconv.FormatInt(size, 10))
		w.WriteHeader(http.StatusRequestedRangeNotSatisfiable)
		return
	}

	cmn.SetResponseHeaders(w.Header(), rng.Length, version)

	// Read only selected range from a TFRecord file
	reader, err := tfRecordChunkReader(tfRecord, rng.Start, rng.Length)
	if err != nil {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}

	_, err = io.Copy(w, reader)
	if err != nil {
		cmn.InvalidMsgHandler(w, http.StatusBadRequest, "error copying TFRecord to response writer: %v", err)
		return
	}
}

// TODO: We might be able to cache this results, however it would require setting
// object name and bucket name in the headers, on the target side.
func onTheFlyTransform(req *http.Request, responseWriter http.ResponseWriter) error {
	rangeStr := req.Header.Get(cmn.HeaderRange)
	if rangeStr == "" {
		return onTheFlyTransformWholeObject(req, responseWriter)
	}

	var (
		buff    = bytes.NewBuffer(nil)
		counter = &cmn.WriteCounter{}
		w       = io.MultiWriter(buff, counter)
	)

	defer req.Body.Close()
	if err := transforms.CreatePipeline(req.Body, w, isTarGzRequest(req), transformJob).Do(); err != nil {
		return err
	}

	rng, err := cmn.ObjectRange(rangeStr, counter.Size())
	if err != nil {
		return err
	}

	n, err := cmn.CopySection(buff, responseWriter, rng.Start, rng.Length)
	if err != nil {
		return err
	}

	cmn.SetResponseHeaders(responseWriter.Header(), n, req.Header.Get(cmn.HeaderVersion))
	return nil
}

func onTheFlyTransformWholeObject(req *http.Request, responseWriter io.Writer) error {
	defer req.Body.Close()
	return transforms.CreatePipeline(req.Body, responseWriter, isTarGzRequest(req), transformJob).Do()
}

func isTarGzRequest(r *http.Request) bool {
	arTy := strings.ToUpper(r.URL.Query().Get("archive_type"))
	return arTy == "TAR.GZ" || arTy == "TARGZ" || arTy == "TGZ"
}
