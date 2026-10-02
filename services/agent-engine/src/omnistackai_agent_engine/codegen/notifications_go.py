"""PC-053: notifications in a generated Go backend (`internal/handlers/notifications.go`).

The same API and outbox as Python's (see `notifications_python.py`); the database writes the
notifications, so the backends agree on who hears of what.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import notifications_sql as q

#: (method, path, handler) - every one behind RequireAuth.
GO_NOTIFICATION_ROUTES = (
    ("GET", "/notifications", "NotificationsInbox"),
    ("GET", "/notifications/unread", "NotificationsUnread"),
    ("POST", "/notifications/read-all", "NotificationsReadAll"),
    ("POST", "/notifications/{notificationId}/read", "NotificationsRead"),
    ("GET", "/notifications/preferences", "NotificationsPreferences"),
    ("PUT", "/notifications/preferences", "NotificationsSetPreference"),
)


def _go_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _raw(value: str) -> str:
    assert "`" not in value
    return f"`{value}`"


def go_notifications_file(ir: ApplicationIR) -> str:
    rules = "\n".join(
        f"\t{{Rule: {_go_str(r.rule)}, Label: {_go_str(r.label)}, Channels: []string{{{', '.join(_go_str(c) for c in r.channels)}}}, "
        f"OnlyRoles: []string{{{', '.join(_go_str(x) for x in r.only_roles)}}}}},"
        for r in q.rule_catalogue(ir)
    )
    config = (
        "var notificationRules = []notificationRule{\n" + rules + "\n}\n\n"
        "const (\n"
        f"\tsqlClaimEmails = {_raw(q.CLAIM_EMAILS)}\n"
        f"\tsqlEmailSent = {_raw(q.EMAIL_SENT)}\n"
        f"\tsqlEmailSkipped = {_raw(q.EMAIL_SKIPPED)}\n"
        f"\tsqlEmailFailed = {_raw(q.EMAIL_FAILED)}\n"
        f"\tsqlInbox = {_raw(q.INBOX)}\n"
        f"\tsqlInboxUnread = {_raw(q.INBOX_UNREAD)}\n"
        f"\tsqlUnreadCount = {_raw(q.UNREAD_COUNT)}\n"
        f"\tsqlMarkRead = {_raw(q.MARK_READ)}\n"
        f"\tsqlMarkAllRead = {_raw(q.MARK_ALL_READ)}\n"
        f"\tsqlMutes = {_raw(q.MUTES)}\n"
        f"\tsqlMute = {_raw(q.MUTE)}\n"
        f"\tsqlUnmute = {_raw(q.UNMUTE)}\n"
        ")\n"
    )
    return _GO.replace("__CONFIG__", config)


_GO = r'''package handlers

// Notifications (OmniStackAI PC-053): a person's own, their preferences, and the email outbox.
//
// The database writes each notification (a trigger per entity, a reminder per schedule), leaving out the
// channels its recipient muted. In-app ones reach the bell live (R-569); emails wait in the outbox here.

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

type notificationRule struct {
	Rule      string   `json:"rule"`
	Label     string   `json:"label"`
	Channels  []string `json:"channels"`
	OnlyRoles []string `json:"-"` // a rule only for some roles is offered to them alone
}

__CONFIG__
type notificationRow struct {
	ID        string     `json:"id"`
	Rule      string     `json:"rule"`
	Entity    string     `json:"entity"`
	RecordID  *string    `json:"record_id"`
	Title     string     `json:"title"`
	Body      string     `json:"body"`
	ReadAt    *time.Time `json:"read_at"`
	CreatedAt time.Time  `json:"created_at"`
}

// notificationsMe is the signed-in account's id; the development session has none.
func notificationsMe(w http.ResponseWriter, r *http.Request) (string, bool) {
	me := OwnerOf(ClaimsFrom(r))
	if me == "" {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "sign in with an account"})
		return "", false
	}
	return me, true
}

func (h *Handlers) NotificationsInbox(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	query := sqlInbox
	if v := r.URL.Query().Get("unread"); v == "1" || v == "true" {
		query = sqlInboxUnread
	}
	rows, err := h.DB.QueryContext(r.Context(), query, me)
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	out := []notificationRow{}
	for rows.Next() {
		var n notificationRow
		if err := rows.Scan(&n.ID, &n.Rule, &n.Entity, &n.RecordID, &n.Title, &n.Body, &n.ReadAt, &n.CreatedAt); err != nil {
			dbError(w, err)
			return
		}
		out = append(out, n)
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handlers) NotificationsUnread(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	var count int64
	if err := h.DB.QueryRowContext(r.Context(), sqlUnreadCount, me).Scan(&count); err != nil {
		dbError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]int64{"count": count})
}

func (h *Handlers) NotificationsReadAll(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	res, err := h.DB.ExecContext(r.Context(), sqlMarkAllRead, me)
	if err != nil {
		dbError(w, err)
		return
	}
	updated, _ := res.RowsAffected()
	writeJSON(w, http.StatusOK, map[string]int64{"updated": updated})
}

func (h *Handlers) NotificationsRead(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	id := r.PathValue("notificationId")
	var got string
	if err := h.DB.QueryRowContext(r.Context(), sqlMarkRead, id, me).Scan(&got); err != nil {
		if strings.Contains(err.Error(), "no rows") {
			writeJSON(w, http.StatusNotFound, map[string]string{"detail": "not_found"})
			return
		}
		dbError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"id": id, "read": true})
}

func (h *Handlers) NotificationsPreferences(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	rows, err := h.DB.QueryContext(r.Context(), sqlMutes, me)
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	muted := map[string]bool{}
	allMuted := []string{}
	for rows.Next() {
		var rule, channel string
		if err := rows.Scan(&rule, &channel); err != nil {
			dbError(w, err)
			return
		}
		muted[rule+"\x00"+channel] = true
		if rule == "*" {
			allMuted = append(allMuted, channel)
		}
	}
	sort.Strings(allMuted)
	held := map[string]bool{}
	for _, role := range liveRoles(ClaimsFrom(r)["roles"]) {
		held[role] = true
	}
	out := []map[string]any{}
	for _, rule := range notificationRules {
		offered := len(rule.OnlyRoles) == 0
		for _, role := range rule.OnlyRoles {
			offered = offered || held[role]
		}
		if !offered {
			continue
		}
		ruleMuted := []string{}
		for _, channel := range rule.Channels {
			if muted[rule.Rule+"\x00"+channel] {
				ruleMuted = append(ruleMuted, channel)
			}
		}
		sort.Strings(ruleMuted)
		out = append(out, map[string]any{"rule": rule.Rule, "label": rule.Label, "channels": rule.Channels, "muted": ruleMuted})
	}
	writeJSON(w, http.StatusOK, map[string]any{"all_muted": allMuted, "rules": out})
}

func (h *Handlers) NotificationsSetPreference(w http.ResponseWriter, r *http.Request) {
	me, ok := notificationsMe(w, r)
	if !ok {
		return
	}
	var body struct {
		Rule    string `json:"rule"`
		Channel string `json:"channel"`
		Muted   bool   `json:"muted"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "invalid body"})
		return
	}
	known := body.Rule == "*"
	for _, rule := range notificationRules {
		known = known || rule.Rule == body.Rule
	}
	if !known || (body.Channel != "in_app" && body.Channel != "email") {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "unknown rule or channel"})
		return
	}
	query := sqlUnmute
	if body.Muted {
		query = sqlMute
	}
	if _, err := h.DB.ExecContext(r.Context(), query, me, body.Rule, body.Channel); err != nil {
		dbError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"rule": body.Rule, "channel": body.Channel, "muted": body.Muted})
}

// --- the email outbox ------------------------------------------------------------------------------

func sendNotificationEmail(to, subject, text string) error {
	url := os.Getenv("EMAIL_API_URL")
	if url == "" {
		url = "https://api.resend.com/emails"
	}
	if text == "" {
		text = subject
	}
	payload, _ := json.Marshal(map[string]any{"from": os.Getenv("EMAIL_FROM"), "to": []string{to}, "subject": subject, "text": text})
	request, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	request.Header.Set("Authorization", "Bearer "+os.Getenv("RESEND_API_KEY"))
	request.Header.Set("Content-Type", "application/json")
	response, err := (&http.Client{Timeout: 15 * time.Second}).Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode >= 300 {
		return fmt.Errorf("email provider answered %d", response.StatusCode)
	}
	return nil
}

// sendDueEmails sends what is due in the outbox.
func (h *Handlers) sendDueEmails(ctx context.Context) error {
	rows, err := h.DB.QueryContext(ctx, sqlClaimEmails)
	if err != nil {
		return err
	}
	type due struct{ id, title, body, email string }
	batch := []due{}
	for rows.Next() {
		var d due
		var attempts int
		if err := rows.Scan(&d.id, &d.title, &d.body, &attempts, &d.email); err != nil {
			rows.Close()
			return err
		}
		batch = append(batch, d)
	}
	rows.Close()
	configured := os.Getenv("RESEND_API_KEY") != "" && os.Getenv("EMAIL_FROM") != ""
	for _, d := range batch {
		if !configured {
			_, _ = h.DB.ExecContext(ctx, sqlEmailSkipped, "email is not configured (RESEND_API_KEY, EMAIL_FROM)", d.id)
			continue
		}
		if err := sendNotificationEmail(d.email, d.title, d.body); err != nil {
			message := err.Error()
			if len(message) > 500 {
				message = message[:500]
			}
			_, _ = h.DB.ExecContext(ctx, sqlEmailFailed, message, d.id)
			log.Printf("notification email failed: %v", err)
			continue
		}
		_, _ = h.DB.ExecContext(ctx, sqlEmailSent, d.id)
	}
	return nil
}

// RunNotifications is started by main.go: it sends the outbox every NOTIFICATIONS_EMAIL_SECONDS (10).
func (h *Handlers) RunNotifications() {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("NOTIFICATIONS_EMAIL_DISABLED"))) {
	case "1", "true", "yes":
		return
	}
	interval := 10 * time.Second
	if v, err := strconv.ParseFloat(os.Getenv("NOTIFICATIONS_EMAIL_SECONDS"), 64); err == nil && v >= 1 {
		interval = time.Duration(v * float64(time.Second))
	}
	for {
		if err := h.sendDueEmails(context.Background()); err != nil {
			log.Printf("notifications: %v", err)
		}
		time.Sleep(interval)
	}
}
'''
