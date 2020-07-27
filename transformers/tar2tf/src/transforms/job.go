// Package transforms provides tools to transform TAR to TFRecords files
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package transforms

import (
	"fmt"
	"image"
	"image/color"
	_ "image/jpeg"
	_ "image/png"
	"math/rand"

	"github.com/NVIDIA/ais-tar2tf/transformers/tar2tf/src/cmn"
	"github.com/NVIDIA/go-tfdata/tfdata/core"
	"github.com/NVIDIA/go-tfdata/tfdata/transform"
	"github.com/NVIDIA/go-tfdata/tfdata/transform/selection"
	"github.com/disintegration/imaging"
	jsoniter "github.com/json-iterator/go"
)

const (
	TfOpDecode = "Decode"
	TfOpRotate = "Rotate"
	TfOpResize = "Resize"
	TfOpRename = "Rename"
)

type (
	ConversionMsg struct {
		MsgType string              `json:"type"`
		Key     string              `json:"ext_name"`
		DstSize []int               `json:"dst_size"`
		Renames map[string][]string `json:"renames"`
		Angle   float64             `json:"angle"`
	}

	SelectionMsg struct {
		Key string `json:"ext_name"` // TODO: support multiple keys in one selection.
	}

	// Conversions
	DecodeConv struct {
		key string
	}

	RotateConv struct {
		key   string
		angle float64
	}

	ResizeConv struct {
		dstSize []int
		key     string
	}

	RenameConv struct {
		renames map[string][]string
	}

	// Selections
	Select struct {
		key string
	}

	TransformJobMsg struct {
		Conversions []ConversionMsg `json:"conversions"`
		Selections  []SelectionMsg  `json:"selections"`
	}

	TransformJob struct {
		Conversions []transform.SampleTransformation
		Selections  []selection.Sample
	}

	SampleToTFExampleReader struct {
		SampleReader core.SampleReader
	}
)

var (
	_ selection.Sample = &Select{}

	_ transform.SampleTransformation = &RenameConv{}
	_ transform.SampleTransformation = &DecodeConv{}
	_ transform.SampleTransformation = &ResizeConv{}
	_ transform.SampleTransformation = &RotateConv{}
)

func (j *TransformJobMsg) ToTransformJob() (*TransformJob, error) {
	var (
		tj = &TransformJob{}
	)

	for _, c := range j.Conversions {
		conv, err := c.ToSampleTransformation()
		if err != nil {
			return tj, err
		}
		tj.Conversions = append(tj.Conversions, conv)
	}
	for _, s := range j.Selections {
		tj.Selections = append(tj.Selections, s.ToSampleSelection())
	}
	return tj, nil
}

func (msg *ConversionMsg) ToSampleTransformation() (transform.SampleTransformation, error) {
	switch msg.MsgType {
	case TfOpDecode:
		return &DecodeConv{key: msg.Key}, nil
	case TfOpResize:
		return &ResizeConv{key: msg.Key, dstSize: msg.DstSize}, nil
	case TfOpRename:
		return &RenameConv{renames: msg.Renames}, nil
	case TfOpRotate:
		return &RotateConv{key: msg.Key, angle: msg.Angle}, nil
	default:
		return nil, fmt.Errorf("unknown conversion type %q", msg.MsgType)
	}
}

func (msg *SelectionMsg) ToSampleSelection() selection.Sample {
	return &Select{key: msg.Key}
}

func (c *DecodeConv) TransformSample(sample core.Sample) core.Sample {
	img, _, err := image.Decode(cmn.NewByteHandle(sample[c.key].([]byte)))
	cmn.AssertNoErr(err)
	cmn.Assert(img != nil, "expected non-nil result")
	sample[c.key] = img
	return sample
}

func (c *RotateConv) TransformSample(sample core.Sample) core.Sample {
	img := sample[c.key].(image.Image)
	angle := c.angle
	if angle == 0 {
		angle = rand.Float64() * 100
	}
	sample[c.key] = imaging.Rotate(img, angle, color.Black)
	return sample
}

func (c *ResizeConv) TransformSample(sample core.Sample) core.Sample {
	sample[c.key] = imaging.Resize(sample[c.key].(image.Image), c.dstSize[0], c.dstSize[1], imaging.Linear)
	return sample
}

func (c *RenameConv) TransformSample(sample core.Sample) core.Sample {
	for dstName, srcNames := range c.renames {
		for _, srcName := range srcNames {
			if _, ok := sample[srcName]; ok {
				sample[dstName] = sample[srcName]
				delete(sample, srcName)
			}
		}
	}
	return sample
}

func (s *Select) SelectSample(sample core.Sample) []string {
	return []string{s.key}
}

func (r *SampleToTFExampleReader) Read() (*core.TFExample, error) {
	sample, err := r.SampleReader.Read()
	if err != nil {
		return nil, err
	}

	example := core.NewTFExample()
	for k, v := range sample {
		switch t := v.(type) {
		case image.Image:
			cmn.AssertNoErr(example.AddImage(k, t))
		case []byte:
			example.AddBytes(k, t)
		default:
			b, err := jsoniter.Marshal(v)
			if err != nil {
				return nil, err
			}
			example.AddBytes(k, b)
		}
	}
	return example, nil
}
