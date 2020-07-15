package main

import (
	"bytes"
	"flag"
	"fmt"
	"html"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

var (
	aisTargetUrl string
	endpoint     string

	client *http.Client
)

func main() {
	var (
		ipAddress = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		port      = flag.Int("p", 8000, "Specify the port on which the server listens")
	)

	flag.Parse()
	endpoint = fmt.Sprintf("%s:%d", *ipAddress, *port)
	aisTargetUrl = os.Getenv("AIS_TARGET_URL")
	client = &http.Client{}

	http.HandleFunc("/", tar2tfHandler)

	log.Printf("Starting tar2tf transformer at %s", endpoint)
	log.Fatal(http.ListenAndServe(endpoint, nil))
}

func tar2tfHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		tar2tfPostHandler(w, r)
	case http.MethodGet:
		tar2tfGetHandler(w, r)
	default:
		invalidMsgHandler(w, http.StatusBadRequest, "invalid http method %s", r.Method)
	}
}

func tar2tfPostHandler(w http.ResponseWriter, r *http.Request) {
	if err := onTheFlyTransform(r, w); err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, "failed transforming TAR: %s", err.Error())
	}
}

func tar2tfGetHandler(w http.ResponseWriter, r *http.Request) {
	escaped := html.EscapeString(r.URL.Path)
	escaped = strings.TrimPrefix(escaped, "/")

	apiItems := strings.SplitN(escaped, "/", 4)
	if len(apiItems) < 4 {
		invalidMsgHandler(w, http.StatusBadRequest, "expected 2 path elements")
		return
	}

	// AIS GET object API path
	assert(apiItems[0] == "v1", "")
	assert(apiItems[1] == "objects", "")

	if aisTargetUrl == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	obj := &tarObject{
		bucket: apiItems[2],
		name:   apiItems[3],
		tarGz:  isTarGzRequest(r),
	}

	// Make sure that transformed TFRecord exists - if it doesn't, get TAR from a target
	// and transform it to TFRecord.
	tfRecord, version, err := transformFromRemoteOrPass(obj)
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}

	// Extract the requested bytes range from a header.
	rng, err := objectRange(r.Header.Get(HeaderRange), fsTFRecordSize(tfRecord))
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}
	setResponseHeaders(w.Header(), rng.Length, version)

	// Read only selected range from a TFRecord file
	reader, err := tfRecordChunkReader(tfRecord, rng.Start, rng.Length)
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}

	_, err = io.Copy(w, reader)
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}
}

// TODO: We might be able to cache this results, however it would require setting
// object name and bucket name in the headers, on the target side.
func onTheFlyTransform(req *http.Request, responseWriter http.ResponseWriter) error {
	rangeStr := req.Header.Get(HeaderRange)
	if rangeStr == "" {
		return onTheFlyTransformWholeObject(req, responseWriter)
	}

	var (
		buff    = bytes.NewBuffer(nil)
		counter = &writeCounter{}
		w       = io.MultiWriter(buff, counter)
	)

	defer req.Body.Close()
	if err := defaultPipeline(req.Body, w, isTarGzRequest(req)).Do(); err != nil {
		return err
	}

	rng, err := objectRange(rangeStr, counter.Size())
	if err != nil {
		return err
	}

	n, err := copySection(buff, responseWriter, rng.Start, rng.Length)
	if err != nil {
		return err
	}

	setResponseHeaders(responseWriter.Header(), n, req.Header.Get(HeaderVersion))
	return nil
}

func onTheFlyTransformWholeObject(req *http.Request, responseWriter io.Writer) error {
	defer req.Body.Close()
	return defaultPipeline(req.Body, responseWriter, isTarGzRequest(req)).Do()
}

func isTarGzRequest(r *http.Request) bool {
	arTy := strings.ToUpper(r.URL.Query().Get("archive_type"))
	return arTy == "TAR.GZ" || arTy == "TARGZ" || arTy == "TGZ"
}
