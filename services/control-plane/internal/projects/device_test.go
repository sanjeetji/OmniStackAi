package projects

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// PC-063: one account holds the emulator at a time; the others never see its screen.
func TestAndroidDevice_OneAccountAtATime(t *testing.T) {
	androidLease = &emulatorLease{}
	pStore := newFakeProjectStore()
	alice := auth.User{EmailVerified: true, ID: "usr-dev-a", Email: "a@example.com"}
	bob := auth.User{EmailVerified: true, ID: "usr-dev-b", Email: "b@example.com"}
	proj, _ := pStore.CreateProject(context.Background(), alice.ID, "Phone App", "")

	var paths []string
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.Method+" "+r.URL.Path)
		if strings.HasSuffix(r.URL.Path, "/screen") {
			w.Header().Set("Content-Type", "image/png")
			_, _ = w.Write([]byte("\x89PNG"))
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"state":"running"}`))
	}))
	defer mock.Close()

	call := func(user auth.User, method, path, body string) (int, string) {
		server := setupTestServer(t, fakeAuthStore{user: user}, pStore, mock.URL)
		req, _ := http.NewRequest(method, server.URL+path, strings.NewReader(body))
		req.Header.Set("Authorization", testBearer)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		defer resp.Body.Close()
		out, _ := io.ReadAll(resp.Body)
		return resp.StatusCode, string(out)
	}

	if code, _ := call(alice, http.MethodPost, "/device/android", `{"action":"boot"}`); code != http.StatusOK {
		t.Fatalf("alice boot = %d", code)
	}
	if code, _ := call(alice, http.MethodGet, "/device/android/screen", ""); code != http.StatusOK {
		t.Fatalf("alice screen = %d", code)
	}
	if code, _ := call(alice, http.MethodPost, "/projects/"+proj.ID+"/device", `{}`); code != http.StatusOK {
		t.Fatalf("alice open = %d", code)
	}
	before := len(paths)
	if code, _ := call(bob, http.MethodGet, "/device/android/screen", ""); code != http.StatusConflict {
		t.Errorf("bob sees alice's screen: %d", code)
	}
	if code, _ := call(bob, http.MethodPost, "/device/android/input", `{"kind":"tap","x":1,"y":1}`); code != http.StatusConflict {
		t.Errorf("bob drives alice's device: %d", code)
	}
	if code, body := call(bob, http.MethodGet, "/device/android", ""); code != http.StatusOK || !strings.Contains(body, "in_use") {
		t.Errorf("bob's status = %d %s, want in_use", code, body)
	}
	if code, _ := call(bob, http.MethodPost, "/projects/"+proj.ID+"/device", `{}`); code != http.StatusNotFound {
		t.Errorf("bob opens alice's project = %d, want 404", code)
	}
	if len(paths) != before {
		t.Errorf("bob's requests reached the Studio: %v", paths[before:])
	}
	if code, _ := call(alice, http.MethodPost, "/device/android", `{"action":"stop"}`); code != http.StatusOK {
		t.Fatalf("alice stop = %d", code)
	}
	if code, _ := call(bob, http.MethodPost, "/device/android", `{"action":"boot"}`); code != http.StatusOK {
		t.Errorf("after alice stopped, bob boot = %d", code)
	}
	if paths[2] != "POST /api/workspaces/"+proj.ID+"/device" {
		t.Errorf("open went to %s", paths[2])
	}
}
