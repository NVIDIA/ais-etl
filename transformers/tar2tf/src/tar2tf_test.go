// Package main is an entry point to Tar2Tf transformation
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"net/http"
	"net/url"
	"os"
	"testing"

	"github.com/NVIDIA/go-tfdata/tfdata/core"
)

const tarPath = "tar-single.tar"

func mockRequest(t *testing.T) (r *http.Request) {
	var err error

	r = &http.Request{}
	r.Body, err = os.Open(tarPath)
	r.URL = &url.URL{}
	if err != nil {
		t.Fatal(err.Error())
	}
	return r
}

func TestTar2TfSimple(t *testing.T) {
	initVars("localhost", 8080, nil)

	var (
		req  = mockRequest(t)
		buff = bytes.NewBuffer(nil)
	)

	err := onTheFlyTransformWholeObject(req, buff)
	if err != nil {
		t.Fatal(err.Error())
	}

	r := core.NewTFRecordReader(buff)
	examples, err := r.ReadAllExamples(1)
	if err != nil {
		t.Fatal(err.Error())
	}
	if len(examples) != 1 {
		t.Fatalf("expected 1 example, got %d", len(examples))
	}
}

func TestTar2TfConvTransform(t *testing.T) {
	var (
		req  = mockRequest(t)
		buff = bytes.NewBuffer(nil)

		filterSpec = []byte(`
			{
			  "conversions": [
				{
				  "type": "Decode",
				  "ext_name": "png"
				},
				{
				  "type": "Rotate",
				  "ext_name": "png"
				}
			  ],
			  "selections": [
				{
				  "ext_name": "png"
				},
				{
				  "ext_name": "cls"
				}
			  ]
			}
		`)
	)

	initVars("localhost", 8080, filterSpec)
	err := onTheFlyTransformWholeObject(req, buff)
	if err != nil {
		t.Fatal(err.Error())
	}

	r := core.NewTFRecordReader(buff)
	examples, err := r.ReadAllExamples(1)
	if err != nil {
		t.Fatal(err.Error())
	}
	if len(examples) != 1 {
		t.Fatalf("expected 1 example, got %d", len(examples))
	}
}
