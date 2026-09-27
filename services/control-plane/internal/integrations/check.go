// Package integrations is the verified integrations catalog (PC-013): one list of everything a
// project or account can connect, and a health test for each that asks the provider itself
// whether the saved credentials work. A test never runs a model, sends an email or charges
// anything, and its answer never contains the credential.
package integrations

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/smtp"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// Status is a health test's verdict.
type Status string

const (
	// OK: the provider accepted the credentials.
	OK Status = "ok"
	// Failed: the provider refused them, or the settings cannot work.
	Failed Status = "failed"
	// Unchecked: no answer either way (provider unreachable or rate limiting, or no free check
	// exists); nothing is claimed.
	Unchecked Status = "unchecked"
)

// Result is one health test's answer.
type Result struct {
	Integration string    `json:"integration"`
	Status      Status    `json:"status"`
	Message     string    `json:"message"`
	CheckedAt   time.Time `json:"checked_at"`
}

// Checker runs health tests. The zero value calls the real providers.
type Checker struct {
	Client *http.Client
	// BaseURL, when set, replaces every provider's origin (tests only).
	BaseURL string
	// AllowPrivate lets a mail server on a private or loopback address be tested (local
	// development only); otherwise a user's settings cannot be used to probe the platform's network.
	AllowPrivate bool
	// Resolve looks a host up (tests may replace it).
	Resolve func(ctx context.Context, host string) ([]net.IP, error)
	Now     func() time.Time
}

func (c Checker) client() *http.Client {
	if c.Client != nil {
		return c.Client
	}
	return &http.Client{Timeout: 15 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error {
		return http.ErrUseLastResponse
	}}
}

func (c Checker) now() time.Time {
	if c.Now != nil {
		return c.Now()
	}
	return time.Now()
}

func (c Checker) origin(real string) string {
	if c.BaseURL != "" {
		return strings.TrimRight(c.BaseURL, "/")
	}
	return real
}

// Check tests one integration with its settings (field keys as the catalog names them).
func (c Checker) Check(ctx context.Context, integration string, cfg map[string]string) Result {
	status, message := c.check(ctx, integration, cfg)
	return Result{Integration: integration, Status: status, Message: message, CheckedAt: c.now().UTC()}
}

func (c Checker) check(ctx context.Context, integration string, cfg map[string]string) (Status, string) {
	get := func(k string) string { return strings.TrimSpace(cfg[k]) }
	switch integration {
	case "ga4":
		id := strings.ToUpper(get("measurement_id"))
		if !regexp.MustCompile(`^G-[A-Z0-9]{6,16}$`).MatchString(id) {
			return Failed, "That is not a Measurement ID (they look like G-XXXXXXXXXX)."
		}
		return Unchecked, "The Measurement ID is well formed. Google has no way to confirm it without your Google account: open Realtime in Google Analytics after the app gets a visit."
	case "resend":
		return c.resend(ctx, get("api_key"), get("from_email"))
	case "smtp":
		return c.smtp(ctx, get("host"), get("port"), get("username"), get("password"))
	case "stripe":
		return c.stripe(ctx, get("secret_key"), get("publishable_key"), get("webhook_secret"))
	case "razorpay":
		return c.razorpay(ctx, get("key_id"), get("key_secret"))
	}
	if strings.HasPrefix(integration, "ai:") {
		return c.aiKey(ctx, strings.TrimPrefix(integration, "ai:"), get("api_key"))
	}
	return Unchecked, "There is no health test for this integration."
}

// call makes one request and returns the status code and (bounded) body. Errors never carry the
// credential: it is only ever in a header.
func (c Checker) call(ctx context.Context, method, url string, header map[string]string, basicUser, basicPass string) (int, []byte, error) {
	req, err := http.NewRequestWithContext(ctx, method, url, nil)
	if err != nil {
		return 0, nil, err
	}
	for k, v := range header {
		req.Header.Set(k, v)
	}
	if basicUser != "" {
		req.SetBasicAuth(basicUser, basicPass)
	}
	resp, err := c.client().Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer func() { _ = resp.Body.Close() }()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 256<<10))
	return resp.StatusCode, body, nil
}

// verdict turns a provider's answer to a read-only request into a status.
func verdict(name string, code int, err error) (Status, string, bool) {
	switch {
	case err != nil:
		return Unchecked, fmt.Sprintf("%s could not be reached just now. Nothing was decided; try again.", name), false
	case code == http.StatusUnauthorized || code == http.StatusForbidden:
		return Failed, fmt.Sprintf("%s refused the key. Check it was copied whole and has not been revoked.", name), false
	case code == http.StatusTooManyRequests:
		return Unchecked, fmt.Sprintf("%s is limiting requests just now; try again in a minute.", name), false
	case code >= 200 && code < 300:
		return OK, "", true
	default:
		return Unchecked, fmt.Sprintf("%s answered %d; nothing was decided.", name, code), false
	}
}

func (c Checker) resend(ctx context.Context, key, from string) (Status, string) {
	if key == "" {
		return Failed, "No Resend API key is saved."
	}
	code, body, err := c.call(ctx, http.MethodGet, c.origin("https://api.resend.com")+"/domains",
		map[string]string{"Authorization": "Bearer " + key}, "", "")
	if code == http.StatusUnauthorized && strings.Contains(string(body), "restricted_api_key") {
		// A sending-only key cannot list domains - but Resend recognised it.
		return OK, "Resend accepted the key (a sending-only key, so its domains cannot be listed)."
	}
	if code == http.StatusBadRequest && strings.Contains(string(body), "API key is invalid") {
		code = http.StatusUnauthorized // Resend's answer for an unknown key
	}
	status, message, ok := verdict("Resend", code, err)
	if !ok {
		return status, message
	}
	var list struct {
		Data []struct {
			Name   string `json:"name"`
			Status string `json:"status"`
		} `json:"data"`
	}
	_ = json.Unmarshal(body, &list)
	domain := ""
	if at := strings.LastIndex(from, "@"); at >= 0 {
		domain = strings.ToLower(strings.TrimSpace(from[at+1:]))
	}
	if domain == "" || domain == "resend.dev" {
		return OK, "Resend accepted the key."
	}
	for _, d := range list.Data {
		if strings.EqualFold(d.Name, domain) {
			if d.Status == "verified" {
				return OK, fmt.Sprintf("Resend accepted the key, and %s is a verified sending domain.", domain)
			}
			return Failed, fmt.Sprintf("Resend accepted the key, but %s is not verified yet (%s). Finish its DNS records in Resend.", domain, d.Status)
		}
	}
	return Failed, fmt.Sprintf("Resend accepted the key, but %s is not one of its sending domains. Add and verify it in Resend.", domain)
}

func (c Checker) stripe(ctx context.Context, secret, publishable, webhook string) (Status, string) {
	if secret == "" {
		return Failed, "No Stripe secret key is saved."
	}
	if !strings.HasPrefix(secret, "sk_") && !strings.HasPrefix(secret, "rk_") {
		return Failed, "That is not a Stripe secret key (they start with sk_test_ or sk_live_)."
	}
	mode := "test"
	if strings.Contains(secret, "_live_") {
		mode = "live"
	}
	if publishable != "" && !strings.HasPrefix(publishable, "pk_"+mode+"_") {
		return Failed, fmt.Sprintf("The publishable key is not a %s-mode key, but the secret key is. Use a matching pair.", mode)
	}
	if webhook != "" && !strings.HasPrefix(webhook, "whsec_") {
		return Failed, "The webhook signing secret should start with whsec_."
	}
	code, _, err := c.call(ctx, http.MethodGet, c.origin("https://api.stripe.com")+"/v1/balance", nil, secret, "")
	if status, message, ok := verdict("Stripe", code, err); !ok {
		return status, message
	}
	return OK, fmt.Sprintf("Stripe accepted the secret key (%s mode).", mode)
}

func (c Checker) razorpay(ctx context.Context, keyID, keySecret string) (Status, string) {
	if keyID == "" || keySecret == "" {
		return Failed, "The Razorpay key id and key secret are both needed."
	}
	code, _, err := c.call(ctx, http.MethodGet, c.origin("https://api.razorpay.com")+"/v1/payments?count=1", nil, keyID, keySecret)
	if status, message, ok := verdict("Razorpay", code, err); !ok {
		return status, message
	}
	mode := "test"
	if strings.HasPrefix(keyID, "rzp_live_") {
		mode = "live"
	}
	return OK, fmt.Sprintf("Razorpay accepted the key pair (%s mode).", mode)
}

// aiProviders lists a free, read-only call per model provider that only succeeds with a valid key.
var aiProviders = map[string]struct {
	name, origin, path, header, prefix string
}{
	"openai":        {"OpenAI", "https://api.openai.com", "/v1/models", "Authorization", "Bearer "},
	"anthropic":     {"Anthropic", "https://api.anthropic.com", "/v1/models", "x-api-key", ""},
	"google":        {"Google Gemini", "https://generativelanguage.googleapis.com", "/v1beta/models?pageSize=1", "x-goog-api-key", ""},
	"google-gemini": {"Google Gemini", "https://generativelanguage.googleapis.com", "/v1beta/models?pageSize=1", "x-goog-api-key", ""},
	"gemini":        {"Google Gemini", "https://generativelanguage.googleapis.com", "/v1beta/models?pageSize=1", "x-goog-api-key", ""},
	"groq":          {"Groq", "https://api.groq.com", "/openai/v1/models", "Authorization", "Bearer "},
	"openrouter":    {"OpenRouter", "https://openrouter.ai", "/api/v1/key", "Authorization", "Bearer "},
	"deepseek":      {"DeepSeek", "https://api.deepseek.com", "/user/balance", "Authorization", "Bearer "},
	"mistral":       {"Mistral", "https://api.mistral.ai", "/v1/models", "Authorization", "Bearer "},
}

// AIProviderCheckable reports whether a model provider has a free key check.
func AIProviderCheckable(provider string) bool {
	_, ok := aiProviders[strings.ToLower(provider)]
	return ok
}

func (c Checker) aiKey(ctx context.Context, provider, key string) (Status, string) {
	if key == "" {
		return Failed, "No key is saved."
	}
	p, ok := aiProviders[strings.ToLower(provider)]
	if !ok {
		return Unchecked, "This provider has no free way to check a key; it is checked by your next build that uses it."
	}
	header := map[string]string{p.header: p.prefix + key}
	if p.header == "x-api-key" {
		header["anthropic-version"] = "2023-06-01"
	}
	code, _, err := c.call(ctx, http.MethodGet, c.origin(p.origin)+p.path, header, "", "")
	if status, message, ok := verdict(p.name, code, err); !ok {
		return status, message
	}
	return OK, p.name + " accepted the key. No model was run."
}

// ErrPrivateAddress means a mail server resolved to an address the platform will not dial.
var ErrPrivateAddress = errors.New("private address")

func (c Checker) resolve(ctx context.Context, host string) ([]net.IP, error) {
	if c.Resolve != nil {
		return c.Resolve(ctx, host)
	}
	if ip := net.ParseIP(host); ip != nil {
		return []net.IP{ip}, nil
	}
	addrs, err := net.DefaultResolver.LookupIPAddr(ctx, host)
	if err != nil {
		return nil, err
	}
	ips := make([]net.IP, 0, len(addrs))
	for _, a := range addrs {
		ips = append(ips, a.IP)
	}
	return ips, nil
}

// publicIP is false for loopback, private, link-local, unspecified, multicast and CGNAT addresses.
func publicIP(ip net.IP) bool {
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() ||
		ip.IsUnspecified() || ip.IsMulticast() || ip.IsInterfaceLocalMulticast() {
		return false
	}
	if v4 := ip.To4(); v4 != nil && v4[0] == 100 && v4[1]&0xc0 == 64 { // 100.64.0.0/10
		return false
	}
	return true
}

func (c Checker) smtp(ctx context.Context, host, port, user, pass string) (Status, string) {
	if host == "" || user == "" || pass == "" {
		return Failed, "The mail server, username and password are all needed."
	}
	if port == "" {
		port = "587"
	}
	portNum, err := strconv.Atoi(port)
	if err != nil || portNum < 1 || portNum > 65535 {
		return Failed, "The port must be a number between 1 and 65535."
	}
	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	ips, err := c.resolve(ctx, host)
	if err != nil || len(ips) == 0 {
		return Failed, fmt.Sprintf("%s could not be found. Check the server name.", host)
	}
	// Dial the address that was checked, so a second lookup cannot point somewhere else.
	ip := ips[0]
	if !c.AllowPrivate {
		for _, candidate := range ips {
			if !publicIP(candidate) {
				return Failed, fmt.Sprintf("%s points to a private network address, which the platform does not connect to. Use your provider's public mail server.", host)
			}
		}
	}
	address := net.JoinHostPort(ip.String(), strconv.Itoa(portNum))
	dialer := &net.Dialer{Timeout: 10 * time.Second}
	var conn net.Conn
	tlsConfig := &tls.Config{ServerName: host, MinVersion: tls.VersionTLS12}
	if portNum == 465 {
		conn, err = tls.DialWithDialer(dialer, "tcp", address, tlsConfig)
	} else {
		conn, err = dialer.DialContext(ctx, "tcp", address)
	}
	if err != nil {
		return Failed, fmt.Sprintf("Could not connect to %s on port %d. Check the server and port.", host, portNum)
	}
	if deadline, ok := ctx.Deadline(); ok {
		_ = conn.SetDeadline(deadline)
	}
	client, err := smtp.NewClient(conn, host)
	if err != nil {
		_ = conn.Close()
		return Failed, fmt.Sprintf("%s on port %d did not answer like a mail server.", host, portNum)
	}
	defer func() { _ = client.Close() }()
	if err := client.Hello("omnistackai.check"); err != nil {
		return Failed, "The mail server did not accept a greeting."
	}
	if portNum != 465 {
		if ok, _ := client.Extension("STARTTLS"); ok {
			if err := client.StartTLS(tlsConfig); err != nil {
				return Failed, "The mail server's encryption (STARTTLS) failed: its certificate may not match " + host + "."
			}
		} else if !c.AllowPrivate {
			return Failed, "The mail server offers no encryption on this port, so the password would travel in the clear. Use port 587 or 465."
		}
	}
	if ok, _ := client.Extension("AUTH"); !ok {
		return Failed, "The mail server does not offer sign-in on this port."
	}
	if err := client.Auth(plainAuth{user: user, pass: pass}); err != nil {
		return Failed, "The mail server refused the username or password."
	}
	_ = client.Quit()
	return OK, fmt.Sprintf("Signed in to %s:%d as %s. No email was sent.", host, portNum, user)
}

// plainAuth is AUTH PLAIN without net/smtp's refusal of unencrypted local servers (the
// encryption rule is enforced above, where local development may relax it).
type plainAuth struct{ user, pass string }

func (a plainAuth) Start(*smtp.ServerInfo) (string, []byte, error) {
	return "PLAIN", []byte("\x00" + a.user + "\x00" + a.pass), nil
}

func (a plainAuth) Next(_ []byte, more bool) ([]byte, error) {
	if more {
		return nil, errors.New("unexpected server challenge")
	}
	return nil, nil
}
