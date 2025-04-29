package main

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"

	"github.com/NVIDIA/aistore/cmn/cos"
	"github.com/NVIDIA/aistore/ext/etl"
	"github.com/stretchr/testify/assert"
)

func TestEchoServerPutHandler(t *testing.T) {
	var secretPrefix = "/v1/_object/some_secret"
	os.Setenv("AIS_TARGET_URL", "http://localhost:8080"+secretPrefix)
	svr := NewEchoServer("localhost", 8000)

	t.Run("directPut=none", func(t *testing.T) {
		t.Run("argType=default", func(t *testing.T) {
			svr.argType = etl.ArgTypeDefault
			var (
				body = []byte("test bytes")
				req  = httptest.NewRequest(http.MethodPut, "/", bytes.NewReader(body))
				w    = httptest.NewRecorder()
			)

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusOK, resp.StatusCode)
			assert.Equal(t, body, result)
		})

		t.Run("argType=fqn", func(t *testing.T) {
			svr.argType = etl.ArgTypeFQN
			file, content := createFQNFile(t)
			defer os.Remove(file)

			var (
				path = "/" + url.PathEscape(file)
				req  = httptest.NewRequest(http.MethodPut, path, nil)
				w    = httptest.NewRecorder()
			)

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusOK, resp.StatusCode)
			assert.Equal(t, content, result)
		})
	})

	t.Run("directPut=success", func(t *testing.T) {
		var directPutPath = "ais@#test/obj"
		directPutTargetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			assert.Equal(t, r.Method, http.MethodPut)
			assert.Equal(t, cos.JoinWords(secretPrefix, directPutPath), r.URL.Path)
			w.WriteHeader(http.StatusNoContent)
		}))
		defer directPutTargetServer.Close()

		t.Run("argType=default", func(t *testing.T) {
			svr.argType = etl.ArgTypeDefault
			var (
				content = []byte("test bytes")
				req     = httptest.NewRequest(http.MethodPut, "/", bytes.NewReader(content))
				w       = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusNoContent, resp.StatusCode)
			assert.Equal(t, len(result), 0)
		})

		t.Run("argType=fqn", func(t *testing.T) {
			svr.argType = etl.ArgTypeFQN
			file, _ := createFQNFile(t)
			defer os.Remove(file)

			var (
				path = "/" + url.PathEscape(file)
				req  = httptest.NewRequest(http.MethodPut, path, nil)
				w    = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusNoContent, resp.StatusCode)
			assert.Equal(t, len(result), 0)
		})
	})

	t.Run("directPut=fail", func(t *testing.T) {
		var directPutPath = "ais@#test/obj"
		directPutTargetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			assert.Equal(t, r.Method, http.MethodPut)
			assert.Equal(t, cos.JoinWords(secretPrefix, directPutPath), r.URL.Path)
			w.WriteHeader(http.StatusInternalServerError)
		}))
		defer directPutTargetServer.Close()

		t.Run("argType=default", func(t *testing.T) {
			svr.argType = etl.ArgTypeDefault
			var (
				content = []byte("test bytes")
				req     = httptest.NewRequest(http.MethodPut, "/", bytes.NewReader(content))
				w       = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()

			assert.Equal(t, http.StatusInternalServerError, resp.StatusCode)
		})

		t.Run("argType=fqn", func(t *testing.T) {
			svr.argType = etl.ArgTypeFQN
			file, _ := createFQNFile(t)
			defer os.Remove(file)

			var (
				path = "/" + url.PathEscape(file)
				req  = httptest.NewRequest(http.MethodPut, path, nil)
				w    = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoPutHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()

			assert.Equal(t, http.StatusInternalServerError, resp.StatusCode)
		})
	})
}

func TestEchoServerGetHandler(t *testing.T) {
	var (
		secretPrefix = "/v1/_object/some_secret"
		objUname     = "ais@#test/obj"
		objContent   = []byte("mocked object content")
	)
	localTargetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, r.Method, http.MethodGet)
		assert.Equal(t, cos.JoinWords(secretPrefix, objUname), r.URL.Path)
		w.WriteHeader(http.StatusOK)
		w.Write(objContent)
	}))
	defer localTargetServer.Close()

	os.Setenv("AIS_TARGET_URL", localTargetServer.URL+secretPrefix)
	svr := NewEchoServer("localhost", 8000)

	t.Run("directPut=none", func(t *testing.T) {
		t.Run("argType=default", func(t *testing.T) {
			svr.argType = etl.ArgTypeDefault
			var (
				req = httptest.NewRequest(http.MethodGet, "/"+objUname, nil)
				w   = httptest.NewRecorder()
			)

			svr.echoGetHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusOK, resp.StatusCode)
			assert.Equal(t, objContent, result)
		})

		t.Run("argType=fqn", func(t *testing.T) {
			svr.argType = etl.ArgTypeFQN
			file, content := createFQNFile(t)
			defer os.Remove(file)

			var (
				path = "/" + url.PathEscape(file)
				req  = httptest.NewRequest(http.MethodGet, path, nil)
				w    = httptest.NewRecorder()
			)

			svr.echoGetHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusOK, resp.StatusCode)
			assert.Equal(t, content, result)
		})
	})

	t.Run("directPut=success", func(t *testing.T) {
		var directPutPath = "ais@#test/obj"
		directPutTargetServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			assert.Equal(t, r.Method, http.MethodPut)
			assert.Equal(t, cos.JoinWords(secretPrefix, directPutPath), r.URL.Path)
			w.WriteHeader(http.StatusNoContent)
		}))
		defer directPutTargetServer.Close()

		t.Run("argType=default", func(t *testing.T) {
			svr.argType = etl.ArgTypeDefault
			var (
				req = httptest.NewRequest(http.MethodGet, "/"+objUname, nil)
				w   = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoGetHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusNoContent, resp.StatusCode)
			assert.Equal(t, len(result), 0)
		})

		t.Run("argType=fqn", func(t *testing.T) {
			svr.argType = etl.ArgTypeFQN
			file, _ := createFQNFile(t)
			defer os.Remove(file)

			var (
				path = "/" + url.PathEscape(file)
				req  = httptest.NewRequest(http.MethodGet, path, nil)
				w    = httptest.NewRecorder()
			)
			req.Header = http.Header{"Ais-Node-Url": []string{cos.JoinPath(directPutTargetServer.URL, url.PathEscape(directPutPath))}}

			svr.echoGetHandler(w, req)

			resp := w.Result()
			defer resp.Body.Close()
			result, _ := io.ReadAll(resp.Body)

			assert.Equal(t, http.StatusNoContent, resp.StatusCode)
			assert.Equal(t, len(result), 0)
		})
	})
}

func createFQNFile(t *testing.T) (string, []byte) {
	var content = []byte("mocked file content")
	tmpfile, err := os.CreateTemp("", "mockfile")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	if _, err := tmpfile.Write(content); err != nil {
		t.Fatalf("failed to write to temp file: %v", err)
	}
	tmpfile.Close()
	return tmpfile.Name(), content
}
