// Package httpx holds small HTTP helpers shared by the services: JSON
// responses, a health handler, and logging middleware that also propagates a
// request/trace id for cross-service traceability.
package httpx

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// RequestIDHeader is propagated between services so a single request can be
// traced end-to-end (ui -> core -> worker) in the logs.
const RequestIDHeader = "X-Request-Id"

// JSON writes v as an application/json response with the given status code.
func JSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// Error writes a JSON error body.
func Error(w http.ResponseWriter, status int, msg string) {
	JSON(w, status, map[string]string{"error": msg})
}

// Health returns a handler for GET /health.
func Health(service string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		JSON(w, http.StatusOK, map[string]string{"status": "ok", "service": service})
	}
}

// RequestID returns the incoming request id or generates a new one.
func RequestID(r *http.Request) string {
	if id := r.Header.Get(RequestIDHeader); id != "" {
		return id
	}
	b := make([]byte, 8)
	if _, err := rand.Read(b); err != nil {
		return "req-unknown"
	}
	return "req-" + hex.EncodeToString(b)
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

// Logging wraps a handler, logging each request to stdout with method, path,
// status, latency, and the propagated request id. Logs go to stdout/stderr so
// they are available for troubleshooting (per the document).
func Logging(service string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := RequestID(r)
		w.Header().Set(RequestIDHeader, id)
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		start := time.Now()
		next.ServeHTTP(rec, r)
		log.Printf("service=%s request_id=%s method=%s path=%s status=%d duration=%s remote=%s",
			service, id, r.Method, r.URL.Path, rec.status, time.Since(start), r.RemoteAddr)
	})
}

// Env reads an environment variable falling back to def when empty.
func Env(getenv func(string) string, key, def string) string {
	if v := getenv(key); v != "" {
		return v
	}
	return def
}
