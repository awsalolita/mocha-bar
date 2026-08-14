// Package event defines the shared event envelope used across the FactoryOps
// platform (ui-service -> core-service -> worker-service / SQS) and the
// validation rules described in the Test Project document.
package event

import (
	"errors"
	"fmt"
	"strings"
	"time"
)

// Type identifiers for the two event categories.
const (
	TypeA = "A" // Order event   -> worker-service -> RDS Proxy -> Aurora
	TypeB = "B" // Operation event -> SQS -> Lambda -> DynamoDB
)

// Event is the unified envelope accepted by the ingestion API. A single struct
// carries the fields for both categories; only the relevant subset is used per
// type. Field names mirror the datastore columns/attributes in the document.
type Event struct {
	Type    string `json:"type"`
	EventID string `json:"event_id"`
	TS      string `json:"ts"`

	// Type-A (order) fields.
	OrderID string  `json:"order_id,omitempty"`
	Amount  float64 `json:"amount,omitempty"`

	// Type-B (operation) fields.
	Operator  string `json:"operator,omitempty"`
	Operation string `json:"operation,omitempty"`
}

// Normalize trims text fields and normalizes the timestamp to RFC3339/ISO8601
// in UTC. It mirrors the normalization the document asks the Lambda to perform
// for Type-B and is safe to apply to Type-A as well.
func (e *Event) Normalize() {
	e.Type = strings.ToUpper(strings.TrimSpace(e.Type))
	e.EventID = strings.TrimSpace(e.EventID)
	e.OrderID = strings.TrimSpace(e.OrderID)
	e.Operator = strings.TrimSpace(e.Operator)
	e.Operation = strings.ToUpper(strings.TrimSpace(e.Operation))

	if ts := strings.TrimSpace(e.TS); ts != "" {
		if parsed, err := ParseTimestamp(ts); err == nil {
			e.TS = parsed.UTC().Format(time.RFC3339)
		} else {
			e.TS = ts
		}
	} else {
		e.TS = time.Now().UTC().Format(time.RFC3339)
	}
}

// Validate applies the rules common to every event plus the per-type rules.
func (e *Event) Validate() error {
	if e.EventID == "" {
		return errors.New("event_id is required")
	}
	switch e.Type {
	case TypeA:
		return e.validateA()
	case TypeB:
		return e.validateB()
	default:
		return fmt.Errorf("unknown event type %q (expected A or B)", e.Type)
	}
}

func (e *Event) validateA() error {
	if e.OrderID == "" {
		return errors.New("order_id is required for Type-A")
	}
	if e.Amount <= 0 {
		return errors.New("amount must be greater than 0 for Type-A")
	}
	if _, err := ParseTimestamp(e.TS); err != nil {
		return fmt.Errorf("invalid ts for Type-A: %w", err)
	}
	return nil
}

// validateB enforces the Type-B rules from the document:
//   - orderId must start with ORD-
//   - operator must start with op- or operator-
//   - operation must be PACK or SHIP
func (e *Event) validateB() error {
	if !strings.HasPrefix(e.OrderID, "ORD-") {
		return errors.New("order_id must start with ORD- for Type-B")
	}
	if !(strings.HasPrefix(e.Operator, "op-") || strings.HasPrefix(e.Operator, "operator-")) {
		return errors.New("operator must start with op- or operator- for Type-B")
	}
	if e.Operation != "PACK" && e.Operation != "SHIP" {
		return errors.New("operation must be PACK or SHIP for Type-B")
	}
	if _, err := ParseTimestamp(e.TS); err != nil {
		return fmt.Errorf("invalid ts for Type-B: %w", err)
	}
	return nil
}

// ParseTimestamp accepts a few common timestamp encodings and returns a time.
func ParseTimestamp(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	layouts := []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
		"2006-01-02",
	}
	var lastErr error
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, nil
		} else {
			lastErr = err
		}
	}
	return time.Time{}, fmt.Errorf("unrecognized timestamp %q: %w", s, lastErr)
}
