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

// UserHeader names the signed-in user a request acts for, so the Studio can apply per-user quotas.
// Only requests carrying the token are believed, and the control plane sets it from the session.
const UserHeader = "X-OmniStack-User"

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
//
// PC-107: it also keeps more idle connections to the Studio. The default keeps two per host, so a
// page load through the console's preview proxy - a dozen asset requests, each checking the
// preview - opened fresh connections from the container to the host, some stalled past the 15 s
// deadline, and each became a 404 and a missing script in the preview.
func Install(studioURL, token string) {
	if base, ok := http.DefaultTransport.(*http.Transport); ok {
		base.MaxIdleConns = 128
		base.MaxIdleConnsPerHost = 64
	}
	http.DefaultTransport = Wrap(http.DefaultTransport, studioURL, token)
}
