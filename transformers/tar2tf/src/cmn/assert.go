// Package cmn common low-level types and utilities
/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 */
package cmn

import (
	"log"
)

func Assert(cond bool, msg string) {
	if !cond {
		panic(msg)
	}
}

func AssertNoErr(err error) {
	if err != nil {
		Assert(false, err.Error())
	}
}

func Exit(err error) {
	if err != nil {
		log.Fatal(err.Error())
	}
}
