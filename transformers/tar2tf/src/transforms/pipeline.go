// Package transforms provides tools to transform TAR to TFRecords files
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package transforms

import (
	"io"

	"github.com/NVIDIA/go-tfdata/tfdata/core"
	"github.com/NVIDIA/go-tfdata/tfdata/pipeline"
	"github.com/NVIDIA/go-tfdata/tfdata/transform"
)

func CreatePipeline(r io.Reader, w io.Writer, isTarGz bool, job *TransformJob) *pipeline.DefaultPipeline {
	if job != nil {
		return transformPipeline(r, w, isTarGz, job)
	}
	return defaultPipeline(r, w, isTarGz)
}

func defaultPipeline(r io.Reader, w io.Writer, isTarGz bool) *pipeline.DefaultPipeline {
	p := pipeline.NewPipeline()
	if isTarGz {
		p.FromTarGz(r)
	} else {
		p.FromTar(r)
	}
	return p.SampleToTFExample().ToTFRecord(w, 8)
}

func transformPipeline(r io.Reader, w io.Writer, isTarGz bool, job *TransformJob) *pipeline.DefaultPipeline {
	p := pipeline.NewPipeline()
	if isTarGz {
		p.FromTarGz(r)
	} else {
		p.FromTar(r)
	}

	var transformations []transform.SampleTransformation
	transformations = append(transformations, job.Conversions...)
	if len(job.Selections) > 0 { // Select everything by default.
		transformations = append(transformations, transform.SampleSelections(job.Selections...))
	}
	p.TransformSamples(transformations...).WithSample2TFExampleStage(func(sr core.SampleReader) core.TFExampleReader {
		return &SampleToTFExampleReader{SampleReader: sr}
	}).ToTFRecord(w)
	return p
}
