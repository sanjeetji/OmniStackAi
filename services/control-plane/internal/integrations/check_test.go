package integrations

import (
	"bufio"
	"context"
	"encoding/base64"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// fakeSMTP answers like a mail server that accepts one username and password.
func fakeSMTP(t *testing.T, user, pass string, startTLS bool) (host, port string) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go func(c net.Conn) {
				defer func() { _ = c.Close() }()
				r := bufio.NewReader(c)
				say := func(s string) { _, _ = c.Write([]byte(s + "\r\n")) }
				say("220 fake ESMTP")
				for {
					line, err := r.ReadString('\n')
					if err != nil {
						return
					}
					cmd := strings.TrimSpace(line)
					switch {
					case strings.HasPrefix(cmd, "EHLO"):
						if startTLS {
							say("250-fake")
							say("250-STARTTLS")
						} else {
							say("250-fake")
						}
						say("250 AUTH PLAIN")
					case strings.HasPrefix(cmd, "AUTH PLAIN "):
						got, _ := base64.StdEncoding.DecodeString(strings.TrimPrefix(cmd, "AUTH PLAIN "))
						if string(got) == "\x00"+user+"\x00"+pass {
							say("235 ok")
						} else {
							say("535 bad credentials")
						}
					case cmd == "QUIT":
						say("221 bye")
						return
					default:
						say("250 ok")
					}
				}
			}(conn)
		}
	}()
	host, port, _ = net.SplitHostPort(ln.Addr().String())
	return host, port
}

func TestAMailServerIsSignedIntoAndNothingIsSent(t *testing.T) {
	host, port := fakeSMTP(t, "me@example.com", "right", false)
	local := Checker{AllowPrivate: true}
	ctx := context.Background()
	if r := local.Check(ctx, "smtp", map[string]string{"host": host, "port": port, "username": "me@example.com", "password": "right"}); r.Status != OK {
		t.Fatalf("good password: %+v", r)
	}
	r := local.Check(ctx, "smtp", map[string]string{"host": host, "port": port, "username": "me@example.com", "password": "wrong"})
	if r.Status != Failed || strings.Contains(r.Message, "wrong") {
		t.Fatalf("wrong password: %+v", r)
	}
}

func TestAMailServerCannotBeUsedToReachThePrivateNetwork(t *testing.T) {
	host, port := fakeSMTP(t, "u", "p", false)
	hosted := Checker{}
	for _, h := range []string{host, "10.0.0.5", "169.254.169.254", "192.168.1.1", "100.64.0.1", "::1"} {
		r := hosted.Check(context.Background(), "smtp", map[string]string{"host": h, "port": port, "username": "u", "password": "p"})
		if r.Status != Failed || !strings.Contains(r.Message, "private network") {
			t.Fatalf("%s was dialled: %+v", h, r)
		}
	}
	// A name that resolves to a private address is refused the same way.
	named := Checker{Resolve: func(context.Context, string) ([]net.IP, error) { return []net.IP{net.ParseIP("127.0.0.1")}, nil }}
	if r := named.Check(context.Background(), "smtp", map[string]string{"host": "mail.evil.test", "port": port, "username": "u", "password": "p"}); r.Status != Failed {
		t.Fatalf("rebinding name: %+v", r)
	}
}

func TestProvidersDecideAndTheKeyNeverAppearsInTheAnswer(t *testing.T) {
	var seen []string
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = append(seen, r.Method+" "+r.URL.Path)
		user, pass, _ := r.BasicAuth()
		good := r.Header.Get("Authorization") == "Bearer good" || r.Header.Get("x-api-key") == "sk-ant-good" ||
			r.Header.Get("x-goog-api-key") == "good" || user == "sk_test_good" || (user == "rzp_test_id" && pass == "good")
		switch {
		case r.Header.Get("Authorization") == "Bearer busy":
			w.WriteHeader(http.StatusTooManyRequests)
		case good:
			_, _ = w.Write([]byte(`{"data":[]}`))
		default:
			w.WriteHeader(http.StatusUnauthorized)
		}
	}))
	defer api.Close()
	c := Checker{BaseURL: api.URL}
	ctx := context.Background()
	cases := []struct {
		integration string
		cfg         map[string]string
		want        Status
	}{
		{"stripe", map[string]string{"secret_key": "sk_test_good"}, OK},
		{"stripe", map[string]string{"secret_key": "sk_test_bad"}, Failed},
		{"stripe", map[string]string{"secret_key": "sk_test_good", "publishable_key": "pk_live_x"}, Failed}, // mixed modes
		{"razorpay", map[string]string{"key_id": "rzp_test_id", "key_secret": "good"}, OK},
		{"razorpay", map[string]string{"key_id": "rzp_test_id", "key_secret": "bad"}, Failed},
		{"ai:openai", map[string]string{"api_key": "good"}, OK},
		{"ai:openai", map[string]string{"api_key": "sk-bad-secret-value"}, Failed},
		{"ai:anthropic", map[string]string{"api_key": "sk-ant-good"}, OK},
		{"ai:google-gemini", map[string]string{"api_key": "good"}, OK},
		{"ai:groq", map[string]string{"api_key": "busy"}, Unchecked},
		{"ai:nvidia", map[string]string{"api_key": "nvapi-x"}, Unchecked},
	}
	for _, tc := range cases {
		r := c.Check(ctx, tc.integration, tc.cfg)
		if r.Status != tc.want {
			t.Errorf("%s %v: got %s (%s), want %s", tc.integration, tc.cfg, r.Status, r.Message, tc.want)
		}
		for _, v := range tc.cfg {
			if len(v) > 6 && strings.Contains(r.Message, v) {
				t.Errorf("%s: the answer repeats a credential: %s", tc.integration, r.Message)
			}
		}
	}
	for _, call := range seen {
		if !strings.HasPrefix(call, "GET ") {
			t.Errorf("a health test may only read: %s", call)
		}
	}
	unreachable := Checker{BaseURL: "http://127.0.0.1:1"}
	if r := unreachable.Check(ctx, "ai:openai", map[string]string{"api_key": "good"}); r.Status != Unchecked {
		t.Errorf("an unreachable provider decided something: %+v", r)
	}
}

func TestResendsAnswerForAnUnknownKeyIsAFailure(t *testing.T) {
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusBadRequest) // what api.resend.com answers, checked live
		_, _ = w.Write([]byte(`{"statusCode":400,"message":"API key is invalid","name":"validation_error"}`))
	}))
	defer api.Close()
	if r := (Checker{BaseURL: api.URL}).Check(context.Background(), "resend", map[string]string{"api_key": "re_x"}); r.Status != Failed {
		t.Fatalf("%+v", r)
	}
}

func TestASendingOnlyResendKeyIsRecognised(t *testing.T) {
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"name":"restricted_api_key","message":"This API key is restricted to only send emails"}`))
	}))
	defer api.Close()
	if r := (Checker{BaseURL: api.URL}).Check(context.Background(), "resend", map[string]string{"api_key": "re_x"}); r.Status != OK {
		t.Fatalf("%+v", r)
	}
}

func TestEveryCatalogEntrySaysHowItIsChecked(t *testing.T) {
	seen := map[string]bool{}
	for _, e := range Catalog {
		if seen[e.ID] || e.HowChecked == "" || e.Where == "" {
			t.Errorf("entry %q is incomplete or repeated", e.ID)
		}
		seen[e.ID] = true
		switch e.Verification {
		case "live", "format", "on_use":
		default:
			t.Errorf("%s: unknown verification %q", e.ID, e.Verification)
		}
		if strings.HasPrefix(e.ID, "ai:") && (e.Verification == "live") != AIProviderCheckable(strings.TrimPrefix(e.ID, "ai:")) {
			t.Errorf("%s: the catalog and the checks disagree", e.ID)
		}
	}
}
