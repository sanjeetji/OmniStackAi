"""R-569: live updates in a generated Go backend (`internal/handlers/realtime.go`).

The same stream as Python's (see `realtime_python.py`): one pgx connection LISTENs, changes fan out
to open Server-Sent Event streams filtered by ownership, and a one-minute ticket opens a stream.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import realtime_sql as q

#: (method, path, handler, guarded) - registered in main.go.
GO_REALTIME_ROUTES = (
    ("POST", "/realtime/ticket", "RealtimeTicket", True),
    ("GET", "/realtime/stream", "RealtimeStream", False),
)


def _go_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def go_realtime_file(ir: ApplicationIR, slug: str) -> str:
    rows = "\n".join(
        f"\t{_go_str(t.table)}: {{Entity: {_go_str(t.entity)}, Owned: {'true' if t.owned else 'false'}, "
        f"SeeAll: []string{{{', '.join(_go_str(r) for r in t.see_all)}}}, Strict: {'true' if t.strict else 'false'}}},"
        for t in q.live_tables(ir)
    )
    config = (
        f"const liveChannel = {_go_str(q.CHANNEL)}\n"
        f"const liveTicketSeconds = {q.TICKET_SECONDS}\n"
        f"const livePingSeconds = {q.PING_SECONDS}\n"
        f"const liveDefaultDSN = {_go_str(f'postgres://localhost:5432/{slug}')}\n\n"
        "var liveTables = map[string]liveTable{\n" + rows + "\n}\n"
    )
    return _GO.replace("__CONFIG__", config)


_GO = r'''package handlers

// Live updates (OmniStackAI R-569): changes to live entities, streamed as they happen.
//
// A trigger publishes each change on the app_changes channel; RunRealtime listens once and sends each
// change to the open streams of the people who may see that record. An event names the entity, the
// operation and the id - the page fetches the record through the API, as it always does.

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
)

type liveTable struct {
	Entity string
	Owned  bool
	SeeAll []string
	Strict bool // a notification is its recipient's alone (PC-053)
}

__CONFIG__
type liveChange struct {
	T, Op, ID, O, A string
}

type liveEvent struct {
	Entity string `json:"entity"`
	Op     string `json:"op"`
	ID     string `json:"id"`
}

type liveHolder struct {
	Sub   string   `json:"sub"`
	Roles []string `json:"roles"`
	Exp   int64    `json:"exp"`
}

type liveStream struct {
	holder   liveHolder
	entities map[string]bool
	ch       chan liveEvent
}

var (
	liveMu      sync.Mutex
	liveStreams = map[*liveStream]struct{}{}
)

func liveSecret() string { return os.Getenv("JWT_SECRET") }

func liveSign(payload string) string {
	mac := hmac.New(sha256.New, []byte(liveSecret()))
	mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}

func liveRoles(raw any) []string {
	out := []string{}
	switch v := raw.(type) {
	case []any:
		for _, r := range v {
			if s, ok := r.(string); ok {
				out = append(out, s)
			}
		}
	case []string:
		out = append(out, v...)
	}
	return out
}

// readLiveTicket returns the ticket's holder, or false when it is forged, malformed or expired.
func readLiveTicket(ticket string, now time.Time) (liveHolder, bool) {
	var holder liveHolder
	payload, signature, found := strings.Cut(ticket, ".")
	if !found || payload == "" || !hmac.Equal([]byte(signature), []byte(liveSign(payload))) {
		return holder, false
	}
	raw, err := base64.RawURLEncoding.DecodeString(payload)
	if err != nil || json.Unmarshal(raw, &holder) != nil || holder.Exp < now.Unix() {
		return holder, false
	}
	return holder, true
}

func liveMayHear(holder liveHolder, change liveChange) bool {
	table, ok := liveTables[change.T]
	if !ok {
		return false
	}
	if !table.Owned {
		return true
	}
	if table.Strict {
		return holder.Sub != "" && holder.Sub == change.A
	}
	for _, role := range holder.Roles {
		if role == "admin" {
			return true
		}
		for _, allowed := range table.SeeAll {
			if role == allowed {
				return true
			}
		}
	}
	return holder.Sub != "" && (holder.Sub == change.O || holder.Sub == change.A)
}

func liveFanOut(payload string) {
	var raw map[string]any
	if json.Unmarshal([]byte(payload), &raw) != nil {
		return
	}
	text := func(key string) string { s, _ := raw[key].(string); return s }
	change := liveChange{T: text("t"), Op: text("op"), ID: text("id"), O: text("o"), A: text("a")}
	table, ok := liveTables[change.T]
	if !ok {
		return
	}
	event := liveEvent{Entity: table.Entity, Op: change.Op, ID: change.ID}
	liveMu.Lock()
	defer liveMu.Unlock()
	for stream := range liveStreams {
		if stream.entities != nil && !stream.entities[table.Entity] {
			continue
		}
		if !liveMayHear(stream.holder, change) {
			continue
		}
		select {
		case stream.ch <- event:
		default: // a stream that cannot keep up is closed; its page reconnects
			delete(liveStreams, stream)
			close(stream.ch)
		}
	}
}

// RunRealtime is started by main.go: it LISTENs for changes and fans them out, reconnecting if the
// database goes away.
func (h *Handlers) RunRealtime() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = liveDefaultDSN
	}
	for {
		ctx := context.Background()
		conn, err := pgx.Connect(ctx, dsn)
		if err == nil {
			_, err = conn.Exec(ctx, "LISTEN "+liveChannel)
			for err == nil {
				note, waitErr := conn.WaitForNotification(ctx)
				if err = waitErr; err == nil {
					liveFanOut(note.Payload)
				}
			}
			conn.Close(ctx)
		}
		log.Printf("realtime: %v", err)
		time.Sleep(2 * time.Second)
	}
}

// RealtimeTicket trades the bearer token for a one-minute ticket to open the stream with.
func (h *Handlers) RealtimeTicket(w http.ResponseWriter, r *http.Request) {
	if liveSecret() == "" {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"detail": "auth_not_configured"})
		return
	}
	claims := ClaimsFrom(r)
	holder := liveHolder{Sub: OwnerOf(claims), Roles: liveRoles(claims["roles"]), Exp: time.Now().Unix() + liveTicketSeconds}
	body, _ := json.Marshal(holder)
	payload := base64.RawURLEncoding.EncodeToString(body)
	writeJSON(w, http.StatusOK, map[string]any{"ticket": payload + "." + liveSign(payload), "expires_in": liveTicketSeconds})
}

// RealtimeStream is a Server-Sent Events stream of the changes this ticket's holder may hear of.
func (h *Handlers) RealtimeStream(w http.ResponseWriter, r *http.Request) {
	holder, ok := readLiveTicket(r.URL.Query().Get("ticket"), time.Now())
	if !ok || liveSecret() == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "invalid_ticket"})
		return
	}
	flusher, ok := w.(http.Flusher)
	if !ok {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"detail": "streaming_unsupported"})
		return
	}
	stream := &liveStream{holder: holder, ch: make(chan liveEvent, 256)}
	if wanted := r.URL.Query().Get("entities"); wanted != "" {
		stream.entities = map[string]bool{}
		for _, name := range strings.Split(wanted, ",") {
			stream.entities[name] = true
		}
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, "event: ready\ndata: {}\n\n")
	flusher.Flush()
	liveMu.Lock()
	liveStreams[stream] = struct{}{}
	liveMu.Unlock()
	defer func() {
		liveMu.Lock()
		if _, open := liveStreams[stream]; open {
			delete(liveStreams, stream)
			close(stream.ch)
		}
		liveMu.Unlock()
	}()
	ping := time.NewTicker(livePingSeconds * time.Second)
	defer ping.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-ping.C:
			fmt.Fprint(w, ": ping\n\n")
			flusher.Flush()
		case event, open := <-stream.ch:
			if !open {
				return
			}
			body, _ := json.Marshal(event)
			fmt.Fprintf(w, "event: change\ndata: %s\n\n", body)
			flusher.Flush()
		}
	}
}
'''
