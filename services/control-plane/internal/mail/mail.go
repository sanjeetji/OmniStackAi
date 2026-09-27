// Package mail sends the platform's own email: verification and password-reset links (PC-012).
//
// Through Resend when RESEND_API_KEY and EMAIL_FROM are set (keys last: PC-070). Without them, in
// dev mode (OMNISTACKAI_DEV_MODE=1) the message is written to the server log so a developer can
// follow the link; outside dev mode nothing is logged but the fact that email is not configured —
// a reset link in a production log would be a way into someone's account.
package mail

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"
)

// Mailer sends one plain-text email.
type Mailer interface {
	Send(ctx context.Context, to, subject, text string) error
}

// FromEnv picks Resend, the dev-mode log, or a mailer that reports it is not configured.
func FromEnv(logger *slog.Logger) Mailer {
	key, from := strings.TrimSpace(os.Getenv("RESEND_API_KEY")), strings.TrimSpace(os.Getenv("EMAIL_FROM"))
	if key != "" && from != "" {
		return &Resend{APIKey: key, From: from, BaseURL: "https://api.resend.com", Client: &http.Client{Timeout: 15 * time.Second}}
	}
	if os.Getenv("OMNISTACKAI_DEV_MODE") == "1" {
		return DevLog{Logger: logger}
	}
	return NotConfigured{Logger: logger}
}

// Resend sends through Resend's API.
type Resend struct {
	APIKey, From, BaseURL string
	Client                *http.Client
}

func (r *Resend) Send(ctx context.Context, to, subject, text string) error {
	body, _ := json.Marshal(map[string]any{"from": r.From, "to": []string{to}, "subject": subject, "text": text})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.BaseURL+"/emails", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+r.APIKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := r.Client.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode/100 != 2 {
		return fmt.Errorf("mail: Resend answered %d", resp.StatusCode)
	}
	return nil
}

// DevLog writes the message to the log (dev mode only).
type DevLog struct{ Logger *slog.Logger }

func (d DevLog) Send(_ context.Context, to, subject, text string) error {
	d.Logger.Warn("email not configured; dev mode shows it here", "to", to, "subject", subject, "body", text)
	return nil
}

// NotConfigured sends nothing and logs no content.
type NotConfigured struct{ Logger *slog.Logger }

func (n NotConfigured) Send(_ context.Context, _ string, subject, _ string) error {
	n.Logger.Error("email is not configured (RESEND_API_KEY, EMAIL_FROM); message not sent", "subject", subject)
	return nil
}
