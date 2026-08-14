// worker-service runs on ECS in VPC-DATA (worker-cluster). It validates Type-A
// (order) events and persists them idempotently to Aurora PostgreSQL through
// RDS Proxy:
//
//	GET  /health     -> health check (also pings the database)
//	POST /api/events -> validate + persist a Type-A event to Aurora
//	GET  /api/events -> return persisted Type-A events
//
// Registered in Cloud Map as worker.svc.internal. Connect to Aurora ONLY via
// the RDS Proxy endpoint (DB_HOST).
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/lib/pq"

	"github.com/factoryops/services/internal/config"
	"github.com/factoryops/services/internal/event"
	"github.com/factoryops/services/internal/httpx"
)

const createTableDDL = `
CREATE TABLE IF NOT EXISTS events_orders (
    event_id   VARCHAR(64) PRIMARY KEY,
    order_id   VARCHAR(64) NOT NULL,
    amount     NUMERIC(12,2) NOT NULL,
    ts         TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);`

type server struct {
	db     *sql.DB
	dbHost string
	dbPort string
}

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)
	log.SetPrefix("[worker-service] ")

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

	db, host, port, err := openDB(conf)
	if err != nil {
		log.Fatalf("database init failed: %v", err)
	}
	defer db.Close()

	s := &server{db: db, dbHost: host, dbPort: port}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/api/events", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			s.save(w, r)
		case http.MethodGet:
			s.list(w, r)
		default:
			httpx.Error(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	srv := &http.Server{
		Addr:              addr,
		Handler:           httpx.Logging("worker-service", mux),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("listening on %s", addr)
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

// tcpCheck verifies that host:port accepts a TCP connection. RDS / RDS Proxy
// endpoints do not answer ICMP, so we probe the port rather than "ping" them.
func tcpCheck(host, port string, timeout time.Duration) error {
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, port), timeout)
	if err != nil {
		return err
	}
	_ = conn.Close()
	return nil
}

// openDB builds a connection to Aurora via RDS Proxy and ensures the table.
// Credentials are resolved with precedence: env var > config.ini > default.
// Reachability is verified with a TCP connection check (not a DB/ICMP ping).
func openDB(conf *config.Config) (*sql.DB, string, string, error) {
	host := conf.Value("DB_HOST", "database", "host", "localhost")
	port := conf.Value("DB_PORT", "database", "port", "5432")
	name := conf.Value("DB_NAME", "database", "name", "factoryops")
	user := conf.Value("DB_USER", "database", "user", "postgres")
	pass := conf.Value("DB_PASSWORD", "database", "password", "")
	sslmode := conf.Value("DB_SSLMODE", "database", "sslmode", "require")

	dsn := fmt.Sprintf("host=%s port=%s dbname=%s user=%s password=%s sslmode=%s connect_timeout=10",
		host, port, name, user, pass, sslmode)

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, host, port, err
	}
	// Keep the pool modest; RDS Proxy multiplexes connections behind it.
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	// Reachability check over TCP (works against RDS Proxy, unlike ICMP ping).
	if err := tcpCheck(host, port, 10*time.Second); err != nil {
		return nil, host, port, fmt.Errorf("tcp connect to %s:%s failed: %w", host, port, err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	if _, err := db.ExecContext(ctx, createTableDDL); err != nil {
		return nil, host, port, fmt.Errorf("create table: %w", err)
	}
	log.Printf("connected to Aurora via %s:%s db=%s (tcp ok, table ready)", host, port, name)
	return db, host, port, nil
}

// health reports readiness using a TCP connection check to the RDS Proxy
// endpoint (no DB ping / ICMP), keeping the check cheap and proxy-friendly.
func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if err := tcpCheck(s.dbHost, s.dbPort, 3*time.Second); err != nil {
		httpx.JSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unhealthy", "service": "worker-service", "error": err.Error(),
		})
		return
	}
	httpx.JSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "worker-service"})
}

// save validates a Type-A event and inserts it idempotently. Duplicate
// event_ids (out-of-order / redelivered events) are ignored via ON CONFLICT.
func (s *server) save(w http.ResponseWriter, r *http.Request) {
	var e event.Event
	if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&e); err != nil {
		httpx.Error(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return
	}
	e.Type = event.TypeA
	e.Normalize()
	if err := e.Validate(); err != nil {
		httpx.Error(w, http.StatusBadRequest, err.Error())
		return
	}

	ts, err := event.ParseTimestamp(e.TS)
	if err != nil {
		httpx.Error(w, http.StatusBadRequest, "invalid ts: "+err.Error())
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	res, err := s.db.ExecContext(ctx,
		`INSERT INTO events_orders (event_id, order_id, amount, ts)
		 VALUES ($1, $2, $3, $4)
		 ON CONFLICT (event_id) DO NOTHING`,
		e.EventID, e.OrderID, e.Amount, ts.UTC())
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "database error: "+err.Error())
		return
	}

	rows, _ := res.RowsAffected()
	status := "saved"
	if rows == 0 {
		status = "duplicate_ignored" // idempotent replay
	}
	log.Printf("request_id=%s Type-A event_id=%s %s", httpx.RequestID(r), e.EventID, status)
	httpx.JSON(w, http.StatusOK, map[string]any{
		"status":   status,
		"event_id": e.EventID,
		"order_id": e.OrderID,
		"amount":   e.Amount,
		"ts":       ts.UTC().Format(time.RFC3339),
	})
}

func (s *server) list(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	rows, err := s.db.QueryContext(ctx,
		`SELECT event_id, order_id, amount, ts, created_at
		 FROM events_orders ORDER BY created_at DESC LIMIT 500`)
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "database error: "+err.Error())
		return
	}
	defer rows.Close()

	out := []map[string]any{}
	for rows.Next() {
		var (
			eventID, orderID string
			amount           float64
			ts, createdAt    time.Time
		)
		if err := rows.Scan(&eventID, &orderID, &amount, &ts, &createdAt); err != nil {
			httpx.Error(w, http.StatusInternalServerError, "scan error: "+err.Error())
			return
		}
		out = append(out, map[string]any{
			"event_id":   eventID,
			"order_id":   orderID,
			"amount":     amount,
			"ts":         ts.UTC().Format(time.RFC3339),
			"created_at": createdAt.UTC().Format(time.RFC3339),
		})
	}
	httpx.JSON(w, http.StatusOK, out)
}
