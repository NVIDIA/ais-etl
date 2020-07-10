package main

import (
	"flag"
	"fmt"
	"html"
	"io"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/NVIDIA/go-tfdata/tfdata/pipeline"
)

var (
	aisTargetUrl string
	endpoint string

	client *http.Client
)

func main() {
	var (
		ipAddress = flag.String("l", "localhost", "Specify the IP address on which the server listens")
		port = flag.Int("p", 8000, "Specify the port on which the server listens")
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
	if err := transform(r.Body, w, isTarGzRequest(r)); err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, "failed transforming TAR: %s", err.Error())
	}
}

func tar2tfGetHandler(w http.ResponseWriter, r *http.Request) {
	escaped := html.EscapeString(r.URL.Path)
	escaped = strings.TrimPrefix(escaped, "/")

	split := strings.SplitN(escaped, "/", 2)
	if len(split) < 2 {
		invalidMsgHandler(w, http.StatusBadRequest, "expected 2 path elements")
		return
	}

	bucket, object := split[0], split[1]

	if aisTargetUrl == "" {
		invalidMsgHandler(w, http.StatusBadRequest, "missing env variable AIS_TARGET_URL")
		return
	}

	resp, err := client.Get(fmt.Sprintf("%s/%s/%s", aisTargetUrl, bucket, object))
	if err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := transform(resp.Body, w, isTarGzRequest(r)); err != nil {
		invalidMsgHandler(w, http.StatusBadRequest, err.Error())
	}
}

func transform(r io.ReadCloser, w io.Writer, tarGz bool) error {
	p := pipeline.NewPipeline()
	if tarGz {
		p.FromTarGz(r)
	} else {
		p.FromTar(r)
	}
	defer r.Close()
	return p.SampleToTFExample().ToTFRecord(w).Do()
}

func invalidMsgHandler(w http.ResponseWriter, errCode int, format string, a ...interface{}) {
	w.Header().Set("Content-type", "application/json")
	w.WriteHeader(errCode)
	w.Write([]byte(fmt.Sprintf(format, a...)))
}

func isTarGzRequest(r *http.Request) bool {
	arTy := strings.ToUpper(r.URL.Query().Get("archive_type"))
	return arTy == "TAR.GZ" || arTy == "TARGZ" || arTy == "TGZ"
}
