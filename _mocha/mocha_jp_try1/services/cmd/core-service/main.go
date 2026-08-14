// core-service runs on ECS in VPC-APP (app-cluster). It is the unified event
// ingestion API and the consolidated read-only API:
//
//	GET  /health     -> health check
//	POST /api/events -> Type-A: synchronous call to worker-service (worker.svc.internal)
//	                    Type-B: asynchronous publish to SQS (events-b-queue)
//	GET  /api/events -> consolidated view of Type-A (via worker) + Type-B (DynamoDB)
//
// Registered in Cloud Map as core.svc.internal.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	sqstypes "github.com/aws/aws-sdk-go-v2/service/sqs/types"

	"github.com/factoryops/services/internal/config"
	"github.com/factoryops/services/internal/event"
	"github.com/factoryops/services/internal/httpx"
)

type server struct {
	http      *http.Client
	sqs       *sqs.Client
	ddb       *dynamodb.Client
	workerURL string
	queueURL  string
	ddbTable  string
}

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)
	log.SetPrefix("[core-service] ")

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

	// SQS/DynamoDB region: env > [sqs] region > [aws] region > SDK default.
	region := conf.Value("AWS_REGION", "sqs", "region", "")
	if region == "" {
		region = conf.Value("AWS_REGION", "aws", "region", "")
	}
	loadOpts := []func(*awsconfig.LoadOptions) error{}
	if region != "" {
		loadOpts = append(loadOpts, awsconfig.WithRegion(region))
	}
	cfg, err := awsconfig.LoadDefaultConfig(context.Background(), loadOpts...)
	if err != nil {
		log.Fatalf("failed to load AWS config: %v", err)
	}

	s := &server{
		http:      &http.Client{Timeout: 15 * time.Second},
		sqs:       sqs.NewFromConfig(cfg),
		ddb:       dynamodb.NewFromConfig(cfg),
		workerURL: conf.Value("WORKER_SERVICE_URL", "services", "worker_service_url", "http://worker.svc.internal:8080"),
		queueURL:  conf.Value("EVENTS_B_QUEUE_URL", "sqs", "queue_url", ""),
		ddbTable:  conf.Value("DDB_TABLE", "dynamodb", "table", "events_operations"),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", httpx.Health("core-service"))
	mux.HandleFunc("/api/events", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			s.ingest(w, r)
		case http.MethodGet:
			s.consolidated(w, r)
		default:
			httpx.Error(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	srv := &http.Server{
		Addr:              addr,
		Handler:           httpx.Logging("core-service", mux),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("listening on %s worker=%s queue=%s ddb=%s", addr, s.workerURL, s.queueURL, s.ddbTable)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop
	log.Println("shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
}

// ingest parses the envelope and routes by type.
func (s *server) ingest(w http.ResponseWriter, r *http.Request) {
	var e event.Event
	if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&e); err != nil {
		httpx.Error(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}
	e.Normalize()
	if err := e.Validate(); err != nil {
		httpx.Error(w, http.StatusBadRequest, err.Error())
		return
	}

	reqID := httpx.RequestID(r)
	switch e.Type {
	case event.TypeA:
		s.routeTypeA(w, r.Context(), reqID, e)
	case event.TypeB:
		s.routeTypeB(w, r.Context(), reqID, e)
	}
}

// routeTypeA forwards synchronously to worker-service and relays its response.
func (s *server) routeTypeA(w http.ResponseWriter, ctx context.Context, reqID string, e event.Event) {
	payload, _ := json.Marshal(e)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.workerURL+"/api/events", bytes.NewReader(payload))
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "failed to build worker request")
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(httpx.RequestIDHeader, reqID)

	resp, err := s.http.Do(req)
	if err != nil {
		httpx.Error(w, http.StatusBadGateway, "worker-service unreachable: "+err.Error())
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	log.Printf("request_id=%s routed Type-A event_id=%s to worker status=%d", reqID, e.EventID, resp.StatusCode)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	_, _ = w.Write(body)
}

// routeTypeB publishes to SQS asynchronously; the Lambda normalizer consumes it.
func (s *server) routeTypeB(w http.ResponseWriter, ctx context.Context, reqID string, e event.Event) {
	if s.queueURL == "" {
		httpx.Error(w, http.StatusInternalServerError, "EVENTS_B_QUEUE_URL not configured")
		return
	}
	payload, _ := json.Marshal(e)
	_, err := s.sqs.SendMessage(ctx, &sqs.SendMessageInput{
		QueueUrl:    aws.String(s.queueURL),
		MessageBody: aws.String(string(payload)),
		MessageAttributes: map[string]sqstypes.MessageAttributeValue{
			"source":     {DataType: aws.String("String"), StringValue: aws.String("core-service")},
			"request_id": {DataType: aws.String("String"), StringValue: aws.String(reqID)},
		},
	})
	if err != nil {
		httpx.Error(w, http.StatusBadGateway, "failed to enqueue Type-B event: "+err.Error())
		return
	}
	log.Printf("request_id=%s enqueued Type-B event_id=%s", reqID, e.EventID)
	httpx.JSON(w, http.StatusAccepted, map[string]any{
		"status":   "accepted",
		"type":     e.Type,
		"event_id": e.EventID,
	})
}

// consolidated merges Type-A (from worker) and Type-B (from DynamoDB).
func (s *server) consolidated(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	reqID := httpx.RequestID(r)

	typeA := s.fetchTypeA(ctx, reqID)
	typeB, err := s.scanTypeB(ctx)
	if err != nil {
		log.Printf("request_id=%s dynamodb scan error: %v", reqID, err)
	}

	httpx.JSON(w, http.StatusOK, map[string]any{
		"type_a": typeA,
		"type_b": typeB,
		"counts": map[string]int{"type_a": len(typeA), "type_b": len(typeB)},
	})
}

func (s *server) fetchTypeA(ctx context.Context, reqID string) []map[string]any {
	out := []map[string]any{}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.workerURL+"/api/events", nil)
	if err != nil {
		return out
	}
	req.Header.Set(httpx.RequestIDHeader, reqID)
	resp, err := s.http.Do(req)
	if err != nil {
		log.Printf("request_id=%s worker fetch error: %v", reqID, err)
		return out
	}
	defer resp.Body.Close()
	var rows []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&rows); err == nil {
		return rows
	}
	return out
}

func (s *server) scanTypeB(ctx context.Context) ([]map[string]any, error) {
	out := []map[string]any{}
	p := dynamodb.NewScanPaginator(s.ddb, &dynamodb.ScanInput{
		TableName: aws.String(s.ddbTable),
	})
	for p.HasMorePages() {
		page, err := p.NextPage(ctx)
		if err != nil {
			return out, err
		}
		var items []map[string]any
		if err := attributevalue.UnmarshalListOfMaps(page.Items, &items); err != nil {
			return out, err
		}
		out = append(out, items...)
	}
	return out, nil
}
