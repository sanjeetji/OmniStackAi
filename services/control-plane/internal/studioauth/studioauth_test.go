package studioauth

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestTheTokenGoesToTheStudioOnly(t *testing.T) {
	var gotStudio, gotOther string
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { gotStudio = r.Header.Get(Header) }))
	defer studio.Close()
	other := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { gotOther = r.Header.Get(Header) }))
	defer other.Close()

	client := &http.Client{Transport: Wrap(http.DefaultTransport, studio.URL, "s3cret")}
	for _, u := range []string{studio.URL + "/api/workspaces/x/preview", other.URL + "/elsewhere"} {
		resp, err := client.Get(u)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
	}
	if gotStudio != "s3cret" {
		t.Errorf("studio got %q, want the token", gotStudio)
	}
	if gotOther != "" {
		t.Errorf("another origin got %q; the token must never leave for it", gotOther)
	}
}

func TestNoTokenChangesNothing(t *testing.T) {
	if Wrap(http.DefaultTransport, "http://127.0.0.1:4173", "") != http.DefaultTransport {
		t.Error("an empty token must leave the transport untouched")
	}
}

// PC-107: Install keeps more idle connections to the Studio, and the token still goes with every
// call. (A client cloned from the default transport before Install carried no token at all.)
func TestInstallKeepsConnectionsAndTheToken(t *testing.T) {
	saved := http.DefaultTransport
	defer func() { http.DefaultTransport = saved }()
	base := &http.Transport{}
	http.DefaultTransport = base
	Install("http://studio.local:4173", "s3cret")
	wrapped, ok := http.DefaultTransport.(*transport)
	if !ok || wrapped.base != base || wrapped.token != "s3cret" {
		t.Fatalf("the default transport must carry the Studio token, got %#v", http.DefaultTransport)
	}
	if base.MaxIdleConnsPerHost != 64 || base.MaxIdleConns != 128 {
		t.Fatalf("idle connections per host = %d, want 64", base.MaxIdleConnsPerHost)
	}
}
