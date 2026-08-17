// ui-service runs on EC2 in VPC-EDGE. It serves the event-visualization web UI
// and exposes the public entry API:
//
//	GET  /              -> web UI
//	GET  /health        -> health check
//	POST /api/events    -> forwards the event to core-service for processing
//	GET  /api/events    -> proxies the consolidated read-only view from core-service
//
// It never talks to datastores directly; everything flows through core-service
// (core.svc.internal) so VPC-EDGE only needs egress to VPC-APP.
package main

import (
	"bytes"
	"context"
	"embed"
	"flag"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/factoryops/services/internal/config"
	"github.com/factoryops/services/internal/httpx"
)

//go:embed web/index.html
var webFS embed.FS

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)
	log.SetPrefix("[ui-service] ")

	configPath := flag.String("config", "", "path to config.ini (default: ./config.ini or next to binary)")
	flag.Parse()

	// Load config.ini. Precedence per setting: env var > config.ini > default.
	conf := config.Load(*configPath)
	if conf.Path != "" {
		log.Printf("loaded configuration from %s", conf.Path)
	} else {
		log.Printf("no config.ini found; using environment variables and defaults")
	}

	addr := ":" + conf.Value("PORT", "server", "port", "8080")
	coreURL := conf.Value("CORE_SERVICE_URL", "services", "core_service_url", "http://core.svc.internal:8080")
	client := &http.Client{Timeout: 15 * time.Second}

	index, err := webFS.ReadFile("web/index.html")
	if err != nil {
		log.Fatalf("failed to load embedded UI: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", httpx.Health("ui-service"))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(index)
	})

	// /api/events: POST forwards for processing, GET proxies the read-only view.
	mux.HandleFunc("/api/events", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost, http.MethodGet:
			proxy(client, coreURL+"/api/events", w, r)
		default:
			httpx.Error(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	srv := &http.Server{
		Addr:              addr,
		Handler:           httpx.Logging("ui-service", mux),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("listening on %s, forwarding to core=%s", addr, coreURL)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	shutdown(srv)
}

// proxy forwards the incoming request to target, propagating the request id and
// streaming the upstream response back to the caller.
func proxy(client *http.Client, target string, w http.ResponseWriter, r *http.Request) {
	var body io.Reader
	if r.Body != nil {
		data, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if err != nil {
			httpx.Error(w, http.StatusBadRequest, "failed to read request body")
			return
		}
		body = bytes.NewReader(data)
	}

	req, err := http.NewRequestWithContext(r.Context(), r.Method, target, body)
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "failed to build upstream request")
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(httpx.RequestIDHeader, httpx.RequestID(r))

	resp, err := client.Do(req)
	if err != nil {
		httpx.Error(w, http.StatusBadGateway, "core-service unreachable: "+err.Error())
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	_, _ = io.Copy(w, resp.Body)
}

func shutdown(srv *http.Server) {
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop
	log.Println("shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
}
