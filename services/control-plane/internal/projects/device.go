package projects

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// PC-063: the Android emulator the Studio runs on this machine. There is one, so one account
// holds it at a time: whoever sets it up, starts it or opens an app on it, for deviceLease after
// their last action. Everyone else sees that it is in use and never its screen. Hosted devices,
// one per session, are PC-065.

const (
	deviceLease  = 30 * time.Minute
	deviceBudget = 30 * time.Second
	// Opening an app can download and install Expo Go first.
	deviceOpenBudget = 6 * time.Minute
)

type emulatorLease struct {
	mu     sync.Mutex
	holder string
	until  time.Time
}

var androidLease = &emulatorLease{}

// claim gives the device to user unless someone else holds a current lease.
func (l *emulatorLease) claim(user string, now time.Time) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.holder != "" && l.holder != user && now.Before(l.until) {
		return false
	}
	l.holder, l.until = user, now.Add(deviceLease)
	return true
}

// heldByOther reports whether another account holds a current lease.
func (l *emulatorLease) heldByOther(user string, now time.Time) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.holder != "" && l.holder != user && now.Before(l.until)
}

func (l *emulatorLease) release(user string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.holder == user {
		l.holder = ""
	}
}

func registerDevice(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /device/android", handleAndroid(deps, http.MethodGet, ""))
	mux.HandleFunc("POST /device/android", handleAndroid(deps, http.MethodPost, ""))
	mux.HandleFunc("GET /device/android/screen", handleAndroid(deps, http.MethodGet, "/screen"))
	mux.HandleFunc("POST /device/android/input", handleAndroid(deps, http.MethodPost, "/input"))
	mux.HandleFunc("POST /projects/{id}/device", handleProjectDevice(deps))
}

func handleAndroid(deps Deps, method, suffix string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		now := time.Now()
		var body io.Reader
		if method == http.MethodPost {
			raw, err := io.ReadAll(io.LimitReader(r.Body, 4096))
			if err != nil {
				writeError(w, http.StatusBadRequest, "invalid body")
				return
			}
			body = bytes.NewReader(raw)
			if suffix == "" {
				var in struct {
					Action string `json:"action"`
				}
				if json.Unmarshal(raw, &in) != nil {
					writeError(w, http.StatusBadRequest, "invalid body")
					return
				}
				if !androidLease.claim(user.ID, now) {
					writeError(w, http.StatusConflict, "the emulator is in use by another account")
					return
				}
				if in.Action == "stop" {
					defer androidLease.release(user.ID)
				}
			} else if !androidLease.claim(user.ID, now) {
				writeError(w, http.StatusConflict, "the emulator is in use by another account")
				return
			}
		} else if androidLease.heldByOther(user.ID, now) {
			if suffix == "/screen" {
				writeError(w, http.StatusConflict, "the emulator is in use by another account")
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"state": "in_use", "error": "Another account is using the emulator on this machine."})
			return
		}
		target := deps.AgentEngineURL + "/api/device/android" + suffix
		proxyUpstreamWithin(w, r, deps, method, target, body, deviceBudget)
	}
}

// handleProjectDevice opens the project's running mobile preview on the emulator.
func handleProjectDevice(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if !androidLease.claim(user.ID, time.Now()) {
			writeError(w, http.StatusConflict, "the emulator is in use by another account")
			return
		}
		var in struct {
			App string `json:"app"`
		}
		_ = json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&in)
		payload, _ := json.Marshal(map[string]string{"app": in.App})
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/device"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, bytes.NewReader(payload), deviceOpenBudget)
	}
}
