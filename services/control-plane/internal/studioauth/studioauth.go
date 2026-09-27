// Package studioauth proves to the Studio (agent-engine) that a request comes from this control
// plane (PC-009).
//
// The Studio builds, edits, previews and publishes any workspace it is asked to. Ownership is
// checked here, in the control plane; the Studio trusted whoever reached it. On one person's
// laptop that was only this process, but on a shared host it is anything that can open a socket.
// With OMNISTACKAI_STUDIO_TOKEN set, the Studio refuses requests without the token, and every
// request this process sends to the Studio's address carries it.
//
// It wraps http.DefaultTransport rather than each of the dozen clients that call the Studio, so a
// call site added later cannot forget it. The token goes only to the Studio's own origin.
package studioauth

import (
	"net/http"
	"net/url"
	"strings"
)

// Header is the request header the Studio checks.
const Header = "X-OmniStack-Studio-Token"

type transport struct {
	base   http.RoundTripper
	origin string
	token  string
}

func (t *transport) RoundTrip(r *http.Request) (*http.Response, error) {
	if originOf(r.URL) == t.origin && r.Header.Get(Header) == "" {
		r = r.Clone(r.Context())
		r.Header.Set(Header, t.token)
	}
	return t.base.RoundTrip(r)
}

func originOf(u *url.URL) string {
	if u == nil {
		return ""
	}
	return strings.ToLower(u.Scheme + "://" + u.Host)
}

// Wrap returns a RoundTripper that adds the token to requests for studioURL's origin only.
// With an empty token or an unparsable URL it returns base unchanged.
func Wrap(base http.RoundTripper, studioURL, token string) http.RoundTripper {
	parsed, err := url.Parse(studioURL)
	if token == "" || err != nil || parsed.Host == "" {
		return base
	}
	return &transport{base: base, origin: originOf(parsed), token: token}
}

// Install wraps http.DefaultTransport for the whole process.
func Install(studioURL, token string) {
	http.DefaultTransport = Wrap(http.DefaultTransport, studioURL, token)
}
